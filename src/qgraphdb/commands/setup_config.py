from __future__ import annotations

from qlever.log import log
from qlever.util import run_curl_command
from qoxigraph.commands.setup_config import (
    SetupConfigCommand as QoxigraphSetupConfigCommand,
)


class SetupConfigCommand(QoxigraphSetupConfigCommand):
    """
    Should behave exactly the same as setup-config command in qoxigraph,
    just with a different Docker image name
    """

    IMAGE = "ontotext/graphdb:11.0.1"

    def execute(self, args) -> bool:
        qleverfile_successfully_created = super().execute(args)
        if not qleverfile_successfully_created:
            return False

        repo_config_ttl = (
            "https://graphdb.ontotext.com/documentation/11.0/_downloads/"
            "565be93599bf4c3324147fb94b562595/repo-config.ttl"
        )
        try:
            run_curl_command(url=repo_config_ttl, result_file="config.ttl")
            log.info(
                "Successfully downloaded config.ttl for specifying config parameters."
            )
            return True
        except Exception as e:
            log.error(f"Failed to download config.ttl file: {e}")
            log.info(f"Download it manually from {repo_config_ttl}")
            return False

