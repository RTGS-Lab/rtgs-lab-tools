# Spatial Data Module

**Status:** ETL Pipeline Complete - Prototype Complete  
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

### ✅ COMPLETED - Full ETL Pipeline Prototype
- [x] **Core Infrastructure** - Extractor classes, registry, CLI integration
- [x] **Data Sources** - MN Geospatial Commons (vector & raster support)
- [x] **File Export** - GeoParquet (primary), Shapefile, CSV formats
- [x] **Database Integration** - PostGIS logging and metadata catalog
- [x] **CLI Commands** - Complete extraction workflow
- [x] **Production Testing** - End-to-end validation with real datasets

### 📊 Verified Pipeline Results
**Vector Dataset (wildlife_areas):**
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

### CLI Commands Reference

#### 1. `list-datasets` - Dataset Discovery
**Purpose:** Display all available datasets with their descriptions, source types, and spatial types.

```bash
rtgs spatial-data list-datasets
```

**Options:** None

**Use Case:** Discover what datasets are available before extraction.

---

#### 2. `test` - Validation Testing
**Purpose:** Test dataset extraction without saving files (database-only mode). Useful for validating accessibility and checking feature counts before full extraction.

```bash
rtgs spatial-data test --dataset <dataset_name>
```

**Options:**
- `--dataset` (required) - Name of dataset to test

**Example:**
```bash
rtgs spatial-data test --dataset aquatic_areas
# Output: SUCCESS: Test successful! Features: 1571, Duration: 1.2s
```

---

#### 3. `extract` - Single Dataset Extraction
**Purpose:** Extract a single spatial dataset with full control over output format and location.

```bash
rtgs spatial-data extract --dataset <dataset_name> [OPTIONS]
```

**Options:**
- `--dataset` (required) - Dataset name to extract
- `--output-dir` (optional) - Output directory (if omitted, database-only mode)
- `--output-format` (optional) - Choose format: `geoparquet` | `shapefile` | `csv` (default: geoparquet)
- `--create-zip` (optional flag) - Create zip archive of output files
- `--note` (optional) - Add note for logging/documentation

**Operational Modes:**

**Mode 1: Database-only (no files saved locally)**
```bash
rtgs spatial-data extract --dataset wildlife_areas
```

**Mode 2: Database + File Output**
```bash
# Extract as GeoParquet (default, recommended)
rtgs spatial-data extract --dataset wildlife_areas --output-dir ./data

# Extract as Shapefile for GIS compatibility
rtgs spatial-data extract --dataset wildlife_areas --output-dir ./data --output-format shapefile

# Extract with documentation note
rtgs spatial-data extract --dataset wildlife_areas --output-dir ./data --note "Q4 2025 parcel analysis"

# Extract and create zip archive
rtgs spatial-data extract --dataset wildlife_areas --output-dir ./data --create-zip
```

---

#### 4. `extract-all` - Batch Extraction
**Purpose:** Extract ALL available datasets in one command with progress tracking and summary reporting.

```bash
rtgs spatial-data extract-all [OPTIONS]
```

**Options:**
- `--output-dir` (optional) - Output directory (if omitted, database-only mode)
- `--output-format` (optional) - Choose format: `geoparquet` | `shapefile` | `csv` (default: geoparquet)
- `--create-zip` (optional flag) - Create zip archives for all outputs
- `--note` (optional) - Add note for logging/documentation
- `--continue-on-error` (optional flag) - Continue processing remaining datasets if one fails

**Examples:**
```bash
# Extract all to database only (no files)
rtgs spatial-data extract-all

# Extract all datasets as Shapefiles
rtgs spatial-data extract-all --output-dir ./data --output-format shapefile

# Extract all with resilience (don't stop on errors)
rtgs spatial-data extract-all --output-dir ./data --continue-on-error

# Extract all with documentation
rtgs spatial-data extract-all --output-dir ./data --note "Complete dataset refresh for Q4 analysis"
```

