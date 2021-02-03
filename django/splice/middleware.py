"""
Splice middleware to enforce trusted sinks. This middleware
does not run if response if not a TemplateResponse object
(or equivalent). For example, Django's render() function in
django.shortcuts bypasses this middleware because it does not
return TemplateResponse but HttpResponse instead. We use a
decorator, called "check_context", on the render() function
to check its context argument to enforce trusted data sink.
"""

from functools import wraps
from django.splice.untrustedtypes import is_synthesized


def check_context(render_func):
    """Decorator that checks render()'s context argument before actual rendering."""
    @wraps(render_func)
    def _wrapped_render_func(request, template_name, context=None, content_type=None, status=None, using=None):
        if context:
            for key, value in context.items():
                if is_synthesized(value):
                    raise ValueError("{value} is a synthesized value and cannot "
                                     "pass through a trusted sink".format(value=value))
        return render_func(request, template_name, context, content_type, status, using)
    return _wrapped_render_func


class SpliceMiddleware(object):
    """New-style middleware (after Django 1.10)."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.
        return response

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
            if is_synthesized(value):
                raise ValueError("{value} is a synthesized value and cannot "
                                 "pass through a trusted sink".format(value=value))
        return response
