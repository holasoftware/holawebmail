import functools
from urllib.parse import urlencode


from django.contrib.auth import REDIRECT_FIELD_NAME
from django.urls import reverse
from django.http import HttpResponseRedirect


def login_required(fn, *args, **kwargs):
    @functools.wraps(fn)
    def wrapped(request, *args, **kwargs):
        if not hasattr(request, "webmail_user") or request.webmail_user is None or not request.webmail_user.is_authenticated:
            login_url = reverse("webmail:login")
            redirect_to = request.build_absolute_uri(request.path)
            # redirect_to = request.get_full_path()

            return HttpResponseRedirect(login_url + "?" + urlencode({
                REDIRECT_FIELD_NAME: redirect_to
            }))
        else:
            return fn(request, *args, **kwargs)
    return wrapped

