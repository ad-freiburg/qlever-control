from __future__ import annotations

from termcolor import colored

from qlever.command import QleverCommand
from qlever.log import log
from qlever.util import run_command


class InstallCommand(QleverCommand):
    """
    Class for executing the `install` command.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return (
            "Install the packages needed to run QLever natively"
            " (using `SYSTEM=native` in the Qleverfile)"
        )

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "--os",
            choices=["ubuntu-24.04"],
            default="ubuntu-24.04",
            help="Install for this operating system"
            " (default and currently only choice: ubuntu-24.04)",
        )

    def execute(self, args) -> bool:
        # URL of `Dockerfile` of QLever's GitHub repository.
        dockerfile_url = "https://raw.githubusercontent.com/ad-freiburg/qlever/refs/heads/master/Dockerfile"
        create_install_script_cmd = (
            f"curl -s {dockerfile_url}"
            f" | \grep RUN"
            f" | sed '1,/RUN cmake/!d'"
            f" | sed 's/^RUN //'"
            f" | sed 's/\(apt-get\)/sudo \\1/g; s/ \\(chmod\\|\\.\\/\\)/ sudo \\1/g'"
            f" | sed 's/^\\(cmake\\)/mkdir -p build \\&\\& cd build\\n\\1/'"
            f" | (cat; echo 'cmake --build . && cd ..') "
            f" > INSTALL.sh"
        )

        # Show action description.
        qlever_github_url = "https://github.com/ad-freiburg/qlever"
        self.show(
            f"Check that the current directory is a working copy"
            f" of {qlever_github_url}\n"
            f"{create_install_script_cmd}",
            args.show,
        )
        if args.show:
            return True

        # Check that the current directory is a working copy
        # of the QLever repository.
        check_working_copy_cmd = (
            "git remote show origin -n | grep h.URL | sed 's/.*://;s/.git$//'"
        )
        try:
            run_command(check_working_copy_cmd)
        except Exception:
            log.error(
                "The current directory does not appear to be a working copy"
                "of {qlever_github_url}"
            )
            return False

        # Execute the command to create the `INSTALL.sh` script.
        try:
            run_command(create_install_script_cmd)
            log.info(
                "Wrote the following to `INSTALL.sh`, either copy&paste "
                "to your shell, or run `source INSTALL.sh`"
            )
            log.info("")
            install_cmds = run_command("cat INSTALL.sh", return_output=True)
            log.info(colored(install_cmds.strip(), "blue"))
        except Exception as e:
            log.info("Error creating `INSTALL.sh`")
            log.info(e)
            log.info("")
            return False

        # That's it, the actually installing has to be done by the user
        # from the shell.
        return True
