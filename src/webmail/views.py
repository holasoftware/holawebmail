import functools
import json
import io
import mimetypes
import struct
import itertools
import uuid
import time
import email
from email.policy import EmailPolicy
from urllib.parse import urlencode


from django.http.response import JsonResponse, FileResponse, HttpResponseRedirect, HttpResponseNotAllowed, Http404
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext as _
from django.utils.decorators import method_decorator
from django.utils.formats import localize
from django.utils.safestring import mark_safe
from django.urls import reverse as reverse_url
from django.contrib import messages as admin_messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.gzip import gzip_page
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import View, FormView, CreateView, DeleteView, UpdateView, ListView, TemplateView
from django.template.defaultfilters import filesizeformat
from django.template.loader import render_to_string
from django.template.exceptions import TemplateDoesNotExist
from django.core import validators
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.db.utils import IntegrityError
from django.shortcuts import redirect
from django.forms.models import model_to_dict


from .auth_decorators import login_required
from .auth import login as auth_login, logout as auth_logout, update_session_auth_hash
from .srp import Verifier as SRP_Verifier, gN
from .models import MailboxModel, SmtpServerModel, Pop3MailServerModel, MessageModel, MessageAttachmentModel, TagModel, UploadAttachmentSessionModel, ContactModel, WebmailUserModel, UnknownFolderException, AccessLogModel, InvalidEmailMessageException
from .signals import file_attachment_uploaded_signal, attachment_downloaded_signal, message_flagged_as_spam_signal, message_flagged_as_not_spam_signal, message_queued_signal, attachments_uploaded_signal, user_logged_in_signal
from .forms import MailActionForm, ComposeMailForm, MailboxForm, Pop3MailServerForm, MailboxActionForm, ContactForm, ContactActionForm, UsernameForm, SignUpForm, SRPUserInfoForm, SmtpServerForm
#from .email_signature import EmailSignature
from .ajax import ajax, AJAXError, InvalidAjaxRequest, FormAJAXError
from .utils import format_body_reply
from .hooks import dispatch_hook
from .webmail_url_utils import reverse_webmail_url, get_folder_url, get_url_patterns_string_formats, redirect
from .logutils import get_logger
from . import settings


logger = get_logger()


FORWARD_MESSAGE_TEMPLATE = """


-------- Forwarded Message --------
Subject: %(subject)s
Date: %(date)s
From: %(from)s
To: %(to)s
CC: %(cc)s"""


def serialize_page_obj(page_obj):
    paginator = page_obj.paginator

    return {
        "paginator": {
            "count": paginator.count,
            "num_pages": paginator.num_pages
        },
        "number": page_obj.number,
        "previous_page_number": page_obj.previous_page_number,
        "has_previous": page_obj.has_previous,
        "has_next": page_obj.has_next,
        "next_page_number": page_obj.next_page_number
    }

def guest_only_view(f):
    @functools.wraps(f, assigned=functools.WRAPPER_ASSIGNMENTS)
    def wrapped(request, *args, **kwargs):
        user = request.webmail_user
        if user.is_authenticated:
            return redirect("init")
        else:
            return f(request, *args, **kwargs)
    return wrapped


def calculate_free_space(user):
    pass

# TODO: Add timestamp to notifications

def get_related_object_fields(instance, fields=None, exclude=None):
    data = []

    opts = instance._meta
    for f in itertools.chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
        if fields and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue

        label = f.verbose_name

        py_value = f.value_from_object(instance)
        if py_value is None:
            continue
        elif py_value is True:
            value = _("Yes")
        elif py_value is False:
            value = _("No")
        else:
            value = str(py_value)
     
        data.append({
            "label": label,
            "value": value
        })

    return data


def mailbox_view_decorator(func=None, required=False):
    def decorator(func):
        @functools.wraps(func)
        def wrap(request, *args, **kwargs):
            mailbox_id = None

            if "mbox" in kwargs:
                mailbox_id = kwargs.pop("mbox")
            elif "mbox" in request.GET:
                mailbox_id = request.GET["mbox"]
                try:
                    mailbox_id = int(mailbox_id)
                except ValueError:
                    mailbox_id = None

            if mailbox_id is None:
                if required:
                    raise Http404

                request.current_mailbox = None
                return func(request, *args, **kwargs)
            else:
                mailbox = get_object_or_404(MailboxModel, id=mailbox_id, user=request.webmail_user)
                request.current_mailbox = mailbox

                if required:
                    return func(request, mailbox, *args, **kwargs)
                else:
                    return func(request, *args, **kwargs)

        return wrap

    if func is None:
        return decorator
    else:
        return decorator(func)


def get_message_or_404(mailbox, message_id):
    try:
        message_id = int(message_id)
    except ValueError:
        raise Http404

    message = get_object_or_404(MessageModel, id=message_id, mailbox=mailbox)
    return message    


def get_unread_message_count(mailbox):
    unread = {}

    for folder_name, folder_id in MessageModel.FOLDER_ID_BY_NAME.items():
        unread[folder_name] = MessageModel.unread_messages.filter(folder_id=folder_id, mailbox=mailbox).count()

    return unread


def get_default_mailbox(user):
    default_mailbox = MailboxModel.objects.filter(user=user, is_default=True).first()

    if default_mailbox is None:
        default_mailbox = MailboxModel.objects.filter(user=user).order_by("name").first()
    
    return default_mailbox 


def get_contact_emails(user):
    return list(ContactModel.objects.values_list('email',flat=True).filter(user=user))


def get_webmail_context(request, page_name=None, context=None):
    # Proporcionar información por defecto
    #   - lista de contactos
    #       - contact_id
    #       - displayed_name
    #       - email
    #   - mailbox
    #       - mailbox_id
    #       - name
    #       (ordered list)
    #   - default mailbox id
    #   - mail signature

    mailbox = request.current_mailbox
    user = request.webmail_user

    if context is None:
        context = {}

    if page_name is not None and "page_name" not in context:
        context["page_name"] = page_name

    if hasattr(request, "current_mailbox") and request.current_mailbox is not None:
        current_mailbox = request.current_mailbox

        unread_message_count = get_unread_message_count(current_mailbox)
        context["unread_message_count"] = unread_message_count
        context["mbox"] = current_mailbox.pk
        context["pop3_mail_server_configured"] = current_mailbox.is_pop3_mail_server_configured

        context["show_compose_btn"] = settings.WEBMAIL_SHOW_COMPOSE_BTN

    mailbox_menu = MailboxModel.objects.filter(user=request.webmail_user).values("id", "name", "is_default")

    context["url_patterns_string_formats"] = get_url_patterns_string_formats()

    context["mailbox_menu"] = mailbox_menu
    context["user"] = user
    context["brand_name"] = settings.WEBMAIL_BRAND_NAME

    context["show_folders"] = settings.WEBMAIL_SHOW_FOLDERS
    context["show_folder_inbox"] = settings.WEBMAIL_SHOW_FOLDER_INBOX
    context["show_folder_sent"] = settings.WEBMAIL_SHOW_FOLDER_SENT
    context["show_folder_spam"] = settings.WEBMAIL_SHOW_FOLDER_SPAM
    context["show_folder_trash"] = settings.WEBMAIL_SHOW_FOLDER_TRASH

    context["user_can_mark_as_spam"] = settings.WEBMAIL_USER_CAN_MARK_AS_SPAM

    free_space = calculate_free_space(user)
    context["free_space"] = free_space

    context["extra_js_vars"] = dispatch_hook("extra_js_vars", {}, mailbox=mailbox, user=user)
    context["extra_head"] = dispatch_hook("extra_head", "")

    context["before_end_body"] = dispatch_hook("before_end_body", "")

    context["extra_stylesheets"] = dispatch_hook("extra_stylesheets", [])
    context["extra_scripts"] = dispatch_hook("extra_scripts", [])

    manage_mailboxes = settings.WEBMAIL_ENABLE_MANAGE_MAILBOXES

    context["show_mailboxes_admin"] = manage_mailboxes

    webmail_management_links = [
        {
            "url": reverse_webmail_url('profile', mailbox=mailbox),
            "text": _("Profile")
        },
        {
            "url": reverse_webmail_url('contacts', mailbox=mailbox),
            "text": _("Contacts")
        },
        # Import
    ]

    if settings.WEBMAIL_IMPORT_MAIL_ENABLED:
        webmail_management_links.append({
            "url": reverse_webmail_url('import_mail', mailbox=mailbox),
            "text": _("Import")
        });

    if manage_mailboxes:
        webmail_management_links.insert(0,
            {
                "url": reverse_webmail_url('mailboxes', mailbox=mailbox),
                "text": _("Manage mailboxes")
            }
        )

    if settings.WEBMAIL_ENABLE_ACCESS_LOGS:
        webmail_management_links.append(
            {
                "url": reverse_webmail_url('access_logs', mailbox=mailbox),
                "text": _("Show access logs")
            }
        )

    context["webmail_management_links"] = dispatch_hook("webmail_management_links", webmail_management_links, mailbox=mailbox, user=user)

    context["webmail_session_id"] = request.webmail_session.get("session_id", "")

    context = dispatch_hook("page_context", context, request=request)
    context = dispatch_hook("%s_page_context" % page_name, context, request=request)
    return context


def set_session_id(sender, request, user, **kw):
    request.webmail_session["session_id"] = uuid.uuid1().hex

user_logged_in_signal.connect(set_session_id, sender=WebmailUserModel)


def render_webmail_page(request, template_name, page_name, context=None):
    context = get_webmail_context(request, page_name, context)

    return render(request, template_name, context)


def redirect_to_login(next):
    """
    Redirect the user to the login page, passing the given 'next' page.
    """
    return redirect("login", query_params={REDIRECT_FIELD_NAME: next})


