"""Weather data fetching utilities for GEMS API.

RTGS Lab, 2024
Migrated from rtgsET library
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import pandas as pd
import requests


def date_chunks(
    start_date: str, end_date: str, chunk_size: int = 365
) -> List[Tuple[str, str]]:
    """Split date ranges into chunks of specified days.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        chunk_size: Number of days per chunk (default: 365)

    Yields:
        Tuples of (chunk_start_date, chunk_end_date) strings
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    chunk = timedelta(days=chunk_size)

    chunks = []
    while start < end:
        chunk_end = min(start + chunk, end)
        chunks.append((start.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
        start = chunk_end + timedelta(days=0)

    return chunks


def fetch_weather_data(
    url: str,
    headers: dict,
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    chunk_size: int = 365,
) -> pd.DataFrame:
    """Fetch weather data from GEMS API and return as DataFrame.

    Args:
        url: API endpoint URL (typically GEMS weather API)
        headers: HTTP headers for authentication
        lat: Latitude coordinate
        lon: Longitude coordinate
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        chunk_size: Number of days per API call (default: 365)

    Returns:
        DataFrame containing weather data from all date chunks

    Raises:
        requests.RequestException: If API calls fail
        ValueError: If response format is unexpected
    """
    # Initialize an empty DataFrame to store the results
    all_data = pd.DataFrame()

    # Adjust the end_date to include the original end_date in the API call
    adjusted_end_date = (
        datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    # Loop through each date chunk
    chunks = date_chunks(start_date, adjusted_end_date, chunk_size=chunk_size)

    for start, end in chunks:
        params = {"lat": lat, "lon": lon, "start_date": start, "end_date": end}

        # Make the GET request
        response = requests.get(
            url="https://exchange-1.gems.msi.umn.edu/weather/v2/history/daily",
            headers=headers,
            params=params,
        )

        # Check the response status and append the data if successful
        if response.status_code == 200:
            data = response.json()

            # Assuming the daily weather data is in a list named "data" in the JSON response
            if "data" in data:
                df = pd.DataFrame(data["data"])
                all_data = pd.concat([all_data, df], ignore_index=True)
            else:
                print(f"No 'data' found for range {start} to {end}.")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            raise requests.RequestException(
                f"API call failed: {response.status_code} - {response.text}"
            )

    return all_data


def check_missing_dates(
    df: pd.DataFrame, start_date: str, end_date: str, date_column: str
) -> Optional[List[str]]:
    """Check if all dates are present in the DataFrame.

    Args:
        df: DataFrame containing date data
        start_date: Expected start date in YYYY-MM-DD format
        end_date: Expected end date in YYYY-MM-DD format
        date_column: Name of the date column to check

    Returns:
        List of missing dates (sorted) or None if all dates are present
    """
    # Generate a full list of expected dates
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    all_dates = pd.date_range(start=start, end=end).strftime("%Y-%m-%d").tolist()

    # Convert the date column in the DataFrame to string format for comparison
    df[date_column] = pd.to_datetime(df[date_column]).dt.strftime("%Y-%m-%d")

    # Find any missing dates
    df_dates = df[date_column].tolist()
    missing_dates = set(all_dates) - set(df_dates)

    if missing_dates:
        # Sort the missing dates
        sorted_missing_dates = sorted(missing_dates)
        print(f"Missing dates (sorted): {sorted_missing_dates}")
        return sorted_missing_dates

    print("All dates are accounted for.")
    return None


def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude and longitude coordinates.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Returns:
        True if coordinates are valid, False otherwise
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180


def validate_date_range(start_date: str, end_date: str) -> bool:
    """Validate date range format and logic.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        True if date range is valid, False otherwise
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        return start <= end
    except ValueError:
        return False
