Hola Webmail
------------

``holawebmail`` is a Django webmail app. 

It's a webmail focused in privacy and cybersecurity.

Privacy and cybersecurity are really hard problems nowadays. The goal of this project is to provide an ethical tool to help people to protect themshelves.

Documentation and screenshots: [https://holasoftware.github.io/holawebmail_docs/](https://holasoftware.github.io/holawebmail_docs/)


Features
--------
- Login using SRP authentication
- Webmail users have different database table for login credentials and sessions than admin staff
- Safe upload of big file during email composition using upload sessions
- Markdown editor for sending emails
- Logging of all authentication attempts.
- Logging control session
- Export/Import emails
- Hook system to extend easily the webmail
- Multiconfigurable
- Save mails to draft store
- Enable or disable autodraft
- Search text in mails
- Add star to interesting mails
- Show original email headers
- Minimal dependencies (only Django)
- Responsive and clean UI design
- Automatic generation of fake data for testing purposes


Requirements
------------

* Python 3

* Django >= 4



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

    SESSION_ENGINE = "webmail.session_engine"

These are the required apps:

    - django.contrib.auth
    - django.contrib.contenttypes
    - django.contrib.sessions
    - django.contrib.messages
    - django.contrib.staticfiles

These are the required middlewares:

    - django.contrib.sessions.middleware.SessionMiddleware
    - django.middleware.csrf.CsrfViewMiddleware
    - django.contrib.messages.middleware.MessageMiddleware


Run database migrations to set up the needed database tables.
    
    python manage.py migrate

To add testing data and see the application running in a demo:

    python manage.py testdata

Credentials for the demo:

    username:test
    password:test

Create a super user:

    python manage.py createsuperuser

To start the application:

    python manage.py runserver

The application is served in the root path `/` and the django admin in `/admin/`.

To fetch all emails from all active POP3 servers:

    python manage.py fetch

To fetch all emails for a specific mailboxes:

    python manage.py fetch <mailbox_name1> <mailbox_name2> ...
Every argument is a mailbox ID or a term with the username and the mailbox name concatenated with a colon:

    username:mailbox_name

To send all the queued emails in one time:

    python manage.py sendmail

To send all queued emails forever inside a loop (Control+C to terminate):

    python manage.py sendmail --forever

To purge old tasks that are completed or cancelled:

    python manage.py purgeoldsendmailtasks


Settings
--------
*WEBMAIL_AUTODRAFT_ENABLED*: To enable/disable the autodraft.

*WEBMAIL_UI_BRAND_NAME*: Change the brand name, instead of "!Hola mail!"


Technical notes
---------------
The user login using SRP authentication without never sending the password on the wire. 
    https://wikipedia.org/wiki/Secure_Remote_Password_protocol

For better security and isolation of the session cookies, the recommendation is to run the django admin in a different origin than the webmail application or in case of using the same origin, run a different process for the django admin with a different cookie session name setting (just change the environment variable `APP` to a different value for example. See the file `app/settings.py`). The tables for the webmail users and the django admin staff are different. This makes possible to use different databases for the django user credentials and the user of the webmail and any data related to the webmail application. The way to do this is using the `DATABASE` setting to define multiple databases and a routing scheme in `DATABASE_ROUTERS` to provide a different database name for the model `AUTH_USER_MODEL` and another one for the models of the webmail like for example `webmail.models.WebmailUser`.

By design, the code use minimal dependencies as possible to avoid more points of attack. 

The webmail process in the background an asyncronous task for getting and processing emails from a POP3 email server, and another task for sending all the enqueed emails stored in the database.

File attachments are also temporarily stored in the database, which means if you are sending files larger than several hundred KB in size, you are likely to run into database limitations on how large your query can be. If this happens, you'll either need to increase your database limits (a procedure that depends on which database you are using).