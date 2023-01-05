
class NoSmtpServerConfiguredException(Exception):
    pass


class InvalidEmailMessageException(Exception):
    def __init__(self, error_message, email_message):
        self.email_message = email_message
        super().__init__(error_message)


