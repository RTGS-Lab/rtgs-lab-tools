#!/usr/bin/env python3
"""
GEMS Sensing Data Parser - Base Class
This module contains the abstract base class for all event type parsers.
"""

import abc
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple


class EventParser(abc.ABC):
    """
    Abstract base class for all event type parsers.
    Defines the interface that all concrete parser implementations must follow.
    """

    def __init__(self, schema_registry=None, error_db=None):
        """
        Initialize the parser with optional schema registry and error database.
        
        Args:
            schema_registry: Registry of schemas for validation
            error_db: Error code database for error event parsing
        """
        self.schema_registry = schema_registry
        self.error_db = error_db
    
    @abc.abstractmethod
    def can_parse(self, event_type: str) -> bool:
        """
        Determine if this parser can handle the given event type.
        
        Args:
            event_type: The event type identifier
            
        Returns:
            bool: True if this parser can handle the event type, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def parse(self, raw_data: pd.Series) -> List[Dict[str, Any]]:
        """
        Parse a single event record into a normalized structure.
        
        Args:
            raw_data: A pandas Series containing the raw event data
                (including id, node_id, event, message, etc.)
            
        Returns:
            List[Dict[str, Any]]: List of normalized measurement records
        """
        pass
    
    def _extract_common_fields(self, raw_data: pd.Series) -> Dict[str, Any]:
        """
        Extract common fields shared by all event types.
        
        Args:
            raw_data: A pandas Series containing the raw event data
            
        Returns:
            Dict[str, Any]: A dictionary of common fields
        """
        return {
            "id": raw_data.get("id"),
            "node_id": raw_data.get("node_id"),
            "event_type": raw_data.get("event"),
            "timestamp": raw_data.get("publish_time"),
            "ingest_time": raw_data.get("ingest_time"),
            "message_id": raw_data.get("message_id")
        }
    
    def _safely_parse_json(self, json_str: str) -> Dict[str, Any]:
        """
        Safely parse a JSON string with error handling.
        
        Args:
            json_str: JSON string to parse
            
        Returns:
            Dict[str, Any]: Parsed JSON object or empty dict on error
        """
        try:
            # Handle possible escaped JSON strings
            if json_str.startswith('"') and json_str.endswith('"'):
                json_str = json_str[1:-1]
            
            # Replace escaped quotes
            json_str = json_str.replace('\\"', '"').replace('""', '"')
            
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            # Log error but don't fail parsing
            print(f"Error parsing JSON: {e}")
            return {}