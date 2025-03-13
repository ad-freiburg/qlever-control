from __future__ import annotations

from qoxigraph.commands import stop


class StopCommand(stop.StopCommand):
    def description(self) -> str:
        return "Stop Jena server for a given dataset or port"
