from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from django.urls import reverse as reverse_url
from django.db.models import OuterRef, Subquery


from webmail.models import WebmailUserModel, AccessLogModel, ContactModel, MailboxModel, Pop3MailServerModel, SmtpServerModel, TagModel, MessageModel, MessageAttachmentModel, UploadAttachmentSessionModel, SendMailTaskModel, SendMailTaskLogModel



class MailboxModelAdmin(admin.ModelAdmin):
    list_per_page = 10
    list_display = ('id', 'name', 'user', 'is_default', 'emails', 'created_at')
    list_filter = ('is_default', )

    readonly_fields = ('user', 'name', 'is_default', 'emails', 'created_at')
    search_fields = ('user', 'name')

    def has_add_permission(self, request, obj=None):
        return False


class Pop3MailServerModelAdmin(admin.ModelAdmin):
    list_per_page = 10
    list_display = ('id', 'mailbox', 'active', 'username', 'password', 'ip_address', 'port', 'use_ssl', 'last_polling')
    readonly_fields = ('mailbox', 'active', 'username', 'password', 'ip_address', 'port', 'use_ssl', 'last_polling',)

    def has_add_permission(self, request, obj=None):
        return False


class SmtpServerModelAdmin(admin.ModelAdmin):
    list_per_page = 10
    list_display = ('id', 'mailbox', 'ip_address', 'port', 'username', 'password', 'use_tls', 'use_ssl', 'from_email', 'from_name',)
    readonly_fields = ('mailbox', 'ip_address', 'port', 'username', 'password', 'use_tls', 'use_ssl', 'from_email', 'from_name')

    def from_email_header(self, instance):
        return instance.get_from_email_header_value()
    from_email_header.short_description = 'Email'

    def has_add_permission(self, request, obj=None):
        return False


class ContactModelAdmin(admin.ModelAdmin):
    list_per_page = 10
    list_display = ('id', 'get_user_filter_url', 'displayed_name', 'email',)
    readonly_fields = ('user', 'displayed_name', 'email')


    def get_user_filter_url(self, instance):
        return mark_safe("<a href='?user=%s'>%s</a>" % (instance.user.id, instance.user.username))

    get_user_filter_url.short_description = "User"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "user" in request.GET:
            try:
                user_id = int(request.GET["user"])
            except ValueError:
                pass
            else:
                qs.filter(user__id=user_id)

        return qs

    def has_add_permission(self, request, obj=None):
        return False


class MessageAttachmentInline(admin.StackedInline):
    model = MessageAttachmentModel
    fields = ('file_name', 'mimetype', 'file')
    readonly_fields = ('file_name', 'mimetype', 'file')
    extra = 0
    max_num = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class MessageModelAdmin(admin.ModelAdmin):
    # TODO: Facilitar un filtro por mailbox
    list_per_page = 10
#    fields = (
#        ('from_email', 'date', 'folder', 'tags'),
#        ('to', 'cc', 'bcc'),
#        'subject', 'body',)
    list_display = ('id', 'get_mailbox_filter_url', 'folder', 'subject', 'to', 'in_reply_to', 'from_me', 'to_me', 'imported', 'is_starred_header', 'attachment_count', 'date',)
    readonly_fields = ['id', 'mailbox', 'folder_id', 'from_email', 'date',  'message_id', 'in_reply_to', 'imported', 'is_starred', 'tags',  'subject', 'to', 'cc', 'bcc', 'to_me', 'to_me_email', 'text_plain', 'html', 'read_at',]
    list_filter = ('folder_id', 'from_me', 'to_me', 'is_starred', 'imported')
    search_fields = ('mailbox', 'from_email', 'to', 'cc', 'bcc', 'subject')
    date_hierarchy = 'date'
    inlines = (MessageAttachmentInline,)

    def get_mailbox_filter_url(self, instance):
        return mark_safe("<a href='?mailbox=%s'>%s</a>" % (instance.mailbox.id, instance.mailbox.name))

    get_mailbox_filter_url.short_description = "Mailbox"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "mailbox" in request.GET:
            try:
                mailbox_id = int(request.GET["mailbox"])
            except ValueError:
                pass
            else:
                qs.filter(mailbox__id=mailbox_id)

        return qs

    def has_add_permission(self, request, obj=None):
        return False

    def attachment_count(self, instance):
        return instance.attachments.count()
    attachment_count.short_description = 'Num. Attachments'

    def is_starred_header(self, instance):
        return instance.is_starred
    is_starred_header.short_description = "starred"
    is_starred_header.boolean = True


