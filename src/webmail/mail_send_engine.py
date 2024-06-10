import contextlib
import smtplib
import time
from socket import error as socket_error


from django.db import NotSupportedError, OperationalError, transaction
from django.db.models import Q
from django.utils import timezone


from .models import SendMailTask, NoSmtpServerConfiguredException
from .logutils import get_logger
from . import settings, lockfile


logger = get_logger()


def prioritize_sending_email_tasks_ids():
    """
    Returns the messages in the queue in the order they should be sent.
    """
    for task_data in SendMailTask.objects.non_deferred().order_by('priority', 'created_at').values("id"):
        yield task_data["id"]


@contextlib.contextmanager
def sender_context(send_mail_task_id):
    """
    Makes a context manager appropriate for sending a message.
    Entering the context using `with` may return a `None` object if the message
    has been sent/deleted already.
    """
    # We wrap each message sending inside a transaction (otherwise
    # select_for_update doesn't work).

    # We also do `nowait` for databases that support it. The result of this is
    # that if two processes (which might be on different machines) both attempt
    # to send the same queue, the loser for the first message will immediately
    # get an error, and will be able to try the second message. This means the
    # work for sending the messages will be distributed between the two
    # processes. Otherwise, the losing process has to wait for the winning
    # process to finish and release the lock, and the winning process will
    # almost always win the next message etc.
    with transaction.atomic():
        try:
            try:
                yield SendMailTask.objects.filter(id=send_mail_task_id).select_for_update(nowait=True).get()
            except NotSupportedError:
                # MySQL does not support the 'nowait' argument
                yield SendMailTask.objects.filter(id=send_mail_task_id).select_for_update().get()
        except SendMailTask.DoesNotExist:
            # Deleted by someone else
            yield None
        except OperationalError:
            # Locked by someone else
            yield None


def get_sending_email_context_managers():
    """
    Returns a series of context managers that are used for sending mails in the queue.
    Entering the context manager returns the actual message
    """
    for task_id in prioritize_sending_email_tasks_ids():
        yield sender_context(task_id)


def acquire_lock(
    lock_path=settings.WEBMAIL_MAILER_LOCK_PATH,    
    lock_wait_timeout=settings.WEBMAIL_MAILER_LOCK_WAIT_TIMEOUT):
    # lock_path: allows for a different lockfile path. The default is a file
    # in the current working directory.

    # lock_wait_timeout: lock timeout value. how long to wait for the lock to become available.
    # default behavior is to never wait for the lock to be available.


    lock = lockfile.FileLock(lock_path)

    try:
        lock.acquire(lock_wait_timeout)
    except lockfile.AlreadyLocked:
        logger.debug("Not possible to acquire the lock. Lock already in place. quitting.")
        return False, lock
    except lockfile.LockTimeout:
        logger.debug("Not possible to acquire the lock. Waiting for the lock timed out. quitting.")
        return False, lock
    logger.debug("Lock acquired.")
    return True, lock


def release_lock(lock):
    logger.debug("Releasing lock.")
    lock.release()
    logger.debug("Lock released.")


