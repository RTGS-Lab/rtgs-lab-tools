"""Extractor for local user-provided spatial files."""

import logging
from pathlib import Path
from typing import Any, Dict

import geopandas as gpd

from .base import SpatialSourceExtractor

logger = logging.getLogger(__name__)


class LocalFileExtractor(SpatialSourceExtractor):
    """Extract spatial data from local files (user-provided flat files)."""

    def __init__(self, dataset_config: Dict[str, Any], **kwargs):
        """Initialize local file extractor.

        Args:
            dataset_config: Configuration with 'file_path' key
            **kwargs: Additional options
        """
        super().__init__(dataset_config, **kwargs)

        self.file_path = Path(dataset_config.get("file_path"))
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        self.layer_name = dataset_config.get("layer_name")

    def extract(self) -> gpd.GeoDataFrame:
        """Extract data from local file.

        Returns:
            GeoDataFrame with the spatial features
        """
        logger.info(f"Reading local file: {self.file_path}")

        try:
            # Determine file type and read accordingly
            suffix = self.file_path.suffix.lower()

            if suffix == ".parquet" or suffix == ".geoparquet":
                gdf = gpd.read_parquet(self.file_path)
            elif suffix == ".geojson" or suffix == ".json":
                gdf = gpd.read_file(self.file_path)
            elif suffix == ".gpkg":
                # GeoPackage - may have multiple layers
                if self.layer_name:
                    gdf = gpd.read_file(self.file_path, layer=self.layer_name)
                else:
                    # Read first layer
                    gdf = gpd.read_file(self.file_path)
            elif suffix == ".shp":
                gdf = gpd.read_file(self.file_path)
            elif suffix == ".zip":
                # Assume zipped shapefile
                gdf = gpd.read_file(f"zip://{self.file_path}")
            else:
                # Try generic read_file
                gdf = gpd.read_file(self.file_path)

            logger.info(f"Read {len(gdf)} features from {self.file_path.name}")

            # Validate
            if not self.validate_spatial_integrity(gdf):
                logger.warning("Spatial data validation found issues")

            # Standardize to EPSG:4326
            gdf = self.standardize_crs(gdf)

            # Log geometry types
            geom_types = gdf.geometry.geom_type.value_counts().to_dict()
            logger.info(f"Geometry types: {geom_types}")

            return gdf

        except Exception as e:
            logger.error(f"Failed to read file {self.file_path}: {e}")
            raise


def discover_local_datasets(local_directory: Path) -> Dict[str, Dict[str, Any]]:
    """
    Discover all spatial files in a local directory.

    Args:
        local_directory: Path to directory containing spatial files

    Returns:
        Dictionary mapping dataset names to configuration
    """
    if not local_directory.exists():
        logger.warning(f"Local directory does not exist: {local_directory}")
        return {}

    # Supported extensions
    spatial_extensions = {
        ".shp", ".gpkg", ".geoparquet", ".parquet",
        ".geojson", ".json", ".zip"
    }

    datasets = {}

    for file_path in local_directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in spatial_extensions:
            # Use stem (filename without extension) as dataset name
            dataset_name = file_path.stem

            # Basic configuration
            config = {
                "file_path": str(file_path),
                "source_type": "local",
                "description": f"Local file: {file_path.name}",
            }

            datasets[dataset_name] = config
            logger.debug(f"Discovered local dataset: {dataset_name} -> {file_path.name}")

    logger.info(f"Discovered {len(datasets)} local datasets in {local_directory}")
    return datasets


def get_local_dataset_info(local_directory: Path) -> Dict[str, Dict[str, Any]]:
    """
    Get detailed information about local datasets without loading them.

    Args:
        local_directory: Path to directory containing spatial files

    Returns:
        Dictionary with dataset information
    """
    datasets = discover_local_datasets(local_directory)

    # Add file size information
    for name, config in datasets.items():
        file_path = Path(config["file_path"])
        config["file_size_mb"] = file_path.stat().st_size / (1024 * 1024)

    return datasets
