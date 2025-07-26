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
        qleverfile_successfully_created = super().execute(args)
        if not qleverfile_successfully_created:
            return False

        log.info("Fetching RWStore.properties file...")
        properties_file_path = (
            Path(__file__).parent.parent / "RWStore.properties"
        )
        destination = Path("RWStore.properties")
        try:
            shutil.copy(properties_file_path, destination)
            log.info("Copied RWStore.properties to current directory!")
            return True
        except Exception as e:
            file_url = (
                "https://github.com/ad-freiburg/qlever-control/tree/main/src/"
                "qblazegraph/RWStore.properties"
            )
            log.error(
                "Couldn't copy RWStore.properties file to current working "
                f"directory! Error: {e}\n"
            )
            log.info(f"Download it manually from {file_url}")
            return False