def send_all(
    max_processed_tasks_in_batch=settings.WEBMAIL_MAILER_MAX_PROCESSED_TASKS_IN_BATCH,
    max_succeed_tasks_in_batch=settings.WEBMAIL_MAILER_MAX_SUCCEED_TASKS_IN_BATCH,
    max_failed_tasks_in_batch=settings.WEBMAIL_MAILER_MAX_FAILED_TASKS_IN_BATCH,
    max_failed_or_deferred_tasks_in_batch=settings.WEBMAIL_MAILER_MAX_FAILED_OR_DEFERRED_TASKS_IN_BATCH,
    max_times_mail_deferred=settings.WEBMAIL_MAILER_MAX_TIMES_MAIL_DEFERRED,
    sleep_time_if_no_lock_acquired=settings.WEBMAIL_MAILER_SLEEP_TIME_IF_NO_LOCK_ACQUIRED,
    throttle_time=settings.WEBMAIL_MAILER_THROTTLE_TIME, 
    delete_completed_tasks=settings.WEBMAIL_MAILER_DELETE_COMPLETED_TASKS, 
    defer_duration=settings.WEBMAIL_MAILER_DEFER_DURATION, 
    lock_path=settings.WEBMAIL_MAILER_LOCK_PATH, 
    lock_wait_timeout=settings.WEBMAIL_MAILER_LOCK_WAIT_TIMEOUT):
    """
    Send all eligible messages in the queue.
    """


    logger.debug("Started processing tasks.")

    start_time = time.time()

    num_succeed = 0
    num_failed = 0
    num_deferred = 0

    num_cancelled = 0

    num_tasks_processed = 0

    lock = None

    try:
        for sending_email_context_manager in get_sending_email_context_managers():
            while True:
                acquired, lock = acquire_lock(lock_path=lock_path, lock_wait_timeout=lock_wait_timeout)
                if acquired:
                    break
                else:
                    time.sleep(sleep_time_if_not_acquired_file_lock)

            num_tasks_processed += 1

            with sending_email_context_manager as send_email_task:
                if send_email_task is None:
                    release_lock(lock)
                    lock = None

                    continue

                send_email_task.set_status_in_progress()

                release_lock(lock)
                lock = None

                logger.info("Running email send task #%d" % send_email_task.id)

                if max_times_mail_deferred is not None and send_email_task.num_deferred_times >= max_times_mail_deferred:
                    notify_failure = True
                    defer = False
                else:
                    notify_failure = False
                    defer = True

                try:
                    success = send_email_task.send(notify_failure=notify_failure)
                except NoSmtpServerConfiguredException:
                    num_cancelled += 1
                    send_email_task.set_status_cancelled()
                    continue

                if success:
                    num_succeed += 1

                    if delete_completed_tasks:
                        send_email_task.delete()
                    else:
                        send_email_task.set_status_completed()
                else:
                    if defer:
                        send_email_task.defer(hours=defer_duration)
                        logger.info("Sending email task #%d deferred due to failure", send_email_task.id)

                        num_deferred += 1
                    else:
                        send_email_task.set_status_failed()
                        num_failed += 1

            # Allow sending a fixed/limited amount of emails in each delivery run

            if max_processed_tasks_in_batch is not None and num_tasks_processed >= max_processed_tasks_in_batch:
                logger.warning("Max number of email sending tasks processed (%s) reached, stopping for this round", max_processed_tasks_in_batch)
                break

            if max_succeed_tasks_in_batch is not None and num_succeed >= max_succeed_tasks_in_batch:
                logger.info("Max succeed tasks (%s) sending email reached, stopping for this round", max_succeed_tasks_in_batch)
                break

            if max_failed_tasks_in_batch is not None and num_failed >= max_failed_tasks_in_batch:
                logger.warning("Max failed tasks (%s) sending email reached, stopping for this round", max_failed_tasks_in_batch)
                break

            if max_failed_or_deferred_tasks_in_batch is not None and num_failed + num_deferred >= max_failed_or_deferred_tasks_in_batch:
                logger.warning("Max failed or deferred (%s) reached sending email, stopping for this round", max_failed_or_deferred_tasks_in_batch)
                break

            # When delivering, wait some time between emails to avoid server overload
            # defaults to 0 for no waiting
            if throttle_time:
                logger.debug("Throttling email delivery. Sleeping %s seconds", throttle_time)
                time.sleep(throttle_time)
    finally:
        if lock is not None:
            release_lock(lock)

    if num_tasks_processed == 0:
        logger.info("No message in the queue. No mail processed.")
    else:
        logger.info("Mail sent resume: %d total processed; %s succeed; %d failed: %d deferred; %d cancelled.\nDone in %.2f seconds", num_tasks_processed, num_succeed, num_failed, num_deferred, num_cancelled, (time.time() - start_time))


def send_all_loop(sleep_time_if_queue_empty=settings.WEBMAIL_MAILER_SLEEP_TIME_IF_QUEUE_EMPTY, **kwargs):
    """
    Loop indefinitely, checking queue at intervals of EMPTY_QUEUE_SLEEP and
    sending messages if any are on queue.

    PARAM queue_empty_sleep_time: when queue is empty, how long to wait (in seconds) before checking again
    """

    while True:
        while not SendMailTask.objects.all():
            logger.debug("sleeping for %s seconds before checking queue again" % sleep_time)
            time.sleep(sleep_time_if_queue_empty)
        send_all(**kwargs)
