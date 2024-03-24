from __future__ import annotations

import re
import shlex
import subprocess
import time

from termcolor import colored

from qlever.command import QleverCommand
from qlever.commands.clear_cache import ClearCacheCommand
from qlever.log import log, mute_log


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
        subparser.add_argument("--download-or-count",
                               choices=["download", "count"], default="count",
                               help="Whether to download the full result "
                               "or just compute the size of the result")
        subparser.add_argument("--limit", type=int,
                               help="Limit on the number of results")
        subparser.add_argument("--clear-cache",
                               choices=["yes", "no"],
                               default="yes",
                               help="Clear the cache before each query")

    def execute(self, args) -> bool:
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
                           else f"curl -s https://qlever.cs.uni-freiburg.de/"
                                f"api/examples/{args.ui_config}")
        sed_arg = args.query_ids.replace(",", "p;").replace("-", ",") + "p"
        get_queries_cmd += f" | sed -n '{sed_arg}'"
        sparql_endpoint = (args.sparql_endpoint if args.sparql_endpoint
                           else f"localhost:{args.port}")
        self.show(f"Obtain queries via: {get_queries_cmd}\n"
                  f"SPARQL endpoint: {sparql_endpoint}\n"
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
            # log.info(f"get_queries_cmd: {get_queries_cmd}")
            example_query_lines = subprocess.run(
                    get_queries_cmd, shell=True, check=True,
                    text=True, stdout=subprocess.PIPE).stdout.splitlines()
        except Exception as e:
            log.error(f"Failed to get example queries ({e})")
            return False
        # for i, line in enumerate(lines.splitlines()):
        #     try:
        #         description, query = line.split("\t")
        #         example_queries.append((description, query))
        # num_example_queries = len(example_queries)

        # Launch the queries one after the other and for each print: the
        # description, the result size, and the query processing time.
        count = 0
        total_time_seconds = 0.0
        total_result_size = 0
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

            # Count query.
            if args.download_or_count == "count":
                # Find first string matching ?[a-zA-Z0-9_]+ in query.
                match = re.search(r"\?[a-zA-Z0-9_]+", query)
                if not match:
                    log.error("Could not find a variable in this query:")
                    log.info("")
                    log.info(query)
                    return False
                first_var = match.group(0)
                query = query.replace(
                        "SELECT ",
                        f"SELECT (COUNT({first_var}) AS {first_var}_count_) "
                        f"WHERE {{ SELECT ", 1) + " }"

            # Limit query.
            if args.limit:
                query = query.replace(
                        "SELECT ", "SELECT * WHERE { SELECT ", 1) \
                          + f" }} LIMIT {args.limit}"

            # Launch query.
            query_cmd = (f"curl -s {sparql_endpoint}"
                         f" -H \"Accept: text/tab-separated-values\""
                         f" --data-urlencode query={shlex.quote(query)}")
            if args.download_or_count == "count":
                query_cmd += " | sed 1d"
            else:
                query_cmd += " | sed 1d | wc -l"
            try:
                log.debug(query_cmd)
                start_time = time.time()
                result_size = int(subprocess.run(
                        query_cmd, shell=True, check=True, text=True,
                        stdout=subprocess.PIPE).stdout)
                time_seconds = time.time() - start_time
                time_string = f"{time_seconds:.2f}"
                result_string = f"{result_size:>14,}"
            except Exception as e:
                time_seconds = 0.0
                time_string = "---"
                result_size = 0
                result_string = colored(f"        FAILED {e}", "red")

            # Print description, time, result in tabular form.
            if (len(description) > 60):
                description = description[:57] + "..."
            log.info(f"{description:<60}  {time_string:>6} s  "
                     f"{result_string}")
            count += 1
            total_time_seconds += time_seconds
            total_result_size += result_size

        # Print total time.
        log.info("")
        description = (f"TOTAL   for {count} "
                       f"{'query' if count == 1 else 'queries'}")
        log.info(f"{description:<60}  {total_time_seconds:6.2f} s  "
                 f"{total_result_size:>14,}")
        description = (f"AVERAGE for {count} "
                       f"{'query' if count == 1 else 'queries'}")
        log.info(f"{description:<60}  {total_time_seconds / count:6.2f} s  "
                 f"{round(total_result_size / count):>14,}")
        return True
