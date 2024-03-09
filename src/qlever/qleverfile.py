from __future__ import annotations

import socket
from configparser import ConfigParser, ExtendedInterpolation

from qlever.containerize import Containerize


class QleverfileException(Exception):
    pass


class Qleverfile:
    """
    Class that defines all the possible parameters that can be specified in a
    Qleverfile + functions for parsing.
    """

    @staticmethod
    def all_arguments():
        """
        Define all possible parameters. A value of `None` means that there is
        no default value.
        """

        # Helper function that takes a list of positional arguments and a list
        # of keyword arguments and returns a tuple of both. That way, we can
        # defined arguments below with exactly the same syntax as we would for
        # `argparse.add_argument`.
        def arg(*args, **kwargs):
            return (args, kwargs)

        all_args = {}
        data_args = all_args["data"] = {}
        index_args = all_args["index"] = {}
        server_args = all_args["server"] = {}
        runtime_args = all_args["runtime"] = {}
        ui_args = all_args["ui"] = {}

        data_args["name"] = arg(
                "--name", type=str, required=True,
                help="The name of the dataset")
        data_args["get_data_cmd"] = arg(
                "--get-data-cmd", type=str, required=True,
                help="The command to get the data")
        data_args["index_description"] = arg(
                "--index-description", type=str, required=True,
                help="A concise description of the indexed dataset")
        data_args["text_description"] = arg(
                "--text-description", type=str, default=None,
                help="A description of the indexed text if any")

        index_args["input_files"] = arg(
                "--input-files", type=str, required=True,
                help="A space-separated list of patterns that match "
                     "all the files of the dataset")
        index_args["cat_input_files"] = arg(
                "--cat-input-files", type=str, required=True,
                help="The command that produces the input")
        index_args["settings_json"] = arg(
                "--settings-json", type=str, default="{}",
                help="The `.settings.json` file for the index")
        index_args["index_binary"] = arg(
                "--index-binary", type=str, default="IndexBuilderMain",
                help="The binary for building the index (this requires "
                     "that you have compiled QLever on your machine)")
        index_args["only_pso_and_pos_permutations"] = arg(
                "--only-pso-and-pos-permutations", action="store_true",
                default=False,
                help="Only create the PSO and POS permutations")
        index_args["use_patterns"] = arg(
                "--use-patterns", action="store_true", default=True,
                help="Precompute so-called patterns needed for fast processing"
                     " of queries like SELECT ?p (COUNT(DISTINCT ?s) AS ?c) "
                     "WHERE { ?s ?p [] ... } GROUP BY ?p")
        index_args["with_text_index"] = arg(
                "--with-text-index",
                choices=["none", "from_text_records", "from_literals",
                         "from_text_records_and_literals"],
                default="none",
                help="Whether to also build an index for text search"
                     "and for which texts")
        index_args["stxxl_memory"] = arg(
                "--stxxl-memory", type=str, default="5G",
                help="The amount of memory to use for the index build "
                     "(the name of the option has historical reasons)")

        server_args["server_binary"] = arg(
                "--server-binary", type=str, default="ServerMain",
                help="The binary for starting the server (this requires "
                     "that you have compiled QLever on your machine)")
        server_args["host_name"] = arg(
                "--host-name", type=str, default=f"{socket.getfqdn()}",
                help="The name of the host on which the server listens for "
                     "requests")
        server_args["port"] = arg(
                "--port", type=int, required=True,
                help="The port on which the server listens for requests")
        server_args["access_token"] = arg(
                "--access-token", type=str, default=None,
                help="The access token for privileged operations")
        server_args["memory_for_queries"] = arg(
                "--memory-for-queries", type=str, default="5G",
                help="The maximal amount of memory used for query processing"
                     " (if a query needs more than what is available, the "
                     "query will not be processed)")
        server_args["cache_max_size"] = arg(
                "--cache-max-size", type=str, default="2G",
                help="The maximal amount of memory used for caching")
        server_args["cache_max_size_single_entry"] = arg(
                "--cache-max-size-single-entry", type=str, default="1G",
                help="The maximal amount of memory used for caching a single "
                     "query result")
        server_args["cache_max_num_entries"] = arg(
                "--cache-max-num-entries", type=int, default=200,
                help="The maximal number of entries in the cache"
                     " (the eviction policy when the cache is full is LRU)")
        server_args["timeout"] = arg(
                "--timeout", type=str, default="30s",
                help="The maximal time in seconds a query is allowed to run"
                     " (can be increased per query with the URL parameters "
                     "`timeout` and `access_token`)")
        server_args["num_threads"] = arg(
                "--num-threads", type=int, default=8,
                help="The number of threads used for query processing")
        server_args["only_pso_and_pos_permutations"] = arg(
                "--only-pso-and-pos-permutations", action="store_true",
                default=False,
                help="Only use the PSO and POS permutations (then each "
                     "triple pattern must have a fixed predicate)")
        server_args["use_patterns"] = arg(
                "--use-patterns", action="store_true", default=True,
                help="Use the patterns precomputed during the index build"
                     " (see `qlever index --help` for their utility)")
        server_args["with_text_index"] = arg(
                "--with-text-index", action="store_true", default=False,
                help="Whether to the text index if one was precomputed"
                     " (see `qlever index --help` for details)")

        runtime_args["system"] = arg(
                "--system", type=str,
                choices=Containerize.supported_systems() + ["native"],
                default="docker",
                help=("Whether to run commands like `index` or `start` "
                      "natively or in a container, and if in a container, "
                      "which system to use"))
        runtime_args["image"] = arg(
                "--image", type=str,
                default="docker.io/adfreiburg/qlever",
                help="The name of the image when running in a container")
        runtime_args["index_container"] = arg(
                "--index-container", type=str,
                help="The name of the container used by `qlever index`")
        runtime_args["server_container"] = arg(
                "--server-container", type=str,
                help="The name of the container used by `qlever start`")

        ui_args["ui_port"] = arg(
                "--ui_port", type=int, default=7000,
                help="The port of the Qlever UI when running `qlever ui`")
        ui_args["ui_config"] = arg(
                "--ui-config", type=str, default="default",
                help="The name of the backend configuration for the QLever UI"
                     " (this determines AC queries and example queries)")
        ui_args["ui_system"] = arg(
                "--ui-system", type=str,
                choices=Containerize.supported_systems(),
                default="docker",
                help="Which container system to use for `qlever ui`"
                     " (unlike for `qlever index` and `qlever start`, "
                     " \"native\" is not yet supported here)")
        ui_args["ui_image"] = arg(
                "--ui-image", type=str,
                default="docker.io/adfreiburg/qlever-ui",
                help="The name of the image used for `qlever ui`")
        ui_args["ui_container"] = arg(
                "--ui-container", type=str,
                help="The name of the container used for `qlever ui`")

        return all_args

    @staticmethod
    def read(qleverfile_path):
        """
        Read the given Qleverfile (the function assumes that it exists) and
        return a `ConfigParser` object with all the options and their values.

        NOTE: The keys have the same hierarchical structure as the keys in
        `all_arguments()`. The Qleverfile may contain options that are not
        defined in `all_arguments()`. They can be used as temporary variables
        to define other options, but cannot be accessed by the commands later.
        """

        # Read the Qleverfile.
        config = ConfigParser(interpolation=ExtendedInterpolation())
        try:
            config.read(qleverfile_path)
        except Exception as e:
            raise QleverfileException(f"Error parsing {qleverfile_path}: {e}")

        # Make sure that all the sections are there.
        for section in ["data", "index", "server", "runtime", "ui"]:
            if section not in config:
                config[section] = {}

        # Add "inherited" values. For example, if `name` is defined, but
        # `server_container_name` is not, then set `server_container_name`
        # to `qlever.server.<name>`.
        if "name" in config["data"]:
            name = config["data"]["name"]
            runtime = config["runtime"]
            if "server_container" not in runtime:
                runtime["server_container"] = f"qlever.server.{name}"
            if "index_container" not in runtime:
                runtime["index_container"] = f"qlever.index.{name}"
            if "ui_container" not in config["ui"]:
                config["ui"]["ui_container"] = f"qlever.ui.{name}"

        # Return the parsed Qleverfile with the added inherited values.
        return config
