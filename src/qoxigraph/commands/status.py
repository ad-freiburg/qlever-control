from __future__ import annotations

from qlever.commands import status


class StatusCommand(status.StatusCommand):
    DEFAULT_REGEX = "oxigraph\\s+serve-read-only"

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "--cmdline-regex",
            default=self.DEFAULT_REGEX,
            help=(
                "Show only processes where the command line matches this regex"
            ),
        )
