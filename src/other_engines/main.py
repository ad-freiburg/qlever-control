#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

# Copyright 2024, University of Freiburg,
# Chair of Algorithms and Data Structures
# Author: Tanmay Garg

from __future__ import annotations

import sys
import traceback
from importlib import import_module
from pathlib import Path

from termcolor import colored

from other_engines.config import ArgumentsManager
from qlever.config import ConfigException
from qlever.log import log, log_levels


def main():
    selected_engine = Path(sys.argv[0]).stem[1:]
    engine_class_name = selected_engine.capitalize()
    module_path = f"other_engines.engines.{selected_engine}"
    try:
        module = import_module(module_path)
    except ImportError as e:
        raise Exception(
            f"Could not import module {module_path} "
            f"for engine {selected_engine}: {e}"
        )

    engine_class = getattr(module, engine_class_name)()

    # Parse the command line arguments and read the Configfile
    try:
        engine_config = ArgumentsManager(engine=engine_class)
        args = engine_config.parse_args()
    except ConfigException as e:
        log.error(e)
        log.info("")
        log.info(traceback.format_exc())
        exit(1)

    # Execute the command.
    command = f"{args.command.replace('-', '_')}_command"
    log.setLevel(log_levels[args.log_level])
    try:
        log.info("")
        log.info(colored(f"Command: {command}", attrs=["bold"]))
        log.info("")
        commandWasSuccesful = getattr(engine_class, command)(args)
        log.info("")
        if not commandWasSuccesful:
            exit(1)
    except KeyboardInterrupt:
        log.info("")
        log.info("Ctrl-C pressed, exiting ...")
        log.info("")
        exit(1)
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")
        log.info("")
        log.info(traceback.format_exc())
        exit(1)
