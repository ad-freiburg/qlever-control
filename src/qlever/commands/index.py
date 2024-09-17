from __future__ import annotations

import glob
import shlex

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import (get_existing_index_files, get_total_file_size,
                         run_command)


class IndexCommand(QleverCommand):
    """
    Class for executing the `index` command.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return ("Build the index for a given RDF dataset")

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str: list[str]]:
        return {"data": ["name", "format"],
                "index": ["input_files", "cat_input_files", "settings_json",
                          "index_binary",
                          "only_pso_and_pos_permutations", "use_patterns",
                          "text_index", "stxxl_memory"],
                "runtime": ["system", "image", "index_container"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
                "--overwrite-existing", action="store_true",
                default=False,
                help="Overwrite an existing index, think twice before using.")

    def execute(self, args) -> bool:
        # Construct the command line.
        index_cmd = (f"{args.cat_input_files} | {args.index_binary}"
                     f" -F {args.format} -"
                     f" -i {args.name}"
                     f" -s {args.name}.settings.json")
        if args.only_pso_and_pos_permutations:
            index_cmd += " --only-pso-and-pos-permutations --no-patterns"
        if not args.use_patterns:
            index_cmd += " --no-patterns"
        if args.text_index in \
                ["from_text_records", "from_text_records_and_literals"]:
            index_cmd += (f" -w {args.name}.wordsfile.tsv"
                          f" -d {args.name}.docsfile.tsv")
        if args.text_index in \
                ["from_literals", "from_text_records_and_literals"]:
            index_cmd += " --text-words-from-literals"
        if args.stxxl_memory:
            index_cmd += f" --stxxl-memory {args.stxxl_memory}"
        index_cmd += f" | tee {args.name}.index-log.txt"

        # If the total file size is larger than 10 GB, set ulimit (such that a
        # large number of open files is allowed).
        total_file_size = get_total_file_size(
                shlex.split(args.input_files))
        if total_file_size > 1e10:
            index_cmd = f"ulimit -Sn 1048576; {index_cmd}"

        # Run the command in a container (if so desired).
        if args.system in Containerize.supported_systems():
            index_cmd = Containerize().containerize_command(
                    index_cmd,
                    args.system, "run --rm",
                    args.image,
                    args.index_container,
                    volumes=[("$(pwd)", "/index")],
                    working_directory="/index")

        # Command for writing the settings JSON to a file.
        settings_json_cmd = (f"echo {shlex.quote(args.settings_json)} "
                             f"> {args.name}.settings.json")

        # Show the command line.
        self.show(f"{settings_json_cmd}\n{index_cmd}", only_show=args.show)
        if args.show:
            return False

        # When running natively, check if the binary exists and works.
        if args.system == "native":
            try:
                run_command(f"{args.index_binary} --help")
            except Exception as e:
                log.error(f"Running \"{args.index_binary}\" failed, "
                          f"set `--index-binary` to a different binary or "
                          f"set `--system to a container system`")
                log.info("")
                log.info(f"The error message was: {e}")
                return False

        # Check if all of the input files exist.
        for pattern in shlex.split(args.input_files):
            if len(glob.glob(pattern)) == 0:
                log.error(f"No file matching \"{pattern}\" found")
                log.info("")
                log.info("Did you call `qlever get-data`? If you did, check "
                         "GET_DATA_CMD and INPUT_FILES in the QLeverfile")
                return False

        # Check if index files (name.index.*) already exist.
        existing_index_files = get_existing_index_files(args.name)
        if len(existing_index_files) > 0 and not args.overwrite_existing:
            log.error(
                    f"Index files for basename \"{args.name}\" found, if you "
                    f"want to overwrite them, use --overwrite-existing")
            log.info("")
            log.info(f"Index files found: {existing_index_files}")
            return False

        # Remove already existing container.
        if args.system in Containerize.supported_systems() \
                and args.overwrite_existing:
            if Containerize.is_running(args.system, args.index_container):
                log.info(f"An Index process is still running. Stopping it...")
                try:
                    run_command(f"{args.system} rm -f {args.index_container}")
                except Exception as e:
                    log.error(f"Removing existing container failed: {e}")
                    return False

        # Write settings.json file.
        try:
            run_command(settings_json_cmd)
        except Exception as e:
            log.error(f"Writing the settings.json file failed: {e}")
            return False

        # Run the index command.
        try:
            run_command(index_cmd, show_output=True)
        except Exception as e:
            log.error(f"Building the index failed: {e}")
            return False

        return True
