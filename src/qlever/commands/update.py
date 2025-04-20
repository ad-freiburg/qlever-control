from __future__ import annotations

import json
import re
import shlex

import sseclient

from qlever.command import QleverCommand
from qlever.log import log
from qlever.util import run_command


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
        return {"server": ["port", "access_token"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "url",
            nargs="?",
            type=str,
            default=self.wikidata_update_stream_url,
            help="URL of the SSE stream to update from",
        )
        subparser.add_argument(
            "--group-size",
            type=int,
            default=1,
            help="Group this many messages together into one update "
            "(default: one update for each message); NOTE: this simply "
            "concatenates the `rdf_added_data` and `rdf_deleted_data` fields, "
            "which is not 100% correct; as soon as chaining is supported, "
            "this will be fixed",
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

        # Execute the command, by iterating over all messages in the stream.
        client = sseclient.SSEClient(
            args.url, headers={"Accept": "text/event-stream"}
        )
        date_list = []
        insert_data_list = []
        delete_data_list = []
        current_group_size = 0
        curl_cmd_count = 0
        for event in client:
            # Only process non-empty messages.
            if event.event != "message" or not event.data:
                continue
            try:
                event_data = json.loads(event.data)
                date = event_data.get("dt")
                entity_id = event_data.get("entity_id")
                operation = event_data.get("operation")
                rdf_added_data = event_data.get("rdf_added_data")
                rdf_deleted_data = event_data.get("rdf_deleted_data")
                if rdf_added_data is not None:
                    rdf_added_data = rdf_added_data.get("data")
                if rdf_deleted_data is not None:
                    rdf_deleted_data = rdf_deleted_data.get("data")
            except Exception as e:
                log.error(f"Error reading data from message: {e}")
                continue

            # Adding to current group until group size is reached.
            date_list.append(date)
            if rdf_added_data:
                insert_data_list.append(rdf_added_data)
            if rdf_deleted_data:
                delete_data_list.append(rdf_deleted_data)
            current_group_size += 1
            if current_group_size < args.group_size:
                continue
            else:
                insert_data = "\n".join(insert_data_list)
                delete_data = "\n".join(delete_data_list)
                insert_data_list = []
                delete_data_list = []
                current_group_size = 0
                if args.group_size == 1:
                    log.info(
                        f"Processing operation {operation} from date {date} "
                        f"for entity {entity_id}"
                    )
                else:
                    log.info(
                        f"Processing group of {args.group_size} messages "
                        f"from dates {date_list[0]} to {date_list[-1]}"
                    )
                date_list = []

            # Construct update operation.
            delete_insert_operation = (
                f"DELETE {{ {delete_data} }} "
                f"INSERT {{ {insert_data} }} "
                f"WHERE {{ }}"
            )
            delete_insert_operation = re.sub(
                "\s+", " ", delete_insert_operation
            )
            # log.warn(delete_insert_operation)

            # Construct curl command.
            sparql_endpoint = f"localhost:{args.port}"
            update_arg = f"update={shlex.quote(delete_insert_operation)}"
            access_arg = f"access-token={shlex.quote(args.access_token)}"
            curl_cmd = (
                f"curl -s {sparql_endpoint}"
                f" --data-urlencode {update_arg}"
                f" --data-urlencode {access_arg}"
            )

            # For group size 1, show the command, otherwise write to file.
            if args.group_size == 1:
                log.warn(curl_cmd)
            else:
                curl_cmd_count += 1
                curl_cmd_file_name = f"update.curl-cmd.{curl_cmd_count}"
                with open(curl_cmd_file_name, "w") as f:
                    f.write(curl_cmd)
                log.warn(f"curl command written to {curl_cmd_file_name}")

            # Run it.
            try:
                result = run_command(curl_cmd, return_output=True)
            except Exception as e:
                log.warn(f"Error running curl command: {e}")
                if args.group_size == 1:
                    log.warn(curl_cmd)
                continue

            # Results should be a JSON, parse it.
            try:
                result = json.loads(result)
            except Exception as e:
                log.warn(f"Error parsing JSON result: {e}")
                if args.group_size == 1:
                    log.warn(curl_cmd)
                continue

            # Check if the result contains a QLever exception.
            if "exception" in result:
                error_msg = result["exception"]
                log.error(f"QLever exception: {error_msg}")
                if args.group_size == 1:
                    log.warn(curl_cmd)
                continue

            # Show statistics of the update operation.
            try:
                ins_before = result["delta-triples"]["before"]["inserted"]
                del_before = result["delta-triples"]["before"]["deleted"]
                ins_after = result["delta-triples"]["after"]["inserted"]
                del_after = result["delta-triples"]["after"]["deleted"]
                time_total = result["time"]["total"]
                print(
                    f"INS: {ins_before} -> {ins_after}, "
                    f"DEL: {del_before} -> {del_after}, "
                    f"TIME: {time_total}"
                )
            except Exception as e:
                log.warn(
                    f"Error extracting statistics: {e}, "
                    f"curl command was: {curl_cmd}"
                )
                continue
