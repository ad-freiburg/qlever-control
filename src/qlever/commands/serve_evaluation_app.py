from __future__ import annotations

from pathlib import Path

from qlever.command import QleverCommand
from qlever.util import run_command

EVAL_DIR = Path(__file__).parent.parent / "evaluation"


class ServeEvaluationAppCommand(QleverCommand):
    """
    Class for executing the `serve-evaluation-app` command.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return "Serve the SPARQL Engine performance comparison webapp"

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "--port",
            type=int,
            default=8000,
            help=(
                "Port where the Performance comparison webapp will be "
                "served (Default = 8000)"
            ),
        )

        # subparser.add_argument(
        #     "--host",
        #     type=str,
        #     default="localhost",
        #     help=(
        #         "Host where the Performance comparison webapp will be "
        #         "served (Default = localhost)"
        #     ),
        # )
        subparser.add_argument(
            "--results-dir",
            type=str,
            default=".",
            help=(
                "Path to the directory where yaml result files from "
                "example-queries are saved (Default = current working dir)"
            ),
        )

    def execute(self, args) -> bool:
        yaml_dir = Path(args.results_dir)
        path_to_st_main = (
            Path(__file__).parent.parent / "evaluation" / "main.py"
        )
        serve_cmd = (
            f"export QLEVER_YAML_RESULTS_DIR={yaml_dir.absolute()} && "
            f"streamlit run {path_to_st_main.absolute()} --server.port {args.port}"
        )
        run_command(serve_cmd, show_output=True)
        return True
