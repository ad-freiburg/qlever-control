from __future__ import annotations

import glob
import shlex
from pathlib import Path

import rdflib

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import binary_exists, run_command


class IndexCommand(QleverCommand):
    def __init__(self):
        self.script_name = "qgraphdb"

    def description(self) -> str:
        return "Build the index for a given RDF dataset"

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name", "format"],
            "index": [
                "input_files",
                "index_binary",
                "threads",
                "jvm_args",
                "entity_index_size",
                "ruleset",
            ],
            "server": ["timeout", "read_only"],
            "runtime": ["system", "image", "index_container"],
        }

    def additional_arguments(self, subparser):
        pass

    def update_config_ttl(self, args) -> None:
        try:
            timeout = int(args.timeout[:-1])
        except ValueError:
            timeout = 0

        config_dict = {
            "repositoryID": args.name,
            "label": f"{args.name} repository TTL config file",
            "throw-QueryEvaluationException-on-timeout": "true",
            "read-only": "true" if args.read_only else "false",
            "query-timeout": str(timeout),
            "ruleset": args.ruleset,
            "entity-index-size": str(args.entity_index_size),
        }
        graph = rdflib.Graph()
        graph.parse(Path.cwd() / "config.ttl", format="ttl")
        for sub, pred, obj in graph:
            pred_str = str(pred).split("#")[1]
            if pred_str in config_dict:
                new_val = rdflib.Literal(config_dict[pred_str])
                graph.remove((sub, pred, obj))
                graph.add((sub, pred, new_val))
        graph.serialize(destination=Path.cwd() / "config.ttl", format="ttl")
        log.info(
            "config.ttl successfully overwritten with relevant Qleverfile entries!"
        )

    @staticmethod
    def wrap_cmd_in_container(args, cmd: str) -> str:
        return Containerize().containerize_command(
            cmd=cmd,
            container_system=args.system,
            run_subcommand="run --rm",
            image_name=args.image,
            container_name=args.index_container,
            volumes=[("$(pwd)", "/opt/data")],
            working_directory="/opt/data",
        )

    def execute(self, args) -> bool:
        index_cmd = (
            f"{args.index_binary} preload {args.jvm_args} "
            f"-c config.ttl -t {args.threads} "
            f"{args.input_files}"
        )
        index_cmd += f" | tee {args.name}.index-log.txt"

        if args.system != "native":
            index_cmd = self.wrap_cmd_in_container(args, index_cmd)

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

        # Run the index command.
        try:
            self.update_config_ttl(args)
            run_command(index_cmd, show_output=True)
        except Exception as e:
            log.error(f"Building the index failed: {e}")
            return False

        return True
