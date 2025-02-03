import glob
import shlex
from pathlib import Path

from other_engines.engine import SparqlEngine
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import run_command


class Oxigraph(SparqlEngine):
    def __init__(self) -> None:
        super().__init__(engine_name="Oxigraph")
        self.image = "ghcr.io/oxigraph/oxigraph"

    def get_config_arguments(self, command: str) -> dict[str : list[str]]:
        config_args = super().get_config_arguments(command)
        if config_args is not None:
            return config_args
        if command == "setup-config":
            return {}
        if command == "get-data":
            return {"data": ["name", "get_data_cmd"], "index": ["input_files"]}
        if command == "index":
            return {
                "data": ["name", "format"],
                "index": [
                    "input_files",
                ],
                "runtime": ["system", "image", "index_container"],
            }
        if command == "start":
            return {
                "data": ["name", "description"],
                "server": [
                    "host_name",
                    "port",
                ],
                "runtime": [
                    "system",
                    "image",
                    "server_container",
                    "index_container",
                ],
            }
        if command == "log":
            return {
                "data": ["name"],
                "runtime": [
                    "system",
                    "image",
                    "server_container",
                    "index_container",
                ],
            }
        if command == "stop":
            return {
                "data": ["name"],
                "server": ["port"],
                "runtime": ["server_container"],
            }
        raise ValueError(
            f"Couldn't fetch relevant Configfile arguments for {command}. "
            f"The command must be one of {self.commands.keys()}"
        )

    def index_command(self, args) -> bool:
        # Run the command in a container (if so desired).
        system = args.system
        input_files = args.input_files
        index_container = args.index_container
        index_cmd = f"load --location /index --file /index/{input_files}"
        # index_cmd += f" > {dataset}.index-log.txt 2>&1"
        index_cmd = Containerize().containerize_command(
            cmd=index_cmd,
            container_system=system,
            run_subcommand="run -d --rm",
            image_name=self.image,
            container_name=index_container,
            volumes=[("$(pwd)", "/index")],
            use_bash=False,
        )

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
                    "Did you call `qoxigraph get-data`? If you did, check "
                    "GET_DATA_CMD and INPUT_FILES in the Oxigraphfile"
                )
                return False

        if len([p.name for p in Path.cwd().glob("*.sst")]) != 0:
            log.error(
                "Index files (*.sst) found in current directory "
                "which shows presence of a previous index"
            )
            log.info("")
            log.info("Aborting the index operation...")
            return False

        # Run the index command.
        try:
            log.info(
                "Run `qoxigraph log` to see the progress of index command "
                "after this command terminates"
            )
            run_command(index_cmd, show_output=True)
        except Exception as e:
            log.error(f"Building the index failed: {e}")
            return False

        return True

    def start_command(self, args) -> bool:
        """
        Start the server for Oxigraph (requires that you have built an index with
        `qoxigraph index` before)
        """
        system = args.system
        dataset = args.name

        # Check if index and server container still running
        index_container = args.index_container
        server_container = args.server_container
        if Containerize().is_running(system, index_container):
            log.info(
                f"{system} container {index_container} is still up, "
                "which means that data loading is in progress. Please wait...\n"
                f"Check status of {index_container} with `qoxigraph log`"
            )
            return False

        if Containerize().is_running(system, server_container):
            log.info(
                f"{system} container {server_container} exists, "
                f"which means that server for {dataset} is already running. \n"
                f"Stop the container {server_container} with `qoxigraph stop` "
                "first before starting a new one."
            )
            return False

        # Check if index files (*.sst) present in cwd
        if len([p.name for p in Path.cwd().glob("*.sst")]) == 0:
            log.info(
                f"No Oxigraph index files for {dataset} found! "
                "Did you call `qoxigraph index`? If you did, check if .sst "
                "index files are present in current working directory."
            )
            return False

        port = int(args.port)
        start_cmd = "serve-read-only --location /index --bind=0.0.0.0:7878"
        start_cmd = Containerize().containerize_command(
            cmd=start_cmd,
            container_system=system,
            run_subcommand="run -d --restart=unless-stopped",
            image_name=self.image,
            container_name=server_container,
            volumes=[("$(pwd)", "/index")],
            ports=[(port, 7878)],
            use_bash=False,
        )

        # Show the command line.
        self.show(start_cmd, only_show=args.show)
        if args.show:
            return True

        # Run the start command.
        try:
            run_command(start_cmd, show_output=True)
            log.info(
                "Follow the server log by running `qoxigraph log` until "
                "the server is ready. (Ctrl-C stops following the log, "
                "but not the server)"
            )
            log.info(
                f"Oxigraph server webapp for {dataset} will be available at "
                f"http://localhost:{port} and the sparql endpoint for "
                f"queries is http://localhost:{port}/query"
            )
        except Exception as e:
            log.error(f"Starting the Oxigraph server failed: {e}")
            return False

        return True
