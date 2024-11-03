from __future__ import annotations
import unittest
from unittest.mock import patch, MagicMock, call
from qlever.commands.index import IndexCommand
import shlex


# Test execute of index command for basic case with successful execution
class TestIndexCommand(unittest.TestCase):
    @patch('qlever.commands.index.run_command')
    @patch('qlever.commands.index.Containerize')
    @patch('qlever.commands.index.get_existing_index_files')
    @patch('qlever.commands.index.get_total_file_size')
    @patch('qlever.commands.index.glob')
    def test_execute_successful_indexing_without_extras(self, mock_glob,
                    mock_get_total_file_size, mock_get_existing_index_files,
                                         mock_containerize, mock_run_command):
        # Setup args
        args = MagicMock()
        args.name = "TestName"
        args.format = "turtle"
        args.cat_input_files = "cat input.nt"
        args.index_binary = "/test/path/index-binary"
        args.settings_json = '{"example": "settings"}'
        args.input_files = "*.nt"
        args.only_pso_and_pos_permutations = False
        args.use_patterns = True
        args.text_index = "Test Index"
        args.stxxl_memory = None
        args.system = "native"
        args.show = False
        args.overwrite_existing = False
        args.index_container = "test_container"
        args.image = "test_image"
        args.multi_input_json = False

        # Mock glob, get_total_file_size, get_existing_index_files,
        # run_command and containerize
        mock_glob.glob.return_value = ["input1.nt", "input2.nt"]
        mock_get_total_file_size.return_value = 5e9  # 5 GB
        mock_get_existing_index_files.return_value = []
        mock_run_command.return_value = None
        mock_containerize.supported_systems.return_value = ["docker"]


        # Instantiate and executing the IndexCommand
        result = IndexCommand().execute(args)

        # Assertions
        expected_index_cmd = (f"{args.cat_input_files} | {args.index_binary}"
                         f" -i {args.name} -s {args.name}.settings.json"
                         f" -F {args.format} -f - | tee"
                         f" {args.name}.index-log.txt")
        index_cmd_call = call(expected_index_cmd, show_output=True)

        expected_settings_json_cmd = (f"echo {shlex.quote(args.settings_json)} "
                             f"> {args.name}.settings.json")

        expected_index_binary_cmd = f"{args.index_binary} --help"

        # Testing if run_command was called exactly 3 times with the correct
        # parameters and in the correct order
        mock_run_command.assert_has_calls([call(expected_index_binary_cmd),
                                call(expected_settings_json_cmd), 
                                index_cmd_call], any_order=False)
        assert result


    @patch('qlever.commands.index.run_command')
    @patch('qlever.commands.index.Containerize')
    @patch('qlever.commands.index.get_existing_index_files')
    @patch('qlever.commands.index.get_total_file_size')
    @patch('qlever.commands.index.log')
    @patch('qlever.commands.index.glob')
    def test_execute_indexing_with_already_existing_files(self, mock_glob,
         mock_log, mock_get_total_file_size, mock_get_existing_index_files,
         mock_containerize, mock_run_command):
        # Setup args
        args = MagicMock()
        args.name = "TestName"
        args.format = "turtle"
        args.cat_input_files = "cat input.nt"
        args.index_binary = "/test/path/index-binary"
        args.settings_json = '{"example": "settings"}'
        args.input_files = "*.nt"
        args.only_pso_and_pos_permutations = False
        args.use_patterns = True
        args.text_index = None
        args.stxxl_memory = None
        args.system = "native"
        args.show = False
        args.overwrite_existing = False
        args.index_container = "test_container"
        args.image = "test_image"
        args.multi_input_json = False

        # Mock glob, get_total_file_size, get_existing_index_files,
        # run_command and containerize
        mock_glob.glob.return_value = ["input1.nt", "input2.nt"]
        mock_get_total_file_size.return_value = 5e9  # 5 GB
        mock_get_existing_index_files.return_value = ["TestName.index"]
        mock_run_command.return_value = None
        mock_containerize.supported_systems.return_value = []

        # Instantiate the IndexCommand
        ic = IndexCommand()

        # Execute the function
        result = ic.execute(args)

        # Assertions
        assert not result
        # Verify that the error message was logged
        mock_log.error.assert_called_once_with(
            f"Index files for basename \"{args.name}\" found, if you "
                    f"want to overwrite them, use --overwrite-existing")
        # Check that the info log contains the exception message
        mock_log.info.assert_any_call(
            f"Index files found: {mock_get_existing_index_files.return_value}")
        # Checking if run_command was only called once
        # (not after detecting existing files)
        mock_run_command.assert_called_once_with(f"{args.index_binary} --help")


    @patch('qlever.commands.index.run_command')
    @patch('qlever.commands.index.Containerize')
    @patch('qlever.commands.index.get_existing_index_files')
    @patch('qlever.commands.index.get_total_file_size')
    @patch('qlever.commands.index.log')
    @patch('qlever.commands.index.glob')
    def test_execute_fails_if_no_indexing_binary_is_found(self, mock_glob,
                            mock_log, mock_get_total_file_size,
                            mock_get_existing_index_files, mock_containerize,
                            mock_run_command):
        # Setup args
        args = MagicMock()
        args.name = "TestName"
        args.format = "turtle"
        args.cat_input_files = "cat input.nt"
        args.index_binary = "/test/path/no-binary-found"
        args.settings_json = '{"example": "settings"}'
        args.input_files = "*.nt"
        args.only_pso_and_pos_permutations = False
        args.use_patterns = True
        args.text_index = None
        args.stxxl_memory = None
        args.system = "native"
        args.show = False
        args.overwrite_existing = False
        args.index_container = "test_container"
        args.image = "test_image"
        args.multi_input_json = False

        # Mock glob, get_total_file_size, get_existing_index_files,
        # run_command and containerize
        # if run_command is called throw an Exception with "Binary not found"
        mock_glob.glob.return_value = ["input1.nt", "input2.nt"]
        mock_get_total_file_size.return_value = 5e9  # 5 GB
        mock_get_existing_index_files.return_value = []
        mock_run_command.side_effect = Exception("Binary not found")
        mock_containerize.supported_systems.return_value = []

        # Instantiate the IndexCommand
        ic = IndexCommand()

        # Execute the function
        result = ic.execute(args)

        # Assertions
        self.assertFalse(result)
        # Verify that the error message was logged
        mock_log.error.assert_called_once_with(
            f"Running \"{args.index_binary}\" failed, "
                          f"set `--index-binary` to a different binary or "
                          f"set `--system to a container system`")
        # Check that the info log contains the exception message
        mock_log.info.assert_any_call(
            "The error message was: Binary not found")
        # Checking if run_command was only called once
        # (not after throwing an Exception)
        mock_run_command.assert_called_once_with(f"{args.index_binary} --help")


    @patch('qlever.commands.index.run_command')
    @patch('qlever.commands.index.Containerize')
    @patch('qlever.commands.index.get_existing_index_files')
    @patch('qlever.commands.index.get_total_file_size')
    @patch('qlever.commands.index.glob')
    def test_execute_total_file_size_greater_than_ten_gb(self, mock_glob,
                                                    mock_get_total_file_size,
         mock_get_existing_index_files, mock_containerize, mock_run_command):
        # Setup args
        args = MagicMock()
        args.name = "TestName"
        args.format = "turtle"
        args.cat_input_files = "cat input.nt"
        args.index_binary = "/test/path/index-binary"
        args.settings_json = '{"example": "settings"}'
        args.input_files = "*.nt"
        args.only_pso_and_pos_permutations = False
        args.use_patterns = True
        args.text_index = None
        args.stxxl_memory = None
        args.system = "native"
        args.show = False
        args.overwrite_existing = False
        args.index_container = "test_container"
        args.image = "test_image"
        args.multi_input_json = False

        # Mock glob, get_total_file_size, get_existing_index_files,
        # run_command and containerize
        mock_glob.glob.return_value = ["input1.nt", "input2.nt"]
        mock_get_total_file_size.return_value = 15e9  # 15 GB
        mock_get_existing_index_files.return_value = []
        mock_run_command.return_value = None
        mock_containerize.supported_systems.return_value = []

        # Instantiate the IndexCommand
        ic = IndexCommand()

        # Execute the function
        result = ic.execute(args)

        # Assertions
        expected_index_cmd = (
            f"ulimit -Sn 1048576; {args.cat_input_files} | {args.index_binary}"
                         f" -i {args.name} -s {args.name}.settings.json"
                         f" -F {args.format} -f -"
            f" | tee {args.name}.index-log.txt"
        )
        mock_run_command.assert_any_call(expected_index_cmd, show_output=True)
        self.assertTrue(result)
