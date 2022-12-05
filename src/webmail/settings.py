import os

from django.conf import settings as django_settings
from django.utils.translation import gettext_lazy as _


APP_INDEX = os.environ.get("APP", "")


WEBMAIL_DOMAIN_NAME_MESSAGE_ID = getattr(django_settings, "WEBMAIL_DOMAIN_NAME_MESSAGE_ID", "holawebmail.com")
WEBMAIL_EMAIL_FOR_ERROR_NOTIFICATION = getattr(django_settings, "WEBMAIL_EMAIL_FOR_ERROR_NOTIFICATION", "error-delivery@holawebmail.com")
WEBMAIL_ENABLE_MANAGE_MAILBOXES = getattr(django_settings, "WEBMAIL_ENABLE_MANAGE_MAILBOXES", True)
WEBMAIL_ENABLE_ACCESS_LOGS = getattr(django_settings, "WEBMAIL_ENABLE_ACCESS_LOGS", True)
WEBMAIL_ENABLE_MANAGE_POP3_MAIL_SERVER = getattr(django_settings, "WEBMAIL_ENABLE_MANAGE_POP3_MAIL_SERVER", True)
WEBMAIL_ENABLE_MANAGE_SMTP_SERVER = getattr(django_settings, "WEBMAIL_ENABLE_MANAGE_SMTP_SERVER", True)
WEBMAIL_ENABLE_REGISTRATION = getattr(django_settings, "WEBMAIL_ENABLE_REGISTRATION", True)
WEBMAIL_ENABLE_DEMO_REGISTRATION_PAGE = getattr(django_settings, "WEBMAIL_ENABLE_DEMO_REGISTRATION_PAGE", True)
WEBMAIL_PLUGINS = getattr(django_settings, "WEBMAIL_PLUGINS", None)

# Compose settings
WEBMAIL_SHOW_COMPOSE_BTN = getattr(django_settings, "WEBMAIL_SHOW_COMPOSE_BTN", True)
WEBMAIL_SHOW_BCC = getattr(django_settings, "WEBMAIL_SHOW_BCC", True)
WEBMAIL_SHOW_CC = getattr(django_settings, "WEBMAIL_SHOW_CC", True)

# Mailer settings
WEBMAIL_MAILER_PAUSE_SEND = getattr(django_settings, "WEBMAIL_MAILER_PAUSE_SEND", False)
WEBMAIL_MAILER_SLEEP_TIME_IF_QUEUE_EMPTY = getattr(django_settings, "WEBMAIL_MAILER_SLEEP_TIME_IF_QUEUE_EMPTY", 30)
WEBMAIL_MAILER_LOCK_PATH = getattr(django_settings, "WEBMAIL_MAILER_LOCK_PATH", "sending_mail")
WEBMAIL_MAILER_LOCK_WAIT_TIMEOUT = getattr(django_settings, "WEBMAIL_MAILER_LOCK_WAIT_TIMEOUT", -1)
WEBMAIL_MAILER_SLEEP_TIME_IF_NO_LOCK_ACQUIRED = getattr(django_settings, "WEBMAIL_MAILER_SLEEP_TIME_IF_NO_LOCK_ACQUIRED", 20)
WEBMAIL_MAILER_MAX_PROCESSED_TASKS_IN_BATCH = getattr(django_settings, "WEBMAIL_MAILER_MAX_PROCESSED_TASKS_IN_BATCH", None)
WEBMAIL_MAILER_MAX_SUCCEED_TASKS_IN_BATCH = getattr(django_settings, "WEBMAIL_MAILER_MAX_SUCCEED_TASKS_IN_BATCH", None)
WEBMAIL_MAILER_MAX_FAILED_TASKS_IN_BATCH = getattr(django_settings, "WEBMAIL_MAILER_MAX_FAILED_TASKS_IN_BATCH", None)
WEBMAIL_MAILER_MAX_FAILED_OR_DEFERRED_TASKS_IN_BATCH = getattr(django_settings, "WEBMAIL_MAILER_MAX_FAILED_OR_DEFERRED_TASKS_IN_BATCH", None)
WEBMAIL_MAILER_MAX_TIMES_MAIL_DEFERRED = getattr(django_settings, "WEBMAIL_MAILER_MAX_TIMES_MAIL_DEFERRED", None)
WEBMAIL_MAILER_DEFER_DURATION = getattr(django_settings, "WEBMAIL_MAILER_DEFER_DURATION", 2)
WEBMAIL_MAILER_THROTTLE_TIME = getattr(django_settings, "WEBMAIL_MAILER_THROTTLE_TIME", 0)
WEBMAIL_MAILER_DELETE_COMPLETED_TASKS = getattr(django_settings, "WEBMAIL_MAILER_DELETE_COMPLETED_TASKS", True)

