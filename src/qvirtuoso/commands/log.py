from __future__ import annotations

from qlever.commands import log as log_cmd


class LogCommand(log_cmd.LogCommand):
    def execute(self, args) -> bool:
        args.log_file = "virtuoso.log"
        return super().execute(args)
