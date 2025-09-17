# Spatial Data Module

**Status:** ETL Pipeline Complete - PRODUCTION READY  
**Branch:** `ben/etl-pipeline-v0`  
**Output Format:** GeoParquet + PostGIS Database Logging

## Overview

The `spatial_data` module provides extraction and processing capabilities for geospatial datasets required by the Hennepin County Parcel Prioritization Model. This module operates as a parallel system to the existing `sensing_data` module, designed specifically for spatial data sources.

## Architecture

This module implements the **Parallel Module Architecture** following software engineering best practices:

- **Clean Separation**: Spatial data processing separate from time-series sensor data
- **Infrastructure Reuse**: Leverages 85% of existing rtgs-lab-tools infrastructure
- **Native Spatial Operations**: Uses GeoPandas GeoDataFrames (not forced measurement schemas)
- **Extractors Pattern**: Purpose-built extractors for each data source type (not parsers)

## Implementation Status

### ✅ COMPLETED - Full ETL Pipeline
- [x] **Core Infrastructure** - Extractor classes, registry, CLI integration
- [x] **Data Sources** - MN Geospatial Commons (vector & raster support)
- [x] **File Export** - GeoParquet (primary), Shapefile, CSV formats
- [x] **Database Integration** - PostGIS logging and metadata catalog
- [x] **CLI Commands** - Complete extraction workflow
- [x] **Production Testing** - End-to-end validation with real datasets

### 📊 Verified Pipeline Results
**Vector Dataset (protected_areas):**
- 1,731 MultiPolygon features extracted in 0.8 seconds
- Output: 2.9 MB GeoParquet file
- CRS transformation: EPSG:26915 → EPSG:4326

**Raster Dataset (groundwater_recharge):** 
- 201,264 polygon features (raster-to-vector) in 14.5 seconds
- Output: 5.6 MB GeoParquet file
- Spatial processing: AAIGRID → polygon conversion

### 🎯 Next Phase - Scale & Expand
- [ ] Add remaining 18+ MN Geospatial datasets to registry
- [ ] Implement additional data sources (Google Earth Engine, etc.)
- [ ] Add automated update detection and scheduling

## Quick Start

### Prerequisites
```bash
# Spatial dependencies
pip install geopandas rasterio requests sqlalchemy
```

### Available Commands
```bash
# List available datasets
rtgs spatial-data list-datasets

# Test extraction (no file output)
rtgs spatial-data test --dataset protected_areas

# Extract with file output (default: GeoParquet)
rtgs spatial-data extract --dataset protected_areas

# Extract with specific format
rtgs spatial-data extract --dataset groundwater_recharge --output-format geoparquet

# Extract to custom directory
rtgs spatial-data extract --dataset protected_areas --output-dir ./custom_data
```

## Dataset Registry

**Available Datasets:**
- `protected_areas` - DNR Wildlife Management Areas (1,731 polygons)
- `groundwater_recharge` - Mean annual groundwater recharge 1996-2010 (201k grid cells)

**Supported Formats:**
- **GeoParquet** (recommended) - Optimal performance and compression
- **Shapefile** - Maximum GIS compatibility 
- **CSV+WKT** - Simple text format for basic sharing

## Module Structure

```
spatial_data/
├── __init__.py                    # Lazy loading interface
├── README.md                      # This file
├── cli.py                         # CLI commands
├── db_schema.sql                  # PostGIS database schema
├── db_logger.py                   # Database integration
├── core/
│   ├── __init__.py
│   └── extractor.py              # Main ETL orchestrator
├── sources/
│   ├── __init__.py
│   ├── base.py                   # SpatialSourceExtractor base class
│   └── mn_geospatial.py         # MN Geospatial Commons extractor
└── registry/
    ├── __init__.py
    └── dataset_registry.py       # Dataset configuration
```

## Design Principles

### 1. Extractors vs Parsers
- **Extractors**: Acquire data from external sources + process it
- **Parsers**: Transform already-retrieved data
- Spatial data needs **extractors** because data lives in external systems

### 2. Infrastructure Reuse
```python
# Reuses existing rtgs-lab-tools components:
from ...core import Config, PostgresLogger, GitLogger
from ...core.exceptions import ValidationError, RTGSLabToolsError
```

### 3. Native Spatial Data Structures
```python
# Returns GeoDataFrames, not measurement records
def extract(self) -> gpd.GeoDataFrame:
    # Natural spatial operations: coordinate transforms, spatial validation
```

## Python API

```python
from rtgs_lab_tools.spatial_data import extract_spatial_data

# Extract to GeoParquet file
result = extract_spatial_data(
    dataset_name="protected_areas",
    output_dir="./data",
    output_format="geoparquet",
    note="Production data extraction"
)

print(f"Extracted {result['records_extracted']} features")
print(f"Output file: {result['output_file']}")
print(f"File size: {result['file_size_mb']:.2f} MB")
```

## Pipeline Architecture

**Data Flow:** Extract → Transform → Export → Log
- **Extract**: Download from MN Geospatial Commons APIs
- **Transform**: CRS standardization, raster-to-vector conversion
- **Export**: Save as GeoParquet (or Shapefile/CSV)
- **Log**: Record extraction metadata in PostGIS database

**Database Schema:**
- `spatial_datasets` - Dataset catalog and metadata
- `spatial_extractions` - Extraction logs with performance metrics
- `spatial_data_quality` - Quality validation results

## Technical Decisions

**Architecture:** Parallel module design (separate from sensor data processing)
**Output Format:** GeoParquet selected for optimal performance and future-proofing
**Database:** PostGIS integration for metadata catalog and extraction logging
**Performance:** Sub-second to 15-second extractions with efficient compression

## Contributing

**Current Status:** Production-ready ETL pipeline for spatial data extraction

**Next Development Priorities:**
1. **Dataset Expansion** - Add remaining MN Geospatial Commons datasets (18+ remaining)
2. **Source Integration** - Google Earth Engine, Planet Labs, additional APIs
3. **Automation** - Scheduled updates and change detection
4. **Quality Assurance** - Enhanced validation and error handling

## Related Files

- `spatial_data_format_comparison.md` - Format analysis and decision matrix
- `db_schema.sql` - Complete PostGIS database schema
- `etl_pipeline_plan_v3.md` - Implementation planning document