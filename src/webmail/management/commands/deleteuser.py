import sys


from django.core.management.base import BaseCommand

from webmail.models import WebmailUser


class Command(BaseCommand):
    help = "Delete user by ID"

    def add_arguments(self, parser):
        parser.add_argument(
            'user_id',
            type=int,
            help='User ID',
        )

    def handle(self, user_id, **kw):
        num_deleted, _ = WebmailUser.objects.filter(id=user_id).delete()

        if num_deleted == 0:
            self.stderr.write("No user with ID: %s" % user_id)
            sys.exit(1)
        else:
            self.stdout.write("Deleted user #%s" % user_id)
