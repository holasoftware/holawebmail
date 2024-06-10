import sys


from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError


from webmail.models import WebmailUser, Mailbox


class Command(BaseCommand):
    help = "Create a mailbox for a user"

    def add_arguments(self, parser):
        parser.add_argument(
            'user_id',
            help='User Id'
        )

        parser.add_argument(
            'mailbox_name',
            help='Mailbox name',
        )

        parser.add_argument(
            '--default',
            action="store_true",
            default=False,
            help='Default'
        )

    def handle(self, user_id, mailbox_name, default=False, **kw):
        try:
            user = WebmailUser.objects.get(id=user_id)
        except WebmailUser.DoesNotExist:
            self.stderr.write("User does not exits: %s" % username)
            sys.exit(1)


        try:
            mailbox = Mailbox.objects.create(user=user, name=mailbox_name)
        except IntegrityError:
            self.stderr.write("Mailbox with the same name already exists for that user: %s" % mailbox_name)
            sys.exit(1)


        if default:
            mailbox.set_as_default()

