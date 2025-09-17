"""Main spatial data extraction function - mirrors sensing_data.extract_data() API."""

import logging
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Reuse existing rtgs-lab-tools infrastructure
from ...core.exceptions import ValidationError, RTGSLabToolsError
from ..registry.dataset_registry import get_dataset_config
from ..sources.mn_geospatial import MNGeospatialExtractor
from ..db_logger import SpatialDataLogger

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
        
        # 4. Save to file if output_dir is specified
        output_file = None
        file_size_mb = None
        
        if output_dir and not gdf.empty:
            output_file, file_size_mb = _save_to_file(
                gdf, dataset_name, output_dir, output_format, create_zip
            )
            logger.info(f"Saved {len(gdf)} features to {output_file}")
        
        # 5. Prepare results
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
            "output_file": output_file,
            "file_size_mb": file_size_mb,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "note": note
        }
        
        # 6. Log extraction to database
        try:
            with SpatialDataLogger() as db_logger:
                db_logger.log_extraction(results)
        except Exception as e:
            logger.warning(f"Failed to log extraction to database: {e}")
        
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


def _save_to_file(gdf, dataset_name: str, output_dir: str, output_format: str, create_zip: bool):
    """Save GeoDataFrame to file with specified format.
    
    Args:
        gdf: GeoDataFrame to save
        dataset_name: Name of the dataset
        output_dir: Output directory
        output_format: Format to save (geoparquet, shapefile, csv)
        create_zip: Whether to create zip archive
        
    Returns:
        Tuple of (output_file_path, file_size_mb)
    """
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Determine file extension and save method
    if output_format.lower() == "geoparquet":
        file_path = output_path / f"{dataset_name}.parquet"
        gdf.to_parquet(file_path, compression='snappy')
        logger.info(f"Saved as GeoParquet with snappy compression")
        
    elif output_format.lower() == "shapefile":
        file_path = output_path / f"{dataset_name}.shp"
        gdf.to_file(file_path, driver='ESRI Shapefile')
        logger.info(f"Saved as Shapefile")
        
    elif output_format.lower() == "csv":
        file_path = output_path / f"{dataset_name}.csv"
        # Convert geometry to WKT for CSV export
        gdf_csv = gdf.copy()
        gdf_csv['geometry'] = gdf_csv['geometry'].apply(lambda x: x.wkt)
        gdf_csv.to_csv(file_path, index=False)
        logger.info(f"Saved as CSV with WKT geometry")
        
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    # Get file size
    file_size_bytes = file_path.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    # Create zip archive if requested
    if create_zip:
        zip_path = output_path / f"{dataset_name}_{output_format}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if output_format.lower() == "shapefile":
                # Include all shapefile components
                for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
                    shp_file = file_path.with_suffix(ext)
                    if shp_file.exists():
                        zipf.write(shp_file, shp_file.name)
            else:
                # Single file formats
                zipf.write(file_path, file_path.name)
        
        logger.info(f"Created zip archive: {zip_path}")
        return str(zip_path), file_size_mb
    
    return str(file_path), file_size_mb