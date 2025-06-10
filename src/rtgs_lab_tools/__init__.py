"""RTGS Lab Tools - Environmental sensing and climate data toolkit."""

__version__ = "0.1.0"
__author__ = "RTGS Lab"
__email__ = "rtgs@umn.edu"

# Core infrastructure
from .core import Config, DatabaseManager
from .core.exceptions import APIError, DatabaseError, ValidationError
from .core.git_logger import GitLogger

# Device management
from .device_configuration import ParticleClient, ParticleConfigUpdater

# Error analysis
from .error_analysis import ErrorCodeParser

# Climate data
from .gridded_data import ERA5Client, download_era5_data, process_era5_data

# High-level data extraction functions
from .sensing_data import extract_data, get_raw_data, list_available_projects

# Visualization functions
from .visualization import (
    create_multi_parameter_plot,
    create_time_series_plot,
    parse_sensor_messages,
)

__all__ = [
    # Core
    "DatabaseManager",
    "Config",
    "GitLogger",
    "ValidationError",
    "DatabaseError",
    "APIError",
    # Data extraction
    "extract_data",
    "list_available_projects",
    "get_raw_data",
    # Visualization
    "create_time_series_plot",
    "create_multi_parameter_plot",
    "parse_sensor_messages",
    # Device management
    "ParticleConfigUpdater",
    "ParticleClient",
    "ErrorCodeParser",
    # Climate data
    "ERA5Client",
    "download_era5_data",
    "process_era5_data",
]
