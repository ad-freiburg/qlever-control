#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

# Copyright 2024, University of Freiburg,
# Chair of Algorithms and Data Structures
# Author: Hannah Bast <bast@cs.uni-freiburg.de>

from qlever.config import QleverConfig, ConfigException
from qlever.command import execute_command
from termcolor import colored


def main():
    # Parse the command line arguments and read the Qleverfile.
    try:
        qlever_config = QleverConfig()
        args = qlever_config.parse_args()
    except ConfigException as e:
        print(colored(e, "red"))
        exit(1)

    # Execute the command.
    execute_command(args.command, args)
