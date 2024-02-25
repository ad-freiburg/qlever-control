from abc import ABC, abstractmethod
from qlever import command_classes


class QleverCommand(ABC):
    """
    Abstract base class for all the commands in `qlever/commands`.
    """

    @staticmethod
    @abstractmethod
    def help_text():
        """
        Return the help text that will be shown upon `qlever <command> --help`.
        """
        pass

    @staticmethod
    @abstractmethod
    def relevant_arguments():
        """
        Retun the arguments relevant for this command. This must be a subset of
        the names of `all_arguments` defined in `QleverConfig`. Only these
        arguments can then be used in the `execute` method.
        """
        pass

    @staticmethod
    @abstractmethod
    def should_have_qleverfile():
        """
        Return `True` if the command should have a Qleverfile, `False`
        otherwise. If a command should have a Qleverfile, but none is
        specified, the command can still be executed if all the required
        arguments are specified on the command line, but there will be warning.
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