**Example Output:**
```
Extracting all 10 available datasets
[1/10] Extracting: wildlife_areas
  [SUCCESS] 1731 features in 0.9s
    File: ./data/wildlife_areas.parquet (2.90 MB)
[2/10] Extracting: groundwater_recharge
  [SUCCESS] 201264 features in 13.5s
...
============================================================
EXTRACTION SUMMARY
============================================================
Total datasets: 10
Succeeded: 10
Failed: 0
```

---

### Quick Command Reference

| Command | Purpose | Required Options | Common Use |
|---------|---------|-----------------|------------|
| `list-datasets` | Show all available datasets | None | Discovery |
| `test` | Validate dataset access | `--dataset` | Pre-extraction check |
| `extract` | Extract single dataset | `--dataset` | Targeted extraction |
| `extract-all` | Extract all datasets | None | Batch processing |

## Dataset Registry

**Available Datasets:**
- `wildlife_areas` - DNR Wildlife Management Areas (1,731 polygons)
- `groundwater_recharge` - Mean annual groundwater recharge 1996-2010 (201k grid cells)
- `scientific_and_natural_areas` - DNR Scientific and Natural Areas (237 polygons)
- `TNC_lands` - The Nature Conservancy lands in MN, ND, & SD (383 polygons)
- `aquatic_areas` - DNR Fisheries Acquisition - Aquatic Management Areas (1,571 polygons)
- `MBS_sites` - Minnesota County Biological Survey - Sites of Biodiversity Significance (12,591 polygons)
- `WAN` - Wildlife Action Network - Minnesota Wildlife Action Plan Network (133,283 polygons)
- `land_use` - Generalized Land Use 2020 - Metropolitan Council Regional Land Use (22 polygons)
- `cemeteries` - Cemeteries from Regional Parcels (filtered to cemetery parcels only) (108 polygons)
- `watersheds` - DNR Level 9 Watersheds - Hydrologic Unit Boundaries (131,411 polygons)

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

# Extract to database only (no file output)
result = extract_spatial_data(
    dataset_name="wildlife_areas",
    note="Database catalog only"
)

# Extract and save to GeoParquet file
result = extract_spatial_data(
    dataset_name="wildlife_areas",
    output_dir="./data",
    output_format="geoparquet",
    note="Production data extraction"
)

print(f"Extracted {result['records_extracted']} features")
if result.get('output_file'):
    print(f"Output file: {result['output_file']}")
    print(f"File size: {result['file_size_mb']:.2f} MB")
else:
    print("Data logged to database only")
```

## Pipeline Architecture

**Data Flow:** Extract → Transform → Export (Optional) → Log
- **Extract**: Download from MN Geospatial Commons APIs
- **Transform**: CRS standardization, raster-to-vector conversion
- **Export**: Optionally save as GeoParquet (or Shapefile/CSV) to local storage
- **Log**: Record extraction metadata in PostGIS database

### Flexible Output Options

The module supports two operational modes:

1. **Database Catalog Only** - Extract and log metadata without saving files locally
   - Useful for cataloging available data
   - Minimal disk space usage
   - Quick validation of datasets

2. **Database + File Output** - Extract, save to file, and log metadata
   - Full spatial data available for analysis
   - Choose output format (GeoParquet, Shapefile, CSV)
   - Custom output directory

This flexibility allows you to catalog datasets in the database and only save files to local storage when needed for specific analysis tasks.

### Batch Extraction

The `extract-all` command allows you to extract all available datasets at once:

**Features:**
- Extract all 10 datasets in a single command
- Progress tracking with [n/total] counter
- Detailed summary report at completion
- Optional `--continue-on-error` flag to continue if one dataset fails
- Same output options as single extraction (database-only or with files)

**Example output:**
```
Extracting all 10 available datasets
[1/10] Extracting: wildlife_areas
  [SUCCESS] 1731 features in 0.9s
[2/10] Extracting: groundwater_recharge
  [SUCCESS] 201264 features in 13.5s
[3/10] Extracting: aquatic_areas
  [SUCCESS] 1571 features in 1.2s
...
EXTRACTION SUMMARY
Total datasets: 10
Succeeded: 10
Failed: 0
```

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