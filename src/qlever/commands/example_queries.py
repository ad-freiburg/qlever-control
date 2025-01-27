from __future__ import annotations

import re
import shlex
import subprocess
import time
import traceback
from pathlib import Path

from termcolor import colored

from qlever.command import QleverCommand
from qlever.commands.clear_cache import ClearCacheCommand
from qlever.log import log, mute_log
from qlever.util import run_command, run_curl_command


class ExampleQueriesCommand(QleverCommand):
    """
    Class for executing the `warmup` command.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return "Show how much of the cache is currently being used"

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
            help="Command to get example queries as TSV "
            "(description, query)",
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
            default="yes",
            help="Clear the cache before each query",
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
            help="Width for printing the error message " "(0 = no limit)",
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
        except Exception:
            log.error(
                "Failed to pretty-print query, "
                "returning original query: {e}"
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

    def execute(self, args) -> bool:
        # We can't have both `--remove-offset-and-limit` and `--limit`.
        if args.remove_offset_and_limit and args.limit:
            log.error("Cannot have both --remove-offset-and-limit and --limit")
            return False

        # If `args.accept` is `application/sparql-results+json` or
        # `application/qlever-results+json` or `AUTO`, we need `jq`.
        if (
            args.accept == "application/sparql-results+json"
            or args.accept == "application/qlever-results+json"
            or args.accept == "AUTO"
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
        if args.clear_cache == "yes" and not is_qlever:
            log.warning("Clearing the cache only works for QLever")
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
            f"Clear cache before each query:"
            f" {args.clear_cache.upper()}\n"
            f"Download result for each query or just count:"
            f" {args.download_or_count.upper()}"
            + (f" with LIMIT {args.limit}" if args.limit else ""),
            only_show=args.show,
        )
        if args.show:
            return True

        # Get the example queries.
        try:
            example_query_lines = run_command(
                get_queries_cmd, return_output=True
            )
            if len(example_query_lines) == 0:
                log.error("No example queries matching the criteria found")
                return False
            example_query_lines = example_query_lines.splitlines()
        except Exception as e:
            log.error(f"Failed to get example queries: {e}")
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
            try:
                curl_cmd = (
                    f"curl -s {sparql_endpoint}"
                    f' -w "HTTP code: %{{http_code}}\\n"'
                    f' -H "Accept: {accept_header}"'
                    f" --data-urlencode query={shlex.quote(query)}"
                )
                log.debug(curl_cmd)
                result_file = (
                    f"qlever.example_queries.result."
                    f"{abs(hash(curl_cmd))}.tmp"
                )
                start_time = time.time()
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
                    error_msg = {
                        "short": f"HTTP code: {http_code}",
                        "long": re.sub(
                            r"\s+", " ", Path(result_file).read_text()
                        ),
                    }
            except Exception as e:
                if args.log_level == "DEBUG":
                    traceback.print_exc()
                error_msg = {
                    "short": "Exception",
                    "long": re.sub(r"\s+", " ", str(e)),
                }

            # Get result size (via the command line, in order to avoid loading
            # a potentially large JSON file into Python, which is slow).
            if error_msg is None:
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
                    else:
                        try:
                            result_size = run_command(
                                f'jq -r ".results.bindings[0]'
                                f" | to_entries[0].value.value"
                                f' | tonumber" {result_file}',
                                return_output=True,
                            )
                        except Exception as e:
                            error_msg = {
                                "short": "Malformed JSON",
                                "long": "curl returned with code 200, "
                                "but the JSON is malformed: "
                                + re.sub(r"\s+", " ", str(e)),
                            }

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
                            result_size = run_command(
                                f'jq -r ".results.bindings | length"'
                                f" {result_file}",
                                return_output=True,
                            )
                        except Exception as e:
                            error_msg = {
                                "short": "Malformed JSON",
                                "long": re.sub(r"\s+", " ", str(e)),
                            }

            # Remove the result file (unless in debug mode).
            if args.log_level != "DEBUG":
                Path(result_file).unlink(missing_ok=True)

            # Print description, time, result in tabular form.
            if len(description) > width_query_description:
                description = (
                    description[: width_query_description_half - 2]
                    + " ... "
                    + description[-width_query_description_half + 2 :]
                )
            if error_msg is None:
                result_size = int(result_size)
                log.info(
                    f"{description:<{width_query_description}}  "
                    f"{time_seconds:6.2f} s  "
                    f"{result_size:>{args.width_result_size},}"
                )
                query_times.append(time_seconds)
                result_sizes.append(result_size)
            else:
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

        # Check that each query has a time and a result size, or it failed.
        assert len(result_sizes) == len(query_times)
        assert len(query_times) + num_failed == len(example_query_lines)

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
