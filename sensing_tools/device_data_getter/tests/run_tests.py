#!/usr/bin/env python3
"""
Test runner for get_sensing_data.py unit tests
"""
import unittest
import sys
import os

# Import test modules
# Use relative imports when script is run directly from the tests directory
from test_credentials import TestCredentials
from test_database import TestDatabaseOperations
from test_file_operations import TestFileOperations
from test_cli import TestCommandLineInterface

def run_tests():
    """Run all test cases and report results"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestCredentials))
    test_suite.addTest(unittest.makeSuite(TestDatabaseOperations))
    test_suite.addTest(unittest.makeSuite(TestFileOperations))
    test_suite.addTest(unittest.makeSuite(TestCommandLineInterface))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_tests())