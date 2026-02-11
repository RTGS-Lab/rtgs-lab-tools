"""Main spatial data extraction function - mirrors sensing_data.extract_data() API."""

import logging
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import geopandas as gpd

# Reuse existing rtgs-lab-tools infrastructure
from ...core.exceptions import RTGSLabToolsError, ValidationError
from ..config import get_config, SpatialDataConfig
from ..db_logger import SpatialDataLogger
from ..registry.dataset_registry import get_dataset_config, get_dataset_config_by_mode
from ..sources.mn_geospatial import MNGeospatialExtractor
from ..sources.fgdb import FGDBExtractor
from ..sources.local_file import LocalFileExtractor

logger = logging.getLogger(__name__)

# Map source types to extractor classes
EXTRACTOR_CLASSES = {
    "mn_geospatial": MNGeospatialExtractor,
    "fgdb": FGDBExtractor,
    "local": LocalFileExtractor,
}


def extract_spatial_data(
    dataset_name: str,
    output_dir: Optional[str] = None,
    output_format: str = "geoparquet",
    create_zip: bool = False,
    note: Optional[str] = None,
    config: Optional[SpatialDataConfig] = None,
) -> Dict[str, Any]:
    """Extract spatial dataset - mirrors sensing_data.extract_data() signature.

    Args:
        dataset_name: Name of the dataset to extract
        output_dir: Output directory (default: ./data)
        output_format: Output format - geoparquet, shapefile, or csv
        create_zip: Whether to create zip archive
        note: Optional note for logging
        config: Optional configuration (if None, loads from file/defaults)

    Returns:
        Dictionary with extraction results
    """
    start_time = datetime.now()

    try:
        # 0. Load configuration if not provided
        if config is None:
            config = get_config()

        # 1. Look up dataset configuration based on mode
        dataset_config = get_dataset_config_by_mode(
            dataset_name,
            mode=config.mode,
            local_directory=config.data.get_local_directory(),
            local_prefix=config.data.local_prefix
        )
        if not dataset_config:
            raise ValueError(
                f"Unknown dataset: {dataset_name} (mode: {config.mode})"
            )

        logger.info(f"Starting extraction of dataset: {dataset_name}")

        # 2. Get appropriate extractor class
        source_type = dataset_config["source_type"]
        extractor_class = EXTRACTOR_CLASSES.get(source_type)

        if not extractor_class:
            raise ValueError(f"No extractor available for source type: {source_type}")

        # 3. Create extractor instance and extract data
        extractor = extractor_class(dataset_config)
        gdf = extractor.extract()

        # 3.5 Apply attribute filter if specified
        if "attribute_filter" in dataset_config and not gdf.empty:
            filter_config = dataset_config["attribute_filter"]
            columns = filter_config.get("columns", [])
            values = filter_config.get("values", [])
            match_type = filter_config.get("match_type", "any")

            if columns and values:
                logger.info(f"Applying attribute filter: {filter_config.get('description', 'No description')}")
                original_count = len(gdf)

                try:
                    # Create a mask for rows where ANY column contains ANY of the target values
                    import pandas as pd
                    mask = pd.Series([False] * len(gdf))

                    for col in columns:
                        if col in gdf.columns:
                            mask |= gdf[col].isin(values)
                        else:
                            logger.warning(f"Column '{col}' not found in dataset")

                    gdf = gdf[mask]

                    filtered_count = len(gdf)
                    if original_count > 0:
                        logger.info(f"Filter applied: {original_count} features -> {filtered_count} features ({filtered_count/original_count*100:.1f}% retained)")
                    else:
                        logger.info(f"Filter applied: {filtered_count} features extracted")
                except Exception as e:
                    logger.error(f"Failed to apply attribute filter: {e}")
                    logger.warning("Continuing with unfiltered data")

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
            "note": note,
        }

        # 6. Log extraction to database (if enabled in config)
        if config.database.logging_enabled:
            try:
                with SpatialDataLogger() as db_logger:
                    db_logger.log_extraction(results)
            except Exception as e:
                logger.warning(f"Failed to log extraction to database: {e}")
        else:
            logger.debug("Database logging disabled in configuration")

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
            "note": note,
        }

        logger.error(f"Failed to extract dataset {dataset_name}: {e}")
        raise RTGSLabToolsError(f"Spatial data extraction failed: {e}") from e


def _save_to_file(
    gdf, dataset_name: str, output_dir: str, output_format: str, create_zip: bool
):
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
        gdf.to_parquet(file_path, compression="snappy")
        logger.info(f"Saved as GeoParquet with snappy compression")

    elif output_format.lower() == "shapefile":
        file_path = output_path / f"{dataset_name}.shp"
        gdf.to_file(file_path, driver="ESRI Shapefile")
        logger.info(f"Saved as Shapefile")

    elif output_format.lower() == "csv":
        file_path = output_path / f"{dataset_name}.csv"
        # Convert geometry to WKT for CSV export
        gdf_csv = gdf.copy()
        gdf_csv["geometry"] = gdf_csv["geometry"].apply(lambda x: x.wkt)
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

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            if output_format.lower() == "shapefile":
                # Include all shapefile components
                for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                    shp_file = file_path.with_suffix(ext)
                    if shp_file.exists():
                        zipf.write(shp_file, shp_file.name)
            else:
                # Single file formats
                zipf.write(file_path, file_path.name)

        logger.info(f"Created zip archive: {zip_path}")
        return str(zip_path), file_size_mb

    return str(file_path), file_size_mb


# Extension to format mapping for extract_from_path
_EXTENSION_FORMAT_MAP = {
    ".shp": "shapefile",
    ".gpkg": "geopackage",
    ".geoparquet": "parquet",
    ".parquet": "parquet",
    ".geojson": "geojson",
    ".json": "geojson",
    ".zip": "zip",
    ".gdb": "fgdb",
}


def extract_from_path(
    file_path: str,
    layer_name: Optional[str] = None,
    target_crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """Extract spatial data directly from a file path, bypassing the registry.

    Detects format by file extension and uses the appropriate extractor.
    Returns a validated, CRS-standardized GeoDataFrame.

    Args:
        file_path: Path to spatial data file (.shp, .gpkg, .parquet, .geojson, .gdb, .zip)
        layer_name: Optional layer name for multi-layer formats (FGDB, GeoPackage)
        target_crs: Target CRS for standardization (default: EPSG:4326)

    Returns:
        GeoDataFrame with standardized CRS

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file format is not supported
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    # Handle FGDB directories (end in .gdb)
    if suffix == ".gdb" or (path.is_dir() and path.name.endswith(".gdb")):
        config = {
            "source_type": "fgdb",
            "layer_name": layer_name,
        }
        extractor = FGDBExtractor(config, fgdb_path=str(path))
        gdf = extractor.extract()
    elif suffix in (".shp", ".gpkg", ".geoparquet", ".parquet", ".geojson", ".json", ".zip"):
        config = {
            "source_type": "local",
            "file_path": str(path),
            "layer_name": layer_name,
        }
        extractor = LocalFileExtractor(config)
        gdf = extractor.extract()
    else:
        raise ValueError(
            f"Unsupported file format: {suffix}. "
            f"Supported: {', '.join(sorted(_EXTENSION_FORMAT_MAP.keys()))}"
        )

    # Ensure target CRS
    if gdf.crs is None:
        logger.warning(f"No CRS defined, assuming {target_crs}")
        gdf = gdf.set_crs(target_crs)
    elif str(gdf.crs) != target_crs:
        gdf = gdf.to_crs(target_crs)

    return gdf
