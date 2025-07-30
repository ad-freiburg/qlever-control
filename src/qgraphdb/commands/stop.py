from __future__ import annotations

from qjena.commands.status import StatusCommand
from qoxigraph.commands.stop import StopCommand as QoxigraphStopCommand


class StopCommand(QoxigraphStopCommand):
    STATUS_COMMAND = StatusCommand()
    DEFAULT_REGEX = "com.ontotext.graphdb.server.GraphDBServer"

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "runtime": ["system", "server_container"],
        }

    def description(self) -> str:
        return "Stop the GraphDB server"

