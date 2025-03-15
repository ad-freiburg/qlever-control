from __future__ import annotations

from qoxigraph.commands import status


class StatusCommand(status.StatusCommand):
    DEFAULT_REGEX = "fuseki-server"
