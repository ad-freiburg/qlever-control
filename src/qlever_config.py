# import importlib.resources
# import pkgutil
import Qleverfiles
from pathlib import Path
# from zipfile import ZipFile


# ref: https://stackoverflow.com/a/58941536
# data = importlib.resources.read_text("Qleverfiles", "Qleverfile.olympics")
# data = pkgutil.get_data("Qleverfiles", "Qleverfile.olympics").decode()


def list_config_names() -> list[str]:
    """
    ls all the bundled configuration files (Qleverfiles)

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


def print_config(config_name: str) -> str:
    """
    dumps contents of a bundled config file
    """
    return Path(Qleverfiles.__path__[0], config_name).read_text(encoding="UTF-8")
