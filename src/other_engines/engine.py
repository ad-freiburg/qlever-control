from __future__ import annotations

import inspect
import re
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from termcolor import colored

from qlever.commands.example_queries import ExampleQueriesCommand
from qlever.commands.get_data import GetDataCommand
from qlever.commands.query import QueryCommand
from qlever.commands.stop import stop_container
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import get_random_string


class SparqlEngine(ABC):
    """
    A base class for SparqlEngine != QLever
    The class holds engine_name and a dict {command_name: command_description}
    The command names and description are automatically taken from functions
    that end with "_command" and their docstring.
    !! Make sure to have trailing __command only for functions that represent
    a command being executed.
    Most common functions that are shared between different engines are
    implemented here, but can be overriden in child classes.
    Only container based setup is supported for now!
    """

    def __init__(self, engine_name: str) -> None:
        self.engine_name = engine_name
        self.commands = self.get_command_dict()
        self.configfiles_path = Path(__file__).parent / "Configfiles"
        self.configfile_path = Path(f"{self.engine_name}file")

    def get_command_dict(self) -> dict[str, str]:
        """
        Get a dictionary for all commands supported by this Engine
        {command_name: command_description}
        Command name is taken from command functions without the "_command"
        Command description is taken from the command function docstring.
        """
        command_dict = {}
        for name, method in inspect.getmembers(
            self.__class__, predicate=inspect.isfunction
        ):
            if name.endswith("_command"):
                docstring = inspect.getdoc(getattr(self.__class__, name)) or ""
                clean_docstring = re.sub(r"\s+", " ", docstring.strip())
                clean_docstring = clean_docstring.replace(
                    "Configfile", f"{self.engine_name}file"
                )
                command_name = name[: -len("_command")].replace("_", "-")
                command_dict[command_name] = clean_docstring
        return command_dict

    def command_should_have_configfile(self, command: str) -> bool:
        """
        Return `True` if the command should have a Configfile, `False`
        otherwise. If a command should have a Configfile, but none is
        specified, the command can still be executed if all the required
        arguments are specified on the command line, but there will be warning.
        """
        cmds_that_need_configfile = [
            "get-data",
            "index",
            "start",
            "stop",
            "log",
        ]
        return command in cmds_that_need_configfile

    @abstractmethod
    def get_config_arguments(self, command: str) -> dict[str : list[str]]:
        """
        Return the arguments relevant for the passed command. This must be a
        subset of the names of `all_arguments` defined in configfile.py.
        Only these arguments can then be used in the respective command method.
        """
        if command in ("example-queries", "query"):
            return {"server": ["port"]}
        return None

    def additional_arguments(self, command: str, subparser) -> None:
        """
        Add additional command-specific arguments (which are not in
        `configfile.all_arguments` and cannot be specified in the Configfile)
        to the given `subparser`.
        """
        configfile_names = [
            p.name.split(".")[1]
            for p in self.configfiles_path.glob("Configfile.*")
        ]
        if command == "setup-config":
            subparser.add_argument(
                "config_name",
                type=str,
                choices=configfile_names,
                nargs="?",
                default="default",
                help=(
                    f"The name of the pre-configured {self.engine_name}"
                    "file to create [default = default]"
                ),
            )
        if command == "log":
            subparser.add_argument(
                "--tail-num-lines",
                type=int,
                default=20,
                help=(
                    "Show this many of the last lines of the log "
                    "file [default = 20]"
                ),
            )
            subparser.add_argument(
                "--from-beginning",
                action="store_true",
                default=False,
                help="Show all lines of the log file [default = False]",
            )
            subparser.add_argument(
                "--no-follow",
                action="store_true",
                default=False,
                help="Don't follow the log file [default = False]",
            )
        if command == "example-queries":
            subparser.add_argument(
                "--ui_config",
                type=str,
                choices=configfile_names,
                nargs="?",
                default="default",
                help=(
                    "The name of the pre-configured QLever ui_config "
                    "to use to get example queries [default = default]"
                ),
            )
            ExampleQueriesCommand().additional_arguments(subparser)
        if command == "query":
            subparser.add_argument(
                "--access-token",
                type=str,
                help=(
                    "QLever access_token to send privileged commands "
                    "to the server"
                ),
            )
            QueryCommand().additional_arguments(subparser)

    def show(self, command_description: str, only_show: bool = False):
        """
        Helper function that shows the command line or description of an
        action, together with an explanation.
        """

        log.info(colored(command_description, "blue"))
        log.info("")
        if only_show:
            log.info(
                f'You called "q{self.engine_name.lower()} ... --show", '
                "therefore the command is only shown, but not executed "
                '(omit the "--show" to execute it)'
            )

    @staticmethod
    def show_container_logs(log_cmd: str, active_ps: str) -> None:
        """
        Execute a container logs command and show the output for a given
        active process active_ps
        """
        log.info(
            f"Showing logs for {active_ps} command. Press Ctrl-C to stop "
            f"following (will not stop the {active_ps} process)"
        )

        try:
            run_command(log_cmd, show_output=True)
        except Exception as e:
            log.error(f"Cannot display container logs - {e}")

    def setup_config_command(self, args) -> bool:
        """
        Get a pre-configured Configfile for the given engine and config_name
        """
        # Construct the command line and show it.
        configfile_path = (
            self.configfiles_path / f"Configfile.{args.config_name}"
        )
        setup_config_cmd = (
            f"cat {configfile_path}"
            f" | sed -E 's/(^ACCESS_TOKEN.*)/\\1_{get_random_string(12)}/'"
        )
        setup_config_cmd += f"> {self.engine_name}file"
        self.show(setup_config_cmd, only_show=args.show)
        if args.show:
            return True

        # If there is already a Configfile in the current directory, exit.
        if self.configfile_path.is_file():
            log.error(
                f"`{self.engine_name}file` already exists in current directory"
            )
            log.info("")
            log.info(
                f"If you want to create a new {self.engine_name}file using "
                f"`q{self.engine_name.lower()} setup-config`, "
                f"delete the existing {self.engine_name}file first"
            )
            return False

        # Copy the Configfile to the current directory.
        try:
            subprocess.run(
                setup_config_cmd,
                shell=True,
                check=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
        except Exception as e:
            log.error(
                f'Could not copy "{configfile_path}" to current directory: {e}'
            )
            return False

        # If we get here, everything went well.
        log.info(
            f'Created {self.engine_name}file for config "{args.config_name}"'
            f" in current directory"
        )
        return True

    def get_data_command(self, args) -> bool:
        """
        Get data using the GET_DATA_CMD in the Configfile
        """
        GetDataCommand.show = self.show
        return GetDataCommand().execute(args)

    def log_command(self, args) -> bool:
        """
        Show the last lines of the index/server container log and follow it
        """
        system = args.system
        index_container = args.index_container
        server_container = args.server_container

        log_cmd = f"{system} logs "

        if not args.from_beginning:
            log_cmd += f"-n {args.tail_num_lines} "
        if not args.no_follow:
            log_cmd += "-f "

        if Containerize().is_running(system, index_container):
            log_cmd += index_container
            active_ps = "index"
        elif Containerize().is_running(system, server_container):
            log_cmd += server_container
            active_ps = "start"
        else:
            log_cmd = None

        if log_cmd is None:
            log.info(
                f"No running index or start {system} container found!"
                f"Are you sure you called `q{self.engine_name.lower()} index` "
                f"or `q{self.engine_name.lower()} start` "
                "and have a process running?"
            )
            return False

        # Show the command line.
        self.show(log_cmd, only_show=args.show)
        if args.show:
            return True

        self.show_container_logs(log_cmd, active_ps)
        return True

    @abstractmethod
    def index_command(self) -> bool:
        """
        Build the index for a given RDF dataset
        """
        pass

    @abstractmethod
    def start_command(self) -> bool:
        """
        Start the server for given Engine
        """
        pass

    def stop_command(self, args) -> bool:
        """
        Stop the server by stopping and removing the server container
        """
        server_container = args.server_container

        description = f"Checking for container with name {server_container}"
        self.show(description, only_show=args.show)
        if args.show:
            return True

        # First check if container is running and if yes, stop and remove it
        if stop_container(server_container):
            return True

    def example_queries_command(self, args) -> bool:
        """
        Execute queries against a SPARQL endpoint and get runtime information
        """
        ExampleQueriesCommand.show = self.show
        return ExampleQueriesCommand().execute(args)

    def query_command(self, args) -> bool:
        """
        Send a query to a SPARQL endpoint
        """
        QueryCommand.show = self.show
        return QueryCommand().execute(args)
