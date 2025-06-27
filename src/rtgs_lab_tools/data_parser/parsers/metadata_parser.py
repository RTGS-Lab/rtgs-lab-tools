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
        Process metadata fields from the Metadata section.
        
        Args:
            data: Full JSON data dictionary containing "Metadata" section
            path_prefix: Current path prefix for nested measurements  
            common_fields: Common fields for all measurements
            result: List to append results to
        """
        # Check if this is the root metadata structure
        if "Metadata" not in data:
            print("No 'Metadata' section found in data")
            return
            
        metadata_section = data["Metadata"]
        
        # Extract basic metadata info
        metadata_info = {}
        for field in ["Time", "Device ID", "Packet ID", "NumDevices"]:
            if field in metadata_section:
                metadata_info[field] = metadata_section[field]
        
        # Extract location if available
        location = {}
        if "Loc" in metadata_section and isinstance(metadata_section["Loc"], list):
            loc = metadata_section["Loc"]
            if len(loc) >= 2:
                location["latitude"] = loc[0]
                location["longitude"] = loc[1]
            if len(loc) >= 3:
                location["altitude"] = loc[2]
            if len(loc) >= 4:
                location["location_timestamp"] = loc[3]
        
        # Process devices array
        if "Devices" in metadata_section and isinstance(metadata_section["Devices"], list):
            devices = metadata_section["Devices"]
            
            for device_entry in devices:
                if not isinstance(device_entry, dict):
                    continue
                
                # Each device entry is a dictionary with a single key (the device type)
                for device_type, device_data in device_entry.items():
                    if not isinstance(device_data, dict):
                        continue
                    
                    # Extract position information
                    position = device_data.get("Pos")
                    
                    # Process device metadata recursively
                    self._process_device_metadata(
                        device_type=device_type,
                        device_data=device_data,
                        position=position,
                        common_fields={**common_fields, **location},
                        metadata=metadata_info,
                        path_prefix="",
                        result=result
                    )
    
    def _process_device_metadata(
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
        Process device metadata to extract configuration info.
        
        Args:
            device_type: Type of device
            device_data: Device metadata dictionary
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
                self._process_device_metadata(
                    device_type=device_type,
                    device_data=value,
                    position=position,
                    common_fields=common_fields,
                    metadata=metadata,
                    path_prefix=current_path,
                    result=result
                )
            elif isinstance(value, list):
                # Handle array values - serialize to string for metadata
                converted_value, value_type = TypeSystem.convert_value(str(value))
                
                record = {
                    **common_fields,
                    "device_type": device_type,
                    "device_position": position,
                    "measurement_path": current_path,
                    "measurement_name": key,
                    "value": converted_value,
                    "unit": None,
                    "metadata": {**metadata, "value_type": "list", "data_type": "configuration"}
                }
                
                result.append(record)
            elif value is not None:
                # Simple key-value pair - this is configuration metadata
                converted_value, value_type = TypeSystem.convert_value(value)
                
                # Determine unit/type based on key name for metadata fields
                unit = None
                if any(x in key.lower() for x in ["firmware", "hardware", "version", "schema"]):
                    unit = "version"
                elif "sn" == key.lower() or "serial" in key.lower():
                    unit = "serial_number"
                elif "uuid" in key.lower():
                    unit = "uuid"
                elif any(x in key.lower() for x in ["model", "mfg"]):
                    unit = "identifier"
                elif any(x in key.lower() for x in ["id", "adr"]):
                    unit = "address"
                
                record = {
                    **common_fields,
                    "device_type": device_type,
                    "device_position": position,
                    "measurement_path": current_path,
                    "measurement_name": key,
                    "value": converted_value,
                    "unit": unit,
                    "metadata": {**metadata, "value_type": value_type, "data_type": "configuration"}
                }
                
                result.append(record)