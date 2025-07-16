"""GEE Datasets access using python API"""

import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import ee
import geopandas as gpd
import pandas as pd

from ..core import Config
from ..core.exceptions import APIError, ValidationError
from .utils import qa_bands

logger = logging.getLogger(__name__)

cfg = Config()
GEE_PROJECT = cfg.GEE_PROJECT
BUCKET_NAME = cfg.BUCKET_NAME


def init_ee():
    try:
        import ee

        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)

    except ImportError:
        logger.warning(
            "Gridded data functionality requires earthegine and xarray. Install with: pip install rtgs-lab-tools[climate]"
        )


def compute_clouds(img, mask, roi):
    scale = mask.projection().nominalScale().getInfo()

    pixel_area = (
        mask.unmask(0)
        .reduceRegion(
            reducer=ee.Reducer.count(), geometry=roi, scale=scale, maxPixels=1e13
        )
        .getInfo()
    )  # <-- Move .getInfo() here
    total_pixels = pixel_area.get("clouds", None)
    if not total_pixels:
        return 100.0

    valid_area = mask.reduceRegion(
        reducer=ee.Reducer.sum(), geometry=roi, scale=scale, maxPixels=1e13
    ).getInfo()  # <-- Move .getInfo() here
    valid_pixels = valid_area.get("clouds", 0)
    if not valid_pixels:
        valid_pixels = 0

    masked_pct = 100 * (1 - valid_pixels / total_pixels)
    return masked_pct


def filter_clouds(name, img, qa_band):
    qa = img.select(qa_band)
    if name == "MOD" or name == "MYD":
        cloud = qa.bitwiseAnd(1 << 0).eq(1)
        shadow = qa.bitwiseAnd(1 << 1).eq(1)
        cirrus = qa.bitwiseAnd(1 << 2).eq(1)
        return cloud.Or(shadow).Or(cirrus).rename("clouds").toInt16()
    elif name == "Sentinel-2":
        cloud = qa.bitwiseAnd(1 << 10).gt(0)
        cirrus = qa.bitwiseAnd(1 << 11).gt(0)
        return cloud.Or(cirrus).rename("clouds").toInt16()
    elif name == "Landsat-8" or name == "Landsat-9":
        cloud_bit = 1 << 3  # Cloud
        cloud_shadow_bit = 1 << 4  # Cloud Shadow
        cirrus_bit = 1 << 2  # Cirrus

        cloud = qa.bitwiseAnd(cloud_bit).gt(0)
        shadow = qa.bitwiseAnd(cloud_shadow_bit).gt(0)
        cirrus = qa.bitwiseAnd(cirrus_bit).gt(0)

        combined_mask = cloud.Or(shadow).Or(cirrus)

        return combined_mask.rename("clouds").toInt16()

    elif name == "VIIRS":
        cloud_conf = qa.rightShift(2).bitwiseAnd(3)
        is_cloud = cloud_conf.gte(2)
        return is_cloud.rename("clouds").toInt16()

    return img


def list_GEE_vars(source):
    dataset = ee.ImageCollection(source).first()
    band_names = dataset.bandNames().getInfo()
    return band_names


def load_roi(path):
    gdf = gpd.read_file(path)
    geojson_dict = gdf.__geo_interface__
    geom = ee.FeatureCollection(geojson_dict)
    return geom


def make_reducer(roi, scale):
    def _fn(img):
        vals = img.reduceRegion(
            ee.Reducer.first(), roi, scale, bestEffort=True, maxPixels=1e13
        )

        date_str = ee.Date(img.get("system:time_start")).format("YYYY-MM-dd")
        return ee.Feature(roi, vals).set("date", date_str)

    return _fn


def search_images(name, source, roi, start_date, end_date, out_dir):
    """A function to get all available images for a give date range.

    Args:
        name: Short dataset name
        source: GEE path to the dataset to download
        roi: GEE FeatureCollection with region of interest
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        out_dir: Local output directory
    """

    def clip_img(img):
        return img.clip(roi)

    assert roi.geometry().getInfo()["type"] in [
        "Polygon",
        "MultiPolygon",
    ], f"ERROR: The Region of Interest (roi) should be POLYGON or MULTIPOLYGON. Now it is: {roi.geometry().getInfo()['type']}"
    assert (
        name in qa_bands.keys()
    ), f"ERROR: The selected dataset, {name}, is not listed as satellite imagery: {list(qa_bands.keys())}"

    if name in qa_bands.keys():
        qa_band = qa_bands[name]

    collection = (
        ee.ImageCollection(source).filterBounds(roi).filterDate(start_date, end_date)
    )
    collection_list = collection.toList(collection.size())
    size = collection.size().getInfo()
    print(f"Found {size} files to export")
    d = []
    for i in range(size):
        img = clip_img(ee.Image(collection_list.get(i)))
        img_id = img.id().getInfo() or f"image_{i}"

        mask = filter_clouds(name, img, qa_band)
        cloud_percentage = compute_clouds(img, mask, roi)
        d.append(
            [
                img_id,
                ee.Date(img.get("system:time_start")).format("YYYY-MM-dd").getInfo(),
                cloud_percentage,
            ]
        )
    df = pd.DataFrame(data=d, columns=["ID", "date", "clouds"])
    df.to_csv(
        os.path.join(out_dir, f"search_results_{name}_{start_date}_{end_date}.csv"),
        index=None,
    )
    print("Search is complete!")


