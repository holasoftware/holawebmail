from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


from webmail.fake_data import create_fake_data


class Command(BaseCommand):
    help = 'Initialize website'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            help="Root username",
            default="root",
        )

        parser.add_argument(
            '--email',
            help="Root email",
            default="",
        )

        parser.add_argument(
            '--password',
            help="Root password",
            default="root",
        )

        parser.add_argument(
            '--no-test-data',
            dest="test_data",
            help="Don't create test data",
            default=True,
            action='store_false'
        )

    def handle(self, *args, **options):
        call_command('migrate')

        User = get_user_model()
        User.objects.create_superuser(options["username"], options["email"], options["password"])

        if options["test_data"]:
            create_fake_data()