class WebmailViewMixin:
    page_name = None

    permission_denied_message = ''
    # raise_exception_on_permission_denied = False
    permission_denied_raise_exception = False

    def get_permission_denied_message(self):
        """
        Override this method to override the permission_denied_message attribute.
        """
        return self.permission_denied_message

    def handle_no_permission(self):
        if self.permission_denied_raise_exception or (hasattr(request,"webmail_user") and self.request.webmail_user.is_authenticated):
            raise PermissionDenied(self.get_permission_denied_message())

        # redirect_to = request.build_absolute_uri(request.path)
        redirect_to = self.request.get_full_path()
        return redirect_to_login(redirect_to)

    # TODO: Hace falta csrf_protect cuando el middleware esta activo ???
    @method_decorator(login_required)
    @method_decorator(csrf_protect)
    @method_decorator(mailbox_view_decorator)
    def dispatch(self, request, *args, **kwargs):
        self.mailbox = request.current_mailbox

        return super().dispatch(request, *args, **kwargs)

    def reverse_url(self, _viewname, **kwargs):
        return reverse_webmail_url(_viewname, kwargs=kwargs, mailbox=self.mailbox)

    def redirect(self, _viewname, kwargs=None, query_params=None):
        return redirect(_viewname, kwargs=kwargs, query_params=query_params, mailbox=self.mailbox)

    def get_page_name(self):
        return self.page_name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = get_webmail_context(self.request, self.get_page_name(), context)

        return context


class WebmailTemplateView(WebmailViewMixin, TemplateView):
    pass

class WebmailModelFormViewMixin(WebmailViewMixin):
    page_title = None
    object_name = None
    object_action_name = None
    template_name = "webmail/model_form.html"
    success_message = None
    action_url = None
    form_id = None
    form_css_class = None
    back_url = None
    back_url_text = None

    def get_form_id(self):
        if self.form_id is None:
            return self.object_name + "_form"
        else:
            return self.form_id

    def get_form_css_class(self):
        return self.form_css_class

    def get_back_url(self):
        return self.back_url

    def get_action_url(self):
        return self.action_url

    def get_back_url_text(self):
        return self.back_url_text

    def get_page_name(self):
        return "%s_%s" % (self.object_name, self.object_action_name)

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = self.page_title
        kwargs["object_name"] = self.object_name
        kwargs["form_id"] = self.get_form_id()
        kwargs["form_css_class"] = self.get_form_css_class()
        kwargs["action_url"] = self.get_action_url()
        kwargs["back_url_text"] = self.get_back_url_text()
        kwargs["back_url"] = self.get_back_url()

        return super().get_context_data(**kwargs)

    def get_success_message(self, instance):
        if self.success_message:
            return mark_safe(self.success_message.format(instance=instance))

    def form_valid(self, form):
        success_message = self.get_success_message(form.instance)

        if success_message is not None:
            admin_messages.success(self.request, success_message)
        
        return super().form_valid(form)


class WebmailCreateView(WebmailModelFormViewMixin, CreateView):
    object_action_name = "add"


class WebmailUpdateView(WebmailModelFormViewMixin, UpdateView):
    object_action_name = "edit"
    delete_url = None

    def get_delete_url(self):
        return self.delete_url

    def get_context_data(self, **kwargs):
        delete_url = self.get_delete_url()
        if delete_url:
            kwargs["delete_url"] = delete_url 

        return super().get_context_data(**kwargs)


class WebmailDeleteView(WebmailViewMixin, DeleteView):
    pass


class WebmailListView(WebmailViewMixin, ListView):
    paginate_by = 10
    template_name = "webmail/model_list.html"
    title = None
    object_name = None
    columns = None
    add_obj_url_name = None
    bulk_action_url_name = None
    back_url = None
    back_url_text = None
    obj_actions = None

    show_list_controls = True

    can_bulk_delete = True
    allowed_to_edit_objects = True

    def get_allowed_to_edit_object(self, obj):
        return self.allowed_to_edit_objects

    def get_back_url(self):
        return self.back_url

    def get_back_url_text(self):
        return self.back_url_text

    def get_columns(self):
        return list(self.columns)

    def get_table_row_data(self, obj):
        return {column["name"]: getattr(obj, column["name"]) for column in self.columns}

    def get_bulk_action_url_name(self):
        if self.bulk_action_url_name is not None:
            return self.bulk_action_url_name
        else:
            return self.object_name + "s_bulk_action"

    def get_add_obj_url_name(self):
        if self.add_obj_url_name is not None:
            return self.add_obj_url_name
        else:
            return self.object_name + "_add"

    def get_page_name(self):
        if self.page_name is not None:
            return self.page_name
        else:
            return self.object_name + "_list"

    def get_obj_actions(self):
        if self.obj_actions is None:
            obj_actions = []
        else:
            obj_actions = list(self.obj_actions)

        if self.can_bulk_delete:
            obj_actions.append({
                "label": _("Delete"),
                "action_name": "delete"
            })

        return obj_actions

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = self.title
        context["object_name"] = self.object_name
        context["back_url"] = self.get_back_url()
        context["back_url_text"] = self.get_back_url_text()

        if self.show_list_controls:
            context["show_list_controls"] = self.show_list_controls
            context["add_obj_url_name"] = self.get_add_obj_url_name()

            obj_actions = self.get_obj_actions()

            if obj_actions:
                context["obj_actions"] = obj_actions
                context["bulk_action_url_name"] = self.get_bulk_action_url_name()

        page_name = self.get_page_name()

        columns = dispatch_hook(page_name + "_columns", self.get_columns())

        context["table_headers"] = [column["label"] for column in columns]

        column_names = [column["name"] for column in columns]

        page_obj = context["page_obj"]
        context["page_obj"] = serialize_page_obj(page_obj)

        object_list = context.pop("object_list")

        table_rows = []
        for obj in object_list:
            row_data = dispatch_hook(page_name + "_table_row", self.get_table_row_data(obj), obj=obj)

            table_rows.append({
                "id": obj.id,
                "cell_data_list": [row_data[column_name] if column_name in row_data else "" for column_name in column_names],
                "obj_editable": self.get_allowed_to_edit_object(obj)
            })

        context["table_rows"] = table_rows

        return context


def get_initial_url(user):
    default_mailbox = get_default_mailbox(user)

    if default_mailbox is None:
        url = reverse_webmail_url("mailbox_add")
    else:
        url = get_folder_url(default_mailbox, folder_name="inbox")

    return url


@require_GET
@guest_only_view
def login(request):
#    if request.method == "POST":
#        form = AuthenticationForm(request, data=request.POST)

#        if not form.is_valid():
#            return render(request, "webmail/login.html", {
#                "form": form
#            })

#        user = form.get_user()
#        auth_login(request, user)

#        next_url = reverse_url("init")

#        return HttpResponseRedirect(next_url)
#    else:
    context = {}
    if "username" in request.GET:
        username = request.GET["username"]
        context["username"] = username

    context["html_head_title"] = settings.WEBMAIL_LOGIN_HTML_HEAD_TITLE
    context["logo_alt"] = settings.WEBMAIL_LOGIN_LOGO_ALT
    context["logo_image_url"] = settings.WEBMAIL_LOGIN_LOGO_IMAGE_URL
    context["logo_width"] = settings.WEBMAIL_LOGIN_LOGO_WIDTH
    context["logo_height"] = settings.WEBMAIL_LOGIN_LOGO_HEIGHT
    context["title"] = settings.WEBMAIL_LOGIN_TITLE
    context["background_color"] = settings.WEBMAIL_LOGIN_BACKGROUND_COLOR

    return render(request, "webmail/login.html", context)


@login_required
def logout(request):
    auth_logout(request)

    return redirect("login")


def autologin(request, username):
    if not settings.WEBMAIL_AUTOLOGIN_ENABLED:
        raise Http404

    try:
        user = WebmailUserModel.objects.get(username=username)
    except WebmailUserModel.DoesNotExist:
        raise Http404

    auth_login(request, user)

    url = get_initial_url(request.webmail_user)
    return HttpResponseRedirect(url)


# def home(request):
@login_required
def init(request):
    url = get_initial_url(request.webmail_user)
    return HttpResponseRedirect(url)


@login_required
@mailbox_view_decorator
def mailboxes(request):
    if "page" in request.GET:
        page_num = request.GET["page"]

        try:
            page_num = int(page)
        except ValueError:
            page_num = 1
    else:
        page_num = 1

    
    query = MailboxModel.objects.filter(user=request.webmail_user)
    if query.count() == 0:
        return self.reverse_url("mailbox_add")

    paginator = Paginator(query, settings.WEBMAIL_MAILBOX_ITEMS_PER_PAGE)

    try:
        page = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        raise Http404

    return render_webmail_page(request, "webmail/mailbox_list.html", "mailbox_list", {
        "page": page
    })


class MailboxCreateView(WebmailCreateView):
    page_title = _("Add mailbox")
    object_name = "mailbox"
    form_class = MailboxForm
    success_message = _('Mailbox <b>{instance.name}</b> created!')
    back_url_text = _("Back to mailbox list")

    def get_success_url(self):
        return self.reverse_url("mailbox_edit", mailbox_id=self.object.id)

    def dispatch(self, *args, **kwargs):
        try:
            return super().dispatch(*args, **kwargs)
        except IntegrityError:
            admin_messages.error(self.request, _('Mailbox with the same name already exists!'))

            return redirect("mailboxes", mailbox=self.mailbox)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.webmail_user

        return kwargs

    def get_back_url(self):
        return self.reverse_url("mailboxes")

    def get_action_url(self):
        return self.reverse_url("mailbox_add")


