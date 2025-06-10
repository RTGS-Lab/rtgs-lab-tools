"""Data processing utilities for gridded climate data."""

import logging
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ..core.exceptions import ValidationError

logger = logging.getLogger(__name__)

try:
    import xarray as xr

    XARRAY_AVAILABLE = True
except ImportError:
    XARRAY_AVAILABLE = False
    logger.warning(
        "Gridded data processing requires xarray. Install with: pip install rtgs-lab-tools[climate]"
    )


def process_era5_data(
    file_path: str,
    variables: Optional[List[str]] = None,
    temporal_aggregation: Optional[str] = None,
    spatial_subset: Optional[Dict[str, float]] = None,
) -> "xr.Dataset":
    """Process ERA5 NetCDF data with optional aggregation and subsetting.

    Args:
        file_path: Path to ERA5 NetCDF file
        variables: Specific variables to extract
        temporal_aggregation: Temporal aggregation ('daily', 'monthly')
        spatial_subset: Spatial subset as {'lat_min': ..., 'lat_max': ..., 'lon_min': ..., 'lon_max': ...}

    Returns:
        Processed xarray Dataset

    Raises:
        ValidationError: If file cannot be processed
    """
    if not XARRAY_AVAILABLE:
        raise ValidationError("Gridded data processing requires xarray package")

    try:
        # Load dataset
        ds = xr.open_dataset(file_path)
        logger.info(f"Loaded ERA5 dataset with variables: {list(ds.data_vars)}")

        # Select specific variables if requested
        if variables:
            available_vars = list(ds.data_vars)
            missing_vars = [v for v in variables if v not in available_vars]
            if missing_vars:
                raise ValidationError(f"Variables not found in dataset: {missing_vars}")
            ds = ds[variables]

        # Apply spatial subset
        if spatial_subset:
            lat_slice = slice(
                spatial_subset.get("lat_max"), spatial_subset.get("lat_min")
            )
            lon_slice = slice(
                spatial_subset.get("lon_min"), spatial_subset.get("lon_max")
            )
            ds = ds.sel(latitude=lat_slice, longitude=lon_slice)
            logger.info(f"Applied spatial subset: {spatial_subset}")

        # Apply temporal aggregation
        if temporal_aggregation:
            if temporal_aggregation == "daily":
                ds = ds.resample(time="D").mean()
                logger.info("Applied daily temporal aggregation")
            elif temporal_aggregation == "monthly":
                ds = ds.resample(time="M").mean()
                logger.info("Applied monthly temporal aggregation")
            else:
                raise ValidationError(
                    f"Unknown temporal aggregation: {temporal_aggregation}"
                )

        # Add useful attributes
        ds.attrs["processed_by"] = "rtgs-lab-tools"
        ds.attrs["processing_date"] = pd.Timestamp.now().isoformat()

        return ds

    except Exception as e:
        logger.error(f"Failed to process ERA5 data: {e}")
        raise ValidationError(f"ERA5 processing failed: {e}")


def extract_time_series(
    dataset: "xr.Dataset",
    variable: str,
    lat: float,
    lon: float,
    method: str = "nearest",
) -> pd.DataFrame:
    """Extract time series at a specific location from gridded data.

    Args:
        dataset: xarray Dataset with gridded data
        variable: Variable name to extract
        lat: Latitude in degrees
        lon: Longitude in degrees
        method: Interpolation method ('nearest', 'linear')

    Returns:
        DataFrame with time series data

    Raises:
        ValidationError: If extraction fails
    """
    if not XARRAY_AVAILABLE:
        raise ValidationError("Time series extraction requires xarray package")

    try:
        if variable not in dataset.data_vars:
            raise ValidationError(f"Variable '{variable}' not found in dataset")

        # Extract data at location
        if method == "nearest":
            point_data = dataset[variable].sel(
                latitude=lat, longitude=lon, method="nearest"
            )
        elif method == "linear":
            point_data = dataset[variable].interp(
                latitude=lat, longitude=lon, method="linear"
            )
        else:
            raise ValidationError(f"Unknown interpolation method: {method}")

        # Convert to DataFrame
        df = point_data.to_dataframe().reset_index()
        df = df[["time", variable]].rename(
            columns={"time": "timestamp", variable: "value"}
        )

        # Add metadata
        df["variable"] = variable
        df["latitude"] = lat
        df["longitude"] = lon
        df["extraction_method"] = method

        logger.info(f"Extracted {len(df)} time points for {variable} at ({lat}, {lon})")
        return df

    except Exception as e:
        logger.error(f"Failed to extract time series: {e}")
        raise ValidationError(f"Time series extraction failed: {e}")


def calculate_spatial_statistics(
    dataset: "xr.Dataset", variable: str, region: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """Calculate spatial statistics for a variable.

    Args:
        dataset: xarray Dataset
        variable: Variable name
        region: Optional spatial region for statistics

    Returns:
        Dictionary with spatial statistics
    """
    if not XARRAY_AVAILABLE:
        raise ValidationError("Spatial statistics require xarray package")

    try:
        data = dataset[variable]

        # Apply regional subset if specified
        if region:
            lat_slice = slice(region.get("lat_max"), region.get("lat_min"))
            lon_slice = slice(region.get("lon_min"), region.get("lon_max"))
            data = data.sel(latitude=lat_slice, longitude=lon_slice)

        # Calculate statistics
        stats = {
            "mean": float(data.mean()),
            "std": float(data.std()),
            "min": float(data.min()),
            "max": float(data.max()),
            "median": float(data.median()),
        }

        logger.info(f"Calculated spatial statistics for {variable}")
        return stats

    except Exception as e:
        logger.error(f"Failed to calculate spatial statistics: {e}")
        raise ValidationError(f"Spatial statistics calculation failed: {e}")


def regrid_data(
    dataset: "xr.Dataset",
    target_grid: Dict[str, Union[List[float], float]],
    method: str = "bilinear",
) -> "xr.Dataset":
    """Regrid data to a target grid.

    Args:
        dataset: Source dataset
        target_grid: Target grid specification
        method: Regridding method

    Returns:
        Regridded dataset
    """
    if not XARRAY_AVAILABLE:
        raise ValidationError("Regridding requires xarray package")

    try:
        # Create target coordinates
        if "lat" in target_grid and "lon" in target_grid:
            target_lat = np.array(target_grid["lat"])
            target_lon = np.array(target_grid["lon"])
        else:
            # Create regular grid from bounds and resolution
            lat_min = target_grid.get("lat_min", -90)
            lat_max = target_grid.get("lat_max", 90)
            lon_min = target_grid.get("lon_min", -180)
            lon_max = target_grid.get("lon_max", 180)
            resolution = target_grid.get("resolution", 1.0)

            target_lat = np.arange(lat_min, lat_max + resolution, resolution)
            target_lon = np.arange(lon_min, lon_max + resolution, resolution)

        # Interpolate to target grid
        regridded = dataset.interp(
            latitude=target_lat, longitude=target_lon, method=method
        )

        logger.info(f"Regridded data to {len(target_lat)}x{len(target_lon)} grid")
        return regridded

    except Exception as e:
        logger.error(f"Failed to regrid data: {e}")
        raise ValidationError(f"Regridding failed: {e}")
