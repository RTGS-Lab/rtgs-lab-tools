"""
Unit tests for file operations in get_sensing_data.py
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import pandas as pd
import shutil
import zipfile

# Add parent directory to path to import get_sensing_data.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import get_sensing_data

class TestFileOperations(unittest.TestCase):
    """Test file operations like saving data and creating directories"""
    
    def setUp(self):
        """Set up temporary directory for test files"""
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a simple test dataframe
        self.test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'node_id': ['node1', 'node2', 'node3'],
            'publish_time': pd.date_range(start='2023-01-01', periods=3),
            'message': ['msg1', 'msg2', 'msg3']
        })
        
    def tearDown(self):
        """Clean up after tests"""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_ensure_data_directory(self):
        """Test creating data directory"""
        # Test with default directory
        data_dir = get_sensing_data.ensure_data_directory()
        self.assertTrue(os.path.exists(data_dir))
        self.assertEqual(data_dir, os.path.join(os.getcwd(), 'data'))
        
        # Test with custom directory
        custom_dir = os.path.join(self.temp_dir, 'custom_data')
        data_dir = get_sensing_data.ensure_data_directory(custom_dir)
        self.assertTrue(os.path.exists(custom_dir))
        self.assertEqual(data_dir, custom_dir)
    
    def test_calculate_file_hash(self):
        """Test calculating file hash"""
        # Create a test file with known content
        test_file = os.path.join(self.temp_dir, 'test_file.txt')
        test_content = b'test content for hashing'
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Calculate hash with our function
        file_hash = get_sensing_data.calculate_file_hash(test_file)
        
        # Calculate expected hash
        import hashlib
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        # Compare
        self.assertEqual(file_hash, expected_hash)
    
    @patch('get_sensing_data.logger')
    def test_save_data_csv(self, mock_logger):
        """Test saving data to CSV"""
        # Save data to CSV
        filename = 'test_output'
        output_file = get_sensing_data.save_data(
            self.test_df,
            self.temp_dir,
            filename,
            format='csv',
            create_zip=False
        )
        
        # Check file exists
        expected_path = os.path.join(self.temp_dir, 'test_output.csv')
        self.assertEqual(output_file, expected_path)
        self.assertTrue(os.path.exists(expected_path))
        
        # Check content
        saved_df = pd.read_csv(expected_path)
        self.assertEqual(len(saved_df), 3)
        self.assertEqual(saved_df['node_id'].tolist(), ['node1', 'node2', 'node3'])
    
    @patch('get_sensing_data.logger')
    def test_save_data_parquet(self, mock_logger):
        """Test saving data to Parquet format"""
        try:
            import pyarrow  # Check if pyarrow is available
            
            # Save data to Parquet
            filename = 'test_output'
            output_file = get_sensing_data.save_data(
                self.test_df,
                self.temp_dir,
                filename,
                format='parquet',
                create_zip=False
            )
            
            # Check file exists
            expected_path = os.path.join(self.temp_dir, 'test_output.parquet')
            self.assertEqual(output_file, expected_path)
            self.assertTrue(os.path.exists(expected_path))
            
            # Check content
            saved_df = pd.read_parquet(expected_path)
            self.assertEqual(len(saved_df), 3)
            self.assertEqual(saved_df['node_id'].tolist(), ['node1', 'node2', 'node3'])
            
        except ImportError:
            self.skipTest("pyarrow not available, skipping Parquet test")
    
    @patch('get_sensing_data.logger')
    def test_save_data_with_zip(self, mock_logger):
        """Test saving data with zip compression"""
        # Save data with zip
        filename = 'test_output'
        output_file = get_sensing_data.save_data(
            self.test_df,
            self.temp_dir,
            filename,
            format='csv',
            create_zip=True
        )
        
        # Check zip file exists
        expected_zip = os.path.join(self.temp_dir, 'test_output.csv.zip')
        self.assertEqual(output_file, expected_zip)
        self.assertTrue(os.path.exists(expected_zip))
        
        # Check zip contents
        with zipfile.ZipFile(expected_zip, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            # Check original CSV and metadata are in the zip
            self.assertIn('test_output.csv', file_list)
            self.assertTrue(any('metadata' in name for name in file_list))

if __name__ == '__main__':
    unittest.main()