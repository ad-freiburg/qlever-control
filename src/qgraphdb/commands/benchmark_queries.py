from __future__ import annotations

from qlever.commands.benchmark_queries import (
    BenchmarkQueriesCommand as QleverBenchmarkQueriesCommand,
)


class BenchmarkQueriesCommand(QleverBenchmarkQueriesCommand):
    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name"],
            "server": ["host_name", "port", "timeout"],
            "ui": ["ui_config"],
        }

    def execute(self, args) -> bool:
        if not args.sparql_endpoint:
            port = 7200 if not args.override_port else args.override_port
            args.sparql_endpoint = (
                f"{args.host_name}:{port}/repositories/{args.name}"
            )
        return super().execute(args)
