#!/usr/bin/env python3
"""
GEMS Sensing Parser - CSV Writer
Outputs parsed data to CSV format.
"""

import os
import pandas as pd
from typing import List, Dict, Any, Optional


class CSVWriter:
    """
    Writes parsed data to CSV format.
    """
    
    def __init__(self, output_dir: str = "./parsed_data"):
        """
        Initialize CSV writer with output directory.
        
        Args:
            output_dir: Directory to write CSV files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def write(self, data, file_path: str) -> str:
        """
        Write parsed data to CSV file.
        
        Args:
            data: DataFrame or list of normalized data records
            file_path: File path to write to
            
        Returns:
            str: Path to written file
        """
        if isinstance(data, pd.DataFrame):
            df = data
            if df.empty:
                print("No data to write")
                return None
        elif isinstance(data, list):
            if not data:
                print("No data to write")
                return None
            df = pd.DataFrame(data)
        else:
            print(f"Unsupported data type: {type(data)}")
            return None
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Write to CSV
        df.to_csv(file_path, index=False)
        print(f"Wrote {len(df)} records to {file_path}")
        
        return file_path