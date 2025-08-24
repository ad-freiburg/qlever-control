from __future__ import annotations

from qoxigraph.commands.setup_config import (
    SetupConfigCommand as QoxigraphSetupConfigCommand,
)


class SetupConfigCommand(QoxigraphSetupConfigCommand):
    """
    Should behave exactly the same as setup-config command in qoxigraph,
    just with a different Docker image name and CAT_INPUT_FILES index arg
    """

    IMAGE = "adfreiburg/millenniumdb"

    FILTER_CRITERIA = QoxigraphSetupConfigCommand.FILTER_CRITERIA
    FILTER_CRITERIA["index"].append("CAT_INPUT_FILES")

    ENGINE_SPECIFIC_PARAMETERS = {
        "index": {"BUFFER_STRINGS": "2GB", "BUFFER_TENSORS": "2GB"},
        "server": {
            "TIMEOUT": "60s",
            "THREADS": 1,
            "STRINGS_STATIC": "1GB",
            "STRINGS_DYNAMIC": "1GB",
            "VERSIONED_BUFFER": "2GB",
            "UNVERSIONED_BUFFER": "1GB",
        },
    }
