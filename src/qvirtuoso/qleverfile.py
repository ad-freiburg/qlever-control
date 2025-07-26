from __future__ import annotations


def qleverfile_args(all_args: dict[str, dict[str, tuple]]) -> None:
    """Define additional mdb specific Qleverfile parameters"""

    def arg(*args, **kwargs):
        return (args, kwargs)

    index_args = all_args["index"]
    server_args = all_args["server"]

    index_args["index_binary"] = arg(
        "--index-binary",
        type=str,
        default="isql",
        help=(
            "The isql binary for building the index (default: isql) "
            "(this requires that you have virtuoso binaries installed "
            "on your machine)"
        ),
    )
    index_args["isql_port"] = arg(
        "--isql-port",
        type=int,
        default=1111,
        help="The port used by Virtuoso's ISQL index binary",
    )

    server_args["server_binary"] = arg(
        "--server-binary",
        type=str,
        default="virtuoso-t",
        help=(
            "The binary for starting the server (default: virtuoso-t) "
            "(this requires that you have virtuoso binaries installed "
            "on your machine)"
        ),
    )
