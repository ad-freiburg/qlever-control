from __future__ import annotations

from qoxigraph.commands import setup_config


class SetupConfigCommand(setup_config.SetupConfigCommand):
    """
    Should behave exactly the same as setup-config command in qoxigraph,
    just with a different Docker image name
    """
    IMAGE = "adfreiburg/qjena"
