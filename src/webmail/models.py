import datetime
import time
import uuid
import email.header
from email.utils import parseaddr
from email import message_from_string
# from quopri import encode as encode_quopri
from io import BytesIO
import mimetypes
import os
import base64
from tempfile import NamedTemporaryFile
import smtplib
import sys
import traceback
import hashlib
from importlib import import_module


from django.core.files.base import ContentFile, File
from django.core.mail.message import EmailMessage as DjangoEmailMessage, EmailMultiAlternatives as DjangoEmailMultiAlternatives
from django.contrib.sessions.backends.base import SessionBase as SessionStoreBase
from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.crypto import get_random_string, salted_hmac
from django.utils.functional import cached_property
from django.utils.text import get_text_list
from django.utils import timezone
from django.dispatch import receiver as signal_receiver
from django.urls import reverse as reverse_url


from . import utils, settings
from .signals import inbound_email_received_signal, user_logged_in_signal
from .validators import validate_email_with_name, username_validator, hexdigits_validator
from .pop3_transport import Pop3Transport
from .fields import CommaSeparatedEmailField
from .srp import salted_verification_key
from .srp.srp_defaults import DEFAULT_BIT_GROUP_NUMBER
from .logutils import get_logger
from .exceptions import NoSmtpServerConfiguredException, InvalidEmailMessageException


logger = get_logger()


if settings.WEBMAIL_SPAM_FILTER is None:
    def is_spam(message):
        return False
else:
    is_spam = import_module(settings.WEBMAIL_SPAM_FILTER).is_spam


if settings.WEBMAIL_HTML2TEXT is None:
    html2text = import_module(settings.WEBMAIL_HTML2TEXT).html2text
else:
    html2text = None


def parse_addresses_from_header(header):
    addresses = []
    for address in header.split(','):
        if address:
            addresses.append(
                parseaddr(
                    address
                )[1].lower()
            )
    return addresses


class WebmailUserManager(models.Manager):
    def make_random_password(self, length=10,
                             allowed_chars='abcdefghjkmnpqrstuvwxyz'
                                           'ABCDEFGHJKLMNPQRSTUVWXYZ'
                                           '23456789'):
        """
        Generate a random password with the given length and given
        allowed_chars. The default value of allowed_chars does not have "I" or
        "O" or letters and digits that look similar -- just to avoid confusion.
        """
        return get_random_string(length, allowed_chars)

    def create_user(self, username, password=None, displayed_name=None,  srp_group=DEFAULT_BIT_GROUP_NUMBER):
        """
        Create and save a user with the given username, displayed name and password.
        """
        if not password:
            password = self.make_random_password()

        s, v = salted_verification_key(username, password)
        salt = s.hex()
        verifier = hex(v)[2:]

        user = self.model(username=username, displayed_name=displayed_name, salt=salt, verifier=verifier, srp_group=srp_group)

        user.save(using=self._db)
        return user


class WebmailUser(models.Model):
    username = models.CharField(
        _('Username'),
        max_length=30,
        unique=True,
        help_text=_('Required. 30 characters or fewer. Letters and digits only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        }
    )

    displayed_name = models.CharField(
        _('Displayed name'),
        help_text=_('Displayed name in admin panel. Keep it blank to display username only.'),
        max_length=150,
        null=True,
        blank=True
    )

    # password_updated_date
    last_time_password_changed = models.DateTimeField(_('Last time password changed'), help_text=_('Last time password was changed'), null=True, blank=True, editable=False)

    is_2fa_enabled = models.BooleanField(_('2FA'), help_text=_('Is 2 factor authentication enabled?'), db_index=True, default=False)

    # verified = models.BooleanField(default=False)

    is_active = models.BooleanField(
        _('Active'),
        default=True,
        db_index=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        )
    )

    srp_group = models.IntegerField(choices=((1024,1024), (1536,1536), (2048,2048), (3072, 3072), (4096, 4096), (6144, 6144), (8192, 8192)), blank=True)
    verifier = models.TextField(validators=[hexdigits_validator], max_length=1000, blank=True)
    salt = models.CharField(validators=[hexdigits_validator], max_length=255, blank=True)

    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects = WebmailUserManager()

    class Meta:
        verbose_name = _('Webmail User')
        verbose_name_plural = _('Webmail Users')

