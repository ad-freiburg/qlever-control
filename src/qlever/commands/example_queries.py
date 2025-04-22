from __future__ import annotations

import csv
import json
import re
import shlex
import subprocess
import time
import traceback
from io import StringIO
from pathlib import Path
from typing import Any

from rdflib import Graph
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString
from termcolor import colored

from qlever.command import QleverCommand
from qlever.commands.clear_cache import ClearCacheCommand
from qlever.log import log, mute_log
from qlever.util import run_command, run_curl_command

MAX_RESULT_SIZE = 50


class ExampleQueriesCommand(QleverCommand):
    """
    Class for running a given sequence of example queries and showing
    their processing times and result sizes.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return "Run the given queries and show their processing times and result sizes"

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {"server": ["port"], "ui": ["ui_config"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "--sparql-endpoint", type=str, help="URL of the SPARQL endpoint"
        )
        subparser.add_argument(
            "--sparql-endpoint-preset",
            choices=[
                "https://qlever.dev/api/wikidata",
                "https://qlever.dev/api/uniprot",
                "https://qlever.dev/api/pubchem",
                "https://qlever.dev/api/osm-planet",
                "https://wikidata.demo.openlinksw.com/sparql",
                "https://sparql.uniprot.org/sparql",
            ],
            help="SPARQL endpoint from fixed list (to save typing)",
        )
        subparser.add_argument(
            "--get-queries-cmd",
            type=str,
            help="Command to get example queries as TSV (description, query)",
        )
        subparser.add_argument(
            "--queries-file",
            type=str,
            help=(
                "Path to a YAML file containing queries.  "
                "The YAML file should have a top-level "
                "key called 'queries', which is a list of dictionaries. "
                "Each dictionary should contain 'query' for the query name "
                "and 'sparql' for the SPARQL query."
            ),
        )
        subparser.add_argument(
            "--query-ids",
            type=str,
            default="1-$",
            help="Query IDs as comma-separated list of "
            "ranges (e.g., 1-5,7,12-$)",
        )
        subparser.add_argument(
            "--query-regex",
            type=str,
            help="Only consider example queries matching "
            "this regex (using grep -Pi)",
        )
        subparser.add_argument(
            "--download-or-count",
            choices=["download", "count"],
            default="download",
            help="Whether to download the full result "
            "or just compute the size of the result",
        )
        subparser.add_argument(
            "--limit", type=int, help="Limit on the number of results"
        )
        subparser.add_argument(
            "--remove-offset-and-limit",
            action="store_true",
            default=False,
            help="Remove OFFSET and LIMIT from the query",
        )
        subparser.add_argument(
            "--accept",
            type=str,
            choices=[
                "text/tab-separated-values",
                "text/csv",
                "application/sparql-results+json",
                "application/qlever-results+json",
                "text/turtle",
                "AUTO",
            ],
            default="application/sparql-results+json",
            help="Accept header for the SPARQL query; AUTO means "
            "`text/turtle` for CONSTRUCT AND DESCRIBE queries, "
            "`application/sparql-results+json` for all others",
        )
        subparser.add_argument(
            "--clear-cache",
            choices=["yes", "no"],
            default="no",
            help="Clear the cache before each query (only works for QLever)",
        )
        subparser.add_argument(
            "--width-query-description",
            type=int,
            default=70,
            help="Width for printing the query description",
        )
        subparser.add_argument(
            "--width-error-message",
            type=int,
            default=80,
            help="Width for printing the error message (0 = no limit)",
        )
        subparser.add_argument(
            "--width-result-size",
            type=int,
            default=14,
            help="Width for printing the result size",
        )
        subparser.add_argument(
            "--add-query-type-to-description",
            action="store_true",
            default=False,
            help="Add the query type (SELECT, ASK, CONSTRUCT, DESCRIBE, "
            "UNKNOWN) to the description",
        )
        subparser.add_argument(
            "--show-query",
            choices=["always", "never", "on-error"],
            default="never",
            help="Show the queries that will be executed (always, never, on error)",
        )
        subparser.add_argument(
            "--show-prefixes",
            action="store_true",
            default=False,
            help="When showing the query, also show the prefixes",
        )
        subparser.add_argument(
            "--generate-output-file",
            action="store_true",
            default=False,
            help="Generate output file in the 'output' directory",
        )
        subparser.add_argument(
            "--backend-name",
            default=None,
            help="Name for the backend that would be used in performance comparison",
        )
        subparser.add_argument(
            "--output-basename",
            default=None,
            help="Name for the dataset that would be used in performance comparison",
        )

    def pretty_printed_query(self, query: str, show_prefixes: bool) -> str:
        remove_prefixes_cmd = (
            " | sed '/^PREFIX /Id'" if not show_prefixes else ""
        )
        pretty_print_query_cmd = (
            f"echo {shlex.quote(query)}"
            f" | docker run -i --rm sparqling/sparql-formatter"
            f"{remove_prefixes_cmd} | grep -v '^$'"
        )
        try:
            query_pretty_printed = run_command(
                pretty_print_query_cmd, return_output=True
            )
            return query_pretty_printed.rstrip()
        except Exception as e:
            log.error(
                f"Failed to pretty-print query, returning original query: {e}"
            )
            return query.rstrip()

    def sparql_query_type(self, query: str) -> str:
        match = re.search(
            r"(SELECT|ASK|CONSTRUCT|DESCRIBE)\s", query, re.IGNORECASE
        )
        if match:
            return match.group(1).upper()
        else:
            return "UNKNOWN"

    @staticmethod
    def parse_queries_file(queries_file: str) -> dict[str, list[str, str]]:
        """
        Parse a YAML file and validate its structure.
        """
        yaml = YAML(typ="safe")
        with open(queries_file, "r", encoding="utf-8") as file:
            try:
                data = yaml.load(file)  # Load YAML safely
            except yaml.YAMLError as exc:
                log.error(f"Error parsing {queries_file} file: {exc}")

        error_msg = (
            "Error: YAML file must contain a top-level 'queries' key."
            "Error: 'queries' must be a list."
            "Error: Each item in 'queries' must contain 'query' and 'sparql' keys."
        )
        # Validate the structure
        if not isinstance(data, dict) or "queries" not in data:
            log.error(error_msg)
            return {}

        if not isinstance(data["queries"], list):
            log.error(error_msg)
            return {}

        for item in data["queries"]:
            if (
                not isinstance(item, dict)
                or "query" not in item
                or "sparql" not in item
            ):
                log.error(error_msg)
                return {}

        return data

    def get_example_queries(
        self,
        queries_file: str | None = None,
        get_queries_cmd: str | None = None,
    ) -> list[str]:
        """
        Get example queries from get_queries_cmd or by reading the yaml file
        """
        # yaml file case -> convert to tsv (description \t query)
        if queries_file is not None:
            queries_data = self.parse_queries_file(queries_file)
            queries = queries_data.get("queries")
            if queries is None:
                return []
            example_query_lines = [
                f"{query['query']}\t{query['sparql']}" for query in queries
            ]
            return example_query_lines

        # get_queries_cmd case -> run the command
        if get_queries_cmd is not None:
            # Get the example queries.
            try:
                example_query_lines = run_command(
                    get_queries_cmd, return_output=True
                )
                if len(example_query_lines) == 0:
                    return []
                example_query_lines = example_query_lines.splitlines()
                return example_query_lines
            except Exception as e:
                log.error(f"Failed to get example queries: {e}")
                return []
        return []

    def execute(self, args) -> bool:
        # We can't have both `--remove-offset-and-limit` and `--limit`.
        if args.remove_offset_and_limit and args.limit:
            log.error("Cannot have both --remove-offset-and-limit and --limit")
            return False

        if args.generate_output_file:
            if args.output_basename is None or args.backend_name is None:
                log.error(
                    "Both --output-basename and --backend-name parameters"
                    " must be passed when --generate-output-file is passed"
                )
                return False

        # If `args.accept` is `application/sparql-results+json` or
        # `application/qlever-results+json` or `AUTO`, we need `jq`.
        if args.accept in (
            "application/sparql-results+json",
            "application/qlever-results+json",
            "AUTO",
        ):
            try:
                subprocess.run(
                    "jq --version",
                    shell=True,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                log.error(f"Please install `jq` for {args.accept} ({e})")
                return False

        # Handle shotcuts for SPARQL endpoint.
        if args.sparql_endpoint_preset:
            args.sparql_endpoint = args.sparql_endpoint_preset

        # Limit only works with full result.
        if args.limit and args.download_or_count == "count":
            log.error("Limit only works with full result")
            return False

        # Clear cache only works for QLever.
        is_qlever = (
            not args.sparql_endpoint
            or args.sparql_endpoint.startswith("https://qlever")
        )
        if args.generate_output_file:
            is_qlever = is_qlever or "qlever" in args.backend_name.lower()
        if args.clear_cache == "yes":
            if is_qlever:
                log.warning(
                    "Clearing the cache before each query"
                    " (only works for QLever)"
                )
            else:
                log.warning(
                    "Clearing the cache only works for QLever"
                    ", option `--clear-cache` is ignored"
                )
                args.clear_cache = "no"

        # Show what the command will do.
        get_queries_cmd = (
            args.get_queries_cmd
            if args.get_queries_cmd
            else f"curl -sv https://qlever.cs.uni-freiburg.de/"
            f"api/examples/{args.ui_config}"
        )
        sed_arg = args.query_ids.replace(",", "p;").replace("-", ",") + "p"
        get_queries_cmd += f" | sed -n '{sed_arg}'"
        if args.query_regex:
            get_queries_cmd += f" | grep -Pi {shlex.quote(args.query_regex)}"
        sparql_endpoint = (
            args.sparql_endpoint
            if args.sparql_endpoint
            else f"localhost:{args.port}"
        )
        self.show(
            f"Obtain queries via: {get_queries_cmd}\n"
            f"SPARQL endpoint: {sparql_endpoint}\n"
            f"Accept header: {args.accept}\n"
            f"Download result for each query or just count:"
            f" {args.download_or_count.upper()}"
            + (f" with LIMIT {args.limit}" if args.limit else ""),
            only_show=args.show,
        )
        if args.show:
            return True

        # Get the example queries either from queries_file or get_queries_cmd
        example_query_lines = (
            self.get_example_queries(get_queries_cmd=get_queries_cmd)
            if args.queries_file is None
            else self.get_example_queries(queries_file=args.queries_file)
        )

        if len(example_query_lines) == 0:
            log.error("No example queries matching the criteria found")
            return False

        # We want the width of the query description to be an uneven number (in
        # case we have to truncated it, in which case we want to have a " ... "
        # in the middle).
        width_query_description_half = args.width_query_description // 2
        width_query_description = 2 * width_query_description_half + 1

        # Launch the queries one after the other and for each print: the
        # description, the result size (number of rows), and the query
        # processing time (seconds).
        query_times = []
        result_sizes = []
        yaml_records = {"queries": []}
        num_failed = 0
        for example_query_line in example_query_lines:
            # Parse description and query, and determine query type.
            description, query = example_query_line.split("\t")
            if len(query) == 0:
                log.error("Could not parse description and query, line is:")
                log.info("")
                log.info(example_query_line)
                return False
            query_type = self.sparql_query_type(query)
            if args.add_query_type_to_description or args.accept == "AUTO":
                description = f"{description} [{query_type}]"

            # Clear the cache.
            if args.clear_cache == "yes":
                args.server_url = sparql_endpoint
                args.complete = False
                clear_cache_successful = False
                with mute_log():
                    clear_cache_successful = ClearCacheCommand().execute(args)
                if not clear_cache_successful:
                    log.warn("Failed to clear the cache")

            # Remove OFFSET and LIMIT (after the last closing bracket).
            if args.remove_offset_and_limit or args.limit:
                closing_bracket_idx = query.rfind("}")
                regexes = [
                    re.compile(r"OFFSET\s+\d+\s*", re.IGNORECASE),
                    re.compile(r"LIMIT\s+\d+\s*", re.IGNORECASE),
                ]
                for regex in regexes:
                    match = re.search(regex, query[closing_bracket_idx:])
                    if match:
                        query = (
                            query[: closing_bracket_idx + match.start()]
                            + query[closing_bracket_idx + match.end() :]
                        )

            # Limit query.
            if args.limit:
                query += f" LIMIT {args.limit}"

            # Count query.
            if args.download_or_count == "count":
                # First find out if there is a FROM clause.
                regex_from_clause = re.compile(
                    r"\s*FROM\s+<[^>]+>\s*", re.IGNORECASE
                )
                match_from_clause = re.search(regex_from_clause, query)
                from_clause = " "
                if match_from_clause:
                    from_clause = match_from_clause.group(0)
                    query = (
                        query[: match_from_clause.start()]
                        + " "
                        + query[match_from_clause.end() :]
                    )
                # Now we can add the outer SELECT COUNT(*).
                query = (
                    re.sub(
                        r"SELECT ",
                        "SELECT (COUNT(*) AS ?qlever_count_)"
                        + from_clause
                        + "WHERE { SELECT ",
                        query,
                        count=1,
                        flags=re.IGNORECASE,
                    )
                    + " }"
                )

            # A bit of pretty-printing.
            query = re.sub(r"\s+", " ", query)
            query = re.sub(r"\s*\.\s*\}", " }", query)
            if args.show_query == "always":
                log.info("")
                log.info(
                    colored(
                        self.pretty_printed_query(query, args.show_prefixes),
                        "cyan",
                    )
                )

            # Accept header. For "AUTO", use `text/turtle` for CONSTRUCT
            # queries and `application/sparql-results+json` for all others.
            accept_header = args.accept
            if accept_header == "AUTO":
                if query_type == "CONSTRUCT" or query_type == "DESCRIBE":
                    accept_header = "text/turtle"
                else:
                    accept_header = "application/sparql-results+json"

            # Launch query.
            curl_cmd = (
                f"curl -s {sparql_endpoint}"
                f' -w "HTTP code: %{{http_code}}\\n"'
                f' -H "Accept: {accept_header}"'
                f" --data-urlencode query={shlex.quote(query)}"
            )
            log.debug(curl_cmd)
            result_file = (
                f"qlever.example_queries.result.{abs(hash(curl_cmd))}.tmp"
            )
            start_time = time.time()
            try:
                http_code = run_curl_command(
                    sparql_endpoint,
                    headers={"Accept": accept_header},
                    params={"query": query},
                    result_file=result_file,
                ).strip()
                if http_code == "200":
                    time_seconds = time.time() - start_time
                    error_msg = None
                else:
                    time_seconds = time.time() - start_time
                    error_msg = {
                        "short": f"HTTP code: {http_code}",
                        "long": re.sub(
                            r"\s+", " ", Path(result_file).read_text()
                        ),
                    }
            except Exception as e:
                time_seconds = time.time() - start_time
                if args.log_level == "DEBUG":
                    traceback.print_exc()
                error_msg = {
                    "short": "Exception",
                    "long": re.sub(r"\s+", " ", str(e)),
                }

            def get_json_error_msg(e: Exception) -> dict[str, str]:
                error_msg = {
                    "short": "Malformed JSON",
                    "long": "curl returned with code 200, "
                    "but the JSON is malformed: "
                    + re.sub(r"\s+", " ", str(e)),
                }
                return error_msg

            # Get result size (via the command line, in order to avoid loading
            # a potentially large JSON file into Python, which is slow).
            if error_msg is None:
                single_int_result = None
                # CASE 0: The result is empty despite a 200 HTTP code (not a
                # problem for CONSTRUCT and DESCRIBE queries).
                if Path(result_file).stat().st_size == 0 and (
                    not query_type == "CONSTRUCT"
                    and not query_type == "DESCRIBE"
                ):
                    result_size = 0
                    error_msg = {
                        "short": "Empty result",
                        "long": "curl returned with code 200, "
                        "but the result is empty",
                    }

                # CASE 1: Just counting the size of the result (TSV or JSON).
                elif args.download_or_count == "count":
                    if accept_header == "text/tab-separated-values":
                        result_size = run_command(
                            f"sed 1d {result_file}", return_output=True
                        )
                    elif accept_header == "application/qlever-results+json":
                        try:
                            # sed cmd to get the number between 2nd and 3rd double_quotes
                            result_size = run_command(
                                f"jq '.res[0]' {result_file}"
                                " | sed 's/[^0-9]*\\([0-9]*\\).*/\\1/'",
                                return_output=True,
                            )
                        except Exception as e:
                            error_msg = get_json_error_msg(e)
                    else:
                        try:
                            result_size = run_command(
                                f'jq -r ".results.bindings[0]'
                                f" | to_entries[0].value.value"
                                f' | tonumber" {result_file}',
                                return_output=True,
                            )
                        except Exception as e:
                            error_msg = get_json_error_msg(e)

                # CASE 2: Downloading the full result (TSV, CSV, Turtle, JSON).
                else:
                    if (
                        accept_header == "text/tab-separated-values"
                        or accept_header == "text/csv"
                    ):
                        result_size = run_command(
                            f"sed 1d {result_file} | wc -l", return_output=True
                        )
                    elif accept_header == "text/turtle":
                        result_size = run_command(
                            f"sed '1d;/^@prefix/d;/^\\s*$/d' "
                            f"{result_file} | wc -l",
                            return_output=True,
                        )
                    elif accept_header == "application/qlever-results+json":
                        result_size = run_command(
                            f'jq -r ".resultsize" {result_file}',
                            return_output=True,
                        )
                    else:
                        try:
                            result_size = int(
                                run_command(
                                    f'jq -r ".results.bindings | length"'
                                    f" {result_file}",
                                    return_output=True,
                                ).rstrip()
                            )
                        except Exception as e:
                            error_msg = get_json_error_msg(e)
                        if result_size == 1:
                            try:
                                single_int_result = int(
                                    run_command(
                                        f'jq -e -r ".results.bindings[0][] | .value"'
                                        f" {result_file}",
                                        return_output=True,
                                    ).rstrip()
                                )
                            except Exception:
                                pass

            error_msg_for_yaml = {}

            # Print description, time, result in tabular form.
            if len(description) > width_query_description:
                description = (
                    description[: width_query_description_half - 2]
                    + " ... "
                    + description[-width_query_description_half + 2 :]
                )
            if error_msg is None:
                result_size = int(result_size)
                single_int_result = (
                    f"   [single int result: {single_int_result:,}]"
                    if single_int_result is not None
                    else ""
                )
                log.info(
                    f"{description:<{width_query_description}}  "
                    f"{time_seconds:6.2f} s  "
                    f"{result_size:>{args.width_result_size},}"
                    f"{single_int_result}"
                )
                query_times.append(time_seconds)
                result_sizes.append(result_size)
            else:
                for key in error_msg.keys():
                    error_msg_for_yaml[key] = error_msg[key]
                num_failed += 1
                if (
                    args.width_error_message > 0
                    and len(error_msg["long"]) > args.width_error_message
                    and args.log_level != "DEBUG"
                    and args.show_query != "on-error"
                ):
                    error_msg["long"] = (
                        error_msg["long"][: args.width_error_message - 3]
                        + "..."
                    )
                seperator_short_long = (
                    "\n" if args.show_query == "on-error" else "  "
                )
                log.info(
                    f"{description:<{width_query_description}}    "
                    f"{colored('FAILED   ', 'red')}"
                    f"{colored(error_msg['short'], 'red'):>{args.width_result_size}}"
                    f"{seperator_short_long}"
                    f"{colored(error_msg['long'], 'red')}"
                )
                if args.show_query == "on-error":
                    log.info(
                        colored(
                            self.pretty_printed_query(
                                query, args.show_prefixes
                            ),
                            "cyan",
                        )
                    )
                    log.info("")

            # Get the yaml record if output file needs to be generated
            if args.generate_output_file:
                result_length = None if error_msg is not None else 1
                result_length = (
                    result_size
                    if args.download_or_count == "download"
                    and result_length is not None
                    else result_length
                )
                results_for_yaml = (
                    error_msg_for_yaml
                    if error_msg is not None
                    else result_file
                )
                yaml_record = self.get_record_for_yaml(
                    query=description,
                    sparql=self.pretty_printed_query(
                        query, args.show_prefixes
                    ),
                    client_time=time_seconds,
                    result=results_for_yaml,
                    result_size=result_length,
                    accept_header=accept_header,
                )
                yaml_records["queries"].append(yaml_record)

            # Remove the result file (unless in debug mode).
            if args.log_level != "DEBUG":
                Path(result_file).unlink(missing_ok=True)

        # Check that each query has a time and a result size, or it failed.
        assert len(result_sizes) == len(query_times)
        assert len(query_times) + num_failed == len(example_query_lines)

        if len(yaml_records["queries"]) != 0:
            outfile = (
                f"{args.output_basename}.{args.backend_name}.results.yaml"
            )
            self.write_query_data_to_yaml(
                query_data=yaml_records,
                out_file=outfile,
            )

        # Show statistics.
        if len(query_times) > 0:
            n = len(query_times)
            total_query_time = sum(query_times)
            average_query_time = total_query_time / n
            median_query_time = sorted(query_times)[n // 2]
            total_result_size = sum(result_sizes)
            average_result_size = round(total_result_size / n)
            median_result_size = sorted(result_sizes)[n // 2]
            query_or_queries = "query" if n == 1 else "queries"
            description = f"TOTAL   for {n} {query_or_queries}"
            log.info("")
            log.info(
                f"{description:<{width_query_description}}  "
                f"{total_query_time:6.2f} s  "
                f"{total_result_size:>14,}"
            )
            description = f"AVERAGE for {n} {query_or_queries}"
            log.info(
                f"{description:<{width_query_description}}  "
                f"{average_query_time:6.2f} s  "
                f"{average_result_size:>14,}"
            )
            description = f"MEDIAN  for {n} {query_or_queries}"
            log.info(
                f"{description:<{width_query_description}}  "
                f"{median_query_time:6.2f} s  "
                f"{median_result_size:>14,}"
            )

        # Show number of failed queries.
        if num_failed > 0:
            log.info("")
            description = "Number of FAILED queries"
            num_failed_string = f"{num_failed:>6}"
            if num_failed == len(example_query_lines):
                num_failed_string += "  [all]"
            log.info(
                colored(
                    f"{description:<{width_query_description}}  "
                    f"{num_failed:>24}",
                    "red",
                )
            )

        # Return success (has nothing to do with how many queries failed).
        return True

    def get_record_for_yaml(
        self,
        query: str,
        sparql: str,
        client_time: float,
        result: str | dict[str, str],
        result_size: int | None,
        accept_header: str,
    ) -> dict[str, Any]:
        """
        Construct a dictionary with query information for yaml file
        """
        record = {
            "query": query,
            "sparql": LiteralScalarString(sparql),
            "runtime_info": {},
        }
        if result_size is None:
            results = f"{result['short']}: {result['long']}"
            headers = []
        else:
            record["result_size"] = result_size
            result_size = (
                MAX_RESULT_SIZE
                if result_size > MAX_RESULT_SIZE
                else result_size
            )
            headers, results = self.get_query_results(
                result, result_size, accept_header
            )
            if accept_header == "application/qlever-results+json":
                runtime_info_cmd = (
                    f"jq 'if .runtimeInformation then"
                    f" .runtimeInformation else"
                    f' "null" end\' {result}'
                )
                runtime_info_str = run_command(
                    runtime_info_cmd, return_output=True
                )
                if runtime_info_str != "null":
                    record["runtime_info"] = json.loads(runtime_info_str)
        record["runtime_info"]["client_time"] = client_time
        record["headers"] = headers
        record["results"] = results
        return record

    def get_query_results(
        self, result_file: str, result_size: int, accept_header: str
    ) -> tuple[list[str], list[list[str]]]:
        """
        Return headers and results as a tuple
        """
        if accept_header in ("text/tab-separated-values", "text/csv"):
            separator = "," if accept_header == "text/csv" else "\t"
            get_result_cmd = f"sed -n '1,{result_size + 1}p' {result_file}"
            results_str = run_command(get_result_cmd, return_output=True)
            results = results_str.splitlines()
            reader = csv.reader(StringIO(results_str), delimiter=separator)
            headers = next(reader)
            results = [row for row in reader]
            return headers, results
        elif accept_header == "application/qlever-results+json":
            get_result_cmd = (
                f"jq '{{headers: .selected, results: .res[0:{result_size}]}}' "
                f"{result_file}"
            )
            results_str = run_command(get_result_cmd, return_output=True)
            results_json = json.loads(results_str)
            return results_json["headers"], results_json["results"]
        elif accept_header == "application/sparql-results+json":
            get_result_cmd = (
                f"jq '{{headers: .head.vars, "
                f"bindings: .results.bindings[0:{result_size}]}}' "
                f"{result_file}"
            )
            results_str = run_command(get_result_cmd, return_output=True)
            results_json = json.loads(results_str)
            results = []
            bindings = results_json.get("bindings", [])
            for binding in bindings:
                result = []
                if not binding or not isinstance(binding, dict):
                    results.append([])
                    continue
                for obj in binding.values():
                    value = '"' + obj["value"] + '"'
                    if obj["type"] == "uri":
                        value = "<" + value.strip('"') + ">"
                    elif "datatype" in obj:
                        value += "^^<" + obj["datatype"] + ">"
                    elif "xml:lang" in obj:
                        value += "@" + obj["xml:lang"]
                    result.append(value)
                results.append(result)
            return results_json["headers"], results
        else:  # text/turtle
            graph = Graph()
            graph.parse(result_file, format="turtle")
            headers = ["?subject", "?predicate", "?object"]
            results = []
            for i, (s, p, o) in enumerate(graph):
                if i >= result_size:
                    break
                results.append([str(s), str(p), str(o)])
            return headers, results

    @staticmethod
    def write_query_data_to_yaml(
        query_data: dict[str, list[dict[str, Any]]], out_file: str
    ) -> None:
        """
        Write yaml record for all queries to output yaml file
        """
        yaml = YAML()
        yaml.default_flow_style = False
        output_dir = Path(__file__).parent.parent / "evaluation" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        yaml_file_path = output_dir / out_file
        with open(yaml_file_path, "wb") as eval_yaml_file:
            yaml.dump(query_data, eval_yaml_file)
        symlink_path = Path(out_file)
        if not symlink_path.exists():
            symlink_path.symlink_to(yaml_file_path)
