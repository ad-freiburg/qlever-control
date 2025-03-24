from __future__ import annotations

from abc import ABC, abstractmethod
from importlib import import_module
from pathlib import Path

from termcolor import colored

from qlever.log import log
from qlever.util import snake_to_camel


class CommandObjects:
    def __init__(self, script_name: str) -> None:
        self.script_name = script_name
        self._command_objects = self._fetch_command_objects()

    def _fetch_command_objects(self) -> dict[str, QleverCommand]:
        command_objects = {}
        package_path = Path(__file__).parent.parent / self.script_name
        command_names = [
            Path(p).stem
            for p in package_path.glob("commands/*.py")
            if p.name != "__init__.py"
        ]
        for command_name in command_names:
            module_path = f"{self.script_name}.commands.{command_name}"
            class_name = snake_to_camel(command_name) + "Command"
            try:
                module = import_module(module_path)
            except ImportError as e:
                raise Exception(
                    f"Could not import module {module_path} "
                    f"for {self.script_name}: {e}"
                ) from e
            # Create an object of the class and store it in the dictionary. For the
            # commands, take - instead of _.
            command_class = getattr(module, class_name)
            command_objects[command_name.replace("_", "-")] = command_class()
        return command_objects

    def __iter__(self):
        return iter(self._command_objects.items())

    def __getitem__(self, command: str) -> QleverCommand:
        return self._command_objects[command]


class QleverCommand(ABC):
    """
    Abstract base class for all the commands in `qlever/commands`.
    """

    @abstractmethod
    def __init__(self):
        """
        Initialize the command.

        IMPORTANT: This should be very LIGHTWEIGHT (typically: a few
        assignments, if any) because we create one object per command and
        initialize each of them.
        """
        pass

    @abstractmethod
    def description(self) -> str:
        """
        A concise description of the command, which will be shown when the user
        types `qlever --help` or `qlever <command> --help`.
        """
        pass

    @abstractmethod
    def should_have_qleverfile(self) -> bool:
        """
        Return `True` if the command should have a Qleverfile, `False`
        otherwise. If a command should have a Qleverfile, but none is
        specified, the command can still be executed if all the required
        arguments are specified on the command line, but there will be warning.
        """
        pass

    @abstractmethod
    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        """
        Retun the arguments relevant for this command. This must be a subset of
        the names of `all_arguments` defined in `QleverConfig`. Only these
        arguments can then be used in the `execute` method.
        """
        pass

    @abstractmethod
    def additional_arguments(self, subparser):
        """
        Add additional command-specific arguments (which are not in
        `QleverConfig.all_arguments` and cannot be specified in the Qleverfile)
        to the given `subparser`. If there are no additional arguments, just
        implement as `pass`.
        """
        pass

    @abstractmethod
    def execute(self, args) -> bool:
        """
        Execute the command with the given `args`. Return `True` if the command
        executed normally. Return `False` if it did not execute normally, but
        the problem could be identified and handled. In all other cases, raise
        a `CommandException`.
        """
        pass

    @staticmethod
    def show(command_description: str, only_show: bool = False):
        """
        Helper function that shows the command line or description of an
        action, together with an explanation.
        """

        log.info(colored(command_description, "blue"))
        log.info("")
        if only_show:
            log.info(
                'You passed the argument "--show", therefore the command '
                'is only shown, but not executed (omit the "--show" to '
                "execute it)"
            )
