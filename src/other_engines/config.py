from __future__ import annotations

import argparse
import os
from pathlib import Path

import argcomplete
from termcolor import colored

from other_engines.engine import SparqlEngine
from qlever.containerize import Containerize
from qlever.log import log, log_levels
from qlever.qleverfile import Qleverfile


def all_arguments():
    """
    Take all existing arguments from Qleverfile
    and add/replace the ones that are new/different from QLever
    """

    def arg(*args, **kwargs):
        return (args, kwargs)

    all_args = Qleverfile.all_arguments()
    all_args["runtime"]["index_cmd"] = arg(
        "--run-in-foreground",
        action="store_true",
        default=False,
        help=(
            "Run the index command in the foreground "
            "(default: run in the background with `docker run -d`)"
        ),
    )
    all_args["runtime"]["start_cmd"] = arg(
        "--run-in-foreground",
        action="store_true",
        default=False,
        help=(
            "Run the server in the foreground "
            "(default: run in the background with `docker run -d`)"
        ),
    )
    all_args["runtime"]["system"] = arg(
        "--system",
        type=str,
        choices=Containerize.supported_systems(),
        default="docker",
        help=(
            "Which system to use to run commands like `index` "
            "or `start` in a container"
        ),
    )
    all_args["runtime"]["index_container"] = arg(
        "--index-container",
        type=str,
        help="The name of the container used by the index command",
    )
    all_args["runtime"]["server_container"] = arg(
        "--server-container",
        type=str,
        help="The name of the container used by the start command",
    )
    return all_args


class ArgumentsManager:
    SPECIAL_ARGS = ["image", "index_container", "server_container"]

    def __init__(self, engine: SparqlEngine) -> None:
        self.engine = engine
        self.engine_name = engine.engine_name
        self.commands = engine.commands

    def get_default_config_value(self, arg_name: str, config):
        """
        Get default values for SPECIAL_ARGS
        """
        name = config["data"]["name"]
        if arg_name == "image":
            return self.engine.image
        if arg_name == "index_container":
            return f"{self.engine_name.lower()}.index.{name}"
        if arg_name == "server_container":
            return f"{self.engine_name.lower()}.server.{name}"
        return None

    def add_subparser_for_command(
        self,
        subparsers,
        command_name: str,
        description: str,
        config=None,
    ) -> None:
        """
        Add subparser for the given command. Take the arguments from
        `self.engine.get_config_arguments()` and report an error if
        one of them is not contained in `all_arguments`. Overwrite the
        default values with the values from `config` if specified.
        """

        arg_names = self.engine.get_config_arguments(command_name)
        all_configfile_args = all_arguments()

        def argument_error(prefix: str):
            log.info("")
            log.error(
                f"{prefix} in `other_engines.configfile.all_arguments()` "
                f"for command `{command_name}`"
            )
            log.info("")
            log.info(
                f"Value of `get_config_arguments_for_command` "
                f"`{command_name}`:"
            )
            log.info("")
            log.info(f"{arg_names}")
            log.info("")
            exit(1)

        # Add the subparser.
        subparser = subparsers.add_parser(
            command_name, description=description, help=description
        )

        # Add the arguments relevant for the command.
        for section in arg_names:
            if section not in all_configfile_args:
                argument_error(f"Section `{section}` not found")
            for arg_name in arg_names[section]:
                if arg_name not in all_configfile_args[section]:
                    argument_error(
                        f"Argument `{arg_name}` of section "
                        f"`{section}` not found"
                    )
                args, kwargs = all_configfile_args[section][arg_name]
                kwargs_copy = kwargs.copy()
                # If `configfile_config` is given, add info about default
                # values to the help string.
                if config is not None:
                    default_value = kwargs.get("default", None)
                    config_value = (
                        config.get(section, arg_name, fallback=None)
                        if arg_name not in self.SPECIAL_ARGS
                        else self.get_default_config_value(arg_name, config)
                    )
                    if config_value is not None:
                        kwargs_copy["default"] = config_value
                        kwargs_copy["required"] = False
                        kwargs_copy["help"] += (
                            f" [default, from {self.engine_name}file: "
                            f"{config_value}]"
                        )
                    else:
                        kwargs_copy["help"] += f" [default: {default_value}]"
                subparser.add_argument(*args, **kwargs_copy)

        # Additional arguments that are shared by all commands.
        self.engine.additional_arguments(command_name, subparser)
        subparser.add_argument(
            "--show",
            action="store_true",
            default=False,
            help="Only show what would be executed, but don't execute it",
        )
        subparser.add_argument(
            "--log-level",
            choices=log_levels.keys(),
            default="INFO",
            help="Set the log level",
        )

    def parse_args(self):
        # Determine whether we are in autocomplete mode or not.
        autocomplete_mode = "COMP_LINE" in os.environ

        # Check if the user has registered this script for argcomplete.
        argcomplete_check_off = os.environ.get(
            f"{self.engine_name.upper()}_ARGCOMPLETE_CHECK_OFF"
        )
        argcomplete_enabled = os.environ.get(
            f"{self.engine_name.upper()}_ARGCOMPLETE_ENABLED"
        )
        if not argcomplete_enabled and not argcomplete_check_off:
            log.info("")
            log.warning(
                f"To enable autocompletion, run the following command, "
                f"and consider adding it to your `.bashrc` or `.zshrc`:"
                f"\n\n"
                f'eval "$(register-python-argcomplete q{self.engine_name.lower()})"'
                f" && export {self.engine_name.upper()}_ARGCOMPLETE_ENABLED=1"
            )
            log.info("")

        configfile_path = Path(f"{self.engine_name}file")
        configfile_exists = configfile_path.is_file()

        if configfile_exists and not autocomplete_mode:
            try:
                config = Qleverfile.read_qleverfile(configfile_path)
            except Exception as e:
                log.info("")
                log.error(
                    f"Error parsing {self.engine_name}file `{configfile_path}`"
                    f": {e}"
                )
                log.info("")
                exit(1)
        else:
            config = None

        parser = argparse.ArgumentParser(
            description=colored(
                f"This is the q{self.engine_name.lower()} command line tool, "
                f"it's all you need to work with {self.engine_name} in a "
                f"{' or '.join(Containerize.supported_systems())} "
                "container environment",
                attrs=["bold"],
            )
        )
        subparsers = parser.add_subparsers(dest="command")
        subparsers.required = True
        for command_name, description in self.commands.items():
            self.add_subparser_for_command(
                subparsers=subparsers,
                command_name=command_name,
                description=description,
                config=config,
            )

        argcomplete.autocomplete(parser, always_complete_options="long")

        # If called without arguments, show the help message.
        if len(os.sys.argv) == 1:
            parser.print_help()
            exit(0)

        args = parser.parse_args()

        # If the command says that we should have a Qleverfile, but we don't,
        # issue a warning.
        if self.engine.command_should_have_configfile(args.command):
            if not configfile_exists:
                log.warning(
                    f"Invoking command `{args.command}` without a "
                    f"{self.engine_name}file. You have to specify all "
                    "required arguments on the command line. "
                    "This is possible, but not recommended."
                )

        return args
