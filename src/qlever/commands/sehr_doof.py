from qlever.command import QleverCommand


class SehrDoofCommand(QleverCommand):
    """
    Class for executing the `doof` command.
    """

    @staticmethod
    def add_subparser(subparsers):
        subparsers.add_parser(
                "sehr_doof",
                help="Sehr doofes command")

    @staticmethod
    def arguments():
        return {"data": ["name"], "server": ["port"]}

    @staticmethod
    def execute(args):
        print(f"Executing command `sehr doof` with args: {args}")