class MailboxUpdateView(WebmailUpdateView):
    page_title = _("Edit mailbox") 
    form_class = MailboxForm
    object_name = "mailbox"
    success_message = _('Mailbox updated successfully!')
    back_url_text = _("Back to mailbox list")

    def get_success_url(self):
        mailbox_id = self.kwargs["mailbox_id"]
        return self.reverse_url("mailbox_edit", mailbox_id=mailbox_id)

    def get_back_url(self):
        return self.reverse_url("mailboxes")

    def dispatch(self, *args, **kwargs):
        try:
            return super().dispatch(*args, **kwargs)
        except IntegrityError:
            admin_messages.error(self.request, _('Mailbox with the same name already exists!'))
            url = self.reverse_url("mailboxes")

            return HttpResponseRedirect(url)

    def get_object(self):
        mailbox_id = self.kwargs["mailbox_id"]

        try:
            return MailboxModel.objects.get(id=mailbox_id, user=self.request.webmail_user)
        except MailboxModel.DoesNotExist:
            raise Http404

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.webmail_user

        return kwargs

    def get_context_data(self, **kwargs):
        mailbox_id = self.kwargs["mailbox_id"]

        after_form_buttons = ""
        bottom_objects = []

        if settings.WEBMAIL_ENABLE_MANAGE_SMTP_SERVER:
            try:
                smtp_server = self.object.smtp_server
    #        except AttributeError:
            except SmtpServerModel.DoesNotExist:
                after_form_buttons += '<a style="margin-left:8px" href="' + self.reverse_url('smtp_server_add', mailbox_id=mailbox_id) + '">' + _("Add SMTP server") + '</a>'
            else:
                bottom_objects.append({
                    "title": _("SMTP Server"),
                    "fields": get_related_object_fields(smtp_server),
                    "edit_url": self.reverse_url("smtp_server_edit", mailbox_id=mailbox_id)
                })

        if settings.WEBMAIL_ENABLE_MANAGE_POP3_MAIL_SERVER:
            try:
                pop3_mail_server = self.object.pop3_mail_server
    #        except AttributeError:
            except Pop3MailServerModel.DoesNotExist:
                after_form_buttons += '<a style="margin-left:8px" href="' + self.reverse_url('pop3_mail_server_add', mailbox_id=mailbox_id) + '">' + _("Add POP3 mail server") + '</a>'
            else:
                bottom_objects.append({
                    "title": _("POP3 Mail Server"),
                    "fields": get_related_object_fields(pop3_mail_server),
                    "edit_url": self.reverse_url("pop3_mail_server_edit", mailbox_id=mailbox_id)
                })

        if after_form_buttons:
            kwargs["after_form_buttons"] = after_form_buttons

        if bottom_objects:
            kwargs["model_form_bottom"] = {
                "template_name": "webmail/includes/info_objects.html",
                "data": {
                    "objects": bottom_objects
                }
            }

        return super().get_context_data(**kwargs)

    def get_action_url(self):
        mailbox_id = self.kwargs["mailbox_id"]
        return self.reverse_url("mailbox_edit", mailbox_id=mailbox_id)

    def get_delete_url(self):
        mailbox_id = self.kwargs["mailbox_id"]
        return self.reverse_url("mailbox_delete", mailbox_id=mailbox_id)


class MailboxDeleteView(WebmailViewMixin, DeleteView):
    def get_success_url(self):
        return self.reverse_url("mailboxes")

    def get_object(self):
        mailbox_id = self.kwargs["mailbox_id"]

        try:
            return MailboxModel.objects.get(id=mailbox_id, user=self.request.webmail_user)
        except MailboxModel.DoesNotExist:
            raise Http404

    def delete(self, request, *args, **kwargs):
        admin_messages.success(self.request, _('Mailbox deleted!'))
        response = super().delete(request, *args, **kwargs)

        return response


class Pop3MailServerCreateView(WebmailCreateView):
    object_name = "pop3_mail_server"            
    page_title = _("Add POP3 mail server")
    form_class = Pop3MailServerForm
    success_message = _('POP3 mail server created for mailbox <b>{instance.mailbox.name}</b>')

    def get_success_url(self):
        mailbox_id = self.kwargs["mailbox_id"]

        return self.reverse_url("pop3_mail_server_edit", mailbox_id=mailbox_id)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        mailbox_id = kwargs["mailbox_id"]

        try:
            self.mailbox = MailboxModel.objects.get(id=mailbox_id, user=self.request.webmail_user)
        except MailboxModel.DoesNotExist:
            raise Http404

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["mailbox"] = self.mailbox

        return kwargs

    def get_action_url(self):
        mailbox_id = self.kwargs["mailbox_id"]
        return self.reverse_url("pop3_mail_server_add", mailbox_id=mailbox_id)

    def get_back_url(self):
        mailbox_id = self.kwargs["mailbox_id"]

        return self.reverse_url("mailbox_edit", mailbox_id=mailbox_id)


class Pop3MailServerUpdateView(WebmailUpdateView):
    object_name ="pop3_mail_server"            
    form_class = Pop3MailServerForm
    page_title = _("Edit POP3 mail server")
    success_message = _('POP3 mail server for mailbox <b>{instance.mailbox.name}</b> updated successfully')

    def get_success_url(self):
        mailbox_id = self.kwargs["mailbox_id"]

        return self.reverse_url("pop3_mail_server_edit", mailbox_id=mailbox_id)

    def get_object(self):
        mailbox_id = self.kwargs["mailbox_id"]

        try:
            return Pop3MailServerModel.objects.get(mailbox__id=mailbox_id, mailbox__user=self.request.webmail_user)
        except Pop3MailServerModel.DoesNotExist:
            raise Http404

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["mailbox"] = self.mailbox

        return kwargs

    # TODO: Revisar esta parte. genera errores cuando se entra a este tipo de urls
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        mailbox_id = kwargs["mailbox_id"]

        try:
            self.mailbox = MailboxModel.objects.get(id=mailbox_id, user=self.request.webmail_user)
        except MailboxModel.DoesNotExist:
            raise Http404

    def get_action_url(self):
        mailbox_id = self.kwargs["mailbox_id"]
        return self.reverse_url("pop3_mail_server_edit", mailbox_id=mailbox_id)

    def get_delete_url(self):
        mailbox_id = self.kwargs["mailbox_id"]
        return self.reverse_url("pop3_mail_server_delete", mailbox_id=mailbox_id)

    def get_back_url(self):
        mailbox_id = self.kwargs["mailbox_id"]

        return self.reverse_url("mailbox_edit", mailbox_id=mailbox_id)


class Pop3MailServerDeleteView(WebmailViewMixin, DeleteView):
    def get_success_url(self):
        mailbox_id = self.kwargs["mailbox_id"]

        return self.reverse_url("mailbox_edit", mailbox_id=mailbox_id)

    def get_object(self):
        mailbox_id = self.kwargs["mailbox_id"]

        try:
            return Pop3MailServerModel.objects.get(mailbox__id=mailbox_id, mailbox__user=self.request.webmail_user)
        except Pop3MailServerModel.DoesNotExist:
            raise Http404

    def delete(self, request, *args, **kwargs):
        admin_messages.success(self.request, _('POP3 mail server deleted!'))
        response = super().delete(request, *args, **kwargs)

        return response


class SmtpServerCreateView(WebmailCreateView):
    object_name = "smtp_server"            
    page_title = _("Add SMTP server")
    form_class = SmtpServerForm
    success_message = _('SMTP server created for mailbox <b>{instance.mailbox.name}</b>')

    def get_success_url(self):
        mailbox_id = self.kwargs["mailbox_id"]

        return self.reverse_url("smtp_server_edit", mailbox_id=mailbox_id)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        mailbox_id = kwargs["mailbox_id"]

        try:
            self.mailbox = MailboxModel.objects.get(id=mailbox_id, user=self.request.webmail_user)
        except MailboxModel.DoesNotExist:
            raise Http404

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["mailbox"] = self.mailbox

        return kwargs

    def get_action_url(self):
        mailbox_id = self.kwargs["mailbox_id"]
        return self.reverse_url("smtp_server_add", mailbox_id=mailbox_id)

    def get_back_url(self):
        mailbox_id = self.kwargs["mailbox_id"]

        return self.reverse_url("mailbox_edit", mailbox_id=mailbox_id)


class SmtpServerUpdateView(WebmailUpdateView):
    object_name ="smtp_server"            
    form_class = SmtpServerForm
    page_title = _("Edit SMTP server")
    success_message = _('SMTP server for mailbox <b>{instance.mailbox.name}</b> updated successfully')

    def get_success_url(self):
        mailbox_id = self.kwargs["mailbox_id"]

        return self.reverse_url("smtp_server_edit", mailbox_id=mailbox_id)

    def get_object(self):
        mailbox_id = self.kwargs["mailbox_id"]

        try:
            return SmtpServerModel.objects.get(mailbox__id=mailbox_id, mailbox__user=self.request.webmail_user)
        except SmtpServerModel.DoesNotExist:
            raise Http404

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["mailbox"] = self.mailbox

        return kwargs

    # TODO: Revisar esta parte. genera errores cuando se entra a este tipo de urls
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        mailbox_id = kwargs["mailbox_id"]

        try:
            self.mailbox = MailboxModel.objects.get(id=mailbox_id, user=self.request.webmail_user)
        except MailboxModel.DoesNotExist:
            raise Http404

    def get_action_url(self):
        mailbox_id = self.kwargs["mailbox_id"]
        return self.reverse_url("smtp_server_edit", mailbox_id=mailbox_id)

    def get_delete_url(self):
        mailbox_id = self.kwargs["mailbox_id"]
        return self.reverse_url("smtp_server_delete", mailbox_id=mailbox_id)

    def get_back_url(self):
        mailbox_id = self.kwargs["mailbox_id"]

        return self.reverse_url("mailbox_edit", mailbox_id=mailbox_id)


class SmtpServerDeleteView(WebmailViewMixin, DeleteView):
    def get_success_url(self):
        mailbox_id = self.kwargs["mailbox_id"]

        return self.reverse_url("mailbox_edit", mailbox_id=mailbox_id)

    def get_object(self):
        mailbox_id = self.kwargs["mailbox_id"]

        try:
            return SmtpServerModel.objects.get(mailbox__id=mailbox_id, mailbox__user=self.request.webmail_user)
        except SmtpServerModel.DoesNotExist:
            raise Http404

    def delete(self, request, *args, **kwargs):
        admin_messages.success(self.request, _('SMTP server deleted!'))
        response = super().delete(request, *args, **kwargs)

        return response


