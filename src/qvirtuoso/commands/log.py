from __future__ import annotations

from qlever.commands.log import LogCommand as QleverLogCommand


class LogCommand(QleverLogCommand):
    def execute(self, args) -> bool:
        args.log_file = "virtuoso.log"
        return super().execute(args)
