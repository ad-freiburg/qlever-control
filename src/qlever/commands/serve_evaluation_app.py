from __future__ import annotations

import json
import math
import re
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

import yaml

from qlever.command import QleverCommand
from qlever.log import log

EVAL_DIR = Path(__file__).parent.parent / "evaluation"



def get_query_stats(queries: list[dict]) -> dict[str, float | None]:
    query_data = {stat: val for stat, val in QUERY_STATS_DICT.items()}    
    failed = under_1 = bw_1_to_5 = over_5 = 0
    total_time = total_log_time = 0.0
    runtimes = []
    for query in queries:
        if len(query["headers"]) == 0 and isinstance(query["results"], str):
            failed += 1
        else:
            runtime = float(query["runtime_info"]["client_time"])
            total_time += runtime
            total_log_time += max(math.log(runtime), 0.001)
            runtimes.append(runtime)
            if runtime <= 1:
                under_1 += 1
            elif runtime > 5:
                over_5 += 1
            else:
                bw_1_to_5 += 1
    total_successful = len(runtimes)
    if total_successful == 0:
        query_data["failed"] = 100.0
    else:
        query_data["ameanTime"] = total_time / total_successful
        query_data["gmeanTime"] = math.exp(total_log_time / total_successful)
        query_data["medianTime"] = sorted(runtimes)[total_successful // 2]
        query_data["under1s"] = (under_1 / total_successful) * 100
        query_data["between1to5s"] = (bw_1_to_5 / total_successful) * 100
        query_data["over5s"] = (over_5 / total_successful) * 100
        query_data["failed"] = (failed / len(queries)) * 100
    return query_data


def create_performance_data(yaml_dir: Path) -> dict | None:
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
            queries_data = yaml.safe_load(queries_file)
            query_stats = get_query_stats(queries_data["queries"])
            performance_data[dataset][engine] = {**query_stats, **queries_data}
    return performance_data


QUERY_STATS_DICT = {
    "ameanTime": None,
    "gmeanTime": None,
    "medianTime": None,
    "under1s": 0.0,
    "between1to5s": 0.0,
    "over5s": 0.0,
    "failed": 0.0,
}


def get_all_query_stats_by_kb(
    performance_data: dict[str, dict[str, float | list]], kb: str
) -> dict[str, list]:
    """
    Given a knowledge base (kb), get all query stats for each engine to display
    on the main page of eval web app as a table
    """
    engines_dict = performance_data[kb]
    engines_dict_for_table = {col: [] for col in ["engine_name"] + QUERY_STATS_DICT.keys()}
    for engine, engine_stats in engines_dict.items():
        engines_dict_for_table["engine_name"].append(engine.capitalize())
        for metric_key in QUERY_STATS_DICT.keys():
            metric = engine_stats[metric_key]
            engines_dict_for_table[metric_key].append(metric)
    return engines_dict_for_table


def extract_core_value(sparql_value: list[str] | str) -> str:
    if isinstance(sparql_value, list):
        if not sparql_value:
            return ""
        sparql_value = sparql_value[0]

    if not isinstance(sparql_value, str) or not sparql_value.strip():
        return ""

    # URI enclosed in angle brackets
    if sparql_value.startswith("<") and sparql_value.endswith(">"):
        return sparql_value[1:-1]

    # Literal string (e.g., "\"Some value\"")
    literal_match = re.match(r'^"((?:[^"\\]|\\.)*)"', sparql_value)
    if literal_match:
        raw = literal_match.group(1)
        return re.sub(r"\\(.)", r"\1", raw)

    # Fallback
    return sparql_value


def get_single_result(query_data) -> str | None:
    result_size = query_data.get("result_size")
    result_size = 0 if result_size is None else result_size
    single_result = None
    if (
        result_size == 1
        and len(query_data["headers"]) == 1
        and len(query_data["results"]) == 1
    ):
        single_result = query_data["results"][0]
        single_result = extract_core_value(single_result)
        try:
            single_result = f"{int(single_result):,}"
        except ValueError:
            pass
    return single_result


def get_query_runtimes(
    performance_data: dict[str, dict[str, float | list]], kb: str, engine: str
) -> dict[str, list]:
    all_queries_data = performance_data[kb][engine]["queries"]
    query_runtimes = {
        "query": [],
        "runtime": [],
        "failed": [],
        "result_size": [],
    }
    for query_data in all_queries_data:
        query_runtimes["query"].append(query_data["query"])
        runtime = round(query_data["runtime_info"]["client_time"], 2)
        query_runtimes["runtime"].append(runtime)
        failed = (
            isinstance(query_data["results"], str)
            or len(query_data["headers"]) == 0
        )
        query_runtimes["failed"].append(failed)
        result_size = query_data.get("result_size")
        result_size = 0 if result_size is None else result_size
        single_result = get_single_result(query_data)
        result_size_to_display = (
            f"{result_size:,}"
            if single_result is None
            else f"1 [{single_result}]"
        )
        query_runtimes["result_size"].append(result_size_to_display)
    return query_runtimes


def get_query_results_df(
    headers: list[str], query_results: list[list[str]]
) -> dict[str, list[str]]:
    query_results_lists = [[] for _ in headers]
    for result in query_results:
        for i in range(len(headers)):
            query_results_lists[i].append(result[i])
    query_results_dict = {
        header: query_results_lists[i] for i, header in enumerate(headers)
    }
    return query_results_dict


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
