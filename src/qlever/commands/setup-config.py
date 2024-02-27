import subprocess
from pathlib import Path

from qlever.command import QleverCommand
from qlever.log import log


class SetupConfigCommand(QleverCommand):
    """
    Class for executing the `setup-config` command.
    """

    def __init__(self):
        self.qleverfiles_path = Path(__file__).parent.parent / "Qleverfiles"
        self.qleverfile_names = \
            [p.name.split(".")[1]
             for p in self.qleverfiles_path.glob("Qleverfile.*")]

    def description(self) -> str:
        return "Create a pre-configured Qleverfile"

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str: list[str]]:
        return {}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
                "config_name", type=str,
                choices=self.qleverfile_names,
                help="The name of the pre-configured Qleverfile to create")

    def execute(self, args) -> bool:
        # Construct the command line and show it.
        qleverfile_path = (self.qleverfiles_path
                           / f"Qleverfile.{args.config_name}")
        setup_config_cmd = f"cp -a {qleverfile_path} Qleverfile"
        self.show(setup_config_cmd, only_show=args.show)
        if args.show:
            return False

        # If there is already a Qleverfile in the current directory, exit.
        qleverfile_path = Path("Qleverfile")
        if qleverfile_path.exists():
            log.error("`Qleverfile` already exists in current directory")
            log.info("")
            log.info("If you want to create a new Qleverfile using "
                     "`qlever setup-config`, delete the existing Qleverfile "
                     "first")
            return False

        # Copy the Qleverfile to the current directory.
        try:
            subprocess.run(setup_config_cmd, shell=True, check=True,
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except Exception as e:
            log.error(f"Could not copy \"{qleverfile_path}\""
                      f" to current directory: {e}")
            return False

        # If we get here, everything went well.
        log.info(f"Created Qleverfile for config \"{args.config_name}\""
                 f" in current directory")
        return True

        # if config_name == "default":
        #     log.info("Since this is the default Qleverfile, you need to "
        #              "edit it before you can continue")
        #     log.info("")
        #     log.info("Afterwards, run `qlever` without arguments to see "
        #              "which actions are available")
        # else:
        #     show_available_action_names()
        # log.info("")
