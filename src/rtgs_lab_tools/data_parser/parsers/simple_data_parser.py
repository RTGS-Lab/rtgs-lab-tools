#!/usr/bin/env python3
"""
GEMS Sensing Parser - Simple Data Event Parser
Parses "Data" format events (flat CSV structure without headers).
"""

import csv
import io
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from .base import EventParser
from ..utils.type_system import TypeSystem


class SimpleDataParser(EventParser):
    """
    Parser for simple "Data" format events (flat CSV structure).
    """
    
    def can_parse(self, event_type: str) -> bool:
        """
        Check if this parser can handle the given event type.
        
        Args:
            event_type: Event type string
            
        Returns:
            bool: True if this parser can handle the event type
        """
        return event_type == "Data"
    
    def parse(self, raw_data: pd.Series) -> List[Dict[str, Any]]:
        """
        Parse a Data event into a normalized structure.
        
        Args:
            raw_data: Raw data record
            
        Returns:
            List[Dict[str, Any]]: List of normalized measurements
        """
        # Extract common fields
        common = self._extract_common_fields(raw_data)
        
        # Get the message
        message = raw_data.get("message", "")
        if not message:
            print(f"Empty message for record {raw_data.get('id')}")
            return []
        
        # Parse the message
        result = []
        try:
            # Attempt to parse as CSV
            values = []
            for row in csv.reader([message.strip()]):
                values = [v.strip() for v in row]
            
            if not values:
                print(f"No values found in record {raw_data.get('id')}")
                return []
            
            # Since there are no headers, we'll use generic names
            # First value is typically a timestamp
            if len(values) > 0:
                converted_value, value_type = TypeSystem.convert_value(values[0])
                
                record = {
                    **common,
                    "device_type": "Unknown",
                    "device_position": None,
                    "measurement_path": "Data.0",
                    "measurement_name": "timestamp",
                    "value": converted_value,
                    "unit": None
                }
                
                result.append(record)
            
            # Process remaining values as generic measurements
            for i, value in enumerate(values[1:], 1):
                converted_value, value_type = TypeSystem.convert_value(value)
                
                record = {
                    **common,
                    "device_type": "Unknown",
                    "device_position": None,
                    "measurement_path": f"Data.{i}",
                    "measurement_name": f"value_{i}",
                    "value": converted_value,
                    "unit": None
                }
                
                result.append(record)
            
        except Exception as e:
            print(f"Error parsing Data format in record {raw_data.get('id')}: {e}")
        
        return result