import poplib
import email
from email.policy import default as email_policy, strict as email_strict_policy
from email.errors import MessageParseError, MessageDefect


from . import settings


class Pop3Transport:
    def __init__(self, hostname, port=None, ssl=False):
        self.hostname = hostname
        if ssl:
            self.transport = poplib.POP3_SSL
            if port is None:
                port = poplib.POP3_SSL_PORT
        else:
            self.transport = poplib.POP3
            if port is None:
                port = poplib.POP3_PORT

        self.port = port

    def connect(self, username, password):
        self.server = self.transport(self.hostname, self.port)
        self.server.user(username)
        self.server.pass_(password)

    def get_email_from_bytes(self, contents):
        if settings.WEBMAIL_EMAIL_PARSING_STRICT_POLICY:
            policy = email_strict_policy
        else:
            policy = email_policy

        message = email.message_from_bytes(contents, policy=policy)

        return message

    def get_message_body(self, message_lines):
        return bytes('\r\n', 'ascii').join(message_lines)

    def get_message(self, condition=None):
        # TODO: USE UIDL
        message_count = len(self.server.list()[1])
        for i in range(message_count):
            msg_contents = self.get_message_body(
                self.server.retr(i + 1)[1]
            )
            try:
                message = self.get_email_from_bytes(msg_contents)
            except (MessageParseError, MessageDefect):
                continue

            if condition and not condition(message):
                continue

            yield message

            self.server.dele(i + 1)
        self.server.quit()
        return
