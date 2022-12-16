from importlib import import_module

from django.core.management.base import BaseCommand

from webmail import settings


class Command(BaseCommand):
    help = (
        "Can be run as a cronjob or directly to clean out expired sessions in the webmail."
    )

    def handle(self, **options):
        engine = import_module(settings.WEBMAIL_SESSION_ENGINE)
        try:
            engine.SessionStore.clear_expired()
        except NotImplementedError:
            self.stderr.write("Session engine '%s' doesn't support clearing "
                              "expired sessions.\n" % settings.WEBMAIL_SESSION_ENGINE)
