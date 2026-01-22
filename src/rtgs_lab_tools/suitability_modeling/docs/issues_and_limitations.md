# Suitability Modeling Module: Issues and Limitations

## Critical Bugs

These bugs prevent the module from executing successfully and must be fixed immediately.

### Bug #1: AttributeError in Categorical Scoring Function

**Severity**: 🔴 CRITICAL - Blocks execution
**Location**: `core/execution_engine.py:324`
**Status**: Unresolved

**Error Message**:
```
AttributeError: 'numpy.ndarray' object has no attribute 'values'
```

**Root Cause**:
The `_score_categorical()` method has inconsistent return types:
- Line 319: Creates pandas Series with `.map()` method
- Line 322: Creates numpy array with `np.full()` as fallback
- Line 324: Tries to call `.values` on both, but numpy arrays don't have this attribute

**Problematic Code**:
```python
# execution_engine.py:318-324
if category_column in joined.columns:
    scores = joined[category_column].map(mapping).fillna(0)  # pandas Series
else:
    logger.warning(f"Column '{category_column}' not found, using default score of 5")
    scores = np.full(len(study_area), 5.0)  # numpy array

return scores.values  # FAILS when scores is numpy array
```

**Suggested Fix**:
```python
# Option 1: Check type before accessing .values
return scores.values if hasattr(scores, 'values') else scores

# Option 2 (better): Always convert to values at line 319
if category_column in joined.columns:
    scores = joined[category_column].map(mapping).fillna(0).values
else:
    logger.warning(f"Column '{category_column}' not found, using default score of 5")
    scores = np.full(len(study_area), 5.0)

return scores  # Now always returns numpy array
```

**Test Case**: Wildlife corridor model with land_use categorical criterion

---

### Bug #2: Missing Context Parameter in CLI Error Handler

**Severity**: 🟡 MEDIUM - Only triggered on certain errors
**Location**: `cli.py:79` (design_command function)
**Status**: Not encountered in current testing (API key issue resolved first)

**Error Message** (from earlier testing):
```
NameError: name 'ctx' is not defined
```

**Root Cause**:
The `design_command` function calls `ctx.exit(1)` but doesn't have the `@click.pass_context` decorator or `ctx` parameter.

**Problematic Code**:
```python
# cli.py:43-79
@suitability_cli.command(name="design")
@click.option(...)
def design_command(input_file: str, output_file: Optional[str], api_key: Optional[str]):
    try:
        # ... model design code ...
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        logger.exception("Model design failed")
        ctx.exit(1)  # ERROR: ctx not defined
```

**Suggested Fix**:
```python
@suitability_cli.command(name="design")
@click.option(...)
@click.pass_context  # ADD THIS
def design_command(ctx, input_file: str, output_file: Optional[str], api_key: Optional[str]):  # ADD ctx
    try:
        # ... model design code ...
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        logger.exception("Model design failed")
        ctx.exit(1)  # Now ctx is defined
```

---

## Architectural Issues

These are fundamental design problems that limit functionality or produce incorrect results.

### Issue #1: Study Area Boundary NOT Enforced

**Severity**: 🔴 CRITICAL - Produces incorrect results
**Impact**: High - Fundamentally changes what the analysis means
**Status**: By Design (MVP limitation), but undocumented

**Problem Description**:

The model specification includes a `study_area` field (e.g., "Hennepin County"), but this is **purely descriptive metadata** and has NO functional impact on the analysis.

**What Currently Happens**:
1. Model loads all datasets specified in criteria (wildlife_areas, land_use, watersheds)
2. Calculates the **rectangular bounding box** that encompasses all datasets
3. Creates a 100m grid over that entire bounding box (up to 10,000 cells)
4. Scores all grid cells, regardless of whether they're in the specified study area

**Example**:
```yaml
study_area: Hennepin County  # This is IGNORED during execution!
```

If your datasets have statewide coverage, you'll analyze the **entire state**, not just Hennepin County.

**Code Location**: `core/execution_engine.py:168-230` (_create_study_area method)

