from __future__ import annotations

import unittest
from unittest.mock import MagicMock, call, patch

from qlever.commands.log import LogCommand


class TestLogCommand(unittest.TestCase):
    @patch("subprocess.run")
    @patch("qlever.commands.log.log")
    # Test execute of index command for basic case with successful execution
    def test_execute_beginning_without_no_follow(self, mock_log, mock_run):
        # Setup args
        args = MagicMock()
        args.name = "TestName"
        args.from_beginning = True
        args.no_follow = False
        args.show = False

        # Instantiate LogCommand and execute the function
        result = LogCommand().execute(args)

        # Assertions
        log_file = f"{args.name}.server-log.txt"
        expected_log_cmd = f"tail -n +1 -f {log_file}"
        expected_log_msg = (
            f"Follow log file {log_file}, press Ctrl-C "
            f"to stop following (will not stop the server)"
        )
        # Check that the info log contains the exception message
        mock_log.info.assert_has_calls(
            [call(expected_log_msg), call("")], any_order=False
        )

        # Checking if run_command was only called once
        mock_run.assert_called_once_with(expected_log_cmd, shell=True)

        assert result

    @patch("subprocess.run")
    @patch("qlever.commands.log.log")
    # tests execute with args.no_follow = True
    def test_execute_without_beginning_with_no_follow(
        self, mock_log, mock_run
    ):
        # Setup args
        args = MagicMock()
        args.name = "TestName"
        args.from_beginning = False
        args.no_follow = True
        args.show = False
        args.tail_num_lines = 50
        # Instantiate LogCommand and execute the function
        result = LogCommand().execute(args)

        # Assertions
        log_file = f"{args.name}.server-log.txt"
        expected_log_cmd = f"tail -n {args.tail_num_lines} {log_file}"
        expected_log_msg = (
            f"Follow log file {log_file}, press Ctrl-C "
            f"to stop following (will not stop the server)"
        )
        # Check that the info log contains the exception message
        mock_log.info.assert_has_calls(
            [call(expected_log_msg), call("")], any_order=False
        )

        # Checking if run_command was only called once
        mock_run.assert_called_once_with(expected_log_cmd, shell=True)

        assert result

    @patch("qlever.commands.log.LogCommand.show")
    # test if execute returns true for args.show = true
    def test_execute_show(self, mock_show):
        # Setup args
        args = MagicMock()
        args.name = "TestName"
        args.from_beginning = True
        args.no_follow = True
        args.show = True
        # Instantiate LogCommand and execute the function
        result = LogCommand().execute(args)

        # Assertions
        log_file = f"{args.name}.server-log.txt"
        expected_log_cmd = f"tail -n +1 {log_file}"

        # Check that show is executed with correct arguments
        mock_show.assert_called_once_with(
            expected_log_cmd, only_show=args.show
        )
        assert result

    @patch("subprocess.run")
    @patch("qlever.commands.log.log")
    # test for failed subprocess.run
    def test_execute_failed_to_run_subprocess(self, mock_log, mock_run):
        # Setup args
        args = MagicMock()
        args.name = "TestName"
        args.from_beginning = False
        args.no_follow = True
        args.show = False
        args.tail_num_lines = 50

        # Assertions
        # Simulate a command execution failure
        error_msg = Exception("Failed to run subprocess.run")
        mock_run.side_effect = error_msg

        # Instantiate LogCommand and execute the function
        result = LogCommand().execute(args)

        log_file = f"{args.name}.server-log.txt"
        expected_log_cmd = f"tail -n {args.tail_num_lines} {log_file}"
        expected_log_msg = (
            f"Follow log file {log_file}, press Ctrl-C "
            f"to stop following (will not stop the server)"
        )

        # Check that the info log contains the exception message
        mock_log.info.assert_has_calls(
            [call(expected_log_msg), call("")], any_order=False
        )

        # Checking if run_command was only called once
        mock_run.assert_called_once_with(expected_log_cmd, shell=True)

        # Assertions to verify that error was logged
        mock_log.error.assert_called_once_with(error_msg)

        assert not result
