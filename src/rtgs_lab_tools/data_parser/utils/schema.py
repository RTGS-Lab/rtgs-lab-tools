#!/usr/bin/env python3
"""
GEMS Sensing Parser - Schema Registry
Defines and manages schemas for different event types.
"""

from typing import Dict, Any, Optional


class SchemaRegistry:
    """
    Registry for schemas used to validate and map different event types.
    """
    
    def __init__(self):
        """Initialize the schema registry with default schemas."""
        self.schemas = {}
        self._initialize_default_schemas()
    
    def _initialize_default_schemas(self):
        """Set up default schemas for all supported event types."""
        # Core schema for normalized output
        self.schemas["core"] = {
            "id": "int64",
            "node_id": "string",
            "event_type": "string",
            "timestamp": "datetime64[ns]",
            "ingest_time": "datetime64[ns]",
            "device_type": "string",
            "device_position": "object",  # Can be string, list, etc.
            "measurement_path": "string",
            "measurement_name": "string",
            "value": "float64",  # Default type, may be overridden
            "unit": "string",
            "metadata": "object"  # JSON object
        }
        
        # Schemas for specific event types
        
        # CSV Event Schema
        self.schemas["CSV"] = {
            "header_format": "SensorType.Instance.Measurement",
            "data_format": "numeric",
            "column_separator": ","
        }
        
        # Data/v2 Schema
        self.schemas["data/v2"] = {
            "root_key": "Data",
            "metadata_fields": ["Time", "Loc", "Device ID", "Packet ID", "NumDevices"],
            "devices_key": "Devices"
        }
        
        # Diagnostic/v2 Schema
        self.schemas["diagnostic/v2"] = {
            "root_key": "Diagnostic",
            "metadata_fields": ["Time", "Loc", "Device ID", "Packet ID", "NumDevices", "Level"],
            "devices_key": "Devices"
        }
        
        # Error/v2 Schema
        self.schemas["error/v2"] = {
            "root_key": "Error",
            "metadata_fields": ["Time", "Loc", "Device ID", "Packet ID"],
            "devices_key": "Devices",
            "error_code_field": "CODES",
            "error_count_field": "NUM",
            "error_overflow_field": "OW"
        }
        
        # Metadata Schema
        self.schemas["metadata"] = {
            "flexible": True  # Metadata can have variable structure
        }
        
        # JSON (External) Schema
        self.schemas["json"] = {
            "timestamp_field": "TIMESTAMP(TS)",
            "record_number_field": "RECORD(RN)",
            "unit_pattern": r"\((.*?)\)"  # Pattern to extract units from field names
        }
    
    def get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a schema by name.
        
        Args:
            schema_name: Name of the schema to retrieve
            
        Returns:
            Dict[str, Any] or None: Schema definition or None if not found
        """
        return self.schemas.get(schema_name)
    
    def register_schema(self, name: str, schema: Dict[str, Any]):
        """
        Register a new schema or override an existing one.
        
        Args:
            name: Name for the schema
            schema: Schema definition
        """
        self.schemas[name] = schema
    
    def get_dtype_mapping(self) -> Dict[str, Any]:
        """
        Get data type mapping for output schemas (used with pandas).
        
        Returns:
            Dict[str, Any]: Mapping of field names to data types
        """
        core_schema = self.schemas.get("core", {})
        return {k: v for k, v in core_schema.items() if k != "metadata"}