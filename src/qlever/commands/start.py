from __future__ import annotations

import subprocess
import time

from qlever.command import QleverCommand
from qlever.commands.status import StatusCommand
from qlever.commands.stop import StopCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import is_qlever_server_alive, run_command


class StartCommand(QleverCommand):
    """
    Class for executing the `start` command.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return ("Start the QLever server (requires that you have built "
                "an index with `qlever index` before)")

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str: list[str]]:
        return {"data": ["name", "index_description", "text_description"],
                "server": ["server_binary", "port", "access_token",
                           "memory_for_queries", "cache_max_size",
                           "cache_max_size_single_entry",
                           "cache_max_num_entries", "num_threads",
                           "timeout", "only_pso_and_pos_permutations",
                           "use_patterns", "with_text_index"],
                "containerize": ["container_system", "image_name",
                                 "server_container_name"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument("--kill-existing-with-same-name",
                               action="store_true",
                               default=False,
                               help="If a QLever server is already running "
                                    "with the same name, kill it before "
                                    "starting a new server")
        subparser.add_argument("--kill-existing-with-same-port",
                               action="store_true",
                               default=False,
                               help="If a QLever server is already running "
                                    "on the same port, kill it before "
                                    "starting a new server")

    def execute(self, args) -> bool:
        # Kill existing server with the same name if so desired.
        if args.kill_existing_with_same_name:
            args.cmdline_regex = f"^ServerMain.* -i {args.name}"
            args.no_containers = True
            StopCommand().execute(args)
            log.info("")

        # Kill existing server on the same port if so desired.
        if args.kill_existing_with_same_port:
            args.cmdline_regex = f"^ServerMain.* -p {args.port}"
            args.no_containers = True
            StopCommand().execute(args)
            log.info("")

        # Construct the command line based on the config file.
        start_cmd = (f"{args.server_binary}"
                     f" -i {args.name}"
                     f" -j {args.num_threads}"
                     f" -p {args.port}"
                     f" -m {args.memory_for_queries}"
                     f" -c {args.cache_max_size}"
                     f" -e {args.cache_max_size_single_entry}"
                     f" -k {args.cache_max_num_entries}")
        if args.timeout:
            start_cmd += f" -s {args.timeout}"
        if args.access_token:
            start_cmd += f" -a {args.access_token}"
        if args.only_pso_and_pos_permutations:
            start_cmd += " --only-pso-and-pos-permutations"
        if not args.use_patterns:
            start_cmd += " --no-patterns"
        if args.with_text_index in \
                ["from_text_records", "from_literals",
                 "from_text_records_and_literals"]:
            start_cmd += " -t"
        start_cmd += f" > {args.name}.server-log.txt 2>&1"

        # Run the command in a container (if so desired). Otherwise run with
        # `nohup` so that it keeps running after the shell is closed.
        if args.container_system in Containerize.supported_systems():
            if not args.server_container_name:
                args.server_container_name = f"qlever.server.{args.name}"
            start_cmd = Containerize().containerize_command(
                    start_cmd,
                    args.container_system, "run -d --restart=unless-stopped",
                    args.image_name,
                    args.server_container_name,
                    volumes=[("$(pwd)", "/index")],
                    ports=[(args.port, args.port)],
                    working_directory="/index")
        else:
            start_cmd = f"nohup {start_cmd} &"

        # Show the command line.
        self.show(start_cmd, only_show=args.show)
        if args.show:
            return False

        # When running natively, check if the binary exists and works.
        if args.container_system == "native":
            try:
                run_command(f"{args.server_binary} --help")
            except Exception as e:
                log.error(f"Running \"{args.server_binary}\" failed ({e}), "
                          f"set `--server-binary` to a different binary or "
                          f"use `--container_system`")
                return False

        # Check if a QLever server is already running on this port.
        port = args.port
        if is_qlever_server_alive(port):
            log.error(f"QLever server already running on port {port}")

            # Show output of status command.
            args.cmdline_regex = "^ServerMain.* -i [^ ]*"
            log.info("")
            StatusCommand().execute(args)

            return False

        # Check if another process is already listening.
        # if self.net_connections_enabled:
        #     if port in [conn.laddr.port for conn
        #                 in psutil.net_connections()]:
        #         log.error(f"Port {port} is already in use by another process"
        #                   f" (use `lsof -i :{port}` to find out which one)")
        #         return False

        # Execute the command line.
        try:
            run_command(start_cmd)
        except Exception as e:
            log.error(f"Starting the QLever server failed ({e})")
            return False

        # Tail the server log until the server is ready (note that the `exec`
        # is important to make sure that the tail process is killed and not
        # just the bash process).
        log.info(f"Follow {args.name}.server-log.txt until the server is ready"
                 f" (Ctrl-C stops following the log, but not the server)")
        log.info("")
        tail_cmd = f"exec tail -f {args.name}.server-log.txt"
        tail_proc = subprocess.Popen(tail_cmd, shell=True)
        while not is_qlever_server_alive(port):
            time.sleep(1)

        # Set the access token if specified.
        access_arg = f"--data-urlencode \"access-token={args.access_token}\""
        if args.index_description:
            desc = args.index_description
            curl_cmd = (f"curl -Gs http://localhost:{port}/api"
                        f" --data-urlencode \"index-description={desc}\""
                        f" {access_arg} > /dev/null")
            log.debug(curl_cmd)
            try:
                run_command(curl_cmd)
            except Exception as e:
                log.error(f"Setting the index description failed ({e})")
        if args.text_description:
            desc = args.text_description
            curl_cmd = (f"curl -Gs http://localhost:{port}/api"
                        f" --data-urlencode \"text-description={desc}\""
                        f" {access_arg} > /dev/null")
            log.debug(curl_cmd)
            try:
                run_command(curl_cmd)
            except Exception as e:
                log.error(f"Setting the text description failed ({e})")

        # Kill the tail process. NOTE: `tail_proc.kill()` does not work.
        tail_proc.terminate()
