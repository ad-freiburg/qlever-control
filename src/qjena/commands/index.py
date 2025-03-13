from __future__ import annotations

import glob
import shlex
from pathlib import Path

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import run_command


class IndexCommand(QleverCommand):
    def __init__(self):
        self.script_name = "qjena"

    def description(self) -> str:
        return "Build the index for a given RDF dataset"

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name", "format"],
            "index": ["input_files"],
            "server": ["port"],
            "runtime": ["system", "image", "server_container"],
        }

    def additional_arguments(self, subparser):
        pass

    def build_image(self, build_cmd: str, system: str, image: str) -> bool:
        try:
            run_command(build_cmd, show_output=True)
            return True
        except Exception as e:
            log.error(f"Building the {system} image {image} failed: {e}")
            return False

    def execute(self, args) -> bool:
        system = args.system
        input_files = args.input_files
        server_container = args.server_container
        run_subcommand = "run -d"

        loading_flag = "/opt/loading.flag"
        index_cmd = f"touch {loading_flag} && "
        index_cmd += (
            f"tdb2.xloader --loc index data/{input_files} "
            ">> /opt/data/index.log 2>&1 && "
        )
        index_cmd += f"rm {loading_flag} && "
        index_cmd += "tail -f /dev/null"

        index_cmd = Containerize().containerize_command(
            cmd=index_cmd,
            container_system=system,
            run_subcommand=run_subcommand,
            image_name=args.image,
            container_name=server_container,
            volumes=[("$(pwd)", "/opt/data")],
            ports=[(int(args.port), 3030)],
        )

        dockerfile_dir = Path(__file__).parent.parent
        dockerfile_path = dockerfile_dir / "Dockerfile"
        build_cmd = (
            f"{system} build -f {dockerfile_path} -t {args.image} --build-arg "
            f"UID=$(id -u) --build-arg GID=$(id -g) {dockerfile_dir}"
        )
        image_id = run_command(
            f"{system} images -q {args.image}", return_output=True
        )
        cmd_to_show = (
            f"{build_cmd}\n\n{index_cmd}" if not image_id else index_cmd
        )

        # Show the command line.
        self.show(cmd_to_show, only_show=args.show)
        if args.show:
            return True

        # Check if all of the input files exist.
        for pattern in shlex.split(input_files):
            if len(glob.glob(pattern)) == 0:
                log.error(f'No file matching "{pattern}" found')
                log.info("")
                log.info(
                    f"Did you call `{self.script_name} get-data`? If you did, "
                    "check GET_DATA_CMD and INPUT_FILES in the Qleverfile"
                )
                return False

        if Containerize().is_running(system, server_container):
            log.error(
                f"{system} container {server_container} exists, "
                f"which means that server for {args.name} is already running. \n"
                f"Stop the container {server_container} with `{self.script_name} "
                "stop` first before loading the data."
            )
            return False

        if not image_id:
            build_successful = self.build_image(build_cmd, system, args.image)
            if not build_successful:
                return False
        else:
            log.info(
                f"{args.image} image present on the system. Executing command..."
            )

        # Run the index command.
        try:
            run_command(index_cmd)
            log.info(
                f"Follow `{self.script_name} log` until data loading is finished."
                f" (Ctrl-C stops following the log, but NOT the data loading!)"
            )
        except Exception as e:
            log.error(f"Building the index failed: {e}")
            return False

        return True