class MailboxListView(WebmailListView):
    model = MailboxModel

    title = _("List of mailboxes")
    object_name = "mailbox"

    bulk_action_url_name = "mailboxes_bulk_action"

    columns = [
        {
        "name": "name",
        "label": _("Name")
        },
        {
        "name": "emails",
        "label": _("Email")
        },
        {
        "name": "is_default",
        "label": _("Default")
        },
        {
        "name": "created_at",
        "label": _("Creation date")
        },
        {
        "name": "is_smtp_server_configured",
        "label": _("SMTP server")
        # "label": _("Configured mail server")
        },
        {
        "name": "is_pop3_mail_server_configured",
        "label": _("POP3 server")
        # "label": _("Configured mail server")
        },
        {
        "name": "is_pop3_mail_server_active",
        "label": _("POP3 is active")
        },
    ]

    back_url_text = _("Back to inbox")

    def get_back_url(self):
        if self.mailbox is not None:
            return get_folder_url(self.mailbox, folder_name="inbox")

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.webmail_user)

    def get_table_row_data(self, obj):
        row_data = super().get_table_row_data(obj)
        row_data["is_default"] = _("Yes") if row_data["is_default"] else ""
        row_data["created_at"] = localize(row_data["created_at"])
        row_data["is_smtp_server_configured"] = _("Yes") if row_data["is_smtp_server_configured"] else _("No")
        row_data["is_pop3_mail_server_configured"] = _("Yes") if row_data["is_pop3_mail_server_configured"] else _("No")
        row_data["is_pop3_mail_server_active"] = _("Yes") if row_data["is_pop3_mail_server_active"] else _("No")
        return row_data


class BulkActionView:
    success_messages = None
    no_object_selected_error_message = _("Nothing selected")
    form_class = None
    success_url_name = None

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_success_url(self, request):
        url = reverse_webmail_url(self.success_url_name, mailbox=request.current_mailbox)
        return url

    def get_form_args(self):
        return (request.webmail_user,)

    def get_action_form(self, request):
        action_form_class = get_form_class()
        form = self.form_class(*self.get_form_args(), data=request.POST)

        return form

    @require_POST
    @login_required
    @mailbox_view_decorator
    def __call__(self, request):
        form = self.get_action_form(request)
        
        if form.is_valid():
            if form.cleaned_data["obj_list"] is None:
                admin_messages.error(request, self.no_object_selected_error_message)
            else:
                form.apply_action()

                action_name = form.cleaned_data["action_name"]

                message_template = self.success_messages[action_name]
                message = message_template.format(num_contacts=form.get_obj_list_length())

                admin_messages.success(request, mark_safe(message))
        else:
            logger.debug("Error processing mail bulk action", form.errors)
            admin_messages.error(request, _("There was an error processing the action"))

        url = self.get_success_url()

        return HttpResponseRedirect(url)



MAILBOX_ACTION_SUCCESS_MESSAGE = {
    "delete": _("<b>{{ num_mailboxes }}</b> mailbox/es deleted.")
}

@require_POST
@login_required
@mailbox_view_decorator
def mailboxes_bulk_action(request):
    form = MailboxActionForm(user=request.webmail_user, data=request.POST)
    
    if form.is_valid():
        if form.cleaned_data["obj_list"] is None:
            admin_messages.error(request, _("No mailbox selected"))
        else:
            form.apply_action()

            action_name = form.cleaned_data["action_name"]
            message_template = MAILBOX_ACTION_SUCCESS_MESSAGE[action_name]
            message = message_template.format(num_mailboxes=form.get_obj_list_length())

            admin_messages.success(request, mark_safe(message))
    else:
        logger.debug("Error processing mail bulk action", form.errors)
        admin_messages.error(request, _("There was an error processing the action"))

    url = reverse_webmail_url("mailboxes", mailbox=request.current_mailbox)

    return HttpResponseRedirect(url)


class AccessLogsListView(WebmailListView):
    model = AccessLogModel

    title = _("Access logs")
    object_name = "access_log"

    columns = [
        {
        "name": "ip",
        "label": _("IP")
        },
        {
        "name": "user_agent",
        "label": _("User Agent")
        },
        {
        "name": "date",
        "label": _("Date")
        },
    ]

    show_list_controls = False
    can_bulk_delete = False
    allowed_to_edit_objects = False

    back_url_text = _("Back to inbox")

    def get_back_url(self):
        if self.mailbox is not None:
            return get_folder_url(self.mailbox, folder_name="inbox")

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.webmail_user)

    def get_table_row_data(self, obj):
        row_data = super().get_table_row_data(obj)
        row_data["date"] = localize(row_data["date"])
        return row_data


# def folder
@login_required
@mailbox_view_decorator(required=True)
def show_folder(request, mailbox, folder_name="inbox"):
    """
    Displays a list of received messages for the current user.
    Optional Arguments:
        ``template_name``: name of the template to use.
    """

    if "page" in request.GET:
        page_num = request.GET["page"]

        try:
            page_num = int(page_num)
        except ValueError:
            page_num = 1
    else:
        page_num = 1

    folder_id = MessageModel.FOLDER_ID_BY_NAME.get(folder_name, None)
    if folder_id is None:
        raise Http404("Invalid folder name:" + folder_name)

    filters = {}

    Q_objects = [Q(mailbox=mailbox), Q(folder_id=folder_id)]

    if "q" in request.GET:
        q = request.GET["q"]
        filters["q"] = q

        search_text_Q_list = []

        if "text_in_subject" in request.GET and request.GET["text_in_subject"] == "1":
            filters["text_in_subject"] = "1"
            search_text_Q_list.append(Q(subject__icontains=q))

        if "text_in_body" in request.GET and request.GET["text_in_body"] == "1":
            filters["text_in_body"] = "1"
            search_text_Q_list.append(Q(text_plain__icontains=q))

        if "text_in_from_email" in request.GET and request.GET["text_in_from_email"] == "1":
            filters["text_in_from_email"] = "1"
            search_text_Q_list.append(Q(from_email__icontains=q))

        if len(search_text_Q_list) != 0:
            search_text_Q = search_text_Q_list[0]

            for q_obj in search_text_Q_list[1:]:
                search_text_Q |= q_obj

            Q_objects.append(search_text_Q)

    filter_is_read = None
    if "read" in request.GET:
        read_filter = request.GET["read"]
        if read_filter == "1":
            filters["read"] = True
            Q_objects.append(Q(read_at__isnull=False))
        elif read_filter == "0":
            filters["read"] = False
            Q_objects.append(Q(read_at__isnull=True))

    if "starred" in request.GET:
        starred_filter = request.GET["starred"]
        if starred_filter == "1":
            filters["starred"] = True
            Q_objects.append(Q(is_starred=True))
        elif starred_filter == "0":
            filters["starred"] = False
            Q_objects.append(Q(is_starred=False))

    if "has_attachments" in request.GET:
        has_attachments = request.GET["has_attachments"]
        if has_attachments == "1":
            filters["has_attachments"] = True
            Q_objects.append(Q(attachments__isnull=False))
        else:
            filters["has_attachments"] = False
            Q_objects.append(Q(attachments__isnull=True))

    obj_results = MessageModel.objects.filter(*Q_objects) 
    paginator = Paginator(obj_results, settings.WEBMAIL_MESSAGE_ITEMS_PER_PAGE, allow_empty_first_page=False)

    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        raise Http404
    except EmptyPage:
        if filters:
            num_messages = 0
            page_obj = None
        else:
            return render_webmail_page(request, "webmail/folder.html", "folder", {
                "active_folder": folder_name,
                "is_empty_folder": True,
                "init_page_data": {
                    "is_empty_folder": True
                }
            })
    else:
        num_messages = page_obj.paginator.count

#    messages = []

#    for i in range(len(messsage_obj_page)):
#        message = messsage_obj_page[i]

#        # TODO: Falta date del mensaje
#        messages.append({
#            "id": message.id,
#            "subject": message.subject,
#            "from_email": message.from_email,
#            "is_starred": message.is_starred,
#            "read": message.read,
#            "has_attachments": message.has_attachments()
#        })

    unread_message_count = get_unread_message_count(mailbox)

    return render_webmail_page(request, "webmail/folder.html", "folder", {
        "active_folder": folder_name,
        "filters": filters,
        "num_messages": num_messages,
#        "page_num": page_num,
#        "start_index": messsage_list_page.start_index,
#        "end_index": messsage_list_page.end_index,
#        "total_pages": paginator.num_pages,
        "page_obj": page_obj
    })


@ajax(login_required=True, require_POST=True)
@mailbox_view_decorator(required=True)
def mark_as_read(request, mailbox, message_id):
    message = get_message_or_404(mailbox, message_id)
    message.mark_as_read()


@ajax(login_required=True, require_POST=True)
@mailbox_view_decorator(required=True)
def mark_as_unread(request, mailbox, message_id):
    message = get_message_or_404(mailbox, message_id)
    message.mark_as_unread()


@require_POST
@login_required
@mailbox_view_decorator(required=True)
def mark_as_spam(request, mailbox, message_id):
    message = get_message_or_404(mailbox, message_id)

    message_flagged_as_spam_signal.send(sender=MessageModel, message=message)
    message.mark_as_spam()

    admin_messages.success(request, _("Message marked as spam."))

    url = reverse_webmail_url("read_mail", mailbox=mailbox, kwargs={"message_id":message_id})

    return HttpResponseRedirect(url)


@require_POST
@login_required
@mailbox_view_decorator(required=True)
def mark_as_not_junk(request, mailbox, message_id):
    """Mark a message as not junk."""
    message = get_message_or_404(mailbox, message_id)

    if message.folder_id == MessageModel.SPAM_FOLDER_ID:
        message_flagged_as_not_spam_signal.send(sender=MessageModel, message=message)

    message.mark_as_not_junk()

    admin_messages.success(request, _("Message marked as not junk."))

    url = reverse_webmail_url("read_mail", mailbox=mailbox, kwargs={"message_id":message_id})

    return HttpResponseRedirect(url)


