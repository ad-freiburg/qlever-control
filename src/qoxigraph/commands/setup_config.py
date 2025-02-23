from __future__ import annotations

from pathlib import Path

from qlever.commands import setup_config
from qlever.log import log
from qlever.qleverfile import Qleverfile


class SetupConfigCommand(setup_config.SetupConfigCommand):
    IMAGE = "ghcr.io/oxigraph/oxigraph"

    FILTER_CRITERIA = {
        "data": [],
        "index": ["INPUT_FILES", "CAT_INPUT_FILES"],
        "server": ["PORT"],
        "runtime": ["SYSTEM", "IMAGE"],
        "ui": ["UI_CONFIG"],
    }

    def __init__(self):
        self.qleverfiles_path = (
            Path(__file__).parent.parent.parent / "qlever" / "Qleverfiles"
        )
        self.qleverfile_names = [
            p.name.split(".")[1]
            for p in self.qleverfiles_path.glob("Qleverfile.*")
        ]

    def execute(self, args) -> bool:
        # Construct the command line and show it.
        qleverfile_config_path = (
            self.qleverfiles_path / f"Qleverfile.{args.config_name}"
        )
        setup_config_show = (
            f"Creating Qleverfile for {args.config_name} using "
            f"Qleverfile.{args.config_name} file in {self.qleverfiles_path}"
        )
        self.show(setup_config_show, only_show=args.show)
        if args.show:
            return True

        # If there is already a Qleverfile in the current directory, exit.
        qleverfile_path = Path("Qleverfile")
        if qleverfile_path.exists():
            log.error("`Qleverfile` already exists in current directory")
            log.info("")
            log.info(
                "If you want to create a new Qleverfile using "
                "`qlever setup-config`, delete the existing Qleverfile "
                "first"
            )
            return False

        qleverfile_config = Qleverfile.filter(
            qleverfile_config_path, self.FILTER_CRITERIA
        )
        if qleverfile_config.has_section("runtime"):
            qleverfile_config.set("runtime", "IMAGE", self.IMAGE)

        # Copy the Qleverfile to the current directory.
        try:
            with qleverfile_path.open("w") as f:
                qleverfile_config.write(f)
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
        return True
