import time

from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import SuspiciousOperation
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import http_date
from django.http import HttpResponseRedirect
from django.utils.functional import SimpleLazyObject


from .auth import get_webmail_user
from . import settings


class WebmailMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        self.get_response = get_response

    def process_request(self, request):
        session_key = request.COOKIES.get(settings.WEBMAIL_SESSION_COOKIE_NAME)
        session = SessionStore(session_key)

        request.webmail_session = session
        request.webmail_user = SimpleLazyObject(lambda: get_webmail_user(request, session))

    def process_response(self, request, response):
        """
        If request.webmail_session was modified, or if the configuration is to save the
        session every time, save the changes and set a session cookie or delete
        the session cookie if the session has been emptied.
        """
        session = request.webmail_session

        try:
            accessed = session.accessed
            modified = session.modified
            empty = session.is_empty()
        except AttributeError:
            pass
        else:
            # First check if we need to delete this cookie.
            # The session should be deleted only if the session is entirely empty
            if settings.WEBMAIL_SESSION_COOKIE_NAME in request.COOKIES and empty:
                response.delete_cookie(
                    settings.WEBMAIL_SESSION_COOKIE_NAME,
                    path=settings.WEBMAIL_SESSION_COOKIE_PATH,
                    domain=settings.WEBMAIL_SESSION_COOKIE_DOMAIN,
                )
            else:
                if accessed:
                    patch_vary_headers(response, ('Cookie',))
                if (modified or settings.WEBMAIL_SESSION_SAVE_EVERY_REQUEST) and not empty:
                    if session.get_expire_at_browser_close():
                        max_age = None
                        expires = None
                    else:
                        max_age = session.get_expiry_age()
                        expires_time = time.time() + max_age
                        expires = http_date(expires_time)
                    # Save the session data and refresh the client cookie.
                    # Skip session save for 500 responses, refs #3881.
                    if response.status_code != 500:
                        try:
                            session.save()
                        except UpdateError:
                            raise SuspiciousOperation(
                                "The request's session was deleted before the "
                                "request completed. The user may have logged "
                                "out in a concurrent request, for example."
                            )

                        response.set_cookie(
                            settings.WEBMAIL_SESSION_COOKIE_NAME,
                            session.session_key, max_age=max_age,
                            expires=expires, domain=settings.WEBMAIL_SESSION_COOKIE_DOMAIN,
                            path=settings.WEBMAIL_SESSION_COOKIE_PATH,
                            secure=settings.WEBMAIL_SESSION_COOKIE_SECURE or None,
                            httponly=settings.WEBMAIL_SESSION_COOKIE_HTTPONLY or None,
                            samesite=settings.WEBMAIL_SESSION_COOKIE_SAMESITE,
                        )
        return response
