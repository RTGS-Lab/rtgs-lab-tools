"""ERA5 climate data access using Copernicus CDS API."""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from ..core import Config
from ..core.exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)

try:
    import cdsapi
    import xarray as xr

    CDS_AVAILABLE = True
except ImportError:
    CDS_AVAILABLE = False
    logger.warning(
        "ERA5 functionality requires cdsapi and xarray. Install with: pip install rtgs-lab-tools[climate]"
    )


class ERA5Client:
    """Client for downloading ERA5 reanalysis data from Copernicus CDS."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize ERA5 client.

        Args:
            api_key: CDS API key. If None, reads from config.

        Raises:
            APIError: If CDS API is not available or configured
        """
        if not CDS_AVAILABLE:
            raise APIError("ERA5 functionality requires cdsapi and xarray packages")

        self.api_key = api_key or Config().cds_api_key
        if not self.api_key:
            raise APIError(
                "CDS API key not found. Set CDS_API_KEY environment variable or configure ~/.cdsapirc"
            )

        try:
            self.client = cdsapi.Client()
            logger.info("ERA5 client initialized successfully")
        except Exception as e:
            raise APIError(f"Failed to initialize CDS client: {e}")

    def download_era5_reanalysis(
        self,
        variables: List[str],
        start_date: str,
        end_date: str,
        area: Optional[List[float]] = None,
        output_file: Optional[str] = None,
        pressure_levels: Optional[List[int]] = None,
        time_hours: Optional[List[str]] = None,
    ) -> str:
        """Download ERA5 reanalysis data.

        Args:
            variables: List of variable names (e.g., ['2m_temperature', '10m_u_component_of_wind'])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            area: Bounding box as [north, west, south, east] in degrees
            output_file: Output NetCDF file path
            pressure_levels: Pressure levels in hPa for 3D variables
            time_hours: Specific hours to download (e.g., ['00:00', '12:00'])

        Returns:
            Path to downloaded file

        Raises:
            ValidationError: If parameters are invalid
            APIError: If download fails
        """
        try:
            # Validate dates
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            if start_dt > end_dt:
                raise ValidationError("Start date must be before end date")

            if end_dt > datetime.now() - timedelta(days=5):
                raise ValidationError(
                    "ERA5 data has ~5 day delay. Use more recent data."
                )

            # Set default output file
            if not output_file:
                output_file = f"era5_{start_date}_{end_date}.nc"

            # Create output directory
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)

            # Build request parameters
            request_params = {
                "product_type": "reanalysis",
                "variable": variables,
                "year": [str(year) for year in range(start_dt.year, end_dt.year + 1)],
                "month": [f"{month:02d}" for month in range(1, 13)],
                "day": [f"{day:02d}" for day in range(1, 32)],
                "time": time_hours or ["00:00", "06:00", "12:00", "18:00"],
                "format": "netcdf",
            }

            # Add area if specified
            if area:
                if len(area) != 4:
                    raise ValidationError("Area must be [north, west, south, east]")
                request_params["area"] = area

            # Add pressure levels for 3D variables
            if pressure_levels:
                request_params["pressure_level"] = pressure_levels
                dataset = "reanalysis-era5-pressure-levels"
            else:
                dataset = "reanalysis-era5-single-levels"

            logger.info(
                f"Downloading ERA5 data: {variables} from {start_date} to {end_date}"
            )

            # Download data
            self.client.retrieve(dataset, request_params, output_file)

            logger.info(f"ERA5 data downloaded to {output_file}")
            return output_file

        except cdsapi.api.Error as e:
            logger.error(f"CDS API error: {e}")
            raise APIError(f"ERA5 download failed: {e}")
        except Exception as e:
            logger.error(f"ERA5 download error: {e}")
            raise APIError(f"ERA5 download failed: {e}")

    def get_available_variables(self, dataset: str = "single-levels") -> Dict[str, str]:
        """Get available ERA5 variables.

        Args:
            dataset: Dataset type ('single-levels' or 'pressure-levels')

        Returns:
            Dictionary mapping variable codes to descriptions
        """
        # Common ERA5 single-level variables
        single_level_vars = {
            "2m_temperature": "2 metre temperature",
            "2m_dewpoint_temperature": "2 metre dewpoint temperature",
            "surface_pressure": "Surface pressure",
            "mean_sea_level_pressure": "Mean sea level pressure",
            "total_precipitation": "Total precipitation",
            "10m_u_component_of_wind": "10 metre U wind component",
            "10m_v_component_of_wind": "10 metre V wind component",
            "surface_solar_radiation_downwards": "Surface solar radiation downwards",
            "surface_thermal_radiation_downwards": "Surface thermal radiation downwards",
            "skin_temperature": "Skin temperature",
            "soil_temperature_level_1": "Soil temperature level 1",
            "volumetric_soil_water_layer_1": "Volumetric soil water layer 1",
        }

        pressure_level_vars = {
            "temperature": "Temperature",
            "u_component_of_wind": "U component of wind",
            "v_component_of_wind": "V component of wind",
            "geopotential": "Geopotential",
            "relative_humidity": "Relative humidity",
            "specific_humidity": "Specific humidity",
        }

        if dataset == "pressure-levels":
            return pressure_level_vars
        else:
            return single_level_vars


def download_era5_data(
    variables: List[str],
    start_date: str,
    end_date: str,
    area: Optional[List[float]] = None,
    output_file: Optional[str] = None,
    **kwargs,
) -> str:
    """Convenience function to download ERA5 data.

    Args:
        variables: List of variable names
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        area: Bounding box [north, west, south, east]
        output_file: Output file path
        **kwargs: Additional arguments for ERA5Client.download_era5_reanalysis

    Returns:
        Path to downloaded file
    """
    client = ERA5Client()
    return client.download_era5_reanalysis(
        variables=variables,
        start_date=start_date,
        end_date=end_date,
        area=area,
        output_file=output_file,
        **kwargs,
    )
