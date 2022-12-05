from django.forms.widgets import Textarea
from django.core.exceptions import ValidationError
from django.core import validators
from django.utils.translation import ugettext_lazy as _


MULTI_EMAIL_FIELD_EMPTY_VALUES = validators.EMPTY_VALUES + ('[]', )

# Considerar usar esto:
# https://github.com/mrhieu/jQuery-Tags-Input-with-Validation

class CommaSeparatedEmailWidget(Textarea):

    is_hidden = False

    def prep_value(self, value):
        """Prepare value before effectively render widget"""
        if value in MULTI_EMAIL_FIELD_EMPTY_VALUES:
            return ""
        elif isinstance(value, str):
            return value
        elif isinstance(value, list):
            return ", ".join(value)
        raise ValidationError(_('Invalid format.'))

    def render(self, name, value, attrs=None, renderer=None):
        value = self.prep_value(value)
        return super().render(name, value, attrs, renderer=renderer)
