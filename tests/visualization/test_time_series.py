"""Tests for time series plotting functions."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from rtgs_lab_tools.core.exceptions import RTGSLabToolsError, ValidationError
from rtgs_lab_tools.visualization.time_series import (
    create_multi_parameter_plot,
    create_time_series_plot,
    plot_sensor_data,
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
                '{"Data": {"Devices": {"1": {"Temperature": 21.8, "Humidity": 68}}}}',
                '{"Data": {"Devices": {"1": {"Temperature": 22.2, "Humidity": 66}}}}',
            ],
        }
    )


def test_create_time_series_plot(sample_sensor_data, temp_output_dir):
    """Test creating a basic time series plot."""
    with patch("matplotlib.pyplot.show"):  # Prevent display
        output_path = create_time_series_plot(
            df=sample_sensor_data,
            parameter_path="Data.Devices.0.Temperature",
            node_ids=["node_001"],
            output_dir=temp_output_dir,
        )

    assert os.path.exists(output_path)
    assert output_path.endswith(".png")
    assert "Temperature" in output_path


def test_create_time_series_plot_multiple_nodes(sample_sensor_data, temp_output_dir):
    """Test creating time series plot with multiple nodes."""
    with patch("matplotlib.pyplot.show"):
        output_path = create_time_series_plot(
            df=sample_sensor_data,
            parameter_path="Data.Devices.0.Temperature",
            output_dir=temp_output_dir,
            title="Multi-Node Temperature",
        )

    assert os.path.exists(output_path)


def test_create_time_series_plot_no_data(sample_sensor_data, temp_output_dir):
    """Test creating plot with non-existent parameter."""
    with pytest.raises(RTGSLabToolsError, match="Time series plotting failed"):
        create_time_series_plot(
            df=sample_sensor_data,
            parameter_path="NonExistent.Parameter",
            output_dir=temp_output_dir,
        )


def test_create_multi_parameter_plot(sample_sensor_data, temp_output_dir):
    """Test creating multi-parameter plot."""
    parameters = [
        ("Data.Devices.0.Temperature", "node_001"),
        ("Data.Devices.1.Temperature", "node_002"),
    ]

    with patch("matplotlib.pyplot.show"):
        output_path = create_multi_parameter_plot(
            df=sample_sensor_data,
            parameters=parameters,
            output_dir=temp_output_dir,
            title="Temperature Comparison",
        )

    assert os.path.exists(output_path)
    assert output_path.endswith(".png")


def test_create_multi_parameter_plot_no_data(sample_sensor_data, temp_output_dir):
    """Test multi-parameter plot with no valid data."""
    parameters = [
        ("NonExistent.Parameter", "node_001"),
        ("Another.Missing.Parameter", "node_002"),
    ]

    with pytest.raises(RTGSLabToolsError, match="Multi-parameter plotting failed"):
        create_multi_parameter_plot(
            df=sample_sensor_data, parameters=parameters, output_dir=temp_output_dir
        )


def test_plot_sensor_data(sample_sensor_data, temp_output_dir):
    """Test simplified sensor data plotting function."""
    with patch("matplotlib.pyplot.show"):
        output_path = plot_sensor_data(
            df=sample_sensor_data,
            parameter_path="Data.Devices.0.Temperature",
            node_id="node_001",
            output_dir=temp_output_dir,
        )

    assert os.path.exists(output_path)


def test_plot_output_formats(sample_sensor_data, temp_output_dir):
    """Test different output formats."""
    formats = ["png", "pdf", "svg"]

    for fmt in formats:
        with patch("matplotlib.pyplot.show"):
            output_path = create_time_series_plot(
                df=sample_sensor_data,
                parameter_path="Data.Devices.0.Temperature",
                node_ids=["node_001"],
                output_dir=temp_output_dir,
                output_file=f"test_plot_{fmt}",
                format=fmt,
            )

        assert os.path.exists(output_path)
        assert output_path.endswith(f".{fmt}")


def test_plot_custom_figsize(sample_sensor_data, temp_output_dir):
    """Test plotting with custom figure size."""
    with patch("matplotlib.pyplot.show"):
        output_path = create_time_series_plot(
            df=sample_sensor_data,
            parameter_path="Data.Devices.0.Temperature",
            output_dir=temp_output_dir,
            figsize=(16, 10),
        )

    assert os.path.exists(output_path)
