# Spatial Data Module

**Status:** Production Ready

**Version:** 1.1.0

**Output Format:** GeoParquet (primary), Shapefile, CSV

## Overview

The `spatial_data` module provides unified extraction and processing capabilities for geospatial datasets. It serves as the **single data management layer** for all spatial data in rtgs-lab-tools, supporting:

- **FGDB (File Geodatabase)** - Hennepin County analysis datasets (16 layers)
- **MN Geospatial Commons** - Public Minnesota datasets (10+ sources)
- **Local files** - Shapefiles, GeoPackages, GeoParquet, GeoJSON, ZIP archives
- **Directories** - Batch extraction from a folder of spatial files
- **Grid generation** - Regular grid cells from any boundary polygon
- **Schema introspection** - Dataset metadata for LLM prompts

This module is used by the `suitability_modeling` module for AI-powered spatial analysis.

## Quick Start

### Prerequisites

```bash
# Install spatial dependencies
pip install geopandas fiona rasterio requests

# For FGDB support (Hennepin County datasets)
export RTGS_FGDB_PATH="/path/to/HC_EasementAnalysis_Model_Inputs_2020.gdb"
```

### Basic Usage

```bash
# List all available datasets
rtgs spatial-data list-datasets

# Extract a single dataset
rtgs spatial-data extract --dataset wildlife_areas --output-dir ./data

# Extract all datasets
rtgs spatial-data extract-all --output-dir ./data
```

## Data Sources

### FGDB Datasets (Hennepin County)

Requires `RTGS_FGDB_PATH` environment variable pointing to the File Geodatabase.

| Dataset | Description | Features |
|---------|-------------|----------|
| `bee_habitat` | Pollinator habitat suitability | 2 |
| `floodplains` | Floodplain scoring | 2 |
| `hennepin_wetland_inventory` | Comprehensive wetland mapping | 56,018 |
| `habitat_diversity` | Ecosystem diversity scoring | 51 |
| `headwaters` | Stream headwater catchments | 1,447 |
| `important_bird_areas` | Audubon designated bird areas | 6 |
| `mbs_sites` | MN Biological Survey sites | 318 |
| `land_cover` | MLCCS land cover classification | 46,745 |
| `groundwater_recharge_hc` | Groundwater recharge rates | 2,884 |
| `natural_spaces` | Protected natural areas | 1 |
| `protected_areas_hc` | Protected lands composite | 1 |
| `quality_community` | Community quality metrics | 1 |
| `risk_of_development` | Development pressure scoring | 3 |
| `shoreland_buffers` | Lake and stream buffer zones | 1 |
| `groundwater_susceptibility` | Aquifer vulnerability | 976 |
| `wildlife_action_network` | Wildlife corridor ranking | 1,564 |

### MN Geospatial Commons (Public)

Always available without configuration.

| Dataset | Description | Features |
|---------|-------------|----------|
| `wildlife_areas` | DNR Wildlife Management Areas | 1,731 |
| `scientific_and_natural_areas` | DNR Scientific and Natural Areas | 237 |
| `aquatic_areas` | DNR Aquatic Management Areas | 1,571 |
| `MBS_sites` | Sites of Biodiversity Significance | 12,591 |
| `WAN` | Wildlife Action Network | 133,283 |
| `land_use` | Generalized Land Use 2020 | 22 |
| `watersheds` | DNR Level 9 Watersheds | 131,411 |
| `groundwater_recharge` | Groundwater recharge rates | 201,264 |
| `TNC_lands` | The Nature Conservancy lands | 383 |
| `cemeteries` | Regional cemeteries | 108 |

## CLI Commands

### `list-datasets` - Dataset Discovery

Display all available datasets with descriptions.

```bash
rtgs spatial-data list-datasets
```

### `test` - Validation Testing

Test dataset extraction without saving files.

```bash
rtgs spatial-data test --dataset wildlife_areas
```

### `extract` - Single Dataset Extraction

Extract a single dataset with full control over output.

```bash
# Extract as GeoParquet (default)
rtgs spatial-data extract --dataset wildlife_areas --output-dir ./data

# Extract as Shapefile
rtgs spatial-data extract --dataset wildlife_areas --output-dir ./data --output-format shapefile

# Extract FGDB dataset
rtgs spatial-data extract --dataset habitat_diversity --output-dir ./data
```

**Options:**
- `--dataset` (required) - Dataset name
- `--output-dir` - Output directory (omit for database-only mode)
- `--output-format` - `geoparquet` | `shapefile` | `csv` (default: geoparquet)
- `--create-zip` - Create zip archive
- `--note` - Add documentation note

### `extract-all` - Batch Extraction

Extract all available datasets at once.

```bash
rtgs spatial-data extract-all --output-dir ./data --continue-on-error
```

**Options:**
- `--output-dir` - Output directory
- `--output-format` - Output format (default: geoparquet)
- `--continue-on-error` - Continue if one dataset fails

## Python API

### Registry-based Extraction

```python
from rtgs_lab_tools.spatial_data import (
    extract_spatial_data,
    list_available_datasets,
    get_dataset_source,
    is_fgdb_available
)

# Check what's available
datasets = list_available_datasets()
print(f"Available: {len(datasets)} datasets")
print(f"FGDB configured: {is_fgdb_available()}")

# Extract a dataset
result = extract_spatial_data(
    dataset_name="wildlife_areas",
    output_dir="./data",
    output_format="geoparquet"
)

print(f"Extracted {result['records_extracted']} features")
print(f"Output: {result['output_file']}")
```

