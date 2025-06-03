"""
Unit tests for credential handling in get_sensing_data.py
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil

# Add parent directory to path to import get_sensing_data.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import get_sensing_data

class TestCredentials(unittest.TestCase):
    """Test credential loading and setup functionality"""
    
    def setUp(self):
        """Set up temporary directory for test files"""
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
    def tearDown(self):
        """Clean up after tests"""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)
    
    @patch('builtins.input', return_value='y')
    @patch('get_sensing_data.logger')
    def test_setup_credentials(self, mock_logger, mock_input):
        """Test creating credentials template"""
        # Run the setup function
        get_sensing_data.setup_credentials()
        
        # Check if .env file was created
        self.assertTrue(os.path.exists('.env'))
        
        # Check file contents
        with open('.env', 'r') as f:
            content = f.read()
            self.assertIn('DB_HOST=sensing-0.msi.umn.edu', content)
            self.assertIn('DB_USER=your_username', content)
            self.assertIn('DB_PASSWORD=your_password', content)
        
        # Check if logger was called with instructions
        mock_logger.info.assert_any_call("\nINSTRUCTIONS:")
        mock_logger.info.assert_any_call("3. Save the file and exit the editor")
        
        # Test overwrite prompt for existing file
        mock_input.return_value = 'n'
        get_sensing_data.setup_credentials()
        mock_logger.info.assert_any_call("Keeping existing .env file.")
    
    @patch('os.getenv')
    @patch('get_sensing_data.load_dotenv')
    @patch('os.path.exists', return_value=True)
    def test_load_credentials_success(self, mock_exists, mock_load_dotenv, mock_getenv):
        """Test successful loading of credentials"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key: {
            'DB_HOST': 'test-host',
            'DB_PORT': '5432',
            'DB_NAME': 'test-db',
            'DB_USER': 'test-user',
            'DB_PASSWORD': 'test-pass'
        }.get(key)
        
        # Call the function
        creds = get_sensing_data.load_credentials_from_env()
        
        # Check credentials
        self.assertEqual(creds['host'], 'test-host')
        self.assertEqual(creds['port'], '5432')
        self.assertEqual(creds['db'], 'test-db')
        self.assertEqual(creds['user'], 'test-user')
        self.assertEqual(creds['pass'], 'test-pass')
        
        # Check dotenv was loaded
        mock_load_dotenv.assert_called_once()
    
    @patch('os.path.exists', return_value=False)
    def test_load_credentials_missing_file(self, mock_exists):
        """Test error when .env file is missing"""
        with self.assertRaises(FileNotFoundError):
            get_sensing_data.load_credentials_from_env()
    
    @patch('os.getenv')
    @patch('get_sensing_data.load_dotenv')
    @patch('os.path.exists', return_value=True)
    def test_load_credentials_missing_vars(self, mock_exists, mock_load_dotenv, mock_getenv):
        """Test error when required variables are missing"""
        # Mock environment variables with missing DB_USER
        mock_getenv.side_effect = lambda key: {
            'DB_HOST': 'test-host',
            'DB_PORT': '5432',
            'DB_NAME': 'test-db',
            'DB_PASSWORD': 'test-pass'
        }.get(key)
        
        with self.assertRaises(ValueError) as context:
            get_sensing_data.load_credentials_from_env()
        
        self.assertIn('Missing required environment variables', str(context.exception))
        self.assertIn('DB_USER', str(context.exception))
    
    @patch('os.getenv')
    @patch('get_sensing_data.load_dotenv')
    @patch('os.path.exists', return_value=True)
    def test_load_credentials_default_values(self, mock_exists, mock_load_dotenv, mock_getenv):
        """Test error when default values are not changed"""
        # Mock environment variables with default values
        mock_getenv.side_effect = lambda key: {
            'DB_HOST': 'sensing-0.msi.umn.edu',
            'DB_PORT': '5433',
            'DB_NAME': 'gems',
            'DB_USER': 'your_username',
            'DB_PASSWORD': 'test-pass'
        }.get(key)
        
        with self.assertRaises(ValueError) as context:
            get_sensing_data.load_credentials_from_env()
        
        self.assertIn('Default credentials detected', str(context.exception))

if __name__ == '__main__':
    unittest.main()