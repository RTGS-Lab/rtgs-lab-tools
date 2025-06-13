#!/usr/bin/env python3
"""
GEMS Sensing Parser - Parser Factory
Creates the appropriate parser for each event type.
"""

from typing import Dict, Any, Optional, Type
import pandas as pd
from .base import EventParser


class ParserFactory:
    """
    Factory for creating event-specific parsers.
    """
    
    def __init__(self):
        """Initialize the parser factory with registry of parsers."""
        self.parsers = {}
        self.parser_classes = {}
    
    def register_parser(self, event_type: str, parser_class: Type[EventParser]):
        """
        Register a parser class for a specific event type.
        
        Args:
            event_type: The event type this parser handles
            parser_class: The parser class to use
        """
        self.parser_classes[event_type] = parser_class
    
    def create_parser(self, event_type: str, **kwargs) -> Optional[EventParser]:
        """
        Create a parser instance for the given event type.
        
        Args:
            event_type: The event type to create a parser for
            **kwargs: Additional parameters to pass to the parser constructor
            
        Returns:
            EventParser or None: An instance of the appropriate parser or None if not found
        """
        # Handle NaN or None values in event_type
        if event_type is None or pd.isna(event_type):
            print(f"Skipping record with missing event type")
            return None
        
        # Convert to string in case it's not already
        if not isinstance(event_type, str):
            try:
                event_type = str(event_type)
                print(f"Converted non-string event type to string: {event_type}")
            except:
                print(f"Could not convert event type to string: {event_type}")
                return None
        
        # Check if we already have an instance for this type
        if event_type in self.parsers:
            return self.parsers[event_type]
        
        # Try to find a parser class that can handle this event type
        for registered_type, parser_class in self.parser_classes.items():
            # Create a temporary instance to test if it can parse this event type
            temp_parser = parser_class(**kwargs)
            if temp_parser.can_parse(event_type):
                # Store and return the parser instance
                self.parsers[event_type] = temp_parser
                return temp_parser
        
        print(f"No parser found for event type: {event_type}")
        return None