@ajax(login_required=True, require_POST=True)
@mailbox_view_decorator(required=True)
def delete_all_spam(request, mailbox):
    num_messages = MessageModel.spam_folder.filter(mailbox=mailbox).update(folder_id=MessageModel.TRASH_FOLDER_ID)

    return {
        "num_messages": num_messages
    }


@ajax(login_required=True, require_POST=True)
@mailbox_view_decorator(required=True)
def empty_trash(request, mailbox):
    num_messages, _ = MessageModel.trash_folder.filter(mailbox=mailbox).delete()

    return {
        "num_messages": num_messages
    }


@ajax(login_required=True, require_POST=True)
@mailbox_view_decorator(required=True)
def add_star(request, mailbox, message_id):
    message = get_message_or_404(mailbox, message_id)

    message.is_starred = True
    message.save()


@ajax(login_required=True, require_POST=True)
@mailbox_view_decorator(required=True)
def remove_star(request, mailbox, message_id):
    message = get_message_or_404(mailbox, message_id)

    message.is_starred = False
    message.save()


@require_POST
@login_required
@mailbox_view_decorator(required=True)
def mail_delete(request, mailbox, message_id):
    message = get_message_or_404(mailbox, message_id)
    folder_name =  message.get_folder_name()

    message.user_action_delete()

    admin_messages.success(request, _("Message '%s' has been deleted.") % message_id)

    url = get_folder_url(mailbox, folder_name)
    return HttpResponseRedirect(url)


@require_POST
@login_required
@mailbox_view_decorator(required=True)
def move_to_folder(request, mailbox, message_id, folder_name):
    message = get_message_or_404(mailbox, message_id)

    try:
        message.move_to_folder(folder_name)
    except UnknownFolderException:
        raise Http404

    admin_messages.success(request, _("Message successfully moved to folder"))


class UnknownAction(Http404):

    """
    Use this exception when the webmail encounter an unknown action.
    """

    def __init__(self):
        super().__init__(_("Unknown action"))


#    if request.method == 'POST':
#        mailboxes = Mailbox.objects.filter(imap=mailbox.imap)
#        action = request.POST.get('action', None)
#        if action == 'unread':
#            thread.mark_as_unread()
#            admin_messages.success(request, _('The conversation has been marked as'
#                                        ' new'))

#        if action == 'delete':
#            thread.delete_from_imap()
#            admin_messages.success(request, _('The conversation has been '
#                                        'successfully deleted'))

#        if action == 'move':
#            form = MoveForm(mailbox.imap, data=request.POST)
#            if form.is_valid():
#                dest = mailboxes.get(pk=form.cleaned_data['destination'])
#                thread.move_to(dest.name)
#                admin_messages.success(request, _('The conversation has been '
#                                            'successfully moved to '
#                                            '"%s"' % dest.name))
#            else:
#                admin_messages.error(request, _('Unable to move the conversation'))
#        return redirect(reverse('directory', args=[mbox_id]))


MAIL_ACTION_SUCCESS_MESSAGE = {
    "star": _("%d message/s starred."),
    "unstar": _("%d message/s removed stars."),
    "mark_as_read": _("%d message/s marked as read."),
    "mark_as_unread": _("%d message/s marked as unread."),
    "delete_permanently": _("%d message/s deleted permanently."),
    "spam": _("%d message/s marked as spam."),
    "delete": _("%d message/s deleted."),
    "mark_as_not_junk": _("%d message/s marked as Ok.")
}


@require_POST
@login_required
@mailbox_view_decorator(required=True)
def mails_bulk_action(request, mailbox, folder_name):
    if folder_name not in MessageModel.FOLDER_NAMES:
        raise Http404

    if folder_name == "trash" and request.POST.get("action_name", None) == "empty_trash":
        MessageModel.trash_folder.filter(mailbox=mailbox).delete()
        num_deleted, _not_important = MessageModel.trash_folder.filter(mailbox=mailbox).delete()

        if num_deleted == 0:
            admin_messages.error(request, _("Trash folder was already empty."))
        else:
            admin_messages.success(request, _("Deleted %d messages.") % num_deleted)

    elif folder_name == "spam" and request.POST.get("action_name", None) == "delete_all_spam":
        num_updated = MessageModel.spam_folder.filter(mailbox=mailbox).update(folder_id=MessageModel.TRASH_FOLDER_ID)

        if num_updated == 0:
            admin_messages.error(request, _("Spam folder was already empty."))
        else:
            admin_messages.success(request, _("Deleted %d messages.") % num_updated)

    else:
        form = MailActionForm(mailbox=mailbox, folder_name=folder_name, data=request.POST)
        
        if form.is_valid():
            if form.cleaned_data["obj_list"] is None:
                admin_messages.error(request, _("No mail selected"))
            else:
                form.apply_action()

                action_name = form.cleaned_data["action_name"]
                if action_name in MAIL_ACTION_SUCCESS_MESSAGE:
                    num_messages_affected = len(form.cleaned_data["obj_list"])

                    success_template_message = MAIL_ACTION_SUCCESS_MESSAGE[action_name]

                    text = success_template_message % num_messages_affected
                    admin_messages.success(request, text)
        else:
            print(request.POST, form.errors)
            # TODO: Especificar error
            admin_messages.error(request, _("There was an error processing the action"))

    url = get_folder_url(request.current_mailbox, folder_name)
    
    return HttpResponseRedirect(url)

#    action = request.POST.get('action', None)
#    if action == 'unread':
#        thread.mark_as_unread()
#        admin_messages.success(request, _('The conversation has been marked as'
#                                    ' new'))
#    elif action == 'delete':
#        thread.delete_from_imap()
#        admin_messages.success(request, _('The conversation has been '
#                                    'successfully deleted'))

#    elif action == 'move':
#        form = MoveForm(mailbox.imap, data=request.POST)
#        if form.is_valid():
#            dest = mailboxes.get(pk=form.cleaned_data['destination'])
#            thread.move_to(dest.name)
#            admin_messages.success(request, _('The conversation has been '
#                                        'successfully moved to '
#                                        '"%s"' % dest.name))
#        else:
#            admin_messages.error(request, _('Unable to move the conversation'))
#    return redirect(reverse('directory', args=[mbox_id]))


def randid():
    return str(uuid.uuid4()).replace("-", "")


def render_compose_page(request, subject=None, to=None, cc=None, bcc=None, body=None, in_reply_to=None):
    context = {}
    init_page_data = {}

    contact_emails = get_contact_emails(request.webmail_user)
    if contact_emails:
        init_page_data["contact_emails"] = contact_emails

    if subject is not None:
        context["subject"] = subject

    if to is not None:
        context["to"] = to

    if settings.WEBMAIL_SHOW_CC:
        context["show_cc"] = True
        if cc is not None:
            context["cc"] = cc

    if settings.WEBMAIL_SHOW_BCC:
        context["show_bcc"] = True
        if bcc is not None:
            context["bcc"] = bcc

    if in_reply_to is not None:
        context["in_reply_to"] = in_reply_to

    if body is not None:
        context["body"] = body

    init_page_data["auto_drafts"] = settings.WEBMAIL_AUTODRAFT_ENABLED
    init_page_data["draft_saved_text"] = _("Draft saved!")
    init_page_data["saved_draft_at"] = _("Saved draft at ")

    if settings.WEBMAIL_AUTODRAFT_ENABLED:
        init_page_data["autodraft_save_delay"] = settings.WEBMAIL_AUTODRAFT_SAVE_DELAY

    if settings.WEBMAIL_MAIL_SEND_ENABLED:
        context["send_mail_enabled"] = True

        init_page_data["mail_send_url"] = reverse_webmail_url("mail_send", mailbox=request.current_mailbox)
        init_page_data["message_sent_html"] = render_to_string("webmail/message_sent.html")

    if init_page_data:
        context["init_page_data"] = init_page_data

    return render_webmail_page(request, "webmail/compose.html", "compose", context)


@login_required
@mailbox_view_decorator(required=True)
def compose(request, mailbox):
    if "to" in request.GET:
        to = []

        recipient_list = request.GET["to"].split(",")
        for email in recipient_list:
            try:
                # TODO: Comprobar que esta validacion no sea demasiado flexible
                validators.validate_email(email)
            except ValidationError:
                pass
            else:
                to.append(email)
        to = ",".join(to)   
    else:
        to = None

    return render_compose_page(request, to=to)


@login_required
@mailbox_view_decorator(required=True)
def show_mail_headers(request, mailbox, message_id):
    message = get_message_or_404(mailbox, message_id)

    return render_webmail_page(request, "webmail/email_headers.html", "email_headers", {
        "message_id": message.id,
        "email_headers": message.original_email_headers
    })


@ajax(login_required=True, require_POST=True)
@mailbox_view_decorator(required=True)
def mail_send(request, mailbox):
    try:
        smtp_server = mailbox.smtp_server
    except SmtpServerModel.DoesNotExist:
        raise AJAXError(error_description=_("Not possible to send message because no smtp server configured"), error_code="NoSmtpServerConfigured")

    form = ComposeMailForm(mailbox, request.POST)

    if not form.is_valid():
        raise FormAJAXError(form)

    if form.cleaned_data.get("in_reply_to") is not None:
        try:
           message_in_reply_to = MessageModel.objects.get(mailbox=mailbox, pk=in_reply_to_id)
        except MessageModel.DoesNotExist:
            raise Http404
    else:
        message_in_reply_to = None

    text_plain = form.cleaned_data.get("body", None)

    message = MessageModel(
        mailbox=mailbox,
        subject=form.cleaned_data["subject"],
        from_email=smtp_server.get_from_email_header_value(),
        to=form.cleaned_data["to"],
        cc=form.cleaned_data["cc"],
        bcc=form.cleaned_data["bcc"],
        text_plain=text_plain,
        html=None,
        in_reply_to=message_in_reply_to
    )

    if form.cleaned_data["has_attachments"]:
        message.save()

        upload_session = UploadAttachmentSessionModel.objects.create(message_obj_reference=message)

        attachment_upload_url = reverse_webmail_url("attachment_upload", kwargs={"upload_session_id": upload_session.uuid.hex}, mailbox=mailbox)
        finnished_attachments_session_url = reverse_webmail_url("finnished_attachments_session", kwargs={"upload_session_id": upload_session.uuid.hex}, mailbox=mailbox)

        return {
            "attachment_upload_url": attachment_upload_url,
            "finnished_attachments_session_url": finnished_attachments_session_url
        }

    else:
        message.dispatch()

        message_queued_signal.send(sender=MessageModel, message=message)

        return {
            "message_id": message.id,
        }


