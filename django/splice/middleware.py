"""
Splice middleware for taint tracking and for enforcing Django responses to be trusted sinks.
Multiple middlewares are defined here due to middleware ordering and required time of action.
"""

from django.core.exceptions import ImproperlyConfigured
from django.splice.splice import is_synthesized, to_untrusted, add_taints
from django.splice.splicetypes import SpliceStr
from django.splice.identity import TaintSource, set_current_user_id
from django.db.models.query import QuerySet
from django.db.models import Model
from django.apps import apps
from django.core.cache import caches

import gc


def check_streaming_content(content):
    for chunk in content:
        # assert type(chunk) is SpliceBytes
        if is_synthesized(chunk):
            raise ValueError("The stream response contains synthesized data "
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
            set_current_user_id(request.user.id)
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
            # raise ValueError("The response cookies contain synthesized data and "
            #                  "cannot pass through Django's SpliceSinkMiddleware, "
            #                  "which allows only trusted, non-synthesized data")
            print("The response cookies contain synthesized data and "
                  "cannot pass through Django's SpliceSinkMiddleware, "
                  "which allows only trusted, non-synthesized data")
        # Check headers
        for k, v in response._headers.items():
            # A header value v is itself a tuple (k, v)
            if is_synthesized(v):
                print("Header {} contains synthesized data: {}.".format(k, v))
                # raise ValueError("The response header {} is synthesized and "
                #                  "cannot pass through Django's SpliceSinkMiddleware, "
                #                  "which allows only trusted, non-synthesized data"
                #                  .format(k))
            if isinstance(v[1], SpliceStr):
                response[k] = v[1].unsplicify()
        # Unlike HttpResponse, StreamingHttpResponse does not have a content attribute.
        # We must test for streaming responses separately. Ref:
        # https://docs.djangoproject.com/en/3.1/topics/http/middleware/#dealing-with-streaming-responses
        # SimpleTemplateResponse and TemplateResponse are both subclasses of HttpResponse.
        if response.streaming:
            response.streaming_content = check_streaming_content(response.streaming_content)
        else:
            # assert type(response.content) is SpliceBytes
            print("SpliceSinkMiddleware: checking response content...\n{}".format(response.content))
            if is_synthesized(response.content):
                print("Content contains synthesized data.")
                # raise ValueError("The response {value} is synthesized data and "
                #                  "cannot pass through Django's SpliceSinkMiddleware, "
                #                  "which allows only trusted, non-synthesized data"
                #                  .format(value=response.content))

            # Convert the content back to the built-in bytes type for downstream processing.
            # IMPORTANT NOTE: we cannot directly do response.content because doing so will
            # trigger content's setter should will convert the content back to SpliceBytes!
            # Therefore, we circumvent this by directly setting the protected attr _container
            # Check response code at django.http.response
            response._container = [bytes(response.content)]
        return response

    # FIXME: __call__ should probably handle the template case if context-to-bytestring preserves Splice tags!
    def process_template_response(self, request, response):
        """
        request is an HttpRequest object. response is the *TemplateResponse* object (or equivalent)
        returned by a Django view or by a middleware. This function is called just after the view has
        finished executing, if the response instance has a render() method indicating that it is a
        TemplateResponse or equivalent. It must return a response object that implements a render method.
        It could alter the given response by changing response.template_name and response.context_data,
        or it could create and return a brand-new TemplateResponse or equivalent.
        Note that because this function is applied only to TemplateResponse objects or equivalent,
        if a view returns *HttpResponse* or uses render() shortcut to respond, this function does not
        perform trusted data sink enforcement!
        * All view classes that subclass TemplateView (or its subclasses) return TemplateResponse.
        * All view classes that inherit TemplateResponseMixin mixin (or its subclasses) return
          TemplateResponse (this category includes all Django's generic class-based views).
        * All view functions that directly return TemplateResponse
        The following approach would bypass this function:
        * All view functions/classes that return HttpResponse
        * All view functions/classes that use http shortcuts
        """
        # response.context_data is the context data to be used when rendering the template, which must be a dict
        for key, value in response.context_data.items():
            # The context might contain QuerySets from database queries
            if isinstance(value, QuerySet):
                for v in value:
                    # v is an instance of a Model, so we should go through all of its model fields
                    if isinstance(v, Model):
                        for field in v._meta.fields:
                            field_value = getattr(v, field.name)
                            if is_synthesized(field_value):
                                raise ValueError("{value} is a synthesized field and cannot "
                                                 "pass through a trusted sink".format(value=field.name))
            # For other types of value
            elif is_synthesized(value):
                raise ValueError("{value} is a synthesized value and cannot "
                                 "pass through a trusted sink".format(value=value))
        return response


class SpliceDeletionMiddleware(object):
    """
    TBD
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        # SpliceDeletionMiddleware does nothing to request.
        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.
        # Go through all models (database tables) in the apps
        for model in apps.get_models(include_auto_created=False, include_swapped=True):
            print("Checking model {}...".format(model.__name__))
            # We use an iterator to fetch data in chunks, in case
            # the data is too big to fit into memory at once.
            # The `iterator()` method ensures only a few rows are
            # fetched from the database at a time, saving memory.
            dataset = model.objects.all()
            for row in dataset.iterator():
                for field in row._meta.fields:
                    field_value = getattr(row, field.name)
                    if is_synthesized(field_value):
                        print("{} is a synthesized field with value {}".format(field.name, field_value))
        # TODO: Invalidating caches here.
        # FIXME: How do we delete arbitrary objects in a program state?
        gc.get_objects()

        return response
