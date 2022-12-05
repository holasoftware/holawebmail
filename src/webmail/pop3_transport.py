import email
from email.policy import EmailPolicy
# Do *not* remove this, we need to use this in subclasses of EmailTransport
from email.errors import MessageParseError  # noqa: F401

import poplib


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
        message = email.message_from_bytes(contents, policy=EmailPolicy())

        return message

    def get_message_body(self, message_lines):
        return bytes('\r\n', 'ascii').join(message_lines)

    def get_message(self, condition=None):
        message_count = len(self.server.list()[1])
        for i in range(message_count):
            try:
                msg_contents = self.get_message_body(
                    self.server.retr(i + 1)[1]
                )
                message = self.get_email_from_bytes(msg_contents)

                if condition and not condition(message):
                    continue

                yield message
            except MessageParseError:
                continue
            self.server.dele(i + 1)
        self.server.quit()
        return
