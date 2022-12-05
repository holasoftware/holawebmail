import logging
import tempfile
import sys


from django.core.management.base import BaseCommand


from webmail.mail_send_engine import send_all, send_all_loop
from webmail.logutils import get_logger
from webmail import settings


class Command(BaseCommand):
    help = "Do one pass through the mail queue, attempting to send all mail, or send email forever."

    def add_arguments(self, parser):
#        parser.add_argument(
#            '-p', '--processes',
#            type=int,
#            default=1,
#            help='Number of processes used to send emails',
#        )
        parser.add_argument(
            '--forever',
            action="store_true",
            default=False,
            help='Run forever',
        )

        parser.add_argument(
            '-L', '--lockfile',
            dest="lock_path",
            help='Absolute path of lockfile to acquire',
            default=settings.WEBMAIL_MAILER_LOCK_PATH
        )

        parser.add_argument(
            '--lock-wait-timeout',
            type=int,
            default=settings.WEBMAIL_MAILER_LOCK_WAIT_TIMEOUT
        )

        parser.add_argument(
            '--sleep-time-if-no-lock-acquired',
            type=int,
            default=settings.WEBMAIL_MAILER_SLEEP_TIME_IF_NO_LOCK_ACQUIRED
        )

        parser.add_argument(
            '--max-processed-tasks-in-batch',
            type=int,
            default=settings.WEBMAIL_MAILER_MAX_PROCESSED_TASKS_IN_BATCH
        )

        parser.add_argument(
            '--max-succeed-tasks-in-batch',
            type=int,
            default=settings.WEBMAIL_MAILER_MAX_SUCCEED_TASKS_IN_BATCH
        )

        parser.add_argument(
            '--max-failed-tasks-in-batch',
            type=int,
            default=settings.WEBMAIL_MAILER_MAX_FAILED_TASKS_IN_BATCH
        )

        parser.add_argument(
            '--max-failed-or-deferred-tasks-in-batch',
            type=int,
            default=settings.WEBMAIL_MAILER_MAX_FAILED_OR_DEFERRED_TASKS_IN_BATCH
        )

        parser.add_argument(
            '--throttle-time',
            type=int,
            default=settings.WEBMAIL_MAILER_THROTTLE_TIME
        )

        parser.add_argument(
            '--delete-completed-tasks',
            action="store_true",
            default=settings.WEBMAIL_MAILER_DELETE_COMPLETED_TASKS
        )

        parser.add_argument(
            '--max-times-mail-deferred',
            type=int,
            default=settings.WEBMAIL_MAILER_MAX_TIMES_MAIL_DEFERRED
        )

        parser.add_argument(
            '--defer-duration',
            type=int,
            help='How many hours to wait before retrying again this task',
            default=settings.WEBMAIL_MAILER_DEFER_DURATION
        )

        parser.add_argument(
            '--sleep-time-if-queue-empty',
            type=int,
            default=settings.WEBMAIL_MAILER_SLEEP_TIME_IF_QUEUE_EMPTY
        )

        parser.add_argument(
            '-l', '--log-level',
            choices=["info", "debug", "warning", "error"],
            default="debug"
        )

    def handle(self, *args, max_processed_tasks_in_batch=None, max_succeed_tasks_in_batch=None, max_failed_tasks_in_batch=None, max_failed_or_deferred_tasks_in_batch=None, max_defer_email=None, throttle_time=None, delete_completed_tasks=None, max_times_mail_deferred=None, defer_duration=None, lock_wait_timeout=None, lock_path=None, sleep_time_if_no_lock_acquired=None, sleep_time_if_queue_empty=None, **options):
        # allow a sysadmin to pause the sending of mail temporarily.        
        logger = get_logger(options['log_level'].upper())

        if settings.WEBMAIL_MAILER_PAUSE_SEND:
            self.stdout.write("Mailer paused!")
            sys.exit()

        forever = options["forever"]

        kwargs = {}
        if lock_path is not None:
            kwargs["lock_path"] = lock_path

        kwargs = dict(
                lock_path=lock_path,
                lock_wait_timeout=lock_wait_timeout,
                sleep_time_if_no_lock_acquired=sleep_time_if_no_lock_acquired,
                max_processed_tasks_in_batch=max_processed_tasks_in_batch,
                max_succeed_tasks_in_batch=max_succeed_tasks_in_batch,
                max_failed_tasks_in_batch=max_failed_tasks_in_batch,
                max_failed_or_deferred_tasks_in_batch=max_failed_or_deferred_tasks_in_batch,
                max_times_mail_deferred=max_times_mail_deferred,
                throttle_time=throttle_time,
                delete_completed_tasks=delete_completed_tasks,
                defer_duration=defer_duration)

        if forever:
            kwargs["sleep_time_if_queue_empty"] = sleep_time_if_queue_empty
            send_all_loop(**kwargs)
        else:
            send_all(**kwargs)
