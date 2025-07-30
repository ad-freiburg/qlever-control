from __future__ import annotations


def qleverfile_args(all_args: dict[str, dict[str, tuple]]) -> None:
    """Define additional jena specific Qleverfile parameters"""

    def arg(*args, **kwargs):
        return (args, kwargs)

    index_args = all_args["index"]
    server_args = all_args["server"]

    index_args["index_binary"] = arg(
        "--index-binary",
        type=str,
        default="importrdf",
        help=(
            "The binary for building the index (default: importrdf) "
            "(this requires that you have GraphDB installed "
            "on your machine)"
        ),
    )
    index_args["threads"] = arg(
        "--threads",
        type=int,
        default=2,
        help=(
            "Number of rdf parsers."
        ),
    )
    index_args["entity_index_size"] = arg(
        "--entity-index-size",
        type=int,
        default=10000000,
        help=(
            "Defines the initial size of the entity hash table index entries. "
            "The bigger the size, the fewer the collisions in the hash table, "
            "and the faster the entity retrieval. The entity hash table will "
            "adapt to the number of stored entities once the number of collisions "
            "passes a critical threshold."
        ),
    )
    index_args["jvm_args"] = arg(
        "--jvm_args",
        type=str,
        default="-Xms4g -Xmx4G",
        help=(
            "Arguments for the JVM. "
        ),
    )

    server_args["heap_size_gb"] = arg(
        "--heap_size_gb",
        type=str,
        default="4G",
        help=(
            "Sets the Java minimum and maximum heap size (-Xms and -Xmx option)."
        ),
    )
    server_args["server_binary"] = arg(
        "--server-binary",
        type=str,
        default="graphdb",
        help=(
            "The binary for starting the server (default: graphdb) "
            "(this requires that you have GraphDB installed "
            "on your machine)"
        ),
    )
    server_args["timeout"] = arg(
        "--timeout",
        type=str,
        default="30s",
        help="The maximal time in seconds a query is allowed to run",
    )
