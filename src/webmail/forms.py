import re


from django import forms
from django.forms.widgets import HiddenInput, TextInput
from django.forms.models import ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core import validators


from .models import Mailbox, SmtpServer, Pop3MailServer, Message, ContactUser, WebmailUser
from .fields import CommaSeparatedEmailFormField
from .signals import message_flagged_as_spam_signal, message_flagged_as_not_spam_signal


class MultipleValueInput:
    def value_from_datadict(self, data, files, name):
        return data.getlist(name)


class ExtraFormsMixin:
    def __init__(self, data=None, **kwargs):

        self.extra_forms = []

        extra_form_classes = kwargs.pop("extra_form_classes", None)

        if extra_form_classes:
            for extra_form_class in extra_form_classes:
                extra_form = extra_form_class(data, initial=kwargs.get("initial",None), parent_form=self)
                self.extra_forms.append(extra_form)

        super().__init__(data, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        if self.extra_forms:
            for form in self.extra_forms:
                form.full_clean()
                self._errors.update(form._errors)

                cleaned_data.update(form.cleaned_data)

        return cleaned_data


class ChildForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.parent_form = kwargs.pop("parent_form")

        super().__init__(*args, **kwargs)


#from django.utils.text import camel_case_to_spaces
#
#class AdminModelAction(forms.Form):
#    _ids = forms.CharField(label='object ids')

#    class Meta:
#        pass

#    @classmethod
#    def init_meta(cls):
#        name = camel_case_to_spaces(cls.__name__).replace(' ', '_')
#        verbose_name = getattr(cls.Meta, 'verbose_name', name)
#        cls._meta = cls.Meta
#        cls._meta.name = name
#        cls._meta.verbose_name = verbose_name

#    def clean__ids(self):
#        return self.cleaned_data['_ids'].split(',')

#    def get_fields(self):
#        fields = self.fields.copy()
#        del fields['_ids']
#        return fields

#    def filer_queryset(self, queryset):
#        return queryset.filter(pk__in=self.cleaned_data['_ids'])

#    def save(self, queryset):
#        raise NotImplementedError

class ActionForm(forms.Form):
    model = None
    action_name = forms.CharField(widget=HiddenInput)
    # _ids, obj_id
    obj_list = forms.Field(widget=MultipleValueInput, required=False)

    def __init__(self, **kwargs):
        if "queryset" in kwargs:
            queryset = kwargs.pop("queryset")
        else:
            queryset = self.model.objects.filter(**self.get_query_params(kwargs))

        self.queryset = queryset

        super().__init__(**kwargs)

    def get_query_params(self, kwargs):
        raise NotImplementedError

    def clean_obj_list(self):
        value = self.cleaned_data.get("obj_list", None)
        if len(value) == 0: return

        # value = frozenset(value)

        for pk in value:
            try:
                self.queryset.filter(pk=pk)
            except (ValueError, TypeError):
                raise forms.ValidationError("Object id is not of correct type: %s" % val)

#        qs = self.queryset.filter(pk__in=value)
#        pks = {str(o.pk) for o in qs}
#        for val in value:
#            if val not in pks:
#                raise forms.ValidationError("Object id doesn't belong to provided query set: %s" % val)
#        return qs

        return value

    def get_obj_list_length(self):
        return len(self.cleaned_data["obj_list"])

    def filter_queryset(self):
        return self.queryset.filter(pk__in=self.cleaned_data['obj_list'])

    def clean_action_name(self):
        action_name = self.cleaned_data["action_name"]

        if not hasattr(self, "action_" + action_name):
            raise forms.ValidationError(_("Invalid action name: %s") % action_name)

        return action_name

    def apply_action(self):
        obj_list = self.cleaned_data["obj_list"]

        if obj_list is not None:
            action_name = self.cleaned_data["action_name"]
            action_func = getattr(self, "action_" + action_name)

            for obj in self.filter_queryset():
                action_func(obj)


class ActionDeleteMixin:
    def action_delete(self, obj):
        obj.delete()


class MailboxActionForm(ActionDeleteMixin, ActionForm):
    model = Mailbox

    def get_query_params(self, kwargs):
        user = kwargs.pop("user")
        return {
            "user": user
        }


class ContactActionForm(ActionDeleteMixin, ActionForm):
    model = ContactUser

    def get_query_params(self, kwargs):
        user = kwargs.pop("user")
        return {
            "user": user
        }


class MailActionForm(ActionForm):
    model = Message

    def get_query_params(self, kwargs):
        folder_name = kwargs.pop("folder_name")
        folder_id = Message.FOLDER_ID_BY_NAME[folder_name]

        mailbox = kwargs.pop("mailbox")

        return {
            "mailbox": mailbox,
            "folder_id": folder_id
        }

    def action_unstar(self, message):
        message.is_starred = False
        message.save()

    def action_star(self, message):
        message.is_starred = True
        message.save()

    def action_mark_as_read(self, message):
        message.mark_as_read()

    def action_mark_as_unread(self, message):
        message.mark_as_unread()

    def action_delete_permanently(self, message):
        message.delete()

    def action_delete(self, message):
        message.user_action_delete()

    def action_spam(self, message):
        message_flagged_as_spam_signal.send(sender=Message, message=message)
        message.mark_as_spam()

    def action_mark_as_not_junk(self, message):
        """Mark a message as not junk."""
        if message.folder_id == Message.SPAM_FOLDER_ID:
            message_flagged_as_not_spam_signal.send(sender=Message, message=message)

        message.mark_as_not_junk()


class MoveForm(ActionForm):
    destination = forms.TypedChoiceField(coerce=lambda x: int(x), choices=Message.FOLDER_CHOICES)


class MailboxForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        if "instance" in kwargs and kwargs["instance"] is not None:
            emails = ",".join(kwargs["instance"].emails)

            if "initial" in kwargs:
                kwargs["initial"]["emails"] = emails
            else:
                kwargs["initial"] = {
                    "emails": emails
                }

        super().__init__(*args, **kwargs)
        self.instance.user = user

    class Meta:
        model = Mailbox
        fields = ('name', 'emails',)
        widgets = {
            'name': TextInput(attrs={"placeholder": _("Enter name of the mailbox")}),
            'emails': TextInput(attrs={"placeholder": _("List of emails associated to this mailbox")}),
        }

    def clean_name(self):
        return "".join(self.cleaned_data["name"].strip().lower().split())

    def save(self, commit=True):
        super().save(commit=commit)

        if commit and Mailbox.objects.filter(user=self.instance.user).count() == 1:
            self.instance.set_as_default()

        return self.instance


class SmtpServerForm(forms.ModelForm):
    def __init__(self, mailbox=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if mailbox is not None:
            self.instance.mailbox = mailbox

    class Meta:
        model = SmtpServer
        fields = ('ip_address', 'port', 'username', 'password', 'use_ssl', 'from_email', 'from_name',)
        widgets = {
            'ip_address': TextInput(attrs={"placeholder": _("Enter IP or domain name of SMTP server")}),
            'port': TextInput(attrs={"placeholder": _("Enter port of SMTP server")}),
            'username': TextInput(attrs={"placeholder": _("Username")}),
            'password': TextInput(attrs={"placeholder": _("Password")}),
            'from_email': TextInput(attrs={"placeholder": _("From email header field")}),
            'from_name': TextInput(attrs={"placeholder": _("From name header field")}),
        }


class Pop3MailServerForm(forms.ModelForm):
    def __init__(self, mailbox=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if mailbox is not None:
            self.instance.mailbox = mailbox

    class Meta:
        model = Pop3MailServer
        fields = ('ip_address', 'port', 'username', 'password', 'use_ssl', 'active')
        widgets = {
            'ip_address': TextInput(attrs={"placeholder": _("Enter IP or domain name of POP3 server")}),
            'port': TextInput(attrs={"placeholder": _("Enter port of POP3 server")}),
            'username': TextInput(attrs={"placeholder": _("Username")}),
            'password': TextInput(attrs={"placeholder": _("Password")}),
        }


class ComposeMailForm(forms.Form):
    """Compose mail form."""

    subject = forms.CharField(
        label=_("Subject"),
        max_length=1000,
        required=False
    )

    to = CommaSeparatedEmailFormField(label=_("To"))
    cc = CommaSeparatedEmailFormField(label=_("Cc"), required=False)
    bcc = CommaSeparatedEmailFormField(label=_("Bcc"), required=False)

    in_reply_to = forms.ModelChoiceField(None, required=False)

    body = forms.CharField(
        required=False
    )

    has_attachments = forms.BooleanField(required=False)
    # TODO: Mejorar esta parte
    def __init__(self, mailbox, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["in_reply_to"].queryset = Message.objects.filter(mailbox=mailbox)


class AttachmentForm(forms.Form):
    # Utilizar un model form ?????
    attachment = forms.FileField(label=_("Select a file"), allow_empty_file=True)


#class UploadedFileForm(forms.ModelForm):

#    class Meta:
#        model = UploadedFile
#        fields = ('file',)

#    def clean_file(self):
#        data = self.cleaned_data['file']
#        # Change the name of the file to something unguessable
#        # Construct the new name as <unique-hex>-<original>.<ext>
#        data.name = u'%s-%s' % (uuid.uuid4().hex, data.name)
#        return data


class ContactForm(ExtraFormsMixin, forms.ModelForm):
    class Meta:
        model = ContactUser
        fields = ('displayed_name', 'email')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.instance.id is None and user is None:
            self.instance.user = user


class UsernameForm(forms.ModelForm):
    password = forms.CharField(
        label=_("Current Password"),
        required=False,
        widget=forms.PasswordInput,
       # help_text=password_validation.password_validators_help_text_html(),
    )

    class Meta:
        model = WebmailUser
        fields = ["username"]

    def clean_username(self):
        username = self.cleaned_data['username']

        if username == self.instance.username:
            raise forms.ValidationError(_('Please enter another username. The username is the same than before.'))

        if self._meta.model.objects.filter(username=username).exists():
            raise forms.ValidationError(_('You can not use this username.'))

        return username

    def save(self, commit=True):
        user = self.instance
        user.username = self.cleaned_data['username']
        if commit:
            user.save(update_fields=["username"])
        return user


def HexField(**kwargs):
    return forms.CharField(
        validators=[
            validators.RegexValidator(
                r"^[0-9a-f]+$",
                flags=re.IGNORECASE,
                message=_(
                    _("Value must be a hexadecimal number.")
                ),
            )
        ],
        **kwargs
    )


class SignUpForm(forms.ModelForm):
    """
    A form that creates a user from the given username, verifier, salt and srp group.
    """
    class Meta:
        model = WebmailUser
        fields = ("username", "verifier", "salt", "srp_group")

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            WebmailUser.objects.get(username=username)
        except WebmailUser.DoesNotExist:
            return username
        raise forms.ValidationError(_("A user with that username already exists."))


class SRPUserInfoForm(forms.ModelForm):
    class Meta:
        model = WebmailUser
        fields = ("verifier", "salt", "srp_group")



#if settings.USE_GNUPG:
#    from gnupg import GPG


#class KeyForm(forms.ModelForm):

#    def clean_key(self):
#        """
#        Validate the key contains an email address.
#        """
#        key = self.cleaned_data["key"]
#        gpg = GPG(gnupghome=settings.GNUPG_HOME)
#        result = gpg.import_keys(key)
#        if result.count == 0:
#            raise forms.ValidationError(_("Invalid Key"))
#        return key
