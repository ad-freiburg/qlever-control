from __future__ import annotations

import subprocess
from os import environ
from pathlib import Path

import yaml

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import is_port_used, run_command


class UiCommand(QleverCommand):
    """
    Class for launching the QLever UI web application.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return "Launch the QLever UI web application"

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name"],
            "server": ["host_name", "port"],
            "ui": [
                "ui_port",
                "ui_config",
                "ui_system",
                "ui_image",
                "ui_container",
            ],
        }

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "--ui-config-file",
            help="Name of the config file for the QLever UI "
            "(default: <name>.ui-config.yml)",
        )
        subparser.add_argument(
            "--pull-latest",
            type=str,
            choices=["yes", "no"],
            default="yes",
            help="Pull the latest image of the QLever UI",
        )

    def execute(self, args) -> bool:
        # If QLEVER_OVERRIDE_DISABLE_UI is set, this command is disabled.
        qlever_is_running_in_container = environ.get(
            "QLEVER_IS_RUNNING_IN_CONTAINER"
        )
        if qlever_is_running_in_container:
            log.error(
                "The environment variable `QLEVER_OVERRIDE_DISABLE_UI` is set, "
                "therefore `qlever ui` is not available (it should not be called "
                "from inside a container)"
            )
            log.info("")
            if not args.show:
                log.info(
                    "For your information, showing the commands that are "
                    "executed when `qlever ui` is available:"
                )
                log.info("")

        # Construct commands and show them.
        ui_config_name = args.name
        ui_config_file = args.ui_config_file or f"{args.name}.ui-config.yml"
        server_url = f"http://{args.host_name}:{args.port}"
        ui_url = f"http://{args.host_name}:{args.ui_port}"
        pull_cmd = f"{args.ui_system} pull -q {args.ui_image}"
        get_config_cmd = (
            f"{args.ui_system} exec -it "
            f"{args.ui_image} "
            f"bash -c \"python manage.py config {ui_config_name}\""
        )
        start_ui_cmd = (
            f"{args.ui_system} run -d "
            f"--publish {args.ui_port}:7000 "
            f"--name {args.ui_container} "
            f"{args.ui_image}"
        )
        set_config_cmd = (
            f"{args.ui_system} exec -it "
            f"{args.ui_container} "
            f"bash -c \"python manage.py config {ui_config_name} "
            f"{ui_config_file} --hide-all-other-backends\""
        )
        self.show(
            "\n".join(
                [
                    "Stop running containers",
                    pull_cmd,
                    get_config_cmd,
                    start_ui_cmd,
                    set_config_cmd,
                ]
            ),
            only_show=args.show,
        )
        if qlever_is_running_in_container:
            return False
        if args.show:
            return True

        # Stop running containers.
        for container_system in Containerize.supported_systems():
            Containerize.stop_and_remove_container(
                container_system, args.ui_container
            )

        # Check if the UI port is already being used.
        if is_port_used(args.ui_port):
            log.warning(
                f"It looks like port {args.ui_port} for the QLever UI "
                f"is already in use. You can set another port in the "
                f" Qleverfile in the [ui] section with the UI_PORT variable."
            )

        # Start the QLever UI.
        try:
            if args.pull_latest == "yes":
                run_command(pull_cmd)
            run_command(start_ui_cmd)
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to start the QLever UI ({e})")
            return False

        # Check if config file with name `ui_config_file` exists. If not, try
        # to obtain it via `get_config_cmd` and set it as default.
        if Path(ui_config_file).exists():
            log.info(f"Found config file `{ui_config_file}` for QLever UI ...")
        else:
            log.info(
                f"Trying to obtain default config for `{ui_config_name}` ..."
            )
            try:
                config_yaml = run_command(get_config_cmd, return_output=True)
                config_dict = yaml.safe_load(config_yaml)
                config_dict["config"]["backend"]["isDefault"] = True
                config_dict["config"]["backend"]["baseUrl"] = server_url
                config_dict["config"]["backend"]["sortKey"] = 1
            except Exception as e:
                log.error(
                    f"Neither found config file `{ui_config_file}` nor "
                    f"could obtain default config for `{ui_config_name}`"
                )
                log.info("")
                log.info(f"Error message: {e}")
                log.info("")
                log.info(
                    "TODO: provide further instructions for this case "
                    "(obtain `default` config file, edit it, rename it, "
                    "then try again)"
                )
                return False

        # Configure the QLever UI.
        try:
            run_command(set_config_cmd)
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to configure the QLever UI ({e})")
            return False

        # If we come this far, everything should work.
        log.info(
            f"The QLever UI should now be up at {ui_url} ..."
            f"You can log in as QLever UI admin with username and "
            f'password "demo"'
        )
        return True
