from __future__ import annotations

import json
import math
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

from ruamel.yaml import YAML

from qlever.command import QleverCommand
from qlever.log import log

EVAL_DIR = Path(__file__).parent.parent / "evaluation"


def get_query_stats(queries: list[dict]) -> dict[str, float | int]:
    failed, under_1, bw_1_to_5, over_5 = 0, 0, 0, 0
    total_time, total_log_time = 0.0, 0.0
    runtimes = []
    for query in queries:
        runtime = float(query["runtime_info"]["client_time"])
        runtimes.append(runtime)
        total_time += runtime
        total_log_time += max(math.log(runtime), 0.001)
        if len(query["headers"]) == 0 and isinstance(query["results"], str):
            failed += 1
        elif runtime <= 1:
            under_1 += 1
        elif runtime > 5:
            over_5 += 1
        else:
            bw_1_to_5 += 1
    total_queries = len(queries)
    query_data = {
        "ameanTime": total_time / total_queries,
        "gmeanTime": math.exp(total_log_time / total_queries),
        "medianTime": sorted(runtimes)[total_queries // 2], 
        "under1s": (under_1 / total_queries) * 100,
        "between1to5s": (bw_1_to_5 / total_queries) * 100,
        "over5s": (over_5 / total_queries) * 100,
        "failed": (failed / total_queries) * 100,
    }
    return query_data


def create_performance_data(yaml_dir: Path) -> dict | None:
    yaml_parser = YAML(typ="safe")
    performance_data = {}
    if not yaml_dir.is_dir():
        return None
    for yaml_file in yaml_dir.glob("*.results.yaml"):
        file_name_split = yaml_file.stem.split(".")
        if len(file_name_split) != 3:
            continue
        dataset, engine, _ = file_name_split
        if performance_data.get(dataset) is None:
            performance_data[dataset] = {}
        if performance_data[dataset].get(engine) is None:
            performance_data[dataset][engine] = {}
        with yaml_file.open("r", encoding="utf-8") as queries_file:
            queries_data = yaml_parser.load(queries_file)
            query_stats = get_query_stats(queries_data["queries"])
            performance_data[dataset][engine] = {**query_stats, **queries_data}
    return performance_data


class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, yaml_dir: Path | None = None, **kwargs) -> None:
        self.yaml_dir = yaml_dir
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        path = unquote(self.path)

        if path == "/yaml_data":
            try:
                data = create_performance_data(self.yaml_dir)
                json_data = json.dumps(data, indent=2).encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(json_data)))
                self.end_headers()
                self.wfile.write(json_data)

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error loading YAMLs: {e}".encode("utf-8"))
        else:
            super().do_GET()


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
        (
            subparser.add_argument(
                "--host",
                type=str,
                default="localhost",
                help=(
                    "Host where the Performance comparison webapp will be "
                    "served (Default = localhost)"
                ),
            ),
        )
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
        handler = partial(
            CustomHTTPRequestHandler, directory=EVAL_DIR, yaml_dir=yaml_dir
        )
        httpd = HTTPServer(("", args.port), handler)
        log.info(
            f"Performance Comparison Web App is available at "
            f"http://{args.host}:{args.port}/www"
        )
        httpd.serve_forever()
        return True
