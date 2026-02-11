"""ESRI File Geodatabase (FGDB) data extractor."""

import logging
import os
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import SpatialSourceExtractor

if TYPE_CHECKING:
    import geopandas as gpd

try:
    import geopandas as gpd
except ImportError:
    gpd = None

try:
    import fiona
except ImportError:
    fiona = None

logger = logging.getLogger(__name__)

# Environment variable for FGDB path
FGDB_PATH_ENV_VAR = "RTGS_FGDB_PATH"


def get_fgdb_path() -> Optional[str]:
    """Get the FGDB path from environment variable.

    Returns:
        Path to FGDB if set, None otherwise
    """
    return os.environ.get(FGDB_PATH_ENV_VAR)


def is_fgdb_available() -> bool:
    """Check if FGDB is configured and accessible.

    Returns:
        True if FGDB path is set and the file exists
    """
    fgdb_path = get_fgdb_path()
    if not fgdb_path:
        return False
    return os.path.exists(fgdb_path)


def list_fgdb_layers() -> List[str]:
    """List all layers available in the configured FGDB.

    Returns:
        List of layer names, empty list if FGDB not available
    """
    if fiona is None:
        logger.warning("fiona not installed, cannot list FGDB layers")
        return []

    fgdb_path = get_fgdb_path()
    if not fgdb_path or not os.path.exists(fgdb_path):
        return []

    try:
        return fiona.listlayers(fgdb_path)
    except Exception as e:
        logger.error(f"Failed to list FGDB layers: {e}")
        return []


class FGDBExtractor(SpatialSourceExtractor):
    """Extracts spatial data from ESRI File Geodatabase (FGDB)."""

    def __init__(self, dataset_config: Dict[str, Any], fgdb_path: Optional[str] = None, **kwargs):
        """Initialize FGDB extractor.

        Args:
            dataset_config: Configuration dictionary for the dataset
            fgdb_path: Optional direct path to FGDB (overrides env var lookup)
            **kwargs: Additional configuration options

        Raises:
            ValueError: If FGDB path not configured
            ImportError: If fiona not installed
        """
        super().__init__(dataset_config, **kwargs)

        if fiona is None:
            raise ImportError(
                "fiona is required for FGDB extraction. "
                "Install with: pip install fiona"
            )

        self.fgdb_path = fgdb_path or get_fgdb_path()
        if not self.fgdb_path:
            raise ValueError(
                f"FGDB path not configured. "
                f"Set the {FGDB_PATH_ENV_VAR} environment variable "
                f"or pass fgdb_path parameter."
            )

        if not os.path.exists(self.fgdb_path):
            raise ValueError(f"FGDB not found at: {self.fgdb_path}")

        self.layer_name = dataset_config.get("layer_name")
        if not self.layer_name:
            raise ValueError("layer_name is required in dataset_config for FGDB")

    def extract(self) -> "gpd.GeoDataFrame":
        """Extract layer from FGDB.

        Returns:
            GeoDataFrame containing the spatial features
        """
        self.logger.info(f"Extracting layer '{self.layer_name}' from FGDB")

        try:
            # Read the layer from FGDB
            gdf = gpd.read_file(self.fgdb_path, layer=self.layer_name)

            self.logger.info(f"Loaded {len(gdf)} features from {self.layer_name}")
            self.logger.info(f"CRS: {gdf.crs}")
            self.logger.info(f"Columns: {list(gdf.columns)}")

            # Validate spatial integrity
            if not self.validate_spatial_integrity(gdf):
                self.logger.warning("Spatial integrity validation failed")

            # Standardize CRS to WGS84 for consistency with other extractors
            gdf = self.standardize_crs(gdf)

            return gdf

        except Exception as e:
            self.logger.error(f"Failed to extract layer {self.layer_name}: {e}")
            raise

    def get_layer_info(self) -> Dict[str, Any]:
        """Get metadata about the layer.

        Returns:
            Dictionary with layer metadata
        """
        try:
            with fiona.open(self.fgdb_path, layer=self.layer_name) as src:
                return {
                    "layer_name": self.layer_name,
                    "geometry_type": src.schema["geometry"],
                    "crs": str(src.crs),
                    "feature_count": len(src),
                    "columns": list(src.schema["properties"].keys()),
                }
        except Exception as e:
            self.logger.error(f"Failed to get layer info: {e}")
            return {}


def extract_all_fgdb_layers(
    fgdb_path: str, target_crs: str = "EPSG:4326"
) -> Dict[str, "gpd.GeoDataFrame"]:
    """Extract all layers from a File Geodatabase.

    Args:
        fgdb_path: Path to the .gdb directory
        target_crs: Target CRS for standardization (default: EPSG:4326)

    Returns:
        Dictionary mapping layer names to GeoDataFrames

    Raises:
        ImportError: If fiona is not installed
        FileNotFoundError: If FGDB path does not exist
    """
    if fiona is None:
        raise ImportError(
            "fiona is required for FGDB extraction. Install with: pip install fiona"
        )

    if not os.path.exists(fgdb_path):
        raise FileNotFoundError(f"FGDB not found at: {fgdb_path}")

    layers = fiona.listlayers(fgdb_path)
    logger.info(f"Found {len(layers)} layers in FGDB: {fgdb_path}")

    results = {}
    for layer_name in layers:
        try:
            config = {"source_type": "fgdb", "layer_name": layer_name}
            extractor = FGDBExtractor(config, fgdb_path=fgdb_path)
            gdf = extractor.extract()

            # Standardize CRS
            if gdf.crs is not None and str(gdf.crs) != target_crs:
                gdf = gdf.to_crs(target_crs)
            elif gdf.crs is None:
                gdf = gdf.set_crs(target_crs)

            results[layer_name] = gdf
            logger.info(f"  Extracted {layer_name}: {len(gdf)} features")
        except Exception as e:
            logger.warning(f"  Failed to extract layer {layer_name}: {e}")

    logger.info(f"Successfully extracted {len(results)}/{len(layers)} layers")
    return results
