from __future__ import annotations

import glob
import shlex
from pathlib import Path

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import binary_exists, get_total_file_size, run_command


class IndexCommand(QleverCommand):
    def __init__(self):
        self.script_name = "qoxigraph"

    def description(self) -> str:
        return "Build the index for a given RDF dataset"

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name", "format"],
            "index": ["input_files", "ulimit", "index_binary", "lenient"],
            "runtime": ["system", "image", "index_container"],
        }

    def additional_arguments(self, subparser):
        pass

    @staticmethod
    def wrap_cmd_in_container(args, cmd: str) -> str:
        return Containerize().containerize_command(
            cmd=cmd,
            container_system=args.system,
            run_subcommand="run --rm",
            image_name=args.image,
            container_name=args.index_container,
            volumes=[("$(pwd)", "/index")],
            working_directory="/index",
            use_bash=False,
        )

    def execute(self, args) -> bool:
        index_cmd = (
            f"load {'--lenient ' if args.lenient else ''}"
            f"--location . --file {args.input_files} "
            f"|& tee {args.name}.index-log.txt"
        )

        if args.system == "native":
            index_cmd = f"{args.index_binary} {index_cmd}"
            # If the total file size is larger than 10 GB, set ulimit (such that a
            # large number of open files is allowed).
            total_file_size = get_total_file_size(
                shlex.split(args.input_files)
            )
            if args.ulimit is not None:
                index_cmd = f"ulimit -Sn {args.ulimit} && {index_cmd}"
            elif total_file_size > 1e10:
                index_cmd = f"ulimit -Sn 500000 && {index_cmd}"
        else:
            self.wrap_cmd_in_container(args, index_cmd)

        # Show the command line.
        self.show(index_cmd, only_show=args.show)
        if args.show:
            return True

        # Check if all of the input files exist.
        for pattern in shlex.split(args.input_files):
            if len(glob.glob(pattern)) == 0:
                log.error(f'No file matching "{pattern}" found')
                log.info("")
                log.info(
                    f"Did you call `{self.script_name} get-data`? If you did, "
                    "check GET_DATA_CMD and INPUT_FILES in the Qleverfile"
                )
                return False

        # When running natively, check if the binary exists and works.
        if args.system == "native":
            if not binary_exists(args.index_binary, "index-binary"):
                return False
        else:
            if Containerize().is_running(args.system, args.index_container):
                log.info(
                    f"{args.system} container {args.index_container} is still up, "
                    "which means that data loading is in progress. Please wait..."
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
            run_command(index_cmd, show_output=True, show_stderr=True)
        except Exception as e:
            log.error(f"Building the index failed: {e}")
            return False

        return True
