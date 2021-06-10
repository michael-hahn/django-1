"""
Splice middleware for taint tracking and for enforcing Django responses to be trusted sinks.
Multiple middlewares are defined here due to middleware ordering and required time of action.
"""

from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.cache import cache
from django.splice.splice import is_synthesized, to_untrusted, add_taints
from django.splice.splicetypes import SpliceMixin, SpliceStr, SpliceBytes
from django.splice.identity import TaintSource, set_current_user_id, empty_taint, to_int, get_taint_from_id
from django.splice.synthesis import init_synthesizer
from django.splice.replace import replace
from django.splice.constraints import merge_constraints
from django.splice import settings
from django.db.models.query import QuerySet
from django.db.models import Model
from django.apps import apps
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse

import redis, threading, cProfile
from pstats import Stats
from redis_rw_lock import RWLock
from readerwriterlock import rwlock

import ctypes

import gc
import time
import logging

# Note: logging triggers Django PASSWORD_RESET_TIMEOUT_DAYS method in LazySettings class
# (django.conf.__init__) if use ERROR or CRITICAL level logging. In Django v3.1.2,
# PASSWORD_RESET_TIMEOUT_DAYS is still defined in global_settings.py (django/django/conf).
# even though it is deprecated. ERROR or CRITICAL level logging would trigger backtracing
# which Django's exception handler would gather all settings, including PASSWORD_RESET_TIMEOUT_DAYS
# for debugging. This would trigger the method in the LazySettings class. Alas,
# DO NOT USE ERROR OR CRITICAL LEVEL FOR LOGGING; USE INFO.
logger = logging.getLogger(__name__)
logging.basicConfig(filename="data/ReviewUser_1_splice_lock.log")

# NOTE: Set up a Redis connection pool to avoid making a new Redis
#       connection for every request (if we use Redis for readers-
#       writer lock implementation for quiescent point enforcement
#       in SpliceDeletionMiddleware). See these SO posts:
#       https://stackoverflow.com/q/27412135/9632613
#       https://stackoverflow.com/a/31740866/9632613
#       However, although the number of new connection requests
#       have reduced (and supposedly, connecting/disconnecting for
#       each request is very expensive), the performance of using
#       Redis for RWLock is still quite bad.
# connection_pool = redis.ConnectionPool()

# TODO: Consider this optimization in the future
# For performance, we skip taint propagation for read-only requests.
# ESCAPE_URLS = ['/product/']

def check_streaming_content(content):
    for chunk in content:
        if is_synthesized(chunk):
            raise PermissionDenied("The stream response contains synthesized data "
                                   "and cannot pass through Django's SpliceMiddleware,"
                                   "which allows only trusted, non-synthesized data")
        # Convert the content back to the built-in bytes type for downstream processing.
        yield bytes(chunk)


