import os

from django.conf import settings as django_settings
from django.utils.translation import gettext_lazy as _


WEBMAIL_DOMAIN_NAME_MESSAGE_ID = getattr(django_settings, "WEBMAIL_DOMAIN_NAME_MESSAGE_ID", "holawebmail.com")
WEBMAIL_EMAIL_FOR_ERROR_NOTIFICATION = getattr(django_settings, "WEBMAIL_EMAIL_FOR_ERROR_NOTIFICATION", "error-delivery@holawebmail.com")
WEBMAIL_MANAGE_MAILBOXES_ENABLED = getattr(django_settings, "WEBMAIL_MANAGE_MAILBOXES_ENABLED", True)
WEBMAIL_MANAGE_POP3_MAIL_SERVER_ENABLED = getattr(django_settings, "WEBMAIL_MANAGE_POP3_MAIL_SERVER_ENABLED", True)
WEBMAIL_MANAGE_SMTP_SERVER_ENABLED = getattr(django_settings, "WEBMAIL_MANAGE_SMTP_SERVER_ENABLED", True)

# Security authentication
WEBMAIL_ACCESS_LOGS_ENABLED = getattr(django_settings, "WEBMAIL_ACCESS_LOGS_ENABLED", True)
WEBMAIL_CONTROL_SESSIONS_ENABLED = getattr(django_settings, "WEBMAIL_CONTROL_SESSIONS_ENABLED", True)


WEBMAIL_PLUGINS = getattr(django_settings, "WEBMAIL_PLUGINS", None)


# UI settings
WEBMAIL_UI_BRAND_NAME = getattr(django_settings, "WEBMAIL_UI_BRAND_NAME", "¡Hola Mail!")
WEBMAIL_UI_SHOW_COMPOSE_BTN = getattr(django_settings, "WEBMAIL_UI_SHOW_COMPOSE_BTN", True)
WEBMAIL_UI_SHOW_BCC = getattr(django_settings, "WEBMAIL_UI_SHOW_BCC", True)
WEBMAIL_UI_SHOW_CC = getattr(django_settings, "WEBMAIL_UI_SHOW_CC", True)
WEBMAIL_UI_SHOW_FOLDERS = getattr(django_settings, "WEBMAIL_UI_SHOW_FOLDERS", True)
WEBMAIL_UI_SHOW_FOLDER_INBOX = getattr(django_settings, "WEBMAIL_UI_SHOW_FOLDER_INBOX", True)
WEBMAIL_UI_SHOW_FOLDER_SENT = getattr(django_settings, "WEBMAIL_UI_SHOW_FOLDER_SENT", True)
WEBMAIL_UI_SHOW_FOLDER_SPAM = getattr(django_settings, "WEBMAIL_UI_SHOW_FOLDER_SPAM", True)
WEBMAIL_UI_SHOW_FOLDER_TRASH = getattr(django_settings, "WEBMAIL_UI_SHOW_FOLDER_TRASH", True)
WEBMAIL_UI_ITEMS_PER_PAGE = getattr(django_settings, "WEBMAIL_UI_ITEMS_PER_PAGE", 10)
WEBMAIL_UI_MAILBOX_LIST_PAGE_SIZE = getattr(django_settings, "WEBMAIL_UI_MAILBOX_LIST_PAGE_SIZE", WEBMAIL_UI_ITEMS_PER_PAGE)
WEBMAIL_UI_MESSAGE_LIST_PAGE_SIZE = getattr(django_settings, "WEBMAIL_UI_MESSAGE_LIST_PAGE_SIZE", WEBMAIL_UI_ITEMS_PER_PAGE)


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

WEBMAIL_MAIL_SEND_ENABLED = getattr(django_settings, "WEBMAIL_MAIL_SEND_ENABLED", True)


WEBMAIL_SPAM_FILTER = getattr(django_settings, "WEBMAIL_SPAM_FILTER", None)
WEBMAIL_MAX_RETRIES_SEND_MAIL= getattr(django_settings, "WEBMAIL_MAX_RETRIES_SEND_MAIL", 1)
WEBMAIL_WAIT_TIME_NEXT_RETRY_SEND_MAIL = getattr(django_settings, "WEBMAIL_WAIT_TIME_NEXT_RETRY_SEND_MAIL", 0.2)
WEBMAIL_HTML2TEXT = getattr(django_settings, "WEBMAIL_HTML_2_TEXT", "webmail.html2text")
WEBMAIL_DEFAULT_FROM_EMAIL = getattr(django_settings, "WEBMAIL_DEFAULT_FROM_EMAIL", None)
WEBMAIL_EXCERPT_MAX_CHARS = getattr(django_settings, "WEBMAIL_EXCERPT_MAX_CHARS", 20)

# Login page settings
WEBMAIL_LOGIN_HTML_HEAD_TITLE = getattr(django_settings, "WEBMAIL_LOGIN_HTML_HEAD_TITLE", _("Hola Webmail Login"))
WEBMAIL_LOGIN_LOGO_ALT = getattr(django_settings, "WEBMAIL_LOGIN_LOGO_ALT", 'Logo Hola Mail')
WEBMAIL_LOGIN_LOGO_IMAGE_URL = getattr(django_settings, "WEBMAIL_LOGIN_LOGO_IMAGE_URL", 'webmail/images/logo.png')
WEBMAIL_LOGIN_LOGO_WIDTH = getattr(django_settings, "WEBMAIL_LOGIN_LOGO_WIDTH", 72)
WEBMAIL_LOGIN_LOGO_HEIGHT = getattr(django_settings, "WEBMAIL_LOGIN_LOGO_HEIGHT", 72)
WEBMAIL_LOGIN_TITLE = getattr(django_settings, "WEBMAIL_LOGIN_TITLE", _("Hola Webmail Login"))
WEBMAIL_LOGIN_BACKGROUND_COLOR = getattr(django_settings, "WEBMAIL_LOGIN_BACKGROUND_COLOR", "white")


