from __future__ import annotations

from qlever.commands.example_queries import (
    ExampleQueriesCommand as QleverExampleQueriesCommand,
)


class ExampleQueriesCommand(QleverExampleQueriesCommand):
    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {"data": ["name"], "server": ["port"], "ui": ["ui_config"]}

    def execute(self, args) -> bool:
        if not args.sparql_endpoint:
            args.sparql_endpoint = (
                f"localhost:{args.port}/blazegraph/namespace/"
                f"{args.name}/sparql"
            )
        return super().execute(args)
