from __future__ import annotations

import psutil

from qlever.command import QleverCommand
from qlever.util import show_process_info


class StatusCommand(QleverCommand):
    """
    Class for executing the `status` command.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return ("Show QLever processes running on this machine")

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str: list[str]]:
        return {"server": ["server_binary"], "index": ["index_binary"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument("--cmdline-regex",
                               default="^(%%SERVER_BINARY%%|%%INDEX_BINARY%%)",
                               help="Show only processes where the command "
                                    "line matches this regex")

    def execute(self, args) -> bool:
        cmdline_regex = args.cmdline_regex
        # Other commands call status with a custom `cmdline_regex` that contains
        # less or no variables. Doing the replacement on-demand has the benefit
        # that only the variables that are actually used have to be provided by
        # the calling command. For example: the `cmdline_regex` used by start
        # has no variables and requiring the index binary for it would be strange.
        if "%%SERVER_BINARY%%" in cmdline_regex:
            cmdline_regex = cmdline_regex.replace("%%SERVER_BINARY%%", args.server_binary)
        if "%%INDEX_BINARY%%" in cmdline_regex:
            cmdline_regex = cmdline_regex.replace("%%INDEX_BINARY%%", args.index_binary)

        # Show action description.
        self.show(f"Show all processes on this machine where "
                  f"the command line matches {cmdline_regex}"
                  f" using Python's psutil library", only_show=args.show)
        if args.show:
            return True

        # Show the results as a table.
        num_processes_found = 0
        for proc in psutil.process_iter():
            show_heading = num_processes_found == 0
            process_shown = show_process_info(proc, cmdline_regex,
                                              show_heading=show_heading)
            if process_shown:
                num_processes_found += 1
        if num_processes_found == 0:
            print("No processes found")
        return True
