"""Tests for visualization data utilities."""

import pandas as pd
import pytest
from unittest.mock import Mock, patch

from rtgs_lab_tools.visualization.data_utils import (
    parse_measurement_spec,
    extract_array_value,
    detect_data_type,
    get_available_measurements,
    filter_parsed_data,
    _detect_array_length,
)


class TestParseMeasurementSpec:
    """Test the measurement specification parsing function."""

    def test_parse_simple_measurement(self):
        """Test parsing simple measurement without array index."""
        name, index = parse_measurement_spec("Temperature")
        assert name == "Temperature"
        assert index is None

    def test_parse_measurement_with_index(self):
        """Test parsing measurement with array index."""
        name, index = parse_measurement_spec("PORT_V[0]")
        assert name == "PORT_V"
        assert index == 0

    def test_parse_measurement_with_higher_index(self):
        """Test parsing measurement with higher array index."""
        name, index = parse_measurement_spec("PORT_I[15]")
        assert name == "PORT_I"
        assert index == 15

    def test_parse_measurement_with_spaces(self):
        """Test parsing measurement with spaces."""
        name, index = parse_measurement_spec("  Temperature  ")
        assert name == "Temperature"
        assert index is None

    def test_parse_measurement_with_spaces_and_index(self):
        """Test parsing measurement with spaces and array index."""
        name, index = parse_measurement_spec("  PORT_V[3]  ")
        assert name == "PORT_V"
        assert index == 3

    def test_parse_measurement_with_underscore(self):
        """Test parsing measurement with underscore in name."""
        name, index = parse_measurement_spec("BATTERY_VOLTAGE[1]")
        assert name == "BATTERY_VOLTAGE"
        assert index == 1

    def test_parse_invalid_measurement_spec(self):
        """Test parsing invalid measurement specification."""
        with pytest.raises(ValueError) as excinfo:
            parse_measurement_spec("Invalid[spec")
        assert "Invalid measurement specification" in str(excinfo.value)

    def test_parse_empty_measurement_spec(self):
        """Test parsing empty measurement specification."""
        with pytest.raises(ValueError) as excinfo:
            parse_measurement_spec("")
        assert "Invalid measurement specification" in str(excinfo.value)

    def test_parse_measurement_with_negative_index(self):
        """Test parsing measurement with negative index."""
        with pytest.raises(ValueError) as excinfo:
            parse_measurement_spec("PORT_V[-1]")
        assert "Invalid measurement specification" in str(excinfo.value)


class TestExtractArrayValue:
    """Test the array value extraction function."""

    def test_extract_from_list(self):
        """Test extracting value from list."""
        result = extract_array_value([1.0, 2.0, 3.0], 1)
        assert result == 2.0

    def test_extract_from_list_out_of_bounds(self):
        """Test extracting value from list with out of bounds index."""
        result = extract_array_value([1.0, 2.0, 3.0], 5)
        assert result is None

    def test_extract_from_string_array(self):
        """Test extracting value from string representation of array."""
        result = extract_array_value("[1.5, 2.5, 3.5]", 1)
        assert result == 2.5

    def test_extract_from_string_array_with_spaces(self):
        """Test extracting value from string array with spaces."""
        result = extract_array_value("[ 1.5 , 2.5 , 3.5 ]", 2)
        assert result == 3.5

    def test_extract_from_string_array_integers(self):
        """Test extracting value from string array with integers."""
        result = extract_array_value("[10, 20, 30]", 0)
        assert result == 10

    def test_extract_from_empty_string_array(self):
        """Test extracting value from empty string array."""
        result = extract_array_value("[]", 0)
        assert result is None

    def test_extract_from_scalar_index_zero(self):
        """Test extracting value from scalar with index 0."""
        result = extract_array_value(42.5, 0)
        assert result == 42.5

    def test_extract_from_scalar_index_nonzero(self):
        """Test extracting value from scalar with non-zero index."""
        result = extract_array_value(42.5, 1)
        assert result is None

    def test_extract_from_none_value(self):
        """Test extracting value from None."""
        result = extract_array_value(None, 0)
        assert result is None

    def test_extract_from_nan_value(self):
        """Test extracting value from NaN."""
        result = extract_array_value(pd.NA, 0)
        assert result is None

    def test_extract_from_invalid_string(self):
        """Test extracting value from invalid string."""
        result = extract_array_value("not an array", 0)
        assert result == "not an array"

    def test_extract_from_malformed_string_array(self):
        """Test extracting value from malformed string array."""
        result = extract_array_value("[1.5, invalid, 3.5]", 1)
        assert result == "invalid"  # Keep as string when conversion fails


