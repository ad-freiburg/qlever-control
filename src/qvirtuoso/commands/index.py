from __future__ import annotations

import glob
import shlex
import time
from pathlib import Path

from qlever.commands.stop import stop_container
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import run_command
from qoxigraph.commands import index


class IndexCommand(index.IndexCommand):
    def __init__(self):
        self.script_name = "qvirtuoso"

    def additional_arguments(self, subparser) -> None:
        return None

    def execute(self, args) -> bool:
        system = args.system
        input_files = args.input_files
        index_container = args.index_container

        run_subcommand = "run -d -e DBA_PASSWORD=dba"

        exec_cmd = f"{system} exec {index_container} "
        isql_cmd = "isql 1111 dba dba "
        ld_dir_cmd = (
            exec_cmd + isql_cmd + f"exec=\"ld_dir('.', '{input_files}', '');\""
        )
        run_cmd = (
            exec_cmd
            + 'bash -c "'
            + isql_cmd
            + "exec='rdf_loader_run();' && "
            + isql_cmd
            + "exec='checkpoint;'\""
        )

        start_cmd = Containerize().containerize_command(
            cmd="",
            container_system=system,
            run_subcommand=run_subcommand,
            image_name=args.image,
            container_name=index_container,
            volumes=[("$(pwd)", "/database")],
            use_bash=False,
        )

        cmd_to_show = f"{start_cmd}\n\n{ld_dir_cmd}\n{run_cmd}"

        # Show the command line.
        self.show(cmd_to_show, only_show=args.show)
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

        # Run the index command.
        try:
            # Run the index container in detached mode
            run_command(start_cmd)
            log.info("Waiting for Virtuoso server to be online...")
            time.sleep(5)
            last_log_line_cmd = "tail -n 1 virtuoso.log"
            if Path("virtuoso.log").exists():
                start_time = time.time()
                timeout = 60
                last_log_line = ""
                # Wait until the Virtuoso server is online at 1111
                while "Server online at 1111" not in last_log_line:
                    if time.time() - start_time > timeout:
                        log.error(
                            "Timed out waiting for Virtuoso to be online."
                        )
                        return False
                    last_log_line = run_command(
                        last_log_line_cmd, return_output=True
                    )
                    time.sleep(1)
            # Execute the ld_dir and rdf_loader_run commands
            log.info("Virtuoso server online! Loading data into Virtuoso...\n")
            run_command(ld_dir_cmd, show_output=True)
            run_command(run_cmd, show_output=True)
            # Stop the index container as we have the indexed files in cwd
            log.info("")
            log.info("Data loading has finished!")
            return stop_container(index_container)
        except Exception as e:
            log.error(f"Building the index failed: {e}")
            return False

        return True
