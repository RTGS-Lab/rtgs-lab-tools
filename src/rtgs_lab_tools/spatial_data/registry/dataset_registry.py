"""Dataset registry for MN Geospatial Commons and other spatial data sources."""

from typing import Dict, Any, Optional

# Start with just MN Geospatial Commons datasets for MVP
MN_GEOSPATIAL_DATASETS = {
    "protected_areas": {
        "description": "DNR Wildlife Management Areas",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/bdry-dnr-wildlife-mgmt-areas-pub",
        "service_url": "https://services3.arcgis.com/It5SEVVk6Di7yUwt/arcgis/rest/services/DNR_WILDLIFE_MGMT_AREAS_PUB/FeatureServer/0",
        "access_method": "rest_api",
        "file_format": "vector",
        "update_frequency": "yearly",
        "spatial_type": "polygon",
        "model_critical": True,
        "coordinate_system": "EPSG:4326",
        "expected_features": 1200  # Approximate count for validation
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