from __future__ import annotations

import psutil

from qlever.command import QleverCommand
from qlever.util import show_process_info, name_from_path


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
                               default="^(ServerMain|IndexBuilderMain)",
                               help="Show only processes where the command "
                                    "line matches this regex")

    def execute(self, args) -> bool:
        server_binary = name_from_path(args.server_binary)
        index_binary = name_from_path(args.index_binary)
        cmdline_regex = (args.cmdline_regex
                         .replace("ServerMain", server_binary)
                         .replace("IndexBuilderMain", index_binary))

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
