from __future__ import annotations

import requests
import sseclient

from qlever.command import QleverCommand
from qlever.log import log


class UpdateCommand(QleverCommand):
    """
    Class for executing the `update` command.
    """

    def __init__(self):
        self.wikidata_update_stream_url = (
            "https://stream.wikimedia.org/v2/"
            "stream/rdf-streaming-updater.mutation.v2"
        )

    def description(self) -> str:
        return "Update from given SSE stream"

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {"server": ["access_token"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "url",
            nargs="?",
            type=str,
            default=self.wikidata_update_stream_url,
            help="URL of the SSE stream to update from",
        )

    def execute(self, args) -> bool:
        # Construct the command and show it.
        cmd_description = (
            f"Process SSE stream from {args.url} "
            f"as long as this command is running"
        )
        self.show(cmd_description, only_show=args.show)
        if args.show:
            return True

        # Execute the command.
        response = requests.get(
            args.url,
            stream=True,
            headers={
                "Accept": "text/event-stream",
            },
        )
        client = sseclient.SSEClient(response)
        for event in client.events():
            log.info(event.data)