```python
def _create_study_area(self, cell_size: float = 100.0) -> gpd.GeoDataFrame:
    """Create a regular grid for the study area.

    For MVP, we create a simple grid based on the extent of loaded datasets.
    """
    # Get combined bounds of all datasets
    all_bounds = []
    for gdf in self.datasets.values():
        if not gdf.empty:
            all_bounds.append(gdf.total_bounds)

    # Creates rectangular grid over ENTIRE dataset extent
    # Does NOT use study_area parameter at all!
```

**Why This Is a Problem**:
- Users expect "Hennepin County" to mean "analyze only Hennepin County"
- Results include areas outside the intended study area
- Can't compare models with different study areas
- Misleading to stakeholders/reviewers

**Proper Behavior Should Be**:
1. Accept a study area boundary (shapefile, GeoJSON, or dataset name)
2. Load that boundary geometry
3. Create grid cells ONLY within the boundary
4. Clip datasets to the boundary before analysis

**Suggested Enhancement**:
```yaml
study_area:
  type: boundary  # Options: "boundary", "extent", "grid"
  source: county_boundaries  # Dataset name or file path
  filter:
    NAME: "Hennepin County"
  # OR
  # geometry: "path/to/boundary.geojson"
```

**Workaround for Now**:
- Ensure all input datasets are pre-clipped to study area
- Document that study_area field is descriptive only
- Manually verify grid extent matches expectations

---

### Issue #2: Geographic CRS - Distance Calculations Incorrect

**Severity**: 🔴 CRITICAL - Produces incorrect results
**Location**: `core/execution_engine.py:283` (_score_distance_decay method)
**Status**: Unresolved

**Warning Message**:
```
UserWarning: Geometry is in a geographic CRS. Results from 'distance' are likely incorrect.
Use 'GeoSeries.to_crs()' to re-project geometries to a projected CRS before this operation.
```

**Problem Description**:

Distance calculations are performed in **geographic coordinates** (latitude/longitude degrees) instead of **projected coordinates** (meters). This causes:
- Distance values in degrees, not meters
- Inaccurate distance-based scoring
- Distance decay functions using wrong units

**Example**:
```yaml
scoring_function:
  type: distance_decay
  params:
    max_distance: 2000  # Intended: 2000 meters
    decay_rate: 0.001   # Calibrated for meters
```

But if CRS is EPSG:4326 (WGS84), `max_distance` is interpreted as **2000 degrees** (roughly the width of the United States!).

**Root Cause**:
Datasets loaded from spatial_data module retain their original CRS (usually EPSG:4326 for web data). The execution engine doesn't reproject to a projected CRS before distance calculations.

**Code Location**: `core/execution_engine.py:270-285`

```python
def _score_distance_decay(
    self,
    study_area: gpd.GeoDataFrame,
    features: gpd.GeoDataFrame,
    scoring_func: "ScoringFunction"
) -> np.ndarray:
    # ... parameter extraction ...

    # Calculate distances WITHOUT checking/reprojecting CRS
    distances = study_area.geometry.apply(
        lambda geom: features.distance(geom).min()  # Uses whatever CRS is loaded
    )
```

**Suggested Fix**:

```python
def _score_distance_decay(
    self,
    study_area: gpd.GeoDataFrame,
    features: gpd.GeoDataFrame,
    scoring_func: "ScoringFunction"
) -> np.ndarray:
    # Reproject to appropriate projected CRS if needed
    if study_area.crs.is_geographic or features.crs.is_geographic:
        # For Minnesota, use UTM Zone 15N (EPSG:26915)
        # Or detect appropriate UTM zone from centroid
        target_crs = 'EPSG:26915'  # UTM 15N for Minnesota

        if study_area.crs.is_geographic:
            study_area = study_area.to_crs(target_crs)
        if features.crs.is_geographic:
            features = features.to_crs(target_crs)

    # Now distances will be in meters
    distances = study_area.geometry.apply(
        lambda geom: features.distance(geom).min()
    )
```

