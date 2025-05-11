from __future__ import annotations

import json
import re
import shlex

import requests_sse
import requests
from termcolor import colored

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
            "which is not 100%% correct; as soon as chaining is supported, "
            "this will be fixed",
        )
        subparser.add_argument(
            "--num-groups",
            type=int,
            default=0,
            help="Number of groups to process before stopping "
            "(default: 0, i.e., process until interrupted)",
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
        source = requests_sse.EventSource(
            args.url, headers={"Accept": "text/event-stream"}
        )
        source.connect()
        date_list = []
        insert_data_list = []
        delete_data_list = []
        current_group_size = 0
        curl_cmd_count = 0
        total_num_ops = 0
        total_time_ms = 0
        for event in source:
            # Only process non-empty messages.
            if event.type != "message" or not event.data:
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
                date_list.sort()
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
                r"\s+", " ", delete_insert_operation
            )
            # log.warn(delete_insert_operation)

            # Construct curl command. For group size 1, send the operation via
            # `--data-urlencode`, otherwise write to file and send via `--data-binary`.
            sparql_endpoint = f"localhost:{args.port}"
            curl_cmd = (
                f"curl -s -X POST {sparql_endpoint}"
                f" -H 'Authorization: Bearer {args.access_token}'"
                f" -H 'Content-Type: application/sparql-update'"
            )
            if args.group_size == 1:
                curl_cmd += f" --data {shlex.quote(delete_insert_operation)}"
            else:
                curl_cmd_count += 1
                update_arg_file_name = f"update.sparql.{curl_cmd_count}"
                with open(update_arg_file_name, "w") as f:
                    f.write(delete_insert_operation)
                curl_cmd += f" --data-binary @{update_arg_file_name}"
            log.warn(curl_cmd)

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
                num_ops = result["delta-triples"]["operation"]["total"]
                time_ms = int(re.sub(r"ms$", "", result["time"]["total"]))
                time_ms_per_op = time_ms / num_ops
                log.info(
                    colored(
                        f"NUM_OPS: {num_ops:6}, "
                        f"INS: {ins_before:6} -> {ins_after:6}, "
                        f"DEL: {del_before:6} -> {del_after:6}, "
                        f"TIME: {time_ms:7} ms, "
                        f"TIME/OP: {time_ms_per_op:4.1f} ms",
                        attrs=["bold"],
                    )
                )
                total_num_ops += num_ops
                total_time_ms += time_ms
            except Exception as e:
                log.warn(
                    f"Error extracting statistics: {e}, "
                    f"curl command was: {curl_cmd}"
                )
                continue

            # Stop after processing the specified number of groups.
            log.info("")
            if args.num_groups > 0:
                if curl_cmd_count >= args.num_groups:
                    log.info(
                        f"Processed specified number of groups "
                        f"({args.num_groups}), terminating update command"
                    )
                    log.info(
                        colored(
                            f"TOTAL NUM_OPS: {total_num_ops:6}, "
                            f"TOTAL TIME: {total_time_ms:7} ms, "
                            f"AVG TIME/OP: {total_time_ms / total_num_ops:4.1f} ms",
                            attrs=["bold"],
                        )
                    )
                    return True
