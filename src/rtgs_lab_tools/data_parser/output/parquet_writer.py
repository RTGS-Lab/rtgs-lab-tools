#!/usr/bin/env python3
"""
GEMS Sensing Parser - Parquet Writer
Outputs parsed data to Parquet format with optimizations.
"""

import os
import pandas as pd
from typing import List, Dict, Any, Optional


class ParquetWriter:
    """
    Writes parsed data to optimized Parquet format.
    """
    
    def __init__(self, output_dir: str = "./parsed_data", compression: str = "snappy"):
        """
        Initialize Parquet writer with output directory and compression options.
        
        Args:
            output_dir: Directory to write Parquet files
            compression: Compression algorithm (snappy, gzip, or none)
        """
        self.output_dir = output_dir
        self.compression = compression if compression.lower() != "none" else None
        os.makedirs(output_dir, exist_ok=True)
    
    def write(self, data, file_path: str, partition_by: Optional[str] = None) -> str:
        """
        Write parsed data to Parquet file with optimizations.
        
        Args:
            data: DataFrame or list of normalized data records
            file_path: File path to write to
            partition_by: Optional column to partition by (date, node, event)
            
        Returns:
            str: Path to written file(s)
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
        
        # Define optimized column order to group related columns
        column_order = [
            # Core identifiers first
            "id", "node_id", "event_type", "timestamp", "ingest_time", 
            # Device information next
            "device_type", "device_position", 
            # Measurement data
            "measurement_path", "measurement_name", "value", "unit",
            # Geographical data if available
            "latitude", "longitude", "altitude", "location_timestamp",
            # Error data if available
            "error_code", "error_name", "error_description", "error_class", 
            "error_device", "error_subdevice",
            # Metadata last
            "metadata"
        ]
        
        # Reorder columns if they exist
        ordered_columns = [col for col in column_order if col in df.columns]
        remaining_columns = [col for col in df.columns if col not in column_order]
        df = df[ordered_columns + remaining_columns]
        
        if partition_by:
            # Handle different partition strategies
            if partition_by == "date" and "timestamp" in df.columns:
                # Add date column for partitioning
                df["date"] = pd.to_datetime(df["timestamp"]).dt.date
                partition_cols = ["date"]
            elif partition_by == "node" and "node_id" in df.columns:
                partition_cols = ["node_id"]
            elif partition_by == "event" and "event_type" in df.columns:
                partition_cols = ["event_type"]
            else:
                print(f"Invalid partition key: {partition_by}, not partitioning")
                partition_cols = None
            
            if partition_cols:
                # Use directory name without extension
                base_dir = os.path.splitext(file_path)[0]
                # Write partitioned parquet dataset
                df.to_parquet(
                    base_dir,
                    partition_cols=partition_cols,
                    compression=self.compression,
                    index=False
                )
                print(f"Wrote {len(df)} records to partitioned Parquet dataset: {base_dir}")
                return base_dir
        
        # Write non-partitioned file
        df.to_parquet(
            file_path,
            compression=self.compression,
            index=False
        )
        print(f"Wrote {len(df)} records to {file_path}")
        
        return file_path