#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

# Copyright 2024, University of Freiburg,
# Chair of Algorithms and Data Structures
# Author: Hannah Bast <bast@cs.uni-freiburg.de>

import traceback

from termcolor import colored

from qlever import command_objects
from qlever.config import ConfigException, QleverConfig
from qlever.log import log


def main():
    # Parse the command line arguments and read the Qleverfile.
    try:
        qlever_config = QleverConfig()
        args = qlever_config.parse_args()
    except ConfigException as e:
        log.error(e)
        log.info("")
        log.info(traceback.format_exc())
        exit(1)

    # Execute the command.
    command_object = command_objects[args.command]
    try:
        log.info("")
        log.info(colored(f"Command: {args.command}", attrs=["bold"]))
        log.info("")
        command_object.execute(args)
        log.info("")
    except Exception as e:
        log.error(f"An unexpected error occurred, traceback follows")
        log.info("")
        log.info(traceback.format_exc())
        exit(1)
