from abc import ABC, abstractmethod
from qlever import command_classes


class QleverCommand(ABC):
    """
    Abstract base class for all the commands in `qlever/commands`.
    """

    @staticmethod
    @abstractmethod
    def add_subparser(subparsers):
        """
        Add a subparser for the command to the given `subparsers` object.
        """
        pass

    @staticmethod
    @abstractmethod
    def arguments():
        """
        Retun the arguments relevant for this command. This must be a subset of
        the arguments defined in the `QleverConfig` object.
        """
        pass

    @staticmethod
    @abstractmethod
    def execute(args):
        """
        Execute the command with the given `args`.
        """
        pass


def execute_command(command_name, args):
    """
    Execute the command using the appropriate command class (dynamically loaded
    in `__init__.py`).
    """

    command_class = command_classes[command_name]
    command_class.execute(args)
