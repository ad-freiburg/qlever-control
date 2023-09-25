import argparse
import argcomplete

from src.qlever_config import QleverConfig

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
# parser.add_argument(
#     "-c",
#     "--config",
#     metavar="CONFIG",
#     help="load from a bundled Qleverfile",
# )


group_options = parser.add_argument_group(
    "Qlever Options",
    description="Sanity checks, version info, autocomplete, etc...",
    # help="Checking version, health status, system installation, etc."
)


group_options.add_argument(
    "--health",
    action="store_true",
    help="list particulars of the installation",
)
group_options.add_argument(
    "--autocomplete",
    action="store_true",
    help="auto completion in the command line",
)
group_options.add_argument(
    "--lsconfigs", action="store_true", help="list all bundled Qleverfiles"
)

group_options.add_argument(
    "--setup-config",
    # action="store_true",
    choices=QleverConfig.show_available_config_names(),  # default bundled configs
    default="Qleverfile.default",
    metavar="Qle..",
    help="create a new config in the current dir",
)

group_qlever_action = parser.add_argument_group(
    title="Qlever Actions",
    description="Execute Qlever actions against selected config",
).add_mutually_exclusive_group()


group_qlever_action.add_argument(
    "-g",
    "--get-data",
    action="store_true",
    help="downloads .zip file of size X MB, uncompressed to Y MB",
)

group_qlever_action.add_argument(
    "-i",
    "--index",
    action="store_true",
    help="takes ~X seconds and ~Y GB RAM (on an AMD Ryzen 9 5900X)",
)

group_qlever_action.add_argument(
    "-s",
    "--start",
    action="store_true",
    help="starts the server (instant)",
)


argcomplete.autocomplete(parser)
