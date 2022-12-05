from django.core.management.base import BaseCommand


from webmail.fake_data import create_fake_data


class Command(BaseCommand):
    help = 'Create test data'

    def handle(self, *args, **options):
        create_fake_data()

