from django.urls import path, include


from . import views, settings
from .webmail_url_utils import mailbox_url


app_name = 'webmail'


urlpatterns = [
    path('', views.login, name="login"),
    path('login-srp-challenge', views.login_srp_challenge, name="login_srp_challenge"),
    path('login-srp-verify-proof', views.login_srp_verify_proof, name="login_srp_verify_proof"),
]

if settings.WEBMAIL_ENABLE_DEMO_REGISTRATION_PAGE:
    urlpatterns.extend([
        path('signup', views.signup, name="signup"),
        path('signup-upload-srp-params', views.signup_upload_srp_params, name="signup_upload_srp_params"),
    ])

if settings.WEBMAIL_AUTOLOGIN_ENABLED:
    urlpatterns.append(path('auto-login/<username>/', views.autologin, name="autologin"))

urlpatterns.extend([
    path('partial-template/', views.partial_template, name="partial_template"),
    path('mail/logout/', views.logout, name="logout"),
    path('mail/', views.init, name="init"),
    path('mail/user-profile/', views.ProfileView.as_view(), name="profile"),
    path('mail/user-profile/change-username-step1/', views.change_username_step1, name="change_username_step1"),
    path('mail/user-profile/change-username-step2/', views.change_username_step2, name="change_username_step2"),
    path('mail/user-profile/change-password/', views.ChangePasswordView.as_view(), name="change_password"),
    path('mail/user-profile/change-password/step1/', views.change_password_step1, name="change_password_step1"),
    path('mail/user-profile/change-password/step2/', views.change_password_step2, name="change_password_step2"),
    path('mail/contacts/', views.ContactListView.as_view(), name="contacts"),
    path('mail/contacts/action/', views.contacts_bulk_action, name="contacts_bulk_action"),
    path('mail/contacts/add/', views.ContactCreateView.as_view(), name="contact_add"),
    path('mail/contacts/<int:contact_id>/edit/', views.ContactUpdateView.as_view(), name="contact_edit"),
    path('mail/contacts/<int:contact_id>/delete/', views.ContactDeleteView.as_view(), name="contact_delete"),
    mailbox_url('folder/<folder_name>/', views.show_folder, name='show_folder'),
    mailbox_url('folder/<folder_name>/action/', views.mails_bulk_action, name="mails_bulk_action"),
    mailbox_url('import-message/<int:contact_id>/', views.import_message, name='import_message'),
    mailbox_url('compose/', views.compose, name='compose'),
    mailbox_url('send/', views.mail_send, name='mail_send'),
    mailbox_url('empty-trash/', views.empty_trash, name="empty_trash"),
    mailbox_url('delete-all-spam/', views.delete_all_spam, name="delete_all_spam"),
    #path('mail/mailboxes/<int:mailbox_id>/send/<upload_session_id>/attachments/', views.session_attachments, name='list_session_attachments'),
    mailbox_url('send/<upload_session_id>/upload-attachment/', views.attachment_upload, name='attachment_upload'),
    mailbox_url('send/<upload_session_id>/delete-attachment/<int:attachment_id>/', views.attachment_delete, name='attachment_delete'),
    mailbox_url('send/<upload_session_id>/finnished/', views.finnished_attachments_session, name='finnished_attachments_session'),
    mailbox_url('send/<upload_session_id>/cancel/', views.cancel_attachments_session, name='cancel_attachments_session'),
    mailbox_url('message/<int:message_id>/', views.read_mail, name='read_mail'),
    mailbox_url('message/<int:message_id>/headers/', views.show_mail_headers, name='email_headers'),
    mailbox_url('message/<int:message_id>/reply/', views.reply, name='reply'),
    mailbox_url('message/<int:message_id>/reply-all/', views.reply_all, name='reply_all'),
    mailbox_url('message/<int:message_id>/forward/', views.forward_email, name='forward_email'),
    mailbox_url('message/<int:message_id>/delete/', views.mail_delete, name='mail_delete'),
    mailbox_url('message/<int:message_id>/mark-read/', views.mark_as_read, name="mark_as_read"),
    mailbox_url('message/<int:message_id>/mark-unread/', views.mark_as_unread, name="mark_as_unread"),
    mailbox_url('message/<int:message_id>/mark-as-spam/', views.mark_as_spam, name="mark_as_spam"),
    mailbox_url('message/<int:message_id>/mark-as-not-junk/', views.mark_as_not_junk, name="mark_as_not_junk"),
    mailbox_url('message/<int:message_id>/star/', views.add_star, name="add_star"),
    mailbox_url('message/<int:message_id>/unstar/', views.remove_star, name="remove_star"),
    mailbox_url('message/<int:message_id>/attachments/', views.attachment_list, name="attachment_list"),
    mailbox_url('message/<int:message_id>/attachments/<int:attachment_id>/', views.get_attachment, name="get_attachment"),
    mailbox_url('message/<int:message_id>/move_to/<folder_name>/', views.move_to_folder, name="move_to_folder"),

])

