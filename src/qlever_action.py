import os
import glob

from abc import ABC, abstractmethod
from src.qlever_config import QleverConfig



class QleverAction(ABC):
    config: QleverConfig
    name: str
    yes_values: list = ["1", "true", "yes"]

    @abstractmethod
    def index(self):
        pass

    @abstractmethod
    def start(self):
        """
        Action that starts the QLever server according to the settings in the
        [server] section of the Qleverfile. If a server is already running, the
        action reports that fact and does nothing.
        """
        pass

    @abstractmethod
    def get_data(self):
        pass

    def get_total_file_size(self, paths):
        """
        Helper function that gets the total size of all files in the given
        paths in GB.
        """

        total_size = 0
        for path in paths:
            for file in glob.glob(path):
                total_size += os.path.getsize(file)
        return total_size / 1e9

    def _gen_cmdline_index(self):
        """
        Action that builds a QLever index according to the settings in the
        [index] section of the Qleverfile.
        """

        # Construct the command line based on the config file.
        index_config = self.config["index"]
        cmdline = (
            f"{index_config['cat_files']} | {index_config['binary']}"
            f" -F ttl -f -"
            f" -i {self.name}"
            f" -s {self.name}.settings.json"
        )
        if index_config["only_pso_and_pos_permutations"] in self.yes_values:
            cmdline += " --only-pso-and-pos-permutations --no-patterns"
        if index_config["with_text_index"] in [
            "from_text_records",
            "from_text_records_and_literals",
        ]:
            cmdline += f" -w {self.name}.wordsfile.tsv" f" -d {self.name}.docsfile.tsv"
        if index_config["with_text_index"] in [
            "from_literals",
            "from_text_records_and_literals",
        ]:
            cmdline += " --text-words-from-literals"
        if "stxxl_memory_gb" in index_config:
            cmdline += f" --stxxl-memory-gb {index_config['stxxl_memory_gb']}"
        cmdline += f" | tee {self.name}.index-log.txt"

        # If the total file size is larger than 10 GB, set ulimit (such that a
        # large number of open files is allowed).
        total_file_size = self.get_total_file_size(
            self.config["index"]["file_names"].split()
        )
        if total_file_size > 10:
            cmdline = f"ulimit -Sn 1048576; {cmdline}"

    def _gen_cmdline_start(self):
        server_config = self.config["server"]
        cmdline = (
            f"{self.config['server']['binary']}"
            f" -i {self.name}"
            f" -j {server_config['num_threads']}"
            f" -p {server_config['port']}"
            f" -m {server_config['memory_for_queries_gb']}"
            f" -c {server_config['cache_max_size_gb']}"
            f" -e {server_config['cache_max_size_gb_single_entry']}"
            f" -k {server_config['cache_max_num_entries']}"
        )
        if server_config["access_token"]:
            cmdline += f" -a {server_config['access_token']}"
        if server_config["only_pso_and_pos_permutations"] in self.yes_values:
            cmdline += " --only-pso-and-pos-permutations"
        if server_config["no_patterns"] in self.yes_values:
            cmdline += " --no-patterns"
        if self.config["index"]["with_text_index"] in [
            "from_text_records",
            "from_literals",
            "from_text_records_and_literals",
        ]:
            cmdline += " -t"
        cmdline += f" > {self.name}.server-log.txt 2>&1"


class DockerAction(QleverAction):
    def __init__(self, qc: QleverConfig) -> None:
        self.config = qc.config
        self.name = self.config["data"]["name"]


class NativeAction(QleverAction):
    pass
