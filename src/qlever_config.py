# import importlib.resources
# import pkgutil
import os
from pathlib import Path
import logging
from configparser import ConfigParser, ExtendedInterpolation
from thefuzz.process import extractOne
from src.qlever_logging import log
import Qleverfiles

BLUE = "\033[34m"
RED = "\033[31m"
BOLD = "\033[1m"
NORMAL = "\033[0m"

# ref: https://stackoverflow.com/a/58941536
# data = importlib.resources.read_text("Qleverfiles", "Qleverfile.olympics")
# data = pkgutil.get_data("Qleverfiles", "Qleverfile.olympics").decode()


class QleverConfig:
    def __init__(self) -> None:
        self.config = ConfigParser(interpolation=ExtendedInterpolation())

        # load defaults first, then override them with Qleverfile
        # TODO: check if file exists
        self.config.read_dict(self.__DEFAULTS("dummy"))
        self.config.read("Qleverfile")
        print(self.config.items())

        # If the log level was not explicitly set by the first command-line
        # argument (see below), set it according to the Qleverfile.
        if log.level == 0:  # logging.NOTSET:
            log_level = self.config["general"]["log_level"].upper()
            try:
                log.setLevel(getattr(logging, log_level))
            except AttributeError:
                log.error(f'Invalid log level: "{log_level}"')

        # Show some information (for testing purposes only).
        log.debug(
            f"Parsed Qleverfile, sections are: " f"{', '.join(self.config.sections())}"
        )

    def __DEFAULTS(self, dataname: str) -> dict:
        return {
            "general": {
                "log_level": "info",
            },
            "server": {
                "binary": "ServerMain",
                "num_threads": "8",
                "cache_max_size_gb": "5",
                "cache_max_size_gb_single_entry": "1",
                "cache_max_num_entries": "100",
                "with_text_index": "no",
                "only_pso_and_pos_permutations": "no",
                "no_patterns": "no",
            },
            "index": {
                "binary": "IndexBuilderMain",
                "with_text_index": "no",
                "only_pso_and_pos_permutations": "no",
                "no_patterns": "no",
            },
            "docker": {
                "image": "adfreiburg/qlever",
                "container_server": f"qlever.server.{dataname}",
                "container_indexer": f"qlever.indexer.{dataname}",
            },
            "ui": {
                "port": "7000",
                "image": "adfreiburg/qlever-ui",
                "container": "qlever-ui",
            },
        }

    @staticmethod
    def show_available_config_names() -> list[str]:
        """
        ls all the bundled configuration files (Qleverfiles)

        TODO: append other Qleverfile files in the current directory

        Get available config names from the Qleverfiles directory
        (which should be in the same directory as this script).

        sample:
        [
            "Qleverfile.default",
            "Qleverfile.olympics",
            "Qleverfile.dblp",
            "Qleverfile.uniprot",
            "Qleverfile.imdb",
            "Qleverfile.pubchem",
            "Qleverfile.scientists",
            "Qleverfile.osm-country",
            "Qleverfile.yago-4",
            "Qleverfile.wikidata",
        ]
        """
        return list(
            map(
                lambda x: x.name,
                # TODO: something better
                Path(Qleverfiles.__path__[0]).glob("Qleverfile*"),
            )
        )

    @staticmethod
    def print_config(config_name: str) -> str:
        """
        Dumps contents of a bundled config file.

        If the config_name didn't match any of the bundled config,
        Levenshtein Distance is calculated to get the closest result
        """
        ls = QleverConfig.show_available_config_names()
        # TODO: not necessary,
        # since --setup-config is validated by argparse (choice=[...])
        if config_name not in ls:
            didyoumean, _ = extractOne(query=config_name, choices=ls)
            log.warning(f"'{config_name}' not found, did you mean: '{didyoumean}'?")
            return ""
        return Path(Qleverfiles.__path__[0], config_name).read_text(encoding="UTF-8")

    @staticmethod
    def write_config(config_name: str = "Qleverfile.default") -> None:
        """
        Setup a pre-filled Qleverfile in the current directory.
        """

        log.info(f"{BLUE}Creating a pre-filled Qleverfile{NORMAL}")
        log.info("")

        # If there is already a Qleverfile in the current directory, exit.
        if os.path.isfile("Qleverfile"):
            log.error("Qleverfile already exists in current directory")
            log.info("")
            log.info(
                "If you want to create a new Qleverfile using "
                "`qlever --setup-config`, delete the existing Qleverfile "
                "first"
            )
            return

        config_body = QleverConfig.print_config(config_name)

        if config_body == "":
            return

        with open("Qleverfile", mode="w", encoding="UTF-8") as f:
            f.write(config_body)

        if config_name == "Qleverfile.default":
            log.info(
                "Since this is the default Qleverfile, you need to "
                "edit it before you can continue"
            )
            log.info("")
            log.info(
                "Afterwards, run `qleverkontrol` without arguments to see "
                "which actions are available"
            )
