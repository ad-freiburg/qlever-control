from __future__ import annotations

from qlever.commands import stop


class StopCommand(stop.StopCommand):
    def description(self) -> str:
        return "Stop Oxigraph server for a given dataset or port"

    def additional_arguments(self, subparser):
        return None

    def execute(self, args) -> bool:
        server_container = args.server_container

        description = f"Checking for container with name {server_container}"
        self.show(description, only_show=args.show)
        if args.show:
            return True

        # First check if container is running and if yes, stop and remove it
        return stop.stop_container(server_container)
