from __future__ import annotations

from qoxigraph.commands.query import QueryCommand as QoxigraphQueryCommand


class QueryCommand(QoxigraphQueryCommand):
    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name"],
            "server": ["override_port", "host_name", "access_token"],
        }

    def execute(self, args) -> bool:
        if not args.sparql_endpoint:
            port = 7200 if not args.override_port else args.override_port
            args.sparql_endpoint = (
                f"{args.host_name}:{port}/repositories/{args.name}"
            )
        super().execute(args)
