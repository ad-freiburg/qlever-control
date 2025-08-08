from __future__ import annotations

import json
import statistics
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

import yaml

from qlever.command import QleverCommand
from qlever.log import log

EVAL_DIR = Path(__file__).parent.parent / "evaluation"


QUERY_STATS_DICT = {
    "ameanTime": None,
    "gmeanTime": None,
    "medianTime": None,
    "under1s": 0.0,
    "between1to5s": 0.0,
    "over5s": 0.0,
    "failed": 0.0,
}


def get_query_stats(
    queries: list[dict], timeout: int | None, error_penalty: int
) -> dict[str, float | None]:
    query_data = {stat: val for stat, val in QUERY_STATS_DICT.items()}
    if not queries:
        return query_data
    failed = under_1 = bw_1_to_5 = over_5 = 0
    runtimes = []

    for query in queries:
        runtime = float(query["runtime_info"]["client_time"])
        if len(query["headers"]) == 0 and isinstance(query["results"], str):
            failed += 1
            runtime = (
                runtime * error_penalty
                if timeout is None
                else timeout * error_penalty
            )
        else:
            if runtime <= 1:
                under_1 += 1
            elif runtime > 5:
                over_5 += 1
            else:
                bw_1_to_5 += 1
        runtimes.append(runtime)

    total_successful = len(queries) - failed
    query_data["ameanTime"] = statistics.mean(runtimes)
    query_data["gmeanTime"] = statistics.geometric_mean(runtimes)
    query_data["medianTime"] = statistics.median(runtimes)
    query_data["failed"] = (failed / len(queries)) * 100
    if total_successful != 0:
        query_data["under1s"] = (under_1 / total_successful) * 100
        query_data["between1to5s"] = (bw_1_to_5 / total_successful) * 100
        query_data["over5s"] = (over_5 / total_successful) * 100
    return query_data


def create_performance_data(yaml_dir: Path, error_penalty: int) -> dict | None:
    performance_data = {"penalty": error_penalty}
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
            queries_data = yaml.safe_load(queries_file)
            query_stats = get_query_stats(
                queries_data["queries"],
                queries_data.get("timeout"),
                error_penalty,
            )
            performance_data[dataset][engine] = {**query_stats, **queries_data}
    return performance_data


class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args,
        yaml_dir: Path | None = None,
        error_penalty: int = 2,
        **kwargs,
    ) -> None:
        self.yaml_dir = yaml_dir
        self.error_penalty = error_penalty
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        path = unquote(self.path)

        if path == "/yaml_data":
            try:
                data = create_performance_data(
                    self.yaml_dir, self.error_penalty
                )
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
            "--results-dir",
            type=str,
            default=".",
            help=(
                "Path to the directory where yaml result files from "
                "example-queries are saved (Default = current working dir)"
            ),
        )
        subparser.add_argument(
            "--error-penalty",
            type=int,
            default=2,
            help=(
                "The timeout (or failed runtime) will be multiplied with this "
                "error penalty factor when computing aggregate query metrics "
                "(Default = 2)"
            ),
        )

    def execute(self, args) -> bool:
        yaml_dir = Path(args.results_dir)
        handler = partial(
            CustomHTTPRequestHandler,
            directory=EVAL_DIR,
            yaml_dir=yaml_dir,
            error_penalty=args.error_penalty,
        )
        httpd = HTTPServer(("", args.port), handler)
        log.info(
            f"Performance Comparison Web App is available at "
            f"http://{args.host}:{args.port}/www"
        )
        httpd.serve_forever()
        return True
