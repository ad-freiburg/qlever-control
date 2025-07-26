from __future__ import annotations


def qleverfile_args(all_args: dict[str, dict[str, tuple]]) -> None:
    """Define additional blazegraph specific Qleverfile parameters"""

    def arg(*args, **kwargs):
        return (args, kwargs)

    index_args = all_args["index"]
    server_args = all_args["server"]

    index_args["jvm_args"] = arg(
        "--jvm_args",
        type=str,
        default="-Xmx4G",
        help=(
            "Arguments for the JVM. "
            "Do not set to all available RAM. "
            "Increasing is only necessary for large numbers of long literals."
        ),
    )

    server_args["jvm_args"] = arg(
        "--jvm_args",
        type=str,
        default="-Xmx4G",
        help=(
            "Arguments for the JVM."
        ),
    )
    # server_args["timeout"] = arg(
    #     "--timeout",
    #     type=str,
    #     default="30s",
    #     help="The maximal time in seconds a query is allowed to run",
    # )

