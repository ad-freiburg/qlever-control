import argparse
import argcomplete

VERSION = "0.0.1"


BOLD = "\033[1m"
NORMAL = "\033[0m"

parser = argparse.ArgumentParser(
    prog="qleverkontrol",
    description=f"{BOLD}Hello, I am the QLever script{NORMAL}",
    epilog="© 2023 University of Freiburg, Chair for Algorithms and Data Structures",
    allow_abbrev=True,
    exit_on_error=True,
    
)

parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
parser.add_argument(
    "--health", action="store_true", help="list particulars of the installation",
)
parser.add_argument("--autocomplete", action="store_true", help="auto completion in the command line")

parser.add_argument("--lsconfigs", action="store_true", help="list all bundled")
parser.add_argument("-c", "--config", help="load from a bundled Qleverfile")

parser_cmd = parser.add_subparsers(
    title="Supported runtime(s)",
    description="You can interact with QLever using one of the following:",
    help="interact with QLever with Docker or Natively",
    # required=True,
)

parser_cmd_docker = parser_cmd.add_parser(
    "docker", help="use Docker to index datasets and run server"
)
parser_cmd_docker.add_argument(
    "docker_action",
    choices=["up", "down", "stats"],
    help="Spawn, stop or show stats of a Qlever container"
)

parser_cmd_native = parser_cmd.add_parser(
    "native", help="use precompiled native executables"
)

parser_cmd_native.add_argument(
    "native_action",
    choices=["start", "stop"],
    help="Start or Stop ServerMain"

)


argcomplete.autocomplete(parser)