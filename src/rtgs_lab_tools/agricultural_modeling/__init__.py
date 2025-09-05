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

# Heavy dependencies are imported lazily when needed
# This prevents long load times for simple commands like 'rtgs --help'


def __getattr__(name):
    """Lazy loading of heavy dependencies"""
    # Crop parameters
    if name == "get_crop_names":
        from .crop_parameters import get_crop_names

        return get_crop_names
    elif name == "get_crop_parameters":
        from .crop_parameters import get_crop_parameters

        return get_crop_parameters
    elif name == "get_crop_status":
        from .crop_parameters import get_crop_status

        return get_crop_status
    # Distance and speed conversions
    elif name == "degrees_to_radians":
        from .distance_speed import degrees_to_radians

        return degrees_to_radians
    elif name == "feet_to_meters":
        from .distance_speed import feet_to_meters

        return feet_to_meters
    elif name == "meters_per_second_to_miles_per_hour":
        from .distance_speed import meters_per_second_to_miles_per_hour

        return meters_per_second_to_miles_per_hour
    elif name == "miles_per_hour_to_meters_per_second":
        from .distance_speed import miles_per_hour_to_meters_per_second

        return miles_per_hour_to_meters_per_second
    # Evapotranspiration (heavy numpy/pandas dependencies)
    elif name == "calculate_reference_et":
        from .evapotranspiration import calculate_reference_et

        return calculate_reference_et
    elif name == "get_required_columns":
        from .evapotranspiration import get_required_columns

        return get_required_columns
    elif name == "validate_input_data":
        from .evapotranspiration import validate_input_data

        return validate_input_data
    # Growing degree days
    elif name == "calculate_corn_heat_units":
        from .growing_degree_days import calculate_corn_heat_units

        return calculate_corn_heat_units
    elif name == "calculate_gdd_modified":
        from .growing_degree_days import calculate_gdd_modified

        return calculate_gdd_modified
    elif name == "calculate_gdd_original":
        from .growing_degree_days import calculate_gdd_original

        return calculate_gdd_original
    # Temperature conversions (lightweight)
    elif name == "celsius_to_fahrenheit":
        from .temperature import celsius_to_fahrenheit

        return celsius_to_fahrenheit
    elif name == "fahrenheit_to_celsius":
        from .temperature import fahrenheit_to_celsius

        return fahrenheit_to_celsius
    # Weather API utilities (requests dependency)
    elif name == "check_missing_dates":
        from .weather_api import check_missing_dates

        return check_missing_dates
    elif name == "date_chunks":
        from .weather_api import date_chunks

        return date_chunks
    elif name == "fetch_weather_data":
        from .weather_api import fetch_weather_data

        return fetch_weather_data
    elif name == "validate_coordinates":
        from .weather_api import validate_coordinates

        return validate_coordinates
    elif name == "validate_date_range":
        from .weather_api import validate_date_range

        return validate_date_range
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


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
