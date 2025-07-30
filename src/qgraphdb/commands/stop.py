from __future__ import annotations

from qjena.commands.status import StatusCommand
from qoxigraph.commands.stop import StopCommand as QoxigraphStopCommand


class StopCommand(QoxigraphStopCommand):
    STATUS_COMMAND = StatusCommand()
    DEFAULT_REGEX = "com.ontotext.graphdb.server.GraphDBServer"

    def description(self) -> str:
        return "Stop the GraphDB server"

