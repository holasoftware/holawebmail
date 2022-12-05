import logging
from logging.config import dictConfig


_LOGGER_CONFIGURED = False
# Taken from https://github.com/nvie/rq/blob/master/rq/logutils.py
def get_logger(level=None):
    global _LOGGER_CONFIGURED
    # Setup logging for webmail if not already configured
    logger = logging.getLogger('webmail')
    if not _LOGGER_CONFIGURED:
        dictConfig({
            "version": 1,
            "disable_existing_loggers": False,

            "formatters": {
                "webmail": {
                    "format": "[%(levelname)s]%(asctime)s PID %(process)d: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },

            "handlers": {
                "webmail": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                    "formatter": "webmail"
                },
            },

            "loggers": {
                "webmail": {
                    "handlers": ["webmail"],
                    "level": level or "DEBUG"
                }
            }
        })
        _LOGGER_CONFIGURED = True

    return logger
