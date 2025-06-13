#!/usr/bin/env python3
"""
GEMS Sensing Parser - Data/v2 Parser
Parses data/v2 format sensor data events.
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from .base import EventParser
from ..utils.type_system import TypeSystem


class DataV2Parser(EventParser):
    """
    Parser for data/v2 format events.
    """
    
    def can_parse(self, event_type: str) -> bool:
        """
        Check if this parser can handle the given event type.
        
        Args:
            event_type: Event type string
            
        Returns:
            bool: True if this parser can handle the event type
        """
        return event_type.lower() == "data/v2"
    
    def parse(self, raw_data: pd.Series) -> List[Dict[str, Any]]:
        """
        Parse a data/v2 event into a normalized structure.
        
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
            if not data or "Data" not in data:
                print(f"Invalid data/v2 format for record {raw_data.get('id')}")
                return []
            
            # Get the Data section
            data_section = data["Data"]
            
            # Extract metadata
            metadata = {}
            for field in ["Time", "Device ID", "Packet ID", "NumDevices"]:
                if field in data_section:
                    metadata[field] = data_section[field]
            
            # Extract location if available
            location = {}
            if "Loc" in data_section and isinstance(data_section["Loc"], list):
                loc = data_section["Loc"]
                if len(loc) >= 2:
                    location["latitude"] = loc[0]
                    location["longitude"] = loc[1]
                if len(loc) >= 3:
                    location["altitude"] = loc[2]
                if len(loc) >= 4:
                    location["location_timestamp"] = loc[3]
            
            # Process devices array
            if "Devices" in data_section and isinstance(data_section["Devices"], list):
                devices = data_section["Devices"]
                
                for device_entry in devices:
                    if not isinstance(device_entry, dict):
                        continue
                    
                    # Each device entry is a dictionary with a single key (the device type)
                    for device_type, device_data in device_entry.items():
                        if not isinstance(device_data, dict):
                            continue
                        
                        # Extract position information
                        position = device_data.get("Pos")
                        
                        # Process measurements recursively
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
            print(f"Error parsing data/v2 data in record {raw_data.get('id')}: {e}")
        
        return result
    
    def _process_device_data(
        self, 
        device_type: str,
        device_data: Dict[str, Any],
        position: Any,
        common_fields: Dict[str, Any],
        metadata: Dict[str, Any],
        path_prefix: str,
        result: List[Dict[str, Any]]
    ):
        """
        Recursively process device data to extract measurements.
        
        Args:
            device_type: Type of device
            device_data: Device data dictionary
            position: Position information
            common_fields: Common fields for all measurements
            metadata: Metadata for the event
            path_prefix: Current path prefix for nested measurements
            result: List to append results to
        """
        # Skip position as it's handled separately
        skip_keys = ["Pos"]
        
        for key, value in device_data.items():
            if key in skip_keys:
                continue
                
            current_path = f"{path_prefix}.{key}" if path_prefix else key
            
            if isinstance(value, dict):
                # Recurse into nested dictionaries
                self._process_device_data(
                    device_type=device_type,
                    device_data=value,
                    position=position,
                    common_fields=common_fields,
                    metadata=metadata,
                    path_prefix=current_path,
                    result=result
                )
            elif isinstance(value, list):
                # Handle array values
                if all(not isinstance(item, (dict, list)) for item in value):
                    # This is a simple array of values, treat as a single measurement with array value
                    converted_value, value_type = TypeSystem.convert_value(value)
                    
                    record = {
                        **common_fields,
                        "device_type": device_type,
                        "device_position": position,
                        "measurement_path": current_path,
                        "measurement_name": key,
                        "value": converted_value,
                        "unit": None,
                        "metadata": metadata.copy()
                    }
                    
                    result.append(record)
                else:
                    # Complex array with nested structures, handle each item
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            # Recurse into dictionary
                            self._process_device_data(
                                device_type=device_type,
                                device_data=item,
                                position=position,
                                common_fields=common_fields,
                                metadata={**metadata, "array_index": i},
                                path_prefix=f"{current_path}[{i}]",
                                result=result
                            )
                        elif not isinstance(item, (dict, list)) and item is not None:
                            # Simple value in an array
                            converted_value, value_type = TypeSystem.convert_value(item)
                            
                            record = {
                                **common_fields,
                                "device_type": device_type,
                                "device_position": position,
                                "measurement_path": f"{current_path}[{i}]",
                                "measurement_name": key,
                                "value": converted_value,
                                "unit": None,
                                "metadata": {**metadata, "array_index": i}
                            }
                            
                            result.append(record)
            elif value is not None:
                # Simple key-value pair
                converted_value, value_type = TypeSystem.convert_value(value)
                
                # Extract unit if embedded in the key name
                measurement_name, unit = TypeSystem.extract_unit(key)
                
                record = {
                    **common_fields,
                    "device_type": device_type,
                    "device_position": position,
                    "measurement_path": current_path,
                    "measurement_name": measurement_name,
                    "value": converted_value,
                    "unit": unit,
                    "metadata": metadata.copy()
                }
                
                result.append(record)