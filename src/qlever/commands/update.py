from __future__ import annotations

import json
import re
import shlex

import requests
import requests_sse
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
            f"in groups of {args.group_size:,} messages"
        )
        if args.num_groups > 0:
            cmd_description += f", for {args.num_groups} groups"
        else:
            cmd_description += ", until interrupted or stream ends"
        self.show(cmd_description, only_show=args.show)
        if args.show:
            return True

        # Initialize the SSE stream and all the statistics variables.
        source = requests_sse.EventSource(
            args.url, headers={"Accept": "text/event-stream"}
        )
        source.connect()
        date_list = []
        insert_data_list = []
        delete_data_list = []
        current_group_size = 0
        group_count = 0
        total_num_ops = 0
        total_time_ms = 0

        # Iterating over all messages in the stream.
        for event in source:
            # Check if the `args.group_size` is reached (note that we come here
            # after a `continue` due to an error).
            if group_count >= args.num_groups and args.num_groups > 0:
                break

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
                group_count += 1
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
                        f"Processing group #{group_count} "
                        f"with {args.group_size:,} messages, "
                        f"date range: {date_list[0]} - {date_list[-1]}"
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
            sparql_endpoint = f"http://localhost:{args.port}"
            curl_cmd = (
                f"curl -s -X POST {sparql_endpoint}"
                f" -H 'Authorization: Bearer {args.access_token}'"
                f" -H 'Content-Type: application/sparql-update'"
            )
            if args.group_size == 1:
                curl_cmd += f" --data {shlex.quote(delete_insert_operation)}"
            else:
                update_arg_file_name = f"update.sparql.{group_count}"
                with open(update_arg_file_name, "w") as f:
                    f.write(delete_insert_operation)
                curl_cmd += f" --data-binary @{update_arg_file_name}"
            log.warn(curl_cmd)

            # Run it (using `curl` for group size up to 1000, otherwise
            # `requests`).
            try:
                if args.group_size <= 1000:
                    warning_message = "Error running `curl`: {e}"
                    result = run_command(curl_cmd, return_output=True)
                else:
                    warning_message = "Error running `requests.post`: {e}"
                    headers = {
                        "Authorization": f"Bearer {args.access_token}",
                        "Content-Type": "application/sparql-update",
                    }
                    response = requests.post(
                        url=sparql_endpoint,
                        headers=headers,
                        data=delete_insert_operation,
                    )
                    result = response.text
            except Exception as e:
                log.warn(warning_message.format(e=e))
                if args.group_size == 1:
                    log.warn(curl_cmd)
                log.info("")
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
                log.info("")
                continue

            # Helper function for getting the value of `result["time"][...]`
            # without the "ms" suffix.
            def get_time_ms(key: str) -> int:
                value = result["time"][key]
                return int(re.sub(r"ms$", "", value))

            # Show statistics of the update operation.
            try:
                ins_before = result["delta-triples"]["before"]["inserted"]
                del_before = result["delta-triples"]["before"]["deleted"]
                ins_after = result["delta-triples"]["after"]["inserted"]
                del_after = result["delta-triples"]["after"]["deleted"]
                num_ops = int(result["delta-triples"]["operation"]["total"])
                time_ms = get_time_ms("total")
                time_ms_per_op = time_ms / num_ops
                log.info(
                    colored(
                        f"NUM_OPS: {num_ops:6,}, "
                        f"INS: {ins_before:6,} -> {ins_after:6,}, "
                        f"DEL: {del_before:6,} -> {del_after:6,}, "
                        f"TIME: {time_ms:7,} ms, "
                        f"TIME/OP: {time_ms_per_op:4.1f} ms",
                        attrs=["bold"],
                    )
                )
                total_num_ops += num_ops
                total_time_ms += time_ms

                # Also show a detailed breakdown of the total time.
                time_preparation = get_time_ms("preparation")
                time_planning = get_time_ms("planning")
                time_insert = get_time_ms("insert")
                time_delete = get_time_ms("delete")
                time_snapshot = get_time_ms("snapshot")
                time_writeback = get_time_ms("diskWriteback")
                time_where = get_time_ms("where")
                time_unaccounted = time_ms - (
                    time_delete
                    + time_insert
                    + time_planning
                    + time_preparation
                    + time_snapshot
                    + time_where
                    + time_writeback
                )
                log.info(
                    f"PREPARATION: {100 * time_preparation / time_ms:2.0f}%, "
                    f"PLANNING: {100 * time_planning / time_ms:2.0f}%, "
                    f"INSERT: {100 * time_insert / time_ms:2.0f}%, "
                    f"DELETE: {100 * time_delete / time_ms:2.0f}%, "
                    f"SNAPSHOT: {100 * time_snapshot / time_ms:2.0f}%, "
                    f"WRITEBACK: {100 * time_writeback / time_ms:2.0f}%, "
                    f"UNACCOUNTED: {100 * time_unaccounted / time_ms:2.0f}%",
                )

            except Exception as e:
                log.warn(
                    f"Error extracting statistics: {e}, "
                    f"curl command was: {curl_cmd}"
                )
                # Show traceback for debugging.
                import traceback

                traceback.print_exc()
                log.info("")
                continue

            # Stop after processing the specified number of groups.
            log.info("")
            if args.num_groups > 0:
                if group_count >= args.num_groups:
                    break

        # Final statistics after all groups have been processed.
        log.info(
            f"Processed {group_count} "
            f"group{'s' if group_count > 1 else ''}, "
            f"terminating update command"
        )
        log.info(
            colored(
                f"TOTAL NUM_OPS: {total_num_ops:6,}, "
                f"TOTAL TIME: {total_time_ms:7,} ms, "
                f"AVG TIME/OP: {total_time_ms / total_num_ops:4.1f} ms",
                attrs=["bold"],
            )
        )
        return True