**Alternative**: Auto-detect UTM zone from data centroid:
```python
from pyproj import CRS

def get_utm_crs(gdf):
    """Get appropriate UTM CRS for a GeoDataFrame."""
    centroid = gdf.dissolve().centroid.iloc[0]
    lon, lat = centroid.x, centroid.y
    utm_zone = int((lon + 180) / 6) + 1
    hemisphere = 'north' if lat >= 0 else 'south'
    return CRS.from_dict({'proj': 'utm', 'zone': utm_zone, 'hemisphere': hemisphere})
```

**Impact**: All distance-based scoring is currently unreliable

---

### Issue #3: Grid Size Limitation (10,000 cells max)

**Severity**: 🟡 MEDIUM - Limits analysis resolution
**Location**: `core/execution_engine.py:206-215`
**Status**: By Design (MVP limitation), documented in comments

**Problem Description**:

Analysis grid is capped at 10,000 cells maximum. For large study areas:
- 100m cell size results in ~100 x 100 = 10,000 cells = 10km x 10km area
- Hennepin County is ~607 square miles (~1,572 km²)
- Full coverage at 100m would need ~157,000 cells
- Current implementation **samples uniformly** instead, missing spatial detail

**Code**:
```python
# Limit grid size for MVP (max 10,000 cells)
max_cells = 10000
total_cells = len(x_coords) * len(y_coords)

if total_cells > max_cells:
    logger.warning(f"Grid would have {total_cells} cells, sampling {max_cells} instead")
    # Sample uniformly - LOSES spatial detail
    x_sample = np.linspace(minx, maxx, int(np.sqrt(max_cells)))
    y_sample = np.linspace(miny, maxy, int(np.sqrt(max_cells)))
```

**Why It's a Problem**:
- Uniform sampling doesn't preserve spatial patterns
- Can miss important features between sample points
- Resolution varies unpredictably based on dataset extent
- Users unaware that analysis is sampled, not complete

**Better Approaches**:
1. **Adaptive grid**: Finer resolution in high-suitability areas
2. **Configurable limit**: Let users choose performance vs. detail
3. **Streaming/chunked processing**: Process large grids in batches
4. **Warn users**: Show expected grid size before execution

**Suggested Enhancement**:
```python
# Allow users to configure
cell_size: 100  # meters (default)
max_cells: 50000  # Allow larger analyses (optional)
sampling_strategy: "uniform" | "adaptive" | "none"
```

---

## Design Problems

Issues with how the module was designed or how Claude AI generates models.

### Problem #1: Incorrect Column Name in Categorical Scoring

**Severity**: 🟡 MEDIUM - Causes fallback to default scores
**Location**: Model design (Claude AI) + execution_engine.py:312
**Status**: Unresolved

**Warning Message**:
```
Column 'category' not found, using default score of 5
```

**Problem Description**:

When Claude AI designs a model with categorical scoring for the `land_use` dataset, it doesn't know what columns are actually in that dataset. It defaults to using a column named `'category'`, which doesn't exist.

**Example from Generated YAML**:
```yaml
- dataset_name: land_use
  criterion_name: Habitat Quality
  scoring_function:
    type: categorical
    params:
      mapping:
        Forest: 10
        Wetland: 10
        # ... more mappings ...
      # NO column specified! Defaults to 'category'
```

**Root Cause**:

Two issues:
1. **Claude doesn't know dataset schema**: When designing the model, Claude AI receives dataset *names* but not their *schemas* (column names, data types, etc.)
2. **Hardcoded default**: execution_engine.py defaults to column name `'category'` when none specified

**Code Location**: `core/execution_engine.py:312`
```python
category_column = params.get('column', 'category')  # Hardcoded default
```

**Impact**:
- All grid cells get default score of 5
- Categorical criteria don't actually influence results
- Model appears to work but produces meaningless output

**Suggested Fixes**:

**Fix 1: Include Schema in Design Prompt**
```python
# model_designer.py
def _get_available_datasets():
    datasets = {}
    for name, info in spatial_data.list_available_datasets().items():
        # Load a sample to inspect schema
        sample = extract_spatial_data(name, limit=1)
        datasets[name] = {
            'description': info['description'],
            'columns': list(sample.columns),  # Add this!
            'sample_values': {col: sample[col].unique()[:5] for col in sample.columns}
        }
    return datasets
```

