from __future__ import annotations

from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from qlever.command import QleverCommand
from qlever.log import log

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
        subparser.add_argument(
            "--host",
            type=str,
            default="localhost",
            help=(
                "Host where the Performance comparison webapp will be "
                "served (Default = localhost)"
            ),
        )
        subparser.add_argument(
            "--show-files-only",
            action="store_true",
            default=False,
            help="Show list of yaml files that will be used for comparison",
        )

    def execute(self, args) -> bool:
        if args.show_files_only:
            output_dir = EVAL_DIR / "output"
            for yaml_file in output_dir.iterdir():
                if yaml_file.is_file():
                    log.info(yaml_file.name)
            return True

        handler = partial(SimpleHTTPRequestHandler, directory=EVAL_DIR)
        httpd = HTTPServer(("", args.port), handler)
        log.info(
            f"Performance Comparison Web App is available at "
            f"http://{args.host}:{args.port}/www"
        )
        httpd.serve_forever()
        return True
