# Spatial Data Module

**Status:** Phase 1 MVP Complete - TESTED AND WORKING  
**Branch:** `ben/etl-pipeline-v0`  
**Target:** Hennepin County Parcel Prioritization Model Input Data

## Overview

The `spatial_data` module provides extraction and processing capabilities for geospatial datasets required by the Hennepin County Parcel Prioritization Model. This module operates as a parallel system to the existing `sensing_data` module, designed specifically for spatial data sources.

## Architecture

This module implements the **Parallel Module Architecture** following software engineering best practices:

- **Clean Separation**: Spatial data processing separate from time-series sensor data
- **Infrastructure Reuse**: Leverages 85% of existing rtgs-lab-tools infrastructure
- **Native Spatial Operations**: Uses GeoPandas GeoDataFrames (not forced measurement schemas)
- **Extractors Pattern**: Purpose-built extractors for each data source type (not parsers)

## Current Implementation Status

### COMPLETED Phase 1 - MVP 
- [x] Core module structure (`core/`, `sources/`, `registry/`)
- [x] Base `SpatialSourceExtractor` class
- [x] `MNGeospatialExtractor` for Minnesota Geospatial Commons
- [x] Dataset registry with `protected_areas` test dataset
- [x] CLI integration (`rtgs spatial-data` commands)
- [x] Infrastructure integration (Config, logging patterns)
- [x] Spatial dependencies installed (geopandas, requests)
- [x] TESTED: Actual data extraction from MN Geospatial Commons
- [x] GeoPackage zip archive processing
- [x] CLI command validation

### VERIFIED Testing Results
- **Dataset**: DNR Wildlife Management Areas (`protected_areas`)
- **Features Extracted**: 1,731 MultiPolygon features  
- **Source**: MN Geospatial Commons GeoPackage
- **Performance**: 0.8 second extraction time
- **CRS**: Properly transformed from EPSG:26915 to EPSG:4326
- **CLI Commands**: All working (`list-datasets`, `test`)

### Next Phase - File Operations
- [ ] Add file export capabilities (GeoParquet, Shapefile, CSV)
- [ ] Expand dataset registry to all 7 MN Geospatial datasets
- [ ] Add PostgreSQL logging integration
- [ ] Error handling and retry logic

## Quick Start

### Prerequisites
```bash
# Spatial dependencies (already installed)
pip install geopandas requests sqlalchemy python-dotenv
```

### Available Commands - TESTED AND WORKING
```bash
# List available datasets
rtgs spatial-data list-datasets

# Test dataset extraction (no file output) - WORKING
rtgs spatial-data test --dataset protected_areas

# Extract dataset (file operations in next phase)
rtgs spatial-data extract --dataset protected_areas --output-format geoparquet
```

## Current Dataset Registry

**MN Geospatial Commons (1 dataset implemented):**
- `protected_areas` - DNR Wildlife Management Areas

**Target:** 20 total datasets for parcel prioritization model

## Module Structure

```
spatial_data/
├── __init__.py                    # Lazy loading interface
├── README.md                      # This file
├── cli.py                         # CLI commands
├── core/
│   ├── __init__.py
│   └── extractor.py              # Main extraction orchestrator
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

## Example Usage (Current)

```python
from rtgs_lab_tools.spatial_data import extract_spatial_data

# Extract spatial dataset
result = extract_spatial_data(
    dataset_name="protected_areas",
    note="Testing MN Geospatial extraction"
)

print(f"Extracted {result['records_extracted']} features")
print(f"CRS: {result['crs']}")
print(f"Geometry type: {result['geometry_type']}")
```

## Testing Status

### COMPLETED AND VALIDATED
- Module structure and imports
- Dataset registry functionality  
- CLI command registration
- **Actual data extraction from MN Geospatial Commons** (1,731 features)
- **GeoDataFrame processing and validation** (MultiPolygon, CRS transform)
- **Network operations and zip file handling**
- **Unicode encoding issue resolution for Windows**

### Pending Tests (Next Phase)
- File export operations (GeoParquet, Shapefile, CSV)
- Error handling with network failures
- Multiple dataset processing

## Development Notes

**Based on:** `etl_pipeline_plan_v3.md` - Software Engineering Best Practices approach  
**Technical Analysis:** `parser_extension_technical_feasibility_analysis.md`

**Key Decision:** Built as parallel module rather than extending existing sensor data parsers to avoid architectural violations and maintain clean separation of concerns.

## Contributing

This module is in early development. Current focus areas:

1. **Testing**: Validate extraction from MN Geospatial Commons
2. **File Operations**: Add GeoParquet/Shapefile export capabilities  
3. **Dataset Expansion**: Add remaining 6 MN Geospatial Commons datasets
4. **Error Handling**: Robust network and API error handling
5. **Documentation**: Expand usage examples and API documentation

## Related Documents

- `etl_pipeline_plan_v3.md` - Complete implementation plan
- `parser_extension_technical_feasibility_analysis.md` - Architecture analysis
- `data_source_gee_comparison_matrix.md` - Dataset requirements analysis