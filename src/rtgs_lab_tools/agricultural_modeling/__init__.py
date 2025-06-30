"""Unit conversion and small deterministic model tools for RTGS Lab.

This module provides functions for:
- Temperature conversions (Celsius ↔ Fahrenheit)
- Distance and angle conversions (feet to meters, degrees to radians)
- Speed conversions (m/s ↔ mph)
- Agricultural crop parameters and calculations
- Growing Degree Day (GDD) calculations
- Corn Heat Units (CHU) calculations

Migrated from rtgsET library.
"""

from .crop_parameters import get_crop_names, get_crop_parameters, get_crop_status
from .distance_speed import (
    degrees_to_radians,
    feet_to_meters,
    meters_per_second_to_miles_per_hour,
    miles_per_hour_to_meters_per_second,
)
from .evapotranspiration import (
    calculate_reference_et,
    get_required_columns,
    validate_input_data,
)
from .growing_degree_days import (
    calculate_corn_heat_units,
    calculate_gdd_modified,
    calculate_gdd_original,
)
from .temperature import celsius_to_fahrenheit, fahrenheit_to_celsius
from .weather_api import (
    check_missing_dates,
    date_chunks,
    fetch_weather_data,
    validate_coordinates,
    validate_date_range,
)

__all__ = [
    # Temperature conversions
    "celsius_to_fahrenheit",
    "fahrenheit_to_celsius",
    # Distance and speed conversions
    "degrees_to_radians",
    "feet_to_meters",
    "meters_per_second_to_miles_per_hour",
    "miles_per_hour_to_meters_per_second",
    # Crop parameters
    "get_crop_parameters",
    "get_crop_names",
    "get_crop_status",
    # Growing degree days
    "calculate_gdd_original",
    "calculate_gdd_modified",
    "calculate_corn_heat_units",
    # Evapotranspiration
    "calculate_reference_et",
    "get_required_columns",
    "validate_input_data",
    # Weather API utilities
    "date_chunks",
    "fetch_weather_data",
    "check_missing_dates",
    "validate_coordinates",
    "validate_date_range",
]
