"""Tests for visualization data parser."""

import json
from datetime import datetime

import pandas as pd
import pytest

from rtgs_lab_tools.core.exceptions import ValidationError
from rtgs_lab_tools.visualization.data_parser import (
    extract_parameter_from_json,
    extract_time_series_data,
    get_available_parameters,
    parse_sensor_messages,
)


@pytest.fixture
def sample_sensor_data():
    """Sample sensor data with JSON messages."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "node_id": ["node_001", "node_001", "node_002", "node_002"],
            "publish_time": [
                "2023-01-01 10:00:00",
                "2023-01-01 11:00:00",
                "2023-01-01 10:30:00",
                "2023-01-01 11:30:00",
            ],
            "message": [
                '{"Data": {"Devices": {"0": {"Temperature": 22.5, "Humidity": 65}}}}',
                '{"Data": {"Devices": {"0": {"Temperature": 23.1, "Humidity": 62}}}}',
                '{"Data": {"Devices": {"1": {"Pressure": 1013.2, "Light": 450}}}}',
                '{"Diagnostic": {"Battery": {"Voltage": 3.7, "Level": 85}}}',
            ],
        }
    )


def test_parse_sensor_messages(sample_sensor_data):
    """Test parsing JSON messages in sensor data."""
    result = parse_sensor_messages(sample_sensor_data)

    assert len(result) == 4
    assert "parsed_message" in result.columns
    assert "timestamp" in result.columns

    # Check first message is parsed correctly
    first_msg = result.iloc[0]["parsed_message"]
    assert first_msg["Data"]["Devices"]["0"]["Temperature"] == 22.5


def test_parse_sensor_messages_invalid_json():
    """Test parsing with invalid JSON messages."""
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "node_id": ["node_001", "node_002"],
            "publish_time": ["2023-01-01 10:00:00", "2023-01-01 11:00:00"],
            "message": ['{"valid": "json"}', "invalid json"],
        }
    )

    result = parse_sensor_messages(df)

    # Should only return valid entries
    assert len(result) == 1
    assert result.iloc[0]["parsed_message"]["valid"] == "json"


def test_parse_sensor_messages_missing_column():
    """Test parsing with missing message column."""
    df = pd.DataFrame({"id": [1], "node_id": ["node_001"]})

    with pytest.raises(ValidationError, match="DataFrame must have 'message' column"):
        parse_sensor_messages(df)


def test_extract_parameter_from_json():
    """Test parameter extraction from JSON data."""
    data = {
        "Data": {
            "Devices": {
                "0": {"Temperature": 22.5, "Sensors": [{"value": 100}, {"value": 200}]}
            }
        }
    }

    # Test nested object access
    temp = extract_parameter_from_json(data, "Data.Devices.0.Temperature")
    assert temp == 22.5

    # Test array access
    sensor_value = extract_parameter_from_json(data, "Data.Devices.0.Sensors.1.value")
    assert sensor_value == 200

    # Test non-existent path
    missing = extract_parameter_from_json(data, "Data.NonExistent.Path")
    assert missing is None


def test_get_available_parameters(sample_sensor_data):
    """Test getting available parameters from sensor data."""
    parsed_df = parse_sensor_messages(sample_sensor_data)
    parameters = get_available_parameters(parsed_df)

    assert "node_001" in parameters
    assert "node_002" in parameters

    # Check some expected parameters
    node_001_params = parameters["node_001"]
    assert "Data.Devices.0.Temperature" in node_001_params
    assert "Data.Devices.0.Humidity" in node_001_params

    node_002_params = parameters["node_002"]
    assert (
        "Data.Devices.1.Pressure" in node_002_params
        or "Diagnostic.Battery.Voltage" in node_002_params
    )


def test_extract_time_series_data(sample_sensor_data):
    """Test extracting time series data for plotting."""
    parsed_df = parse_sensor_messages(sample_sensor_data)

    # Extract temperature data for node_001
    time_series = extract_time_series_data(
        parsed_df, "Data.Devices.0.Temperature", node_ids=["node_001"]
    )

    assert "node_001" in time_series
    node_data = time_series["node_001"]

    assert len(node_data) == 2  # Two temperature readings
    assert "timestamp" in node_data.columns
    assert "value" in node_data.columns
    assert "parameter" in node_data.columns
    assert "node_id" in node_data.columns

    # Check values
    assert node_data["value"].tolist() == [22.5, 23.1]


def test_extract_time_series_data_no_parsed_messages():
    """Test extracting time series data without parsed messages."""
    df = pd.DataFrame({"node_id": ["node_001"], "timestamp": [datetime.now()]})

    with pytest.raises(
        ValidationError, match="DataFrame must have 'parsed_message' column"
    ):
        extract_time_series_data(df, "Data.Temperature")
