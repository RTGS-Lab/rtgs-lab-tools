# Spatial Data Module

**Status:** Production Ready
**Version:** 1.0.0
**Output Format:** GeoParquet (primary), Shapefile, CSV

## Overview

The `spatial_data` module provides unified extraction and processing capabilities for geospatial datasets. It serves as the **single data management layer** for all spatial data in rtgs-lab-tools, supporting:

- **FGDB (File Geodatabase)** - Hennepin County analysis datasets (16 layers)
- **MN Geospatial Commons** - Public Minnesota datasets (10+ sources)

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

# Check data source
source = get_dataset_source("habitat_diversity")
print(f"Source: {source}")  # 'fgdb' or 'mn_geospatial'
```

## Module Structure

```
spatial_data/
├── __init__.py                    # Lazy loading interface
├── README.md                      # This file
├── cli.py                         # CLI commands
├── db_logger.py                   # Database integration
├── core/
│   ├── __init__.py
│   └── extractor.py              # Main ETL orchestrator
├── sources/
│   ├── __init__.py
│   ├── base.py                   # SpatialSourceExtractor base class
│   ├── mn_geospatial.py          # MN Geospatial Commons extractor
│   └── fgdb.py                   # ESRI File Geodatabase extractor
├── registry/
│   ├── __init__.py
│   └── dataset_registry.py       # Dataset configuration (FGDB + MN)
└── docs/
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
```

### Unified Registry

The dataset registry provides a single interface to all data sources:

```python
from rtgs_lab_tools.spatial_data import list_available_datasets

datasets = list_available_datasets()
# Returns both FGDB and MN Geospatial datasets with 'source' field
```

## Integration with Suitability Modeling

The `suitability_modeling` module uses `spatial_data` as its data layer:

```python
# suitability_modeling uses spatial_data internally
from rtgs_lab_tools.suitability_modeling import design_model, execute_model

# Datasets are loaded automatically via spatial_data
model = design_model("requirements.txt")
results = execute_model(model)
```

## Troubleshooting

### FGDB Not Available

```
FGDB Status: Not configured
```

**Solution:** Set `RTGS_FGDB_PATH` environment variable.

### Dataset Not Found

```
Dataset 'xyz' not found
```

**Solution:** Check available datasets with `rtgs spatial-data list-datasets`.

### Import Errors

```
No module named 'fiona'
```

**Solution:** Install dependencies: `pip install geopandas fiona rasterio`

## Contributing

**Current Status:** Production-ready with FGDB and MN Geospatial Commons support.

**Future Enhancements:**
- Google Earth Engine integration
- Planet Labs integration
- Automated update scheduling
- Additional MN datasets
