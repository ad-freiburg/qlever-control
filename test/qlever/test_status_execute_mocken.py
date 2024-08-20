import unittest
from unittest.mock import patch, MagicMock
import psutil
from qlever.commands.status import StatusCommand
from io import StringIO
import sys
from datetime import datetime


class TestStatusCommand(unittest.TestCase):
    @patch('qlever.commands.status.show_process_info')
    @patch('psutil.process_iter')
    def test_execute_processes_found(self, mock_process_iter, mock_show_process_info):
        # Mocking the input for the execute function
        args = MagicMock()
        args.cmdline_regex = "^(ServerMain|IndexBuilderMain)"
        args.show = False

        # Creating mock psutil.Process objects with necessary attributes
        mock_process1 = MagicMock()
        mock_process1.as_dict.return_value = {
            'cmdline': ['cmdline1'],
            'pid': 1,
            'username': 'user1',
            'create_time': datetime.now().timestamp(),
            'memory_info': MagicMock(rss=512 * 1024 * 1024)  # 512 MB
        }

        mock_process2 = MagicMock()
        mock_process2.as_dict.return_value = {
            'cmdline': ['cmdline2'],
            'pid': 2,
            'username': 'user2',
            'create_time': datetime.now().timestamp(),
            'memory_info': MagicMock(rss=1024 * 1024 * 1024)  # 1 GB
        }

        # Mock the return value of process_iter to be a list of these mocked process objects
        mock_process_iter.return_value = [mock_process1, mock_process2]

        # Simulate show_process_info returning False for the first and True for the second process
        mock_show_process_info.side_effect = [False, True]

        sc = StatusCommand()

        # Execute the function
        result = sc.execute(args)

        # Debugging: Print the actual calls to show_process_info
        print(f"Actual show_process_info calls: {mock_show_process_info.call_args_list}")

        # Assert that process_iter was called once
        mock_process_iter.assert_called_once()

        # Assert that show_process_info was called with the correct arguments
        mock_show_process_info.assert_any_call(mock_process1, args.cmdline_regex, show_heading=True)
        mock_show_process_info.assert_any_call(mock_process2, args.cmdline_regex, show_heading=True)

        self.assertIsNone(result)

    @patch('qlever.util.show_process_info')
    @patch('psutil.process_iter')
    def test_execute_no_processes_found(self, mock_process_iter, mock_show_process_info):
        # Mocking the input for the execute function
        args = MagicMock()
        args.cmdline_regex = "^(ServerMain|IndexBuilderMain)"
        args.show = False

        # Mock process_iter to return an empty list, simulating that no matching processes are found
        mock_process_iter.return_value = []

        # Capture the string-output
        captured_output = StringIO()
        sys.stdout = captured_output

        # Instantiate the StatusCommand
        status_command = StatusCommand()

        # Execute the function
        result = status_command.execute(args)

        # Reset redirect
        sys.stdout = sys.__stdout__

        # Assert that process_iter was called once
        mock_process_iter.assert_called_once()

        # Assert that show_process_info was never called since there are no processes
        mock_show_process_info.assert_not_called()

        self.assertFalse(result)

        # Verify the correct output was printed
        self.assertIn("No processes found", captured_output.getvalue())