class SpliceTaintMiddleware(object):
    """
    New-style middleware (after Django 1.10). This middleware records the
    identity of the client during request processing. After user identification
    is finished, user data (e.g., provided in a form) is immediately tainted
    so that taint propagation happens right from the next middleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        # Set the identity of the authenticated user for
        # taint tracking; do nothing for anonymous users.
        if request.user.is_authenticated:
            # print("SpliceTaintMiddleware.__call__: user ID: {}".format(request.user.id))
            set_current_user_id(request.user.id)

        # TODO: Consider this optimization in the future
        # skip_taint = False
        # path = request.path
        # for url in ESCAPE_URLS:
        #     if url in path:
        #         skip_taint = True
        #         break
        # if skip_taint:
        #     response = self.get_response(request)
        #     return response

        # Start taint tracking right away. User data is
        # originally stored as str in GET and POST, both
        # of which are QuerySet. They are in fact immutable:
        # https://docs.djangoproject.com/en/3.1/ref/request-response/#django.http.QueryDict
        # To modify the values in these two QuerySets, we
        # must perform a copy() as directed by Django.
        request.GET = request.GET.copy()
        for k, v in request.GET.items():
            v = to_untrusted(v)
            v = add_taints(v, TaintSource.current_user_taint)
            request.GET[k] = v
        request.POST = request.POST.copy()
        for k, v in request.POST.items():
            v = to_untrusted(v)
            v = add_taints(v, TaintSource.current_user_taint)
            request.POST[k] = v
        # When SessionMiddleware is activated, each HttpRequest object
        # will have a session attribute, which is a dictionary-like object.
        # You can read it and write to request.session at any point.
        # You can edit it multiple times. Reference:
        # https://docs.djangoproject.com/en/3.1/topics/http/sessions/#using-sessions-in-views
        # Because Splice has no control over session data if it is set
        # before this middleware (and after SessionMiddleware), any
        # session data derived from user data that is set before this
        # middleware is called will not be tainted. Therefore, we do
        # not allow any session data to be set before this middleware.
        if hasattr(request, 'session'):
            if request.session.modified:
                raise ImproperlyConfigured(
                    "The Splice taint middleware requires that any"
                    " middleware before it does not modify session data.  Edit your"
                    " MIDDLEWARE structure to make sure this is the case")

        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.
        # SpliceTaintMiddleware does nothing to response.
        return response


class SpliceSinkMiddleware(object):
    """
    New-style middleware (after Django 1.10). This middleware checks
    the validity of the final response. Once response is checked,
    SpliceSinkMiddleware must also convert the entire response (header +
    content) to built-in types (not Splice-aware types) because the
    downstream wsgi handler (wsgiref/handlers.py) does type check!
    (Note that the header should be of built-in str type. The wsgi
    handler does type check on the header to make sure they are str.)
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        # SpliceSinkMiddleware does nothing to request.
        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.
        # Check response.cookies
        if is_synthesized(response.cookies):
            raise PermissionDenied("The response cookies contain synthesized data and "
                                   "cannot pass through Django's SpliceSinkMiddleware, "
                                   "which allows only trusted, non-synthesized data")
        # Check headers
        for k, v in response._headers.items():
            # A header value v is itself a tuple (k, v)
            if is_synthesized(v):
                raise PermissionDenied("The response header {} is synthesized and "
                                       "cannot pass through Django's SpliceSinkMiddleware, "
                                       "which allows only trusted, non-synthesized data".format(k))
            if isinstance(v[1], SpliceStr):
                response[k] = v[1].unsplicify()
        # Unlike HttpResponse, StreamingHttpResponse does not have a content attribute.
        # We must test for streaming responses separately. Ref:
        # https://docs.djangoproject.com/en/3.1/topics/http/middleware/#dealing-with-streaming-responses
        # SimpleTemplateResponse and TemplateResponse are both subclasses of HttpResponse.

        # TODO: Synthesis checking of the content should have been done already.
        if response.streaming:
            response.streaming_content = check_streaming_content(response.streaming_content)
        else:
            if is_synthesized(response.content):
                raise PermissionDenied("The response {value} is synthesized data and "
                                       "cannot pass through Django's SpliceSinkMiddleware, "
                                       "which allows only trusted, non-synthesized data"
                                       .format(value=response.content))

            # Convert the content back to the built-in bytes type for downstream processing.
            # IMPORTANT NOTE: we cannot directly do response.content because doing so will
            # trigger content's setter should will convert the content back to SpliceBytes!
            # Therefore, we circumvent this by directly setting the protected attr _container
            # Check response code at django.http.response
            response._container = [bytes(response.content)]
        return response

    # FIXME: __call__ should probably handle the template case if context-to-bytestring preserves Splice taint!
    # def process_template_response(self, request, response):
    #     """
    #     request is an HttpRequest object. response is the *TemplateResponse* object (or equivalent)
    #     returned by a Django view or by a middleware. This function is called just after the view has
    #     finished executing, if the response instance has a render() method indicating that it is a
    #     TemplateResponse or equivalent. It must return a response object that implements a render method.
    #     It could alter the given response by changing response.template_name and response.context_data,
    #     or it could create and return a brand-new TemplateResponse or equivalent.
    #     Note that because this function is applied only to TemplateResponse objects or equivalent,
    #     if a view returns *HttpResponse* or uses render() shortcut to respond, this function does not
    #     perform trusted data sink enforcement!
    #     * All view classes that subclass TemplateView (or its subclasses) return TemplateResponse.
    #     * All view classes that inherit TemplateResponseMixin mixin (or its subclasses) return
    #       TemplateResponse (this category includes all Django's generic class-based views).
    #     * All view functions that directly return TemplateResponse
    #     The following approach would bypass this function:
    #     * All view functions/classes that return HttpResponse
    #     * All view functions/classes that use http shortcuts
    #     """
    #     # response.context_data is the context data to be used when rendering the template, which must be a dict
    #     for key, value in response.context_data.items():
    #         # The context might contain QuerySets from database queries
    #         if isinstance(value, QuerySet):
    #             for v in value:
    #                 # v is an instance of a Model, so we should go through all of its model fields
    #                 if isinstance(v, Model):
    #                     for field in v._meta.fields:
    #                         field_value = getattr(v, field.name)
    #                         if is_synthesized(field_value):
    #                             raise ValueError("{value} is a synthesized field and cannot "
    #                                              "pass through a trusted sink".format(value=field.name))
    #         # For other types of value
    #         elif is_synthesized(value):
    #             raise ValueError("{value} is a synthesized value and cannot "
    #                              "pass through a trusted sink".format(value=value))
    #     return response


