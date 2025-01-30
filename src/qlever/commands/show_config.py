from __future__ import annotations

import shlex
from pathlib import Path

import qlever.globals
from qlever.command import QleverCommand
from qlever.envvars import Envvars
from qlever.log import log


class ShowConfigCommand(QleverCommand):
    """
    Class for showing the current configuration (either via a Qleverfile or
    via environment variables).

    """

    def __init__(self):
        self.qleverfiles_path = Path(__file__).parent.parent / "Qleverfiles"
        self.qleverfile_names = [
            p.name.split(".")[1] for p in self.qleverfiles_path.glob("Qleverfile.*")
        ]

    def description(self) -> str:
        return "Set up a Qleverfile or show the current configuration"

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "--varname-width",
            type=int,
            default=25,
            help="Width for variable names in the output",
        )

    def execute(self, args) -> bool:
        # Determine if there is a Qleverfile or environment variables (we need
        # one or the other, but not both).
        qleverfile_exists = qlever.globals.qleverfile_path is not None
        envvars_exist = qlever.globals.envvars_config is not None
        if qleverfile_exists and envvars_exist:
            log.error(
                "There are both a Qleverfile and environment variables, "
                "this should not happen because it is bound to cause "
                "confusion; either remove the Qleverfile or unset the "
                "environment variables using `qlever config --unset-envvars`"
            )
            return False
        if not qleverfile_exists and not envvars_exist:
            log.error("Neither a Qleverfile nor environment variables found")
            return False

        # Show the configuration from the Qleverfile.
        if qleverfile_exists:
            if qlever.globals.qleverfile_config is None:
                log.error("Qleverfile found, but contains no configuration")
                return False
            self.show(
                f"Show the configuration from "
                f"{qlever.globals.qleverfile_path} (with any variables "
                f"on the right-hand side already substituted)",
                only_show=args.show,
            )
            if args.show:
                return True

            is_first_section = True
            for section, varname_and_values in qlever.globals.qleverfile_config.items():
                if section == "DEFAULT":
                    continue
                if not is_first_section:
                    log.info("")
                is_first_section = False
                log.info(f"[{section}]")
                for varname, value in varname_and_values.items():
                    log.info(f"{varname.upper():{args.varname_width}} = " f"{value}")
            return True

        # Show all environment variables of the form QLEVER_SECTION_VARIABLE.
        if envvars_exist:
            self.show(
                "Show all environment variables of the form QLEVER_SECTION_VARIABLE",
                only_show=args.show,
            )
            if args.show:
                return True

            for section, varname_and_values in qlever.globals.envvars_config.items():
                for varname, value in varname_and_values.items():
                    var = Envvars.envvar_name(section, varname)
                    log.info(f"{var:{args.varname_width+7}}" f" = {shlex.quote(value)}")
            return True