def download_GEE_point(name, source, bands, roi, start_date, end_date, out_dir):
    """A function to download GEE pixel for a given point.

    Args:
        name: Short dataset name
        source: GEE path to the dataset to download
        bands: List of variable names
        roi: GEE FeatureCollection with region of interest
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        out_dir: Local output directory
    Returns:
        Path to downloaded file
    """

    if len(bands) < 0:
        bands = list_GEE_vars(source)

    collection = (
        ee.ImageCollection(source).filterBounds(roi).filterDate(start_date, end_date)
    )
    if bands is not None:
        collection = collection.select(bands)

    size = collection.size().getInfo()
    print(f"Found {size} images to process")

    scale = collection.first().select(bands[0]).projection().nominalScale().getInfo()

    os.makedirs(out_dir, exist_ok=True)
    features = []
    points = roi.toList(roi.size())
    for i in range(roi.size().getInfo()):
        point = ee.Feature(points.get(i)).geometry()
        reducer = make_reducer(point, scale)
        feature_collection = collection.map(reducer)
        for feature in feature_collection.getInfo()["features"]:
            row = {
                **{
                    "lon": feature["geometry"]["coordinates"][0],
                    "lat": feature["geometry"]["coordinates"][1],
                },
                **feature["properties"],
            }
            features.append(row)
    df = pd.DataFrame(features).drop_duplicates()
    df.to_csv(os.path.join(out_dir, f"{name}_{start_date}_{end_date}.csv"), index=None)
    print("Exporting is complete!")


def download_GEE_raster(
    name, source, bands, roi, start_date, end_date, out_dest, folder, clouds
):
    """A function to download GEE raster.

    Args:
        name: Short dataset name
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

    def clip_img(img):
        return img.clip(roi)

    roi = roi.geometry()

    if name in qa_bands.keys():
        qa_band = qa_bands[name]

    if len(bands) > 0 and qa_band:
        bands += (
            [qa_band] if qa_band not in bands else []
        )  # adding QA band if not included
    else:
        bands = list_GEE_vars(source)

    collection = (
        ee.ImageCollection(source).filterBounds(roi).filterDate(start_date, end_date)
    )
    if bands is not None:
        collection = collection.select(bands)
    collection_list = collection.toList(collection.size())
    size = collection.size().getInfo()
    print(f"Found {size} files to export")

    if out_dest == "drive":
        for i in range(size):
            img = clip_img(ee.Image(collection_list.get(i)))
            img_id = img.id().getInfo() or f"image_{i}"

            if clouds is not None:
                mask = filter_clouds(name, img, qa_band)
                cloud_percentage = compute_clouds(img, mask, roi)
                cloud_flag = True if cloud_percentage <= int(clouds) else False
            else:
                cloud_flag = True

            if cloud_flag:
                task = ee.batch.Export.image.toDrive(
                    image=img.select(bands[:-1]).toFloat(),
                    folder=folder,
                    fileNamePrefix=f"rtgs_export_{name}_{img_id}",
                    region=roi,
                )

                task.start()

                while task.active():
                    print(f"Processing file {img_id}...")
                    time.sleep(30)

    elif out_dest == "bucket":
        for i in range(size):
            img = ee.Image(collection_list.get(i))
            img_id = img.id().getInfo() or f"image_{i}"

            if clouds:
                mask = filter_clouds(name, img, qa_band)
                cloud_percentage = compute_clouds(img, mask, roi)
                cloud_flag = True if cloud_percentage <= int(clouds) else False
            else:
                cloud_flag = True

            if cloud_flag:
                task = ee.batch.Export.image.toCloudStorage(
                    image=img.select(bands[:-1]).toFloat(),
                    bucket=BUCKET_NAME,
                    description=f"rtgs_export_{name}_{img_id}",
                    fileNamePrefix=folder,
                    region=roi,
                    maxPixels=1e9,
                    fileFormat="GeoTIFF",
                    formatOptions={"cloudOptimized": True},
                )
                task.start()

                while task.active():
                    print(f"Processing file {img_id}...")
                    time.sleep(30)

    print("Exporting is complete!")
