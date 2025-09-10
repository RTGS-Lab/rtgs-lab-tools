"""Dataset registry for MN Geospatial Commons and other spatial data sources."""

from typing import Dict, Any, Optional

# Start with just MN Geospatial Commons datasets for MVP
MN_GEOSPATIAL_DATASETS = {
    "protected_areas": {
        "description": "DNR Wildlife Management Areas",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/bdry-dnr-wildlife-mgmt-areas-pub",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/bdry_dnr_wildlife_mgmt_areas_pub/gpkg_bdry_dnr_wildlife_mgmt_areas_pub.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "yearly",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
        "expected_features": 1731  # Actual count from test
    }
}


def get_dataset_config(dataset_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific dataset."""
    return MN_GEOSPATIAL_DATASETS.get(dataset_name)


def list_available_datasets() -> Dict[str, Dict[str, Any]]:
    """List all available spatial datasets."""
    return MN_GEOSPATIAL_DATASETS


def get_mn_geospatial_datasets() -> Dict[str, Dict[str, Any]]:
    """Get only MN Geospatial Commons datasets."""
    return MN_GEOSPATIAL_DATASETS