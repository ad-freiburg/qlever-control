from __future__ import annotations

from qoxigraph.commands.status import StatusCommand as QoxigraphStatusCommand


class StatusCommand(QoxigraphStatusCommand):
    DEFAULT_REGEX = "virtuoso-t"
