# Spatial Data Module - Development Notes

**Last Updated**: 2025-10-20
**Branch**: `ben/etl-pipeline-v0`

---

## Recent Development Progress

### 2025-10-20 - Dataset Expansion & Attribute Filtering

#### Dataset Growth: 4 → 10 Datasets

**New Datasets Added**:
- `aquatic_areas` - DNR Fisheries Acquisition (1,571 polygons)
- `MBS_sites` - MCBS Sites of Biodiversity Significance (12,591 polygons)
- `WAN` - Wildlife Action Network (133,283 polygons) - largest by count
- `land_use` - Generalized Land Use 2020 (22 polygons)
- `cemeteries` - Cemetery parcels from Regional Parcels (108 polygons, filtered)
- `watersheds` - DNR Level 9 Watersheds (131,411 polygons)

**Total Features**: ~620,000+ across all datasets

#### Major Feature: Attribute Filtering System

**Motivation**: Extract specific subsets from large datasets (e.g., only cemetery parcels from 139,680 total parcels)

**Implementation**:
1. **Registry Configuration** - `attribute_filter` with columns, values, match_type
2. **Extractor Logic** - pandas `.isin()` filtering after extraction
3. **Multi-Layer Support** - `layer_names` to load and combine multiple GeoPackage layers

**Code Changes**:
- `extractor.py:64-95` - Attribute filter application
- `mn_geospatial.py:259-290` - Multi-layer loading and concatenation
- `dataset_registry.py` - Filter config for cemetery dataset

**Cemetery Dataset Example**:
- Before: 139,680 parcels (full Regional Parcels)
- After: 108 cemetery parcels (0.08% retained)
- Filter: 4 use class columns checked for cemetery values
- Extraction: 139 seconds (loads 7 county layers + filtering)

**Benefits**:
- 99.92% data reduction for targeted use cases
- Reusable framework for other filtered datasets
- Maintains full spatial accuracy

#### Enhanced CLI Documentation

**Updated README**:
- Comprehensive CLI command reference with all options
- Operational modes (database-only vs with files)
- Quick command reference table
- Updated dataset count (10 datasets)

---

### 2025-10-14 - Dataset Expansion & REST API Support

#### 1. Dataset Renaming: `protected_areas` → `wildlife_areas`

**Motivation**: Improve naming clarity and consistency for DNR Wildlife Management Areas dataset.

**Changes Made**:
- Updated dataset key in `registry/dataset_registry.py`
- Updated all references in module documentation:
  - `README.md`
  - `db_schema.sql`
  - `docs/geoparquet_decision_matrix.md`
  - `docs/prototype_architecture.md`

**Impact**: No breaking changes to code structure, only naming conventions. Users now reference the dataset as `wildlife_areas` in CLI commands.

---

#### 2. New Dataset: `scientific_and_natural_areas`

**Description**: DNR Scientific and Natural Areas boundaries

**Source**: MN Geospatial Commons
**URL**: https://gisdata.mn.gov/dataset/bdry-scientific-and-nat-areas
**Download URL**: https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/bdry_scientific_and_nat_areas/gpkg_bdry_scientific_and_nat_areas.zip

**Format**: GeoPackage (MultiPolygon)
**Access Method**: Direct download
**Features**: 237 polygons
**Extraction Time**: 1.1 seconds
**CRS**: EPSG:26915 → EPSG:4326

**Technical Challenge**: Multi-layer GeoPackage

The source GeoPackage contains multiple layers:
- `sna_parking` (default)
- `scientific_and_natural_area_boundaries` (target)

**Solution**: Enhanced `MNGeospatialExtractor._extract_from_zip()` to support `layer_name` parameter:

```python
# In dataset_registry.py
"layer_name": "scientific_and_natural_area_boundaries"

# In mn_geospatial.py:212-218
layer_name = self.dataset_config.get("layer_name")
if layer_name:
    self.logger.info(f"Reading specific layer: {layer_name}")
    gdf = gpd.read_file(spatial_path, layer=layer_name)
else:
    gdf = gpd.read_file(spatial_path)
```

**Result**: Clean extraction without layer ambiguity warnings.

