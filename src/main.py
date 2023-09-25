#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import sys
import argparse
from src.qlever_cmd import parser
from src.qlever_docker import is_docker_installed, docker_version
from src.qlever_native import alive_check
from src.qlever_config import QleverConfig
from src.qlever_logging import log


# TODO: logger


def _USAGE_AUTO_COMPLETE() -> str:
    return """
Enable Autocompletion in your current shell:
$ eval "$(register-python-argcomplete qleverkontrol)"

Or globally (edits your ~/.zshenv AND ~/.bash_complete):
$ activate-global-python-argcomplete
"""


def _USAGE_HEALTH() -> str:
    # TODO: align properly
    return f"""
* Docker installed: {is_docker_installed()}
* Docker engine version : {docker_version()}
* QLever server is running (port 7001)? : {alive_check(7001)}
"""


def _USAGE_CONFIG_NAMES() -> str:
    return "\n".join(
        map(lambda x: f"* {x}", QleverConfig.show_available_config_names())
    )


def main_run():
    """
    main entry point for the Qlever script
    used in the setup.py console_scripts
    """

    if len(sys.argv) < 2:
        parser.print_usage()
    args = parser.parse_args()
    print(args)

    match args:  # python >= 3.10 (PEP 636)
        case argparse.Namespace(autocomplete=True):
            log.info(_USAGE_AUTO_COMPLETE())
        case argparse.Namespace(health=True):
            log.info(_USAGE_HEALTH())
        case argparse.Namespace(lsconfigs=True):
            log.info(_USAGE_CONFIG_NAMES())
        case argparse.Namespace(setup_config=c) if c is not None:
            QleverConfig.write_config(config_name=c)


if __name__ == "__main__":
    main_run()
