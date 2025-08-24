from __future__ import annotations

from qoxigraph.commands.setup_config import (
    SetupConfigCommand as QoxigraphSetupConfigCommand,
)


class SetupConfigCommand(QoxigraphSetupConfigCommand):
    """
    Should behave exactly the same as setup-config command in qoxigraph,
    just with a different Docker image name
    """

    IMAGE = "adfreiburg/qjena"

    ENGINE_SPECIFIC_PARAMETERS = {
        "index": {"THREADS": 2, "JVM_ARGS": "-Xmx4G"},
        "server": {"TIMEOUT": "60s", "JVM_ARGS": "-Xmx4G"}
    }
