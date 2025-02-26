from __future__ import annotations

import glob
import shlex

from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import run_command
from qoxigraph.commands import index


class IndexCommand(index.IndexCommand):
    def __init__(self):
        self.script_name = "qvirtuoso"

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {
            "data": ["name", "format"],
            "index": ["input_files"],
            "server": ["host_name", "port"],
            "runtime": ["system", "image", "server_container"],
        }

    def execute(self, args) -> bool:
        system = args.system
        input_files = args.input_files
        server_container = args.server_container

        exec_cmd = f"{system} exec {server_container} "
        isql_cmd = "isql 1111 "
        ld_dir_cmd = (
            exec_cmd + isql_cmd + f"exec=\"ld_dir('.', '{input_files}', '');\""
        )
        if not args.run_in_foreground:
            exec_cmd = f"{system} exec -d {server_container} "
        run_cmd = (
            exec_cmd
            + 'bash -c "'
            + isql_cmd
            + "exec='rdf_loader_run();' && "
            + isql_cmd
            + "exec='checkpoint;'\""
        )

        index_cmd = f"{ld_dir_cmd}\n{run_cmd}"

        # Show the command line.
        self.show(index_cmd, only_show=args.show)
        if args.show:
            return True

        # Check if all of the input files exist.
        for pattern in shlex.split(input_files):
            if len(glob.glob(pattern)) == 0:
                log.error(f'No file matching "{pattern}" found')
                log.info("")
                log.info(
                    f"Did you call `{self.script_name} get-data`? If you did, "
                    "check GET_DATA_CMD and INPUT_FILES in the Qleverfile"
                )
                return False

        if not Containerize().is_running(system, server_container):
            log.info(
                f"{system} container {server_container} not found! "
                f"Did you call `{self.script_name} start`? Virtuoso server "
                "must be started before building an index for the dataset!"
            )
            return False

        last_log_line_cmd = "tail -n 1 virtuoso.log"
        if len(glob.glob("virtuoso.log")) != 0:
            last_log_line = run_command(last_log_line_cmd, return_output=True)
            if "Server online at 1111" not in last_log_line:
                log.info(
                    "Server is not yet online! Please wait... "
                    f"Monitor server status by calling `{self.script_name} log`"
                )
                return False

        # Run the index command.
        try:
            run_command(ld_dir_cmd, show_output=True)
            run_command(run_cmd)
            log.info(
                f"Virtuoso server webapp for {input_files} will be available "
                f"at http://{args.host_name}:{args.port} and the sparql "
                f"endpoint for queries is http://{args.host_name}:{args.port}/sparql"
            )
            log.info("")
            if args.run_in_foreground:
                log.info(
                    "Follow the log as long as the server is"
                    " running (Ctrl-C stops the server)"
                )
            else:
                log.info(
                    f"Run `{self.script_name} log` to see the status until the "
                    "server is ready (Ctrl-C stops following the log, "
                    "but NOT the server)"
                )
        except Exception as e:
            log.error(f"Building the index failed: {e}")
            return False

        return True
