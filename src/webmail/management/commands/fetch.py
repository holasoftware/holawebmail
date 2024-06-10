from django.core.management.base import BaseCommand

from webmail.models import Pop3MailServer
from webmail.logutils import get_logger
from webmail.exceptions import InvalidEmailMessageException


class Command(BaseCommand):
    help = "Get all mails from pop3 mail servers"

    def add_arguments(self, parser):
        parser.add_argument(
            'mailbox_names_or_ids',
            nargs="*",
            help = "List of mailbox Id's or username:mailbox_name items. If no mailbox specified, all active pop3 mail servers will be selected"
        )

        parser.add_argument(
            '-l', '--log-level',
            choices=["info", "debug", "warning", "error"],
            default="debug"
        )

    def handle(self, **options):
        mailbox_names_or_ids = options["mailbox_names_or_ids"]
        if len(mailbox_names_or_ids) == 0:
            pop3_mail_servers = Pop3MailServer.objects.filter(active=True)
        else:
            pop3_mail_servers = []

            for mailbox_name_or_id in mailbox_names_or_ids:
                try:
                    mailbox_id = int(mailbox_name_or_id)
                    try:
                        pop3_mail_server = Pop3MailServer.objects.get(mailbox__id=mailbox_id)
                    except Pop3MailServer.DoesNotExist:
                        self.stderr.write("No mailbox with a pop3 mail server and Id: %s" % mailbox_id)
                    else:
                        pop3_mail_servers.append(pop3_mail_server)
                except ValueError:
                    if ":" not in mailbox_name_or_id:
                        self.stderr.write("Invalid mailbox name. Username and mailbox name separated by a colon is required: %s" % mailbox_name_or_id)
                        continue

                    username, mailbox_name = mailbox_name_or_id.split(":")

                    try:
                        pop3_mail_server = Pop3MailServer.objects.get(
                            mailbox__user__username=username, mailbox__name=mailbox_name)
                    except Pop3MailServer.DoesNotExist:
                        self.stderr.write("No mailbox belonging to user '%s' with a pop3 mail server associated and mailbox name '%s'" % (username, mailbox_name))
                    else:
                        pop3_mail_servers.append(pop3_mail_server)

        if len(pop3_mail_servers) == 0:
            self.stderr.write("Nothing to do")
            return

        logger = get_logger(options['log_level'].upper())

        for pop3_mail_server in pop3_mail_servers:
            mailbox = pop3_mail_server.mailbox

            logger.info(
                'Gathering messages for user "%s" from mailbox "%s"',
                mailbox.user.username,
                mailbox.name
            )

            try:
                for msg_record in pop3_mail_server.get_new_mail():
                    if isinstance(msg_record, InvalidEmailMessageException):
                        logger.warn("Invalid email: %s" % str(msg_record))
                    else:
                        logger.info(
                            'Received %s (from %s)',
                            msg_record.subject,
                            msg_record.from_email
                        )
            except OSError as exc:
                self.stderr.write("OS Error %s: %s" % exc.args)
