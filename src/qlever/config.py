from __future__ import annotations

import argparse
import os
import traceback
from pathlib import Path

import argcomplete

from qlever import command_objects
from qlever.log import log
from qlever.qleverfile import Qleverfile


# Simple exception class for configuration errors (the class need not do
# anything, we just want a distinct exception type).
class ConfigException(Exception):
    def __init__(self, message):
        stack = traceback.extract_stack()[-2]  # Caller's frame.
        self.filename = stack.filename
        self.lineno = stack.lineno
        full_message = f"{message} [in {self.filename}:{self.lineno}]"
        super().__init__(full_message)


class QleverConfig:
    """
    Class that manages all config parameters, and overwrites them with the
    settings from a Qleverfile.

    IMPORTANT: An instance of this class is created for each execution of
    the `qlever` script, in particular, each time the user triggers
    autocompletion. Therefore, pay attention that no unnecessary work is done
    before the call to `argcomplete.autocomplete(...)`. In particular, avoid
    parsing the Qleverfile before that point, it's not needed for
    autocompletion.
    """

    def add_subparser_for_command(self, subparsers, command_name,
                                  command_object, all_qleverfile_args,
                                  qleverfile_config=None):
        """
        Add subparser for the given command. Take the arguments from
        `command_object.relevant_qleverfile_arguments()` and report an error if
        one of them is not contained in `all_qleverfile_args`. Overwrite the
        default values with the values from `qleverfile_config` if specified.
        """

        arg_names = command_object.relevant_qleverfile_arguments()

        # Helper function that shows a detailed error messahe when an argument
        # from `relevant_qleverfile_arguments` is not contained in
        # `all_qleverfile_args`.
        def argument_error(prefix):
            log.info("")
            log.error(f"{prefix} in `Qleverfile.all_arguments()` for command "
                      f"`{command_name}`")
            log.info("")
            log.info(f"Value of `relevant_qleverfile_arguments` for "
                     f"command `{command_name}`:")
            log.info("")
            log.info(f"{arg_names}")
            log.info("")
            exit(1)

        # Add the subparser.
        description = command_object.description()
        subparser = subparsers.add_parser(command_name,
                                          description=description,
                                          help=description)

        # Add the arguments relevant for the command.
        for section in arg_names:
            if section not in all_qleverfile_args:
                argument_error(f"Section `{section}` not found")
            for arg_name in arg_names[section]:
                if arg_name not in all_qleverfile_args[section]:
                    argument_error(f"Argument `{arg_name}` of section "
                                   f"`{section}` not found")
                args, kwargs = all_qleverfile_args[section][arg_name]
                # If `qleverfile_config` is given, add info about default
                # values to the help string.
                if qleverfile_config is not None:
                    default_value = kwargs.get("default", None)
                    qleverfile_value = qleverfile_config.get(
                            section, arg_name, fallback=None)
                    if qleverfile_value is not None:
                        kwargs["default"] = qleverfile_value
                        kwargs["required"] = False
                        kwargs["help"] += (f" [default, from Qleverfile:"
                                           f" {qleverfile_value}]")
                    else:
                        kwargs["help"] += f" [default: {default_value}]"
                subparser.add_argument(*args, **kwargs)

        # Additional arguments for the command.
        command_object.additional_arguments(subparser)
        subparser.add_argument("--show", action="store_true",
                               default=False,
                               help="Only show what would be executed"
                                    ", but don't execute it")

    def parse_args(self):
        # Determine whether we are in autocomplete mode or not.
        autocomplete_mode = "COMP_LINE" in os.environ

        # Create a temporary parser only to parse the `--qleverfile` option, in
        # case it is given. This is because in the actual parser below we want
        # the values from the Qleverfile to be shown in the help strings.
        def add_qleverfile_option(parser):
            parser.add_argument(
                    "--qleverfile", "-q", type=str, default="Qleverfile",
                    help="The Qleverfile to use (default: Qleverfile)")
        qleverfile_parser = argparse.ArgumentParser(add_help=False)
        add_qleverfile_option(qleverfile_parser)
        qleverfile_args, _ = qleverfile_parser.parse_known_args()
        qleverfile_path_name = qleverfile_args.qleverfile

        # Check if the Qleverfile exists and if we are using the default name.
        # We need this again further down in the code, so remember it.
        qleverfile_path = Path(qleverfile_path_name)
        qleverfile_exists = qleverfile_path.is_file()
        qleverfile_is_default = qleverfile_path_name \
            == qleverfile_parser.get_default("qleverfile")
        # If a Qleverfile with a non-default name was specified, but it does
        # not exist, that's an error.
        if not qleverfile_exists and not qleverfile_is_default:
            raise ConfigException(f"Qleverfile with non-default name "
                                  f"`{qleverfile_path_name}` specified, "
                                  f"but it does not exist")
        # If it exists and we are not in the autocompletion mode, parse it.
        #
        # IMPORTANT: No need to parse the Qleverfile in autocompletion mode and
        # it would be unnecessarily expensive to do so.
        if qleverfile_exists and not autocomplete_mode:
            qleverfile_config = Qleverfile.read(qleverfile_path)
        else:
            qleverfile_config = None

        # Now the regular parser with commands and a subparser for each
        # command. We have a dedicated class for each command. These classes
        # are defined in the modules in `qlever/commands`. In `__init__.py`
        # an object of each class is created and stored in `command_objects`.
        parser = argparse.ArgumentParser()
        add_qleverfile_option(parser)
        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = True
        all_args = Qleverfile.all_arguments()
        for command_name, command_object in command_objects.items():
            self.add_subparser_for_command(
                    subparsers, command_name, command_object,
                    all_args, qleverfile_config)

        # Enable autocompletion for the commands and their options.
        #
        # NOTE: All code executed before this line should be relatively cheap
        # because it is executed whenever the user triggers the autocompletion.
        argcomplete.autocomplete(parser, always_complete_options="long")

        # Parse the command line arguments.
        args = parser.parse_args()

        # If the command says that we should have a Qleverfile, but we don't,
        # issue a warning.
        if command_objects[args.command].should_have_qleverfile():
            if not qleverfile_exists:
                log.warning(f"Invoking command `{args.command}` without a "
                            "Qleverfile. You have to specify all required "
                            "arguments on the command line. This is possible, "
                            "but not recommended.")

        return args
