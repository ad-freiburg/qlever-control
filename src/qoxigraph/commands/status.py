from __future__ import annotations

from qlever.commands import status


class StatusCommand(status.StatusCommand):
    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "--cmdline-regex",
            default="oxigraph\\s+serve-read-only",
            help=(
                "Show only processes where the command line matches this regex"
            ),
        )
