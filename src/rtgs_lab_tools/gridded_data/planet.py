"""Planet Labs access using python API"""

import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import pandas as pd
import requests

from ..core import Config
from ..core.exceptions import APIError, ValidationError
from .utils import qa_bands

logger = logging.getLogger(__name__)

cfg = Config()
API_KEY = cfg.PL_API_KEY


def download_file(url, out_dir, filename=None):
    res = requests.get(url, stream=True, auth=(API_KEY, ""))

    if not filename:
        # Construct a filename from the API response
        if "content-disposition" in res.headers:
            filename = (
                res.headers["content-disposition"].split("filename=")[-1].strip("'\"")
            )
        # Construct a filename from the location url
        else:
            filename = url.split("=")[1][:10]
    # Save the file
    with open(os.path.join(out_dir, filename), "wb") as f:
        for chunk in res.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()

    return filename


def download_clipped_scenes(
    source, meta_file, roi, start_date, end_date, clouds, out_dir
):
    """A function to download clipped listed scenes.

    Args:
        source: Planet sensors to search for
        roi: GEE FeatureCollection with region of interest
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        out_dir: Local output directory
    """
    # Authentication
    URL = "https://api.planet.com/data/v1"
    session = requests.Session()
    session.auth = (API_KEY, "")
    res = session.get(URL)
    assert res.status_code == 200, "Connection to PlanetLabs API failed"

    quick_url = "{}/quick-search".format(URL)

    source = source.split(",")

    if meta_file:
        ids = pd.read_csv(meta_file)["id"].tolist()
        id_finder = {"type": "StringInFilter", "field_name": "id", "config": ids}
        request = {"item_types": source, "interval": "year", "filter": id_finder}
        res = session.post(quick_url, json=request)
        result = res.json()

        features = result["features"]
    else:
        date_filter = {
            "type": "DateRangeFilter",
            "field_name": "acquired",
            "config": {
                "gte": start_date + "T00:00:00.000Z",
                "lte": end_date + "T00:00:00.000Z",
            },
        }

        cloud_filter = {
            "type": "RangeFilter",
            "field_name": "cloud_cover",
            "config": {"lte": clouds / 100},
        }

        geometry_filter = {
            "type": "GeometryFilter",
            "field_name": "geometry",
            "config": roi["features"][0]["geometry"],
        }

        and_filter = {
            "type": "AndFilter",
            "config": [date_filter, geometry_filter, cloud_filter],
        }

        request = {
            "item_types": source,
            "interval": "year",
            "filter": and_filter,
        }

        # Send the POST request to the API stats endpoint
        res = session.post(quick_url, json=request)
        result = res.json()

        features = result["features"]
    print(
        "=" * 10,
        "WARNING",
        "=" * 10,
    )
    answer = input(
        f"Total number of scenes: {len(features)}\nRequired storage size: {len(features)*330/1024} Gb\n\nPlanetLabs imagery is distributed by quota. Please make sure that you want to derive every scene.\nProceed? (y/n)"
    )
    proceed = True if answer == "y" else False
    if proceed:
        # Extract item IDs for clipping
        item_ids = [feature["id"] for feature in features]

        # Create clipping order instead of individual downloads
        clip_order = {
            "name": "clipped_order",
            "products": [
                {
                    "item_ids": item_ids,
                    "item_type": source[0],
                    "product_bundle": "analytic_udm2",
                }
            ],
            "tools": [{"clip": {"aoi": roi["features"][0]["geometry"]}}],
        }

        orders_url = "https://api.planet.com/compute/ops/orders/v2"
        clip_res = session.post(orders_url, json=clip_order)
        print(clip_res.json())
        order_id = clip_res.json()["id"]

        print(f"Clipping order submitted: {order_id}")

        while True:
            status_url = f"https://api.planet.com/compute/ops/orders/v2/{order_id}"
            status_res = session.get(status_url)
            order_info = status_res.json()

            state = order_info["state"]
            print(f"Order status: {state}")

            if state == "success":
                print("Order completed successfully!")
                break
            elif state == "failed":
                print("Order failed!")
                break
            else:
                time.sleep(30)

        if state == "success":
            for result in order_info["_links"]["results"]:
                location_url = result["location"]
                download_file(location_url, out_dir)
                print(f"File {result["name"]} downloaded!")


