from __future__ import annotations

from pathlib import Path

from qlever.log import log
from qlever.util import run_command
from qoxigraph.commands import setup_config


class SetupConfigCommand(setup_config.SetupConfigCommand):
    IMAGE = "openlink/virtuoso-opensource-7"
    VIRTUOSO_INI_URL = (
        "https://raw.githubusercontent.com/openlink/virtuoso-opensource/"
        "23abbfbe9eb78d47dd70d8aca08cef0e81202bfb/binsrc/virtuoso/virtuoso.ini"
    )

    def __init__(self):
        super().__init__()
        self.script_name = "qvirtuoso"

    def execute(self, args) -> bool:
        qleverfile_path = Path("Qleverfile")
        exit_status = self.validate_qleverfile_setup(args, qleverfile_path)
        if exit_status is not None:
            return exit_status

        qleverfile_parser = self.get_filtered_qleverfile_parser(
            args.config_name
        )
        # Copy the Qleverfile to the current directory.
        try:
            with qleverfile_path.open("w") as f:
                qleverfile_parser.write(f)
        except Exception as e:
            log.error(
                f'Could not copy "{qleverfile_path}" to current directory: {e}'
            )
            return False

        # If we get here, everything went well.
        log.info(
            f'Created Qleverfile for config "{args.config_name}"'
            f" in current directory"
        )
        log.info("")

        log.info("Fetching virtuoso.ini configuration file...")
        try:
            curl_cmd = f"curl -O {self.VIRTUOSO_INI_URL}"
            run_command(cmd=curl_cmd, show_output=True)
            log.info("")
            log.info(
                "Make sure to edit the virtuoso.ini before calling "
                f"`{self.script_name} start`"
            )
            log.info("")
            log.info(
                "Comment in high-memory settings for NumberOfBuffers and "
                "MaxDirtyBuffers. "
            )
            log.info(
                "Add appropriate values for ResultsSetMaxRows, MaxQueryMem, "
                "MaxQueryCostEstimationTime, MaxQueryExecutionTime."
            )
            log.warning(
                "Make sure to not modify the ServerPort under [Parameters] and "
                "[HTTPServer] sections in virtuoso.ini!"
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
