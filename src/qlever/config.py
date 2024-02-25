import argparse
import argcomplete
from qlever import command_classes
from pathlib import Path
import os
import sys
import shlex


# Simple exception class for configuration errors (the class need not do
# anything, we just want a distinct exception type).
class ConfigException(Exception):
    pass


# Class that manages all config parameters, and overwrites them with the
# settings from a Qleverfile.
class QleverConfig:

    @staticmethod
    def all_arguments():
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

        arguments = {}
        data_args = arguments["data"] = {}
        index_args = arguments["index"] = {}
        server_args = arguments["server"] = {}
        runtime_args = arguments["runtime"] = {}
        ui_args = arguments["ui"] = {}

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

        return arguments

    @staticmethod
    def parse_args():
        # Add subparser for each command via the `add_subparser` method of the
        # corresponding command class (the classes are loaded dynamically in
        # `__init__.py`).
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = True
        for command in command_classes:
            command_classes[command].add_subparser(subparsers)

        # Only if the user has typed a command, do we add the arguments for
        # the respective subparser (which entails parsing the Qleverfile).
        #
        # NOTE 1: We don't want to do this for every command because this has to
        # be done whenever the user triggers autocompletion. Also, this parses
        # the Qleverfile, and there is no need for that before a command has
        # been chosen.
        # 
        # NOTE 2: This code can be reached in two different ways: either in the
        # "normal" way, e.g. when the user types `qlever index --help`, or in
        # the "autocompletion" way, e.g. when the user types `qlever index
        # --<TAB>`, and the shell's completion function is called. In the
        # latter case, the command line is stored in the environment variable
        # `COMP_LINE`.
        try:
            argv = shlex.split(os.environ["COMP_LINE"])
        except KeyError:
            argv = sys.argv
        if len(argv) > 1:
            command_name = argv[1]
            if command_name in command_classes:
                command_class = command_classes[command_name]
                subparser = subparsers.choices[command_name]
                command_arguments = command_class.arguments()
                all_arguments = QleverConfig.all_arguments()
                for section in command_arguments:
                    if section not in all_arguments:
                        raise ConfigException(f"Section '{section}' not found")
                    for arg_name in command_arguments[section]:
                        if arg_name not in all_arguments[section]:
                            raise ConfigException(
                                    f"Argument '{arg_name}' not found in section '{section}'")
                        args, kwargs = all_arguments[section][arg_name]
                        subparser.add_argument(*args, **kwargs)

        # Enable autocompletion for the commands as well as for the command
        # options.
        #
        # NOTE: It is important that all code that is executed before this line
        # is relatively cheap because it is executed whenever the user presses
        # the key (usually TAB) that invokes autocompletion.
        argcomplete.autocomplete(parser, always_complete_options="long")
    
        # Parse the command line arguments and return them.
        return parser.parse_args()
