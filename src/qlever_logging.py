import logging
from termcolor import colored

# TODO: rm termcolor


class CustomFormatter(logging.Formatter):
    """
    Custom formatter for log messages.
    """

    def format(self, record):
        message = record.getMessage()
        if record.levelno == logging.DEBUG:
            return colored(message, "magenta")
        elif record.levelno == logging.WARNING:
            return colored(message, "yellow")
        elif record.levelno in [logging.CRITICAL, logging.ERROR]:
            return colored(message, "red")
        else:
            return message


# Custom logger.
log = logging.getLogger("qlever")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(CustomFormatter())
log.addHandler(handler)