if settings.WEBMAIL_EXPORT_MAIL_ENABLED:
    urlpatterns.append(
        mailbox_url('message/<int:message_id>/export/', views.export_mail, name='export_mail'), 
    )


if settings.WEBMAIL_IMPORT_MAIL_ENABLED:
    urlpatterns.append(
        mailbox_url('import/', views.import_mail, name='import_mail'), 
    )


if settings.WEBMAIL_ENABLE_ACCESS_LOGS:
    urlpatterns.append(
        path('mail/access_logs/', views.AccessLogsListView.as_view(), name="access_logs"),
    )

if settings.WEBMAIL_ENABLE_MANAGE_MAILBOXES:
    urlpatterns.extend([
        path('mail/mailboxes/', views.MailboxListView.as_view(), name="mailboxes"),
        path('mail/mailboxes/action/', views.mailboxes_bulk_action, name="mailboxes_bulk_action"),
        path('mail/mailboxes/add/', views.MailboxCreateView.as_view(), name="mailbox_add"),
        path('mail/mailboxes/<int:mailbox_id>/edit/', views.MailboxUpdateView.as_view(), name="mailbox_edit"),
        path('mail/mailboxes/<int:mailbox_id>/delete/', views.MailboxDeleteView.as_view(), name="mailbox_delete")
     ])


    if settings.WEBMAIL_ENABLE_MANAGE_POP3_MAIL_SERVER:
        urlpatterns.extend([
            path('mail/mailboxes/<int:mailbox_id>/pop3server/', views.Pop3MailServerCreateView.as_view(), name="pop3_mail_server_add"),
            path('mail/mailboxes/<int:mailbox_id>/pop3server/edit/', views.Pop3MailServerUpdateView.as_view(), name="pop3_mail_server_edit"),
            path('mail/mailboxes/<int:mailbox_id>/pop3server/delete/', views.Pop3MailServerDeleteView.as_view(), name="pop3_mail_server_delete")
        ])


    if settings.WEBMAIL_ENABLE_MANAGE_SMTP_SERVER:
        urlpatterns.extend([
            path('mail/mailboxes/<int:mailbox_id>/smtpserver/', views.SmtpServerCreateView.as_view(), name="smtp_server_add"),
            path('mail/mailboxes/<int:mailbox_id>/smtpserver/edit/', views.SmtpServerUpdateView.as_view(), name="smtp_server_edit"),
            path('mail/mailboxes/<int:mailbox_id>/smtpserver/delete/', views.SmtpServerDeleteView.as_view(), name="smtp_server_delete")
        ])


if settings.WEBMAIL_PLUGINS:
    for plugin_name in settings.WEBMAIL_PLUGINS:
        plugin_module_name = "%s_settings.WEBMAIL_plugin" % plugin_name

        try:
            urlpatterns.append(path('', include('%s.urls'%plugin_module_name)))
        except ModuleNotFoundError:
            pass
