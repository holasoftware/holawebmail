import sys


from django.core.management.base import BaseCommand

from webmail.models import MailboxModel


class Command(BaseCommand):
    help = 'Delete mailbox by Id'

    def add_arguments(self, parser):
        parser.add_argument(
            'mailbox_id',
            type=int,
            help='Mailbox ID',
        )

    def handle(self, mailbox_id, **kw):
        num_deleted, _ = MailboxModel.objects.filter(id=mailbox_id).delete()

        if num_deleted == 0:
            self.stderr.write("No mailbox with ID: %s" % mailbox_id)
            sys.exit(1)
        else:
            self.stdout.write("Deleted mailbox with ID: %s" % mailbox_id)
