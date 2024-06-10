import sys


from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from webmail.models import WebmailUser


class Command(BaseCommand):
    help = 'Create webmail user and optionally provide "Displayed name" and/or "Password"'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
        )

        parser.add_argument(
            '--displayed-name',
            help='Displayed name',
        )

        parser.add_argument(
            '--password',
            help='Password',
        )

    def handle(self, username, password=None, displayed_name=False, **kw):
        try:
            user = WebmailUser.objects.create_user(username=username, password=password, displayed_name=displayed_name)
        except IntegrityError:
            self.stderr.write("User with the same username already exists: %s" % username)
            sys.exit(1)

        self.stdout.write(str(user.id))
