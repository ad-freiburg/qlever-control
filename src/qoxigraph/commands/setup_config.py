from __future__ import annotations

from configparser import RawConfigParser
from pathlib import Path

from qlever.command import QleverCommand
from qlever.log import log
from qlever.qleverfile import Qleverfile
from qlever.util import run_command


class SetupConfigCommand(QleverCommand):
    IMAGE = "ghcr.io/oxigraph/oxigraph"

    FILTER_CRITERIA = {
        "data": [],
        "index": ["INPUT_FILES"],
        "server": ["PORT"],
        "runtime": ["SYSTEM", "IMAGE"],
        "ui": ["UI_CONFIG"],
    }

    ENGINE_SPECIFIC_PARAMETERS = {"server": {"READ_ONLY": "yes"}}

    def __init__(self):
        self.script_name = "qoxigraph"
        self.qlever_qleverfiles_path = (
            Path(__file__).parent.parent.parent / "qlever" / "Qleverfiles"
        )
        self.engine_qleverfiles_path = (
            Path(__file__).parent.parent / "Qleverfiles"
        )
        self.qleverfiles_path = {}
        for path in (
            *self.engine_qleverfiles_path.glob("Qleverfile.*"),
            *self.qlever_qleverfiles_path.glob("Qleverfile.*"),
        ):
            config_name = path.name.split(".")[1]
            if config_name in self.qleverfiles_path:
                continue
            self.qleverfiles_path[config_name] = path

    def description(self) -> str:
        return "Get a pre-configured Qleverfile"

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "config_name",
            type=str,
            choices=self.qleverfiles_path,
            help="The name of the pre-configured Qleverfile to create",
        )

    def add_engine_specific_option_values(
        self,
        qleverfile_parser: RawConfigParser,
    ) -> None:
        for section, option_dict in self.ENGINE_SPECIFIC_PARAMETERS.items():
            if qleverfile_parser.has_section(section):
                for option, value in option_dict.items():
                    qleverfile_parser.set(section, option, value)

    def get_filtered_qleverfile_parser(
        self, template_path: Path
    ) -> RawConfigParser:
        qleverfile_parser = Qleverfile.filter(
            template_path, self.FILTER_CRITERIA
        )
        self.add_engine_specific_option_values(qleverfile_parser)
        if qleverfile_parser.has_section("runtime"):
            qleverfile_parser.set("runtime", "IMAGE", self.IMAGE)
        return qleverfile_parser

    def execute(self, args) -> bool:
        # Construct the command line and show it.
        template_path = self.qleverfiles_path[args.config_name]
        setup_config_show = (
            f"Qleverfile for {args.config_name} will be created using "
            f"Qleverfile.{args.config_name} file in {template_path}"
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

        try:
            if template_path.parent.parent.name == self.script_name:
                setup_config_cmd = f"cat {template_path} > Qleverfile"
                run_command(setup_config_cmd)
            else:
                qleverfile_parser = self.get_filtered_qleverfile_parser(
                    template_path
                )
                with qleverfile_path.open("w") as f:
                    qleverfile_parser.write(f)

            log.info(
                f'Created Qleverfile for config "{args.config_name}"'
                f" in current directory"
            )
            return True
        except Exception as e:
            log.error(
                f'Could not copy "{qleverfile_path}" to current directory: {e}'
            )
            return False
