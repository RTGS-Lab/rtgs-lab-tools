#!/usr/bin/env python3
"""
GEMS Sensing Parser - Parser Factory
Creates the appropriate parser for each event type.
"""

from typing import Any, Dict, Optional, Type

import pandas as pd

from .base import EventParser


class ParserFactory:
    """
    Factory for creating event-specific parsers.
    """

    def __init__(self, verbose: bool = False):
        """Initialize the parser factory with registry of parsers."""
        self.parsers = {}
        self.parser_classes = {}
        self.parser_instances = {}  # Cache instances to avoid recreating them
        self.unknown_event_types = set()  # Track unknown event types to avoid spam
        self.verbose = verbose
        self.statistics = {
            "parsing_errors": [],
            "invalid_formats": [],
            "empty_messages": [],
        }

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
            return None

        # Convert to string in case it's not already
        if not isinstance(event_type, str):
            try:
                event_type = str(event_type)
            except:
                return None

        # Check if we already have an instance for this type
        if event_type in self.parsers:
            return self.parsers[event_type]

        # Check if we've already determined this event type has no parser
        if event_type in self.unknown_event_types:
            return None

        # Try to find a parser class that can handle this event type
        for registered_type, parser_class in self.parser_classes.items():
            # Check if we already have an instance of this parser class
            if registered_type not in self.parser_instances:
                self.parser_instances[registered_type] = parser_class(
                    verbose=self.verbose, **kwargs
                )

            # Use the cached instance to test if it can parse this event type
            if self.parser_instances[registered_type].can_parse(event_type):
                # Store and return the parser instance
                self.parsers[event_type] = self.parser_instances[registered_type]
                return self.parser_instances[registered_type]

        # Remember that this event type has no parser to avoid repeated lookups
        self.unknown_event_types.add(event_type)
        return None

    def get_parsing_summary(self) -> Dict[str, Any]:
        """
        Get a summary of parsing statistics.

        Returns:
            Dict with parsing statistics including unknown event types and counts
        """
        return {
            "supported_event_types": list(self.parsers.keys()),
            "unknown_event_types": list(self.unknown_event_types),
            "total_supported_types": len(self.parsers),
            "total_unknown_types": len(self.unknown_event_types),
            "registered_parsers": list(self.parser_classes.keys()),
        }