def download_scenes(source, meta_file, roi, start_date, end_date, clouds, out_dir):
    """A function to download listed scenes.

    Args:
        source: Planet sensors to search for
        roi: GEE FeatureCollection with region of interest
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        out_dir: Local output directory
    """
    # Authentication
    URL = "https://api.planet.com/data/v1"
    session = requests.Session()
    session.auth = (API_KEY, "")
    res = session.get(URL)
    assert res.status_code == 200, "Connection to PlanetLabs API failed"

    quick_url = "{}/quick-search".format(URL)

    source = source.split(",")

    if meta_file:
        ids = pd.read_csv(meta_file)["id"].tolist()
        id_finder = {"type": "StringInFilter", "field_name": "id", "config": ids}
        request = {"item_types": source, "interval": "year", "filter": id_finder}
        res = session.post(quick_url, json=request)
        result = res.json()

        features = result["features"]
    else:
        date_filter = {
            "type": "DateRangeFilter",
            "field_name": "acquired",
            "config": {
                "gte": start_date + "T00:00:00.000Z",
                "lte": end_date + "T00:00:00.000Z",
            },
        }

        cloud_filter = {
            "type": "RangeFilter",
            "field_name": "cloud_cover",
            "config": {"lte": clouds / 100},
        }

        geometry_filter = {
            "type": "GeometryFilter",
            "field_name": "geometry",
            "config": roi["features"][0]["geometry"],
        }

        and_filter = {
            "type": "AndFilter",
            "config": [date_filter, geometry_filter, cloud_filter],
        }

        request = {"item_types": source, "interval": "year", "filter": and_filter}

        # Send the POST request to the API stats endpoint
        res = session.post(quick_url, json=request)
        result = res.json()

        features = result["features"]
    print(
        "=" * 10,
        "WARNING",
        "=" * 10,
    )
    answer = input(
        f"Total number of scenes: {len(features)}\nRequired storage size: {len(features)*330/1024} Gb\n\nPlanetLabs imagery is distributed by quota. Please make sure that you want to derive every scene.\nProceed? (y/n)"
    )
    proceed = True if answer == "y" else False
    if proceed:
        for feature in features:
            assets_url = feature["_links"]["assets"]
            res = session.get(assets_url)
            assets = res.json()

            basic_analytic_4b = assets["basic_analytic_4b"]
            activation_url = basic_analytic_4b["_links"]["activate"]
            session.get(activation_url)

            basic_udm2 = assets["basic_udm2"]
            udm2_activation_url = basic_udm2["_links"]["activate"]
            session.get(udm2_activation_url)
            print("Submitted")

            for img in ["basic_analytic_4b", "basic_udm2"]:
                while True:
                    res = session.get(assets_url)
                    assets = res.json()
                    img = assets["img"]  # refresh!
                    asset_status = img["status"]
                    print(f"Status: {asset_status}")
                    if asset_status == "active":
                        print("Asset is active and ready to download")
                        break
                    time.sleep(120)

                location_url = img["location"]
                download_file(location_url, out_dir)
                print(f"File {feature['id']} downloaded!")


def quick_search(source, roi, start_date, end_date, clouds, out_dir):
    """A function to get all available images for a give date range.

    Args:
        source: Planet sensors to search for
        roi: GEE FeatureCollection with region of interest
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        out_dir: Local output directory
    """
    # Authentication
    URL = "https://api.planet.com/data/v1"
    session = requests.Session()
    session.auth = (API_KEY, "")
    res = session.get(URL)
    assert res.status_code == 200, "Connection to PlanetLabs API failed"
    quick_url = "{}/quick-search".format(URL)

    source = source.split(",")
    # Composing request
    date_filter = {
        "type": "DateRangeFilter",
        "field_name": "acquired",
        "config": {
            "gte": start_date + "T00:00:00.000Z",
            "lte": end_date + "T00:00:00.000Z",
        },
    }

    cloud_filter = {
        "type": "RangeFilter",
        "field_name": "cloud_cover",
        "config": {"lte": clouds / 100},
    }

    geometry_filter = {
        "type": "GeometryFilter",
        "field_name": "geometry",
        "config": roi["features"][0]["geometry"],
    }

    and_filter = {
        "type": "AndFilter",
        "config": [date_filter, geometry_filter, cloud_filter],
    }

    request = {"item_types": source, "interval": "year", "filter": and_filter}

    # Send the POST request to the API stats endpoint
    res = session.post(quick_url, json=request)
    result = res.json()

    features = result["features"]
    data = []
    for feature in features:
        id = feature["id"]
        prop = feature["properties"]
        prop["id"] = id
        if prop["publishing_stage"] == "finalized":
            data.append(list(prop.values()))
    df = pd.DataFrame(columns=prop.keys(), data=data)
    df.to_csv(f"{out_dir}/search_results_PlanetLabs_{start_date}_{end_date}")
    print(f"Found {len(df)} features")
