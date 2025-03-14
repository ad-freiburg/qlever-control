from __future__ import annotations

from qlever.commands import log as log_cmd
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import run_command


class LogCommand(log_cmd.LogCommand):
    def __init__(self):
        self.script_name = "qoxigraph"

    def description(self) -> str:
        return (
            "Show the last lines of the index/server container log "
            "and follow it"
        )

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name"],
            "runtime": [
                "system",
                "image",
                "server_container",
                "index_container",
            ],
        }

    def execute(self, args) -> bool:
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
                f"No running index or start {system} container found! "
                f"Are you sure you called `{self.script_name} index` "
                f"or `{self.script_name} start` "
                "and have a process running?"
            )
            return False

        # Show the command line.
        self.show(log_cmd, only_show=args.show)
        if args.show:
            return True

        log.info(
            f"Showing logs for {active_ps} command. Press Ctrl-C to stop "
            f"following (will not stop the {active_ps} process)"
        )

        try:
            run_command(log_cmd, show_output=True, show_stderr=True)
        except Exception as e:
            log.error(f"Cannot display container logs - {e}")
        return True
