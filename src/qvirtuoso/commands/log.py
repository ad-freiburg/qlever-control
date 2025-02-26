from __future__ import annotations

from qoxigraph.commands import log as log_cmd


class LogCommand(log_cmd.LogCommand):
    def __init__(self):
        self.script_name = "qvirtuoso"
