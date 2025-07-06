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

cfg = Config()
GEE_PROJECT = cfg.GEE_PROJECT 

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

def download_GEE_data(source, bands, roi, start_date, end_date, 
                      out_dest, folder, clouds):
    """A function to download GEE data.

    Args:
        source: GEE path to the dataset to download
        bands: List of variable names
        roi: GEE FeatureCollection with region of interest
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_file: Output files destination type
        folder: Output files destination folder
        clouds: Minimum cloud percentage threshold
    Returns:
        Path to downloaded file
    """
    collection = ee.ImageCollection(source)\
              .filterBounds(roi)\
              .filterDate(start_date, end_date)
    if bands is not None:
        collection = collection.select(bands)

    #TODO: export logic
    if out_dest=='drive':
        task = ee.batch.Export.image.toDrive(
            image=image,
            folder=folder,
            fileNamePrefix='my_image',
            region=roi,
            scale=30 #TODO: create native res dict or alternative
        )
    elif out_dest=='bucket':
        task = ee.batch.Export.image.toCloudStorage(
            image=image,
            bucket='your-bucket-name',  # TODO: Replace with your bucket
            fileNamePrefix=folder, 
            scale=30,
            region=roi,
            maxPixels=1e9,
            fileFormat='GeoTIFF',
            formatOptions={
                'cloudOptimized': True  # Optional: creates Cloud Optimized GeoTIFF
            }
        )

    print('Done!')