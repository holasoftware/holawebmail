import datetime
import email.header
import os
import re
import uuid
from email.utils import parseaddr, formataddr


from django.utils.text import wrap
from django.utils.translation import gettext, gettext_lazy as _


from .logutils import get_logger
from . import settings


logger = get_logger()


def convert_header_to_unicode(header):
    default_charset = settings.WEBMAIL_DEFAULT_CHARSET

    def _decode(value, encoding):
        if isinstance(value, str):
            return value
        if not encoding or encoding == 'unknown-8bit':
            encoding = default_charset
        return value.decode(encoding, 'replace')

    try:
        return ''.join(
            [
                (
                    _decode(bytestr, encoding)
                ) for bytestr, encoding in email.header.decode_header(header)
            ]
        )
    except UnicodeDecodeError:
        logger.exception(
            'Errors encountered decoding header %s into encoding %s.',
            header,
            default_charset,
        )
        return header.decode(default_charset, 'replace')



# favour django-mailer but fall back to django.core.mail

def sanitize_address(address):
    if not isinstance(address, tuple):
        address = parseaddr(address)
    name, email = address
    return formataddr((name, email))


def sanitize_address_list(addresses):
    return [sanitize_address(address) for address in addresses]


def join_address_list(addresses):
    return ', '.join(sanitize_address_list(addresses))


def format_body_reply(sender_name, sender_address, body):
    """
    Wraps text at 90 chars and prepends each
    line with `> `.
    Used for quoting messages in replies.
    """

    if sender_name is None:
        sender_text = sender_address
    else:
        sender_text = sender_name + " " + "[" + sender_address + "]"

    lines = wrap(body, 90).split('\n')
    for i, line in enumerate(lines):
        lines[i] = "> %s" % line
    quote = '\n'.join(lines)
    return gettext(u"%(sender_text)s wrote:\n%(body)s") % {
        'sender_text': sender_text,
        'body': quote
    }

def format_subject(subject):
    """
    Prepends 'Re:' to the subject. To avoid multiple 'Re:'s
    a counter is added.
    NOTE: Currently unused. First step to fix Issue #48.
    FIXME: Any hints how to make this i18n aware are very welcome.

    """
    subject_prefix_re = r'^Re\[(\d*)\]:\ '
    m = re.match(subject_prefix_re, subject, re.U)
    prefix = u""
    if subject.startswith('Re: '):
        prefix = u"[2]"
        subject = subject[4:]
    elif m is not None:
        try:
            num = int(m.group(1))
            prefix = u"[%d]" % (num+1)
            subject = subject[6+len(str(num)):]
        except:
            # if anything fails here, fall back to the old mechanism
            pass

    return gettext(u"Re%(prefix)s: %(subject)s") % {
        'subject': subject,
        'prefix': prefix
    }


def decode_payload(encoding, payload):
    """Decode the payload according to the given encoding

    Supported encodings: base64, quoted-printable.

    :param encoding: the encoding's name
    :param payload: the value to decode
    :return: a string
    """
    encoding = encoding.lower()
    if encoding == "base64":
        import base64
        return base64.b64decode(payload)
    elif encoding == "quoted-printable":
        import quopri
        return quopri.decodestring(payload)
    return payload