**Files Modified**:
- `src/rtgs_lab_tools/spatial_data/registry/dataset_registry.py`
- `src/rtgs_lab_tools/spatial_data/sources/mn_geospatial.py`

---

#### 3. New Dataset: `TNC_lands` (REST API Extraction)

**Description**: The Nature Conservancy lands and waters in Minnesota, North Dakota, & South Dakota

**Source**: TNC Geospatial Conservation Atlas
**Dataset ID**: `53441934d168434e8ff255bda7fd1e3e_1`
**Web URL**: https://geospatial.tnc.org/datasets/53441934d168434e8ff255bda7fd1e3e_1/explore
**REST API URL**: https://services.arcgis.com/F7DSX1DSNSiWmOqh/arcgis/rest/services/TNC_Lands_MNDK_Public_Layer_2024/FeatureServer/1

**Format**: ArcGIS FeatureServer (MultiPolygon)
**Access Method**: REST API
**Features**: 383 polygons
**Extraction Time**: 6.6 seconds
**CRS**: EPSG:4326 (native)

**Technical Challenge**: Finding download URL for ArcGIS Hub dataset

**Investigation Process**:
1. Attempted to find GeoPackage download URL via web scraping → Failed
2. Searched for ArcGIS Hub download URL patterns → Found API endpoints
3. Used TNC Hub API v3 to retrieve dataset metadata:
   ```bash
   curl -s "https://geospatial.tnc.org/api/v3/datasets/53441934d168434e8ff255bda7fd1e3e_1"
   ```
4. Extracted `service_url` from JSON response

**Solution**: Enhanced REST API extraction with pagination support

The existing `_extract_from_rest_api()` method was basic and didn't handle large datasets. We implemented:

1. **Feature count detection** - Query total features before extraction
2. **Automatic pagination** - Handle datasets larger than ArcGIS max record limit (2000)
3. **Batch processing** - Extract in chunks and combine into single GeoDataFrame
4. **Progress logging** - Track extraction progress for large datasets

**Code Enhancement** (`mn_geospatial.py:50-144`):

```python
def _extract_from_rest_api(self) -> "gpd.GeoDataFrame":
    """Extract from ArcGIS REST API service with pagination support."""

    # Get total feature count
    count_params = {
        "where": "1=1",
        "returnCountOnly": "true",
        "f": "json",
    }
    count_response = self.session.get(query_url, params=count_params, timeout=30)
    total_count = count_response.json().get("count", 0)

    # Check if pagination needed
    max_record_count = 2000  # Default ArcGIS limit

    if total_count <= max_record_count:
        # Extract all features at once
        ...
    else:
        # Paginate through results
        all_gdfs = []
        for offset in range(0, total_count, max_record_count):
            params = {
                "where": "1=1",
                "outFields": "*",
                "f": "geojson",
                "returnGeometry": "true",
                "resultOffset": str(offset),
                "resultRecordCount": str(max_record_count),
            }
            batch_gdf = gpd.read_file(response.text)
            all_gdfs.append(batch_gdf)

        # Combine all batches
        gdf = pd.concat(all_gdfs, ignore_index=True)
        gdf = gpd.GeoDataFrame(gdf, geometry='geometry')
```

**Benefits**:
- ✅ Handles datasets of any size
- ✅ Efficient memory usage (streaming)
- ✅ Progress tracking
- ✅ No manual file downloads needed
- ✅ Always gets latest data from API

**Registry Configuration**:

```python
"TNC_lands": {
    "description": "The Nature Conservancy lands and waters in Minnesota, North Dakota, & South Dakota",
    "source_type": "mn_geospatial",
    "extractor_class": "MNGeospatialExtractor",
    "url": "https://geospatial.tnc.org/datasets/53441934d168434e8ff255bda7fd1e3e_1/explore",
    "service_url": "https://services.arcgis.com/F7DSX1DSNSiWmOqh/arcgis/rest/services/TNC_Lands_MNDK_Public_Layer_2024/FeatureServer/1",
    "access_method": "rest_api",  # <-- Key difference
    "file_format": "featureserver",
    "update_frequency": "yearly",
    "spatial_type": "multipolygon",
    "model_critical": True,
    "coordinate_system": "EPSG:4326",
    "expected_features": 383,
}
```

