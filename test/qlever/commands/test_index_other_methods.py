import unittest
from qlever.commands.index import IndexCommand
import argparse


class TestIndexCommand(unittest.TestCase):
    def test_description(self):
        # Create an instance of IndexCommand
        ic = IndexCommand()

        # Call the method
        result = ic.description()

        self.assertEqual(result, "Build the index for a given RDF dataset")

    def test_should_have_qleverfile(self):
        # Create an instance of IndexCommand
        ic = IndexCommand()

        # Call the method
        result = ic.should_have_qleverfile()

        assert result

    def test_relevant_qleverfile_arguments(self):
        # Create an instance of IndexCommand
        ic = IndexCommand()

        # Call the method
        result = ic.relevant_qleverfile_arguments()

        self.assertEqual(result, {"data": ["name", "format"],
               "index": ["input_files", "cat_input_files", "multi_input_json",
                          "settings_json", "index_binary",
                          "only_pso_and_pos_permutations", "use_patterns",
                          "text_index", "stxxl_memory"],
                "runtime": ["system", "image", "index_container"]})

    def test_additional_arguments(self):
        # Create an instance of IndexCommand
        ic = IndexCommand()

        # Create a parser and a subparser
        parser = argparse.ArgumentParser()
        subparser = parser.add_argument_group('test')
        # Call the method
        ic.additional_arguments(subparser)
        # Parse an empty argument list to see the default
        args = parser.parse_args([])

        # Test that the default value for cmdline_regex is set correctly
        self.assertEqual(args.overwrite_existing, False)

        # Test that the help text for cmdline_regex is correctly set
        argument_help = subparser._group_actions[-1].help
        self.assertEqual(argument_help, "Overwrite an existing index, think twice before using.")
      
