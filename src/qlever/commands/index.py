from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import get_total_file_size, run_command


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
        return {"data": ["name"],
                "index": ["file_names", "cat_files", "settings_json",
                          "index_binary",
                          "only_pso_and_pos_permutations", "use_patterns",
                          "with_text_index", "stxxl_memory"],
                "containerize": ["container_system",
                                 "image_name", "index_container_name"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
                "--overwrite-existing", action="store_true",
                default=False,
                help="Overwrite an existing index, think twice before using.")

    def execute(self, args) -> bool:
        # Construct the command line.
        index_cmd = (f"{args.cat_files} | {args.index_binary}"
                     f" -F ttl -f -"
                     f" -i {args.name}"
                     f" -s {args.name}.settings.json")
        if args.only_pso_and_pos_permutations:
            index_cmd += " --only-pso-and-pos-permutations --no-patterns"
        if not args.use_patterns:
            index_cmd += " --no-patterns"
        if args.with_text_index in \
                ["from_text_records", "from_text_records_and_literals"]:
            index_cmd += (f" -w {args.name}.wordsfile.tsv"
                          f" -d {args.name}.docsfile.tsv")
        if args.with_text_index in \
                ["from_literals", "from_text_records_and_literals"]:
            index_cmd += " --text-words-from-literals"
        if args.stxxl_memory:
            index_cmd += f" --stxxl-memory {args.stxxl_memory}"
        index_cmd += f" | tee {args.name}.index-log.txt"

        # If the total file size is larger than 10 GB, set ulimit (such that a
        # large number of open files is allowed).
        total_file_size = get_total_file_size(
                shlex.split(args.file_names))
        if total_file_size > 1e10:
            index_cmd = f"ulimit -Sn 1048576; {index_cmd}"

        # Run the command in a container (if so desired).
        if args.container_system in Containerize.supported_systems():
            index_cmd = Containerize().containerize_command(
                    index_cmd,
                    args.container_system, "run --rm",
                    args.image_name,
                    args.index_container_name,
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
        if args.container_system == "native":
            try:
                run_command(f"{args.index_binary} --help")
            except Exception as e:
                log.error(f"Running \"{args.index_binary}\" failed ({e}), "
                          f"set `--index-binary` to a different binary or "
                          f"use `--container_system`")

        # Check if index files (name.index.*) already exist.
        #
        # TODO: Have an addtional option --overwrite-existing.
        search_dir = Path.cwd()
        if search_dir.glob(f"{args.name}.index.*") \
                and not args.overwrite_existing:
            log.error(
                    f"Index files \"{args.name}.index.*\" already exist, "
                    f"if you want to overwrite them, use --overwrite-existing")
            return False

        # Write settings.json file.
        try:
            subprocess.run(settings_json_cmd, shell=True, check=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        except Exception as e:
            log.error(f"Running \"{settings_json_cmd}\" failed ({e})")
            return False

        # Run the index command.
        try:
            subprocess.run(index_cmd, shell=True, check=True)
        except Exception as e:
            log.error(f"Running \"{index_cmd}\" failed ({e})")
            return False

        return True