**Files Modified**:
- `src/rtgs_lab_tools/spatial_data/registry/dataset_registry.py`
- `src/rtgs_lab_tools/spatial_data/sources/mn_geospatial.py`

---

## Current Dataset Inventory

| Dataset Name | Source | Features | Format | Access Method | Extraction Time | Notes |
|--------------|--------|----------|--------|---------------|-----------------|-------|
| `wildlife_areas` | MN Geospatial | 1,731 | GeoPackage | Download | 0.8s | |
| `groundwater_recharge` | MN Geospatial | 201,264 | AAIGRID (Raster) | Download | 14.5s | Largest dataset |
| `scientific_and_natural_areas` | MN Geospatial | 237 | GeoPackage | Download | 1.1s | Multi-layer |
| `TNC_lands` | TNC Geospatial | 383 | FeatureServer | REST API | 6.6s | |
| `aquatic_areas` | MN Geospatial | 1,571 | GeoPackage | Download | 1.2s | |
| `MBS_sites` | MN Geospatial | 12,591 | GeoPackage | Download | 2.9s | |
| `WAN` | MN Geospatial | 133,283 | GeoPackage | Download | 5.5s | Multi-layer |
| `land_use` | MN Geospatial | 22 | GeoPackage | Download | 4.5s | Highly generalized |
| `cemeteries` | MN Geospatial | 108 | GeoPackage | Download | 139s | **Filtered** (7 layers) |
| `watersheds` | MN Geospatial | 131,411 | GeoPackage | Download | 12.3s | Multi-layer |

**Total Datasets**: 10
**Total Features**: ~620,000+ (vector + raster grid cells)

---

## Architecture Enhancements

### Multi-Layer GeoPackage Support

**Problem**: Some GeoPackage files contain multiple layers. By default, GeoPandas reads the first layer, which may not be the desired one.

**Solutions**:

**1. Single Layer Selection** - Add `layer_name` parameter:

```python
"layer_name": "scientific_and_natural_area_boundaries"
```

Extractor checks for this parameter and passes it to `gpd.read_file()`:

```python
if layer_name:
    gdf = gpd.read_file(spatial_path, layer=layer_name)
else:
    gdf = gpd.read_file(spatial_path)
```

**2. Multiple Layer Loading** - Add `layer_names` parameter (list):

```python
"layer_names": ["ParcelsAnoka", "ParcelsCarver", "ParcelsDakota", ...]
```

Extractor loads each layer and combines with `pd.concat()`:

```python
if layer_names:
    gdfs = []
    for layer in layer_names:
        layer_gdf = gpd.read_file(spatial_path, layer=layer)
        gdfs.append(layer_gdf)
    gdf = pd.concat(gdfs, ignore_index=True)
```

**Usage**: Use `layer_name` for single layer, `layer_names` for multiple layers to combine.

---

### REST API Pagination

**Problem**: ArcGIS REST API services have a maximum record count limit (typically 2000). Datasets with more features require pagination.

**Solution**: Enhanced `_extract_from_rest_api()` with automatic pagination:

1. Query total feature count first
2. Determine if pagination needed
3. Extract in batches if count > max_record_count
4. Combine all batches into single GeoDataFrame

**Performance**: ~3 seconds per 1000 features (network dependent)

**Future Enhancement**: Consider parallel batch downloads for very large datasets (>10k features)

---

### Attribute Filtering

**Problem**: Some datasets are too broad - need to extract specific subsets (e.g., only cemeteries from all parcels)

**Solution**: Add `attribute_filter` to dataset registry:

```python
"attribute_filter": {
    "description": "Extract only cemetery parcels",
    "columns": ["XUSECLASS1", "XUSECLASS2", "XUSECLASS3", "XUSECLASS4"],
    "values": ["PRIVATE CEMETERIES", "PUBLIC CEMETERIES"],
    "match_type": "any"  # Match if ANY column contains ANY value
}
```

Extractor applies filter after extraction using pandas boolean indexing:

```python
mask = pd.Series([False] * len(gdf))
for col in columns:
    if col in gdf.columns:
        mask |= gdf[col].isin(values)
gdf = gdf[mask]
```

