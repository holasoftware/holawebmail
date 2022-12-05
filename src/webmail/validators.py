import re

from email.utils import getaddresses

from django.utils.encoding import force_text
from django.core.validators import validate_email, RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# WHATWG HTML5 spec, section 4.10.5.1.5.
#HTML5_EMAIL_RE = (
#    r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]"
#    r"+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}"
#    r"[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]"
#    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
#)
#def validate_email(s):
#    # from http://www.wellho.net/resources/ex.php4?item=y115/relib.py
#    return re.match(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)", s, re.IGNORECASE)


def validate_email_list(value):
    """
    Validate every email address in a comma separated list of emails.
    """

    if isinstance(value, (tuple, list)):
        addresses = [(None, email_address) if isinstance(email_address, str) else email_address for email_address in value]
    else:
        value = force_text(value)
        addresses = getaddresses([value])

    for name, email in addresses:
        if email == "":
            raise ValidationError(_("Address name '{name}' without email.").format(name=name), code='invalid')
        else:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError(_("Invalid email address <b>{email}</b>.").format(email=email), code='invalid')


def validate_email_with_name(value):
    """
    Validate email address.

    Both "Recipient Name <email@example.com>" and "email@example.com" are valid.
    """
    value = force_text(value)

    recipient = value
    if '<' and '>' in value:
        start = value.find('<') + 1
        end = value.find('>')
        if start < end:
            recipient = value[start:end]

    validate_email(recipient)


hexdigits_validator = RegexValidator(
    r"^[0-9a-f]+$",
    flags=re.IGNORECASE,
    message=_(
        _("Value must be a hexadecimal number.")
    ),
)

username_validator = RegexValidator(
    r'^[a-zA-Z0-9]+$',
    flags = re.ASCII,
    message=_(
        _('Enter a valid username. This value may contain only English letters and numbers.')
    ),
)
