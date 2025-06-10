"""Evapotranspiration calculation functions.

RTGS Lab, 2024
Migrated from rtgsET library

This module implements the Penman-Monteith equation for calculating
reference evapotranspiration (ET) for alfalfa (ETo) and grass (ETr).
"""

from datetime import datetime
from typing import Any, Dict

import numpy as np
import pandas as pd


def calculate_reference_et(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate reference evapotranspiration using the Penman-Monteith equation.

    This function takes a DataFrame with meteorological data and adds columns
    for ETo (reference ET for alfalfa) and ETr (reference ET for grass).

    Args:
        df: DataFrame containing required meteorological columns:
            - Date: ISO 8601 format date string
            - Tmax_C: Maximum temperature (°C)
            - Tmin_C: Minimum temperature (°C)
            - T_dew_C: Dew point temperature (°C)
            - U3_m_s-1: Wind speed at 3m height (m/s)
            - Rs_W_m2: Solar radiation (W/m²)
            - Elevation_m: Elevation (meters)
            - Latitude_rad: Latitude (radians)

    Returns:
        DataFrame with added columns:
            - ETo (in/day): Reference ET for alfalfa (inches/day)
            - ETr (in/day): Reference ET for grass (inches/day)

    Reference:
        Penman-Monteith equation as implemented by A. Ayoub
        Requires Date in ISO 8601 format
    """
    # Create a copy to avoid modifying the original
    df = df.copy()

    # Helper function for Julian day calculation
    def day_of_year(row):
        try:
            date_object = datetime.fromisoformat(row["Date"])
            return date_object.timetuple().tm_yday
        except ValueError:
            print("Invalid ISO date format")
            return None

    # Julian Date (day of year)
    df["Julian Date (day)"] = df.apply(day_of_year, axis=1)

    # U2 (Wind Speed at 2m) in meters per second (m/s)
    df["U2 (m/s)"] = df["U3_m_s-1"] * (4.87 / np.log(67.8 * 3 - 5.42))

    # Rs (Solar Radiation) in MegaJoules per square meter per day (MJ/m²/day)
    df["Rs (MJ/m²/day)"] = df["Rs_W_m2"] * 0.0864

    # Tavg (Average Temperature) in degrees Celsius (°C)
    df["Tavg (°C)"] = (df["Tmax_C"] + df["Tmin_C"]) / 2
    df["Tavg (°C)"] = pd.to_numeric(df["Tavg (°C)"], errors="raise")

    # Lambda (λ) in MegaJoules per kilogram (MJ/kg)
    df["Lambda (MJ/kg)"] = 2.501 - (2.361e-3 * df["Tavg (°C)"])

    # P (Atmospheric Pressure) in kiloPascals (kPa)
    df["P (kPa)"] = 101.3 * ((293 - 0.0065 * df["Elevation_m"]) / 293) ** 5.26

    # Gamma (ϒ) in kiloPascals per degree Celsius (kPa/°C)
    df["Gamma (kPa/°C)"] = (1.013 * 1e-3 * df["P (kPa)"]) / (
        0.622 * df["Lambda (MJ/kg)"]
    )

    # Delta (∆) in kiloPascals per degree Celsius (kPa/°C)
    df["Delta (kPa/°C)"] = (
        4098 * (0.6108 * np.exp(17.27 * df["Tavg (°C)"] / (df["Tavg (°C)"] + 237.3)))
    ) / ((df["Tavg (°C)"] + 237.3) ** 2)

    # eᵒ(Tmax) (Saturation Vapor Pressure at Tmax) in kiloPascals (kPa)
    df["eᵒ(Tmax) (kPa)"] = 0.6108 * np.exp(
        17.27 * df["Tmax_C"] / (df["Tmax_C"] + 237.3)
    )

    # eᵒ(Tmin) (Saturation Vapor Pressure at Tmin) in kiloPascals (kPa)
    df["eᵒ(Tmin) (kPa)"] = 0.6108 * np.exp(
        17.27 * df["Tmin_C"] / (df["Tmin_C"] + 237.3)
    )

    # eᵒs (Average Saturation Vapor Pressure) in kiloPascals (kPa)
    df["eᵒs (kPa)"] = (df["eᵒ(Tmax) (kPa)"] + df["eᵒ(Tmin) (kPa)"]) / 2

    # eᵒa (Actual Vapor Pressure) in kiloPascals (kPa)
    df["eᵒa (kPa)"] = 0.6108 * np.exp(17.27 * df["T_dew_C"] / (df["T_dew_C"] + 237.3))

    # VPD (Vapor Pressure Deficit) in kiloPascals (kPa)
    df["VPD (kPa)"] = df["eᵒs (kPa)"] - df["eᵒa (kPa)"]

    # dr (Inverse Relative Distance Earth-Sun)
    df["Inverse Relative Distance Earth-Sun"] = 1 + 0.033 * np.cos(
        2 * np.pi * df["Julian Date (day)"] / 365
    )

    # δ (Solar Declination) in radians (rad)
    df["Solar Declination (rad)"] = 0.409 * np.sin(
        (2 * np.pi * df["Julian Date (day)"] / 365) - 1.39
    )

    # ωs (Sunset Hour Angle) in radians (rad)
    df["Sunset Hour Angle (rad)"] = np.arccos(
        -np.tan(df["Latitude_rad"]) * np.tan(df["Solar Declination (rad)"])
    )

    # Ra (Extraterrestrial Radiation) in MegaJoules per square meter per day (MJ/m²/day)
    df["Ra (MJ/m²/day)"] = (
        (24 * 60 / np.pi)
        * 0.082
        * df["Inverse Relative Distance Earth-Sun"]
        * (
            df["Sunset Hour Angle (rad)"]
            * np.sin(df["Latitude_rad"])
            * np.sin(df["Solar Declination (rad)"])
            + (
                np.cos(df["Latitude_rad"])
                * np.cos(df["Solar Declination (rad)"])
                * np.sin(df["Sunset Hour Angle (rad)"])
            )
        )
    )

    # Rso (Clear Sky Solar Radiation) in MegaJoules per square meter per day (MJ/m²/day)
    df["Rso (MJ/m²/day)"] = (0.75 + 2e-5 * df["Elevation_m"]) * df["Ra (MJ/m²/day)"]

    # Rns (Net Solar Radiation) in MegaJoules per square meter per day (MJ/m²/day)
    df["Rns (MJ/m²/day)"] = (1 - 0.23) * df["Rs (MJ/m²/day)"]  # using alfalfa albedo

    # Rnl (Net Longwave Radiation) in MegaJoules per square meter per day (MJ/m²/day)
    df["Rnl (MJ/m²/day)"] = (
        (
            4.903e-9
            * ((df["Tavg (°C)"] + 273.16) ** 4 + (df["Tmin_C"] + 273.16) ** 4)
            / 2
        )
        * (0.34 - 0.14 * np.sqrt(df["eᵒa (kPa)"]))
        * ((1.35 * np.minimum(df["Rs (MJ/m²/day)"] / df["Rso (MJ/m²/day)"], 1) - 0.35))
    )

    # Rn (Net Radiation) in MegaJoules per square meter per day (MJ/m²/day)
    df["Rn (MJ/m²/day)"] = df["Rns (MJ/m²/day)"] - df["Rnl (MJ/m²/day)"]

    # ETo (Reference Evapotranspiration for alfalfa) in inches per day (in/day)
    df["ETo (in/day)"] = (
        (
            0.408 * df["Delta (kPa/°C)"] * df["Rn (MJ/m²/day)"]
            + df["Gamma (kPa/°C)"]
            * (900 / (df["Tavg (°C)"] + 273))
            * df["U2 (m/s)"]
            * df["VPD (kPa)"]
        )
        / (df["Delta (kPa/°C)"] + df["Gamma (kPa/°C)"] * (1 + 0.34 * df["U2 (m/s)"]))
        * 0.0393701
    )

    # ETr (Reference Evapotranspiration for grass) in inches per day (in/day)
    df["ETr (in/day)"] = (
        (
            0.408 * df["Delta (kPa/°C)"] * df["Rn (MJ/m²/day)"]
            + df["Gamma (kPa/°C)"]
            * (1600 / (df["Tavg (°C)"] + 273))
            * df["U2 (m/s)"]
            * df["VPD (kPa)"]
        )
        / (df["Delta (kPa/°C)"] + df["Gamma (kPa/°C)"] * (1 + 0.38 * df["U2 (m/s)"]))
        * 0.0393701
    )

    # Clean up intermediate columns
    intermediate_cols = [
        "Julian Date (day)",
        "U2 (m/s)",
        "Rs (MJ/m²/day)",
        "Tavg (°C)",
        "Lambda (MJ/kg)",
        "P (kPa)",
        "Gamma (kPa/°C)",
        "Delta (kPa/°C)",
        "eᵒ(Tmax) (kPa)",
        "eᵒ(Tmin) (kPa)",
        "eᵒs (kPa)",
        "eᵒa (kPa)",
        "VPD (kPa)",
        "Inverse Relative Distance Earth-Sun",
        "Solar Declination (rad)",
        "Sunset Hour Angle (rad)",
        "Ra (MJ/m²/day)",
        "Rso (MJ/m²/day)",
        "Rns (MJ/m²/day)",
        "Rnl (MJ/m²/day)",
        "Rn (MJ/m²/day)",
    ]

    df.drop(columns=intermediate_cols, inplace=True)

    return df


def get_required_columns() -> Dict[str, str]:
    """Get the required column names and descriptions for ET calculation.

    Returns:
        Dictionary mapping column names to their descriptions
    """
    return {
        "Date": "ISO 8601 format date string (YYYY-MM-DD)",
        "Tmax_C": "Maximum temperature (°C)",
        "Tmin_C": "Minimum temperature (°C)",
        "T_dew_C": "Dew point temperature (°C)",
        "U3_m_s-1": "Wind speed at 3m height (m/s)",
        "Rs_W_m2": "Solar radiation (W/m²)",
        "Elevation_m": "Elevation (meters)",
        "Latitude_rad": "Latitude (radians)",
    }


def validate_input_data(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate input DataFrame for ET calculation.

    Args:
        df: DataFrame to validate

    Returns:
        Dictionary with validation results:
            - valid: Boolean indicating if data is valid
            - missing_columns: List of missing required columns
            - errors: List of validation error messages
    """
    required_cols = get_required_columns()
    missing_cols = []
    errors = []

    # Check for required columns
    for col in required_cols:
        if col not in df.columns:
            missing_cols.append(col)

    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")

    # Check for non-numeric columns (except Date)
    if not missing_cols:
        numeric_cols = [col for col in required_cols if col != "Date"]
        for col in numeric_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                errors.append(f"Column '{col}' must be numeric")

    # Check for empty data
    if len(df) == 0:
        errors.append("DataFrame is empty")

    return {
        "valid": len(errors) == 0,
        "missing_columns": missing_cols,
        "errors": errors,
    }
