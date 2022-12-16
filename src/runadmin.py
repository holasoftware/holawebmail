#!/usr/bin/env python
"""Django's command-line utility for running admin app."""
import os
import sys


def main():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'admin.settings'

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    args = [sys.argv[0]] + ["runserver"] + sys.argv[1:]
    execute_from_command_line(args)


if __name__ == '__main__':
    main()
