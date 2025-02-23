from __future__ import annotations

import glob
import shlex
from pathlib import Path

from qlever.commands import index
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import run_command


class IndexCommand(index.IndexCommand):
    def __init__(self):
        self.script_name = "qoxigraph"

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name", "format"],
            "index": [
                "input_files",
            ],
            "runtime": ["system", "image", "index_container"],
        }

    def additional_arguments(self, subparser):
        subparser.add_argument(
            "--run-in-foreground",
            action="store_true",
            default=False,
            help=(
                "Run the index command in the foreground "
                "(default: run in the background)"
            ),
        )

    def execute(self, args) -> bool:
        system = args.system
        input_files = args.input_files
        index_container = args.index_container
        run_subcommand = "run --rm"
        if not args.run_in_foreground:
            run_subcommand += " -d"
        index_cmd = f"load --location /index --file /index/{input_files}"
        index_cmd = Containerize().containerize_command(
            cmd=index_cmd,
            container_system=system,
            run_subcommand=run_subcommand,
            image_name=args.image,
            container_name=index_container,
            volumes=[("$(pwd)", "/index")],
            use_bash=False,
        )

        # Show the command line.
        self.show(index_cmd, only_show=args.show)
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

        if len([p.name for p in Path.cwd().glob("*.sst")]) != 0:
            log.error(
                "Index files (*.sst) found in current directory "
                "which shows presence of a previous index"
            )
            log.info("")
            log.info("Aborting the index operation...")
            return False

        # Run the index command.
        try:
            run_command(index_cmd, show_output=True)
            if not args.run_in_foreground:
                log_cmd = f"{system} logs -f {index_container}"
                log.info(
                    "Showing logs for index command. Press Ctrl-C to stop "
                    "following (will not stop the index process)"
                )
                try:
                    run_command(log_cmd, show_output=True)
                except Exception as e:
                    log.error(f"Cannot display container logs - {e}")
        except Exception as e:
            log.error(f"Building the index failed: {e}")
            return False

        return True