### Direct File Extraction (v1.1.0)

Extract from any spatial file without going through the registry.

```python
from rtgs_lab_tools.spatial_data import extract_from_path

# Single file — shapefile, GeoPackage, GeoParquet, GeoJSON, or ZIP
gdf = extract_from_path("path/to/wetlands.shp")
gdf = extract_from_path("path/to/data.gpkg", layer_name="parcels")
gdf = extract_from_path("path/to/features.parquet")
```

### Batch Extraction (v1.1.0)

Load all layers from a directory or FGDB at once.

```python
from rtgs_lab_tools.spatial_data import (
    extract_all_from_directory,
    extract_all_fgdb_layers,
)

# All spatial files in a directory → Dict[name, GeoDataFrame]
datasets = extract_all_from_directory("path/to/data_folder/")

# All layers from a File Geodatabase
datasets = extract_all_fgdb_layers("path/to/data.gdb")

for name, gdf in datasets.items():
    print(f"{name}: {len(gdf)} features, {gdf.geometry.geom_type.unique()}")
```

### Grid Generation (v1.1.0)

Generate regular grid cells clipped to a boundary polygon.

```python
from rtgs_lab_tools.spatial_data import generate_grid, extract_from_path

boundary = extract_from_path("study_area.shp")
grid = generate_grid(boundary, cell_size=200.0, max_cells=50000)
# Returns GeoDataFrame with grid cells in the same CRS as input
```

### Schema Introspection (v1.1.0)

Extract dataset metadata for use in LLM prompts (used by `suitability_modeling`).

```python
from rtgs_lab_tools.spatial_data import get_dataset_schema, format_schemas_for_llm

schema = get_dataset_schema("wetlands", gdf)
# Returns: {name, geometry_type, columns, feature_count}

# Format multiple schemas for an LLM prompt
schemas = [get_dataset_schema(name, gdf) for name, gdf in datasets.items()]
prompt_text = format_schemas_for_llm(schemas)
```

## Module Structure

```
spatial_data/
├── __init__.py                    # Lazy loading interface
├── README.md                      # This file
├── cli.py                         # CLI commands
├── config.py                      # Configuration management
├── db_logger.py                   # Database integration
├── core/
│   ├── __init__.py
│   ├── extractor.py              # Main ETL orchestrator + extract_from_path()
│   ├── grid.py                   # Grid generation from boundary polygons
│   └── schema.py                 # Dataset schema introspection for LLMs
├── sources/
│   ├── __init__.py
│   ├── base.py                   # SpatialSourceExtractor base class
│   ├── mn_geospatial.py          # MN Geospatial Commons extractor
│   ├── fgdb.py                   # ESRI File Geodatabase extractor + batch extraction
│   └── local_file.py             # Local file extractor + directory batch extraction
├── registry/
│   ├── __init__.py
│   └── dataset_registry.py       # Dataset configuration (FGDB + MN)
└── docs/
    ├── dev-notes.md              # Development notes and changelog
    └── *.md                      # Additional documentation
```

## Configuration

### FGDB Path

Set the `RTGS_FGDB_PATH` environment variable:

**Linux/macOS:**
```bash
export RTGS_FGDB_PATH="/path/to/HC_EasementAnalysis_Model_Inputs_2020.gdb"
```

**Windows PowerShell:**
```powershell
$env:RTGS_FGDB_PATH="C:\path\to\HC_EasementAnalysis_Model_Inputs_2020.gdb"
```

**Windows (persistent):**
1. Open Environment Variables settings
2. Add `RTGS_FGDB_PATH` as user variable
3. Restart terminal

## Output Formats

| Format | Extension | Best For |
|--------|-----------|----------|
| **GeoParquet** | `.parquet` | Performance, compression, cloud workflows |
| **Shapefile** | `.shp` | GIS software compatibility |
| **CSV** | `.csv` | Simple sharing, spreadsheets |

GeoParquet is recommended for most use cases (50% smaller than Shapefile).

## Architecture

### Extractor Pattern

Each data source has a dedicated extractor class:

```python
class FGDBExtractor(SpatialSourceExtractor):
    """Extracts from ESRI File Geodatabase."""
    def extract(self) -> gpd.GeoDataFrame:
        ...

class MNGeospatialExtractor(SpatialSourceExtractor):
    """Extracts from MN Geospatial Commons."""
    def extract(self) -> gpd.GeoDataFrame:
        ...

class LocalFileExtractor(SpatialSourceExtractor):
    """Extracts from local spatial files."""
    def extract(self) -> gpd.GeoDataFrame:
        ...
```

### Two Access Modes

1. **Registry mode** — `extract_spatial_data("wildlife_areas")` uses the dataset registry to look up source configuration and route to the correct extractor. Best for known, catalogued datasets.

2. **Direct mode** — `extract_from_path("path/to/file.shp")` detects the format by extension and extracts immediately. Best for user-provided files and ad-hoc analysis.

### Integration with Suitability Modeling

The `suitability_modeling` module uses `spatial_data` as its data layer. In the v0.2.0 pipeline, the suitability CLI prompts users for file paths and routes them through `spatial_data`'s extractors:

```python
# suitability_modeling v0.2.0 uses spatial_data's direct extraction
from rtgs_lab_tools.spatial_data import extract_from_path, generate_grid, get_dataset_schema

boundary = extract_from_path(user_boundary_path)
grid = generate_grid(boundary, cell_size=100)
datasets = extract_all_from_directory(user_datasets_path)
schemas = [get_dataset_schema(name, gdf) for name, gdf in datasets.items()]
```

---