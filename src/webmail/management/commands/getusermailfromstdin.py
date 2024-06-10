import email
import sys


from django.core.management.base import BaseCommand, CommandError


from webmail.models import Mailbox
from webmail.logutils import get_logger


logger = get_logger()


class Command(BaseCommand):
    help = "Receive incoming mail via stdin"

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            help="Username"
        )
        parser.add_argument(
            'mailbox_name',
            help="The name of the mailbox that will receive the message"
        )

    def handle(self, username, mailbox_name=None, *args, **options):
        try:
            mailbox = Mailbox.objects.get(user__username=username, name=mailbox_name)
        except Mailbox.DoesNotExist:
            raise CommandError("Mailbox does not exist")

        email_message = email.message_from_string(sys.stdin.read())
        if email_message:
            mailbox.process_incomming_email(email_message)
            logger.info(
                "Message received from %s",
                email_message['from']
            )
        else:
            logger.warning("Message not processable.")