Then Claude can generate:
```yaml
scoring_function:
  type: categorical
  params:
    column: land_cover_class  # Actual column name
    mapping:
      Forest: 10
      Wetland: 10
```

**Fix 2: Auto-Detect Column**
```python
# execution_engine.py
def _score_categorical(self, study_area, features, scoring_func):
    category_column = params.get('column')

    if not category_column:
        # Auto-detect: find first string/object column
        string_cols = features.select_dtypes(include=['object', 'string']).columns
        if len(string_cols) > 0:
            category_column = string_cols[0]
            logger.info(f"Auto-detected category column: {category_column}")
        else:
            logger.warning("No categorical column found, using default score")
            return np.full(len(study_area), 5.0)
```

**Fix 3: Validation**
Add validation that warns users when specified column doesn't exist:
```python
# model_specification.py - validate()
def validate(self):
    # ... existing validation ...

    # Check categorical columns exist
    for criterion in self.criteria:
        if criterion.scoring_function.type == 'categorical':
            column = criterion.scoring_function.params.get('column')
            if not column:
                warnings.warn(f"Criterion '{criterion.criterion_name}' missing 'column' parameter")
```

---

### Problem #2: spatial_data Module Import Warning

**Severity**: 🟢 LOW - Doesn't affect functionality
**Location**: `core/model_designer.py:30-50`
**Status**: By design (graceful degradation)

**Warning Message**:
```
spatial_data module not available, using limited dataset list
```

**Problem Description**:

During model design, the system tries to import the spatial_data module to get available datasets. If import fails, it falls back to a hardcoded list.

**Why It Happens**:
- The spatial_data module is in the same package but import can fail in some environments
- Happens when Python path isn't set correctly
- Happens during development/testing

**Code Location**: `core/model_designer.py`
```python
def _get_available_datasets() -> Dict[str, Any]:
    """Get available spatial datasets."""
    try:
        from ...spatial_data.registry import list_available_datasets
        return list_available_datasets()
    except ImportError:
        logger.warning("spatial_data module not available, using limited dataset list")
        # Fallback to hardcoded list
        return {
            'wildlife_areas': {'description': 'DNR Wildlife Management Areas'},
            'land_use': {'description': 'Land use/land cover'},
            # ... limited list ...
        }
```

**Impact**:
- Minimal - fallback list includes main datasets
- Claude still generates valid models
- Some datasets might be unavailable in fallback mode

**Not a Critical Issue**: Works as intended (graceful degradation)

---

### Problem #3: No Dataset Availability Check During Design

**Severity**: 🟡 MEDIUM - Can generate unexecutable models
**Status**: Not implemented

**Problem Description**:

Claude AI can design models using datasets that:
- Don't exist in the registry
- Haven't been downloaded yet
- Are spelled incorrectly

Users only discover this when execution fails.

**Example**:
Claude might generate:
```yaml
criteria:
  - dataset_name: protected_areas  # Doesn't exist!
```

But the actual dataset is named `wildlife_areas`.

**Suggested Fix**:

Add validation during design:
```python
# model_designer.py
def design_model(requirements_file, output_file, api_key):
    # ... existing code ...

    # Validate designed model
    model_spec = ModelSpecification.from_dict(model_dict)

    # Check dataset availability
    available_datasets = _get_available_datasets()
    for criterion in model_spec.criteria:
        if criterion.dataset_name not in available_datasets:
            logger.error(f"Dataset '{criterion.dataset_name}' not available!")
            logger.info(f"Available datasets: {list(available_datasets.keys())}")
            raise ValueError(f"Unknown dataset: {criterion.dataset_name}")

    model_spec.validate()  # Existing validation
```

---

## Data Integration Issues

Problems related to loading and processing spatial datasets.

### Issue #1: Multiple Layers in GeoPackage

**Severity**: 🟢 LOW - Generates warning but works
**Dataset**: watersheds (geos_dnr_watersheds.gpkg)
**Status**: By design (uses default layer)

