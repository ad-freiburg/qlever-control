#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

from qlever.config import QleverConfig
from qlever.command import execute_command

def main():
    args = QleverConfig.parse_args()
    execute_command(args.command, args)
