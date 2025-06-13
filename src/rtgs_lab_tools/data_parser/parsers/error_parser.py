#!/usr/bin/env python3
"""
GEMS Sensing Parser - Error/v2 Parser
Parses error/v2 format system error events.
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from .base import EventParser
from ..utils.error_codes import ErrorCodeHandler


class ErrorV2Parser(EventParser):
    """
    Parser for error/v2 format events.
    """
    
    def __init__(self, schema_registry=None, error_db=None):
        """
        Initialize the parser with schema registry and error database.
        
        Args:
            schema_registry: Schema registry
            error_db: Path to error code database file
        """
        super().__init__(schema_registry, error_db)
        self.error_handler = ErrorCodeHandler(error_db)
    
    def can_parse(self, event_type: str) -> bool:
        """
        Check if this parser can handle the given event type.
        
        Args:
            event_type: Event type string
            
        Returns:
            bool: True if this parser can handle the event type
        """
        return event_type.lower() == "error/v2"
    
    def parse(self, raw_data: pd.Series) -> List[Dict[str, Any]]:
        """
        Parse an error/v2 event into a normalized structure.
        
        Args:
            raw_data: Raw data record
            
        Returns:
            List[Dict[str, Any]]: List of normalized error records
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
            if not data or "Error" not in data:
                print(f"Invalid error/v2 format for record {raw_data.get('id')}")
                return []
            
            # Get the Error section
            error_section = data["Error"]
            
            # Extract metadata
            metadata = {}
            for field in ["Time", "Device ID", "Packet ID"]:
                if field in error_section:
                    metadata[field] = error_section[field]
            
            # Extract location if available
            location = {}
            if "Loc" in error_section and isinstance(error_section["Loc"], list):
                loc = error_section["Loc"]
                if len(loc) >= 2:
                    location["latitude"] = loc[0]
                    location["longitude"] = loc[1]
                if len(loc) >= 3:
                    location["altitude"] = loc[2]
                if len(loc) >= 4:
                    location["location_timestamp"] = loc[3]
            
            # Process devices array for errors
            if "Devices" in error_section and isinstance(error_section["Devices"], list):
                devices = error_section["Devices"]
                
                for device_entry in devices:
                    if not isinstance(device_entry, dict):
                        continue
                    
                    # Each device entry is a dictionary with a single key (the device type)
                    for device_type, device_info in device_entry.items():
                        if not isinstance(device_info, dict):
                            continue
                        
                        # Extract position information
                        position = device_info.get("Pos")
                        
                        # Get error codes
                        if "CODES" in device_info and isinstance(device_info["CODES"], list):
                            error_codes = device_info["CODES"]
                            overflow = device_info.get("OW", False)
                            error_count = device_info.get("NUM", len(error_codes))
                            
                            # Process each error code
                            for code in error_codes:
                                # Parse the error code
                                error_info = self.error_handler.parse_error_code(code)
                                
                                # Create normalized error record
                                record = {
                                    **common,
                                    **location,
                                    "device_type": device_type,
                                    "device_position": position,
                                    "measurement_path": f"{device_type}.{code}",
                                    "measurement_name": error_info["error_name"],
                                    "value": 1,  # Presence of error coded as 1
                                    "unit": None,
                                    "metadata": {
                                        **metadata,
                                        "overflow": overflow,
                                        "error_count": error_count
                                    },
                                    "error_code": code,
                                    "error_name": error_info["error_name"],
                                    "error_description": error_info["error_description"],
                                    "error_class": error_info["error_class"],
                                    "error_device": error_info["error_device"],
                                    "error_subdevice": error_info["error_subdevice"]
                                }
                                
                                result.append(record)
            
        except Exception as e:
            print(f"Error parsing error/v2 data in record {raw_data.get('id')}: {e}")
        
        return result