#    def set_from_password(self, password, srp_group=1024):
#        self.srp_group = srp_group
#        N, g, s, v = mathtls.makeVerifier(self.user.username,
#                                          password,
#                                          self.srp_group)
#        self.srpN = b64encode(mathtls.numberToString(N))
#        self.srpg = str(g)
#        self.verifier = b64encode(mathtls.numberToString(v))
#        self.salt = b64encode(s)

    def get_session_auth_hash(self):
        """
        Return an HMAC of the SRP parameters.
        """
        key_salt = "webmail.models.WebmailUser.get_session_auth_hash"
        return salted_hmac(key_salt, "%s:%s:%s" % (self.srp_group, self.verifier, self.salt)).hexdigest()


    @property
    def is_anonymous(self):
        """
        Always return False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True

    def __str__(self):
        return self.username

    def activate(self):
        self.is_active = True
        self.save(update_fields=["is_active"])

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=["is_active"])

    def get_last_login_date(self):
        return self.access_logs.all().latest("date").date


class WebmailSessionManager(models.Manager):
    use_in_migrations = True

    # TODO: Revisar esta parte
    def encode(self, session_dict):
        """
        Return the given session dictionary serialized and encoded as a string.
        """
        session_store_class = self.model.get_session_store_class()
        return session_store_class().encode(session_dict)

    def save(self, user, session_key, session_dict, expire_date):
        s = self.model(user=user, session_key=session_key, session_data=self.encode(session_dict), expire_date=expire_date)
        if session_dict:
            s.save()
        else:
            s.delete()  # Clear sessions with no data.
        return s

    def filter_active(self, user=None):
        kwargs = {
            "expire_date__gte": timezone.now()
        }

        if user is not None:
            kwargs["user"] = user

        return self.filter(**kwargs)

    def filter_other_active_sessions(self, request):
        return WebmailSession.objects.filter_active(
            user=request.webmail_user).exclude(session_key=request.session.session_key)

    def filter_expired(self, user=None):
        kwargs = {
            "expire_date__lt": timezone.now()
        }

        if user is not None:
            kwargs["user"] = user

        return self.filter(**kwargs)

    def delete_expired(self, user=None):
        return self.filter_expired(user=user).delete()


class WebmailSessionAbstractModel(models.Model):
    uuid = models.UUIDField(_('UUID'), unique=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(WebmailUser, null=True, blank=True, editable=False, db_index=True, on_delete=models.CASCADE)
    session_key = models.CharField(_('Session key'), max_length=40, primary_key=True)
    session_data = models.TextField(_('Session data'), editable=False)
    expire_date = models.DateTimeField(_('Expire date'), editable=False, db_index=True)
    last_activity = models.DateTimeField(_('Last activity'), editable=False, auto_now=True)

    objects = WebmailSessionManager()

    class Meta:
        abstract = True

    def __str__(self):
        return self.session_key

    def get_decoded(self):
        session_store_class = self.get_session_store_class()
        return session_store_class().decode(self.session_data)


class WebmailSession(WebmailSessionAbstractModel):
    @classmethod
    def get_session_store_class(cls):
        return SessionStoreBase

    class Meta:
        verbose_name = _('Webmail Session')
        verbose_name_plural = _('Webmail Sessions')
        ordering = ('-last_activity',)


class AccessLog(models.Model):
    user = models.ForeignKey(WebmailUser, on_delete=models.CASCADE, db_index=True, editable=False, related_name="access_logs")
    user_agent = models.TextField(_("User Agent"), null=True, editable=False)
    ip = models.GenericIPAddressField(_("IP Address"), null=True, editable=False)
    date = models.DateTimeField(_('Date Last login'), auto_now_add=True)

    class Meta:
        verbose_name = _('Access Log')
        verbose_name_plural = _('Access Logs')

        ordering = ('-date',)

    def __str__(self):
        return str(self.id)


def extract_ip(request):
    client_ip = request.META.get('REMOTE_ADDR')
    proxies = None
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for is not None:
        closest_proxy = client_ip
        forwarded_for_ips = [ip.strip() for ip in forwarded_for.split(',')]
        client_ip = forwarded_for_ips.pop(0)
        forwarded_for_ips.reverse()
        proxies = [closest_proxy] + forwarded_for_ips

    return (client_ip, proxies)


def register_access_log(sender, request, user, **kw):
    ip, _not_important = extract_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    AccessLog.objects.create(user=user, user_agent=user_agent, ip=ip)

user_logged_in_signal.connect(register_access_log, sender=WebmailUser)


class AnonymousUser:
    id = None
    pk = None
    username = ''
    is_active = False

    def __str__(self):
        return 'AnonymousUser'

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __hash__(self):
        return 1  # instances always return the same hash value

    def __int__(self):
        raise TypeError('Cannot cast AnonymousUser to int. Are you trying to use it in place of User?')

    def save(self):
        raise NotImplementedError("Django doesn't provide a DB representation for AnonymousUser.")

    def delete(self):
        raise NotImplementedError("Django doesn't provide a DB representation for AnonymousUser.")

    @property
    def is_anonymous(self):
        return True

    @property
    def is_authenticated(self):
        return False


class ContactUser(models.Model):
    user = models.ForeignKey(WebmailUser, on_delete=models.CASCADE, related_name="contacts")
    displayed_name = models.CharField(
        _('displayed name'),
        max_length=150,
        null=False,
        blank=False
    )
    email = models.EmailField(max_length=150)

    extra_data = models.JSONField(null=True, blank=True, editable=False)

    creation_date = models.DateTimeField(_('creation date'), auto_now_add=True)
    modification_date = models.DateTimeField(_('modification date'), auto_now=True)

    def __str__(self):
        return self.displayed_name

    class Meta:
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')

        ordering = ('displayed_name',)

        unique_together = ('user', 'email')


class ActiveMailboxManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            active=True,
        )


class Mailbox(models.Model):
    user = models.ForeignKey(WebmailUser, on_delete=models.CASCADE, related_name="mailboxes")

    name = models.CharField(
        _('Name'),
        max_length=255,
    )

    # my_email_list
    emails = CommaSeparatedEmailField(_("Email"), blank=True, null=True, help_text=_("Email/s related to the mailbox and used to associate them as mine")) 
    
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    active_mailboxes = ActiveMailboxManager()

    def set_as_default(self):
        with transaction.atomic():
            self.__class__.objects.filter(~Q(id=self.id), user=self.user).update(is_default=False)
            self.is_default=True
            self.save(update_fields=["is_default"])

    def get_absolute_url(self):
        url = reverse_url("mailbox_edit", kwargs={"mailbox_id": self.id})
        return url

    def process_incomming_email(self, email_message):
        """Process a message incoming to this mailbox."""

        inbound_email_received_signal.send(sender=Mailbox, email_message=email_message, mailbox=self)

        if is_spam(email_message):
            folder_id = Message.SPAM_FOLDER_ID
        else:
            folder_id = Message.INBOX_FOLDER_ID

        return self.import_email(email_message, folder_id=folder_id)

    def import_email(self, email_message, folder_id=None):
        if folder_id is None:
            folder_id = Message.INBOX_FOLDER_ID

        msg_record = Message.process_raw_email_message(mailbox=self, email_message=email_message, folder_id=folder_id, my_email_list=self.emails)

        return msg_record

    @property
    def is_smtp_server_configured(self):
        return SmtpServer.objects.filter(mailbox=self).exists()

    @property
    def is_pop3_mail_server_configured(self):
        return Pop3MailServer.objects.filter(mailbox=self).exists()

    @property
    def is_pop3_mail_server_active(self):
        try:
            return self.pop3_mail_server.active
        except Pop3MailServer.DoesNotExist:
            return False

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Mailbox')
        verbose_name_plural = _('Mailboxes')

        ordering = ('name',)
        unique_together = ('user', 'name')


class Pop3MailServer(models.Model):
    mailbox = models.OneToOneField(
        Mailbox,
        related_name='pop3_mail_server',
        verbose_name=_('Mailbox'),
        on_delete=models.CASCADE
    )
    # modificar esta parte para que se puedan poner dominios ????
    ip_address = models.GenericIPAddressField(('IP address'))
    port = models.PositiveIntegerField(_('Port'), default=25, help_text=_("(465 with SSL)"))

    username = models.CharField(_('Username'), max_length=75)
    password = models.CharField(_('Password'), null=True, blank=True, max_length=75)

    # size
    last_polling = models.DateTimeField(
        _("Last polling"),
        help_text=(_("The time of last successful polling for messages."
                     "It is blank for new mailboxes and is not set for "
                     "mailboxes that only receive messages via a pipe.")),
        blank=True,
        null=True,
        editable=False
    )

    use_ssl = models.BooleanField(_("Use SSL"), default=False)

    active = models.BooleanField(
        _('Active'),
        help_text=(_(
            "Check this e-mail inbox for new e-mail messages during polling "
            "cycles.  This checkbox does not have an effect upon whether "
            "mail is collected here when this mailbox receives mail from a "
            "pipe, and does not affect whether e-mail messages can be "
            "dispatched from this mailbox. "
        )),
        blank=True,
        default=True,
    )

    class Meta:
        verbose_name = _('Pop3 Mail Server')
        verbose_name_plural = _('Pop3 Mail Servers')
        db_table = "webmail_pop3mailserver"


    def get_connection(self):
        """Returns the transport instance for this mailbox."""

        conn = Pop3Transport(
                self.ip_address,
                port=self.port if self.port else None,
                ssl=self.use_ssl
            )
        conn.connect(self.username, self.password)
        
        return conn

    def get_new_mail(self, condition=None):
        """Connect to this transport and fetch new messages."""

        mailbox = self.mailbox

        new_mail = []
        connection = self.get_connection()
        if not connection:
            return
        for email_message in connection.get_message(condition):
            try:
                msg = mailbox.process_incomming_email(email_message)
            except InvalidEmailMessageException as e:
                yield e
            else:
                yield msg

        self.last_polling = timezone.now()
        self.save(update_fields=['last_polling'])

    def __str__(self):
        return '%s@%s:%s' % (self.username, self.ip_address, self.port)


class SmtpServer(models.Model):
    """
    All the needed information to connect to a SMTP server and send emails.
    """
    mailbox = models.OneToOneField(
        Mailbox,
        related_name='smtp_server',
        verbose_name=_('Mailbox'),
        on_delete=models.CASCADE
    )

    from_email = models.EmailField(
        _('From email'),
        help_text=(_(
            "Example: mailbot@yourdomain.com<br />"
            "'From' header to set for outgoing email.<br />"
            "<br />"
            "If you do not use this e-mail inbox for outgoing mail, this "
            "setting is unnecessary.<br />"
            "If you send e-mail without setting this, your 'From' header will'"
            "be set to match the setting `settings.WEBMAIL_DEFAULT_FROM_EMAIL`."
        )),
        blank=True,
        null=True,
        default=None,
    )
    from_name = models.CharField(_("From name"), null=True, blank=True, max_length=100)

    ip_address = models.GenericIPAddressField(('IP address'))
    port = models.PositiveIntegerField(_('Port'), default=25, help_text=_("(465 with SSL)"))

    username = models.CharField(_('Username'), max_length=75)
    password = models.CharField(_('Password'), null=True, blank=True, max_length=75)

    use_tls = models.BooleanField(_("Use TLS"), default=False)
    use_ssl = models.BooleanField(_("Use SSL"), default=False)

    def __str__(self):
        return '%s@%s:%s' % (self.username, self.ip_address, self.port)

    def get_from_email_header_value(self):
        if self.from_name:
            return "%s <%s>" % (self.from_name, self.from_email)
        else:
            return self.from_email

    def send_mail(self, recipient_list, multipart_mail_message):
        from_email = self.get_from_email_header_value() or settings.WEBMAIL_DEFAULT_FROM_EMAIL

        if self.use_ssl:
            smtp = smtplib.SMTP_SSL(
                keyfile = self.ssl_keyfile, certfile = self.ssl_certfile
            )
        else:
            smtp = smtplib.SMTP()

        smtp.connect(host = self.ip_address or "localhost", port=self.port)


        # TLS/SSL are mutually exclusive, so only attempt TLS over
        # non-secure connections.
        if not self.use_ssl and self.use_tls:
            smtp.ehlo()
            smtp.starttls(keyfile = self.ssl_keyfile, certfile = self.ssl_certfile)
            smtp.ehlo()

        # authenticate
        smtp.login(user = self.username, password = self.password)

        #
        # Send email
        #
        statusdict = smtp.sendmail(
            from_email,
            recipient_list,
            multipart_mail_message
        )

        try:
            smtp.quit()
        except (ssl.SSLError, smtplib.SMTPServerDisconnected):
            # This happens when calling quit() on a TLS connection
            # sometimes, or when the connection was already disconnected
            # by the server.
            smtp.close()
        
        return statusdict

    class Meta:
        verbose_name = _('SMTP Server')
        verbose_name_plural = _('SMTP Servers')
        db_table = "webmail_smtpserver"


class MessageTag(models.Model):
    name = models.CharField(verbose_name=_("Name"), unique=True, max_length=100)

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")


class UnknownFolderException(Exception):
    def __init__(self, folder_name):
        self.folder_name = folder_name


class FolderManager(models.Manager):
    folder_name = None

    def get_queryset(self):
        return super().get_queryset().filter(
            folder_id=self.model.FOLDER_ID_BY_NAME[self.folder_name]
        )

    def filter_unread(self):
        return super().filter(
            read_at__isnull=True
        )

    def filter_read(self):
        return super().filter(
            read_at__isnull=False
        )

    def filter_starred(self):
        return super().filter(
            is_starred=True
        )

    def filter_unstarred(self):
        return super().filter(
            is_starred=False
        )

    def filter_with_cc(self):
        return super().filter(
            cc__isnull=False
        )

    def filter_with_bcc(self):
        return super().filter(
            bcc__isnull=False
        )


class InboxFolderManager(FolderManager):
    folder_name = "inbox"

class SentFolderManager(FolderManager):
    folder_name = "sent"

class SpamFolderManager(FolderManager):
    folder_name = "spam"

class TrashFolderManager(FolderManager):
    folder_name = "trash"


class UnreadMessagesManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            read_at__isnull=True
        )

class ReadMessagesManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            read_at__isnull=False
        )

class StarredMessagesManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            is_starred=True
        )

class UnstarredMessagesManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            is_starred=False
        )


class Message(models.Model):
    INBOX_FOLDER_ID = 0
    SENT_FOLDER_ID = 1
    SPAM_FOLDER_ID = 2
    TRASH_FOLDER_ID = 3

    FOLDER_ID_BY_NAME = {
        "inbox": INBOX_FOLDER_ID,
        "sent": SENT_FOLDER_ID,
        "trash": TRASH_FOLDER_ID,
        "spam": SPAM_FOLDER_ID
    }

    FOLDER_CHOICES = ((INBOX_FOLDER_ID, _('Inbox')), (SENT_FOLDER_ID, _('Sent')), (SPAM_FOLDER_ID, _('Spam')), (TRASH_FOLDER_ID, _('Trash')))
    FOLDER_NAMES = ["inbox", "sent", "spam", "trash"]
    FOLDER_IDS = [INBOX_FOLDER_ID, SENT_FOLDER_ID, SPAM_FOLDER_ID, TRASH_FOLDER_ID]

    mailbox = models.ForeignKey(
        Mailbox,
        related_name='messages',
        verbose_name=_('Mailbox'),
        on_delete=models.CASCADE
    )

    folder_id = models.IntegerField(_("Folder"), default=None, choices=FOLDER_CHOICES, null=True, blank=True, db_index=True)

    subject = models.CharField(
        _('Subject'),
        max_length=1000
    )

    message_id = models.CharField(
        _('Message ID'),
        max_length=255
    )

    in_reply_to = models.ForeignKey(
        'webmail.Message',
        related_name='replies',
        blank=True,
        null=True,
        verbose_name=_('In reply to'),
        on_delete=models.CASCADE
    )

    original_email_headers = models.JSONField(_("Original email headers"), editable=False, null=True, blank=True)

    from_me = models.BooleanField(_("From me"), default=False)
    from_email = models.CharField(_("From"), max_length=254, validators=[validate_email_with_name])
    to = CommaSeparatedEmailField(_("To"), null=True, blank=True)
    cc = CommaSeparatedEmailField(_("Cc"), null=True, blank=True)
    bcc = CommaSeparatedEmailField(_("Bcc"), null=True, blank=True)

    to_me = models.BooleanField(_("To me"), default=False, db_index=True)
    to_me_email = models.EmailField(blank=True, null=True)

    is_starred = models.BooleanField(_("Starred"), default=False, db_index=True)

    text_plain = models.TextField(
        _('Text Plain'), blank=True, null=True
    )

    html = models.TextField(
        _('HTML'), blank=True, null=True
    )

    date = models.DateTimeField(
        _('Date'),
        auto_now_add=True
    )

    read_at = models.DateTimeField(
        _('Read at'),
        default=None,
        blank=True,
        null=True,
    )

    imported = models.BooleanField(
        _("Imported"),
        default=False)

    tags = models.ManyToManyField(MessageTag)

    objects = models.Manager()

    unread_messages = UnreadMessagesManager()
    read_messages = ReadMessagesManager()

    starred_messages = StarredMessagesManager()
    unstarred_messages = UnstarredMessagesManager()

    inbox_folder = InboxFolderManager()
    sent_folder = SentFolderManager()
    spam_folder = SpamFolderManager()
    trash_folder = TrashFolderManager()


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_email_message = None

    @classmethod
    def _get_email_content_decoded(cls, email_message):
        payload = email_message.get_payload(decode=True)

        charset = email_message.get_charset()
        if not charset:
            charset = 'ascii'

        try:
            # Make sure that the payload can be properly decoded in the
            # defined charset, if it can't, let's mash some things
            # inside the payload :-\
            content = payload.decode(charset)
        except LookupError:
            logger.warning(
                "Unknown encoding %s; interpreting as ASCII!",
                charset
            )
            content = payload.decode(
                'ascii',
                'ignore'
            )
        except ValueError:
            logger.warning(
                "Decoding error encountered; interpreting %s as ASCII!",
                charset
            )
            content = payload.decode(
                'ascii',
                'ignore'
            )

        return content

    @classmethod
    def _process_email_attachment(cls, attachment, msg_record, allowed_mimetypes=None):
#            ctype, encoding = mimetypes.guess_type(attachment.file_attachment.path)

#            if ctype is None or encoding is not None:
#                ctype = 'application/octet-stream'

        attachment_content_type = attachment.get_content_type()

        if allowed_mimetypes is not None and not attachment_content_type in allowed_mimetypes:
            return
        else:
            raw_filename = attachment.get_filename()

            if raw_filename is None:
                extension = mimetypes.guess_extension(attachment_content_type)

                if not extension:
                    extension = '.bin'

                file_name = "unknown" + extension
            else:
                file_name = utils.convert_header_to_unicode(raw_filename)

            record_attachment = MessageAttachment()
            record_attachment.file_name = file_name

            # TODO: Revisar esta parte
            record_attachment.file.save(
                uuid.uuid4().hex + extension,
                ContentFile(
                    BytesIO(
                        attachment.get_payload(decode=True)
                    ).getvalue()
                )
            )
            record_attachment.message = msg_record

#            headers = {}
#            for key, value in attachment.items():
#                headers[key] = value

#            record_attachment.headers = headers
            record_attachment.mimetype = attachment_content_type
            record_attachment.save()

    @staticmethod
    def validate_email_message(email_message):
        for header_name in ["From", "To", "Subject"]:
            if header_name not in email_message:
                raise InvalidEmailMessageException("This is header is mandatory: %s" % header_name, email_message)

    @classmethod
    def process_raw_email_message(cls, mailbox, email_message, folder_id=None, my_email_list=None):
        cls.validate_email_message(email_message)

        msg_record = cls()

        msg_record.mailbox = mailbox
        if 'Subject' in email_message:
            msg_record.subject = (
                utils.convert_header_to_unicode(email_message['Subject'])[0:255]
            )

        if 'Message-Id' in email_message:
            msg_record.message_id = email_message['Message-Id'][0:255].strip()

        if 'From' in email_message:
            from_header = utils.convert_header_to_unicode(email_message['From'])

            from_email = parseaddr(from_header)[1].lower()
            msg_record.from_email = from_email

            if my_email_list is not None:
                for my_email in my_email_list:
                    if my_email == from_email:
                        msg_record.from_me = True
                        break

        if 'To' in email_message:            
            to_header = utils.convert_header_to_unicode(email_message['To'])

            msg_record.to = parse_addresses_from_header(to_header)

            msg_record.to_me = False

            if my_email_list is not None:
                for my_email in my_email_list:
                    if my_email in msg_record.to:
                        msg_record.to_me = True
                        msg_record.to_me_email = my_email
                        break

        elif 'Delivered-To' in email_message:
            delivered_to_header = utils.convert_header_to_unicode(
                email_message['Delivered-To']
            )
            msg_record.to = parse_addresses_from_header(delivered_to_header)

        if 'CC' in email_message:            
            cc_header = utils.convert_header_to_unicode(
                email_message['CC']
            )
            msg_record.cc = parse_addresses_from_header(cc_header)

        if 'BCC' in email_message:            
            bcc = utils.convert_header_to_unicode(
                email_message['BCC']
            )
            msg_record.bcc = parse_addresses_from_header(bcc_header)

        plain_text_body = email_message.get_body(preferencelist=('plain'))
        html_body = email_message.get_body(preferencelist=('html'))

        if plain_text_body is not None:
            msg_record.text_plain = cls._get_email_content_decoded(plain_text_body)

        if html_body is not None:
            msg_record.html = cls._get_email_content_decoded(html_body)

        if email_message['In-Reply-To']:
            try:
                msg_record.in_reply_to = Message.objects.get(
                    message_id=email_message['In-Reply-To'].strip()
                )
            except Message.DoesNotExist:
                pass

        msg_record.folder_id = folder_id

        msg_record.original_email_headers = {
            k.capitalize(): str(email.header.make_header(email.header.decode_header(s)))
            for k,s in email_message.items()
        }
        msg_record.save()

        if email_message.is_multipart():
            if settings.WEBMAIL_STRIP_UNALLOWED_MIMETYPES and settings.WEBMAIL_ALLOWED_MIMETYPES is not None:
                allowed_mimetypes = settings.WEBMAIL_ALLOWED_MIMETYPES

            for attachment in email_message.iter_attachments():
                cls._process_email_attachment(attachment, msg_record, allowed_mimetypes=allowed_mimetypes)

        return msg_record

    @property
    def folder(self):
        return self.get_folder_name()

    def get_folder_name(self):
        if self.pk is None:
            return 

        return self.FOLDER_NAMES[self.folder_id]

    def move_to_folder_id(self, folder_name):
        try:
            folder_id = self.FOLDER_ID_BY_NAME[folder_name]
        except KeyError:
            raise UnknownFolderException(folder_name)

        self.folder_id = folder_id
        self.save(update_fields=["folder_id"])

    def user_action_delete(self):
        folder_id = self.folder_id

        if folder_id == self.TRASH_FOLDER_ID or folder_id == self.SPAM_FOLDER_ID:
            self.delete()
        else:
            self.folder_id = self.TRASH_FOLDER_ID
            self.save(update_fields=["folder_id"])

    def mark_as_read(self, date=None):
        if self.read_at is None:
            if date is None:
                date = timezone.now()
            self.read_at = date
            self.save(update_fields=["read_at"])

    def mark_as_unread(self):
        self.read_at = None
        self.save(update_fields=["read_at"])

    def mark_as_spam(self):
        self.folder_id = self.SPAM_FOLDER_ID
        self.save(update_fields=["folder_id"])

    def mark_as_not_junk(self):
        self.folder_id = self.INBOX_FOLDER_ID
        self.save(update_fields=["folder_id"])

    @property
    def body(self):
        return self.text_plain or self.html

    @property
    def is_read(self):
        return self.read_at is not None

    @property
    def is_junk(self):
        return self.folder_id == self.SPAM_FOLDER_ID or self.folder_id == self.TRASH_FOLDER_ID

    @property
    def is_good_received_mail(self):
        return self.folder_id == self.INBOX_FOLDER_ID

    @property
    def recipients(self):
        recipient_list = []

        if self.to:
            recipient_list.extend(self.to)

        if self.cc:
            recipient_list.extend(self.cc)

        if self.bcc:
            recipient_list.extend(self.bcc)

        return recipient_list

    def delete(self, *args, **kwargs):
        """Delete this message and all stored attachments."""
        for attachment in self.attachments.all():
            # This attachment is attached only to this message.
            attachment.delete()
        return super().delete(*args, **kwargs)

    def has_attachments(self):
        return self.attachments.count() > 0

    def get_text(self):
        text_plain = None

        if self.text_plain:
            text_plain = self.text_plain
        else:
            if self.html and html2text is not None:
                text_plain = html2text(self.html)

        return text_plain

    def get_excerpt(self):
        text = self.get_text()
        if text:
            # TODO
            return get_excerpt(text, max_chars=settings.WEBMAIL_EXCERPT_MAX_CHARS)

    @property
    def email_message(self):
        """
        Returns Django EmailMessage object for sending.
        """
        if self._cached_email_message:
            return self._cached_email_message
        else:
            msg = self.prepare_email_message()
            return msg

    # build_message
    def prepare_email_message(self):
        """
        Returns a django ``EmailMessage`` or django ``EmailMultiAlternatives`` object,
        depending on whether html is empty.
        """

#        mail = DjangoEmailMultiAlternatives(subject, message, self.from_email, recipient_list, connection=connection)
#        if html_message:
#            mail.attach_alternative(html_message, 'text/html')

        if self.html:
            if self.text_plain:
                text_plain = self.text_plain
            else:
                if html2text is not None:
                    text_plain = html2text(self.html)
                else:
                    text_plain = None

            if text_plain is not None:
                msg = DjangoEmailMultiAlternatives(
                    subject=self.subject, body=text_plain, from_email=self.from_email,
                    to=self.to, bcc=self.bcc, cc=self.cc,
                    connection=connection)
                msg.attach_alternative(self.html, "text/html")
            else:
                msg = DjangoEmailMessage(
                    subject=self.subject, body=self.html, from_email=self.from_email,
                    to=self.to, bcc=self.bcc, cc=self.cc)
                msg.content_subtype = 'html'

        else:
            msg = DjangoEmailMessage(
                subject=self.subject, body=self.text_plain, from_email=self.from_email,
                to=self.to, bcc=self.bcc, cc=self.cc)
                # TODO: Añadir parámetros de encriptación en keyword 'headers'

        # TODO: Comprobar como se lee un archivo
        for attachment in self.attachments.all():
            msg.attach(attachment.file_name, attachment.file.read(), mimetype=attachment.mimetype or None)
            attachment.file.close()

        if self.message_id:
            msg.extra_headers['Message-Id'] = self.message_id

        if self.in_reply_to and self.in_reply_to.message_id:
            msg.extra_headers['In-Reply-To'] = self.in_reply_to.message_id

        self._cached_email_message = msg

        return msg

    def make_msgid(self):
        data = ",".join(self.recipients) + self.subject + self.body
        uid = hashlib.md5(data.encode("utf-8")).hexdigest()

        i = 0
        while True:
            try:
                Message.objects.get(message_id=uid + str(i))
            except Message.DoesNotExists:
                uid = uid + str(i)

                break

            i += 1

        # uid = uuid.uuid4().hex
        return '<%s@%s>' % (uid, settings.WEBMAIL_DOMAIN_NAME_MESSAGE_ID)
        # See: email.utils.make_msgid

    def dispatch(self, priority=None):
        """
        Sends email and log the result.
        """
        if self.folder_id is not None:
            if self.folder_id == self.SENT_FOLDER_ID:
                logger.error(
                    "Message already processed: %s" % self.pk
                )
            else:
                logger.error(
                    "Message from different folder_id '%s': %s" % (self.get_folder_name(), self.pk)
                )
            return

        self.from_me = True
        self.folder_id = self.SENT_FOLDER_ID

        if self.id is None:
            self.save()
        else:
            update_fields = ["folder_id", "from_me"]
            if not self.message_id:
                self.message_id = self.make_msgid()
                update_fields.append("message_id")

            self.save(update_fields=update_fields)

        logger.info("Adding message to task queue.")

        SendMailTask.objects.create_from_message(message=self, priority=priority)


    def to_dict(self):
        message_dict = {'subject': self.subject,
                        'from_email': self.from_email,
                        "message_id": self.message_id,
                        "is_starred": self.is_starred,
                        "imported": self.imported,
                        'to': self.to,
                        'bcc': self.bcc,
                        'cc': self.cc}

        if self.read_at:
            message_dict["read_at"] = time.mktime(self.read_at.timetuple())

        if self.to_me:
            self.message_dict["to_me"] = self.to_me_email

        if self.in_reply_to:
            message_dict["reply_to"] = self.in_reply_to.id

        if self.html:
            message_dict["html"] = self.html

        text = self.get_text()
        if text:
            message_dict["text_plain"] = text

        message_attachment_ids =[attachment.id for attachment in self.attachments.all()]

        if message_attachment_ids:
            message_dict["attachment_ids"] = message_attachment_ids

        return message_dict

    @classmethod
    def from_dict(cls, messagedict):
        # TODO
        msg = cls()

        attachments = message_kwargs.pop('attachments')
        message_kwargs['attachments'] = []
        for attachment in attachments:
            filename, contents, mimetype = attachment
            contents = base64.b64decode(contents.encode('ascii'))

            # For a mimetype starting with text/, content is expected to be a string.
            if mimetype and mimetype.startswith('text/'):
                contents = contents.decode()

            message_kwargs['attachments'].append((filename, contents, mimetype))

        return message

    def __str__(self):
        txt = str(self.id)
        if self.subject:
            txt += " - " + self.subject

        return txt

    class Meta:
        ordering = ('-date',)
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')


def get_attachment_save_path(instance, filename):
    attachment_template_path = os.path.join(
        settings.WEBMAIL_ATTACHMENT_UPLOAD_TO,
        uuid.uuid4().hex,
    )

    attachment_path = datetime.datetime.utcnow().strftime(attachment_template_path)
    return attachment_path

#    @classmethod
#    def _save_original_email(cls, email_message, msg):
#        if settings.WEBMAIL_COMPRESS_ORIGINAL_MESSAGE:
#            with NamedTemporaryFile(suffix=".eml.gz") as fp_tmp:
#                with gzip.GzipFile(fileobj=fp_tmp, mode="w") as fp:
#                    fp.write(email_message.as_string().encode('utf-8'))
#                msg_record.eml.save(
#                    "{}.eml.gz".format(uuid.uuid4()),
#                    File(fp_tmp),
#                    save=False
#                )

#        else:
#            msg_record.eml.save(
#                '%s.eml' % uuid.uuid4(),
#                ContentFile(email_message.as_string()),
#                save=False
#            )

class MessageAttachment(models.Model):
    message = models.ForeignKey(
        Message,
        related_name='attachments',
        null=False,
        blank=False,
        verbose_name=_('Message'),
        on_delete=models.CASCADE
    )

    file_name = models.TextField(_('File name'), help_text=_("The original filename"))
    mimetype = models.CharField(max_length=255, default='', blank=True)

    file = models.FileField(
        _('File'),
        upload_to=get_attachment_save_path,
    )

    def delete(self, *args, **kwargs):
        """Deletes the attachment."""
        self.file.delete()
        return super().delete(*args, **kwargs)

#    def __str__(self):
#        return self.file.url

    def __str__(self):
        return '[%s] %s' % (self.id, self.file_name)

    class Meta:
        verbose_name = _('Message Attachment')
        verbose_name_plural = _('Message Attachments')


class UploadAttachmentSession(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid1, editable=False, db_column='uuid')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    message_obj_reference = models.OneToOneField(
        Message,
        related_name='upload_session',
        null=True,
        blank=True,
        verbose_name=_('message'),
        on_delete=models.CASCADE
    )

    def delete(self, *args, **kwargs):
        """Delete this compose session and all upload files associated."""
        if self.message_obj_reference.folder_id is None:
            self.message_obj_reference.delete()

        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = _('Upload Attachment Session')
        verbose_name_plural = _('Upload Attachment Sessions')


#def compose_upload_to(instance, filename):
#    file_path = os.path.join(settings.ATTACHMENT_TEMP_DIR, str(instance.compose_session.id), uuid.uuid1())
#    return file_path

#class ComposeUploadedFile(models.Model):
#    compose_session = models.ForeignKey(ComposeModel, on_delete=models.CASCADE, related_name="uploads", db_column='compose_session')
#    file_name = models.TextField()
#    file = models.FileField(
#        _('File'), db_column='file', upload_to=compose_upload_to
#    )
#    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')

#    def delete(self, *args, **kwargs):
#        """Deletes the attachment."""
#        self.file.delete()
#        return super().delete(*args, **kwargs)


class SendMailTaskManager(models.Manager):
    def create_from_message(self, message, priority=None):
        multipart_mail_message = message.email_message.message().as_bytes(linesep='\r\n')

        if priority is None:
            priority = SendMailTask.PRIORITY_MEDIUM

        return super().create(
            mailbox=message.mailbox,
            email_recipients=message.recipients,
            multipart_mail_message = multipart_mail_message,
            priority=priority)

    def high_priority(self):
        """
        the high priority messages in the queue
        """
        return self.filter(priority=SendMailTask.PRIORITY_HIGH)

    def medium_priority(self):
        """
        the medium priority messages in the queue
        """
        return self.filter(priority=SendMailTask.PRIORITY_MEDIUM)

    def low_priority(self):
        """
        the low priority messages in the queue
        """
        return self.filter(priority=SendMailTask.PRIORITY_LOW)

    def non_deferred(self):
        """
        the messages in the queue not deferred
        """
        return self.filter(
                    status=SendMailTask.STATUS_QUEUED) \
                .filter(
                    Q(scheduled_time__lte=timezone.now()) | Q(scheduled_time=None))

    def deferred(self):
        """
        the deferred messages in the queue
        """
        return self.filter(
                    status=SendMailTask.STATUS_QUEUED) \
                .filter(
                    scheduled_time__isnull=False, scheduled_time__gt=timezone.now())

    def purge_old_entries(self, days):
        last_sent_date_limit = timezone.now() - datetime.timedelta(days=days)
        query = self.filter(
            Q(last_sent_at__lt=last_sent_date_limit) | Q(status=SendMailTask.STATUS_CANCELLED)
        ).exclude(status__in=[SendMailTask.STATUS_QUEUED, SendMailTask.STATUS_IN_PROGRESS])

        count = query.count()
        query.delete()
        return count


# OutboundMessageQueueModel, SendMailQueueModel, MailQueueModel, SendMailModel
class SendMailTask(models.Model):
    PRIORITY_HIGH = 1
    PRIORITY_MEDIUM = 2
    PRIORITY_LOW = 3

    PRIORITY_CHOICES = [
        (PRIORITY_HIGH, _("High")),
        (PRIORITY_MEDIUM, _("Medium")),
        (PRIORITY_LOW, _("Low")),
    ]

    STATUS_QUEUED = 0
    STATUS_IN_PROGRESS = 1
    # STATUS_SENT, STATUS_SENT_SUCCESSFULLY, STATUS_SUCCESS
    STATUS_COMPLETED = 2
    STATUS_FAILED = 3
    STATUS_CANCELLED = 4

    STATUS_CHOICES = [
        (STATUS_QUEUED, _("Queued")),
        (STATUS_IN_PROGRESS, _("In progress")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_FAILED, _("Failed")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]
    mailbox = models.ForeignKey(Mailbox, on_delete=models.CASCADE, related_name="send_tasks")
    email_recipients = CommaSeparatedEmailField()

    # message_data, encoded_mimeparts, serialized_email
    multipart_mail_message = models.BinaryField()

    # when_added
    created_at = models.DateTimeField(auto_now_add=True)

    priority = models.PositiveSmallIntegerField(_("Priority"), choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM, db_index=True)

    # Emails with 'queued' status will get processed by ``sendmail`` command.
    # Status field will then be set to ``in progess`` when started being processed, and when it's already processed ``failed`` or ``completed`` depending on whether it's successfully delivered.
    status = models.PositiveSmallIntegerField(
        _("Status"),
        choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    # num_retries
    num_deferred_times = models.PositiveSmallIntegerField(_("Number of times deferred"), default=0, db_index=True)
    # deferred_at
    scheduled_time = models.DateTimeField(_('The scheduled sending time'),
                                          blank=True, null=True, db_index=True)

    last_sent_at = models.DateTimeField(blank=True, null=True)
    last_sent_succeed = models.BooleanField(blank=True, null=True, db_index=True)

    objects = SendMailTaskManager()

    class Meta:
        verbose_name = _("Send Mail Task")
        verbose_name_plural = _("Send Email Task Queue")

    def is_done(self):
        return self.status in (self.STATUS_COMPLETED, self.STATUS_FAILED, self.STATUS_CANCELLED) 

    def is_in_progress(self):
        return self.status == self.STATUS_IN_PROGRESS

    def set_status_queued(self):
        self.status = self.STATUS_QUEUED
        self.scheduled_time = None

        self.save(update_fields=("status", "scheduled_time"))

    def set_status_in_progress(self):
        self.status = self.STATUS_IN_PROGRESS
        self.scheduled_time = None

        self.save(update_fields=("status", "scheduled_time"))

    def set_status_completed(self):
        self.status = self.STATUS_COMPLETED
        self.scheduled_time = None

        self.save(update_fields=("status", "scheduled_time"))

    def set_status_failed(self):
        self.status = self.STATUS_FAILED
        self.scheduled_time = None

        self.save(update_fields=("status", "scheduled_time"))

    def set_status_cancelled(self):
        self.status = self.STATUS_CANCELLED
        self.scheduled_time = None

        self.save(update_fields=("status", "scheduled_time"))

    def defer(self, **kw):
        self.status = self.STATUS_QUEUED
        self.scheduled_time = timezone.now() + datetime.timedelta(**kw)
        self.num_deferred_times += 1
        self.save(update_fields=("status", "num_deferred_times", "scheduled_time",))

    def __str__(self):
        return str(self.id)

    def _get_email_message(self):
        return message_from_string(self.multipart_mail_message)

    def _set_email_message(self, email_message):
        self.multipart_mail_message = email_message.as_bytes(linesep='\r\n')

    email_message = property(
        _get_email_message,
        _set_email_message,
        doc="""EmailMessage object. If this is mutated, you will need to