class BinaryDataDeserializer:
    # TODO: Mejorar esta parte

    field_format_length = {
        'c': 1,
        'b': 1,
        'B': 1,
        '?': 1,
        'h': 2,
        'H': 2,
        'i': 4,
        'I': 4,
        'l': 4,
        'L': 4,
        'q': 8,
        'Q': 8,
        'f': 4,
        'd': 8
    }

    def __init__(self, serialized_data):
        self.offset = 0
        self.serialized_data = serialized_data

    def is_end(self):
        return len(self.serialized_data) == self.offset

    def check_length(self, length):
        if self.offset + length > len(self.serialized_data):
            raise Exception("Not possible to read %d. Its out of boundaries" % length)

    def read_raw_binary_data(self, length):
        self.check_length(length)

        raw_data = self.serialized_data[self.offset:self.offset+length]
        self.offset += length
        return raw_data

    def read_string_field(self, length, encoding="utf-8"):
        self.check_length(length)

        raw_string = self.read_raw_binary_data(length)

        return raw_string.decode(encoding)
        
    def read_field(self, field_format):
        if len(field_format) == 1:
            if field_format not in self.field_format_length:
                raise Exception("Invalid field format %s"%field_format)

            length = self.field_format_length[field_format]

        elif len(field_format) == 2:
            if field_format[0] not in ["@", "=", "<", ">", "!"] or field_format[1] not in self.field_format_length:
                raise Exception("Invalid field format %s"%field_format)

            length = self.field_format_length[field_format[1]]
        else:
            raise Exception("Invalid field format %s"%field_format)


        self.check_length(length)

        return struct.unpack(field_format, self.read_raw_binary_data(length))[0]


def deserialize_message(serialized_message):
    deserializer = BinaryDataDeserializer(serialized_message)

    subject_length = deserializer.read_field(">B")
    subject = deserializer.read_string_field(subject_length)

    message_content_length = deserializer.read_field(">I")
    message_content = deserializer.read_string_field(message_content_length)

    message_data = {
        "subject": subject,
        "message_content": message_content
    }

    if deserializer.is_end():
        return message_data

    file_attachments = []

    num_attachments = deserializer.read_field(">B")
    for i in range(num_attachments):
        name_length = deserializer.read_field(">B")
        name = deserializer.read_string_field(name_length)

        file_data_length = deserializer.read_field(">I")
        file_data = deserializer.read_raw_binary_data(file_data_length)

        file_attachments.append({
            "name": name,
            "file_data": file_data
        })

    message_data["file_attachments"] = file_attachments

    return message_data


@ajax(login_required=True, require_POST=True)
@mailbox_view_decorator(required=True)
def import_message(request, mailbox, contact_id):
    try:
        contact = ContactModel.objects.get(id=contact_id, user=request.webmail_user)
    except ContactModel.DoesNotExist:
        raise Http404

    serialized_message = request.body

    message_data = deserialize_message(serialized_message)

    message = MessageModel(
        mailbox=mailbox,
        subject=message_data["subject"],
        folder_id=MessageModel.INBOX_FOLDER_ID,
        imported=True,
        from_email=contact.email,
        to=mailbox.from_email,
        text_plain=message_data["message_content"],
        html=None
    )
    message.save()

    if "file_attachments" in message_data:
        for file_attachment in message_data["file_attachments"]:
            attachment_mimetype = mimetypes.guess_type(file_attachment["name"])[0]

            MessageAttachmentModel.objects.create(file=ContentFile(file_attachment["file_data"], file_attachment["name"]), file_name=file_attachment["name"], mimetype=attachment_mimetype, message=message)

    return {
        "message_id": message.id
    }


@login_required
@mailbox_view_decorator(required=True)
def reply(request, mailbox, message_id):
    message = get_message_or_404(mailbox, message_id)

    try:
        contact = ContactModel.objects.get(user=request.webmail_user, email=message.from_email)
    except ContactModel.DoesNotExist:
        sender_name = None
    else:
        sender_name = contact.displayed_name

    subject = "RE: " + message.subject
    to = ",".join(message.to)
    body = format_body_reply(sender_name, message.from_email, message.body)

    return render_compose_page(request, subject=subject, to=to, body=body, in_reply_to=message_id)


@login_required
@mailbox_view_decorator(required=True)
def reply_all(request, mailbox, message_id):
    message = get_message_or_404(mailbox, message_id)

    try:
        sender_name = ContactModel.objects.get(user=request.webmail_user, email=message.from_email)
    except ContactModel.DoesNotExist:
        sender_name = None
    else:
        sender_name = contact.displayed_name

    to = ",".join(message.to)

    if message.cc:
        cc = ",".join(message.cc)
    else:
        cc = None

    subject = "RE: " + message.subject
    body = format_body_reply(sender_name, message.from_email, message.body)

    return render_compose_page(request, subject=subject, to=to, cc=cc, body=body, in_reply_to=message_id)


@login_required
@mailbox_view_decorator(required=True)
def forward_email(request, mailbox, message_id):
    message = get_message_or_404(mailbox, message_id)

    body = FORWARD_MESSAGE_TEMPLATE % {
        "subject": message.subject,
        "date": message.date,
        "from": message.from_email,
        "to": ", ".join(message.to),
        "cc": ", ".join(message.cc)
    }

    return render_compose_page(request, body=body)


#  mimetypes.guess_type(obj.path)

@ajax(login_required=True, require_POST=True)
@mailbox_view_decorator(required=True)
def attachment_upload(request, mailbox, upload_session_id):
    upload_session = get_object_or_404(UploadAttachmentSessionModel, message_obj_reference__mailbox=mailbox, uuid=upload_session_id)

    fobj = request.FILES['attachment']
    if fobj.size > settings.WEBMAIL_MAX_ATTACHMENT_SIZE:
        raise Http404

    file_attachment_uploaded_signal.send(sender=UploadAttachmentSessionModel, request=request, upload_session=upload_session, file_attachment=fobj)
        # Copy the Django attachment (which may be a file or in memory) over to a temp file.

#        # After attached file is placed in a temporary file and ATTACHMENTS_CLAMD is active scan it for viruses:
#        if getattr(settings, 'ATTACHMENTS_CLAMD', False):
#            import pyclamd
#            cd = pyclamd.ClamdUnixSocket()
#            virus = cd.scan_file(path)
#            if virus is not None:
#                # if ATTACHMENTS_QUARANTINE_PATH is set, move the offending file to the quaranine, otherwise delete
#                if getattr(settings, 'ATTACHMENTS_QUARANTINE_PATH', False):
#                    quarantine_path = os.path.join(getattr(settings, 'ATTACHMENTS_QUARANTINE_PATH'), os.path.basename(path))
#                    os.rename(path, quarantine_path)
#                else:
#                    os.remove(path)
#                raise VirusFoundException('**WARNING** virus %s found in the file %s, could not upload!' % (virus[path][1], fobj.name))
    attachment_mimetype = mimetypes.guess_type(fobj.name)[0]

    try:
        message_attachment = MessageAttachmentModel.objects.create(file=fobj, file_name=fobj.name, mimetype=attachment_mimetype, message=upload_session.message_obj_reference)

#    except VirusFoundException as ex:
#        logger.exception(str(ex))
#        return JsonAJAXError('virus_found', force_text(ex))
    except Exception as exc:
        logger.exception('Error attaching file to session %s', upload_session_id)
        raise AJAXError('upload_attachment_error', "Error uploading attachment", error_data={"exception":force_text(exc)})


@ajax(login_required=True, require_POST=True)
@mailbox_view_decorator(required=True)
def attachment_delete(request):
    pass


@ajax(login_required=True, require_POST=True)
@mailbox_view_decorator(required=True)
def cancel_attachments_session(request, mailbox, upload_session_id):
    upload_session = get_object_or_404(UploadAttachmentSessionModel, message_obj_reference__mailbox=mailbox, uuid=upload_session_id)
    upload_session.delete()

    return {
        "upload_session_id": upload_session_id
    }


@ajax(login_required=True)
@mailbox_view_decorator(required=True)
def finnished_attachments_session(request, mailbox, upload_session_id):
    user = request.webmail_user

    upload_session = get_object_or_404(UploadAttachmentSessionModel, message_obj_reference__mailbox=mailbox, uuid=upload_session_id)

    attachments_uploaded_signal.send(sender=UploadAttachmentSessionModel, upload_session=upload_session)

    message = upload_session.message_obj_reference
    message.dispatch()

    message_queued_signal.send(sender=MessageModel, message=message)

    upload_session.delete()

    free_space = calculate_free_space(user)

    return {        
        "free_space": free_space,
        "message_id": message.id
    }


#    contact = Contact.objects.get(pk=pk)
#    output = vcard(contact).output_string()
#    filename = "contact_%s%s.vcf" % (contact.first_name, contact.last_name)
#    response = HttpResponse(output, content_type="text/x-vCard")
#    response['Content-Disposition'] = 'attachment; filename=%s' % filename
#    return response

# download_attachment

@login_required
@mailbox_view_decorator(required=True)
@gzip_page
def get_attachment(request, mailbox, message_id, attachment_id):
    """Fetch a message attachment"""
    # Mirarme: django-file-upload-download

    try:
        attachment = MessageAttachmentModel.objects.get(message=message_id, message__mailbox=mailbox, pk=attachment_id)
    except MessageAttachmentModel.DoesNotExist:
        raise Http404

    attachment_downloaded_signal.send(sender=MessageAttachmentModel, attachment=attachment)

    fd = attachment.file.open().file

    try:
        response = FileResponse(fd, as_attachment=True, filename=attachment.file_name)
        return response
    except Exception:
        raise Http404