class TestDetectDataType:
    """Test the data type detection function."""

    def test_detect_parsed_data(self):
        """Test detecting parsed data format."""
        df = pd.DataFrame({
            'device_type': ['sensor'],
            'measurement_name': ['Temperature'],
            'measurement_path': ['Data.Temperature'],
            'value': [25.0],
            'unit': ['°C'],
            'timestamp': ['2023-01-01T00:00:00'],
            'node_id': ['node_001'],
            'event_type': ['data']
        })
        
        result = detect_data_type(df)
        assert result == "parsed"

    def test_detect_raw_data(self):
        """Test detecting raw data format."""
        df = pd.DataFrame({
            'event': ['temperature'],
            'message': ['{"temp": 25.0}'],
            'publish_time': ['2023-01-01T00:00:00'],
            'node_id': ['node_001']
        })
        
        result = detect_data_type(df)
        assert result == "raw"

    def test_detect_unknown_data(self):
        """Test detecting unknown data format."""
        df = pd.DataFrame({
            'random_column': ['value'],
            'another_column': ['data']
        })
        
        result = detect_data_type(df)
        assert result == "unknown"

    def test_detect_partial_parsed_data(self):
        """Test detecting partial parsed data format."""
        df = pd.DataFrame({
            'device_type': ['sensor'],
            'measurement_name': ['Temperature'],
            'value': [25.0],
            'timestamp': ['2023-01-01T00:00:00'],
            'node_id': ['node_001']
        })
        
        result = detect_data_type(df)
        assert result == "unknown"  # Less than 6 matching columns

    def test_detect_case_insensitive(self):
        """Test that detection is case insensitive."""
        df = pd.DataFrame({
            'EVENT': ['temperature'],
            'MESSAGE': ['{"temp": 25.0}'],
            'PUBLISH_TIME': ['2023-01-01T00:00:00'],
            'NODE_ID': ['node_001']
        })
        
        result = detect_data_type(df)
        assert result == "raw"


class TestGetAvailableMeasurements:
    """Test the available measurements function."""

    def test_get_basic_measurements(self):
        """Test getting basic measurements without arrays."""
        df = pd.DataFrame({
            'node_id': ['node_001', 'node_001', 'node_002'],
            'measurement_name': ['Temperature', 'Humidity', 'Temperature'],
            'value': [25.0, 60.0, 23.0]
        })
        
        result = get_available_measurements(df)
        
        assert 'node_001' in result
        assert 'node_002' in result
        assert 'Temperature' in result['node_001']
        assert 'Humidity' in result['node_001']
        assert 'Temperature' in result['node_002']

    def test_get_measurements_with_arrays(self):
        """Test getting measurements with array values."""
        df = pd.DataFrame({
            'node_id': ['node_001', 'node_001', 'node_001'],
            'measurement_name': ['PORT_V', 'PORT_V', 'Temperature'],
            'value': ['[1.0, 2.0, 3.0]', '[1.1, 2.1, 3.1]', 25.0]
        })
        
        result = get_available_measurements(df)
        
        assert 'node_001' in result
        assert 'PORT_V' in result['node_001']
        assert 'PORT_V[0]' in result['node_001']
        assert 'PORT_V[1]' in result['node_001']
        assert 'PORT_V[2]' in result['node_001']
        assert 'Temperature' in result['node_001']

    def test_get_measurements_missing_columns(self):
        """Test error when required columns are missing."""
        df = pd.DataFrame({
            'wrong_column': ['value']
        })
        
        with pytest.raises(ValueError) as excinfo:
            get_available_measurements(df)
        assert "must have 'node_id' and 'measurement_name' columns" in str(excinfo.value)

    def test_get_measurements_empty_dataframe(self):
        """Test with empty dataframe."""
        df = pd.DataFrame({
            'node_id': [],
            'measurement_name': [],
            'value': []
        })
        
        result = get_available_measurements(df)
        assert result == {}

    def test_get_measurements_with_nan_values(self):
        """Test handling NaN values in measurement names."""
        df = pd.DataFrame({
            'node_id': ['node_001', 'node_001'],
            'measurement_name': ['Temperature', None],
            'value': [25.0, 60.0]
        })
        
        result = get_available_measurements(df)
        
        assert 'node_001' in result
        assert 'Temperature' in result['node_001']
        assert len(result['node_001']) == 1  # NaN measurement should be filtered out


