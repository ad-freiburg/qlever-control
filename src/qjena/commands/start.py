from __future__ import annotations

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import run_command


class StartCommand(QleverCommand):
    def __init__(self):
        self.script_name = "qjena"

    def description(self) -> str:
        return (
            "Start the server for Jena (requires that you have built an "
            "index before) (Runs in a container)"
        )

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name"],
            "server": ["host_name", "port"],
            "runtime": ["system", "image", "server_container"],
        }

    def additional_arguments(self, subparser):
        subparser.add_argument(
            "--run-in-foreground",
            action="store_true",
            default=False,
            help=(
                "Run the start command in the foreground "
                "(default: run in the background)"
            ),
        )

    @staticmethod
    def is_data_loading(system: str, container: str) -> bool:
        """
        Check if `index` command is still running and data loading
        is in progress
        """
        check_index_running_cmd = (
            f"{system} exec {container} bash -c "
            "\"test -f /opt/loading.flag && echo 'running' || "
            "echo 'finished'\""
        )
        index_ps_running = run_command(
            check_index_running_cmd, return_output=True
        )
        return index_ps_running.strip() == "running"

    @staticmethod
    def index_exists(system: str, container: str) -> bool:
        """
        Check if the index was built correctly and the index folder Data-0001
        exists in /opt/index directory in the container
        """
        check_index_cmd = (
            f"{system} exec {container} bash -c "
            "\"test -d /opt/index && test -d /opt/index/Data-0001 "
            "&& echo 'exists' || echo 'missing'\""
        )
        index_exists = run_command(check_index_cmd, return_output=True)
        return index_exists.strip() == "exists"

    @staticmethod
    def is_server_alive(url: str) -> bool:
        """
        Check if the Jena server is already alive at the given endpoint url
        """
        check_server_cmd = (
            f"curl -s {url} && echo 'alive' || echo 'not'"
        )
        is_server_alive = run_command(check_server_cmd, return_output=True)
        return "alive" in is_server_alive.strip()

    def execute(self, args) -> bool:
        system = args.system
        dataset = args.name

        server_container = args.server_container

        port = int(args.port)
        exec_cmd = (
            f"{system} exec {'-d ' if not args.run_in_foreground else ''}"
            f"{server_container} bash -c "
        )
        serve_cmd = (
            '"java -jar /opt/apache-jena-fuseki/fuseki-server.jar --port 3030 '
            f'--loc /opt/index /{args.name} > /opt/data/server.log 2>&1 &"'
        )
        start_cmd = exec_cmd + serve_cmd

        # Show the command line.
        self.show(start_cmd, only_show=args.show)
        if args.show:
            return True

        # Warn if server container not running (i.e. index not built)
        if not Containerize().is_running(system, server_container):
            log.error(
                f"{system} container {server_container} does not exist! "
                f"Did you call `{self.script_name} index`?"
            )
            return False
        # Check if index process ongoing
        if self.is_data_loading(system, server_container):
            log.error(
                "Data loading is in progress. Please wait...\n"
                f"Check status of {server_container} with "
                f"`{self.script_name} log`"
            )
            return False

        # Check if index folder Data-0001 missing
        if not self.index_exists(system, server_container):
            log.error(
                f"Index folder Data-0001 missing in {system} container "
                f"{server_container}! Did you call "
                f"`{self.script_name} index`?"
            )
            return False

        # Check and warn if server already running
        endpoint_url = f"http://{args.host_name}:{port}"
        server_url = f"{endpoint_url}/{args.name}/query"
        if self.is_server_alive(server_url):
            log.error(f"Jena server already running on {server_url}")
            log.info(
                f"To kill the existing server, use `{self.script_name} stop` "
            )
            return False

        # Run the start command.
        try:
            run_command(start_cmd, show_output=True)
            log.info(
                f"Jena server webapp for {dataset} will be available at "
                f"{endpoint_url} and the sparql endpoint for "
                f"queries is {server_url}"
            )
            if args.run_in_foreground:
                log.info(
                    "Follow the log as long as the server is"
                    " running (Ctrl-C stops the server)"
                )
            else:
                log.info(
                    f"Follow `{self.script_name} log` until the server is ready"
                    f" (Ctrl-C stops following the log, but NOT the server)"
                )
        except Exception as e:
            log.error(f"Starting the Jena server failed: {e}")
            return False

        return True
