from qlever.command import QleverCommand


class IndexCommand(QleverCommand):
    """
    Class for executing the `index` command.
    """

    @staticmethod
    def add_subparser(subparsers):
        subparsers.add_parser(
                "index",
                help="Building an index")

    @staticmethod
    def arguments():
        return {"index": ["cat_files", "settings_json"]}

    @staticmethod
    def execute(args):
        print(f"Executing command `doof` with args: {args}")
