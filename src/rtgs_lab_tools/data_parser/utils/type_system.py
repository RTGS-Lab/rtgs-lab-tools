#!/usr/bin/env python3
"""
GEMS Sensing Parser - Type System
Handles conversion and validation of data types.
"""

import re
import json
import datetime
from typing import Any, Dict, List, Optional, Union, Tuple


class TypeSystem:
    """
    Handles conversion and validation of data types for parsed measurements.
    """
    
    @staticmethod
    def convert_value(value: Any, target_type: str = None) -> Tuple[Any, str]:
        """
        Convert a value to the appropriate type.
        
        Args:
            value: The value to convert
            target_type: Optional target type to convert to
            
        Returns:
            Tuple[Any, str]: Converted value and the inferred type as a string
        """
        if value is None:
            return None, "null"
        
        # If target type is specified, attempt conversion
        if target_type:
            try:
                if target_type == "float" or target_type == "float64":
                    return float(value), "float"
                elif target_type == "int" or target_type == "int64":
                    return int(value), "int"
                elif target_type == "bool":
                    return bool(value), "bool"
                elif target_type == "datetime":
                    if isinstance(value, (int, float)):
                        # Assume Unix timestamp
                        return datetime.datetime.fromtimestamp(value), "datetime"
                    else:
                        # Try parsing as ISO format
                        return datetime.datetime.fromisoformat(str(value)), "datetime"
                else:
                    # Default to string
                    return str(value), "string"
            except (ValueError, TypeError):
                # If conversion fails, fall back to automatic detection
                pass
        
        # Automatic type detection
        if isinstance(value, bool):
            return value, "bool"
        elif isinstance(value, int):
            return value, "int"
        elif isinstance(value, float):
            return value, "float"
        elif isinstance(value, (datetime.datetime, datetime.date)):
            return value, "datetime"
        elif isinstance(value, (list, tuple)):
            return value, "array"
        elif isinstance(value, dict):
            return value, "object"
        else:
            # Try to parse as JSON
            try:
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    parsed = json.loads(value)
                    return parsed, "object" if isinstance(parsed, dict) else "array"
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Try to parse as number
            try:
                if isinstance(value, str) and re.match(r'^-?\d+(\.\d+)?$', value):
                    if '.' in value:
                        parsed = float(value)
                        return parsed, "float"
                    else:
                        parsed = int(value)
                        return parsed, "int"
            except (ValueError, TypeError):
                pass
            
            # Try to parse as datetime
            try:
                if isinstance(value, str):
                    # Common datetime patterns
                    for pattern in [
                        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO format
                        r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # SQL format
                        r'^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',  # MM/DD/YYYY
                    ]:
                        if re.match(pattern, value):
                            parsed = datetime.datetime.fromisoformat(value.replace('T', ' '))
                            return parsed, "datetime"
            except (ValueError, TypeError):
                pass
            
            # If all else fails, return as string
            return str(value), "string"
    
    @staticmethod
    def extract_unit(field_name: str) -> Tuple[str, Optional[str]]:
        """
        Extract unit information from a field name if available.
        
        Args:
            field_name: Field name that might contain unit information
            
        Returns:
            Tuple[str, Optional[str]]: Clean field name and unit (if found)
        """
        # Check for units in parentheses: "Temperature(C)" or "BattV_Avg(Volts)"
        unit_pattern = r'^(.*?)\((.*?)\)$'
        match = re.match(unit_pattern, field_name)
        
        if match:
            clean_name = match.group(1).strip()
            unit = match.group(2).strip()
            return clean_name, unit
        
        # No explicit unit found
        return field_name, None