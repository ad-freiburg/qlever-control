from __future__ import annotations

import glob
import shlex

from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import run_command
from qoxigraph.commands import start


class StartCommand(start.StartCommand):
    def __init__(self):
        self.script_name = "qvirtuoso"

    def description(self) -> str:
        return (
            "Start the server for Virtuoso (must be done before building an "
            "index for Virtuoso) (Runs in a container)"
        )

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name", "format"],
            "index": ["input_files",],
            "server": ["host_name", "port"],
            "runtime": ["system", "image", "server_container"],
        }

    def execute(self, args) -> bool:
        system = args.system
        dataset = args.name

        server_container = args.server_container

        port = int(args.port)
        run_subcommand = "run --restart=unless-stopped"
        if not args.run_in_foreground:
            run_subcommand += " -d"
        start_cmd = Containerize().containerize_command(
            cmd="",
            container_system=system,
            run_subcommand=run_subcommand,
            image_name=args.image,
            container_name=server_container,
            volumes=[("$(pwd)", "/database")],
            ports=[(port, 8890)],
            use_bash=False,
        )

        # Show the command line.
        self.show(start_cmd, only_show=args.show)
        if args.show:
            return True

        # Check if all of the input files exist.
        for pattern in shlex.split(args.input_files):
            if len(glob.glob(pattern)) == 0:
                log.error(f'No file matching "{pattern}" found')
                log.info("")
                log.info(
                    f"Did you call `{self.script_name} get-data`? If you did, "
                    "check GET_DATA_CMD and INPUT_FILES in the Qleverfile"
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

        # Run the start command.
        try:
            run_command(start_cmd, show_output=True)
            log.info(
                f"Virtuoso server webapp for {dataset} will be available at "
                f"http://{args.host_name}:{port}"
            )
            log.info("")
            log.info(
                f"Call `{self.script_name} index` after this to build the "
                f"index for {args.name}"
            )
            log.info("")
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
            log.error(f"Starting the Virtuoso server failed: {e}")
            return False

        return True
