from __future__ import annotations

import json
import re
import shlex
import time

import rdflib.term
import requests
import requests_sse
from rdflib import Graph
from termcolor import colored

from qlever.command import QleverCommand
from qlever.log import log


# Monkey patch `rdflib.term._castLexicalToPython` to avoid casting of literals
# to Python types. We do not need it (all we want it convert Turtle to N-Triples),
# and we can speed up parsing by a factor of about 2.
def custom_cast_lexical_to_python(lexical, datatype):
    return None  # Your desired behavior


rdflib.term._castLexicalToPython = custom_cast_lexical_to_python


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
        subparser.add_argument(
            "--lag-seconds",
            type=int,
            default=5,
            help="When a message is encountered that is within this many "
            "seconds of the current time, finish the current batch "
            "(and show a warning that this happened)",
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
        current_group_size = 0
        group_count = 0
        total_num_ops = 0
        total_time_s = 0
        start_time = time.perf_counter()

        # Iterating over all messages in the stream.
        for event in source:
            # Beginning of a new group of messages.
            if current_group_size == 0:
                date_list = []
                group_assembly_start_time = time.perf_counter()
                insert_triples = set()
                delete_triples = set()

            # Check if the `args.group_size` is reached (note that we come here
            # after a `continue` due to an error).
            if group_count >= args.num_groups and args.num_groups > 0:
                break

            # Process the message.
            if event.type != "message" or not event.data:
                continue
            try:
                # event_id = json.loads(event.last_event_id)
                event_data = json.loads(event.data)
                # date_ms_since_epoch = event_id[0].get("timestamp")
                # date = time.strftime(
                #     "%Y-%m-%dT%H:%M:%SZ",
                #     time.gmtime(date_ms_since_epoch / 1000.0),
                # )
                date = event_data.get("meta").get("dt")
                # date = event_data.get("dt")
                date = re.sub(r"\.\d*Z$", "Z", date)
                entity_id = event_data.get("entity_id")
                operation = event_data.get("operation")
                rdf_added_data = event_data.get("rdf_added_data")
                rdf_deleted_data = event_data.get("rdf_deleted_data")

                # Process the to-be-deleted triples.
                if rdf_deleted_data is not None:
                    try:
                        rdf_deleted_data = rdf_deleted_data.get("data")
                        graph = Graph()
                        log.debug(f"RDF deleted data: {rdf_deleted_data}")
                        graph.parse(data=rdf_deleted_data, format="turtle")
                        for s, p, o in graph:
                            triple = f"{s.n3()} {p.n3()} {o.n3()}"
                            # NOTE: In case there was a previous `insert` of that
                            # triple, it is safe to remove that `insert`, but not
                            # the `delete` (in case the triple is contained in the
                            # original data).
                            if triple in insert_triples:
                                insert_triples.remove(triple)
                            delete_triples.add(triple)
                    except Exception as e:
                        log.error(f"Error reading `rdf_deleted_data`: {e}")
                        return False

                # Process the to-be-added triples.
                if rdf_added_data is not None:
                    try:
                        rdf_added_data = rdf_added_data.get("data")
                        graph = Graph()
                        log.debug("RDF added data: {rdf_added_data}")
                        graph.parse(data=rdf_added_data, format="turtle")
                        for s, p, o in graph:
                            triple = f"{s.n3()} {p.n3()} {o.n3()}"
                            # NOTE: In case there was a previous `delete` of that
                            # triple, it is safe to remove that `delete`, but not
                            # the `insert` (in case the triple is not contained in
                            # the original data).
                            if triple in delete_triples:
                                delete_triples.remove(triple)
                            insert_triples.add(triple)
                    except Exception as e:
                        log.error(f"Error reading `rdf_added_data`: {e}")
                        return False

            except Exception as e:
                log.error(f"Error reading data from message: {e}")
                log.info(event)
                continue

            # Continue assembling until the group size is reached.
            date_list.append(date)
            current_group_size += 1
            if current_group_size < args.group_size:
                continue

            # Process the current group of messages.
            group_assembly_end_time = time.perf_counter()
            group_assembly_time_ms = int(
                1000 * (group_assembly_end_time - group_assembly_start_time)
            )
            group_count += 1
            date_list.sort()
            current_group_size = 0
            if args.group_size == 1:
                log.info(
                    f"Processing operation {operation} from date {date} "
                    f"for entity {entity_id}"
                    f"  [assembly time: {group_assembly_time_ms:,} ms]"
                )
            else:
                log.info(
                    f"Processing group #{group_count} "
                    f"with {args.group_size:,} messages, "
                    f"date range: {date_list[0]} - {date_list[-1]}"
                    f"  [assembly time: {group_assembly_time_ms:,} ms]"
                )

            # Add the date of the last message to `insert_triples`.
            insert_triples.add(
                f"<http://wikiba.se/ontology#Dump> "
                f"<http://schema.org/dateModified> "
                f'"{date_list[-1]}"^^<http://www.w3.org/2001/XMLSchema#dateTime>'
            )

            # Construct update operation.
            delete_insert_operation = (
                f"DELETE {{\n  {' . \n  '.join(delete_triples)} .\n}} "
                f"INSERT {{\n  {' . \n  '.join(insert_triples)} .\n}} "
                f"WHERE {{ }}\n"
            )

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
                with open(f"update.result.{group_count}", "w") as f:
                    f.write(result)
            except Exception as e:
                log.warn(f"Error running `requests.post`: {e}")
                if args.group_size == 1:
                    log.warn(curl_cmd)
                log.info("")
                continue

            # Results should be a JSON, parse it.
            try:
                result = json.loads(result)
                if isinstance(result, list):
                    result = result[0]
            except Exception as e:
                log.error(
                    f"Error parsing JSON result: {e}"
                    f", the first 1000 characters are:"
                )
                log.info(result[:1000])
                log.info("")
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
            def get_time_ms(*keys: str) -> int:
                value = result["time"]
                for key in keys:
                    value = value[key]
                return int(value)
                # return int(re.sub(r"ms$", "", value))

            # Show statistics of the update operation.
            try:
                ins_after = result["delta-triples"]["after"]["inserted"]
                del_after = result["delta-triples"]["after"]["deleted"]
                ops_after = result["delta-triples"]["after"]["total"]
                num_ins = int(result["delta-triples"]["operation"]["inserted"])
                num_del = int(result["delta-triples"]["operation"]["deleted"])
                num_ops = int(result["delta-triples"]["operation"]["total"])
                time_ms = get_time_ms("total")
                time_us_per_op = int(1000 * time_ms / num_ops)
                log.info(
                    colored(
                        f"NUM_OPS: {num_ops:+6,} -> {ops_after:6,}, "
                        f"INS: {num_ins:+6,} -> {ins_after:6,}, "
                        f"DEL: {num_del:+6,} -> {del_after:6,}, "
                        f"TIME: {time_ms:7,} ms, "
                        f"TIME/OP: {time_us_per_op:,} µs",
                        attrs=["bold"],
                    )
                )

                # Also show a detailed breakdown of the total time.
                time_preparation = get_time_ms(
                    "execution", "processUpdateImpl", "preparation"
                )
                time_insert = get_time_ms(
                    "execution", "processUpdateImpl", "insertTriples", "total"
                )
                time_delete = get_time_ms(
                    "execution", "processUpdateImpl", "deleteTriples", "total"
                )
                time_snapshot = get_time_ms("execution", "snapshotCreation")
                time_writeback = get_time_ms("execution", "diskWriteback")
                time_unaccounted = time_ms - (
                    time_delete
                    + time_insert
                    + time_preparation
                    + time_snapshot
                    + time_writeback
                )
                log.info(
                    f"PREPARATION: {100 * time_preparation / time_ms:2.0f}%, "
                    # f"PLANNING: {100 * time_planning / time_ms:2.0f}%, "
                    f"INSERT: {100 * time_insert / time_ms:2.0f}%, "
                    f"DELETE: {100 * time_delete / time_ms:2.0f}%, "
                    f"SNAPSHOT: {100 * time_snapshot / time_ms:2.0f}%, "
                    f"WRITEBACK: {100 * time_writeback / time_ms:2.0f}%, "
                    f"UNACCOUNTED: {100 * time_unaccounted / time_ms:2.0f}%",
                )

                # Show the totals so far.
                total_num_ops += num_ops
                total_time_s += time_ms / 1000.0
                elapsed_time_s = time.perf_counter() - start_time
                time_us_per_op = int(1e6 * total_time_s / total_num_ops)
                log.info(
                    colored(
                        f"TOTAL NUM_OPS SO FAR: {total_num_ops:8,}, "
                        f"TOTAL TIME SO FAR: {total_time_s:4.0f} s, "
                        f"ELAPSED TIME SO FAR: {elapsed_time_s:4.0f} s, "
                        f"AVG TIME/OP SO FAR: {time_us_per_op:,} µs",
                        attrs=["bold"],
                    )
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
        elapsed_time_s = time.perf_counter() - start_time
        time_us_per_op = int(1e6 * total_time_s / total_num_ops)
        log.info(
            f"Processed {group_count} "
            f"group{'s' if group_count > 1 else ''}, "
            f"terminating update command"
        )
        log.info(
            colored(
                f"TOTAL NUM_OPS: {total_num_ops:8,}, "
                f"TOTAL TIME: {total_time_s:4.0f} s, "
                f"ELAPSED TIME: {elapsed_time_s:4.0f} s, "
                f"AVG TIME/OP: {time_us_per_op:,} µs",
                attrs=["bold"],
            )
        )
        return True
