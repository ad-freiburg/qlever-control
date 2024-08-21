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
        self.presets = {
                "virtuoso-wikidata":
                "https://wikidata.demo.openlinksw.com/sparql",
                "qlever-wikidata":
                "https://qlever.cs.uni-freiburg.de/api/wikidata"
                }

    def description(self) -> str:
        return ("Show how much of the cache is currently being used")

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str: list[str]]:
        return {"server": ["port"], "ui": ["ui_config"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument("--sparql-endpoint", type=str,
                               help="URL of the SPARQL endpoint")
        subparser.add_argument("--sparql-endpoint-preset",
                               choices=self.presets.keys(),
                               help="Shortcut for setting the SPARQL endpoint")
        subparser.add_argument("--get-queries-cmd", type=str,
                               help="Command to get example queries as TSV "
                               "(description, query)")
        subparser.add_argument("--query-ids", type=str,
                               default="1-$",
                               help="Query IDs as comma-separated list of "
                               "ranges (e.g., 1-5,7,12-$)")
        subparser.add_argument("--query-regex", type=str,
                               help="Only consider example queries matching "
                               "this regex (using grep -Pi)")
        subparser.add_argument("--download-or-count",
                               choices=["download", "count"], default="count",
                               help="Whether to download the full result "
                               "or just compute the size of the result")
        subparser.add_argument("--limit", type=int,
                               help="Limit on the number of results")
        subparser.add_argument("--remove-offset-and-limit",
                               action="store_true", default=False,
                               help="Remove OFFSET and LIMIT from the query")
        subparser.add_argument("--accept", type=str,
                               choices=["text/tab-separated-values",
                                        "text/csv",
                                        "application/sparql-results+json",
                                        "text/turtle"],
                               default="text/tab-separated-values",
                               help="Accept header for the SPARQL query")
        subparser.add_argument("--clear-cache",
                               choices=["yes", "no"],
                               default="yes",
                               help="Clear the cache before each query")
        subparser.add_argument("--width-query-description", type=int,
                               default=40,
                               help="Width for printing the query description")
        subparser.add_argument("--width-error-message", type=int,
                               default=80,
                               help="Width for printing the error message "
                               "(0 = no limit)")
        subparser.add_argument("--width-result-size", type=int,
                               default=14,
                               help="Width for printing the result size")

    def execute(self, args) -> bool:
        # We can't have both `--remove-offset-and-limit` and `--limit`.
        if args.remove_offset_and_limit and args.limit:
            log.error("Cannot have both --remove-offset-and-limit and --limit")
            return False

        # If `args.accept` is `application/sparql-results+json`, we need `jq`.
        if args.accept == "application/sparql-results+json":
            try:
                subprocess.run("jq --version", shell=True, check=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except Exception as e:
                log.error(f"Please install `jq` for {args.accept} ({e})")
                return False

        # Handle shotcuts for SPARQL endpoint.
        if args.sparql_endpoint_preset in self.presets:
            args.sparql_endpoint = self.presets[args.sparql_endpoint_preset]
            args.ui_config = args.sparql_endpoint_preset.split("-")[1]

        # Limit only works with full result.
        if args.limit and args.download_or_count == "count":
            log.error("Limit only works with full result")
            return False

        # Clear cache only works for QLever.
        is_qlever = (not args.sparql_endpoint
                     or args.sparql_endpoint.startswith("https://qlever"))
        if args.clear_cache == "yes" and not is_qlever:
            log.warning("Clearing the cache only works for QLever")
            args.clear_cache = "no"

        # Show what the command will do.
        get_queries_cmd = (args.get_queries_cmd if args.get_queries_cmd
                           else f"curl -sv https://qlever.cs.uni-freiburg.de/"
                                f"api/examples/{args.ui_config}")
        sed_arg = args.query_ids.replace(",", "p;").replace("-", ",") + "p"
        get_queries_cmd += f" | sed -n '{sed_arg}'"
        if args.query_regex:
            get_queries_cmd += f" | grep -Pi {shlex.quote(args.query_regex)}"
        sparql_endpoint = (args.sparql_endpoint if args.sparql_endpoint
                           else f"localhost:{args.port}")
        self.show(f"Obtain queries via: {get_queries_cmd}\n"
                  f"SPARQL endpoint: {sparql_endpoint}\n"
                  f"Accept header: {args.accept}\n"
                  f"Clear cache before each query:"
                  f" {args.clear_cache.upper()}\n"
                  f"Download result for each query or just count:"
                  f" {args.download_or_count.upper()}" +
                  (f" with LIMIT {args.limit}" if args.limit else ""),
                  only_show=args.show)
        if args.show:
            return False

        # Get the example queries.
        try:
            example_query_lines = run_command(get_queries_cmd,
                                              return_output=True)
            if len(example_query_lines) == 0:
                log.error("No example queries matching the criteria found")
                return False
            example_query_lines = example_query_lines.splitlines()
        except Exception as e:
            log.error(f"Failed to get example queries: {e}")
            return False

        # Launch the queries one after the other and for each print: the
        # description, the result size, and the query processing time.
        total_time_seconds = 0.0
        total_result_size = 0
        count_succeeded = 0
        count_failed = 0
        for example_query_line in example_query_lines:
            # Parse description and query.
            description, query = example_query_line.split("\t")
            if len(query) == 0:
                log.error("Could not parse description and query, line is:")
                log.info("")
                log.info(example_query_line)
                return False

            # Clear the cache.
            if args.clear_cache == "yes":
                args.server_url = sparql_endpoint
                args.complete = False
                with mute_log():
                    ClearCacheCommand().execute(args)

            # Remove OFFSET and LIMIT (after the last closing bracket).
            if args.remove_offset_and_limit or args.limit:
                closing_bracket_idx = query.rfind("}")
                regexes = [re.compile(r"OFFSET\s+\d+\s*", re.IGNORECASE),
                           re.compile(r"LIMIT\s+\d+\s*", re.IGNORECASE)]
                for regex in regexes:
                    match = re.search(regex, query[closing_bracket_idx:])
                    if match:
                        query = query[:closing_bracket_idx + match.start()] + \
                                query[closing_bracket_idx + match.end():]

            # Limit query.
            if args.limit:
                query += f" LIMIT {args.limit}"

            # Count query.
            if args.download_or_count == "count":
                # First find out if there is a FROM clause.
                regex_from_clause = re.compile(r"\s*FROM\s+<[^>]+>\s*",
                                               re.IGNORECASE)
                match_from_clause = re.search(regex_from_clause, query)
                from_clause = " "
                if match_from_clause:
                    from_clause = match_from_clause.group(0)
                    query = (query[:match_from_clause.start()] + " " +
                             query[match_from_clause.end():])
                # Now we can add the outer SELECT COUNT(*).
                query = re.sub(r"SELECT ",
                               "SELECT (COUNT(*) AS ?qlever_count_)"
                               + from_clause + "WHERE { SELECT ",
                               query, count=1, flags=re.IGNORECASE) + " }"

            # A bit of pretty-printing.
            query = re.sub(r"\s+", " ", query)
            query = re.sub(r"\s*\.\s*\}", " }", query)

            # Launch query.
            try:
                curl_cmd = (f"curl -s {sparql_endpoint}"
                            f" -w \"HTTP code: %{{http_code}}\\n\""
                            f" -H \"Accept: {args.accept}\""
                            f" --data-urlencode query={shlex.quote(query)}")
                log.debug(curl_cmd)
                result_file = (f"qlever.example_queries.result."
                               f"{abs(hash(curl_cmd))}.tmp")
                start_time = time.time()
                http_code = run_curl_command(sparql_endpoint,
                                             headers={"Accept": args.accept},
                                             params={"query": query},
                                             result_file=result_file).strip()
                if http_code != "200":
                    raise Exception(f"HTTP code {http_code}"
                                    f"  {Path(result_file).read_text()}")
                time_seconds = time.time() - start_time
                error_msg = None
            except Exception as e:
                if args.log_level == "DEBUG":
                    traceback.print_exc()
                error_msg = re.sub(r"\s+", " ", str(e))

            # Get result size (via the command line, in order to avoid loading
            # a potentially large JSON file into Python, which is slow).
            if error_msg is None:
                try:
                    if args.download_or_count == "count":
                        if args.accept == "text/tab-separated-values":
                            result_size = run_command(
                                    f"sed 1d {result_file}",
                                    return_output=True)
                        else:
                            result_size = run_command(
                                    f"jq -r \".results.bindings[0]"
                                    f" | to_entries[0].value.value"
                                    f" | tonumber\" {result_file}",
                                    return_output=True)
                    else:
                        if (args.accept == "text/tab-separated-values"
                                or args.accept == "text/csv"):
                            result_size = run_command(
                                    f"sed 1d {result_file} | wc -l",
                                    return_output=True)
                        elif args.accept == "text/turtle":
                            result_size = run_command(
                                    f"sed '1d;/^@prefix/d;/^\\s*$/d' "
                                    f"{result_file} | wc -l",
                                    return_output=True)
                        else:
                            result_size = run_command(
                                    f"jq -r \".results.bindings | length\""
                                    f" {result_file}",
                                    return_output=True)
                    result_size = int(result_size)
                except Exception as e:
                    error_msg = str(e)

            # Remove the result file (unless in debug mode).
            if args.log_level != "DEBUG":
                Path(result_file).unlink(missing_ok=True)

            # Print description, time, result in tabular form.
            if len(description) > args.width_query_description:
                description = description[:args.width_query_description - 3]
                description += "..."
            if error_msg is None:
                log.info(f"{description:<{args.width_query_description}}  "
                         f"{time_seconds:6.2f} s  "
                         f"{result_size:>{args.width_result_size},}")
                count_succeeded += 1
                total_time_seconds += time_seconds
                total_result_size += result_size
            else:
                count_failed += 1
                if (args.width_error_message > 0
                        and len(error_msg) > args.width_error_message
                        and args.log_level != "DEBUG"):
                    error_msg = error_msg[:args.width_error_message - 3]
                    error_msg += "..."
                log.error(f"{description:<{args.width_query_description}}    "
                          f"failed   "
                          f"{colored(error_msg, 'red')}")

        # Print total time.
        log.info("")
        if count_succeeded > 0:
            query_or_queries = "query" if count_succeeded == 1 else "queries"
            description = (f"TOTAL   for {count_succeeded} {query_or_queries}")
            log.info(f"{description:<{args.width_query_description}}  "
                     f"{total_time_seconds:6.2f} s  "
                     f"{total_result_size:>14,}")
            description = (f"AVERAGE for {count_succeeded} {query_or_queries}")
            log.info(f"{description:<{args.width_query_description}}  "
                     f"{total_time_seconds / count_succeeded:6.2f} s  "
                     f"{round(total_result_size / count_succeeded):>14,}")
        else:
            if count_failed == 1:
                log.info(colored("One query failed", "red"))
            elif count_failed > 1:
                log.info(colored("All queries failed", "red"))

        # Return success (has nothing to do with how many queries failed).
        return True
