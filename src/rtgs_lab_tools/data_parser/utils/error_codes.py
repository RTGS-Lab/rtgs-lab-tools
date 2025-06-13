#!/usr/bin/env python3
"""
GEMS Sensing Parser - Error Code Utilities
Integrates with error_code_parser.py to handle error codes.
"""

import os
import sys
from typing import Dict, List, Any, Optional

# Add parent directory to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
try:
    # Import the error_code_parser classes
    from error_code_parser import ErrorCode, load_error_database
except ImportError:
    print("Failed to import error_code_parser.py - error code parsing will be limited")


class ErrorCodeHandler:
    """
    Handle error codes using error_code_parser.py functionality.
    """
    
    def __init__(self, error_db_path: Optional[str] = None):
        """
        Initialize the error code handler with an optional path to error codes database.
        
        Args:
            error_db_path: Path to the error code database markdown file
        """
        self.error_db = self._load_error_db(error_db_path)
    
    def _load_error_db(self, error_db_path: Optional[str]) -> Dict[str, Dict[str, str]]:
        """
        Load error database using error_code_parser.
        
        Args:
            error_db_path: Path to the error code database markdown file
            
        Returns:
            Dict[str, Dict[str, str]]: Error code database
        """
        try:
            return load_error_database(error_db_path)
        except Exception as e:
            print(f"Error loading error database: {e}")
            return {}
    
    def parse_error_code(self, code: str) -> Dict[str, Any]:
        """
        Parse an error code into its components and description.
        
        Args:
            code: Error code in hex format
            
        Returns:
            Dict[str, Any]: Error information
        """
        try:
            error = ErrorCode(code, self.error_db)
            
            return {
                "error_code": code,
                "error_name": error.error_info.get('specific_name', 'UNKNOWN_ERROR'),
                "error_description": error.error_info.get('description', 'No description available'),
                "error_class": error.error_info.get('class', 'Unknown'),
                "error_device": error.error_info.get('hardware_device', 'Unknown Device'),
                "error_subdevice": error.error_info.get('hardware_subdevice', 'Unknown Subdevice')
            }
        except Exception as e:
            print(f"Error parsing error code {code}: {e}")
            return {
                "error_code": code,
                "error_name": "PARSING_ERROR",
                "error_description": f"Error parsing code: {str(e)}",
                "error_class": "Unknown",
                "error_device": "Unknown",
                "error_subdevice": "Unknown"
            }