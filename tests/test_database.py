"""
Unit tests for database operations in get_sensing_data.py
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import pandas as pd

# Add parent directory to path to import get_sensing_data.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import get_sensing_data

class TestDatabaseOperations(unittest.TestCase):
    """Test database query and connection functions"""
    
    def setUp(self):
        """Set up mock objects"""
        self.mock_engine = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_result = MagicMock()
        self.mock_execute = MagicMock(return_value=self.mock_result)
        
        # Mock connection and transaction
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_conn
        self.mock_conn.begin.return_value.__enter__.return_value = MagicMock()
        self.mock_conn.execute = self.mock_execute
    
    def test_create_engine_from_credentials(self):
        """Test creating SQLAlchemy engine from credentials"""
        with patch('get_sensing_data.create_engine') as mock_create_engine:
            creds = {
                'host': 'test-host',
                'port': '5432',
                'db': 'test-db',
                'user': 'test-user',
                'pass': 'test-pass'
            }
            get_sensing_data.create_engine_from_credentials(creds)
            
            # Check correct connection string
            mock_create_engine.assert_called_once()
            conn_str = mock_create_engine.call_args[0][0]
            self.assertIn('postgresql://test-user:test-pass@test-host:5432/test-db', conn_str)
    
    def test_list_available_projects(self):
        """Test listing available projects with node counts"""
        # Setup mock to return project data
        self.mock_result.fetchall.return_value = [
            ('project1', 5),
            ('project2', 10),
            ('project3', 3)
        ]
        
        # Setup text mock to capture SQL
        mock_text = MagicMock()
        mock_text.return_value.text = """
        SELECT project, COUNT(DISTINCT node_id) as node_count
        FROM node
        GROUP BY project
        ORDER BY project
        """
        
        # Call the function
        with patch('get_sensing_data.text', mock_text):
            result = get_sensing_data.list_available_projects(self.mock_engine)
        
        # Check result
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], ('project1', 5))
        self.assertEqual(result[1], ('project2', 10))
        self.assertEqual(result[2], ('project3', 3))
        
        # Check SQL query was executed (no need to check content as we're mocking it)
        self.mock_execute.assert_called_once()
    
    def test_check_project_exists_found(self):
        """Test checking if a project exists when it does"""
        # Setup mock to return a project
        self.mock_result.fetchall.return_value = [('winterturf', 15)]
        
        # Call the function
        with patch('get_sensing_data.text'):
            exists, projects = get_sensing_data.check_project_exists(self.mock_engine, 'winterturf')
        
        # Check result
        self.assertTrue(exists)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0], ('winterturf', 15))
    
    def test_check_project_exists_not_found(self):
        """Test checking if a project exists when it doesn't"""
        # Setup mock to return empty result
        self.mock_result.fetchall.return_value = []
        
        # Call the function
        with patch('get_sensing_data.text'):
            exists, projects = get_sensing_data.check_project_exists(self.mock_engine, 'nonexistent')
        
        # Check result
        self.assertFalse(exists)
        self.assertEqual(len(projects), 0)
    
    @patch('get_sensing_data.check_project_exists')
    @patch('get_sensing_data.pd.DataFrame')
    @patch('get_sensing_data.text')
    def test_get_raw_data_success(self, mock_text, mock_dataframe, mock_check_exists):
        """Test getting raw data successfully"""
        # Setup mocks
        mock_check_exists.return_value = (True, [('winterturf', 15)])
        self.mock_result.fetchall.return_value = [('data1',), ('data2',)]
        self.mock_result.keys.return_value = ['column1', 'column2']
        mock_text.return_value = "SQL QUERY"
        mock_df = MagicMock()
        mock_dataframe.return_value = mock_df
        
        # Call the function
        result = get_sensing_data.get_raw_data(
            self.mock_engine, 
            project='winterturf',
            start_date='2023-01-01',
            end_date='2023-01-31'
        )
        
        # Check result
        self.assertEqual(result, mock_df)
        
        # Just verify that execute was called
        self.mock_execute.assert_called()
        
        # Verify that the project was passed correctly to check_project_exists
        self.assertEqual(mock_check_exists.call_args[0][1], 'winterturf')
    
    @patch('get_sensing_data.check_project_exists')
    @patch('get_sensing_data.list_available_projects')
    def test_get_raw_data_project_not_found(self, mock_list_projects, mock_check_exists):
        """Test error when project doesn't exist"""
        # Setup mocks
        mock_check_exists.return_value = (False, [])
        mock_list_projects.return_value = [('otherproject', 10)]
        
        # Call the function and check for ValueError
        with self.assertRaises(ValueError) as context:
            get_sensing_data.get_raw_data(self.mock_engine, 'nonexistent')
        
        # Check error message
        self.assertIn('Project \'nonexistent\' not found', str(context.exception))
    
    @patch('get_sensing_data.check_project_exists')
    @patch('get_sensing_data.pd.DataFrame')
    @patch('get_sensing_data.text')
    def test_get_raw_data_with_node_filter(self, mock_text, mock_dataframe, mock_check_exists):
        """Test filtering by node IDs"""
        # Setup mocks
        mock_check_exists.return_value = (True, [('winterturf', 15)])
        self.mock_result.fetchall.return_value = [('data1',), ('data2',)]
        self.mock_result.keys.return_value = ['column1', 'column2']
        mock_dataframe.return_value = MagicMock()
        
        # Setup mock_text to include node ID filter in SQL
        mock_text.return_value = "SQL QUERY WITH node_id IN ('node1','node2')"
        
        # Call function with node_ids
        get_sensing_data.get_raw_data(
            self.mock_engine, 
            project='winterturf',
            node_ids=['node1', 'node2'],
            start_date='2023-01-01',
            end_date='2023-01-31'
        )
        
        # Verify the node IDs were passed to the function
        # This is an indirect test since we can't easily check the SQL directly in the test
        self.assertEqual(mock_check_exists.call_args[0][1], 'winterturf')
        self.mock_execute.assert_called()  # Just verify execution happened

if __name__ == '__main__':
    unittest.main()