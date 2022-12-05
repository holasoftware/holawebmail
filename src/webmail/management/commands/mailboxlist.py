import sys


from django.core.management.base import BaseCommand


from webmail.models import MailboxModel


class Command(BaseCommand):
    help = "List all mailboxes names of a specific user"

    def add_arguments(self, parser):
        parser.add_argument(
            'user_id',
            help='User Id'
        )

    def handle(self, user_id, **kw):
        for mailbox in MailboxModel.objects.filter(user__id=user_id):
            self.stdout.write(mailbox.name)