class MessageAttachmentModelAdmin(admin.ModelAdmin):
    list_display = ('message_url', 'file_name', 'mimetype')
    list_filter = ('mimetype',)

    def message_url(self, instance):
        message = instance.message
        message_id = message.id

        message_url = reverse_url('admin:{}_{}_change'.format(instance._meta.app_label, message._meta.model_name), args=(message_id,))

        return mark_safe("<a href='%s'>%s</a>" % (message_url, message_id))
    message_url.short_description = "Message"

    def has_add_permission(self, request, obj=None):
        return False


class TagModelAdmin(admin.ModelAdmin):
    list_display = ('name',)

    def has_add_permission(self, request, obj=None):
        return False


class UploadAttachmentSessionModelAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False

class WebmailUserModelAdmin(admin.ModelAdmin):
    list_per_page = 10
    list_display = ["username", "displayed_name", "last_time_password_changed", "is_2fa_enabled", "last_login", "is_active", "date_created"]
    readonly_fields = ["username", "displayed_name", "is_active", "is_2fa_enabled", "last_login", "last_time_password_changed"]
    date_hierarchy = "date_created"

    exclude = ["srp_group", "verifier", "salt"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        access_log_subquery = AccessLogModel.objects.filter(user=OuterRef('pk')).order_by('date')
        queryset = queryset.annotate(last_login=Subquery(access_log_subquery.values('date')[:1]))

        return queryset

    def has_add_permission(self, request, obj=None):
        return False

    def last_login(self, obj):
        return obj.last_login

    last_login.short_description = 'Last login'


class SendMailTaskModelAdmin(admin.ModelAdmin):
    list_per_page = 10
    list_display = ["id", "priority", "status", "created_at","num_deferred_times", "scheduled_time", "last_sent_at",  "show_logs"]
    readonly_fields = ["priority", "status", "created_at","num_deferred_times", "scheduled_time", "last_sent_at"]
    date_hierarchy = "created_at"
    list_filter = ("priority", "status",)

#    def show_to(self, instance):
#        return ", ".join(instance.email_recipients)
#    show_to.short_description = "To"  # noqa: E305

#    def plain_text_body(self, instance):
#        email_message = instance.email_message

#        if hasattr(email_message, 'body'):
#            return email_message.body
#        else:
#            return "<Can't decode>"

    def has_add_permission(self, request, obj=None):
        return False

    def show_logs(self, instance):
        url = reverse_url('admin:%s_sendmailtasklogmodel_changelist' % self.model._meta.app_label)

        return mark_safe("<a href='%s?task=%s'>Show logs</a>" % (url, instance.id))


class SendMailTaskLogModelAdmin(admin.ModelAdmin):
    list_per_page = 10
    list_display = ["id", "get_task_url", "success", "email", "sent_at", "exception_type", "exception_message"]
    list_filter = ["task", "success", "exception_type"]
    date_hierarchy = "sent_at"
    readonly_fields = ["task", "success", "email", "sent_at", "exception_type", "exception_message", "py_traceback"]

    search_fields = ['task', "exception_type", "exception_message"]

    def has_add_permission(self, request, obj=None):
        return False

    def get_task_url(self, instance):
        task_id = instance.task.id

        change_task_url = reverse_url('admin:{}_{}_change'.format(instance._meta.app_label, instance._meta.model_name), args=(task_id,))

        return mark_safe("<a href='%s'>%s</a>" % (change_task_url, task_id))
    get_task_url.short_description = 'Task'


admin.site.register(WebmailUserModel, WebmailUserModelAdmin)
admin.site.register(ContactModel, ContactModelAdmin)
admin.site.register(MailboxModel, MailboxModelAdmin)
admin.site.register(Pop3MailServerModel, Pop3MailServerModelAdmin)
admin.site.register(SmtpServerModel, SmtpServerModelAdmin)
admin.site.register(TagModel, TagModelAdmin)
admin.site.register(MessageModel, MessageModelAdmin)
admin.site.register(MessageAttachmentModel, MessageAttachmentModelAdmin)
admin.site.register(UploadAttachmentSessionModel, UploadAttachmentSessionModelAdmin)
admin.site.register(SendMailTaskModel, SendMailTaskModelAdmin)
admin.site.register(SendMailTaskLogModel, SendMailTaskLogModelAdmin)
admin.site.register(AccessLogModel)

admin.site.site_header = "Webmail Admin"
admin.site.site_title = "Webmail Admin Portal"
admin.site.index_title = "Welcome to Webmail Admin Portal"