# Sign up page settings
WEBMAIL_SIGNUP_ENABLED = getattr(django_settings, "WEBMAIL_SIGNUP_ENABLED", True)
WEBMAIL_SIGNUP_LOGO_ALT = getattr(django_settings, "WEBMAIL_SIGNUP_LOGO_ALT", 'Logo Hola Mail')
WEBMAIL_SIGNUP_LOGO_IMAGE_URL = getattr(django_settings, "WEBMAIL_SIGNUP_LOGO_IMAGE_URL", 'webmail/images/logo.png')
WEBMAIL_SIGNUP_LOGO_WIDTH = getattr(django_settings, "WEBMAIL_SIGNUP_LOGO_WIDTH", 72)
WEBMAIL_SIGNUP_LOGO_HEIGHT = getattr(django_settings, "WEBMAIL_SIGNUP_LOGO_HEIGHT", 72)
WEBMAIL_SIGNUP_TITLE = getattr(django_settings, "WEBMAIL_SIGNUP_TITLE", _("Sign up"))
WEBMAIL_SIGNUP_BACKGROUND_COLOR = getattr(django_settings, "WEBMAIL_SIGNUP_BACKGROUND_COLOR", "white")
WEBMAIL_SIGNUP_HTML_HEAD_TITLE = getattr(django_settings, "WEBMAIL_SIGNUP_HTML_HEAD_TITLE", _("Hola Webmail Sign Up"))


WEBMAIL_AUTOLOGIN_ENABLED = getattr(django_settings, "WEBMAIL_AUTOLOGIN_ENABLED", False)

# Import/Export settings
WEBMAIL_EXPORT_MAIL_ENABLED = getattr(django_settings, "WEBMAIL_EXPORT_MAIL_ENABLED", True)
WEBMAIL_IMPORT_MAIL_ENABLED = getattr(django_settings, "WEBMAIL_IMPORT_MAIL_ENABLED", True)


WEBMAIL_EMAIL_HEADERS_PAGE_ENABLED = getattr(django_settings, "WEBMAIL_EMAIL_HEADERS_PAGE_ENABLED", True)

WEBMAIL_USER_CAN_MARK_AS_SPAM = getattr(django_settings, "WEBMAIL_USER_CAN_MARK_AS_SPAM", True)

# Autodraft settings
WEBMAIL_AUTODRAFT_ENABLED = getattr(django_settings, "WEBMAIL_AUTODRAFT_ENABLED", False)
WEBMAIL_AUTODRAFT_SAVE_DELAY = getattr(django_settings, "WEBMAIL_AUTODRAFT_SAVE_DELAY", False)

# Attachment settings
WEBMAIL_ATTACHMENT_UPLOAD_TO = getattr(django_settings, "WEBMAIL_ATTACHMENT_UPLOAD_TO", 'mailbox_attachments/%Y/%m/%d/')
WEBMAIL_ATTACHMENT_MAX_SIZE = getattr(django_settings, "WEBMAIL_ATTACHMENT_MAX_SIZE", 10000000)


# Fake data settings
WEBMAIL_FAKE_DATA_NAMES = getattr(django_settings, "WEBMAIL_FAKE_DATA_NAMES", ["miguel", "juan", "alberto", "roberto", "manuel", "carlos", "marian", "miriam", "ana", "tania", "sebastian", "monica", "david", "santiago", "samuel", "nuria", "jorge", "daniel", "teresa", "maria", "dolores", "samanta", "veronica", "cristina", "rodrigo", "lucas", "pablo", "matilde", "francisco", "sandra", "sheila", "marina", "domingo", "pedro", "matias", "yolanda", "luis", "ramon"])
WEBMAIL_FAKE_DATA_SURNAMES = getattr(django_settings, "WEBMAIL_FAKE_DATA_SURNAMES", ["martinez", "lopez", "garcia", "rodriguez", "martin", "gonzalez", "franco", "gutierrez", "guzman", "de vega", "calderon", "de la barca"])
WEBMAIL_FAKE_DATA_EMAIL_DOMAINS = getattr(django_settings, "WEBMAIL_FAKE_DATA_EMAIL_DOMAINS", ['yahoo.com', 'msn.com', 'zoho.com', 'hotmail.com', 'live.com', 'outlook.com', 'aol.com', 'email.com', 'tutanota.com', 'fastmail.com', 'gmail.com', 'hushmail.com', 'mail.ru', 'aim.com', 'proton.me', 'mailinator.com'])

WEBMAIL_STRIP_UNALLOWED_MIMETYPES = getattr(django_settings, "WEBMAIL_STRIP_UNALLOWED_MIMETYPES", False)
WEBMAIL_ALLOWED_MIMETYPES = getattr(django_settings, "WEBMAIL_ALLOWED_MIMETYPES", ['text/plain', 'text/html'])
WEBMAIL_DEFAULT_CHARSET = getattr(django_settings, "WEBMAIL_DEFAULT_CHARSET", 'iso8859-1')


WEBMAIL_EMAIL_PARSING_STRICT_POLICY = getattr(django_settings, "WEBMAIL_EMAIL_PARSING_STRICT_POLICY", False)
