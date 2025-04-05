from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import is_server_alive, run_command


class StartCommand(QleverCommand):
    def __init__(self):
        self.script_name = "qvirtuoso"

    def description(self) -> str:
        return (
            "Start the server for Virtuoso (must be done before building an "
            "index for Virtuoso)"
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
        subparser.add_argument(
            "--server-binary",
            type=str,
            default="virtuoso-t",
            help=(
                "The binary for starting the server (default: virtuoso-t) "
                "(this requires that you have virtuoso binaries installed "
                "on your machine)"
            ),
        )

    @staticmethod
    def wrap_cmd_in_container(args) -> str:
        run_subcommand = "run --restart=unless-stopped"
        if not args.run_in_foreground:
            run_subcommand += " -d"
        return Containerize().containerize_command(
            cmd="",
            container_system=args.system,
            run_subcommand=run_subcommand,
            image_name=args.image,
            container_name=args.server_container,
            volumes=[("$(pwd)", "/database")],
            ports=[(args.port, args.port)],
            use_bash=False,
        )

    def execute(self, args) -> bool:
        if args.system == "native":
            start_cmd = args.server_binary
            if args.run_in_foreground:
                start_cmd += " -f"
        else:
            start_cmd = self.wrap_cmd_in_container(args)

        # Show the command line.
        self.show(start_cmd, only_show=args.show)
        if args.show:
            return True

        endpoint_url = f"http://{args.host_name}:{args.port}/sparql"

        # When running natively, check if the binary exists and works.
        if args.system == "native":
            if not shutil.which(args.server_binary):
                log.error(
                    f'Running "{args.server_binary}" failed, '
                    "set `--server-binary` to a different binary or "
                    "set `--system to a container system`"
                )
                return False
        else:
            if Containerize().is_running(args.system, args.server_container):
                log.error(
                    f"Server container {args.server_container} already exists!\n"
                )
                log.info(
                    f"To kill the existing server, use `{self.script_name} stop`"
                )
                return False

        # Check if index db virtuoso.db present in cwd
        if not Path("virtuoso.db").exists():
            log.error(f"No Virtuoso index db for {args.name} found!\n")
            log.info(
                f"Did you call `{self.script_name} index`? If you did, check "
                "if virtuoso.db is present in current working directory."
            )
            return False

        if is_server_alive(url=endpoint_url):
            log.error(f"Virtuoso server already running on {endpoint_url}\n")
            log.info(
                f"To kill the existing server, use `{self.script_name} stop`"
            )
            return False

        # Run the start command.
        try:
            run_command(start_cmd, show_output=True)
            log.info(
                f"Virtuoso server webapp for {args.name} will be available "
                f"at http://{args.host_name}:{args.port} and the sparql "
                f"endpoint for queries is http://{args.host_name}:{args.port}/sparql"
            )
            log.info("")
            if args.run_in_foreground:
                log.info(
                    "Follow the log as long as the server is"
                    " running (Ctrl-C stops the server)"
                )
            else:

        try:
            process = run_command(
                start_cmd,
                use_popen=args.run_in_foreground,
            )
        except Exception as e:
            log.error(f"Starting the Virtuoso server failed ({e})")
            return False

        # Tail the server log until the server is ready (note that the `exec`
        # is important to make sure that the tail process is killed and not
        # just the bash process).
        if args.run_in_foreground:
            log.info(
                "Follow the server logs as long as the server is"
                " running (Ctrl-C stops the server)"
            )
        else:
            log.info(
                "Follow the server logs until the server is ready"
                " (Ctrl-C stops following the log, but NOT the server)"
            )
        log.info("")
        log_cmd = "tail -f virtuoso.log"
        log_proc = subprocess.Popen(log_cmd, shell=True)
        while not is_server_alive(endpoint_url):
            time.sleep(1)

        log.info(
            f"Virtuoso server webapp for {args.name} will be available "
            f"at http://{args.host_name}:{args.port} and the sparql "
            f"endpoint for queries is http://{args.host_name}:{args.port}/sparql"
        )

        # Kill the log process
        if not args.run_in_foreground:
            log_proc.terminate()

        # With `--run-in-foreground`, wait until the server is stopped.
        if args.run_in_foreground:
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
            log_proc.terminate()

        return True
