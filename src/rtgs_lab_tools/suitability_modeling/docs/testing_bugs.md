# Bugs Found During Testing

## Test Date: 2025-01-18

### Bug #1: AttributeError in categorical scoring (CRITICAL)
**Location**: `core/execution_engine.py:324`

**Error**:
```
AttributeError: 'numpy.ndarray' object has no attribute 'values'
```

**Root Cause**:
- Line 322 creates a numpy array: `scores = np.full(len(study_area), 5.0)`
- Line 324 tries to call `.values` on it: `return scores.values`
- Numpy arrays don't have `.values` attribute (that's for pandas Series)

**Fix**:
Change line 324 from:
```python
return scores.values
```
To:
```python
return scores.values if hasattr(scores, 'values') else scores
```

Or better, make line 319 return values directly:
```python
scores = joined[category_column].map(mapping).fillna(0).values
```
And line 324:
```python
return scores
```

---

### Bug #2: Wrong column name for categorical scoring
**Location**: `core/execution_engine.py:312`

**Issue**:
- Default column name is hardcoded as `'category'`
- The land_use dataset doesn't have a column named 'category'
- Falls back to default score of 5 for all cells

**Warning Message**:
```
Column 'category' not found, using default score of 5
```

**Fix**:
- Claude AI should specify the correct column name in the YAML
- OR the categorical scoring function should auto-detect the first text column
- Need to investigate what the actual column names are in the land_use dataset

---

### Bug #3: Geographic CRS warning - distance calculations incorrect
**Location**: `core/execution_engine.py:283`

**Warning**:
```
Geometry is in a geographic CRS. Results from 'distance' are likely incorrect.
Use 'GeoSeries.to_crs()' to re-project geometries to a projected CRS before this operation.
```

**Issue**:
- Distance calculations are being done in lat/lon degrees instead of meters
- The model specifies distances in meters (e.g., `max_distance: 2000`)
- But geometries are not reprojected to a projected CRS first

**Fix**:
In `_calculate_criterion_score()` or `_score_distance_decay()`, add:
```python
# Reproject to projected CRS for accurate distance calculations
if features.crs.is_geographic:
    # Use UTM or State Plane for Minnesota
    features = features.to_crs('EPSG:26915')  # UTM Zone 15N for Minnesota
    study_area = study_area.to_crs('EPSG:26915')
```

---

### Bug #4: Missing context manager in CLI error handling
**Location**: `cli.py:79`

**Error** (from earlier testing):
```
NameError: name 'ctx' is not defined
```

**Issue**:
- Line 79 has `ctx.exit(1)` but function doesn't have `@click.pass_context` decorator
- This was in the `design_command` function

**Status**: Not tested in this run (API key issue fixed first)

**Fix**:
Add `@click.pass_context` decorator and `ctx` parameter to the function signature.

---

## Testing Summary

### What Worked ✓
1. **design** command successfully created YAML model using Claude AI
2. **validate** command (not tested yet, but YAML looks valid)
3. Data loading for all 3 datasets (wildlife_areas, land_use, watersheds)
4. Distance decay scoring for wildlife_areas and watersheds

### What Failed ✗
1. Categorical scoring for land_use dataset (Bug #1 & #2)
2. Distance calculations are inaccurate (Bug #3)

### Next Steps
1. Fix Bug #1 (critical - blocks execution)
2. Investigate land_use dataset schema to fix Bug #2
3. Add CRS reprojection for Bug #3
4. Test validate command
5. Re-test execute command after fixes
6. Verify output files are created correctly

---

## Additional Warnings (Non-Critical)

1. **"DB_USER not found in Secret Manager"** - Logging issue from spatial_data module, doesn't affect execution
2. **"Found 16 invalid geometries"** - Some geometries have issues but processing continues
3. **"Multiple layers in GeoPackage"** - Watersheds dataset has 12 layers, using default layer
4. **"spatial_data module not available"** - Import issue but fallback list works

---

## Test Command Used
```powershell
rtgs suitability execute --model wildlife_corridor_suitability_hennepin.yaml --output-dir ./test_results --output-format geoparquet
```

## Generated Model File
`wildlife_corridor_suitability_hennepin.yaml`

**Criteria:**
- Proximity to Protected Areas (40%) - distance_decay ✓
- Habitat Quality (35%) - categorical ✗ (fails due to Bug #1 & #2)
- Water Access (25%) - distance_decay ✓
