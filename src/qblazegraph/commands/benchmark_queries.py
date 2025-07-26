from __future__ import annotations

from qlever.commands.benchmark_queries import (
    BenchmarkQueriesCommand as QleverBenchmarkQueriesCommand,
)


class BenchmarkQueriesCommand(QleverBenchmarkQueriesCommand):
    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {"data": ["name"], "server": ["port"], "ui": ["ui_config"]}

    def execute(self, args) -> bool:
        if not args.sparql_endpoint:
            args.sparql_endpoint = (
                f"{args.host_name}:{args.port}/blazegraph/namespace/kb/sparql"
            )
        return super().execute(args)
