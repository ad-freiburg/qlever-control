from __future__ import annotations

from qjena.commands.status import StatusCommand
from qoxigraph.commands import stop as qoxigraph_stop


class StopCommand(qoxigraph_stop.StopCommand):
    STATUS_COMMAND = StatusCommand()
    DEFAULT_REGEX = r".*fuseki-server.*--port\s%%PORT%%.*%%NAME%%.*"

    def description(self) -> str:
        return "Stop Jena server for a given dataset or port"

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "--cmdline-regex",
            default=self.DEFAULT_REGEX,
            help="Show only processes where the command "
            "line matches this regex",
        )

    def execute(self, args) -> bool:
        args.cmdline_regex = args.cmdline_regex.replace(
            "%%PORT%%", str(args.port)
        ).replace("%%NAME%%", args.name)
        return super().execute(args)