class TestDetectArrayLength:
    """Test the array length detection function."""

    def test_detect_list_length(self):
        """Test detecting length of list."""
        assert _detect_array_length([1, 2, 3, 4]) == 4

    def test_detect_string_array_length(self):
        """Test detecting length of string array."""
        assert _detect_array_length("[1, 2, 3]") == 3

    def test_detect_empty_array_length(self):
        """Test detecting length of empty array."""
        assert _detect_array_length("[]") == 0

    def test_detect_single_value_length(self):
        """Test detecting length of single value."""
        assert _detect_array_length(42) == 1

    def test_detect_none_length(self):
        """Test detecting length of None."""
        assert _detect_array_length(None) == 0

    def test_detect_nan_length(self):
        """Test detecting length of NaN."""
        assert _detect_array_length(pd.NA) == 0

    def test_detect_malformed_string_length(self):
        """Test detecting length of malformed string."""
        assert _detect_array_length("not an array") == 1


class TestFilterParsedData:
    """Test the parsed data filtering function."""

    def test_filter_basic_measurement(self):
        """Test filtering basic measurement."""
        df = pd.DataFrame({
            'node_id': ['node_001', 'node_001', 'node_002'],
            'measurement_name': ['Temperature', 'Humidity', 'Temperature'],
            'value': [25.0, 60.0, 23.0]
        })
        
        result = filter_parsed_data(df, "Temperature")
        
        assert len(result) == 2
        assert all(result['measurement_name'] == 'Temperature')

    def test_filter_measurement_with_node_ids(self):
        """Test filtering measurement with specific node IDs."""
        df = pd.DataFrame({
            'node_id': ['node_001', 'node_001', 'node_002'],
            'measurement_name': ['Temperature', 'Temperature', 'Temperature'],
            'value': [25.0, 26.0, 23.0]
        })
        
        result = filter_parsed_data(df, "Temperature", node_ids=['node_001'])
        
        assert len(result) == 2
        assert all(result['node_id'] == 'node_001')

    def test_filter_array_measurement(self):
        """Test filtering array measurement with index."""
        df = pd.DataFrame({
            'node_id': ['node_001', 'node_001'],
            'measurement_name': ['PORT_V', 'PORT_V'],
            'value': ['[1.0, 2.0, 3.0]', '[1.1, 2.1, 3.1]'],
            'measurement_path': ['Data.PORT_V', 'Data.PORT_V']
        })
        
        result = filter_parsed_data(df, "PORT_V[1]")
        
        assert len(result) == 2
        assert list(result['value']) == [2.0, 2.1]
        assert all(result['measurement_path'].str.contains('[1]'))

    def test_filter_array_measurement_out_of_bounds(self):
        """Test filtering array measurement with out of bounds index."""
        df = pd.DataFrame({
            'node_id': ['node_001'],
            'measurement_name': ['PORT_V'],
            'value': ['[1.0, 2.0]']
        })
        
        result = filter_parsed_data(df, "PORT_V[5]")
        
        assert len(result) == 0  # Should be empty after filtering out None values

    def test_filter_nonexistent_measurement(self):
        """Test filtering non-existent measurement."""
        df = pd.DataFrame({
            'node_id': ['node_001'],
            'measurement_name': ['Temperature'],
            'value': [25.0]
        })
        
        result = filter_parsed_data(df, "Pressure")
        
        assert len(result) == 0

    def test_filter_empty_dataframe(self):
        """Test filtering empty dataframe."""
        df = pd.DataFrame({
            'node_id': [],
            'measurement_name': [],
            'value': []
        })
        
        result = filter_parsed_data(df, "Temperature")
        
        assert len(result) == 0