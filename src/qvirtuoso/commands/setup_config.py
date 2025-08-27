from __future__ import annotations

from qlever.log import log
from qlever.util import run_command
from qoxigraph.commands.setup_config import (
    SetupConfigCommand as QoxigraphSetupConfigCommand,
)


class SetupConfigCommand(QoxigraphSetupConfigCommand):
    IMAGE = "adfreiburg/virtuoso-opensource-7"
    VIRTUOSO_INI_URL = (
        "https://raw.githubusercontent.com/openlink/virtuoso-opensource/"
        "23abbfbe9eb78d47dd70d8aca08cef0e81202bfb/binsrc/virtuoso/virtuoso.ini"
    )

    ENGINE_SPECIFIC_PARAMETERS = {
        "index": {
            "ISQL_PORT": 1111,
            "FREE_MEMORY_GB": "4G",
            "NUM_PARALLEL_LOADERS": 1,
        },
        "server": {"MAX_QUERY_MEMORY": "2G", "TIMEOUT": "30s"},
    }

    def execute(self, args) -> bool:
        qleverfile_successfully_created = super().execute(args)
        if not qleverfile_successfully_created:
            return False

        log.info("Fetching virtuoso.ini configuration file...")
        try:
            curl_cmd = f"curl -o virtuoso.ini {self.VIRTUOSO_INI_URL}"
            run_command(cmd=curl_cmd, show_output=True)
            log.info(
                "Successfully downloaded virtuoso.ini to the current working "
                "directory!"
            )
        except Exception as e:
            url = (
                "https://github.com/openlink/virtuoso-opensource/blob/"
                "23abbfbe9eb78d47dd70d8aca08cef0e81202bfb/binsrc/virtuoso/"
                "virtuoso.ini"
            )
            log.error(
                "Couldn't download the virtuoso.ini configuration file."
                f"If possible, please download it manually from {url} "
                f"and place it in the current directory. Error -> {e}"
            )
        return True
