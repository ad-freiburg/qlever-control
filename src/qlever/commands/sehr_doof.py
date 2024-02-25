from qlever.command import QleverCommand


class SehrDoofCommand(QleverCommand):
    """
    Class for executing the `doof` command.
    """

    @staticmethod
    def help_text():
        return "Sehr doofes command"

    @staticmethod
    def relevant_arguments():
        return {"data": ["name"], "server": ["port"]}

    @staticmethod
    def should_have_qleverfile():
        return False

    @staticmethod
    def execute(args):
        print(f"Executing command `sehr doof` with args: {args}")
