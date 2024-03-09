# Copyright 2024, University of Freiburg,
# Chair of Algorithms and Data Structures
# Author: Hannah Bast <bast@cs.uni-freiburg.de>

import logging
from termcolor import colored


class CustomFormatter(logging.Formatter):
    """
    Custom formatter for logging.
    """
    def format(self, record):
        message = record.getMessage()
        if record.levelno == logging.DEBUG:
            return colored(f"DEBUG: {message}", "magenta")
        elif record.levelno == logging.WARNING:
            return colored(f"{message}", "yellow")
        elif record.levelno in [logging.CRITICAL, logging.ERROR]:
            return colored(f"{message}", "red")
        else:
            return message


# Custom logger.
log = logging.getLogger("qlever")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(CustomFormatter())
log.addHandler(handler)
