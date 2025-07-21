from __future__ import annotations

import os
import signal
import time

from qlever.command import QleverCommand
from qlever.log import log
from qlever.util import run_command

from qlever.containerize import Containerize


# Exception to be raised when the user interrupts the command with Ctrl+C.
class UserInterruptException(Exception):
    pass


class OsmUpdateCommand(QleverCommand):
    """
    Class for executing the `osm-update` command.
    """

    def __init__(self):
        self.planet_replication_server_url = \
            "https://planet.osm.org/replication/"
        # Remember if Ctrl+C was pressed and if a update is currently running,
        # so we can handle it gracefully.
        self.is_running_update = False
        self.ctrl_c_pressed = False

    def description(self) -> str:
        return "Update OSM data for a given dataset"

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str: list[str]]:
        return {"data": ["name"],
                "server": ["host_name", "port", "access_token"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "granularity",
            nargs=1,
            choices=["minute", "hour", "day"],
            type=str,
            help="The granularity with which the OSM data should be updated. "
                 "Choose from 'minute', 'hour', or 'day'.",
        )
        subparser.add_argument(
            "--once",
            action='store_true',
            default=False,
            help="If set, the OSM data will be updated only once. "
                 "Otherwise, it will be updated continuously at the specified "
                 "granularity.",
        )
        subparser.add_argument(
            "--polyfile",
            nargs='?',
            type=str,
            help="The poly file that defines the boundaries of your osm "
                 "dataset. (Poly files for country extracts are available at "
                 "https://download.geofabrik.de/) If no poly file is provided,"
                 " the complete osm planet data will be used.",
        )
        subparser.add_argument(
            "--replication-server",
            nargs='?',
            type=str,
            help="The URL of the OSM replication server to use. By default, "
                 "the OSM planet replication server "
                 "('https://planet.osm.org/replication/) is used."
        )

    # Handle Ctrl+C gracefully by finishing the current update and then
    # exiting.
    def handle_ctrl_c(self, signal_received, frame):
        if self.ctrl_c_pressed:
            log.warn("\rCtrl+C pressed again, undoing the previous Ctrl+C")
            self.ctrl_c_pressed = False
        else:
            self.ctrl_c_pressed = True
            if self.is_running_update:
                log.warn("\rCtrl+C pressed, will finish the current update "
                         "and then exit [press Ctrl+C again to continue]")
            else:
                raise UserInterruptException()

    def execute(self, args) -> bool:
        # If the user has specified a replication server, use that one,
        # otherwise we use the planet replication server with the specified
        # granularity.
        granularity = args.granularity[0]
        replications_server: str
        if args.replication_server:
            replication_server = args.replication_server
        else:
            replication_server = (f"{self.planet_replication_server_url}"
                                  f"{granularity}/")

        granularity_in_seconds: int
        if granularity == "minute":
            granularity_in_seconds = 60
        elif granularity == "hour":
            granularity_in_seconds = 3600
        elif granularity == "day":
            granularity_in_seconds = 86400

        cmd_description = [
            f"Update OSM data for dataset '{args.name}' with "
            f"granularity '{granularity}' from the OSM replication"
            f" server '{replication_server}'."]
        self.show("\n".join(cmd_description), only_show=args.show)

        signal.signal(signal.SIGINT, self.handle_ctrl_c)
        if not args.once and not args.show:
            log.warn(
                "Press Ctrl+C to finish any currently running updates and end "
                "gracefully, press Ctrl+C again to continue\n"
            )

        # Construct the command to run the osm-live-updates tool.
        olu_cmd = self.construct_olu_cmd(replication_server, args)
        self.show(f"{olu_cmd}")
        if args.show:
            return True

        try:
            while True:
                if self.ctrl_c_pressed:
                    raise UserInterruptException()

                start_time = time.time()

                self.is_running_update = True
                log.info(f"Starting OSM data update...")
                process = run_command(olu_cmd, show_output=True, show_stderr=True, use_popen=True)
                try:
                    process.wait()
                except KeyboardInterrupt:
                    log.warn("\njsdfkalj OSM data update interrupted by user.")
                    self.is_running_update = False
                    self.ctrl_c_pressed = True

                log.info("\nOSM data update completed successfully.")
                self.is_running_update = False

                # If the user has specified `--once`, we exit after the
                # first update.
                if args.once:
                    return True

                # Wait for the next update interval based on the granularity
                elapsed = time.time() - start_time
                sleep_time = max(0, granularity_in_seconds - elapsed)
                if sleep_time > 0:
                    log.info(f"\nWaiting for {sleep_time:.0f} seconds "
                             f"until the next update...")
                time.sleep(sleep_time)

        except UserInterruptException:
            log.info("\nOSM data update interrupted by user.")
            return True

        except BaseException as e:
            log.error(f"An error occurred during the OSM data update: {e}")
            return False

    def construct_olu_cmd(self, replication_server_url: str, args) -> str:
        sparql_endpoint = f"http://{args.host_name}:{args.port}"
        container_name = f"olu-{args.name}"

        olu_cmd = f"{sparql_endpoint}"
        olu_cmd += f" -a {args.access_token}"
        olu_cmd += f" -f {replication_server_url}"
        olu_cmd += f" --qlever"
        olu_cmd += f" --statistics"

        # If the user has specified a polygon file, we add it to the command.
        if args.polyfile:
            # Check if polygon file exists
            if not os.path.exists(args.polyfile):
                log.error(f'No file matching "{args.polyfile}" found')
                log.info("")
                log.info("Check if the polyfile exists and if the path is "
                         "correct.")
                return False

            olu_cmd += f" --polygon {args.polyfile}"

        olu_cmd = Containerize().containerize_command(
            olu_cmd,
            "docker",
            "run --rm",
            "olu:latest",
            container_name,
            volumes=[("$(pwd)", "/update")],
            working_directory="/update",
            use_bash=False
        )

        return olu_cmd
