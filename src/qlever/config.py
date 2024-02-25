import argparse
import argcomplete
from qlever import command_classes
from configparser import ConfigParser, ExtendedInterpolation
from pathlib import Path
from qlever.log import log
import os
import sys
import shlex
import traceback


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
    autocompletion. It's initialization should therefore be lightweight. In
    particular, the functions `all_arguments()` and `parse_qleverfile()` should
    not be called in the constructor, but only when needed (which is, when the
    user has already committed to a command).
    """

    def all_arguments(self):
        """
        Define all possible parameters. A value of `None` means that there is
        no default value, and the parameter is mandatory in the Qleverfile (or
        must be specified via the command line).
        """

        # Helper function that takes a list of positional arguments and a list
        # of keyword arguments and returns a tuple of both. That way, we can
        # defined arguments below with exactly the same syntax as we would for
        # `argparse.add_argument`.
        def arg(*args, **kwargs):
            return (args, kwargs)

        all_args = {}
        data_args = all_args["data"] = {}
        index_args = all_args["index"] = {}
        server_args = all_args["server"] = {}
        runtime_args = all_args["runtime"] = {}
        ui_args = all_args["ui"] = {}

        data_args["name"] = arg(
                "--name", type=str, required=True,
                help="The name of the dataset")
        data_args["get_data_cmd"] = arg(
                "--get-data-cmd", type=str, required=True,
                help="The command to get the data")
        data_args["index_description"] = arg(
                "--index-description", type=str, required=True,
                help="A description of the index")

        index_args["cat_files"] = arg(
                "--cat-files", type=str, required=True,
                help="The command that produces the input")
        index_args["settings_json"] = arg(
                "--settings-json", type=str, default="{}",
                help="The `.settings.json` file for the index")

        server_args["port"] = arg(
                "--port", type=int, required=True,
                help="The port on which the server listens for requests")
        server_args["access_token"] = arg(
                "--access-token", type=str, default=None,
                help="The access token for privileged operations")
        server_args["memory_for_queries"] = arg(
                "--memory-for-queries", type=str, default="1G",
                help="The maximal memory allowed for query processing")

        runtime_args["environment"] = arg(
                "--environment", type=str,
                choices=["docker", "podman", "native"],
                default="docker",
                help="The runtime environment for the server")

        ui_args["port"] = arg(
                "--port", type=int, default=7000,
                help="The port of the Qlever UI web app")

        return all_args

    def parse_qleverfile(self, qleverfile_path):
        """
        Parse the given Qleverfile (the function assumes that it exists) and
        return a `ConfigParser` object with all the options and their values.

        NOTE: The keys have the same hierarchical structure as the keys in
        `all_arguments()`. The Qleverfile may contain options that are not
        defined in `all_arguments()`. They can be used as temporary variables
        to define other options, but cannot be accessed by the commands later.
        """

        config = ConfigParser(interpolation=ExtendedInterpolation())
        try:
            config.read(qleverfile_path)
            return config
        except Exception as e:
            raise ConfigException(f"Error parsing {qleverfile_path}: {e}")

    def add_arguments_to_subparser(self, subparser, arg_names, all_args,
                                   qleverfile_config):
        """
        Add the specified arguments to the given subparser. Take the default
        values from `all_arguments()` and overwrite them with the values from
        the `Qleverfile`, in case it exists.

        IMPORTANT: Don't call this function repeatedly (in particular, not for
        every command, but only for the command for which it is needed), it's
        not cheap.
        """

        for section in arg_names:
            if section not in all_args:
                raise ConfigException(f"Section '{section}' not found")
            for arg_name in arg_names[section]:
                if arg_name not in all_args[section]:
                    raise ConfigException(f"Argument '{arg_name}' not found "
                                          f"in section '{section}'")
                args, kwargs = all_args[section][arg_name]
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

    def get_command_line_arguments(self):
        """
        Get the current command line arguments.

        NOTE: This should work both when the script is called "normally" (in
        which case, we can just use `sys.argv`), as well as when it is called
        by the shell's autocompletion mechanism (in which case, the command
        line is in the environment variable `COMP_LINE`).
        """
        if "COMP_LINE" in os.environ:
            # Note: `COMP_LINE` is a string, with spaces used to separate the
            # arguments and spaces within arguments escaped with a backslash.
            return shlex.split(os.environ["COMP_LINE"])
        else:
            return sys.argv

    def parse_args(self):
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

        # If this is the normal execution of the script (and not a call invoked
        # by the shell's autocompletion mechanism), parse the Qleverfile.
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
        # If it exists and we arenot in the autocompletion mode, parse it.
        if qleverfile_exists and "COMP_LINE" not in os.environ:
            qleverfile_config = self.parse_qleverfile(qleverfile_path)
        else:
            qleverfile_config = None

        # Now the regular parser with commands and a subparser for each
        # command. We have a dedicated class for each command, these classes
        # are defined in the modules in the `qlever/commands` directory and
        # dynamically imported in `__init__.py`.
        parser = argparse.ArgumentParser()
        add_qleverfile_option(parser)
        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = True
        all_args = self.all_arguments()
        for command_name, command_class in command_classes.items():
            help_text = command_class.help_text()
            subparser = subparsers.add_parser(command_name, help=help_text)
            arg_names = command_class.relevant_arguments()
            self.add_arguments_to_subparser(subparser, arg_names, all_args,
                                            qleverfile_config)

        # Enable autocompletion for the commands and their options.
        #
        # NOTE: All code executed before this line should be relatively cheap
        # because it is executed whenever the user triggers the autocompletion.
        argcomplete.autocomplete(parser, always_complete_options="long")

        # Parse the command line arguments.
        args = parser.parse_args()

        # If the command says that we should have a Qleverfile, but we don't,
        # issue a warning.
        if command_classes[args.command].should_have_qleverfile():
            if not qleverfile_exists:
                log.warning(f"Invoking command `{args.command}` without a "
                            "Qleverfile. You have to specify all required "
                            "arguments on the command line. This is possible, "
                            "but not recommended.")

        return args
