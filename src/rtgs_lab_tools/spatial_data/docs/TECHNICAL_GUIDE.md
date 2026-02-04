# Spatial Data Module - Technical Guide

**Version:** 1.0 (MVP + Configuration Modes)
**Status:** Production Ready
**Last Updated:** 2026-02-04

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration System](#configuration-system)
4. [Operational Modes](#operational-modes)
5. [Data Flow](#data-flow)
6. [Core Components](#core-components)
7. [How to Use](#how-to-use)
8. [Extending the Module](#extending-the-module)
9. [Troubleshooting](#troubleshooting)
10. [Performance Considerations](#performance-considerations)

---

## Overview

The `spatial_data` module provides unified data management for spatial (geospatial) datasets in rtgs-lab-tools. It abstracts data acquisition, validation, standardization, and storage behind a simple API, allowing other modules (like `suitability_modeling`) to work with spatial data without worrying about source-specific details.

### Key Features

- **26+ Built-in Datasets**: MN Geospatial Commons and Hennepin County FGDB
- **Local File Support**: Use your own spatial data files
- **Three Operational Modes**: built-in, local, or hybrid
- **Automatic Standardization**: CRS conversion to EPSG:4326
- **Multiple Output Formats**: GeoParquet (default), Shapefile, CSV
- **Database Logging**: Optional PostgreSQL/PostGIS audit trail
- **Configuration-Based**: YAML config files for project-specific settings

### Design Philosophy

1. **Separation of Concerns**: Data management separate from analysis
2. **Single Source of Truth**: All data passes through one pipeline
3. **Flexibility**: Support both built-in and user-provided data
4. **Reusability**: 85% infrastructure reuse from rtgs-lab-tools
5. **Extensibility**: Easy to add new data sources

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    spatial_data Module                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐         ┌────────────────┐             │
│  │ Configuration  │         │    Registry    │             │
│  │   (config.py)  │────────▶│(dataset_...py) │             │
│  └────────────────┘         └────────────────┘             │
│         │                           │                        │
│         ▼                           ▼                        │
│  ┌────────────────────────────────────────────┐            │
│  │       Main Extraction Function             │            │
│  │       (core/extractor.py)                  │            │
│  │   extract_spatial_data(dataset_name)       │            │
│  └────────────────────────────────────────────┘            │
│         │                                                    │
│         ├──────────┬──────────┬──────────┐                 │
│         ▼          ▼          ▼          ▼                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │   MN     │ │   FGDB   │ │  Local   │ │  Future  │    │
│  │Geospatial│ │Extractor │ │   File   │ │Extractors│    │
│  │Extractor │ │          │ │Extractor │ │          │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│         │          │          │                            │
│         └──────────┴──────────┴───────────┐               │
│                                            ▼               │
│                                  ┌────────────────┐        │
│                                  │  GeoDataFrame  │        │
│                                  │  (validated &  │        │
│                                  │ standardized)  │        │
│                                  └────────────────┘        │
│                                            │               │
│         ┌──────────────────────────────────┤               │
│         ▼                                  ▼               │
│  ┌────────────┐                    ┌────────────┐         │
│  │   Output   │                    │  Database  │         │
│  │   Files    │                    │   Logger   │         │
│  │(GeoParquet,│                    │(PostgreSQL)│         │
│  │ Shapefile) │                    │            │         │
│  └────────────┘                    └────────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Module Structure

```
spatial_data/
├── __init__.py                 # Lazy loading interface
├── README.md                   # User documentation
├── cli.py                      # CLI commands
├── config.py                   # Configuration system (NEW)
├── db_logger.py                # PostgreSQL logging
│
├── core/
│   ├── __init__.py
│   └── extractor.py            # Main extraction function
│
├── sources/
│   ├── __init__.py
│   ├── base.py                 # Abstract base class
│   ├── mn_geospatial.py        # MN Geospatial extractor
│   ├── fgdb.py                 # File Geodatabase extractor
│   └── local_file.py           # Local file extractor (NEW)
│
├── registry/
│   ├── __init__.py
│   └── dataset_registry.py     # Dataset configuration
│
└── docs/
    ├── TECHNICAL_GUIDE.md      # This file
    ├── README.md
    ├── dev-notes.md            # Development history
    ├── prototype_architecture.md
    ├── geoparquet_decision_matrix.md
    ├── example-config-built-in.yaml
    ├── example-config-local.yaml
    └── example-config-hybrid.yaml
```

---

## Configuration System

### Configuration File Structure

Configuration files use YAML format (`.rtgs-config.yaml`):

```yaml
mode: built-in | local | hybrid

data:
  local_directory: ./data         # Path to user's flat files
  cache_directory: .rtgs_cache    # Cache for performance
  sources:                        # Built-in sources to enable
    - mn_geospatial
    - fgdb
  local_prefix: local             # Prefix for local datasets in hybrid mode

database:
  logging_enabled: true           # Enable/disable database logging
  # connection_string loaded from RTGS_DB_CONNECTION_STRING env var

output:
  default_format: geoparquet      # Default output format
  default_directory: ./data       # Default output directory
```

### Configuration Discovery

The module searches for configuration in this order:

1. **Explicit path**: `--config-file /path/to/config.yaml`
2. **Current directory**: `.rtgs-config.yaml`
3. **Home directory**: `~/.rtgs-config.yaml`
4. **Defaults**: If no config found, uses built-in mode

### Configuration Classes

**`SpatialDataConfig`** - Main configuration
- `mode`: Operational mode (built-in, local, hybrid)
- `data`: DataConfig instance
- `database`: DatabaseConfig instance
- `output`: OutputConfig instance

**`DataConfig`** - Data source settings
- `local_directory`: Path to local files
- `cache_directory`: Cache location
- `sources`: Enabled built-in sources
- `local_prefix`: Prefix for local datasets

**`DatabaseConfig`** - Database settings
- `logging_enabled`: Enable/disable logging
- `connection_string`: Database connection (from env var)

**`OutputConfig`** - Output preferences
- `default_format`: Default output format
- `default_directory`: Default output directory

---

## Operational Modes

### Mode 1: Built-in (Default)

**Use Case**: Minnesota-based research using curated datasets

**Configuration**:
```yaml
mode: built-in
database:
  logging_enabled: true
```

**Behavior**:
- Uses 26+ built-in datasets (MN Geospatial, FGDB)
- Downloads data from web sources
- Logs extractions to PostgreSQL database
- Requires internet connection
- Requires database configuration

**Datasets Available**:
- MN Geospatial Commons: 10 public datasets
- Hennepin County FGDB: 16 analysis datasets (if configured)

---

### Mode 2: Local

**Use Case**: Using your own spatial data, offline work, non-Minnesota regions

**Configuration**:
```yaml
mode: local
data:
  local_directory: ./data
database:
  logging_enabled: false
```

**Behavior**:
- Uses ONLY user's flat files from `local_directory`
- No web downloads
- No database required
- Files remain as flat files (not imported)
- Validation and CRS standardization performed
- Results cached in `.rtgs_cache/` for performance
- Fully offline-capable

**Supported File Formats**:
- `.shp` - Shapefiles
- `.gpkg` - GeoPackage
- `.geoparquet` / `.parquet` - GeoParquet
- `.geojson` / `.json` - GeoJSON
- `.zip` - Zipped shapefiles

**File Discovery**:
- Automatically discovers all spatial files in `local_directory`
- Dataset names derived from filenames (e.g., `parcels.shp` → `parcels`)

---

### Mode 3: Hybrid

**Use Case**: Combining built-in datasets with custom data

**Configuration**:
```yaml
mode: hybrid
data:
  local_directory: ./my_data
  local_prefix: local
database:
  logging_enabled: true
```

**Behavior**:
- Uses BOTH built-in and local datasets
- Local datasets prefixed to avoid name conflicts
- Example: `my_parcels.shp` → `local:my_parcels`
- Built-in datasets keep original names: `wildlife_areas`
- Database logging enabled for built-in datasets
- Full flexibility

**Usage in Models**:
```yaml
criteria:
  - dataset_name: "wildlife_areas"       # Built-in
  - dataset_name: "local:my_parcels"     # Local file
```

---

## Data Flow

### Extraction Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. extract_spatial_data(dataset_name, ...)                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Load Configuration                                        │
│    - Search for .rtgs-config.yaml                           │
│    - Determine mode (built-in/local/hybrid)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Lookup Dataset Configuration                             │
│    - Mode: built-in  → Check MN Geospatial/FGDB registry   │
│    - Mode: local     → Discover files in local_directory    │
│    - Mode: hybrid    → Check both, apply prefix            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Select Appropriate Extractor                             │
│    - source_type: mn_geospatial → MNGeospatialExtractor    │
│    - source_type: fgdb          → FGDBExtractor             │
│    - source_type: local         → LocalFileExtractor        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Extract Data (source-specific logic)                     │
│    MN Geospatial:                                           │
│    - Download ZIP from URL                                  │
│    - Extract spatial file (GPKG, SHP, AAIGRID)             │
│    - Or fetch from REST API with pagination                │
│                                                             │
│    FGDB:                                                    │
│    - Read layer from File Geodatabase                      │
│                                                             │
│    Local:                                                   │
│    - Read file directly from user's directory              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Validate & Standardize                                   │
│    - Check geometry validity                                │
│    - Verify CRS is defined                                  │
│    - Transform to EPSG:4326 (if needed)                     │
│    - Apply attribute filters (if configured)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Save to File (if output_dir specified)                   │
│    - GeoParquet (default, snappy compression)              │
│    - Shapefile (legacy compatibility)                       │
│    - CSV (with WKT geometry)                                │
│    - Optional: Create ZIP archive                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Log to Database (if database.logging_enabled)            │
│    - Record extraction metadata                             │
│    - Git commit hash for reproducibility                    │
│    - Performance metrics (duration, file size)              │
│    - Feature count, bounds, CRS                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. Return Results Dictionary                                │
│    {                                                        │
│      "success": true,                                       │
│      "dataset_name": "wildlife_areas",                      │
│      "records_extracted": 1746,                             │
│      "crs": "EPSG:4326",                                    │
│      "output_file": "./data/wildlife_areas.parquet",        │
│      "duration_seconds": 5.2                                │
│    }                                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Extractors (`sources/`)

**Base Class: `SpatialSourceExtractor`** (sources/base.py)

Abstract base class defining the extractor interface:

```python
class SpatialSourceExtractor(ABC):
    def __init__(self, dataset_config: Dict[str, Any], **kwargs):
        pass

    @abstractmethod
    def extract(self) -> gpd.GeoDataFrame:
        """Extract data - returns GeoDataFrame"""
        pass

    def validate_spatial_integrity(self, data: gpd.GeoDataFrame) -> bool:
        """Validate geometry and CRS"""
        pass

    def standardize_crs(self, data: gpd.GeoDataFrame, target_crs="EPSG:4326") -> gpd.GeoDataFrame:
        """Transform to standard CRS"""
        pass
```

**MN Geospatial Extractor** (sources/mn_geospatial.py)

Handles downloads from MN Geospatial Commons:

- **Download Method**: ZIP file extraction
  - Downloads ZIP from URL
  - Extracts spatial file (GPKG, SHP, AAIGRID)
  - Handles multi-layer GeoPackages
  - Supports raster-to-vector conversion (AAIGRID)

- **REST API Method**: ArcGIS FeatureServer
  - Automatic pagination for >2000 features
  - JSON to GeoDataFrame conversion
  - Handles large datasets efficiently

**FGDB Extractor** (sources/fgdb.py)

Reads from Hennepin County File Geodatabase:

- Requires `RTGS_FGDB_PATH` environment variable
- Uses fiona to read FGDB layers
- Supports layer name specification
- Conditional availability

**Local File Extractor** (sources/local_file.py) **[NEW]**

Reads user's flat files:

```python
class LocalFileExtractor(SpatialSourceExtractor):
    def __init__(self, dataset_config: Dict[str, Any], **kwargs):
        self.file_path = Path(dataset_config.get("file_path"))
        self.layer_name = dataset_config.get("layer_name")

    def extract(self) -> gpd.GeoDataFrame:
        # Auto-detect format and read
        # Supports: .shp, .gpkg, .geoparquet, .geojson, .zip
        pass
```

### 2. Registry (`registry/dataset_registry.py`)

**Built-in Datasets**:

Hardcoded dictionaries defining 26+ datasets:

```python
MN_GEOSPATIAL_DATASETS = {
    "wildlife_areas": {
        "description": "DNR Wildlife Management Areas",
        "source_type": "mn_geospatial",
        "download_url": "https://...",
        "access_method": "download",
        "file_format": "geopackage",
        "coordinate_system": "EPSG:26915",
        "expected_features": 1731,
    },
    # ... more datasets
}
```

**Mode-Based Functions** [NEW]:

```python
def list_datasets_by_mode(mode, local_directory, local_prefix):
    """List datasets based on operational mode"""
    if mode == "built-in":
        return built_in_datasets
    elif mode == "local":
        return discover_local_datasets(local_directory)
    elif mode == "hybrid":
        return {**built_in_datasets, **prefixed_local_datasets}
```

### 3. Database Logger (`db_logger.py`)

**`SpatialDataLogger`** class:

Logs extraction metadata to PostgreSQL with PostGIS:

```python
with SpatialDataLogger() as logger:
    logger.log_extraction({
        "dataset_name": "wildlife_areas",
        "records_extracted": 1746,
        "duration_seconds": 5.2,
        "file_size_mb": 2.3,
        "git_commit": "abc123",
        "note": "User note here"
    })
```

**Database Tables**:
- `spatial_datasets`: Dataset metadata
- `spatial_extractions`: Extraction history with timestamps

**Features**:
- Context manager for connection handling
- Git commit tracking for reproducibility
- Query methods for analytics
- Graceful failure (warns but doesn't crash)

---

## How to Use

### Quick Start

**1. Built-in Mode (Default)**

```bash
# List available datasets
rtgs spatial-data list-datasets

# Extract a dataset
rtgs spatial-data extract --dataset wildlife_areas --output-dir ./data
```

**2. Local Mode**

```bash
# Create local mode configuration
rtgs spatial-data create-config \
  --mode local \
  --local-data-dir ./my_data \
  --no-database-logging

# Place your files in ./my_data/
cp my_parcels.shp ./my_data/

# List datasets (shows your files)
rtgs spatial-data list-datasets

# Extract your data
rtgs spatial-data extract --dataset my_parcels --output-dir ./results
```

**3. Hybrid Mode**

```bash
# Create hybrid configuration
rtgs spatial-data create-config \
  --mode hybrid \
  --local-data-dir ./my_data

# List datasets (shows both)
rtgs spatial-data list-datasets

# Extract built-in dataset
rtgs spatial-data extract --dataset wildlife_areas --output-dir ./data

# Extract local dataset
rtgs spatial-data extract --dataset local:my_parcels --output-dir ./data
```

### Programmatic Usage

```python
from rtgs_lab_tools.spatial_data import extract_spatial_data

# Extract dataset
result = extract_spatial_data(
    dataset_name="wildlife_areas",
    output_dir="./data",
    output_format="geoparquet",
    note="For suitability analysis"
)

print(f"Extracted {result['records_extracted']} features")
print(f"Output: {result['output_file']}")
```

### With Custom Configuration

```python
from rtgs_lab_tools.spatial_data import extract_spatial_data, SpatialDataConfig, DataConfig, DatabaseConfig
from pathlib import Path

# Create custom config
config = SpatialDataConfig(
    mode="local",
    data=DataConfig(local_directory="./my_data"),
    database=DatabaseConfig(logging_enabled=False)
)

# Use with extraction
result = extract_spatial_data(
    dataset_name="my_parcels",
    output_dir="./results",
    config=config
)
```

### Integration with suitability_modeling

The `suitability_modeling` module automatically uses `spatial_data`:

```yaml
# model.yaml
criteria:
  - dataset_name: "wildlife_areas"        # Built-in or local, transparent
    criterion_name: "Proximity to Wildlife Areas"
    scoring_function:
      type: distance_decay
      params:
        max_distance: 5000
    weight: 60.0
```

```bash
# Just run the model - spatial_data handles data acquisition
rtgs suitability-modeling execute model.yaml
```

---

## Extending the Module

### Adding a New Extractor

1. **Create Extractor Class** in `sources/`:

```python
# sources/my_source.py
from .base import SpatialSourceExtractor
import geopandas as gpd

class MySourceExtractor(SpatialSourceExtractor):
    def __init__(self, dataset_config, **kwargs):
        super().__init__(dataset_config, **kwargs)
        self.api_url = dataset_config.get("api_url")

    def extract(self) -> gpd.GeoDataFrame:
        # 1. Fetch data from your source
        data = self._fetch_from_api()

        # 2. Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame(data)

        # 3. Validate
        self.validate_spatial_integrity(gdf)

        # 4. Standardize CRS
        gdf = self.standardize_crs(gdf)

        return gdf

    def _fetch_from_api(self):
        # Your data acquisition logic
        pass
```

2. **Register Extractor** in `core/extractor.py`:

```python
EXTRACTOR_CLASSES = {
    "mn_geospatial": MNGeospatialExtractor,
    "fgdb": FGDBExtractor,
    "local": LocalFileExtractor,
    "my_source": MySourceExtractor,  # Add here
}
```

3. **Add Datasets** to `registry/dataset_registry.py`:

```python
MY_SOURCE_DATASETS = {
    "my_dataset": {
        "description": "My custom dataset",
        "source_type": "my_source",
        "api_url": "https://api.example.com/data",
        # ... other metadata
    }
}
```

### Adding New Datasets to Existing Sources

**MN Geospatial Commons**:

Add to `MN_GEOSPATIAL_DATASETS` in `registry/dataset_registry.py`:

```python
"new_dataset": {
    "description": "Description here",
    "source_type": "mn_geospatial",
    "download_url": "https://resources.gisdata.mn.gov/...",
    "access_method": "download",  # or "rest_api"
    "file_format": "geopackage",
    "coordinate_system": "EPSG:26915",
    "layer_name": "layer_name",  # Optional for multi-layer GPKG
}
```

**File Geodatabase**:

Add to `FGDB_DATASETS` in `registry/dataset_registry.py`:

```python
"new_fgdb_dataset": {
    "description": "Description here",
    "source_type": "fgdb",
    "layer_name": "LayerName",
    "expected_features": 1000,
}
```

---

## Troubleshooting

### Common Issues

**1. "Dataset not found"**

```
ValueError: Unknown dataset: my_dataset
```

**Solutions**:
- Check dataset name spelling
- Run `rtgs spatial-data list-datasets` to see available datasets
- Verify configuration mode matches dataset source
- In local mode, ensure file exists in `local_directory`

**2. "Local directory does not exist"**

```
ValueError: Local directory does not exist: ./data
```

**Solutions**:
- Create the directory: `mkdir -p ./data`
- Update config with correct path
- Use absolute path instead of relative

**3. "FGDB not available"**

```
Dataset 'habitat_diversity' is in FGDB registry but FGDB not configured
```

**Solutions**:
- Set environment variable: `export RTGS_FGDB_PATH=/path/to/file.gdb`
- Or switch to MN Geospatial datasets only

**4. Database logging fails**

```
WARNING: Failed to log extraction to database: Connection refused
```

**Solutions**:
- Disable database logging in local mode: `logging_enabled: false`
- Check database connection string
- Verify PostgreSQL is running
- This is a warning - extraction still succeeds

**5. CRS transformation warnings**

```
WARNING: No CRS defined, assuming EPSG:4326
```

**Solutions**:
- Ensure input files have defined CRS
- GeoPandas will assume EPSG:4326 and continue
- Verify output is correct

**6. Import errors**

```
ImportError: geopandas is required for spatial data extraction
```

**Solutions**:
- Install dependencies: `pip install geopandas fiona pyogrio`
- Or install full package: `pip install rtgs-lab-tools[spatial]`

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or via environment:
```bash
export RTGS_LOG_LEVEL=DEBUG
rtgs spatial-data extract --dataset wildlife_areas
```

---

## Performance Considerations

### Caching

**Local Mode Caching**:
- First extraction: Validates, standardizes, caches in `.rtgs_cache/`
- Subsequent extractions: Loads from cache (much faster)
- Cache invalidation: Delete `.rtgs_cache/` to force re-processing

**Built-in Mode**:
- Downloads to temp directory
- No persistent cache (re-downloads each time)
- Consider saving to permanent location for reuse

### Large Datasets

**Memory Management**:
- Entire GeoDataFrame loaded into memory
- Large datasets (>100MB) may require significant RAM
- Consider using grid sampling in `suitability_modeling`

**Optimization Tips**:
- Use GeoParquet format (50% smaller than Shapefile)
- Apply attribute filters to reduce dataset size
- Use spatial subsets (clip to study area) early

### Parallel Extraction

Not currently supported - future enhancement:

```python
# Future API
results = extract_spatial_data_batch(
    dataset_names=["dataset1", "dataset2", "dataset3"],
    max_workers=3
)
```

---

## API Reference

### Main Functions

**`extract_spatial_data(dataset_name, output_dir, output_format, create_zip, note, config)`**

Extract and process spatial dataset.

**Parameters**:
- `dataset_name` (str): Name of dataset to extract
- `output_dir` (Optional[str]): Output directory (None = database only)
- `output_format` (str): Format - "geoparquet", "shapefile", "csv"
- `create_zip` (bool): Create ZIP archive
- `note` (Optional[str]): Note for logging
- `config` (Optional[SpatialDataConfig]): Configuration instance

**Returns**: Dict with extraction results

---

**`list_datasets_by_mode(mode, local_directory, local_prefix)`**

List available datasets based on mode.

**Parameters**:
- `mode` (str): "built-in", "local", or "hybrid"
- `local_directory` (Optional[Path]): Path to local files
- `local_prefix` (str): Prefix for local datasets

**Returns**: Dict of dataset_name: config

---

**`SpatialDataConfig.from_yaml(config_path)`**

Load configuration from YAML file.

**Parameters**:
- `config_path` (Path): Path to config file

**Returns**: SpatialDataConfig instance

---

## Version History

**v1.0 (2026-02-04)** - Configuration Modes
- Added local file support
- Three operational modes (built-in, local, hybrid)
- Configuration system
- LocalFileExtractor

**v0.1.0 (2025-10-20)** - MVP Release
- 26+ built-in datasets
- MN Geospatial and FGDB support
- CLI commands
- Database logging
- Production ready

---

## Related Documentation

- **README.md**: User guide and quick start
- **dev-notes.md**: Development history and lessons learned
- **prototype_architecture.md**: Detailed architectural decisions
- **geoparquet_decision_matrix.md**: GeoParquet format justification
- **example-config-*.yaml**: Configuration examples

---

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/your-org/rtgs-lab-tools/issues
- Documentation: See README.md and docs/
- Contact: RTGS Lab, University of Minnesota
