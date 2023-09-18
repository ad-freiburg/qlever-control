#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import sys
import argparse
from src.qlever_cmd import parser
from src.qlever_docker import is_docker_installed, docker_version
from src.qlever_native import alive_check
from src.qlever_config import print_config, list_config_names

# TODO: logger


USAGE_AUTO_COMPLETE = """
Enable Autocompletion in your current shell:
$ eval "$(register-python-argcomplete qleverkontrol)"

Or globally (edits your ~/.zshenv AND ~/.bash_complete):
$ activate-global-python-argcomplete
"""

# TODO: align properly
USAGE_HEALTH = f"""
* Docker installed: {is_docker_installed()}
* Docker engine version : {docker_version()}
* QLever server is running? : {alive_check(7001)}
"""


USAGE_CONFIG_NAMES = "\n".join(map(lambda x: f"* {x}", list_config_names()))


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
            print(USAGE_AUTO_COMPLETE)
        case argparse.Namespace(health=True):
            print(USAGE_HEALTH)
        case argparse.Namespace(lsconfigs=True):
            print(USAGE_CONFIG_NAMES)
        case argparse.Namespace(config=c) if c is not None:
            print(print_config(c))
        case argparse.Namespace(docker_action=a) if a is not None:
            match a:
                case "up":
                    # docker_run()
                    pass
                case "down":
                    pass
                case "stats":
                    pass


if __name__ == "__main__":
    main_run()
