"""Main spatial data extraction function - mirrors sensing_data.extract_data() API."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Reuse existing rtgs-lab-tools infrastructure
from ...core.exceptions import ValidationError, RTGSLabToolsError
from ..registry.dataset_registry import get_dataset_config
from ..sources.mn_geospatial import MNGeospatialExtractor

logger = logging.getLogger(__name__)

# Map source types to extractor classes
EXTRACTOR_CLASSES = {
    "mn_geospatial": MNGeospatialExtractor,
}


def extract_spatial_data(
    dataset_name: str,
    output_dir: Optional[str] = None,
    output_format: str = "geoparquet",
    create_zip: bool = False,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """Extract spatial dataset - mirrors sensing_data.extract_data() signature.
    
    Args:
        dataset_name: Name of the dataset to extract
        output_dir: Output directory (default: ./data)
        output_format: Output format - geoparquet, shapefile, or csv
        create_zip: Whether to create zip archive
        note: Optional note for logging
        
    Returns:
        Dictionary with extraction results
    """
    start_time = datetime.now()
    
    try:
        # 1. Look up dataset configuration
        dataset_config = get_dataset_config(dataset_name)
        if not dataset_config:
            raise ValueError(f"Unknown dataset: {dataset_name}")
        
        logger.info(f"Starting extraction of dataset: {dataset_name}")
        
        # 2. Get appropriate extractor class
        source_type = dataset_config["source_type"]
        extractor_class = EXTRACTOR_CLASSES.get(source_type)
        
        if not extractor_class:
            raise ValueError(f"No extractor available for source type: {source_type}")
        
        # 3. Create extractor instance and extract data
        extractor = extractor_class(dataset_config)
        gdf = extractor.extract()
        
        if gdf.empty:
            logger.warning(f"No features extracted for dataset: {dataset_name}")
        
        # 4. For MVP, just return basic info (no file saving yet)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        results = {
            "success": True,
            "dataset_name": dataset_name,
            "records_extracted": len(gdf),
            "crs": str(gdf.crs) if gdf.crs else None,
            "geometry_type": gdf.geom_type.iloc[0] if not gdf.empty else None,
            "bounds": gdf.total_bounds.tolist() if not gdf.empty else None,
            "columns": gdf.columns.tolist(),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "note": note
        }
        
        logger.info(f"Successfully extracted {len(gdf)} features from {dataset_name}")
        return results
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        error_results = {
            "success": False,
            "dataset_name": dataset_name,
            "error": str(e),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "note": note
        }
        
        logger.error(f"Failed to extract dataset {dataset_name}: {e}")
        raise RTGSLabToolsError(f"Spatial data extraction failed: {e}") from e