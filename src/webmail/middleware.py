from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject


from .auth import get_webmail_user


class WebmailMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.webmail_user = SimpleLazyObject(lambda: get_webmail_user(request))
