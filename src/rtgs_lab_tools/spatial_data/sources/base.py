"""Base class for spatial data source extractors."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# Import geopandas with lazy loading for better performance
try:
    import geopandas as gpd
except ImportError:
    gpd = None

logger = logging.getLogger(__name__)


class SpatialSourceExtractor(ABC):
    """Base class for spatial data sources - separate from sensor EventParser."""

    def __init__(self, dataset_config: Dict[str, Any], **kwargs):
        """Initialize spatial extractor with dataset configuration.

        Args:
            dataset_config: Configuration dictionary for the dataset
            **kwargs: Additional configuration options
        """
        if gpd is None:
            raise ImportError("geopandas is required for spatial data extraction")

        self.dataset_config = dataset_config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def extract(self) -> "gpd.GeoDataFrame":
        """Extract spatial data from source - returns GeoDataFrame.

        Returns:
            GeoDataFrame containing the spatial features
        """
        pass

    def validate_spatial_integrity(self, data: "gpd.GeoDataFrame") -> bool:
        """Validate spatial data quality - geometry validity, CRS consistency.

        Args:
            data: GeoDataFrame to validate

        Returns:
            True if data passes validation, False otherwise
        """
        if data.empty:
            self.logger.warning("Dataset is empty")
            return False

        # Check for valid geometries
        invalid_geoms = ~data.is_valid
        if invalid_geoms.any():
            invalid_count = invalid_geoms.sum()
            self.logger.warning(f"Found {invalid_count} invalid geometries")

        # Check CRS
        if data.crs is None:
            self.logger.warning("No CRS defined for dataset")
            return False

        return True

    def standardize_crs(
        self, data: "gpd.GeoDataFrame", target_crs: str = "EPSG:4326"
    ) -> "gpd.GeoDataFrame":
        """Standardize coordinate reference system.

        Args:
            data: GeoDataFrame to transform
            target_crs: Target CRS (default: EPSG:4326)

        Returns:
            GeoDataFrame with standardized CRS
        """
        if data.crs is None:
            self.logger.warning(f"No CRS defined, assuming {target_crs}")
            data = data.set_crs(target_crs)
        elif str(data.crs) != target_crs:
            self.logger.info(f"Transforming from {data.crs} to {target_crs}")
            data = data.to_crs(target_crs)

        return data
