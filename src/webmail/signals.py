from django.dispatch.dispatcher import Signal


inbound_email_received_signal = Signal()

# This signal is triggered whenever webmail pushes one or more emails into its queue.
message_queued_signal = Signal()

message_flagged_as_spam_signal = Signal()
message_flagged_as_not_spam_signal = Signal()

# Sent when a file is uploaded.
file_attachment_uploaded_signal = Signal()

attachments_uploaded_signal = Signal()

# Sent when an attachment is downloaded.
attachment_downloaded_signal = Signal()

# Outbound message, before sending
pre_send_mail_signal = Signal()

# Outbound message, after sending
post_send_signal = Signal()
#email_sent = Signal()
#email_failed_to_send = Signal()

username_changed_signal = Signal()
password_changed_signal = Signal()

user_recovers_password_signal = Signal()

user_logged_in_signal = Signal()
user_login_failed_signal = Signal()
user_logged_out_signal = Signal()
