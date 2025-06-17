"""RTGS Lab Tools - Environmental sensing and climate data toolkit."""

__version__ = "0.1.0"
__author__ = "RTGS Lab"
__email__ = "rtgs@umn.edu"

# Core infrastructure
from .core import Config, DatabaseManager
from .core.exceptions import APIError, DatabaseError, ValidationError
from .core.postgres_logger import PostgresLogger

# Device management
from .device_configuration import ParticleClient, ParticleConfigUpdater

# Error analysis
from .error_analysis import ErrorCodeParser

# Climate data
from .gridded_data import ERA5Client, download_era5_data, process_era5_data

# High-level data extraction functions
from .sensing_data import extract_data, get_raw_data, list_available_projects

# Data parsing functions
from .data_parser.parsers.factory import ParserFactory
from .data_parser.parsers.data_parser import DataV2Parser

# Visualization functions
from .visualization import (
    create_multi_parameter_plot,
    create_time_series_plot,
    detect_data_type,
    load_and_prepare_data,
)

__all__ = [
    # Core
    "DatabaseManager",
    "Config",
    "PostgresLogger",
    "ValidationError",
    "DatabaseError",
    "APIError",
    # Data extraction
    "extract_data",
    "list_available_projects",
    "get_raw_data",
    # Data parsing
    "ParserFactory",
    "DataV2Parser",
    # Visualization
    "create_time_series_plot",
    "create_multi_parameter_plot",
    "detect_data_type",
    "load_and_prepare_data",
    # Device management
    "ParticleConfigUpdater",
    "ParticleClient",
    "ErrorCodeParser",
    # Climate data
    "ERA5Client",
    "download_era5_data",
    "process_era5_data",
]
