import unittest
from unittest.mock import patch, MagicMock
import psutil
from qlever.command import StatusCommand
from qlever.util import show_process_info
from io import StringIO
import sys


class TestStatusCommand(unittest.TestCase):
    # Test the execute function while mocking psutil.process_iter and show_process_info
    @patch('qlever.util.show_process_info')
    @patch('psutil.process_iter')
    def test_execute(self, mock_process_iter, mock_show_process_info):
        args = MagicMock()
        args.cmdline_regex = "^(ServerMain|IndexBuilderMain)"
        args.show = False
        # replaces return of psutil.process_iter with simplified objects.
        # For other testing use more realistic objects: {'name': 'systemd', 'pid': 1, 'username': 'root'}
        mock_process_iter.return_value = ['process1.anders', 'process2.anders', 'process3.anders', 'example2.qlever']
        mock_show_process_info.side_effect = [False, False, False, True]
        sc = StatusCommand
        # execute the execute function and saving the result
        result = sc.execute(args)
        # Assert
        mock_process_iter.assert_called_once()
        mock_show_process_info.assert_called_once_with(mock_process_iter, args.cmdline_regex, show_heading=True)
        assert result

    def test_execute_no_processes_found(self, mock_process_iter, mock_show_process_info):
        # Arrange
        args = MagicMock()
        args.cmdline_regex = "^(ServerMain|IndexBuilderMain)"
        args.show = False

        # Mock process_iter to return an empty list, simulating no matching processes
        mock_process_iter.return_value = []

        # Redirect stdout to capture print output
        captured_output = StringIO()
        sys.stdout = captured_output

        # Instantiate the StatusCommand
        status_command = StatusCommand()

        # Act
        result = status_command.execute(args)

        # Reset redirect.
        sys.stdout = sys.__stdout__

        # Assert
        mock_process_iter.assert_called_once()
        mock_show_process_info.assert_not_called()
        self.assertFalse(result)

        # Verify the correct output was printed
        self.assertIn("No processes found", captured_output.getvalue())


if __name__ == '__main__':
    unittest.main()