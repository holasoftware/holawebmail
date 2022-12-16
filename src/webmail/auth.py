import re


from django.middleware.csrf import rotate_token
from django.utils.crypto import constant_time_compare
from django.utils.translation import LANGUAGE_SESSION_KEY
from django.utils import timezone


from .models import WebmailUserModel, AnonymousUser
from .signals import user_logged_in_signal, user_logged_out_signal, user_login_failed_signal
from . import settings


AUTH_SESSION_KEY = '_auth_webmail_user_id'
AUTH_HASH_SESSION_KEY = '_auth_webmail_user_hash'


def _get_user_session_key(request):
    # This value in the session is always serialized to a string, so we need
    # to convert it back to Python whenever we access it.
    return WebmailUserModel._meta.pk.to_python(request.session[AUTH_SESSION_KEY])


def login(request, user):
    """
    Persist a user id and a backend in the request. This way a user doesn't
    have to reauthenticate on every request. Note that data set during
    the anonymous session is retained when the user logs in.
    """
    session = request.session
    session_auth_hash = user.get_session_auth_hash()

    if AUTH_SESSION_KEY in session:
        if _get_user_session_key(request) != user.pk or (
                session_auth_hash and
                not constant_time_compare(session.get(AUTH_HASH_SESSION_KEY, ''), session_auth_hash)):
            # To avoid reusing another user's session, create a new, empty
            # session if the existing session corresponds to a different
            # authenticated user.
            session.flush()
    else:
        session.cycle_key()

    session.set_user(user)

    session[AUTH_SESSION_KEY] = user._meta.pk.value_to_string(user)
    session[AUTH_HASH_SESSION_KEY] = session_auth_hash

    request.webmail_user = user

    rotate_token(request)

    user_logged_in_signal.send(sender=WebmailUserModel, request=request, user=user)


def logout(request):
    """
    Remove the authenticated user's ID from the request and flush their session
    data.
    """
    # Dispatch the signal before the user is logged out so the receivers have a
    # chance to find out *who* logged out.
    user = getattr(request, 'webmail_user', None)
    if not getattr(user, 'is_authenticated', True):
        user = None

    user_logged_out_signal.send(sender=user.__class__, request=request, user=user)

    # remember language choice saved to session
    language = request.session.get(LANGUAGE_SESSION_KEY)

    request.session.set_user(None)

    request.session.flush()

    if language is not None:
        request.session[LANGUAGE_SESSION_KEY] = language

    if hasattr(request, 'webmail_user'):
        request.webmail_user = AnonymousUser()


def get_webmail_user(request):
    """
    Return the user model instance associated with the given request session.
    If no user is retrieved, return an instance of `AnonymousUser`.
    """
    session = request.session
    user = AnonymousUser()

    try:
        user_id = _get_user_session_key(request)
    except KeyError:
        pass
    else:
        try:
            user = WebmailUserModel.objects.get(pk=user_id)
        except WebmailUserModel.DoesNotExist:
            return user

        # Verify the session
        session_hash = session.get(AUTH_HASH_SESSION_KEY)
        session_hash_verified = session_hash and constant_time_compare(
            session_hash,
            user.get_session_auth_hash()
        )
        if not session_hash_verified:
            session.flush()
            user = AnonymousUser()

    return user


def update_session_auth_hash(request, user):
    """
    Updating a user's password logs out all sessions for the user.

    Take the current request and the updated user object from which the new
    session hash will be derived and update the session hash appropriately to
    prevent a password change from logging out the session from which the
    password was changed.
    """
    
    session = request.session

    session.cycle_key()
    if request.webmail_user == user:
        session[AUTH_HASH_SESSION_KEY] = user.get_session_auth_hash()

