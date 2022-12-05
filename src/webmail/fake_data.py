import datetime
import random
import os
import string
from email import utils as email_utils


from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile


from .models import WebmailUserModel, ContactModel, MailboxModel, Pop3MailServerModel, SmtpServerModel, TagModel, MessageModel, MessageAttachmentModel
from . import settings



def maybe_true(l=None):
    if l is None:
        l = 0.5

    return random.random() <= l


def generate_random_string(chars, string_length):
    random_string = ''.join(random.choice(chars) for i in range(string_length))

    return random_string


def generate_random_subject():
    return generate_random_string(string.ascii_lowercase, random.choice(range(5,20)))


def lorem_ipsum(qty=15):
    # always start with Lorem ipsum for first output lorem
    para = ""

    # start with lorem ipsum 20% of the time
    if random.randint(0, 5) == 0:
        para = "lorem ipsum "

    # words from the original Lorum ipsum text
    words = "dolor sit amet consectetur adipisicing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua ut enim ad minim veniam quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur excepteur sint occaecat cupidatat non proident sunt in culpa qui officia deserunt mollit anim id est laborum".split()

    for x in list(range(random.randint(int(qty - qty/3)-2, int(qty + qty/3)-2))):
        para += random.choice(words) + " "

    para += random.choice(words)

    para = para.capitalize() + "."
    return para


def random_file_attachment(message):
    file_data = os.urandom(random.randint(10, 100))
    file_name = "attachment%d.bin"% random.randint(1, 1000000)

    mimetype = 'application/octet-stream'

    MessageAttachmentModel.objects.create(file=ContentFile(file_data, file_name), file_name=file_name, mimetype=mimetype, message=message)


def random_body_email(min_sentences=1, max_sentences=50, min_words_paragraph=10, max_words_paragraph=30):
    sentences = []

    for i in range(random.choice(range(min_sentences, max_sentences))):
        qty_words = random.choice(range(min_words_paragraph, max_words_paragraph))
        sentences.append(lorem_ipsum(qty_words))

    return "\n\n".join(sentences)


def random_ip():
    return ".".join([str(random.randrange(0, 255)) for i in range(0, 4)])


def create_fake_data(
    username="test",
    password="test",
    qty_user_contacts=20,
    min_message_attachments=1,
    max_message_attachments=4,
    min_messages_in_folder=20,
    max_messages_in_folder=30,
    max_emails_in_to=4,
    max_emails_in_cc=4,
    max_emails_in_bcc=4,
    probability_of_having_attachment=0.3,
    probability_of_replying_last_message=None,
    probability_message_is_read=None,
    probability_message_is_for_me=0.7,
    probability_message_is_starred=None,
    probability_message_has_cc=0.5,
    probability_message_has_bcc=0.5,
    names=settings.WEBMAIL_FAKE_DATA_NAMES,
    surnames=settings.WEBMAIL_FAKE_DATA_SURNAMES,
    email_domains=settings.WEBMAIL_FAKE_DATA_EMAIL_DOMAINS):

    def random_username(name=None, surname=None):
        if name is None:
            name = random.choice(names)

        if surname is None:
            surname = random.choice(surnames)

        username = "%s.%s%s"%(name.replace(" ","").lower(), surname.replace(" ","").lower() , random.randint(1, 10000))

        return username


    def random_email(username=None):
        if username is None:
            username = random_username()

        domain_name = random.choice(email_domains)

        return "%s@%s" % (username, domain_name)

    user = WebmailUserModel.objects.create_user(username=username, password=password)

    contact_usernames = set()
    for i in range(qty_user_contacts):
        contact_name = random.choice(names)
        contact_surname = random.choice(surnames)

        username = random_username(name=contact_name, surname=contact_surname)
        if username in contact_usernames:
            username += "." + str(i)

        contact_usernames.add(username)

        ContactModel.objects.create(user=user, displayed_name=("%s %s"%(contact_name, contact_surname)).title() , email=random_email(username=username))

    my_email1 = "my_email1@domain.com"

    mailbox1 = MailboxModel.objects.create(user=user, name="mailbox1", emails=my_email1)
    mailbox1_server = Pop3MailServerModel.objects.create(mailbox=mailbox1, username="username1", password="password1", ip_address="32.23.1.12", port=9873, use_ssl=True)

    my_email2 = "my_email2@domain.com"

    mailbox2 = MailboxModel.objects.create(user=user, name="mailbox2", emails=my_email2)
    mailbox2_server = Pop3MailServerModel.objects.create(mailbox=mailbox2, username="username2", password="password2", ip_address="222.123.12.31", port=7987, use_ssl=True)

    mailbox1.set_as_default()

    smtp_server1 = SmtpServerModel.objects.create(mailbox=mailbox1, ip_address="123.23.12.1", port=232, username="usernamename1", password="password1", from_email=my_email1)
    smtp_server2 = SmtpServerModel.objects.create(mailbox=mailbox2, ip_address="223.13.132.12", port=1242, username="usernamename2", password="password2", from_email=my_email2)

    last_message = None

    for folder_id in MessageModel.FOLDER_IDS:
        for i in range(random.choice(range(min_messages_in_folder, max_messages_in_folder))):
            mail_message_id = email_utils.make_msgid()
            is_starred = maybe_true(probability_message_is_starred)

            from_email = random_email()

            to = [random_email() for i in range(random.choice(range(1, max_emails_in_to)))]

            subject = generate_random_subject()

            email_headers = [("From", from_email), ("Subject", subject), ("Date", email_utils.format_datetime(email_utils.localtime())), ("To",  ", ".join(to))]

            if folder_id == MessageModel.SENT_FOLDER_ID:
                from_me = True
                to_me = False
                to_me_email = None
            else:
                from_me = False
                to_me = maybe_true(probability_message_is_for_me)
                if to_me:
                    to_me_email = my_email1
                    to.append(to_me_email)
                else:
                    to_me = False
                    to_me_email = None

            has_cc = maybe_true(probability_message_has_cc)
            if has_cc:
                cc = [random_email() for i in range(random.choice(range(max_emails_in_cc)))]
                email_headers.append(("CC", ", ".join(cc)))
            else:
                cc = None

            has_bcc = maybe_true(probability_message_has_bcc)
            if has_bcc:
                bcc = [random_email() for i in range(random.choice(range(max_emails_in_bcc)))]
                email_headers.append(("BCC", ", ".join(bcc)))
            else:
                bcc = None

            body = random_body_email()

            message = MessageModel(from_email=from_email, mailbox=mailbox1, subject=subject, message_id=mail_message_id, to=to, cc=cc, bcc=bcc, original_email_headers=email_headers, is_starred=is_starred, text_plain =body, folder_id=folder_id, to_me=to_me, to_me_email=to_me_email, from_me=from_me)

            if last_message is not None:
                is_reply_to_last_message = maybe_true(probability_of_replying_last_message)
                if is_reply_to_last_message:
                    message.in_reply_to = last_message

            message.save()

            is_read = maybe_true(probability_message_is_read)
            if is_read:
                message.mark_as_read()

            has_attachments = maybe_true(probability_of_having_attachment)
            if has_attachments:
                num_attachments = random.randint(min_message_attachments, max_message_attachments)
                for i in range(num_attachments):
                    random_file_attachment(message)

            last_message = message

