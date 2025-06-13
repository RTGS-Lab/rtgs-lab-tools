#!/usr/bin/env python3
"""
GEMS Sensing Parser - CSV Event Parser
Parses events with CSV format.
"""

import csv
import io
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from .base import EventParser
from ..utils.type_system import TypeSystem


class CSVEventParser(EventParser):
    """
    Parser for CSV format events.
    """
    
    def can_parse(self, event_type: str) -> bool:
        """
        Check if this parser can handle the given event type.
        
        Args:
            event_type: Event type string
            
        Returns:
            bool: True if this parser can handle the event type
        """
        return event_type.lower() == "csv"
    
    def parse(self, raw_data: pd.Series) -> List[Dict[str, Any]]:
        """
        Parse a CSV event into a normalized structure.
        
        Args:
            raw_data: Raw data record
            
        Returns:
            List[Dict[str, Any]]: List of normalized measurements
        """
        # Extract common fields
        common = self._extract_common_fields(raw_data)
        
        # Get the CSV message
        message = raw_data.get("message", "")
        if not message:
            print(f"Empty message for record {raw_data.get('id')}")
            return []
        
        # Parse the CSV message
        result = []
        try:
            # Split the message into lines
            lines = message.strip().split("\n")
            if len(lines) < 2:
                print(f"Invalid CSV format (not enough lines) for record {raw_data.get('id')}")
                return []
            
            # Parse header and data lines
            header_line = lines[0]
            data_line = lines[1]
            
            # Parse the header to get column names
            headers = [h.strip() for h in header_line.split(",")]
            
            # Parse the data values
            values = []
            # Use csv module to handle quoting correctly
            for row in csv.reader([data_line]):
                values = [v.strip() for v in row]
            
            if len(headers) != len(values):
                print(f"Header/data mismatch: {len(headers)} headers, {len(values)} values in record {raw_data.get('id')}")
                # Try to recover - use shorter length
                min_len = min(len(headers), len(values))
                headers = headers[:min_len]
                values = values[:min_len]
            
            # Process each column
            for header, value in zip(headers, values):
                # Process the sensor format: SensorType.Instance.Measurement
                parts = header.split(".")
                
                if len(parts) >= 3:
                    sensor_type = parts[0]
                    instance = parts[1]
                    measurement = ".".join(parts[2:])  # Join in case measurement has dots
                    
                    # Extract position information
                    # If instance is numeric, use as position
                    position = [instance] if instance.isdigit() else None
                    
                    # Convert the value
                    converted_value, value_type = TypeSystem.convert_value(value)
                    
                    # Extract unit if available in the measurement name
                    measurement_name, unit = TypeSystem.extract_unit(measurement)
                    
                    # Create normalized record
                    record = {
                        **common,
                        "device_type": sensor_type,
                        "device_position": position,
                        "measurement_path": header,
                        "measurement_name": measurement_name,
                        "value": converted_value,
                        "unit": unit
                    }
                    
                    result.append(record)
                else:
                    # Handle malformed headers
                    print(f"Malformed header format: {header} in record {raw_data.get('id')}")
                    # Still try to extract a value
                    converted_value, value_type = TypeSystem.convert_value(value)
                    
                    record = {
                        **common,
                        "device_type": "Unknown",
                        "device_position": None,
                        "measurement_path": header,
                        "measurement_name": header,
                        "value": converted_value,
                        "unit": None
                    }
                    
                    result.append(record)
            
        except Exception as e:
            print(f"Error parsing CSV data in record {raw_data.get('id')}: {e}")
        
        return result