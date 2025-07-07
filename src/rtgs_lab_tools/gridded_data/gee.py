"""GEE Datasets access using python API"""

import time
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

def download_GEE_data(name, source, bands, roi, scale, start_date, end_date, 
                      out_dest, folder, clouds):
    """A function to download GEE data.

    Args:
        name: Short dataset name
        source: GEE path to the dataset to download
        bands: List of variable names
        roi: GEE FeatureCollection with region of interest
        scale: Image resolution
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_file: Output files destination type
        folder: Output files destination folder
        clouds: Minimum cloud percentage threshold
    Returns:
        Path to downloaded file
    """
    def clip_img(img):
        return img.clip(roi)

    collection = ee.ImageCollection(source)\
              .filterBounds(roi)\
              .filterDate(start_date, end_date)
    if bands is not None:
        collection = collection.select(bands)
    collection = collection.map(clip_img)
    collection_list = collection.toList(collection.size())
    size = collection.size().getInfo()
    print(f"Found {size} files to export")

    if scale is None:
        img_bands = list_GEE_vars(source)
        scale = collection.first().select(img_bands[0]).projection().nominalScale().getInfo()

    #TODO: export logic
    if out_dest=='drive':
        for i in range(size):
            img = ee.Image(collection_list.get(i))
            img_id = img.id().getInfo() or f"image_{i}"

            task = ee.batch.Export.image.toDrive(
                image=img,
                folder=folder,
                description=f'rtgs_export_{name}_{img_id}',
                fileNamePrefix='my_image',
                region=roi,
                scale=scale
            )

            task.start()

            while task.active():
                print(f'Processing file {img_id}...')
                time.sleep(30)

    elif out_dest=='bucket':
        for i in range(size):
            img = ee.Image(collection_list.get(i))
            img_id = img.id().getInfo() or f"image_{i}"

            task = ee.batch.Export.image.toCloudStorage(
                image=img,
                bucket='your-bucket-name',  # TODO: Replace with your bucket
                description=f'rtgs_export_{name}_{img_id}',
                fileNamePrefix=folder, 
                scale=scale,
                region=roi,
                maxPixels=1e9,
                fileFormat='GeoTIFF',
                formatOptions={
                    'cloudOptimized': True  
                }
            )
            task.start()

            while task.active():
                print(f'Processing file {img_id}...')
                time.sleep(30)

    print("Exporting is complete!")