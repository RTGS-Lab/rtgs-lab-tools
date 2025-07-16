"""Tests for parser factory."""

from unittest.mock import Mock, patch
import pandas as pd
import pytest

from rtgs_lab_tools.data_parser.parsers.factory import ParserFactory
from rtgs_lab_tools.data_parser.parsers.base import EventParser


class TestParserFactory:
    """Test the parser factory class."""

    @pytest.fixture
    def factory(self):
        """Create a parser factory instance for testing."""
        return ParserFactory()

    @pytest.fixture
    def mock_parser_class(self):
        """Create a mock parser class."""
        mock_class = Mock(spec=EventParser)
        mock_instance = Mock(spec=EventParser)
        mock_instance.can_parse.return_value = True
        mock_class.return_value = mock_instance
        return mock_class

    @pytest.fixture
    def mock_parser_class_false(self):
        """Create a mock parser class that returns False for can_parse."""
        mock_class = Mock(spec=EventParser)
        mock_instance = Mock(spec=EventParser)
        mock_instance.can_parse.return_value = False
        mock_class.return_value = mock_instance
        return mock_class

    def test_init(self, factory):
        """Test factory initialization."""
        assert factory.parsers == {}
        assert factory.parser_classes == {}

    def test_register_parser(self, factory, mock_parser_class):
        """Test registering a parser class."""
        event_type = "test_event"
        factory.register_parser(event_type, mock_parser_class)
        
        assert event_type in factory.parser_classes
        assert factory.parser_classes[event_type] == mock_parser_class

    def test_create_parser_success(self, factory, mock_parser_class):
        """Test creating a parser successfully."""
        event_type = "test_event"
        factory.register_parser(event_type, mock_parser_class)
        
        parser = factory.create_parser(event_type)
        
        assert parser is not None
        assert parser == mock_parser_class.return_value
        mock_parser_class.assert_called_once_with()
        mock_parser_class.return_value.can_parse.assert_called_once_with(event_type)

    def test_create_parser_cached(self, factory, mock_parser_class):
        """Test that parser instances are cached."""
        event_type = "test_event"
        factory.register_parser(event_type, mock_parser_class)
        
        parser1 = factory.create_parser(event_type)
        parser2 = factory.create_parser(event_type)
        
        assert parser1 is parser2
        # Should only create the parser once
        mock_parser_class.assert_called_once()

    def test_create_parser_none_event_type(self, factory):
        """Test creating a parser with None event type."""
        with patch('builtins.print') as mock_print:
            parser = factory.create_parser(None)
            
            assert parser is None
            mock_print.assert_called_once_with("Skipping record with missing event type")

    def test_create_parser_nan_event_type(self, factory):
        """Test creating a parser with NaN event type."""
        with patch('builtins.print') as mock_print:
            parser = factory.create_parser(pd.NA)
            
            assert parser is None
            mock_print.assert_called_once_with("Skipping record with missing event type")

    def test_create_parser_non_string_event_type(self, factory, mock_parser_class):
        """Test creating a parser with non-string event type."""
        event_type = 123
        factory.register_parser("123", mock_parser_class)
        
        with patch('builtins.print') as mock_print:
            parser = factory.create_parser(event_type)
            
            assert parser is not None
            mock_print.assert_called_once_with("Converted non-string event type to string: 123")

    def test_create_parser_no_matching_parser(self, factory, mock_parser_class_false):
        """Test creating a parser when no registered parser can handle the event type."""
        event_type = "test_event"
        factory.register_parser("different_event", mock_parser_class_false)
        
        with patch('builtins.print') as mock_print:
            parser = factory.create_parser(event_type)
            
            assert parser is None
            mock_print.assert_called_once_with(f"No parser found for event type: {event_type}")

    def test_create_parser_multiple_registered_parsers(self, factory, mock_parser_class_false, mock_parser_class):
        """Test creating a parser with multiple registered parsers."""
        event_type = "test_event"
        factory.register_parser("parser1", mock_parser_class_false)
        factory.register_parser("parser2", mock_parser_class)
        
        parser = factory.create_parser(event_type)
        
        assert parser is not None
        assert parser == mock_parser_class.return_value
        # Should test both parsers
        mock_parser_class_false.assert_called_once()
        mock_parser_class.assert_called_once()

    def test_create_parser_can_parse_method(self, factory, mock_parser_class):
        """Test that can_parse method is called correctly."""
        event_type = "test_event"
        factory.register_parser("registered_type", mock_parser_class)
        
        parser = factory.create_parser(event_type)
        
        assert parser is not None
        mock_parser_class.return_value.can_parse.assert_called_once_with(event_type)

    def test_create_parser_empty_registry(self, factory):
        """Test creating a parser with empty registry."""
        with patch('builtins.print') as mock_print:
            parser = factory.create_parser("test_event")
            
            assert parser is None
            mock_print.assert_called_once_with("No parser found for event type: test_event")

    def test_register_multiple_parsers(self, factory, mock_parser_class):
        """Test registering multiple parsers."""
        factory.register_parser("event1", mock_parser_class)
        factory.register_parser("event2", mock_parser_class)
        
        assert len(factory.parser_classes) == 2
        assert "event1" in factory.parser_classes
        assert "event2" in factory.parser_classes

    def test_register_parser_overwrite(self, factory, mock_parser_class):
        """Test that registering a parser overwrites existing registration."""
        new_parser_class = Mock(spec=EventParser)
        
        factory.register_parser("test_event", mock_parser_class)
        factory.register_parser("test_event", new_parser_class)
        
        assert factory.parser_classes["test_event"] == new_parser_class