**Performance**: Negligible overhead (milliseconds) for filtering after extraction

**Use Cases**: Extract parcels by use class, filter sites by significance level, select watersheds by HUC level

---

## How to Find ArcGIS Hub Download URLs

When adding new datasets from ArcGIS Hub sites (e.g., TNC, state portals), follow this process:

### Method 1: Hub API v3 (Recommended)

Extract the dataset ID from the URL:
```
https://geospatial.tnc.org/datasets/53441934d168434e8ff255bda7fd1e3e_1/explore
                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                              Dataset ID
```

Query the Hub API:
```bash
curl -s "https://{hub-domain}/api/v3/datasets/{dataset-id}"
```

Look for the `service_url` in the JSON response:
```bash
curl -s "https://geospatial.tnc.org/api/v3/datasets/53441934d168434e8ff255bda7fd1e3e_1" | \
  grep -o '"url":"[^"]*FeatureServer[^"]*"'
```

### Method 2: Browser DevTools

1. Open the dataset page in browser
2. Open DevTools (F12) → Network tab
3. Click the download button (GeoPackage, Shapefile, etc.)
4. Look for the download request in Network tab
5. Copy the request URL

### Method 3: ArcGIS REST API Discovery

If you know it's an ArcGIS service, try common patterns:

```
# Service directory
https://services.arcgis.com/{org-id}/arcgis/rest/services

# Specific service
https://services.arcgis.com/{org-id}/arcgis/rest/services/{service-name}/FeatureServer/{layer-id}
```

---

## Testing New Datasets

### Test Command

```bash
rtgs spatial-data test --dataset {dataset_name}
```

**What it does**:
- Extracts the dataset (full ETL pipeline)
- Does NOT write to file (test mode)
- Reports: feature count, duration, success/failure
- Validates geometries and CRS

**Example Output**:
```
Testing dataset: TNC_lands
SUCCESS: Test successful!
   Features: 383
   Duration: 6.6s
```

### Full Extraction

```bash
rtgs spatial-data extract --dataset {dataset_name}
```

**Output**: GeoParquet file in `./data/` directory

---

## Next Steps

### Immediate Priorities

1. **Add remaining MN Geospatial datasets** (18+ available)
   - State parks and trails
   - Public waters
   - Soil classifications
   - Land cover / land use

2. **Implement automated update detection**
   - Check source modified dates
   - Compare checksums
   - Trigger re-extraction when changes detected

3. **Enhanced error handling**
   - Retry logic for network failures
   - Better validation messages
   - Graceful degradation

### Medium-Term Goals

1. **Google Earth Engine integration**
   - Satellite imagery (Landsat, Sentinel)
   - Climate data layers
   - NDVI, EVI, other indices

2. **Planet Labs integration**
   - High-resolution imagery
   - Change detection

3. **Spatial queries**
   - Extract by bounding box
   - Filter by attributes
   - Spatial joins

### Long-Term Vision

1. **Automated scheduling**
   - Cron jobs for regular updates
   - Airflow DAGs for complex workflows

2. **Data versioning**
   - Track changes over time
   - Delta storage
   - Time-travel queries

3. **Performance optimization**
   - Parallel downloads
   - Incremental updates
   - Distributed processing (Dask/Ray)

---

## Lessons Learned

### 1. Always Check for Multi-Layer Files

**Issue**: GeoPackages can contain multiple layers. Default layer may not be what you need.

**Solution**: Inspect files first, add `layer_name` to registry if needed.

**Command to list layers**:
```bash
ogrinfo -al -so file.gpkg
```

### 2. REST API is Often Better Than Downloads

**Advantages**:
- Always current data
- No file management
- No disk space usage
- Easier automation

**Disadvantages**:
- Slower for large datasets
- Network dependent
- Requires pagination logic

**Recommendation**: Use REST API for datasets <5k features, downloads for larger datasets or offline workflows.

### 3. Hub API v3 is Your Friend

When working with ArcGIS Hub datasets:
- Don't scrape web pages → Use API
- Hub API v3 provides complete metadata
- Pattern: `https://{hub-domain}/api/v3/datasets/{dataset-id}`

