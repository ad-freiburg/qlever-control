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
        default="oxigraph",
        help=(
            "The binary for building the index (default: oxigraph) "
            "(this requires that you have oxigraph-cli installed "
            "on your machine)"
        ),
    )
    index_args["lenient"] = arg(
        "--lenient",
        action="store_true",
        default=False,
        help=("Attempt to keep loading even if the data file is invalid"),
    )

    server_args["server_binary"] = arg(
        "--server-binary",
        type=str,
        default="oxigraph",
        help=(
            "The binary for starting the server (default: oxigraph) "
            "(this requires that you have oxigraph-cli installed "
            "on your machine)"
        ),
    )