@ajax(login_required=True)
@mailbox_view_decorator(required=True)
def attachment_list(request, mailbox, message_id):
    attachment_objs = MessageAttachmentModel.objects.filter(message=message_id, message__mailbox=mailbox)

    attachment_list = []
    for attachment_obj in attachment_objs:
        attachment_list.append({
            "filename": attachment_obj.file.name, 
            "url": attachment_obj.file.url,
            "mimetype": attachment_obj.mimetype,
            "size": filesizeformat(attachment_obj.file.size)
        })

    return {
        "attachment_list": attachment_list
    }


@login_required
@mailbox_view_decorator(required=True)
def read_mail(request, mailbox, message_id):
    # TODO: Comprobar si esta en contact 
    message = get_message_or_404(mailbox, message_id)
    message.mark_as_read()

    if message.from_me:
        sender = {
            "me": True
        }
    else:
        try:
            contact = ContactModel.objects.get(user=request.webmail_user, email=message.from_email)
        except ContactModel.DoesNotExist:
            sender_name = None
        else:
            sender_name = contact.displayed_name

        sender = {
            "address": message.from_email,
            "name": sender_name
        }

    my_email = message.to_me_email

    receivers = []
    for receiver_email in message.to:
        if receiver_email == my_email:
            receiver = {
                "me": True
            }
            receivers.insert(0, receiver)
        else:
            try:
                contact = ContactModel.objects.get(user=request.webmail_user, email=receiver_email)
            except ContactModel.DoesNotExist:
                receiver_name = None
            else:
                receiver_name = contact.displayed_name

            receiver = {
                "address": receiver_email,
                "name": receiver_name
            }

            receivers.append(receiver)

    if message.cc:
        secondary_receivers = []

        for receiver_email in message.cc:
            if receiver_email == my_email:
                receiver = {
                    "me": True
                }
                secondary_receivers.insert(0, receiver)
            else:
                try:
                    receiver_name = ContactModel.objects.get(user=request.webmail_user, email=receiver_email)
                except ContactModel.DoesNotExist:
                    receiver_name = None
                else:
                    receiver_name = contact.displayed_name

                receiver = {
                    "address": receiver_email,
                    "name": receiver_name
                }

                secondary_receivers.append(receiver)
    else:
        secondary_receivers = None

    folder_name = message.get_folder_name()

    back_page_url = get_folder_url(mailbox, folder_name)
    if "read" in request.GET and request.GET["read"] in ("0", "1"):
        back_page_url += "&read=" + request.GET["read"]

    if "starred" in request.GET and request.GET["starred"] in ("0", "1"):
        back_page_url += "&starred=" + request.GET["starred"]

    if "has_attachments" in request.GET and request.GET["has_attachments"] in ("0", "1"):
        back_page_url += "&has_attachments=" + request.GET["has_attachments"]

    return render_webmail_page(request, "webmail/message.html", "message", {
        "active_folder": folder_name,
        "message": message,
        "sender": sender,
        "receivers": receivers,
        "secondary_receivers": secondary_receivers,
        "back_page_url": back_page_url,
        "show_export_mail_btn": settings.WEBMAIL_EXPORT_MAIL_ENABLED,
        "show_email_headers_btn": settings.WEBMAIL_SHOW_EMAIL_HEADERS_BTN
    })

#    if message.attachments:
#        attachment_list = []
#        for attachment_obj in message.attachments:
#            attachment_list.append({
#                "filename": attachment_obj.file.name, 
#                "url": attachment_obj.file.url,
#                "mimetype": attachment_obj.mimetype,
#                "size": filesizeformat(attachment_obj.file.size)
#            })
#    else:
#        attachment_list = None

#    return {
#        "id": message.id,
#        "message_id": message.message_id,
#        "subject": message.subject,
#        "to": message.to,
#        "cc": message.cc,
#        "bcc": message.bcc,
#        "text_plain": message.text_plain,
#        "html": message.html,
#        "from_email": message.from_email,
#        "is_starred": message.is_starred,
#        "attachment_list": attachment_list
#    }


class ContactEditViewMixin:
    object_name ="contact"            
    form_class = ContactForm
    back_url_text = _("Back to contact list")

    def get_back_url(self):
        return self.reverse_url("contacts")

    def get_success_url(self):
        return self.reverse_url("contact_edit", contact_id=self.object.id)

    def form_valid(self, form):
        dispatch_hook("before_contact_form_valid", form)
        response = super().form_valid(form)

        dispatch_hook("contact_form_valid", form)

        return response

    def form_invalid(self, form):
        dispatch_hook("before_contact_form_invalid", form)
        response = super().form_invalid(form)
        dispatch_hook("contact_form_invalid", form)

        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["extra_form_classes"] = dispatch_hook("extra_contact_form_classes", [])

        return kwargs

    def get_initial(self):
        initial = dispatch_hook("initial_contact_form_data", {}, contact_instance=self.object)
        if initial:
            return initial


class ContactCreateView(ContactEditViewMixin, WebmailCreateView):
    success_message = _('Contact created!')
    page_title = _("Add contact")

    def dispatch(self, *args, **kwargs):
        try:
            return super().dispatch(*args, **kwargs)
        except IntegrityError:
            admin_messages.error(self.request, _('Contact already exists!'))

            return redirect("contacts", mailbox=self.mailbox)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.webmail_user

        return kwargs

    def get_action_url(self):
        return self.reverse_url("contact_add")


class ContactUpdateView(ContactEditViewMixin, WebmailUpdateView):
    page_title = _("Edit contact")
    success_message = _('Contact updated successfully!')

    def get_object(self):
        contact_id = self.kwargs["contact_id"]

        try:
            return ContactModel.objects.get(id=contact_id, user=self.request.webmail_user)
        except ContactModel.DoesNotExist:
            raise Http404

    def get_action_url(self):
        return self.reverse_url("contact_edit", contact_id=self.object.id)

    def get_delete_url(self):
        return self.reverse_url("contact_delete", contact_id=self.object.id)


class ContactDeleteView(WebmailDeleteView):
    def get_success_url(self):
        return self.reverse_url("contacts")

    def get_object(self):
        contact_id = self.kwargs["contact_id"]

        try:
            return ContactModel.objects.get(id=contact_id, user=self.request.webmail_user)
        except ContactModel.DoesNotExist:
            raise Http404

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)

        contact_id = self.kwargs["contact_id"]
        admin_messages.success(request, mark_safe(_('Contact <b>%s</b> called <b>%s</b> deleted!') % (contact_id, self.object.displayed_name)))


        return response


class ContactListView(WebmailListView):
    model = ContactModel

    title = _("List of contacts")
    object_name = "contact"

    columns = [
        {
        "name": "displayed_name",
        "label": _("Name")
        },
        {
        "name": "email",
        "label": _("Email")
        }
    ]

    back_url_text = _("Back to inbox")

    def get_back_url(self):
        if self.mailbox is not None:
            return get_folder_url(self.mailbox, folder_name="inbox")

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.webmail_user)

    def get_table_row_data(self, obj):
        return {"displayed_name": obj.displayed_name, "email": obj.email}


CONTACT_ACTION_SUCCESS_MESSAGE = {
    "delete": _("<b>{num_contacts}</b> contact/s deleted.")
}

@require_POST
@login_required
@mailbox_view_decorator
def contacts_bulk_action(request):
    form = ContactActionForm(user=request.webmail_user, data=request.POST)
    
    if form.is_valid():
        if form.cleaned_data["obj_list"] is None:
            admin_messages.error(request, _("No contact selected"))
        else:
            form.apply_action()

            action_name = form.cleaned_data["action_name"]
            message_template = CONTACT_ACTION_SUCCESS_MESSAGE[action_name]
            message = message_template.format(num_contacts=form.get_obj_list_length())
            admin_messages.success(request, mark_safe(message))
    else:
        # TODO: Specify error
        logger.debug("Error processing contact bulk action", form.errors)
        admin_messages.error(request, _("There was an error processing the action"))

    return redirect("contacts", mailbox=request.current_mailbox)


def serialize_hex(n):
    return hex(n)[2:]


class InvalidAuthentication(Exception):
    pass


