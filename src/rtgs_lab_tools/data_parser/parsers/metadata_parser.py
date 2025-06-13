#!/usr/bin/env python3
"""
GEMS Sensing Parser - Metadata Parser
Parses metadata format system configuration events.
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from .base import EventParser
from ..utils.type_system import TypeSystem


class MetadataV2Parser(EventParser):
    """
    Parser for metadata format events.
    """
    
    def can_parse(self, event_type: str) -> bool:
        """
        Check if this parser can handle the given event type.
        
        Args:
            event_type: Event type string
            
        Returns:
            bool: True if this parser can handle the event type
        """
        return event_type.lower() == "metadata/v2"
    
    def parse(self, raw_data: pd.Series) -> List[Dict[str, Any]]:
        """
        Parse a metadata event into a normalized structure.
        
        Args:
            raw_data: Raw data record
            
        Returns:
            List[Dict[str, Any]]: List of normalized metadata records
        """
        # Extract common fields
        common = self._extract_common_fields(raw_data)
        
        # Get the message
        message = raw_data.get("message", "")
        if not message:
            print(f"Empty message for record {raw_data.get('id')}")
            return []
        
        # Parse the JSON message
        result = []
        try:
            # Try to parse as JSON
            data = self._safely_parse_json(message)
            if not data:
                print(f"Invalid metadata format for record {raw_data.get('id')}")
                return []
            
            # Process the metadata fields
            self._process_metadata_fields(
                data=data, 
                path_prefix="",
                common_fields=common,
                result=result
            )
            
        except Exception as e:
            print(f"Error parsing metadata in record {raw_data.get('id')}: {e}")
        
        return result
    
    def _process_metadata_fields(
        self, 
        data: Dict[str, Any],
        path_prefix: str,
        common_fields: Dict[str, Any],
        result: List[Dict[str, Any]]
    ):
        """
        Recursively process metadata fields.
        
        Args:
            data: Metadata data dictionary
            path_prefix: Current path prefix for nested measurements
            common_fields: Common fields for all measurements
            result: List to append results to
        """
        for key, value in data.items():
            current_path = f"{path_prefix}.{key}" if path_prefix else key
            
            if isinstance(value, dict):
                # Recurse into nested dictionaries
                self._process_metadata_fields(
                    data=value,
                    path_prefix=current_path,
                    common_fields=common_fields,
                    result=result
                )
            elif isinstance(value, list):
                # For list values, serialize to string for simplicity in this version
                # In a future version, could handle lists more elegantly
                converted_value, value_type = TypeSystem.convert_value(str(value))
                
                record = {
                    **common_fields,
                    "device_type": "System",
                    "device_position": None,
                    "measurement_path": current_path,
                    "measurement_name": key,
                    "value": converted_value,
                    "unit": None,
                    "metadata": {"value_type": "list"}
                }
                
                result.append(record)
            else:
                # Handle simple key-value pairs
                converted_value, value_type = TypeSystem.convert_value(value)
                
                record = {
                    **common_fields,
                    "device_type": "System",
                    "device_position": None,
                    "measurement_path": current_path,
                    "measurement_name": key,
                    "value": converted_value,
                    "unit": None,
                    "metadata": {"value_type": value_type}
                }
                
                result.append(record)