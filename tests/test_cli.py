"""
Unit tests for command-line interface in get_sensing_data.py
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import argparse
import pandas as pd

# Add parent directory to path to import get_sensing_data.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import get_sensing_data

class TestCommandLineInterface(unittest.TestCase):
    """Test command-line argument parsing and main function"""
    
    @patch('get_sensing_data.argparse.ArgumentParser.parse_args')
    def test_arg_parser_options(self, mock_parse_args):
        """Test if all expected arguments are defined"""
        # Set up mock return value
        mock_args = MagicMock()
        mock_args.project = 'test-project'
        mock_args.list_projects = False
        mock_args.setup_credentials = False
        mock_args.start_date = '2023-01-01'
        mock_args.end_date = '2023-01-31'
        mock_args.node_id = None
        mock_args.output_dir = None
        mock_args.output = 'csv'
        mock_args.verbose = False
        mock_args.retry_count = 3
        mock_args.zip = False
        mock_parse_args.return_value = mock_args
        
        # Call main() which will use our mocked parse_args
        with patch('get_sensing_data.load_credentials_from_env'), \
             patch('get_sensing_data.create_engine_from_credentials'), \
             patch('get_sensing_data.get_raw_data'), \
             patch('get_sensing_data.ensure_data_directory'), \
             patch('get_sensing_data.save_data'), \
             patch('get_sensing_data.logger'):
            get_sensing_data.main()
        
        # Verify args were parsed
        mock_parse_args.assert_called_once()
    
    @patch('get_sensing_data.setup_credentials')
    @patch('get_sensing_data.argparse.ArgumentParser.parse_args')
    def test_setup_credentials_option(self, mock_parse_args, mock_setup_creds):
        """Test --setup-credentials option"""
        # Set up mock return value
        mock_args = MagicMock()
        mock_args.setup_credentials = True
        mock_parse_args.return_value = mock_args
        
        # Call main()
        with patch('get_sensing_data.logger'):
            result = get_sensing_data.main()
        
        # Verify setup_credentials was called and main returned 0
        mock_setup_creds.assert_called_once()
        self.assertEqual(result, 0)
    
    @patch('get_sensing_data.list_available_projects')
    @patch('get_sensing_data.load_credentials_from_env')
    @patch('get_sensing_data.create_engine_from_credentials')
    @patch('get_sensing_data.argparse.ArgumentParser.parse_args')
    def test_list_projects_option(self, mock_parse_args, mock_create_engine, 
                                 mock_load_creds, mock_list_projects):
        """Test --list-projects option"""
        # Set up mock return values
        mock_args = MagicMock()
        mock_args.setup_credentials = False
        mock_args.list_projects = True
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        mock_list_projects.return_value = [
            ('project1', 5),
            ('project2', 10)
        ]
        
        # Call main()
        with patch('get_sensing_data.logger'):
            result = get_sensing_data.main()
        
        # Verify list_projects was called and main returned 0
        mock_list_projects.assert_called_once_with(mock_engine)
        self.assertEqual(result, 0)
    
    @patch('get_sensing_data.argparse.ArgumentParser.parse_args')
    def test_missing_project_parameter(self, mock_parse_args):
        """Test error when --project is not specified"""
        # Set up mock return value with missing project
        mock_args = MagicMock()
        mock_args.setup_credentials = False
        mock_args.list_projects = False
        mock_args.project = None
        mock_parse_args.return_value = mock_args
        
        # Call main()
        with patch('get_sensing_data.logger'):
            result = get_sensing_data.main()
        
        # Verify main returned error code 1
        self.assertEqual(result, 1)
    
    @patch('get_sensing_data.get_raw_data')
    @patch('get_sensing_data.load_credentials_from_env')
    @patch('get_sensing_data.create_engine_from_credentials')
    @patch('get_sensing_data.ensure_data_directory')
    @patch('get_sensing_data.argparse.ArgumentParser.parse_args')
    def test_node_id_parsing(self, mock_parse_args, mock_ensure_dir, 
                            mock_create_engine, mock_load_creds, mock_get_data):
        """Test parsing of --node-id parameter"""
        # Set up mock return values
        mock_args = MagicMock()
        mock_args.setup_credentials = False
        mock_args.list_projects = False
        mock_args.project = 'test-project'
        mock_args.node_id = 'node1,node2,node3'
        mock_args.start_date = '2023-01-01'
        mock_args.end_date = '2023-01-31'
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        mock_get_data.return_value = pd.DataFrame()  # Empty dataframe to trigger the "no data" path
        
        # Call main()
        with patch('get_sensing_data.logger'):
            result = get_sensing_data.main()
        
        # Verify get_raw_data was called with correct node_ids
        mock_get_data.assert_called_once()
        call_args = mock_get_data.call_args[1]
        self.assertEqual(call_args['node_ids'], ['node1', 'node2', 'node3'])

if __name__ == '__main__':
    unittest.main()