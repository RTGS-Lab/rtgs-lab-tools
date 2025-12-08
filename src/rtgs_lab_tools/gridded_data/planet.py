"""Planet Labs access using python API"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import pandas as pd
import requests
import yaml

from ..core import Config
from ..core.exceptions import APIError, ValidationError
from .utils import qa_bands

logger = logging.getLogger(__name__)

cfg = Config()
API_KEY = cfg.PL_API_KEY


def load_yaml_config(config_path: str) -> Dict:
    """Load and validate YAML configuration file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Dictionary containing configuration

    Raises:
        ValidationError: If configuration is invalid
    """
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Validate required fields
        if "search" not in config:
            raise ValidationError("Configuration must contain 'search' section")

        search = config["search"]
        if "source" not in search:
            raise ValidationError("'search.source' is required")
        if "start_date" not in search:
            raise ValidationError("'search.start_date' is required")
        if "end_date" not in search:
            raise ValidationError("'search.end_date' is required")

        return config

    except yaml.YAMLError as e:
        raise ValidationError(f"Invalid YAML configuration: {e}")
    except FileNotFoundError:
        raise ValidationError(f"Configuration file not found: {config_path}")


def build_planet_filters(config: Dict, roi_geometry: Dict) -> Dict:
    """Build Planet API filters from YAML configuration.

    Args:
        config: Configuration dictionary from YAML
        roi_geometry: GeoJSON geometry for the region of interest

    Returns:
        Dictionary containing Planet API filter configuration
    """
    search = config["search"]
    filters_config = config.get("filters", {})

    # Always include date and geometry filters
    filter_list = []

    # Date filter
    date_filter = {
        "type": "DateRangeFilter",
        "field_name": "acquired",
        "config": {
            "gte": search["start_date"] + "T00:00:00.000Z",
            "lte": search["end_date"] + "T00:00:00.000Z",
        },
    }
    filter_list.append(date_filter)

    # Geometry filter
    geometry_filter = {
        "type": "GeometryFilter",
        "field_name": "geometry",
        "config": roi_geometry,
    }
    filter_list.append(geometry_filter)

    # Cloud cover filter
    if "cloud_cover" in filters_config:
        cloud_config = filters_config["cloud_cover"]
        cloud_filter = {
            "type": "RangeFilter",
            "field_name": "cloud_cover",
            "config": cloud_config,
        }
        filter_list.append(cloud_filter)

    # Instrument filter
    if "instrument" in filters_config:
        instrument_filter = {
            "type": "StringInFilter",
            "field_name": "instrument",
            "config": filters_config["instrument"],
        }
        filter_list.append(instrument_filter)

    # Quality category filter
    if "quality_category" in filters_config:
        quality_filter = {
            "type": "StringInFilter",
            "field_name": "quality_category",
            "config": filters_config["quality_category"],
        }
        filter_list.append(quality_filter)

    # Asset filter
    if "asset_types" in filters_config:
        asset_filter = {
            "type": "AssetFilter",
            "config": filters_config["asset_types"],
        }
        filter_list.append(asset_filter)

    # Additional range filters (generic)
    for key, value in filters_config.items():
        if key not in [
            "cloud_cover",
            "instrument",
            "quality_category",
            "asset_types",
        ] and isinstance(value, dict):
            if "gte" in value or "lte" in value or "gt" in value or "lt" in value:
                range_filter = {
                    "type": "RangeFilter",
                    "field_name": key,
                    "config": value,
                }
                filter_list.append(range_filter)

    # Additional string filters (generic)
    for key, value in filters_config.items():
        if key not in [
            "cloud_cover",
            "instrument",
            "quality_category",
            "asset_types",
        ] and isinstance(value, list):
            string_filter = {
                "type": "StringInFilter",
                "field_name": key,
                "config": value,
            }
            filter_list.append(string_filter)

    # Combine all filters with AND
    and_filter = {"type": "AndFilter", "config": filter_list}

    return and_filter


def batch_search_from_config(config_path: str, roi_dir: str) -> Dict[str, pd.DataFrame]:
    """Perform batch Planet search using YAML config and directory of ROI files.

    Args:
        config_path: Path to YAML configuration file
        roi_dir: Directory containing GeoJSON ROI files

    Returns:
        Dictionary mapping ROI names to DataFrames of search results
    """
    # Load configuration
    config = load_yaml_config(config_path)

    # Get output settings
    output_config = config.get("output", {})
    out_dir = output_config.get("directory", "./planet_search_results")
    filename_pattern = output_config.get(
        "filename_pattern", "search_results_{roi_name}_{start_date}_{end_date}.csv"
    )
    sort_by = output_config.get("sort_by")
    sort_order = output_config.get("sort_order", "asc")
    deduplicate = output_config.get("deduplicate_by_date", False)
    dedup_sort_by = output_config.get("deduplicate_sort_by", "clear_confidence_percent")

    # Create output directory
    os.makedirs(out_dir, exist_ok=True)

    # Find all GeoJSON files in directory
    roi_path = Path(roi_dir)
    geojson_files = list(roi_path.glob("*.geojson"))

    if not geojson_files:
        raise ValidationError(f"No GeoJSON files found in directory: {roi_dir}")

    logger.info(f"Found {len(geojson_files)} ROI files in {roi_dir}")

    # Process each ROI
    results = {}
    search_config = config["search"]

    # Authentication
    URL = "https://api.planet.com/data/v1"
    session = requests.Session()
    session.auth = (API_KEY, "")
    res = session.get(URL)
    if res.status_code != 200:
        raise APIError("Connection to PlanetLabs API failed")

    quick_url = f"{URL}/quick-search"
    source = search_config["source"].split(",")

    for geojson_file in geojson_files:
        roi_name = geojson_file.stem  # Filename without extension

        logger.info(f"Processing ROI: {roi_name}")

        # Load ROI geometry
        with open(geojson_file, "r") as f:
            roi_data = json.load(f)

        # Extract geometry from first feature
        if "features" in roi_data and len(roi_data["features"]) > 0:
            roi_geometry = roi_data["features"][0]["geometry"]
        else:
            logger.warning(f"Skipping {roi_name}: No features found in GeoJSON")
            continue

        # Build filters
        planet_filter = build_planet_filters(config, roi_geometry)

        # Create request
        request = {"item_types": source, "interval": "year", "filter": planet_filter}

        # Send initial request
        res = session.post(quick_url, json=request)
        result = res.json()

        if "features" not in result:
            logger.warning(f"No results for {roi_name}: {result}")
            continue

        # Collect all features with pagination
        all_features = []
        all_features.extend(result["features"])
        page_count = 1
        logger.info(f"Page {page_count}: Found {len(result['features'])} features for {roi_name}")

        # Follow pagination links to get all results
        while "_links" in result and "_next" in result["_links"] and result["_links"]["_next"]:
            next_url = result["_links"]["_next"]
            res = session.get(next_url)
            result = res.json()

            if "features" in result and len(result["features"]) > 0:
                all_features.extend(result["features"])
                page_count += 1
                logger.info(f"Page {page_count}: Found {len(result['features'])} features for {roi_name}")
            else:
                break

        logger.info(f"Total: {len(all_features)} features across {page_count} pages for {roi_name}")

        features = all_features

        # Process features into DataFrame
        data = []
        columns = None
        for feature in features:
            id = feature["id"]
            prop = feature["properties"]
            prop["id"] = id
            if prop.get("publishing_stage") == "finalized":
                if columns is None:
                    columns = list(prop.keys())
                data.append(list(prop.values()))

        if columns is None or len(data) == 0:
            logger.warning(f"No finalized features found for {roi_name}")
            df = pd.DataFrame()
        else:
            df = pd.DataFrame(columns=columns, data=data)
            logger.info(f"Found {len(df)} features for {roi_name}")

            # Add date column for easier processing
            if "acquired" in df.columns:
                df["date_acquired"] = pd.to_datetime(df["acquired"].str[:10])

            # Sort if specified
            if sort_by and sort_by in df.columns:
                ascending = sort_order == "asc"
                df = df.sort_values(by=sort_by, ascending=ascending)

            # Deduplicate by date if specified
            if deduplicate and "date_acquired" in df.columns:
                if dedup_sort_by in df.columns:
                    # Sort by dedup field (descending for confidence, ascending for cloud)
                    ascending = "cloud" in dedup_sort_by.lower()
                    df = df.sort_values(by=dedup_sort_by, ascending=ascending)
                # Keep first occurrence of each date (best based on sort)
                df = df.drop_duplicates(subset="date_acquired", keep="first")
                logger.info(f"After deduplication: {len(df)} unique dates for {roi_name}")

                # Re-sort by original sort field after deduplication
                if sort_by and sort_by in df.columns:
                    ascending = sort_order == "asc"
                    df = df.sort_values(by=sort_by, ascending=ascending)

            # Save to file
            output_filename = filename_pattern.format(
                roi_name=roi_name,
                start_date=search_config["start_date"],
                end_date=search_config["end_date"],
                source=search_config["source"],
            )
            output_path = os.path.join(out_dir, output_filename)
            df.to_csv(output_path, index=False)
            logger.info(f"Saved results to: {output_path}")

        results[roi_name] = df

    return results


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

    # Construct full output path
    output_path = os.path.join(out_dir, filename)

    # Ensure parent directory exists (handles subdirectories in filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save the file
    with open(output_path, "wb") as f:
        for chunk in res.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()

    return filename


def download_clipped_scenes(
    source, meta_file, roi, start_date, end_date, clouds, out_dir, skip_confirmation=False
):
    """A function to download clipped listed scenes.

    Args:
        source: Planet sensors to search for
        roi: GEE FeatureCollection with region of interest
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        out_dir: Local output directory
        skip_confirmation: If True, skip the interactive confirmation prompt
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

        geometry_filter = {
            "type": "GeometryFilter",
            "field_name": "geometry",
            "config": roi["features"][0]["geometry"],
        }

        # Build filter list - only add cloud filter if clouds parameter is provided
        filters = [date_filter, geometry_filter]
        if clouds is not None:
            cloud_filter = {
                "type": "RangeFilter",
                "field_name": "cloud_cover",
                "config": {"lte": clouds / 100},
            }
            filters.append(cloud_filter)

        and_filter = {
            "type": "AndFilter",
            "config": filters,
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

    # Show quota information
    estimated_storage_gb = len(features) * 330 / 1024
    print(f"Total number of scenes: {len(features)}")
    print(f"Required storage size: {estimated_storage_gb:.2f} Gb")

    # Get user confirmation unless skipped
    if not skip_confirmation:
        print("=" * 10, "WARNING", "=" * 10)
        answer = input(
            f"\nPlanetLabs imagery is distributed by quota. Please make sure that you want to derive every scene.\nProceed? (y/n) "
        )
        proceed = True if answer == "y" else False
    else:
        proceed = True
        print("Skipping confirmation (auto-confirmed)")

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
            print(f"\nOrder URL for future downloads: {status_url}")
            print("You can re-download from this order without using more quota.\n")

            for result in order_info["_links"]["results"]:
                location_url = result["location"]
                download_file(location_url, out_dir)
                print(f"File {result['name']} downloaded!")

            return order_id


def download_from_order(order_url, out_dir, overwrite=False):
    """Download files from an existing Planet order without consuming more quota.

    Args:
        order_url: Full Planet order URL (e.g., https://api.planet.com/compute/ops/orders/v2/ORDER_ID)
        out_dir: Local output directory
        overwrite: If True, re-download files that already exist (default: False)

    Returns:
        Dictionary mapping filenames to local file paths
    """
    # Authentication
    session = requests.Session()
    session.auth = (API_KEY, "")

    # Get order info
    print(f"Fetching order from: {order_url}")
    res = session.get(order_url)
    if res.status_code != 200:
        raise APIError(f"Failed to fetch order: {res.status_code} - {res.text}")

    order_info = res.json()
    state = order_info.get("state")

    print(f"Order state: {state}")

    if state == "failed":
        raise APIError(f"Order failed: {order_info}")
    elif state not in ["success", "partial"]:
        print(f"Warning: Order state is '{state}', not 'success'. Attempting download anyway...")

    # Download files
    if "_links" not in order_info or "results" not in order_info["_links"]:
        raise APIError("No results found in order")

    results = order_info["_links"]["results"]
    print(f"\n{len(results)} files available for download")

    downloaded_files = {}
    for result in results:
        filename = result["name"]
        location_url = result["location"]
        output_path = os.path.join(out_dir, filename)

        if not overwrite and os.path.exists(output_path):
            print(f"{filename} already exists, skipping")
            downloaded_files[filename] = output_path
            continue

        print(f"Downloading {filename}...")
        download_file(location_url, out_dir, filename=filename)
        downloaded_files[filename] = output_path
        print(f"  → {output_path}")

    print(f"\nDownloaded {len(downloaded_files)} files to {out_dir}")
    return downloaded_files


def download_scenes(source, meta_file, roi, start_date, end_date, clouds, out_dir, skip_confirmation=False):
    """A function to download listed scenes.

    Args:
        source: Planet sensors to search for
        roi: GEE FeatureCollection with region of interest
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        out_dir: Local output directory
        skip_confirmation: If True, skip the interactive confirmation prompt
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

        geometry_filter = {
            "type": "GeometryFilter",
            "field_name": "geometry",
            "config": roi["features"][0]["geometry"],
        }

        # Build filter list - only add cloud filter if clouds parameter is provided
        filters = [date_filter, geometry_filter]
        if clouds is not None:
            cloud_filter = {
                "type": "RangeFilter",
                "field_name": "cloud_cover",
                "config": {"lte": clouds / 100},
            }
            filters.append(cloud_filter)

        and_filter = {
            "type": "AndFilter",
            "config": filters,
        }

        request = {"item_types": source, "interval": "year", "filter": and_filter}

        # Send the POST request to the API stats endpoint
        res = session.post(quick_url, json=request)
        result = res.json()

        features = result["features"]

    # Show quota information
    estimated_storage_gb = len(features) * 330 / 1024
    print(f"Total number of scenes: {len(features)}")
    print(f"Required storage size: {estimated_storage_gb:.2f} Gb")

    # Get user confirmation unless skipped
    if not skip_confirmation:
        print("=" * 10, "WARNING", "=" * 10)
        answer = input(
            f"\nPlanetLabs imagery is distributed by quota. Please make sure that you want to derive every scene.\nProceed? (y/n) "
        )
        proceed = True if answer == "y" else False
    else:
        proceed = True
        print("Skipping confirmation (auto-confirmed)")

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

    geometry_filter = {
        "type": "GeometryFilter",
        "field_name": "geometry",
        "config": roi["features"][0]["geometry"],
    }

    # Build filter list - only add cloud filter if clouds parameter is provided
    filters = [date_filter, geometry_filter]
    if clouds is not None:
        cloud_filter = {
            "type": "RangeFilter",
            "field_name": "cloud_cover",
            "config": {"lte": clouds / 100},
        }
        filters.append(cloud_filter)

    and_filter = {
        "type": "AndFilter",
        "config": filters,
    }

    request = {"item_types": source, "interval": "year", "filter": and_filter}

    # Send the POST request to the API stats endpoint
    res = session.post(quick_url, json=request)
    result = res.json()

    features = result["features"]
    data = []
    columns = None
    for feature in features:
        id = feature["id"]
        prop = feature["properties"]
        prop["id"] = id
        if prop["publishing_stage"] == "finalized":
            if columns is None:
                columns = list(prop.keys())
            data.append(list(prop.values()))

    if columns is None:
        # No features found, create empty DataFrame
        df = pd.DataFrame()
        print("No features found matching the search criteria")
    else:
        df = pd.DataFrame(columns=columns, data=data)
        print(f"Found {len(df)} features")

    df.to_csv(f"{out_dir}/search_results_PlanetLabs_{start_date}_{end_date}")
