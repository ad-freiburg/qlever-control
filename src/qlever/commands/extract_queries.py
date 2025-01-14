from __future__ import annotations

import re

from qlever.command import QleverCommand
from qlever.log import log


class ExtractQueriesCommand(QleverCommand):
    """
    Class for executing the `extract-queries` command.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return "Extract all SPARQL queries from the server log"

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {"data": ["name"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "--description-format",
            type=str,
            default="Log query {i}",
            help="Prefix for the description of the extracted queries"
            " (default: `Log query {i}`)",
        )
        subparser.add_argument(
            "--output-file",
            type=str,
            default="log-queries.txt",
            help="Output file for the extracted queries (default: `log-queries.txt`)",
        )

    def execute(self, args) -> bool:
        # Show what the command does.
        log_file_name = f"{args.name}.server-log.txt"
        self.show(
            f"Extract SPARQL queries from `{log_file_name}`"
            f" and write them to `{args.output_file}`",
            only_show=args.show,
        )
        if args.show:
            return True

        # Regex for log entries of the form
        # 2025-01-14 04:47:44.950 - INFO
        log_line_regex = (
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) - [A-Z]+:"
        )

        # Read the log file line by line.
        log_file = open(log_file_name, "r")
        queries_file = open(args.output_file, "w")
        query = None
        query_index = 0
        tsv_line_short_width = 150
        for line in log_file:
            if "Processing the following SPARQL query" in line:
                query = []
                query_index += 1
                continue
            if query is not None:
                # Skipe line that start with #
                if not re.match(log_line_regex, line):
                    if not re.match(r"^\s*#", line):
                        line = re.sub(r" #.*", "", line)
                        query.append(line)
                else:
                    query = re.sub(r"\s+", " ", "\n".join(query)).strip()
                    description = args.description_format.format(i=query_index)
                    tsv_line = f"{description}\t{query}"
                    tsv_line_short = (
                        tsv_line
                        if len(tsv_line) < tsv_line_short_width
                        else tsv_line[:tsv_line_short_width] + "..."
                    )
                    log.info(tsv_line_short)
                    print(tsv_line, file=queries_file)
                    query = None
        log_file.close()
        queries_file.close()
        return True
