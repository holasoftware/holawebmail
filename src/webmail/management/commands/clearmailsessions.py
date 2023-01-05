from django.core.management.base import BaseCommand

from webmail.session_engine import SessionStore


class Command(BaseCommand):
    help = (
        "Can be run as a cronjob or directly to clean out expired sessions in the webmail."
    )

    def handle(self, **options):
        SessionStore.clear_expired()