WEBMAIL_SPAM_FILTER = getattr(django_settings, "WEBMAIL_SPAM_FILTER", None)
WEBMAIL_MAX_RETRIES_SEND_MAIL= getattr(django_settings, "WEBMAIL_MAX_RETRIES_SEND_MAIL", 1)
WEBMAIL_WAIT_TIME_NEXT_RETRY_SEND_MAIL = getattr(django_settings, "WEBMAIL_WAIT_TIME_NEXT_RETRY_SEND_MAIL", 0.2)
WEBMAIL_HTML2TEXT = getattr(django_settings, "WEBMAIL_HTML_2_TEXT", "webmail.html2text")
WEBMAIL_DEFAULT_FROM_EMAIL = getattr(django_settings, "WEBMAIL_DEFAULT_FROM_EMAIL", None)
WEBMAIL_MAX_CHARS_EXCERPT = getattr(django_settings, "WEBMAIL_MAX_CHARS_EXCERPT", 20)

# Login page settings
WEBMAIL_LOGIN_HTML_HEAD_TITLE = getattr(django_settings, "WEBMAIL_LOGIN_HTML_HEAD_TITLE", _("Hola Webmail Login"))
WEBMAIL_LOGIN_LOGO_ALT = getattr(django_settings, "WEBMAIL_LOGIN_LOGO_ALT", 'Logo Hola Mail')
WEBMAIL_LOGIN_LOGO_IMAGE_URL = getattr(django_settings, "WEBMAIL_LOGIN_LOGO_IMAGE_URL", 'webmail/images/logo.svg')
WEBMAIL_LOGIN_LOGO_WIDTH = getattr(django_settings, "WEBMAIL_LOGIN_LOGO_WIDTH", 72)
WEBMAIL_LOGIN_LOGO_HEIGHT = getattr(django_settings, "WEBMAIL_LOGIN_LOGO_HEIGHT", 72)
WEBMAIL_LOGIN_TITLE = getattr(django_settings, "WEBMAIL_LOGIN_TITLE", _("Hola Webmail Login"))
WEBMAIL_LOGIN_BACKGROUND_COLOR = getattr(django_settings, "WEBMAIL_LOGIN_BACKGROUND_COLOR", "white")
WEBMAIL_SIGNUP_HTML_HEAD_TITLE = getattr(django_settings, "WEBMAIL_SIGNUP_HTML_HEAD_TITLE", _("Hola Webmail Sign Up"))

# Sign up page settings
WEBMAIL_SIGNUP_LOGO_ALT = getattr(django_settings, "WEBMAIL_SIGNUP_LOGO_ALT", 'Logo Hola Mail')
WEBMAIL_SIGNUP_LOGO_IMAGE_URL = getattr(django_settings, "WEBMAIL_SIGNUP_LOGO_IMAGE_URL", 'webmail/images/logo.svg')
WEBMAIL_SIGNUP_LOGO_WIDTH = getattr(django_settings, "WEBMAIL_SIGNUP_LOGO_WIDTH", 72)
WEBMAIL_SIGNUP_LOGO_HEIGHT = getattr(django_settings, "WEBMAIL_SIGNUP_LOGO_HEIGHT", 72)
WEBMAIL_SIGNUP_TITLE = getattr(django_settings, "WEBMAIL_SIGNUP_TITLE", _("Sign up"))
WEBMAIL_SIGNUP_BACKGROUND_COLOR = getattr(django_settings, "WEBMAIL_SIGNUP_BACKGROUND_COLOR", "white")

WEBMAIL_AUTOLOGIN_ENABLED = getattr(django_settings, "WEBMAIL_AUTOLOGIN_ENABLED", False)

WEBMAIL_BRAND_NAME = getattr(django_settings, "WEBMAIL_BRAND_NAME", "¡Hola Mail!")

WEBMAIL_SHOW_FOLDERS = getattr(django_settings, "WEBMAIL_SHOW_FOLDERS", True)
WEBMAIL_SHOW_FOLDER_INBOX = getattr(django_settings, "WEBMAIL_SHOW_FOLDER_INBOX", True)
WEBMAIL_SHOW_FOLDER_SENT = getattr(django_settings, "WEBMAIL_SHOW_FOLDER_SENT", True)
WEBMAIL_SHOW_FOLDER_SPAM = getattr(django_settings, "WEBMAIL_SHOW_FOLDER_SPAM", True)
WEBMAIL_SHOW_FOLDER_TRASH = getattr(django_settings, "WEBMAIL_SHOW_FOLDER_TRASH", True)

WEBMAIL_EXPORT_MAIL_ENABLED = getattr(django_settings, "WEBMAIL_EXPORT_MAIL_ENABLED", True)
WEBMAIL_IMPORT_MAIL_ENABLED = getattr(django_settings, "WEBMAIL_IMPORT_MAIL_ENABLED", True)

WEBMAIL_SHOW_EMAIL_HEADERS_BTN = getattr(django_settings, "WEBMAIL_SHOW_EMAIL_HEADERS_BTN", True)

WEBMAIL_USER_CAN_MARK_AS_SPAM = getattr(django_settings, "WEBMAIL_USER_CAN_MARK_AS_SPAM", True)

WEBMAIL_AUTODRAFT_ENABLED = getattr(django_settings, "WEBMAIL_AUTODRAFT_ENABLED", False)
WEBMAIL_AUTODRAFT_SAVE_DELAY = getattr(django_settings, "WEBMAIL_AUTODRAFT_SAVE_DELAY", False)

