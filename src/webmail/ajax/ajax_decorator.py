import sys
import traceback
import functools

# from decorator import decorator

from django.conf import settings
from django.http import HttpResponseBadRequest, Http404
from django.http.response import JsonResponse
# TODO: Revisar esta parte
# from django.views.debug import ExceptionReporter

from webmail.logutils import get_logger


from .response import render_to_json, REASON_PHRASES
from .ajax_exceptions import AJAXError, FormAJAXError


logger = get_logger()


#@decorator
def ajax(f=None, login_required=False, require_GET=False, require_POST=False, methods=None, **ajax_kwargs):
    """
    Decorator who guesses the user response type and translates to a serialized
    JSON response. Usage::

        @ajax
        def my_view(request):
            do_something()
            # will send {'ok': true}

        @ajax
        def my_view(request):
            return {'key': 'value'}
            # will send {'ok': true,
                         'data': {'key': 'value'}}

        @ajax
        def my_view(request):
            return HttpResponse('<h1>Hi!</h1>')
            # will send {'status': 200, 'statusText': 'OK',
                         'content': '<h1>Hi!</h1>'}

        @ajax
        def my_view(request):
            return redirect('home')
            # will send {'status': 302, 'statusText': 'FOUND', 'location': '/'}

        # combination with others decorators:

        @ajax
        @login_required
        @require_POST
        def my_view(request):
            pass
            # if request user is not authenticated then the @login_required
            # decorator redirect to login page.
            # will send {'status': 302, 'statusText': 'FOUND',
                         'content': '/login'}

            # if request method is 'GET' then the @require_POST decorator return
            # a HttpResponseNotAllowed response.
            # will send {'status': 405, 'statusText': 'METHOD NOT ALLOWED',
                         'content': null}

    """

    if methods is not None:
        methods = set([method_name.upper() for method_name in methods])

    if require_GET:
        if methods is None:
            methods = set()

        methods.add("GET")

    if require_POST:
        if methods is None:
            methods = set()

        methods.add("POST")

    def decorator(f):
        @functools.wraps(f, assigned=functools.WRAPPER_ASSIGNMENTS)
        def inner(request, *args, **kwargs):
            if login_required and not request.webmail_user.is_authenticated:
                return JsonResponse(
                    {
                        'ok': False,
                        'error_code': "login_required",
                        'error_description': "Login required"
                    })

            if methods and request.method not in methods:
                return JsonResponse(
                    {
                        'ok': False,
                        'error_code': "method_not_allowed",
                        'error_description': "Method not allowed"
                    })

            try:
                result = f(request, *args, **kwargs)
                if isinstance(result, AJAXError):
                    raise result
            except Http404 as e:
                return JsonResponse({
                    'ok': False,
                    'error_code': 'http_error',
                    'error_data': {
                        'status_code': 404,
                        'status_text': str(e) or REASON_PHRASES[404]
                    }
                })
            except AJAXError as e:
                logger.warn('AJAXError: %s - %s'% (request.path, str(e)))

                payload = {
                    'ok': False
                }

                if e.error_code is not None:
                    payload['error_code'] = e.error_code

                if e.error_description is not None:
                    payload['error_description'] = e.error_description

                if e.error_data is not None:
                    payload['error_data'] = e.error_data

                return JsonResponse(payload)
            except Exception as e:
                exc_info = sys.exc_info()
                exc_type, error_message, trace = exc_info

                logger.error('Internal Server Error: %s' % request.path,
                    exc_info=exc_info,
                    extra={
                        'request': request
                    }
                )

                payload = {
                    'ok': False,
                    'error_code': 'internal_server_error',
                    'error_description': 'Internal server error'
                }

                if settings.DEBUG:
                    payload['traceback'] = [{'file': l[0], 'line': l[1], 'in': l[2], 'code': l[3]} for
                        l in traceback.extract_tb(trace)]
                    payload['exceptionMessage'] = error_message

                return JsonResponse(payload)
            else:
                return render_to_json(result, **ajax_kwargs)

        return inner

    if f is not None:
        return decorator(f)

    return decorator
