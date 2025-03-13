from __future__ import annotations

from pathlib import Path

from qlever.commands import log as log_command


class LogCommand(log_command.LogCommand):
    def __init__(self):
        self.script_name = "qjena"

    def description(self) -> str:
        return (
            "Show the last lines of the server or index log file and follow it. "
            "(Default: server log if it exists otherwise index log)"
        )

    def additional_arguments(self, subparser) -> None:
        super().additional_arguments(subparser)
        subparser.add_argument(
            "--index-log",
            action="store_true",
            default=False,
            help=("Follow the index log (default: follow server log)"),
        )

    def execute(self, args) -> bool:
        log_file = "server.log"
        if not Path("server.log").exists() or args.index_log:
            log_file = "index.log"
        args.log_file = log_file
        return super().execute(args)
