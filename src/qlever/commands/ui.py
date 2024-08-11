from __future__ import annotations

import errno
import socket
import subprocess

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log


def is_port_used(port: int) -> bool:
    """
    Try to bind to the port on all interfaces to check if the port is already in use.
    If the port is already in use, `socket.bind` will raise an `OSError` with errno EADDRINUSE.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Ensure that the port is not blocked after the check.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', port))
        sock.close()
        return False
    except OSError as err:
        if err.errno != errno.EADDRINUSE:
            log.warning(f"Failed to determine if port is used: {err}")
        return True


class UiCommand(QleverCommand):
    """
    Class for launching the QLever UI web application.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return ("Launch the QLever UI web application")

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str: list[str]]:
        return {"data": ["name"],
                "server": ["host_name", "port"],
                "ui": ["ui_port", "ui_config",
                       "ui_system", "ui_image", "ui_container"]}

    def additional_arguments(self, subparser) -> None:
        pass

    def execute(self, args) -> bool:
        # Construct commands and show them.
        server_url = f"http://{args.host_name}:{args.port}"
        ui_url = f"http://{args.host_name}:{args.ui_port}"
        pull_cmd = f"{args.ui_system} pull -q {args.ui_image}"
        run_cmd = f"{args.ui_system} run -d " \
                  f"--publish {args.ui_port}:7000 " \
                  f"--name {args.ui_container} " \
                  f"{args.ui_image}"
        exec_cmd = f"{args.ui_system} exec -it " \
                   f"{args.ui_container} " \
                   f"bash -c \"python manage.py configure " \
                   f"{args.ui_config} {server_url}\""
        self.show("\n".join(["Stop running containers",
                            pull_cmd, run_cmd, exec_cmd]), only_show=args.show)
        if args.show:
            return False

        # Stop running containers.
        for container_system in Containerize.supported_systems():
            Containerize.stop_and_remove_container(
                    container_system, args.ui_container)

        # Check if the UI port is already being used.
        if is_port_used(args.ui_port):
            log.warning(f"The port for the UI ({args.ui_port}) may already be in use. You can set another port in the config file in the [UI] section with the UI_PORT key.")

        # Try to start the QLever UI.
        try:
            subprocess.run(pull_cmd, shell=True, stdout=subprocess.DEVNULL)
            subprocess.run(run_cmd, shell=True, stdout=subprocess.DEVNULL)
            subprocess.run(exec_cmd, shell=True, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to start the QLever UI ({e})")
            return False

        # Success.
        log.info(f"The QLever UI should now be up at {ui_url} ..."
                 f"You can log in as QLever UI admin with username and "
                 f"password \"demo\"")
        return True
