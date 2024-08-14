#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

# Copyright 2024, University of Freiburg,
# Chair of Algorithms and Data Structures
# Author: Hannah Bast <bast@cs.uni-freiburg.de>

from __future__ import annotations

import re
import traceback

from termcolor import colored

import qlever.globals
from qlever import command_objects
from qlever.config import ConfigException, QleverConfig
from qlever.log import log, log_levels


def main():
    # Parse the command line arguments and read the Qleverfile.
    try:
        qlever_config = QleverConfig()
        args, qlever.globals.qleverfile_path, \
            qlever.globals.qleverfile_config, \
            qlever.globals.envvars_config = qlever_config.parse_args()
    except ConfigException as e:
        log.error(e)
        log.info("")
        log.info(traceback.format_exc())
        exit(1)

    # Execute the command.
    command_object = command_objects[args.command]
    log.setLevel(log_levels[args.log_level])
    try:
        log.info("")
        log.info(colored(f"Command: {args.command}", attrs=["bold"]))
        log.info("")
        # If the command says that we should have a Qleverfile, but we don't,
        # issue a warning.
        if command_objects[args.command].should_have_qleverfile():
            if qlever.globals.qleverfile_path:
                log.info(f"Invoking command with config from "
                         f"`{qlever.globals.qleverfile_path}` "
                         f"(use `qlever config --show-qleverfile` "
                         f"to see the effective config, or "
                         f"edit the file to change it).")
            else:
                if qlever.globals.envvars_config:
                    log.info("Invoking command without a Qleverfile, but "
                             "with environment variables (use `qlever "
                             "config --show-envvars` to see them and `qlever "
                             "config --unset-envvars` to unset them).")
                else:
                    log.warning("Invoking command with neither a Qleverfile "
                                "nor environment variables. You have to "
                                "specify all required arguments on the "
                                "command line. This is possible, but not "
                                "recommended.")
            log.info("")
        command_object.execute(args)
        log.info("")
    except KeyboardInterrupt:
        log.info("")
        log.info("Ctrl-C pressed, exiting ...")
        log.info("")
        exit(0)
    except Exception as e:
        # Check if it's a certain kind of `AttributeError` and give a hint in
        # that case.
        match_error = re.search(r"object has no attribute '(.+)'", str(e))
        match_trace = re.search(r"(qlever/commands/.+\.py)\", line (\d+)",
                                traceback.format_exc())
        if isinstance(e, AttributeError) and match_error and match_trace:
            attribute = match_error.group(1)
            trace_command = match_trace.group(1)
            trace_line = match_trace.group(2)
            log.error(f"{e} in `{trace_command}` at line {trace_line}")
            log.info("")
            log.info(f"Likely cause: you used `args.{attribute}`, but it was "
                     f"neither defined in `relevant_qleverfile_arguments` "
                     f"nor in `additional_arguments`")
            log.info("")
            log.info(f"If you did not implement `{trace_command}` yourself, "
                     f"please report this issue")
            log.info("")
        else:
            log.error(f"An unexpected error occurred: {e}")
            log.info("")
            log.info(traceback.format_exc())
        exit(1)
