#!/usr/bin/env python3
"""
GEMS Sensing Parser - Error/v2 Parser
Parses error/v2 format system error events.
"""

import os
import re
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from .base import EventParser

# Error code mappings for GEMS devices
ERROR_CLASSES = {
    "0": "Unknown",
    "1": "I2C",
    "2": "Power",
    "3": "IO",
    "4": "Memory",
    "5": "Timing",
    "6": "Coms",
    "7": "Disagree",
    "8": "Internal",
    "9": "Math/Logical",
    "A": "Sensor",
    "E": "System",
    "F": "Warning",
}

HARDWARE_DEVICES = {
    "0": "System Wide",
    "1": "Port 1 Talon",
    "2": "Port 2 Talon",
    "3": "Port 3 Talon",
    "4": "Port 4 Talon",
    "E": "Gonk",
    "F": "Kestrel",
}

HARDWARE_SUB_DEVICES = {
    "0": "General",
    "1": "Power",
    "2": "I2C",
    "3": "UART",
    "4": "SPI",
    "5": "GPIO",
    "6": "ADC",
    "7": "DAC",
    "8": "PWM",
    "9": "Timer",
}


class ErrorV2Parser(EventParser):
    """
    Parser for error/v2 format events.
    """
    
    def __init__(self, schema_registry=None, error_db=None):
        """
        Initialize the parser with schema registry.
        
        Args:
            schema_registry: Schema registry
            error_db: Not used, kept for compatibility
        """
        super().__init__(schema_registry, error_db)
        self.error_db = self._load_errorcodes_database()
    
    def _load_errorcodes_database(self) -> Dict[str, Dict[str, str]]:
        """
        Load error code database from ERRORCODES.md file or fetch from GitHub.
        """
        markdown_content = ""
        
        # Try to use local ERRORCODES.md file if it exists
        if os.path.exists("ERRORCODES.md"):
            with open("ERRORCODES.md", "r", encoding="utf-8") as f:
                markdown_content = f.read()
        else:
            try:
                print("Fetching error codes from GitHub...")
                import requests
                
                url = "https://raw.githubusercontent.com/gemsiot/Firmware_-_FlightControl-Demo/refs/heads/master/ERRORCODES.md"
                response = requests.get(url, allow_redirects=False, timeout=10)
                if response.status_code == 200:
                    markdown_content = response.text
                    print("Got ERRORCODES.md from Github.")
                    # Save for future use
                    with open("ERRORCODES.md", "w", encoding="utf-8") as f:
                        f.write(markdown_content)
                else:
                    print(f"Failed to fetch error codes: HTTP {response.status_code}")
                    return {}
            except Exception as e:
                print(f"Error fetching error codes: {e}")
                return {}
        
        # Parse the markdown table to extract error codes
        error_db = {}
        
        # Find the table section
        table_match = re.search(
            r"\| \*\*Base Error Code Hex\*\* \|.*?\n\|[-:|\s]+\|(.*?)(?:\n\n|$)",
            markdown_content,
            re.DOTALL,
        )
        
        if not table_match:
            print("Could not find error code table in the markdown file.")
            return {}
        
        table_content = table_match.group(1)
        
        # Process each row of the table
        for line in table_content.strip().split("\n"):
            if not line.startswith("|"):
                continue
            
            # Split the line into columns and remove leading/trailing whitespace
            columns = [col.strip() for col in line.split("|")[1:-1]]
            
            if len(columns) < 12:
                continue  # Skip malformed rows
            
            # Extract relevant information
            error_info = {
                "base_error_code_hex": columns[0].lower(),
                "specific_name": columns[1],
                "description": columns[2],
                "base_error_code_value": columns[3],
                "error_code_structure": columns[4],
                "class": columns[5],
                "code": columns[6],
                "subtype": columns[7],
                "hardware_device": columns[8],
                "hardware_subdevice": columns[9],
                "code_name": columns[10],
                "code_location": columns[11],
            }
            
            # Use the hex code as the key
            error_db[error_info["base_error_code_hex"]] = error_info
        
        print(f"Loaded {len(error_db)} error codes from database")
        return error_db
    
    def _find_error_in_db(self, hex_code: str) -> Optional[Dict[str, str]]:
        """Find error in database using matching logic."""
        hex_code = hex_code.lower()
        
        # Add 0x prefix if not present for database lookup
        if not hex_code.startswith("0x"):
            prefixed_code = "0x" + hex_code
        else:
            prefixed_code = hex_code
        
        # Try exact match first with 0x prefix
        if prefixed_code in self.error_db:
            return self.error_db[prefixed_code]
        
        # Try matching first 6 characters (0xCccc)
        if len(prefixed_code) >= 6:
            base_code = prefixed_code[:6]  # e.g., "0x8007" from "0x80070000"
            for code, info in self.error_db.items():
                if code.startswith(base_code):
                    return info
        
        # Try without 0x prefix
        clean_code = hex_code[2:] if hex_code.startswith("0x") else hex_code
        
        # Try first 4 characters without 0x for partial matching
        if len(clean_code) >= 4:
            base_code = clean_code[:4]
            search_pattern = "0x" + base_code
            for code, info in self.error_db.items():
                if code.startswith(search_pattern):
                    return info
        
        return None
    
    def _parse_error_code(self, error_code: Union[str, int]) -> Dict[str, str]:
        """Parse a single error code into components.
        
        First tries to find a specific named error in ERRORCODES.md database.
        If not found, falls back to generic class/device/subdevice decoding.
        
        Args:
            error_code: Error code as string or integer
            
        Returns:
            Dictionary with parsed error components
        """
        try:
            # Convert to string and normalize
            code_str = str(error_code).upper().strip()
            
            # Remove 0x prefix for processing
            if code_str.startswith("0X"):
                clean_code = code_str[2:]
            else:
                clean_code = code_str
            
            # Validate length (should be 4-8 hex digits for GEMS error codes)
            if len(clean_code) < 4 or len(clean_code) > 8:
                return self._create_unknown_error(error_code, f"Invalid code length: {len(clean_code)}")
            
            # STEP 1: Try to find specific named error in database
            db_info = self._find_error_in_db(clean_code)
            if db_info:
                return {
                    "error_code": str(error_code),
                    "error_name": db_info.get("specific_name", "UNKNOWN_ERROR"),
                    "error_description": db_info.get("description", "No description available"),
                    "error_class": db_info.get("class", "Unknown"),
                    "error_device": db_info.get("hardware_device", "Unknown"),
                    "error_subdevice": db_info.get("hardware_subdevice", "Unknown")
                }
            
            # STEP 2: Fall back to generic class/device/subdevice decoding
            # Parse components based on code length
            if len(clean_code) == 8:
                # 8-digit format: 0xCCCDDDSS where C=class, D=device, S=subdevice
                error_class = clean_code[0]
                hardware_device = clean_code[6] if len(clean_code) >= 7 else "0"
                hardware_sub_device = clean_code[7] if len(clean_code) >= 8 else "0"
                specific_error = clean_code[1:6]  # Middle part
            else:
                # 4-digit format: CCDX where C=class, D=device, X=sub
                error_class = clean_code[0]
                hardware_device = clean_code[1]
                hardware_sub_device = clean_code[2]
                specific_error = clean_code[3]
            
            # Look up descriptions
            error_class_name = ERROR_CLASSES.get(error_class, f"Unknown Class ({error_class})")
            hardware_device_name = HARDWARE_DEVICES.get(hardware_device, f"Unknown Device ({hardware_device})")
            hardware_sub_device_name = HARDWARE_SUB_DEVICES.get(hardware_sub_device, f"Unknown Sub-device ({hardware_sub_device})")
            
            # Generate description
            description = f"{error_class_name} error on {hardware_device_name} - {hardware_sub_device_name} (Code: {specific_error})"
            
            return {
                "error_code": str(error_code),
                "error_name": f"{error_class_name}_ERROR",
                "error_description": description,
                "error_class": error_class_name,
                "error_device": hardware_device_name,
                "error_subdevice": hardware_sub_device_name
            }
            
        except Exception as e:
            return self._create_unknown_error(error_code, f"Parsing failed: {str(e)}")
    
    def _create_unknown_error(self, error_code: Union[str, int], reason: str) -> Dict[str, str]:
        """Create error info for unparseable codes."""
        return {
            "error_code": str(error_code),
            "error_name": "UNKNOWN_ERROR",
            "error_description": f"Unable to parse error code: {reason}",
            "error_class": "Unknown",
            "error_device": "Unknown",
            "error_subdevice": "Unknown"
        }
    
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
                                error_info = self._parse_error_code(code)
                                
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
                                    "error_code": error_info["error_code"],
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