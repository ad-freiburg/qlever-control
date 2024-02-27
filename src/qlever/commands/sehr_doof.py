from __future__ import annotations

from qlever.command import QleverCommand


class SehrDoofCommand(QleverCommand):
    """
    Class for executing the `doof` command.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return "Das ist einfach nur doof"

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str: list[str]]:
        return {"data": ["name"], "server": ["port"]}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument("--doofheit", type=str,
                               choices=["doof", "sehr doof", "saudoof"],
                               default="doof",
                               help="How doof the command should be.")

    def execute(self, args) -> bool:
        self.show(f"Executing command `doof` with args: {args}")
        log.error("This command will never be implemented ... doof")
