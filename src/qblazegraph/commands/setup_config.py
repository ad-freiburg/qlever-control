from __future__ import annotations

import shutil
from pathlib import Path

from qlever.log import log
from qoxigraph.commands.setup_config import (
    SetupConfigCommand as QoxigraphSetupConfigCommand,
)


class SetupConfigCommand(QoxigraphSetupConfigCommand):
    """
    Should behave exactly the same as setup-config command in qoxigraph,
    just with a different Docker image name
    """

    IMAGE = "adfreiburg/qblazegraph"

    def execute(self, args) -> bool:
        if not super().execute(args):
            return False

        if args.show:
            return True

        properties_file_path = (
            Path(__file__).parent.parent / "blazegraph.properties"
        )
        destination = Path("blazegraph.properties")
        try:
            shutil.copy(properties_file_path, destination)
            log.info("Copied blazegraph.properties to current directory!")
            return True
        except Exception as e:
            file_url = (
                "https://github.com/ad-freiburg/qlever-control/tree/main/src/"
                "qblazegraph/blazegraph.properties"
            )
            log.error(
                "Couldn't copy blazegraph.properties file to current working "
                f"directory! Error: {e}\n"
            )
            log.info(f"Download it manually from {file_url}")
            return False