**Warning Message**:
```
UserWarning: More than one layer found in 'geos_dnr_watersheds.gpkg':
'dnr_watersheds_catchment_flow_lines' (default),
'dnr_watersheds_auto_catchment_streams',
'dnr_watersheds_catchment_pour_points',
[... 9 more layers ...]
Specify layer parameter to avoid this warning.
```

**Problem Description**:

The watersheds GeoPackage contains 12 different layers. The system uses the default layer, which might not be the most appropriate for the analysis.

**Impact**:
- May use wrong watershed representation
- Results could be unexpected if user assumes different layer
- No way to specify which layer to use

**Suggested Enhancement**:

Allow layer specification in model:
```yaml
criteria:
  - dataset_name: watersheds
    layer: dnr_watersheds_dnr_level_04_huc_08_majors  # Specify layer
    criterion_name: Water Access
```

Or in spatial_data registry:
```python
'watersheds': {
    'description': 'DNR Watersheds',
    'source': 'mn_geospatial',
    'default_layer': 'dnr_watersheds_dnr_level_04_huc_08_majors'
}
```

---

### Issue #2: Invalid Geometries in Datasets

**Severity**: 🟡 MEDIUM - May affect analysis accuracy
**Dataset**: land_use (16 invalid geometries found)
**Status**: Data quality issue

**Warning Message**:
```
Found 16 invalid geometries
```

**Problem Description**:

Some features in the land_use dataset have invalid geometries (self-intersections, unclosed rings, etc.). GeoPandas can usually work with them, but they may cause:
- Incorrect spatial joins
- Wrong distance calculations
- Unexpected behavior in geometry operations

**Impact**:
- Potentially incorrect scores for affected grid cells
- May cause crashes in some operations

**Suggested Fix**:

Add geometry repair in data loading:
```python
# execution_engine.py - _load_datasets()
gdf = gpd.read_parquet(result['output_file'])

# Check and fix invalid geometries
if not gdf.is_valid.all():
    invalid_count = (~gdf.is_valid).sum()
    logger.warning(f"Found {invalid_count} invalid geometries, attempting repair")
    gdf['geometry'] = gdf['geometry'].buffer(0)  # Common repair technique

    # Check if repair worked
    if not gdf.is_valid.all():
        logger.error(f"Could not repair all geometries")
```

---

### Issue #3: Database Logging Failures

**Severity**: 🟢 LOW - Doesn't affect analysis
**Status**: Expected (database not configured)

**Warning Message** (appears 3 times):
```
Failed to log spatial extraction: DB_USER not found in Secret Manager or environment variables
```

**Problem Description**:

The spatial_data module tries to log extractions to a database for audit purposes. This fails when database credentials aren't configured, which is expected in development/testing.

**Impact**: None - spatial data still loads successfully

**Not a Bug**: Expected behavior when database isn't configured

---

## Non-Critical Warnings

Warnings that appear during execution but don't prevent the module from working.

### Warning #1: Non-Conformant Date Format

**Severity**: 🟢 VERY LOW
**Dataset**: wildlife_areas
**Status**: Data format issue (handled gracefully)

**Message**:
```
RuntimeWarning: Non-conformant content for record 1 in column date_inventoried,
2003-01-01T00:00:00.0Z, successfully parsed
```

**Description**: Date field has non-standard format but is successfully parsed. No action needed.

---

## Environment Setup Issues

Problems encountered while setting up the development environment.

### Issue #1: Python Environment Mismatch

**Severity**: 🔴 CRITICAL - Blocks initial setup
**Status**: Resolved during testing

**Problem Description**:

