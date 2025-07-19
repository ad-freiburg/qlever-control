from __future__ import annotations

import subprocess
import time
from pathlib import Path

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import binary_exists, is_server_alive, run_command


class StartCommand(QleverCommand):
    def __init__(self):
        self.script_name = "qjena"

    def description(self) -> str:
        return (
            "Start the server for Jena (requires that you have built an "
            "index before)"
        )

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name"],
            "server": [
                "host_name",
                "jvm_args",
                "port",
                "server_binary",
                "timeout",
            ],
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
    def wrap_cmd_in_container(args, cmd: str) -> str:
        run_subcommand = "run --restart=unless-stopped"
        if not args.run_in_foreground:
            run_subcommand += " -d"
        if not args.run_in_foreground:
            cmd = f"{cmd} > {args.name}.server-log.txt 2>&1"
        return Containerize().containerize_command(
            cmd=cmd,
            container_system=args.system,
            run_subcommand=run_subcommand,
            image_name=args.image,
            container_name=args.server_container,
            volumes=[("$(pwd)", "/opt/data")],
            working_directory="/opt/data",
            ports=[(args.port, args.port)],
        )

    def execute(self, args) -> bool:
        try:
            timeout_ms = int(args.timeout[:-1]) * 1000
        except ValueError as e:
            log.error(f"Invalid timeout value {args.timeout}. Error: {e}")
            return False

        start_cmd = (
            f'env JVM_ARGS="{args.jvm_args}" {args.server_binary} '
            f"--port {args.port} --timeout {timeout_ms} --loc index /{args.name}"
        )

        if args.system == "native":
            if not args.run_in_foreground:
                start_cmd = (
                    f"nohup {start_cmd} > {args.name}.server-log.txt 2>&1 &"
                )
        else:
            start_cmd = self.wrap_cmd_in_container(args, start_cmd)

        # Show the command line.
        self.show(start_cmd, only_show=args.show)
        if args.show:
            return True

        # When running natively, check if the binary exists and works.
        if args.system == "native":
            if not binary_exists(args.server_binary, "server-binary"):
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

        index_dir = Path("index/Data-0001")
        if not index_dir.exists() or not any(index_dir.iterdir()):
            log.info(f"No Jena index files for {args.name} found! ")
            log.info(
                f"Did you call `{self.script_name} index`? If you did, check "
                "if index files are present in index/Data-0001 directory"
            )
            return False

        endpoint_url = f"http://{args.host_name}:{args.port}/{args.name}/query"
        if is_server_alive(url=endpoint_url):
            log.error(f"Jena server already running on {endpoint_url}\n")
            log.info(
                f"To kill the existing server, use `{self.script_name} stop`"
            )
            return False

        try:
            process = run_command(
                start_cmd,
                use_popen=args.run_in_foreground,
            )
        except Exception as e:
            log.error(f"Starting the Jena server failed ({e})")
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
        log_cmd = f"exec tail -f {args.name}.server-log.txt"
        log_proc = subprocess.Popen(log_cmd, shell=True)
        while not is_server_alive(endpoint_url):
            time.sleep(1)

        log.info(
            f"Jena server webapp for {args.name} will be available at "
            f"http://{args.host_name}:{args.port} and the sparql endpoint for "
            f"queries is {endpoint_url}"
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