### 4. Document Expected Feature Counts

Adding `expected_features` to registry helps with:
- Validation (did we get all features?)
- Performance monitoring (extraction time trends)
- Dataset discovery (how big is this dataset?)

**Best Practice**: Always add `expected_features` after first successful test extraction.

---

## Code Quality & Standards

### Naming Conventions

- **Dataset names**: `snake_case` (e.g., `wildlife_areas`, `TNC_lands`)
- **Registry keys**: Match dataset names exactly
- **File names**: Follow dataset names (e.g., `wildlife_areas.parquet`)

### Registry Configuration Fields

**Required**:
- `description` - Human-readable description
- `source_type` - Source system (e.g., `mn_geospatial`)
- `extractor_class` - Extractor to use (e.g., `MNGeospatialExtractor`)
- `url` - Human-readable web URL
- `access_method` - `download` or `rest_api`
- `spatial_type` - Geometry type (e.g., `multipolygon`, `raster`)
- `model_critical` - Boolean, is this dataset required for models?

**Conditional**:
- `download_url` - Required if `access_method` is `download`
- `service_url` - Required if `access_method` is `rest_api`
- `layer_name` - Required for multi-layer GeoPackages

**Optional**:
- `expected_features` - Add after test extraction
- `coordinate_system` - Source CRS (can be `unknown` for rasters)
- `update_frequency` - `yearly`, `monthly`, `static`, etc.
- `data_source` - Original data provider
- `temporal_coverage` - Date range for static datasets
- `units` - Data units for raster values

### Commit Message Format

Follow the existing pattern:

```
<action> <component>: <description>

Examples:
- Add dataset: scientific_and_natural_areas
- Enhance extractor: REST API pagination support
- Fix: layer name handling for multi-layer GeoPackages
- Update docs: REST API discovery methods
```

---

## Troubleshooting

### Issue: "Invalid geometries" warning

**Cause**: Some source data has topological errors

**Solution**: Already handled gracefully - logged as warning, extraction continues

**Code**: `base.py:41-65` - `validate_spatial_integrity()`

### Issue: "More than one layer found" warning

**Cause**: Multi-layer GeoPackage without `layer_name` specified

**Solution**: Add `layer_name` to registry configuration

### Issue: REST API timeout

**Cause**: Large dataset, slow network, or service overload

**Solution**:
1. Increase timeout in code (currently 60s)
2. Check service status
3. Consider using download method instead

### Issue: Feature count mismatch

**Cause**: Dataset updated since `expected_features` was set

**Solution**:
1. Re-run test extraction
2. Update `expected_features` in registry
3. Investigate if significant difference (data quality issue?)

---

## Resources

### MN Geospatial Commons
- **Portal**: https://gisdata.mn.gov/
- **Data format**: GeoPackage, Shapefile, AAIGRID
- **Access**: Direct download (no authentication)

### TNC Geospatial Conservation Atlas
- **Portal**: https://geospatial.tnc.org/
- **Data format**: ArcGIS FeatureServer
- **API**: Hub API v3
- **Access**: REST API (public data)

### ArcGIS REST API Documentation
- **Service types**: https://developers.arcgis.com/rest/services-reference/
- **Query operation**: https://developers.arcgis.com/rest/services-reference/query-feature-service-layer-.htm
- **Pagination**: Use `resultOffset` and `resultRecordCount` parameters

### GeoPandas Documentation
- **Reading files**: https://geopandas.org/en/stable/docs/user_guide/io.html
- **Layer specification**: Pass `layer` parameter to `read_file()`
- **CRS transformations**: https://geopandas.org/en/stable/docs/user_guide/projections.html

---

## Contact & Questions

**Maintainer**: Ben (ben/etl-pipeline-v0 branch)
**RTGS Lab**: https://rtgs.umn.edu/
**Repository**: https://github.com/RTGS-Lab/rtgs-lab-tools
**Issues**: Use GitHub issue tracker

For questions about specific datasets, consult the data provider directly:
- **MN Geospatial Commons**: gisdata.mn.gov contact form
- **TNC**: geospatial.tnc.org contact information
