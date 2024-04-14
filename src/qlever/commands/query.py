from __future__ import annotations

import shlex
import time
import traceback

from qlever.command import QleverCommand
from qlever.log import log
from qlever.util import run_command


class QueryCommand(QleverCommand):
    """
    Class for executing the `query` command.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return ("Send a query to a SPARQL endpoint")

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str: list[str]]:
        return {"server": ["port"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument("--query", type=str,
                               default="SELECT * WHERE { ?s ?p ?o } LIMIT 10",
                               help="SPARQL query to send")
        subparser.add_argument("--sparql-endpoint", type=str,
                               help="URL of the SPARQL endpoint")
        subparser.add_argument("--accept", type=str,
                               choices=["text/tab-separated-values",
                                        "text/csv",
                                        "application/sparql-results+json",
                                        "application/sparql-results+xml",
                                        "application/qlever-results+json"],
                               default="text/tab-separated-values",
                               help="Accept header for the SPARQL query")
        subparser.add_argument("--no-time", action="store_true",
                               default=False,
                               help="Do not print the (end-to-end) time taken")

    def execute(self, args) -> bool:
        # Show what the command will do.
        sparql_endpoint = (args.sparql_endpoint if args.sparql_endpoint
                           else f"localhost:{args.port}")
        curl_cmd = (f"curl -s {sparql_endpoint}"
                    f" -H \"Accept: {args.accept}\""
                    f" --data-urlencode query={shlex.quote(args.query)}")
        self.show(curl_cmd, only_show=args.show)
        if args.show:
            return False

        # Launch query.
        try:
            start_time = time.time()
            run_command(curl_cmd, show_output=True)
            time_msecs = round(1000 * (time.time() - start_time))
            if not args.no_time and args.log_level != "NO_LOG":
                log.info("")
                log.info(f"Query processing time (end-to-end):"
                         f" {time_msecs:,d} ms")
        except Exception as e:
            if args.log_level == "DEBUG":
                traceback.print_exc()
            log.error(e)
            return False

        return True
