from django.core.management.base import BaseCommand


from webmail.models import SendMailTaskModel
from webmail.logutils import get_logger

logger = get_logger()


class Command(BaseCommand):
    help = "Delete mailer log"

    def add_arguments(self, parser):
        parser.add_argument('days', type=int, help="Number of days that a log is considered old")

    def handle(self, days, **options):
        count = SendMailTaskModel.objects.purge_old_entries(days)
        logger.info("%s tasks deleted " % count)
