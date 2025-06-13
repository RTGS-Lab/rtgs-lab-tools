#!/usr/bin/env python3
"""
GEMS Sensing Parser - Diagnostic/v2 Parser
Parses diagnostic/v2 format events with system diagnostic information.
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from .base import EventParser
from .data_parser import DataV2Parser
from ..utils.type_system import TypeSystem


class DiagnosticV2Parser(DataV2Parser):
    """
    Parser for diagnostic/v2 format events.
    Extends DataV2Parser since the structure is similar.
    """
    
    def can_parse(self, event_type: str) -> bool:
        """
        Check if this parser can handle the given event type.
        
        Args:
            event_type: Event type string
            
        Returns:
            bool: True if this parser can handle the event type
        """
        return event_type.lower() == "diagnostic/v2"
    
    def parse(self, raw_data: pd.Series) -> List[Dict[str, Any]]:
        """
        Parse a diagnostic/v2 event into a normalized structure.
        
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
            if not data or "Diagnostic" not in data:
                print(f"Invalid diagnostic/v2 format for record {raw_data.get('id')}")
                return []
            
            # Get the Diagnostic section
            diagnostic_section = data["Diagnostic"]
            
            # Extract metadata
            metadata = {}
            for field in ["Time", "Device ID", "Packet ID", "NumDevices", "Level"]:
                if field in diagnostic_section:
                    metadata[field] = diagnostic_section[field]
            
            # Extract location if available
            location = {}
            if "Loc" in diagnostic_section and isinstance(diagnostic_section["Loc"], list):
                loc = diagnostic_section["Loc"]
                if len(loc) >= 2:
                    location["latitude"] = loc[0]
                    location["longitude"] = loc[1]
                if len(loc) >= 3:
                    location["altitude"] = loc[2]
                if len(loc) >= 4:
                    location["location_timestamp"] = loc[3]
            
            # Process devices array - using the same approach as data_parser.py
            if "Devices" in diagnostic_section and isinstance(diagnostic_section["Devices"], list):
                devices = diagnostic_section["Devices"]
                
                for device_entry in devices:
                    if not isinstance(device_entry, dict):
                        continue
                    
                    # Each device entry is a dictionary with a single key (the device type)
                    for device_type, device_data in device_entry.items():
                        if not isinstance(device_data, dict):
                            continue
                        
                        # Extract position information
                        position = device_data.get("Pos")
                        
                        # Process measurements recursively - reuse the method from DataV2Parser
                        self._process_device_data(
                            device_type=device_type,
                            device_data=device_data,
                            position=position,
                            common_fields={**common, **location},
                            metadata=metadata,
                            path_prefix="",
                            result=result
                        )
            
        except Exception as e:
            print(f"Error parsing diagnostic/v2 data in record {raw_data.get('id')}: {e}")
        
        return result