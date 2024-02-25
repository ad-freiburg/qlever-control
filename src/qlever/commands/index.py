from qlever.command import QleverCommand


class IndexCommand(QleverCommand):
    """
    Class for executing the `index` command.
    """

    @staticmethod
    def help_text():
        return "Building an index"

    @staticmethod
    def relevant_arguments():
        return {"index": ["cat_files", "settings_json"]}

    @staticmethod
    def should_have_qleverfile():
        return True

    @staticmethod
    def execute(args):
        print(f"Executing command `doof` with args: {args}")
