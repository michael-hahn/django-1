"""Splice middleware to enforce Django responses to be trusted sinks."""

from django.splice.splice import is_synthesized, to_untrusted, add_taints
from django.splice.identity import TaintSource, set_current_user_id
from django.db.models.query import QuerySet
from django.db.models import Model


def check_streaming_content(content):
    for chunk in content:
        # assert type(chunk) is SpliceBytes
        if is_synthesized(chunk):
            raise ValueError("The stream response contains synthesized data "
                             "and cannot pass through Django's SpliceMiddleware,"
                             "which allows only trusted, non-synthesized data")
        # Convert the content back to the built-in bytes type for downstream processing.
        yield bytes(chunk)


class SpliceMiddleware(object):
    """
    New-style middleware (after Django 1.10). This middleware records the
    identity of the client during request processing and checks the validity
    of the final response.
    During request processing, after user identification is finished, user
    data (provided in a form) is immediately tainted so that taint propagation
    happens right from the next middleware. Note that typically, middlewares
    should not modify or leak user data in any ways.

    Once response is checked, SpliceMiddleware must also convert the entire
    response (header + content) to built-in types (not Splice-aware types)
    because the downstream wsgi handler (wsgiref/handlers.py) does type check!

    Note that the header should already be of built-in str type because we
    do not shadow built-in str to be SpliceStr in http/response.py! The
    wsgi handler also does type check on the header to make sure they are str.
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

        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.
        # Unlike HttpResponse, StreamingHttpResponse does not have a content attribute.
        # We must test for streaming responses separately. Ref:
        # https://docs.djangoproject.com/en/3.1/topics/http/middleware/#dealing-with-streaming-responses
        # SimpleTemplateResponse and TemplateResponse are both subclasses of HttpResponse.
        if response.streaming:
            response.streaming_content = check_streaming_content(response.streaming_content)
        else:
            # assert type(response.content) is SpliceBytes
            if is_synthesized(response.content):
                raise ValueError("The response {value} is a synthesized data and "
                                 "cannot pass through Django's SpliceMiddleware, "
                                 "which allows only trusted, non-synthesized data"
                                 .format(value=response.content))

            # Convert the content back to the built-in bytes type for downstream processing.
            # IMPORTANT NOTE: we cannot directly do response.content because doing so will
            # trigger content's setter should will convert the content back to SpliceBytes!
            # Therefore, we circumvent this by directly setting the protected attr _container
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
