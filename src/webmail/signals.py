from django.dispatch.dispatcher import Signal


inbound_email_received_signal = Signal(providing_args=["email_message", "mailbox"])

# This signal is triggered whenever webmail pushes one or more emails into its queue.
message_queued_signal = Signal(providing_args=['message'])

message_flagged_as_spam_signal = Signal(providing_args=["message"])
message_flagged_as_not_spam_signal = Signal(providing_args=["message"])

# Sent when a file is uploaded.
file_attachment_uploaded_signal = Signal(providing_args=('request', 'upload_session', 'file_attachment'))

attachments_uploaded_signal = Signal(providing_args=('message', 'upload_session'))

# Sent when an attachment is downloaded.
attachment_downloaded_signal = Signal(providing_args=('request','attachment'))

# Outbound message, before sending
pre_send_mail_signal = Signal(providing_args=['send_task'])

# Outbound message, after sending
post_send_signal = Signal(providing_args=['send_task'])
#email_sent = Signal()
#email_failed_to_send = Signal()

username_changed_signal = Signal(providing_args=['user'])
password_changed_signal = Signal(providing_args=['user'])

user_recovers_password_signal = Signal()

user_logged_in_signal = Signal(providing_args=['request', 'user'])
user_login_failed_signal = Signal(providing_args=['request', 'control_panel_id', 'credentials'])
user_logged_out_signal = Signal(providing_args=['request', 'user'])
