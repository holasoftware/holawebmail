import copy
import json
import warnings


from django.db import models
from django import forms
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.serializers.json import DjangoJSONEncoder


from .validators import validate_email_list
from .widgets import CommaSeparatedEmailWidget


class JSONString(str):
    pass


def checked_loads(value, **kwargs):
    """
    Ensure that values aren't loaded twice, resulting in an encoding error.

    Loaded strings are wrapped in JSONString, as it is otherwise not possible
    to differentiate between a loaded and unloaded string.
    """
    if isinstance(value, (list, dict, int, float, JSONString, type(None))):
        return value

    value = json.loads(value, **kwargs)
    if isinstance(value, str):
        value = JSONString(value)

    return value


class JSONField(models.TextField):
    """JSONField is a generic textfield that serializes/deserializes JSON objects"""

    def __init__(self, *args, dump_kwargs=None, load_kwargs=None, **kwargs):
        self.dump_kwargs = dump_kwargs
        self.load_kwargs = load_kwargs

        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

        if self.dump_kwargs is not None:
            kwargs['dump_kwargs'] = self.dump_kwargs

        if self.load_kwargs is not None:
            kwargs['load_kwargs'] = self.load_kwargs

        return name, path, args, kwargs

    def to_python(self, value):
        try:
            return checked_loads(value, **(self.load_kwargs or {}))
        except ValueError:
            raise ValidationError(_("Enter valid JSON."))

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None

        try:
            return checked_loads(value, **(self.load_kwargs or {}))
        except json.JSONDecodeError:
            warnings.warn('{0!s} failed to load invalid json ({1}) from the database. The value has been returned as a string instead.'.format(self, value), RuntimeWarning)
            return JSONString(value)

    def get_prep_value(self, value):
        """Convert JSON object to a string"""
        if self.null and value is None:
            return None

        dump_kwargs = self.dump_kwargs or {}
        if 'cls' not in dump_kwargs:
            dump_kwargs["cls"] = DjangoJSONEncoder

        return json.dumps(value, **dump_kwargs)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)

        dump_kwargs = self.dump_kwargs or {}
        if 'cls' not in dump_kwargs:
            dump_kwargs["cls"] = DjangoJSONEncoder

        return json.dumps(value, **dump_kwargs)

    def get_default(self):
        """
        Returns the default value for this field.

        The default implementation on models.Field calls force_unicode
        on the default, which means you can't set arbitrary Python
        objects as the default. To fix this, we just return the value
        without calling force_unicode on it. Note that if you set a
        callable as a default, the field will still call it. It will
        *not* try to pickle and encode it.
        """
        if self.has_default():
            if callable(self.default):
                return self.default()
            return copy.deepcopy(self.default)
        # If the field doesn't have a default, then we punt to models.Field.
        return super().get_default()


class CommaSeparatedValueList(list):
    COMMA_SEPARATOR = ", "

    def __init__(self, value=None):
        if value is None:
            super().__init__()
        else:
            if isinstance(value, str):
                value = value.split(self.COMMA_SEPARATOR)

            super().__init__(value)

    def __str__(self):
        return self.COMMA_SEPARATOR.join(self)


class CommaSeparatedEmailFormField(forms.Field):
    widget = CommaSeparatedEmailWidget

    def to_python(self, value):
        "Normalize data to a list of strings."
        # Return None if no input was given.
        if not value:
            return CommaSeparatedValueList()
        return CommaSeparatedValueList([v.strip() for v in value.split(',')])

    def validate(self, value):
        "Check if value consists only of valid emails."

        # Use the parent's handling of required fields, etc.
        super().validate(value)

        validate_email_list(value)


class CommaSeparatedEmailField(models.Field):
    default_validators = [validate_email_list]
    description = _("Comma-separated emails")

    def formfield(self, **kwargs):
        defaults = {
            'form_class': CommaSeparatedEmailFormField,
            'error_messages': {
                'invalid': _('Only comma separated emails are allowed.'),
            }
        }

        defaults.update(kwargs)
        return super().formfield(**defaults)

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def get_prep_value(self, value):
        """
        We need to accomodate queries where a single email,
        or list of email addresses is supplied as arguments. For example:

        - Email.objects.filter(to='mail@example.com')
        - Email.objects.filter(to=['one@example.com', 'two@example.com'])
        """
        if value is None:
            return None

        if isinstance(value, str):
            if value == "":
                return None
            else:
                return value
        else:
            return ','.join(map(lambda s: s.strip(), value))

    def to_python(self, value):
        if isinstance(value, str):
            if value.strip() == '':
                return CommaSeparatedValueList()
            else:
                return CommaSeparatedValueList([s.strip() for s in value.split(',')])
        elif isinstance(value, CommaSeparatedValueList) or value is None:
            return value
        else:
            return CommaSeparatedValueList(value)

    def get_internal_type(self):
        return "TextField"