class SpliceDeletionMiddleware(object):
    """
    New-style middleware (after Django 1.10). This middleware should be
    placed at the very top of the middleware stack. It has two functions:
    1) For a regular request, the request can only be handled if there is
    no pending or on-going deletion request. The middleware enforces this
    requirement; 2) For a deletion request, this middleware pauses the
    request until all on-going regular requests have been handled and then
    performs user deletion. We use a distributed readers-write lock to
    enforce the ordering requirements.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # https://github.com/elarivie/pyReaderWriterLock
        self.lock = rwlock.RWLockWrite()                                    # Threading implementation

        # Profiling code
        # self.cp = cProfile.Profile()

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        # A distributed readers-writer lock to "stop the world"
        # It uses Redis as server. Reference:
        # https://github.com/swapnilsm/redis-rw-lock
        # redis_conn = redis.StrictRedis(connection_pool=connection_pool)   # Redis implementation

        # The deletion request can try to grab the REQUEST writer lock.
        # The writer lock is prioritized so new regular requests cannot
        # obtain reader locks. The deletion request will get the writer
        # lock once all reader locks acquired before the writer lock are
        # released.
        #
        # Use COOKIES to decide whether the request is a deletion request
        # or a regular request. For a deletion request, the cookie contains
        # the ID of the user to be deleted. No deletion is performed if
        # 1) the delete_user cookie is not set, or 2) the ID is 0.
        # Note that COOKIES' value is str, so we convert it to int.
        duid = int(request.COOKIES.get('delete_user', '0'))
        # If it is a deletion request, we will obtain the REQUEST writer lock
        # We will also not call get_response() because nothing else should
        # run but this deletion process in this middleware.
        if duid != 0:
            # request_lock = RWLock(redis_conn, "REQUEST", mode=RWLock.WRITE)   # Redis implementation
            request_lock = self.lock.gen_wlock()                                # Threading implementation

            # start the timer to compute latency for deletion to start
            # (i.e., the time it takes to grab a writer lock for deletion)
            start_timer = time.perf_counter()
            request_lock.acquire()
            logger.info("writer,{},{},{},".format(request.method, request.path, time.perf_counter() - start_timer))

            # For bitarray taint implementation, duid must be converted into bitarray and then back to id.
            # This is because duid is used to determine the position of the set bit in the taint bitarray.
            if settings.BITARRAY:
                dutaint = empty_taint()
                dutaint[duid] = True
                duid = to_int(dutaint)
            # Much easier if we use int taint implementation
            else:
                dutaint = get_taint_from_id(duid)
                duid = dutaint
            # start the timer to compute blocking time to perform deletion
            start_timer = time.perf_counter()
            # Save some statistics
            row_deleted, cell_deleted = 0, 0
            row_total, cell_total = 0, 0
            # Go through all models (database tables) in the apps
            for model in apps.get_models(include_auto_created=False, include_swapped=True):
                # We use an iterator to fetch data in chunks, in case
                # the data is too big to fit into memory at once.
                # The `iterator()` method ensures only a few rows are
                # fetched from the database at a time, saving memory.
                dataset = model.objects.all()
                for row in dataset.iterator():
                    row_total += 1
                    modified = False
                    delete = False
                    for field in row._meta.fields:
                        # Skip taint/synthesized cells
                        if field.name.endswith("_taint") or field.name.endswith("_synthesized"):
                            continue
                        cell_total += 1
                        taint_col = field.name + '_taint'
                        synth_col = field.name + '_synthesized'
                        # Note all columns have a corresponding taint column.
                        # Therefore, the default value is set to be 0, which
                        # would be a "system" taint (i.e., objects, if tainted
                        # with 0, do not belong to any user).
                        taint_val = getattr(row, taint_col, 0)
                        # Deletion by setting the cell to NULL.
                        # Note: For this to work, the data column in the table
                        #  must accept NULL value. Alas, the null=True argument
                        #  must be set in the field definition in the model.
                        #  There exist cases where doing so is not possible (
                        #  e.g., if a column is set to be the primary key).
                        # Note that a unique column (field's unique is set to
                        # be True) can still set to be NULL!
                        # TODO: Alternative approach to deletion?
                        if taint_val == duid:
                            # If a row's primary key is tainted and needs to be
                            # deleted, we can't set it to NULL. We have to delete.
                            if field.primary_key:
                                modified = True
                                delete = True
                                break
                            setattr(row, field.name, None)
                            # Clear the taint associated with the deleted cell
                            setattr(row, taint_col, 0)
                            # Set the synthesized column to true
                            setattr(row, synth_col, True)
                            cell_deleted += 1
                            modified = True
                    # Reflected the change, if exists, to the database. We either remove the record
                    # (if primary key must be deleted) or update some of its values to NULL.
                    if modified:
                        if delete:
                            row.delete()
                            row_deleted += 1
                        else:
                            row.save()
            logger.info(",delete,database,{},{}/{} rows and {}/{} cells"
                        .format(time.perf_counter() - start_timer, row_deleted,
                                row_total, cell_deleted, cell_total))
            start_timer = time.perf_counter()   # restart the timer for program state splicing
            # Save some statistics
            obj_deleted, obj_synthesized = 0, 0
            # Go through the rest of objects in a program state
            # get_objects() returns a list of all objects tracked by the garbage collector
            # See reference: https://docs.python.org/3/library/gc.html#gc.get_objects
            # More description about GC: https://devguide.python.org/garbage_collector/
            # But it seem like finding Python objects in memory can only be best effort:
            # https://stackoverflow.com/questions/62686644/python-find-current-objects-in-memory.
            # This is also because not all objects are tracked by GC.
            objs = gc.get_objects()
            for obj in objs:
                # Only Splice objects with the taint of the user to be deleted need to be synthesized.
                if isinstance(obj, SpliceMixin) and obj.taints == dutaint:
                    # Perform Splice object deletion through synthesis.
                    synthesizer = init_synthesizer(obj)
                    # Concretize constraints for obj using symbolic constraints from its
                    # enclosing data structure.
                    concrete_constraints = []
                    # Each constraint in obj.constraints is a callable that takes the
                    # object as the only argument. Each callback function returns
                    # concrete constraints in disjunctive normal form.
                    for constraint in obj.constraints:
                        concrete_constraints.append(constraint(obj))
                    # Merge all concrete constraints, if needed
                    if not concrete_constraints:
                        merged_constraints = None
                    else:
                        merged_constraints = concrete_constraints[0]
                        for concrete_constraint in concrete_constraints[1:]:
                            merged_constraints = merge_constraints(merged_constraints, concrete_constraint)
                    # Use merged concrete constraints to perform value synthesis.
                    # Synthesis handles setting trusted and synthesized flags properly
                    synthesized_obj = synthesizer.splice_synthesis(merged_constraints)
                    if synthesized_obj is not None:
                        # If synthesis was successful, replace the original obj with the synthesized object.
                        # Note that using ctypes.memmove does not seem to work (leads to segfault).
                        # ctypes.memmove(id(obj), id(synthesized_obj), object.__sizeof__(obj))
                        # ctypes.memmove ref: https://docs.python.org/2/library/ctypes.html#ctypes.memmove
                        try:
                            replace(obj, synthesized_obj)
                            obj_synthesized += 1
                        except:
                            # If replacement failed for some reason, the best we can do is to change object attributes.
                            logger.info("Replacing {} is unsuccessful, we will mark the object "
                                        "synthesized instead".format(obj))
                            obj.trusted = False
                            obj.synthesized = True
                            obj.taints = empty_taint()
                            obj.constraints = []
                    else:
                        # If synthesis failed for some reason, the best we can do is to change object attributes.
                        obj.trusted = False
                        obj.synthesized = True
                        obj.taints = empty_taint()
                        obj.constraints = []
                    obj_deleted += 1

            logger.info(",delete,program state,{},{}/{} objects deleted ({} deleted objects are synthesized)"
                        .format(time.perf_counter() - start_timer, obj_deleted, len(objs), obj_synthesized))

            # If TAINT_DROP is set, some cached HttpResponse may not contain any taint
            # because taint has already dropped when the response is being rendered (for
            # performance optimization). This can be problematic because Splice can no
            # longer identify user data in those cached responses. For correctness and
            # simplicity, we remove everything from the cache. Note that:
            # 1) Django allows different caches and cache backends to exist simultaneously,
            #    so it is possible to put all HttpResponse caches in a specific cache so
            #    that other valid cached data is not cleared. This minimizes the negative
            #    impact on caching when a user is being spliced.
            # 2) Even if only one cache is used, deletion-aware developers can set all
            #    HttpResponse caches with for example the same cache key prefixing, or
            #    use any separation mechanism described in the Django's cache doc:
            #    https://docs.djangoproject.com/en/3.0/topics/cache/#accessing-the-cache
            # 3) Even if no changes are made to cache to help reduce cache performance
            #    like in 1) and 2), it is still OK to clear out the entire cache given
            #    that deletion (splice) is rare.
            # Note that in our current design, everything *except* data structure data
            # (which is in-memory data stored in a different Redis cache and properly
            # tainted) is cleared out when TAINT_DROP is set for simplicity.
            if settings.TAINT_DROP:
                cache.clear()
            # Generate a response directly to return to the user.
            # After deletion is done, redirect the user to the login page.
            response = HttpResponseRedirect(reverse('lfs_login'))
            # Although the content of HttpResponseRedirect response is b'',
            # django.http.response is Splice-aware, so the content will be
            # converted to SpliceBytes, which is not acceptable in write().
            # We do the conversion back to bytes in SpliceSinkMiddleware after
            # taint checking, but in this case, we will not go through
            # SpliceSinkMiddleware. So we will manually convert empty SpliceBytes
            # content here for HttpResponseRedirect().
            response._container = [bytes(response.content)]
            # Set the 'delete_user' cookie to 0.
            response.set_cookie('delete_user', 0)
        # A regular request
        else:
            # The request can try to grab a REQUEST reader lock.
            # It will not get it (blocked) if deletion is in progress.
            # request_lock = RWLock(redis_conn, "REQUEST", mode=RWLock.READ)    # Redis implementation
            request_lock = self.lock.gen_rlock()                                # Threading implementation

            # start the timer to compute latency for request to start
            # (i.e., the time it takes to grab a reader lock)
            start_timer = time.perf_counter()

            # self.cp.enable()
            request_lock.acquire()
            # self.cp.disable()

            logger.info("reader,{},{},{},".format(request.method, request.path, time.perf_counter() - start_timer))
            # For a regular request, business as usual
            response = self.get_response(request)
        # Release the REQUEST reader or writer lock
        request_lock.release()

        # Profiling code
        # p = Stats(self.cp)
        # p.sort_stats('tottime')
        # p.print_stats()
        return response
