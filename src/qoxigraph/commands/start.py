from __future__ import annotations

from pathlib import Path

from qlever.commands import start
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import run_command


class StartCommand(start.StartCommand):
    def __init__(self):
        self.script_name = "qoxigraph"

    def description(self) -> str:
        return (
            "Start the server for Oxigraph (requires that you have built an "
            "index before) (Runs in a container)"
        )

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name"],
            "server": [
                "host_name",
                "port",
            ],
            "runtime": [
                "system",
                "image",
                "server_container",
                "index_container",
            ],
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

    def execute(self, args) -> bool:
        system = args.system
        dataset = args.name

        # Check if index and server container still running
        index_container = args.index_container
        server_container = args.server_container
        if Containerize().is_running(system, index_container):
            log.info(
                f"{system} container {index_container} is still up, "
                "which means that data loading is in progress. Please wait...\n"
                f"Check status of {index_container} with `{self.script_name} log`"
            )
            return False

        if Containerize().is_running(system, server_container):
            log.info(
                f"{system} container {server_container} exists, "
                f"which means that server for {dataset} is already running. \n"
                f"Stop the container {server_container} with `{self.script_name} stop` "
                "first before starting a new one."
            )
            return False

        # Check if index files (*.sst) present in cwd
        if len([p.name for p in Path.cwd().glob("*.sst")]) == 0:
            log.info(
                f"No Oxigraph index files for {dataset} found! "
                f"Did you call `{self.script_name} index`? If you did, check "
                "if .sst index files are present in current working directory."
            )
            return False

        port = int(args.port)
        run_subcommand = "run --restart=unless-stopped"
        if not args.run_in_foreground:
            run_subcommand += " -d"
        start_cmd = "serve-read-only --location /index --bind=0.0.0.0:7878"
        start_cmd = Containerize().containerize_command(
            cmd=start_cmd,
            container_system=system,
            run_subcommand=run_subcommand,
            image_name=args.image,
            container_name=server_container,
            volumes=[("$(pwd)", "/index")],
            ports=[(port, 7878)],
            use_bash=False,
        )

        # Show the command line.
        self.show(start_cmd, only_show=args.show)
        if args.show:
            return True

        # Run the start command.
        try:
            run_command(start_cmd, show_output=True)
            log.info(
                f"Oxigraph server webapp for {dataset} will be available at "
                f"http://{args.host_name}:{port} and the sparql endpoint for "
                f"queries is http://{args.host_name}:{port}/query"
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
            log.error(f"Starting the Oxigraph server failed: {e}")
            return False

        return True
