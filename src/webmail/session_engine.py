from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DjangoDbSessionStore


from webmail.models import WebmailSessionModel


class SessionStore(DjangoDbSessionStore):
    """
    Implement webmail session store.
    """
    def __init__(self, session_key=None):
        super().__init__(session_key)

        self.user = None
        self._uuid = None

        self.loaded = False

    @property
    def uuid(self):
        self.load()
        return self._uuid

    def set_user(self, user):
        self.user = user

    def load(self):
        if not self.loaded:
            self.loaded = True

        return super().load()

    def _get_session_from_db(self):
        session_model_obj = super()._get_session_from_db()
        if session_model_obj is not None:
            self.user = session_model_obj.user
            self._uuid = session_model_obj.uuid

        return session_model_obj

    @classmethod
    def get_model_class(cls):
        return WebmailSessionModel

    def create_model_instance(self, data):
        """
        Return a new instance of the session model object, which represents the
        current session state. Intended to be used for saving the session data
        to the database.
        """
        return self.model(
            user=self.user,
            session_key=self._get_or_create_session_key(),
            session_data=self.encode(data),
            expire_date=self.get_expiry_date(),
        )