set the attribute again to cause the underlying serialised data to be updated.""")

    @property
    def to_addresses(self):
        email_message = self.email_message
        if email_message is not None:
            return email_message.to
        else:
            return []

    @property
    def subject(self):
        email_message = self.email_message
        if email_message is not None:
            return email_message.subject
        else:
            return ""

    def send(self, notify_failure=False, max_retries=settings.WEBMAIL_MAX_RETRIES_SEND_MAIL, wait_time_next_retry=settings.WEBMAIL_WAIT_TIME_NEXT_RETRY_SEND_MAIL):
        try:
            smtp_server = self.mailbox.smtp_server
        except SmtpServer.DoesNotExist:
            logger.error("No smtp server configured for mailbox %d" % self.mailbox.id)

            # TODO: Give detailed instructions how to configure SMTP server
            Message.objects.create(mailbox=self.mailbox, folder_id=Message.INBOX_FOLDER_ID, from_email=settings.WEBMAIL_EMAIL_FOR_ERROR_NOTIFICATION, to=self.email_recipients, subject=_("No SMTP mail server configured!"), text_plain=_("The message has not been sent because no SMTP server configured. Try again after configuring a SMTP server for this mailbox."))

            raise NoSmtpServerConfiguredException()

        logger.info("Starting sending mail task #%s..." % self.id)

        multipart_mail_message = self.multipart_mail_message

        logger.info("Sending email to %s" % ", ".join(self.email_recipients))
        batch = SendMailTaskBatch.objects.create(task=self, num_batch=self.num_deferred_times)

        recipients_with_errors = None

        try:
            recipients_with_errors = smtp_server.send_mail(self.email_recipients, multipart_mail_message)
        #except (OSError, smtplib.SMTPException) as e:
        except Exception as e:
            # TODO: Check OSError: [Errno 101] Network is unreachable. e.errno == 101

            last_sent_succeed = False

            if isinstance(e, smtplib.SMTPRecipientsRefused):
                recipients_with_errors = e.recipients

            exception_message = str(e)
            exception_type = type(e).__name__

            py_traceback = '\n'.join(traceback.format_exception(*sys.exc_info()))

            logger.warning("Exception sending message task '%s'. Exception type: %s. Exception message: %s. Traceback:\n%s" % (self.pk, exception_type, exception_message, py_traceback))

            SendMailTaskExceptionLog.objects.create(
                task_batch=batch,
                exception_type=exception_type,
                exception_message=exception_message,
                py_traceback=py_traceback
            )
        else:
            last_sent_succeed = True

        self.last_sent_at = timezone.now()
        self.last_sent_succeed = last_sent_succeed
        self.save(update_fields=["last_sent_at", "last_sent_succeed"])

        if recipients_with_errors is not None and len(recipients_with_errors) != 0:
            for error_recipient_email, error_status in recipients_with_errors.items():
                code, response = error_status
                SendMailTaskErrorRecipient.objects.create(task_batch=batch, recipient=error_recipient_email, code=code, response=response)

            if len(recipients_with_errors) == len(self.email_recipients):
                if notify_failure:
                    body = _("Error sending mail!")
                else:
                    body = None       
            else:
                body = _("Error sending mail to some recipients!")

            if body is not None:
                recipient_errors_text = get_text_list(recipient_errors, last_word=_("and"))

                Message.objects.create(mailbox=self.mailbox, folder_id=Message.INBOX_FOLDER_ID, from_email=settings.WEBMAIL_EMAIL_FOR_ERROR_NOTIFICATION, to=recipient_errors, subject=_("Error email delivery to {recipients}").format(recipients=recipient_errors_text), text_plain=body)

        return last_sent_succeed


class SendMailTaskBatch(models.Model):
    # last_attempt_at
    task = models.ForeignKey(SendMailTask, db_index=True, on_delete=models.CASCADE, related_name="task_batch_list")
    num_batch = models.PositiveIntegerField(_('Num. Batch'))
    processed_at = models.DateTimeField(_('Processed At'), default=timezone.now)

    class Meta:
        verbose_name = _("Send Mail Task Batch")
        verbose_name_plural = _("Send Mail Task Batches")

        unique_together = ('task', 'num_batch')

        ordering = ('processed_at',)

    def __str__(self):
        return _("Task #%d batch #%d") % (self.task.id, self.num_batch)


class SendMailTaskExceptionLog(models.Model):
    # fields from Message

    task_batch = models.OneToOneField(SendMailTaskBatch, db_index=True, on_delete=models.CASCADE, related_name="exception_log")
    #exception_type = models.CharField(_('Exception type'), max_length=255, blank=True, null=True)

    # additional logging fields when_attempted attempted_at

    exception_type = models.CharField(_("Exception Type"), max_length=255, db_index=True)
    exception_message = models.TextField(_("Exception Message"))
    py_traceback = models.TextField(_("Python Traceback"))

    class Meta:
        verbose_name = _("Mail Sent Error Log")
        verbose_name_plural = _("Mail Sent Error Logs")

    def __str__(self):
        return _("Error sending emails for task batch #%d") % self.task_batch.id


class SendMailTaskErrorRecipient(models.Model):
    task_batch = models.ForeignKey(SendMailTaskBatch, db_index=True, on_delete=models.CASCADE, related_name="error_recipients")
    recipient = models.EmailField(_("Recipient Email"), db_index=True)
    code = models.PositiveIntegerField(_('Code'))
    response = models.TextField(_('SMTP Response'))

    class Meta:
        verbose_name = _("Mail Sent Error Recipient")
        verbose_name_plural = _("Mail Sent Error Recipients")


#class Blob(models.Model):
#    uuid = models.UUIDField(primary_key=True)
#    encrypted_key = models.TextField(help_text=_("Encrypted key in base64"))
#    owner = models.ForeignKey(WebmailUser, db_index=True)
#    data = models.BinaryField()

#    class Meta:
#        verbose_name = _("Blob")
#        verbose_name_plural = _("Blobs")

#    def __str__(self):
#        return self.uuid.hex


#class InvertedIndexBlob(models.Model):
#    owner = models.OneToOneField(WebmailUser, db_index=True)
#    encrypted_key = models.TextField(help_text=_("Encrypted key in base64"))
#    encrypted_term_name = models.TextField(help_text=_("Encrypted term name in base64"))
#    blobs = models.ManyToManyField(Blob)

#    class Meta:
#        verbose_name = _("Blob metadata")
#        verbose_name_plural = _("Blob metadatas")

#    def __str__(self):
#        return self.owner.username

# InvertedIndexBlob stores an inverted index of the emails. The terms are encrypted and are prefixed with the field name. Example: title:term1, body:term2, to:term3. 
# Relationships between blobs are stored inside the data of the blob
# Blob types:
# - Email header
#   - To
#   - CC
#   - BCC
#   - Subject
#   - Date
#   - Has attachments
#   - Body blob Id
# - Email body
#   - text
#   - list of attachments:
#       - name: 
#           - file path
#           - hash
#           - encrypted key

# Attachments are stored encrypted in the file system. They are hashed and then organized in different level of subdirectories accoding to the first characters of the hash. Each subgruoup of characters is a folder name.

# TODO: Convert the application to SPA. This is necessary because many tasks are processed in the frontend in the background. Example.
# - Updating the blob metadata when there is new email, or one email is deleted or a new email is sent

# TODO: To use custom encryption protocol for P2P communication based in Signal protocol (There is no X3DH protocol. A shared key is sent directly in the header of the email encrypted and also the public key and also another parameter to start Diff-heffman algorithm for the rachet protocol). GPG is only used for signing emails.

# TODO: Safe delete
# TODO. Autodelete feature

# TODO: Implent polling using POP3 TLS-SRP authentication
# TODO: asyncio POP3 and SMTP server with TLS-SRP authentication support. Provide web enpoints for checking the time and date of logged sessions, failed logins and retrieved messages