User had two Python installations:
- Python 3.13 at `C:\Users\benla\AppData\Local\Programs\Python\Python313\`
- Anaconda Python at `C:\Users\benla\anaconda3\`

The `anthropic` package was installed in Anaconda, but `rtgs` command used Python 3.13.

**Error**:
```
ModuleNotFoundError: No module named 'anthropic'
```

**Resolution**:
```powershell
# Install in correct Python environment
C:\Users\benla\AppData\Local\Programs\Python\Python313\Scripts\pip.exe install anthropic
```

**Recommendation**:
- Document Python environment requirements
- Add dependency check to CLI startup
- Consider conda environment.yml file

---

### Issue #2: Missing anthropic Package

**Severity**: 🔴 CRITICAL - Blocks design command
**Status**: Resolved

**Problem**:

The `anthropic` package is required but not listed in project dependencies.

**Resolution**:

1. Add to `pyproject.toml` or `requirements.txt`:
```toml
dependencies = [
    "anthropic>=0.73.0",
    "geopandas>=0.14.0",
    # ... other dependencies
]
```

2. Document in README:
```markdown
## Installation

pip install anthropic
```

---

## Recommendations

### Immediate Actions (Before Next Test)

1. **Fix Bug #1** (categorical scoring AttributeError) - CRITICAL
2. **Fix Bug #2** (CLI context parameter) - MEDIUM
3. **Document Issue #1** (study area not enforced) - CRITICAL for user expectations
4. **Fix Issue #2** (CRS reprojection) - CRITICAL for accuracy

### Short-Term Improvements (Next Sprint)

1. **Implement proper study area boundaries**
   - Load boundary shapefiles
   - Clip grid to boundaries
   - Support multiple boundary types (county, watershed, custom)

2. **Add dataset schema to design prompt**
   - Let Claude see column names
   - Generate correct column references
   - Validate column existence

3. **Improve error messages**
   - Show which dataset/criterion failed
   - Suggest fixes for common errors
   - Validate before execution

4. **Add data quality checks**
   - Repair invalid geometries
   - Check for empty datasets
   - Warn about CRS mismatches

### Long-Term Enhancements (Future Releases)

1. **Interactive refinement**
   - Let users fix column names
   - Adjust weights interactively
   - Preview results before full run

2. **Performance optimization**
   - Remove 10,000 cell limit
   - Implement chunked processing
   - Add progress bars

3. **Better spatial extent handling**
   - Auto-detect appropriate grid size
   - Support multiple study area types
   - Adaptive grid resolution

4. **Comprehensive testing**
   - Unit tests for all scoring functions
   - Integration tests with real data
   - End-to-end workflow tests

---

## Test Summary

**Test Date**: January 18, 2025
**Test Scenario**: Wildlife corridor analysis for Hennepin County
**Model File**: `wildlife_corridor_suitability_hennepin.yaml`

### Test Results

| Phase | Status | Notes |
|-------|--------|-------|
| Design | ✅ SUCCESS | Model generated successfully with Claude AI |
| Validation | ⚠️ NOT TESTED | YAML structure looks valid |
| Execution | 🔴 FAILED | AttributeError in categorical scoring |
| Output | ❌ NOT CREATED | Execution failed before output |

### Datasets Loaded Successfully

- ✅ wildlife_areas (distance_decay scoring works)
- ✅ land_use (16 invalid geometries, categorical scoring fails)
- ✅ watersheds (12 layers, uses default, distance_decay works)

### What Worked

1. ✅ Claude API integration
2. ✅ Natural language → YAML model generation
3. ✅ Dataset loading from spatial_data module
4. ✅ Distance decay scoring (with CRS warning)
5. ✅ YAML serialization/deserialization

### What Failed

1. ❌ Categorical scoring (Bug #1)
2. ❌ Study area boundary enforcement (Issue #1)
3. ❌ CRS handling for distance calculations (Issue #2)
4. ❌ Column name detection for categorical data (Problem #1)

---

## Conclusion

The suitability_modeling module demonstrates promising AI-powered design capabilities but requires critical bug fixes before it can produce reliable results. The most significant issues are:

1. **Execution blocker**: AttributeError in categorical scoring
2. **Accuracy issues**: Geographic CRS causing incorrect distances
3. **Expectation mismatch**: Study area boundaries not enforced

Once these core issues are addressed, the module has strong potential for enabling rapid suitability analysis with minimal GIS expertise required from users.

**Next Steps**: Fix critical bugs, then conduct full end-to-end test with output validation.
