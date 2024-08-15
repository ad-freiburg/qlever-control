from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import qlever.globals
from qlever.command import QleverCommand
from qlever.envvars import Envvars
from qlever.log import log
from qlever.util import get_random_string


class ConfigCommand(QleverCommand):
    """
    Class for executing the `config` command.
    """

    def __init__(self):
        self.qleverfiles_path = Path(__file__).parent.parent / "Qleverfiles"
        self.qleverfile_names = \
            [p.name.split(".")[1]
             for p in self.qleverfiles_path.glob("Qleverfile.*")]

    def description(self) -> str:
        return "Set up a Qleverfile or show the current configuration"

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str: list[str]]:
        return {}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
                "--get-qleverfile", type=str,
                choices=self.qleverfile_names,
                help="Get one the many pre-configured Qleverfiles")
        subparser.add_argument(
                "--show-qleverfile", action="store_true",
                default=False,
                help="Show the configuration from the Qleverfile "
                "(if it exists)")
        subparser.add_argument(
                "--show-envvars", action="store_true", default=False,
                help="Show all existing environment variables of the form "
                "QLEVER_SECTION_VARIABLE")
        subparser.add_argument(
                "--varname-width", type=int, default=25,
                help="Width for variable names in the output")
        subparser.add_argument(
                "--set-envvars-from-qleverfile", action="store_true",
                default=False,
                help="Set the environment variables that correspond to the "
                "Qleverfile configuration (for copying and pasting)")
        subparser.add_argument(
                "--unset-envvars", action="store_true", default=False,
                help="Unset all environment variables of the form "
                "QLEVER_SECTION_VARIABLE (for copying and pasting)")

    def execute(self, args) -> bool:
        # Show the configuration from the Qleverfile.
        if args.show_qleverfile:
            if qlever.globals.qleverfile_path is None:
                log.error("No Qleverfile found")
                return False
            if qlever.globals.qleverfile_config is None:
                log.error("Qleverfile found, but contains no configuration")
                return False
            self.show(f"Show the configuration from "
                      f"{qlever.globals.qleverfile_path} (with any variables "
                      f"on the right-hand side already substituted)",
                      only_show=args.show)
            if args.show:
                return False
            else:
                print_empty_line_before_section = False
                for section, varname_and_values in \
                        qlever.globals.qleverfile_config.items():
                    if section == "DEFAULT":
                        continue
                    if print_empty_line_before_section:
                        log.info("")
                    print_empty_line_before_section = True
                    log.info(f"[{section}]")
                    for varname, value in varname_and_values.items():
                        log.info(f"{varname.upper():{args.varname_width}} = "
                                 f"{value}")
            return True

        # Show all environment variables of the form QLEVER_SECTION_VARIABLE.
        if args.show_envvars:
            self.show("Show all environment variables of the form "
                      "QLEVER_SECTION_VARIABLE", only_show=args.show)
            if args.show:
                return False
            if qlever.globals.envvars_config is None:
                log.info("No environment variables found")
            else:
                for section, varname_and_values in \
                        qlever.globals.envvars_config.items():
                    for varname, value in varname_and_values.items():
                        var = Envvars.envvar_name(section, varname)
                        log.info(f"{var:{args.varname_width+7}}"
                                 f" = {shlex.quote(value)}")
            return True

        # Show the environment variables that correspond to the Qleverfile.
        if args.set_envvars_from_qleverfile:
            if qlever.globals.qleverfile_path is None:
                log.error("No Qleverfile found")
                return False
            if qlever.globals.qleverfile_config is None:
                log.error("Qleverfile found, but contains no configuration")
                return False
            self.show("Show the environment variables that correspond to the "
                      "Qleverfile configuration (for copying and pasting)",
                      only_show=args.show)
            if args.show:
                return False
            else:
                for section, varname_and_values in \
                        qlever.globals.qleverfile_config.items():
                    if section == "DEFAULT":
                        continue
                    for varname, value in varname_and_values.items():
                        var = Envvars.envvar_name(section, varname)
                        log.info(f"export {var}={shlex.quote(value)}")
            return True

        # Unset all environment variables of the form QLEVER_SECTION_VARIABLE.
        # Note that this cannot be done in this script because it would not
        # affect the shell calling this script. Instead, show the commands for
        # unsetting the environment variables to copy and paste.
        if args.unset_envvars:
            self.show("Unset all environment variables of the form "
                      "QLEVER_SECTION_VARIABLE (for copying and pasting, "
                      "this command cannot affect the shell from which you "
                      " are calling it)", only_show=args.show)
            if args.show:
                return False
            if qlever.globals.envvars_config is None:
                log.info("No environment variables found")
            else:
                envvar_names = []
                for section, varname_and_values in \
                        qlever.globals.envvars_config.items():
                    for varname, value in varname_and_values.items():
                        envvar_name = Envvars.envvar_name(section, varname)
                        envvar_names.append(envvar_name)
                log.info(f"unset {' '.join(envvar_names)}")
            return True

        # Get one of the pre-configured Qleverfiles.
        if args.get_qleverfile:
            config_name = args.get_qleverfile
            preconfigured_qleverfile_path = \
                    self.qleverfiles_path / f"Qleverfile.{config_name}"
            random_string = get_random_string(12)
            setup_config_cmd = (
                    f"cat {preconfigured_qleverfile_path}"
                    f" | sed -E 's/(^ACCESS_TOKEN.*)/\\1_{random_string}/'"
                    f" > Qleverfile")
            self.show(setup_config_cmd, only_show=args.show)
            if args.show:
                return False

            # If there is already a Qleverfile in the current directory, exit.
            existing_qleverfile_path = Path("Qleverfile")
            if existing_qleverfile_path.exists():
                log.error("`Qleverfile` already exists in current directory")
                log.info("")
                log.info("If you want to create a new Qleverfile using "
                         "`qlever setup-config`, delete the existing "
                         "Qleverfile first")
                return False

            # Copy the Qleverfile to the current directory.
            try:
                subprocess.run(setup_config_cmd, shell=True, check=True,
                               stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL)
            except Exception as e:
                log.error(f"Could not copy \"{preconfigured_qleverfile_path}\""
                          f" to current directory: {e}")
                return False

            # If we get here, everything went well.
            log.info(f"Created Qleverfile for config \"{config_name}\""
                     f" in current directory")
            return True

        # Calling `qlever config` without arguments is an error. Show the help.
        log.error("`qlever config` requires at least one argument, "
                  "see `qlever config --help`")
        return False
