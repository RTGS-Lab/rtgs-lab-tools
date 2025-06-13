#!/usr/bin/env python3
"""
GEMS Sensing Parser - JSON Event Parser
Parses events with JSON format (external systems like weather stations).
"""

import re
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from .base import EventParser
from ..utils.type_system import TypeSystem


class JSONEventParser(EventParser):
    """
    Parser for JSON format events from external systems.
    """
    
    def can_parse(self, event_type: str) -> bool:
        """
        Check if this parser can handle the given event type.
        
        Args:
            event_type: Event type string
            
        Returns:
            bool: True if this parser can handle the event type
        """
        return event_type.lower() == "json"
    
    def parse(self, raw_data: pd.Series) -> List[Dict[str, Any]]:
        """
        Parse a JSON event into a normalized structure.
        
        Args:
            raw_data: Raw data record
            
        Returns:
            List[Dict[str, Any]]: List of normalized measurements
        """
        # Extract common fields
        common = self._extract_common_fields(raw_data)
        
        # Get the JSON message
        message = raw_data.get("message", "")
        if not message:
            print(f"Empty message for record {raw_data.get('id')}")
            return []
        
        # Parse the JSON message
        result = []
        try:
            # Parse JSON
            data = self._safely_parse_json(message)
            if not data:
                print(f"Invalid JSON format for record {raw_data.get('id')}")
                return []
            
            # Get location data if available
            location = {}
            if "Latitude" in data and "Longitude" in data:
                location = {
                    "latitude": float(data["Latitude"]) if data["Latitude"] is not None else None,
                    "longitude": float(data["Longitude"]) if data["Longitude"] is not None else None
                }
                
                if "Elevation" in data:
                    location["altitude"] = float(data["Elevation"]) if data["Elevation"] is not None else None
            
            # Determine timestamp
            timestamp = data.get("TIMESTAMP(TS)") or data.get("Timestamp") or data.get("Time")
            record_num = data.get("RECORD(RN)") or data.get("Record")
            
            # Extract geographic info if available
            geo_fields = ["Latitude", "Longitude", "Elevation", "TIMESTAMP(TS)", "RECORD(RN)"]
            
            # Process each field in the JSON
            for field_name, field_value in data.items():
                # Skip certain fields we've already processed
                if field_name in geo_fields:
                    continue
                
                # Skip null values
                if field_value is None:
                    continue
                
                # Convert the value
                converted_value, value_type = TypeSystem.convert_value(field_value)
                
                # Extract unit information if available in field name
                # Example: "BattV_Avg(Volts)" -> "BattV_Avg", "Volts"
                clean_name, unit = TypeSystem.extract_unit(field_name)
                
                # Create normalized record
                record = {
                    **common,
                    "device_type": "External",
                    "device_position": None,
                    "measurement_path": field_name,
                    "measurement_name": clean_name,
                    "value": converted_value,
                    "unit": unit,
                    **location  # Add location if available
                }
                
                # Add metadata
                metadata = {}
                if record_num is not None:
                    metadata["record_number"] = record_num
                
                if metadata:
                    record["metadata"] = metadata
                
                result.append(record)
            
        except Exception as e:
            print(f"Error parsing JSON data in record {raw_data.get('id')}: {e}")
        
        return result