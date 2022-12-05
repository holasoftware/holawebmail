Hola Webmail
------------

``holawebmail`` is a Django webmail app. 

It's a webmail focused in privacy and cybersecurity.

Privacy and cybersecurity are really hard problems nowadays. The goal of this project is to provide an ethical tool to help people to protect themshelves.


Features
--------
- Login using SRP authentication
- Webmail users have different database table for login credentials and sessions than admin staff
- Safe upload of big file during email composition using upload sessions
- Markdown editor for sending emails
- Logging of all authentication attempts.
- Export/Import emails
- Hook system to extend easily the system
- Save mails to draft store
- Search text in mails
- Add star to interesting mails
- Show original email headers
- Minimal dependencies (only Django)
- Responsive and clean UI design
- Automatic generation of fake data for testing purposes


Requirements
------------

* Python 3

* Django >= 2.1



Getting Started
---------------

Simple usage instructions:

In ``settings.py``:

    INSTALLED_APPS = [
        ...
        "webmail",
        ...
    ]

    MIDDLEWARE = [
        ...
        "webmail.middleware.WebmailMiddleware",
        ...
    ]

Run database migrations to set up the needed database tables.

To add testing data and see the application running in a demo:

    python manage.py testdata


Credentials for the demo:
    username:test
    password:test


To fetch all emails from all active POP3 servers:

    python manage.py fetch

To fetch all emails for a specific mailboxes:

    python manage.py fetch <mailbox_name1> <mailbox_name2> ...
Every argument is a mailbox ID or a term with the username and the mailbox name concatenated with a colon: username:mailbox_name.

To send all the queued emails in one time:

    python manage.py sendmail

To send all queued emails continuosly inside a loop:

    python manage.py sendmail --forever

To purge old tasks that are completed or cancelled:

    python manage.py purgeoldsendmailtasks


Notes
-----
The user login using SRP authentication without never sending the password on the wire. 
    https://wikipedia.org/wiki/Secure_Remote_Password_protocol

By design, the code use minimal dependencies as possible to avoid more points of attack. 

The webmail process in the background an asyncronous task for getting and processing emails from a POP3 email server, and another task for sending all the enqueed emails stored in the database.

File attachments are also temporarily stored in the database, which means if you are sending files larger than several hundred KB in size, you are likely to run into database limitations on how large your query can be. If this happens, you'll either need to increase your database limits (a procedure that depends on which database you are using).

