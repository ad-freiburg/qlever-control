from __future__ import annotations

import shlex
from os import environ
from pathlib import Path

import qlever.globals
from qlever.command import QleverCommand
from qlever.envvars import Envvars
from qlever.log import log
from qlever.util import get_random_string, run_command


class SetupConfigCommand(QleverCommand):
    """
    Class for executing the `setup-config` command.
    """

    def __init__(self):
        self.qleverfiles_path = Path(__file__).parent.parent / "Qleverfiles"
        self.qleverfile_names = [
            p.name.split(".")[1] for p in self.qleverfiles_path.glob("Qleverfile.*")
        ]

    def description(self) -> str:
        return "Get a pre-configured Qleverfile"

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "config_name",
            nargs="?",
            type=str,
            choices=self.qleverfile_names,
            help="The name of the pre-configured Qleverfile to create",
        )
        subparser.add_argument(
            "--set-envvars-from-qleverfile",
            action="store_true",
            default=False,
            help="Show the command line to set the environment variables "
            "that correspond to the Qleverfile configuration (suitable for "
            "copying and pasting)",
        )
        subparser.add_argument(
            "--unset-envvars",
            action="store_true",
            default=False,
            help="Show the command line to unset all environment variables of "
            "the form QLEVER_SECTION_VARIABLE (suitable for copying and pasting)",
        )
        subparser.add_argument(
            "--file",
            type=str,
            default=None,
            help="File to which to write the commands from "
            "`--set-envvars-from-qleverfile` or `--unset-envvars`",
        )

    def execute(self, args) -> bool:
        # Either create a Qleverfile or set or unset environment variables.
        if args.config_name and args.set_envvars_from_qleverfile:
            log.error(
                "If you want to set environment variables based on a "
                "Qleverfile, first create a Qleverfile by running "
                "`qlever setup-config CONFIG_NAME`, and then run "
                "`qlever config --set-envvars-from-qleverfile`"
            )
            return False
        if args.config_name and args.unset_envvars:
            log.error(
                "You cannot create a Qleverfile and unset environment "
                "variables at the same time"
            )
            return False
        if args.set_envvars_from_qleverfile and args.unset_envvars:
            log.error("You cannot set and unset environment variables at the same time")
            return False

        # Show the environment variables that correspond to the Qleverfile.
        if args.set_envvars_from_qleverfile:
            if qlever.globals.qleverfile_path is None:
                log.error("No Qleverfile found")
                return False
            if qlever.globals.qleverfile_config is None:
                log.error("Qleverfile found, but contains no configuration")
                return False
            self.show(
                "Set the environment variables that correspond to the "
                "configuration from the Qleverfile",
                only_show=args.show,
            )
            if args.show:
                return False
            else:
                set_envvar_cmds = []
                for (
                    section,
                    varname_and_values,
                ) in qlever.globals.qleverfile_config.items():
                    if section == "DEFAULT":
                        continue
                    for varname, value in varname_and_values.items():
                        var = Envvars.envvar_name(section, varname)
                        set_envvar_cmd = f"export {var}={shlex.quote(value)}"
                        set_envvar_cmds.append(set_envvar_cmd)
                        log.info(set_envvar_cmd)
                log.info("")
                if args.file:
                    with open(args.file, "w") as f:
                        for cmd in set_envvar_cmds:
                            f.write(cmd + "\n")
                    log.info(
                        f"Commands written to file `{args.file}`, to set "
                        "the environment variables, run `source {args.file}` "
                        "(and if you want to use `qlever` based on these "
                        "environment variables, move or delete the Qleverfile)"
                    )
                else:
                    log.info(
                        "If you want to write these commands to a file, "
                        "rerun with `--file FILENAME`"
                    )
            return True

        # Unset all environment variables of the form QLEVER_SECTION_VARIABLE.
        # Note that this cannot be done in this script because it would not
        # affect the shell calling this script. Instead, show the commands for
        # unsetting the environment variables to copy and paste.
        if args.unset_envvars:
            self.show(
                "Unset all environment variables of the form "
                "QLEVER_SECTION_VARIABLE (for copying and pasting, "
                "this command cannot affect the shell from which you "
                " are calling it)",
                only_show=args.show,
            )
            if args.show:
                return False
            if qlever.globals.envvars_config is None:
                log.info("No environment variables found")
            else:
                envvar_names = []
                for (
                    section,
                    varname_and_values,
                ) in qlever.globals.envvars_config.items():
                    for varname, value in varname_and_values.items():
                        envvar_name = Envvars.envvar_name(section, varname)
                        envvar_names.append(envvar_name)
                unset_cmd = f"unset {' '.join(envvar_names)}"
                log.info(unset_cmd)
                log.info("")
                if args.file:
                    with open(args.file, "w") as f:
                        f.write(unset_cmd)
                    log.info(
                        f"Command written to file `{args.file}`, to unset "
                        "the environment variables, run `source {args.file}`"
                    )
                else:
                    log.info(
                        "If you want to write this command to a file, "
                        "rerun with `--file FILENAME`"
                    )
            return True

        # Show a warning if `QLEVER_OVERRIDE_SYSTEM_NATIVE` is set.
        qlever_is_running_in_container = environ.get("QLEVER_IS_RUNNING_IN_CONTAINER")
        if qlever_is_running_in_container:
            log.warning(
                "The environment variable `QLEVER_IS_RUNNING_IN_CONTAINER` is set, "
                "therefore the Qleverfile is modified to use `SYSTEM = native` "
                "(since inside the container, QLever should run natively)"
            )
            log.info("")

        # Construct the command line and show it.
        qleverfile_path = self.qleverfiles_path / f"Qleverfile.{args.config_name}"
        random_string = get_random_string(12)
        setup_config_cmd = (
            f"cat {qleverfile_path}"
            f" | sed -E 's/(^ACCESS_TOKEN.*)/\\1_{random_string}/'"
        )
        if qlever_is_running_in_container:
            setup_config_cmd += (
                " | sed -E 's/(^SYSTEM[[:space:]]*=[[:space:]]*).*/\\1native/'"
            )
        setup_config_cmd += "> Qleverfile"
        self.show(setup_config_cmd, only_show=args.show)
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

        # Copy the Qleverfile to the current directory.
        try:
            run_command(setup_config_cmd)
        except Exception as e:
            log.error(
                f'Could not copy "{qleverfile_path}"' f" to current directory: {e}"
            )
            return False

        # If we get here, everything went well.
        log.info(
            f'Created Qleverfile for config "{args.config_name}"'
            f" in current directory"
        )
        return True
