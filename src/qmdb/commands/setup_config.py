from __future__ import annotations

from qoxigraph.commands.setup_config import (
    SetupConfigCommand as QoxigraphSetupConfigCommand,
)


class SetupConfigCommand(QoxigraphSetupConfigCommand):
    """
    Should behave exactly the same as setup-config command in qoxigraph,
    just with a different Docker image name and CAT_INPUT_FILES index arg
    """

    IMAGE = "adfreiburg/qmdb"

    FILTER_CRITERIA = QoxigraphSetupConfigCommand.FILTER_CRITERIA
    FILTER_CRITERIA["index"].append("CAT_INPUT_FILES")