WEBMAIL_ITEMS_PER_PAGE = getattr(django_settings, "WEBMAIL_ITEMS_PER_PAGE", 10)
WEBMAIL_MAILBOX_ITEMS_PER_PAGE = getattr(django_settings, "WEBMAIL_MAILBOX_ITEMS_PER_PAGE", WEBMAIL_ITEMS_PER_PAGE)
WEBMAIL_MESSAGE_ITEMS_PER_PAGE = getattr(django_settings, "WEBMAIL_MESSAGE_ITEMS_PER_PAGE", 10)

WEBMAIL_MAIL_SEND_ENABLED = getattr(django_settings, "WEBMAIL_MAIL_SEND_ENABLED", True)

WEBMAIL_ATTACHMENT_UPLOAD_TO = getattr(django_settings, "WEBMAIL_ATTACHMENT_UPLOAD_TO", 'mailbox_attachments/%Y/%m/%d/')
WEBMAIL_MAX_ATTACHMENT_SIZE = getattr(django_settings, "WEBMAIL_MAX_ATTACHMENT_SIZE", 10000000)

# Fake data settings
WEBMAIL_FAKE_DATA_NAMES = getattr(django_settings, "WEBMAIL_FAKE_DATA_NAMES", ["miguel", "juan", "alberto", "roberto", "manuel", "carlos", "marian", "miriam", "ana", "tania", "sebastian", "monica", "david", "santiago", "samuel", "nuria", "jorge", "daniel", "teresa", "maria", "dolores", "samanta", "veronica", "cristina", "rodrigo", "lucas", "pablo", "matilde", "francisco", "sandra", "sheila", "marina", "domingo", "pedro", "matias", "yolanda", "luis", "ramon"])
WEBMAIL_FAKE_DATA_SURNAMES = getattr(django_settings, "WEBMAIL_FAKE_DATA_SURNAMES", ["martinez", "lopez", "garcia", "rodriguez", "martin", "gonzalez", "franco", "gutierrez", "guzman", "de vega", "calderon", "de la barca"])
WEBMAIL_FAKE_DATA_EMAIL_DOMAINS = getattr(django_settings, "WEBMAIL_FAKE_DATA_EMAIL_DOMAINS", ['yahoo.com', 'msn.com', 'zoho.com', 'hotmail.com', 'live.com', 'outlook.com', 'aol.com', 'email.com', 'tutanota.com', 'fastmail.com', 'gmail.com', 'hushmail.com', 'mail.ru', 'aim.com', 'proton.me', 'mailinator.com'])

WEBMAIL_STRIP_UNALLOWED_MIMETYPES = getattr(django_settings, "WEBMAIL_STRIP_UNALLOWED_MIMETYPES", False)
# TODO: Not used yet
WEBMAIL_MIMETYPES_ALLOWED = getattr(django_settings, "WEBMAIL_MIMETYPES_ALLOWED", ['text/plain', 'text/html'])
WEBMAIL_DEFAULT_CHARSET = getattr(django_settings, "WEBMAIL_DEFAULT_CHARSET", 'iso8859-1')

# Session cookie settings
WEBMAIL_SESSION_COOKIE_NAME = getattr(django_settings, "WEBMAIL_SESSION_COOKIE_NAME", "webmail_session%s" % APP_INDEX)

# Age of cookie, in seconds (default: 2 weeks).
WEBMAIL_SESSION_COOKIE_AGE = getattr(django_settings, "WEBMAIL_SESSION_COOKIE_AGE", 60 * 60 * 24 * 7 * 2)

# A string like "example.com", or None for standard domain cookie.
WEBMAIL_SESSION_COOKIE_DOMAIN = getattr(django_settings, "WEBMAIL_SESSION_COOKIE_DOMAIN", None)

# Whether the session cookie should be secure (https:// only).
WEBMAIL_SESSION_COOKIE_SECURE = getattr(django_settings, "WEBMAIL_SESSION_COOKIE_SECURE", False)

# The path of the session cookie.
WEBMAIL_SESSION_COOKIE_PATH = getattr(django_settings, "WEBMAIL_SESSION_COOKIE_PATH", '/')

# Whether to use the HttpOnly flag.
WEBMAIL_SESSION_COOKIE_HTTPONLY = getattr(django_settings, "WEBMAIL_SESSION_COOKIE_HTTPONLY", True)

# Whether to set the flag restricting cookie leaks on cross-site requests. This can be 'Lax', 'Strict', or None to disable the flag.
WEBMAIL_SESSION_COOKIE_SAMESITE = getattr(django_settings, "WEBMAIL_SESSION_COOKIE_SAMESITE", 'Strict')

# Whether to save the session data on every request.
WEBMAIL_SESSION_SAVE_EVERY_REQUEST = getattr(django_settings, "WEBMAIL_SESSION_SAVE_EVERY_REQUEST", False)

# Whether a user's session cookie expires when the Web browser is closed.
WEBMAIL_SESSION_EXPIRE_AT_BROWSER_CLOSE = getattr(django_settings, "WEBMAIL_SESSION_EXPIRE_AT_BROWSER_CLOSE", False)