class SRP_Authentication:
    def __init__(self, post_data, session, session_prefix="", user=None, exception_class=InvalidAuthentication):
        self.post_data = post_data
        self.session = session
        self.session_prefix = session_prefix
        self.user = user

        self.exception_class = exception_class

        self.session_key = None

    def step1(self):
        """SRP challenge"""

        try:
            if self.user is None:
                if "I" not in self.post_data:
                    raise self.exception_class("Parameter I not in POST")

                username = self.post_data["I"]

                try:
                    user = WebmailUserModel.objects.get(username=username)
                # We don't want to leak that the username doesn't exist. Make up a fake salt and verifier.
                except WebmailUserModel.DoesNotExist:
                   raise self.exception_class()

            else:
                user = self.user
                username = user.username

            if "A" not in self.post_data:
                raise self.exception_class("Parameter A not in post data")

            try:
                A = int(self.post_data["A"], 16)
            except ValueError:
                raise self.exception_class("Parameter A is not hexadecimal")

            srp_group = user.srp_group
            g, N = gN[srp_group]

            salt = user.salt

            v = int(user.verifier, 16)

            verifier = SRP_Verifier()
            B = verifier.get_challenge(username, salt, v, A)

            if B is None:
                raise self.exception_class()
        except self.exception_class:
            self._clean_session()

            raise

        if self.user is None:
            self.session[self.session_prefix + "srp_I"] = username
            self.user = user

        self.session[self.session_prefix + "srp_M"] = verifier.M.hex()
        self.session[self.session_prefix + "srp_H_AMK"] = verifier.H_AMK.hex()

        self.session[self.session_prefix + "session_key"] = verifier.session_key.hex()

        return {
            "B": serialize_hex(B),
            "s": salt
        }

    def step2(self):
        """Verify proof"""
        try:
            if self.session_prefix + "srp_M" not in self.session or self.session_prefix + "srp_H_AMK" not in self.session or self.session_prefix + "session_key" not in self.session:
                raise self.exception_class("Required parameters for SRP not saved in session")

            if self.user is None:
                if self.session_prefix + "srp_I" not in self.session:
                    raise self.exception_class("Required parameters for SRP not saved in session")

                username = self.session[self.session_prefix + "srp_I"]

                try:
                    user = WebmailUserModel.objects.get(username=username)
                # We don't want to leak that the username doesn't exist. Make up a fake salt and verifier.
                except WebmailUserModel.DoesNotExist:
                   raise self.exception_class()
                else:
                    self.user = user
            else:
                username = self.user.username

            if "M" not in self.post_data:
                raise self.exception_class("Parameter M not in Post")

            usr_M = self.post_data["M"]

            if self.session[self.session_prefix + "srp_M"] != usr_M:
                raise self.exception_class()

        except self.exception_class:
            self._clean_session()

            raise

        H_AMK = self.session[self.session_prefix + "srp_H_AMK"]

        self.session_key = self.session[self.session_prefix + "session_key"]

        self._clean_session()

        return {
            "H_AMK": H_AMK
        }

    def _clean_session(self):
        if self.session_prefix + "srp_I" in self.session:
            del self.session[self.session_prefix + "srp_I"]

        if self.session_prefix + "srp_M" in self.session:
            del self.session[self.session_prefix + "srp_M"]

        if self.session_prefix + "srp_H_AMK" in self.session:
            del self.session[self.session_prefix + "srp_H_AMK"]
 
        if self.session_prefix + "session_key" in self.session:
            del self.session[self.session_prefix + "session_key"]


class InvalidAuthenticationAjaxError(AJAXError):
    pass

class InvalidPasswordAjaxError(InvalidAuthenticationAjaxError):
    error_code = "invalid_password"
    error_description = "Password not valid!"


class ProfileView(WebmailTemplateView):
    page_name ="profile"
    template_name = "webmail/profile.html"

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = _("Profile")
        kwargs["after_form_buttons"] = "<a style='margin-left: 10px' href='" + self.reverse_url('change_password') +  "'>" + _("Change password") + "</a>"
        kwargs["object_name"] = 'profile'
        kwargs["form_id"] = "profile_form"
        kwargs["form"] = UsernameForm(instance=self.request.webmail_user)

        if self.mailbox is not None:
            kwargs["back_url"] = get_folder_url(self.mailbox, folder_name="inbox")

        return super().get_context_data(**kwargs)


@login_required
@ajax(require_POST=True)
def change_username_step1(request):
    user = request.webmail_user

    srp_info_form = SRPUserInfoForm(request.POST)

    if not srp_info_form.is_valid():
        raise FormAJAXError(srp_info_form)


    username_form = UsernameForm(request.POST, instance=WebmailUserModel(username=user.username))

    if not username_form.is_valid():
        raise FormAJAXError(username_form)

    authentication = SRP_Authentication(request.POST, request.webmail_session, user=user, session_prefix="change_username_", exception_class=InvalidPasswordAjaxError)
    response = authentication.step1()

    request.webmail_session["new_username"] = username_form.cleaned_data["username"]
    request.webmail_session["verifier"] = srp_info_form.cleaned_data["verifier"]
    request.webmail_session["salt"] = srp_info_form.cleaned_data["salt"]
    request.webmail_session["srp_group"] = srp_info_form.cleaned_data["srp_group"]

    return response


@login_required
@ajax(require_POST=True)  
def change_username_step2(request):
    for parameter_name in ("new_username", "verifier", "salt", "srp_group"):
        if parameter_name not in request.webmail_session:
            raise AjaxError("'%s' parameter not in session" % parameter_name)

    user = request.webmail_user

    authentication = SRP_Authentication(request.POST, request.webmail_session, user=user, session_prefix="change_username_", exception_class=InvalidPasswordAjaxError)

    response = authentication.step2()

    username = request.webmail_session["new_username"]

    user.username = username
    user.verifier = request.webmail_session["verifier"]
    user.salt = request.webmail_session["salt"]
    user.srp_group = request.webmail_session["srp_group"]
    user.save(update_fields=("username", "verifier", "salt", "srp_group"))

    update_session_auth_hash(request, user)
    admin_messages.success(request, mark_safe(_('Username changed successfully to <b>%s</b>!') % username))

    return response


class ChangePasswordView(WebmailTemplateView):
    page_name = "change_password"
    template_name = "webmail/change_password.html"


@login_required
@ajax(require_POST=True)
def change_password_step1(request):
    form = SRPUserInfoForm(request.POST)

    if not form.is_valid():
        raise FormAJAXError(form)

    user = request.webmail_user

    authentication = SRP_Authentication(request.POST, request.webmail_session, user=user, session_prefix="change_password_", exception_class=InvalidPasswordAjaxError)
    response = authentication.step1()

    request.webmail_session["verifier"] = form.cleaned_data["verifier"]
    request.webmail_session["salt"] = form.cleaned_data["salt"]
    request.webmail_session["srp_group"] = form.cleaned_data["srp_group"]

    return response

@login_required
@ajax(require_POST=True)  
def change_password_step2(request):
    for parameter_name in ("verifier", "salt", "srp_group"):
        if parameter_name not in request.webmail_session:
            raise AjaxError("'%s' parameter not in session" % parameter_name)

    user = request.webmail_user

    authentication = SRP_Authentication(request.POST, request.webmail_session, user=user, session_prefix="change_password_", exception_class=InvalidPasswordAjaxError)

    response = authentication.step2()

    user.verifier = request.webmail_session["verifier"]
    user.salt = request.webmail_session["salt"]
    user.srp_group = request.webmail_session["srp_group"]
    user.save(update_fields=("verifier", "salt", "srp_group"))

    update_session_auth_hash(request, user)
    admin_messages.success(request, _('Password changed successfully!'))

    request.webmail_session["session_key"] = authentication.session_key

    del request.webmail_session["verifier"]
    del request.webmail_session["salt"]
    del request.webmail_session["srp_group"]

    return response


@require_GET
def signup(request):
    context = {}

    context["html_head_title"] = settings.WEBMAIL_SIGNUP_HTML_HEAD_TITLE
    context["logo_alt"] = settings.WEBMAIL_SIGNUP_LOGO_ALT
    context["logo_image_url"] = settings.WEBMAIL_SIGNUP_LOGO_IMAGE_URL
    context["logo_width"] = settings.WEBMAIL_SIGNUP_LOGO_WIDTH
    context["logo_height"] = settings.WEBMAIL_SIGNUP_LOGO_HEIGHT
    context["title"] = settings.WEBMAIL_SIGNUP_TITLE
    context["background_color"] = settings.WEBMAIL_SIGNUP_BACKGROUND_COLOR

    return render(request, "webmail/signup.html", context)


@ajax(require_POST=True)
def signup_upload_srp_params(request):
    form = SignUpForm(request.POST)
    if form.is_valid():
        form.save()
    else:
        raise FormAJAXError(form)

# user_login_failed_signal.send(sender=__name__, request=request)

class InvalidLoginAjaxError(AJAXError):
    error_code = "invalid_login"
    error_description = "Invalid login!"


@ajax(require_POST=True)
def login_srp_challenge(request):
    authentication = SRP_Authentication(request.POST, request.webmail_session, exception_class=InvalidLoginAjaxError)
    return authentication.step1()

# Step 2: The client sends its proof of S. The server confirms, and sends its proof of S.
@ajax(require_POST=True)  
def login_srp_verify_proof(request):
    authentication = SRP_Authentication(request.POST, request.webmail_session, exception_class=InvalidLoginAjaxError)
    response = authentication.step2()

    auth_login(request, authentication.user)

    return response


@ajax(login_required=True, require_POST=True)
def partial_template(request):
    if "template_name" in request.POST:
        template_name = request.POST["template_name"]
    else:
        raise AJAXError("Missing template name")

    if "context" in request.POST:
        context = request.POST["context"]

        try:
            context = json.loads(context)
        except ValueError:
            raise AJAXError("Context is not json serializable")
    else:
        context = None

    try:
        html = render_to_string(template_name, context)
    except TemplateDoesNotExist:
        raise AJAXError("Template does not exist: " + template_name)

    return {
        "html": html
    }


@login_required
@require_GET
@mailbox_view_decorator(required=True)
def export_mail(request, mailbox, message_id):
    message = get_message_or_404(mailbox, message_id)

    eml_file_bytes = message.email_message.message().as_bytes(linesep='\r\n')

    fd = io.BytesIO(eml_file_bytes)

    mail_file_name = "email_%s.bin" % int(time.time())
    response = FileResponse(fd, as_attachment=True, filename=mail_file_name)
    return response


@login_required
@mailbox_view_decorator(required=True)
def import_mail(request, mailbox):
    if request.method == "POST":
        if "eml" in request.FILES:
            fobj = request.FILES['eml']
            eml_bytestring = fobj.read()

            # TODO: Improve validation
            email_message = email.message_from_bytes(eml_bytestring, policy=EmailPolicy())
            try:
                msg = mailbox.import_email(email_message)
            except InvalidEmailMessageException:
                return render_webmail_page(request, "webmail/import_mail.html", "export_mail", {
                    "form_errors": {
                        "eml": _("Invalid .eml file!")
                    }
                })
            admin_messages.success(request, mark_safe(_("Mail <b>%s</b> imported successfully") % msg.id))

            return redirect("read_mail", mailbox=mailbox, kwargs={"message_id": msg.id})
        else:
            return render_webmail_page(request, "webmail/import_mail.html", "export_mail", {
                "form_errors": {
                    "eml": _("No .eml file uploaded")
                }
            })
    else:
        return render_webmail_page(request, "webmail/import_mail.html", "export_mail")

