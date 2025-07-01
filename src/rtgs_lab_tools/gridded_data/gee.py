"""GEE Datasets access using python API"""

import logging
import os
import geopandas as gpd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from ..core import Config
from ..core.exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)

GEE_PROJECT =  #TODO: IMPORT FROM ENV!

try:
    import ee

    ee.Authenticate()
    ee.Initialize(project=GEE_PROJECT)

    GEE_AVAILABLE = True
except ImportError:
    GEE_AVAILABLE = False
    logger.warning(
        "Gridded data functionality requires earthegine and xarray. Install with: pip install rtgs-lab-tools[climate]"
    )


def list_GEE_vars(source: str):
    dataset = ee.ImageCollection(source).first()
    band_names = dataset.bandNames().getInfo()
    return band_names

def load_roi(path: str):
    gdf = gpd.read_file(path)
    geojson_dict = gdf.__geo_interface__
    roi = ee.FeatureCollection(geojson_dict)
    return roi

def download_GEE_data( #TODO: rebuild the function
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
    # TODO: if variables==None, then parse ALL
    print('Done!')