from __future__ import annotations

import subprocess
from os import environ
from pathlib import Path

import yaml

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import is_port_used, run_command


# Return a YAML string for the given dictionary. Format values with
# newlines using the "|" style.
def dict_to_yaml(dictionary):
    # Custom representer for yaml, which uses the "|" style only for
    # multiline strings.
    #
    # NOTE: We replace all `\r\n` with `\n` because otherwise the `|` style
    # does not work as expected.
    class MultiLineDumper(yaml.Dumper):
        def represent_scalar(self, tag, value, style=None):
            value = value.replace("\r\n", "\n")
            if isinstance(value, str) and "\n" in value:
                style = "|"
            return super().represent_scalar(tag, value, style)

    # Dump as yaml.
    return yaml.dump(
        dictionary,
        sort_keys=False,
        Dumper=MultiLineDumper,
    )


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
            default="Qleveruifile.yml",
            help="Name of the config file for the QLever UI "
            "(default: Qleveruifile.yml)",
        )
        subparser.add_argument(
            "--ui-db-file",
            help="Name of the database file for the QLever UI "
            "(default: <name>.ui-db.sqlite3)",
        )
        subparser.add_argument(
            "--no-pull-latest",
            action="store_true",
            default=False,
            help="Do not pull the latest image for the QLever UI "
            "(default: pull the latest image if image name contains '/')",
        )
        subparser.add_argument(
            "--stop",
            action="store_true",
            default=False,
            help="Stop the running container",
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
        pull_latest_image = "/" in args.ui_image and not args.no_pull_latest
        ui_config_name = args.name
        ui_db_file = args.ui_db_file or f"{args.name}.ui-db.sqlite3"
        ui_db_file_from_image = "qleverui.sqlite3"
        ui_config_file = args.ui_config_file
        sparql_endpoint = f"http://{args.host_name}:{args.port}"
        ui_url = f"http://{args.host_name}:{args.ui_port}"
        pull_cmd = f"{args.ui_system} pull -q {args.ui_image}"
        get_db_cmd = (
            f"{args.ui_system} create "
            f"--name {args.ui_container} "
            f"{args.ui_image} "
            f"&& {args.ui_system} cp "
            f"{args.ui_container}:/app/db/{ui_db_file_from_image} {ui_db_file} "
            f"&& {args.ui_system} rm -f {args.ui_container}"
        )
        start_ui_cmd = (
            f"{args.ui_system} run -d "
            f"--volume $(pwd):/app/db "
            # f"--volume $(pwd)/{ui_db_file}:/app/db/{ui_db_file_from_image} "
            # f"--volume $(pwd)/{ui_config_file}:/app/db/{ui_config_file} "
            f"--env QLEVERUI_DATABASE_URL=sqlite:////app/db/{ui_db_file} "
            f"--publish {args.ui_port}:7000 "
            f"--name {args.ui_container} "
            f"{args.ui_image}"
        )
        get_config_cmd = (
            f"{args.ui_system} exec -it "
            f"{args.ui_container} "
            f'bash -c "python manage.py config {ui_config_name}"'
        )
        set_config_cmd = (
            f"{args.ui_system} exec -it "
            f"{args.ui_container} "
            f'bash -c "python manage.py config {ui_config_name} '
            f'/app/db/{ui_config_file} --hide-all-other-backends"'
        )
        commands_to_show = []
        commands_to_show.append("Check for running containers and stop them")
        if not args.stop:
            if pull_latest_image:
                commands_to_show.append(pull_cmd)
            if not Path(ui_db_file).exists():
                commands_to_show.append(get_db_cmd)
            commands_to_show.append(start_ui_cmd)
            if not Path(ui_config_file).exists():
                commands_to_show.append(get_config_cmd)
            else:
                commands_to_show.append(set_config_cmd)
        self.show("\n".join(commands_to_show), only_show=args.show)
        if qlever_is_running_in_container:
            return False
        if args.show:
            return True

        # Stop running containers.
        was_found_and_stopped = False
        for container_system in Containerize.supported_systems():
            was_found_and_stopped |= Containerize.stop_and_remove_container(
                container_system, args.ui_container
            )
        if was_found_and_stopped:
            log.info(f"Stopped and removed container `{args.ui_container}`")
        else:
            log.info(f"No container with name `{args.ui_container}` found")
        if args.stop:
            return True

        # Check if the UI port is already being used.
        if is_port_used(args.ui_port):
            log.warning(
                f"It looks like port {args.ui_port} for the QLever UI "
                f"is already in use. You can set another port in the "
                f" Qleverfile in the [ui] section with the UI_PORT variable."
            )

        # Get the QLever UI database.
        if Path(ui_db_file).exists():
            log.info(f"Found QLever UI database `{ui_db_file}`, reusing it")
        else:
            log.info(f"Getting QLever UI database `{ui_db_file}` from image")
            try:
                run_command(get_db_cmd)
            except subprocess.CalledProcessError as e:
                log.error(f"Failed to get the QLever UI database ({e})")
                return False

        # Start the QLever UI.
        try:
            if pull_latest_image:
                log.info(f"Pulling image `{args.ui_image}` for QLever UI")
                run_command(pull_cmd)
            log.info(f"Starting new container with name `{args.ui_container}`")
            run_command(start_ui_cmd)
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to start the QLever UI ({e})")
            return False

        # Check if config file with name `ui_config_file` exists. If not, try
        # to obtain it via `get_config_cmd` and set it as default.
        if Path(ui_config_file).exists():
            log.info(f"Found config file `{ui_config_file}` and reusing it")
        else:
            log.info(
                f"Checking if config `{ui_config_name}` exists in "
                f"image `{args.ui_image}` "
            )
            try:
                config_yaml = run_command(get_config_cmd, return_output=True)
                log.info(
                    f"Found it and setting URL for SPARQL endpoint to "
                    f"{sparql_endpoint}"
                )
                config_dict = yaml.safe_load(config_yaml)
                config_dict["config"]["backend"]["isDefault"] = True
                config_dict["config"]["backend"]["baseUrl"] = sparql_endpoint
                config_dict["config"]["backend"]["sortKey"] = 1
                config_yaml = dict_to_yaml(config_dict)
                log.info(f"Writing config to `{ui_config_file}`")
                with open(ui_config_file, "w") as f:
                    f.write(config_yaml)
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
        log.info("")
        log.info(
            f"The QLever UI should now be up at {ui_url}/{ui_config_name}"
        )
        log.info("")
        log.info(
            "You can log in as QLever UI admin with "
            'username and password "demo"'
        )
        log.info(
            f"You can modify the config file at `{ui_config_file}` "
            f"and then just run `qlever ui` again"
        )
        return True
