# Study Area Boundary & Analysis Units Integration

## Overview

Successfully integrated **study area boundary** and **analysis unit** support into the suitability modeling module. The system can now:

1. **Define study area boundaries** - Clip all analysis to a specific geographic boundary (e.g., Hennepin County)
2. **Use multiple analysis unit types**:
   - Grid cells (existing behavior, now boundary-aware)
   - Parcels (land parcels as analysis units)
   - Cities/Towns (municipalities as analysis units)
   - Any custom dataset

This addresses the critical bug where the study area boundary was not enforced during analysis.

## Architecture Changes

### Model Specification Enhancements

**File:** `core/model_specification.py`

Added three new dataclasses to support boundaries and analysis units:

```python
@dataclass
class StudyAreaConfig:
    """Configuration for study area boundary."""
    dataset: Optional[str] = None  # e.g., "hennepin_county_boundary"
    description: str = "Hennepin County"

@dataclass
class AnalysisUnitsConfig:
    """Configuration for analysis units."""
    type: str = "grid"  # "grid", "parcels", "cities", "dataset"
    dataset: Optional[str] = None  # Dataset name if using parcels/cities
    cell_size: float = 100.0  # Grid cell size in meters
    max_cells: int = 10000  # Maximum number of cells/features

@dataclass
class ModelSpecification:
    # ... existing fields ...
    study_area_config: Optional[StudyAreaConfig] = None
    analysis_units_config: Optional[AnalysisUnitsConfig] = None
```

**Key Features:**
- Backward compatible - defaults to no boundary and grid cells if not specified
- Serializes to/from YAML for human-readable model specifications
- Validates configuration on load

### Execution Engine Enhancements

**File:** `core/execution_engine.py`

Completely rewrote the execution workflow to support boundaries and analysis units:

#### New Workflow

```
1. Load study area boundary (if specified)
   ↓
2. Load datasets and clip to boundary
   ↓
3. Create analysis units (grid, parcels, or cities)
   ↓
4. Calculate criterion scores for each unit
   ↓
5. Combine scores with weights
   ↓
6. Export results
```

#### New Methods

1. **`_load_study_area_boundary()`**
   - Loads boundary dataset from PostGIS or spatial_data
   - Returns GeoDataFrame with boundary geometry
   - Returns None if no boundary specified (backward compatible)

2. **`_load_datasets(study_area_boundary)`**
   - Modified to accept boundary parameter
   - Clips each dataset to boundary after loading
   - Ensures CRS compatibility
   - Logs clipping statistics

3. **`_create_study_area(study_area_boundary)`**
   - Now dispatches to specialized methods based on analysis unit type
   - Routes to `_create_grid_units()` or `_load_analysis_units()`

4. **`_create_grid_units(study_area_boundary, analysis_config)`**
   - Creates regular grid cells
   - Clips grid to boundary if specified
   - Uses cell_size and max_cells from config
   - Only creates cells that intersect boundary

5. **`_load_analysis_units(study_area_boundary, analysis_config)`**
   - Loads analysis units from dataset (parcels, cities, etc.)
   - Clips units to boundary if specified
   - Limits number of units to max_cells
   - Supports random sampling if dataset is too large

## Database Integration

### Loaded Datasets

Three new datasets were loaded into PostGIS:

| Dataset Name | Type | Features | Description |
|-------------|------|----------|-------------|
| `hennepin_county_boundary` | Boundary | 1 | County administrative boundary |
| `hennepin_county_cities` | Analysis Unit | ~50 | Cities and towns (CTUs) |
| `hennepin_county_parcels` | Analysis Unit | ~450,000 | Land parcels |

**Loading Script:** `data/migrations/load_shapefile.py`

- Auto-detects dataset type and assigns appropriate tags
- Registers in metadata catalog
- Creates spatial indexes
- Handles CRS transformation to EPSG:26915

## Usage Examples

### Example 1: Grid Analysis with County Boundary

```yaml
model_id: conservation_easements
model_type: weighted_overlay
objective: Identify suitable conservation easement locations

study_area_config:
  dataset: hennepin_county_boundary
  description: Hennepin County

analysis_units_config:
  type: grid
  cell_size: 100.0
  max_cells: 10000

criteria:
  - dataset_name: mn_protected_areas_analysis
    criterion_name: Proximity to Protected Areas
    weight: 40.0
    scoring_function:
      type: distance_decay
      params:
        max_distance: 1000
        decay_rate: 0.002
```

This will:
1. Load Hennepin County boundary
2. Clip all datasets to county boundary
3. Create 100m grid cells only within county
4. Score each cell

### Example 2: Parcel-Based Analysis

```yaml
study_area_config:
  dataset: hennepin_county_boundary
  description: Hennepin County

analysis_units_config:
  type: parcels
  dataset: hennepin_county_parcels
  max_cells: 50000  # Limit to 50k parcels for performance

criteria:
  # ... same as above ...
```

This will:
1. Load Hennepin County boundary
2. Load parcels dataset and clip to boundary
3. Score each parcel individually
4. Results show suitability score per parcel

### Example 3: City-Based Analysis

```yaml
study_area_config:
  dataset: hennepin_county_boundary
  description: Hennepin County

analysis_units_config:
  type: cities
  dataset: hennepin_county_cities
  max_cells: 100

criteria:
  # ... same as above ...
```

This will:
1. Load Hennepin County boundary
2. Load cities/towns dataset
3. Score each municipality
4. Results show suitability score per city

## CLI Usage

The CLI commands automatically support the new features:

### Design a Model

```bash
# Claude AI will understand boundary and analysis unit requirements
rtgs suitability design \
  --input requirements.txt \
  --output model.yaml \
  --db-url postgresql://postgres:password@localhost/rtgs_suitability_data
```

**Example requirements.txt:**
```
Objective:
Identify suitable parcels for conservation easements in Hennepin County.

Study Area:
Use Hennepin County boundary (hennepin_county_boundary).

Analysis Units:
Analyze individual parcels (hennepin_county_parcels).

Criteria:
1. Proximity to protected areas (40%)
2. Habitat diversity (30%)
3. Groundwater recharge importance (30%)
```

### Execute a Model

```bash
rtgs suitability execute \
  --model model.yaml \
  --output-dir ./results \
  --output-format geoparquet \
  --db-url postgresql://postgres:password@localhost/rtgs_suitability_data
```

### Python API

```python
from rtgs_lab_tools.suitability_modeling import (
    ModelSpecification,
    ModelCriterion,
    ScoringFunction,
    StudyAreaConfig,
    AnalysisUnitsConfig,
    execute_model
)

# Create model with parcels
model = ModelSpecification(
    model_id="parcel_suitability",
    model_type="weighted_overlay",
    objective="Score parcels for conservation",
    study_area_config=StudyAreaConfig(
        dataset="hennepin_county_boundary"
    ),
    analysis_units_config=AnalysisUnitsConfig(
        type="parcels",
        dataset="hennepin_county_parcels",
        max_cells=10000
    ),
    criteria=[
        # ... define criteria ...
    ]
)

# Execute
results = execute_model(
    model_spec=model,
    output_dir="./results",
    db_url="postgresql://postgres:password@localhost/rtgs_suitability_data"
)
```

## Testing

### Test Script

**File:** `test_boundary_integration.py`

Run the integration test:

```bash
cd src/rtgs_lab_tools/suitability_modeling
export SUITABILITY_DB_URL="postgresql://postgres:password@localhost:5432/rtgs_suitability_data"
python test_boundary_integration.py
```

The test:
1. Creates a model with boundary and grid units
2. Saves/loads to verify serialization
3. Executes the model
4. Verifies results

### Manual Testing Checklist

- [ ] Test grid analysis with boundary
- [ ] Test parcel analysis with boundary
- [ ] Test city analysis with boundary
- [ ] Test without boundary (backward compatibility)
- [ ] Test with different grid cell sizes
- [ ] Test max_cells limiting
- [ ] Test with multiple criteria from PostGIS
- [ ] Test with mixed PostGIS + spatial_data criteria

## Performance Considerations

### Parcel Analysis Performance

Hennepin County has ~450,000 parcels. Performance tips:

1. **Limit with max_cells**: Set `max_cells: 10000` to randomly sample parcels
2. **Filter by criteria**: Use spatial filters in model design to focus on specific areas
3. **Use spatial indexes**: Ensure PostGIS spatial indexes exist (they do!)
4. **Optimize scoring functions**: Distance calculations can be slow - use max_distance wisely

### Grid Analysis Performance

- **100m cells** = ~25,000 cells for Hennepin County (manageable)
- **50m cells** = ~100,000 cells (slower)
- **500m cells** = ~1,000 cells (fast, good for testing)

### Database Query Optimization

The PostGIS data manager uses:
- Spatial indexes (GiST) for fast intersection queries
- Boundary-based filtering to load only relevant features
- Efficient clipping with `intersects()` predicates

## Benefits

✅ **Accurate Analysis** - Results now properly constrained to study area
✅ **Flexible Units** - Analyze by grid, parcels, cities, or any dataset
✅ **Performance** - Boundary clipping reduces data volume
✅ **Real-World Use Cases** - Parcel-level suitability scoring
✅ **Transparent Results** - Know exactly which parcel/city scored what
✅ **Backward Compatible** - Old models still work (default to no boundary, grid cells)

## Known Limitations

1. **Large Parcel Datasets**: 450k parcels can be slow - use max_cells to limit
2. **Memory Usage**: Loading large datasets into memory (consider spatial filtering in future)
3. **Categorical Scoring on Parcels**: Assumes parcels have relevant attributes - may need joins

## Future Enhancements

Potential improvements:

1. **Spatial Join Optimization**: Pre-compute parcel attributes from criteria datasets
2. **Incremental Processing**: Process parcels in batches for memory efficiency
3. **Multi-Boundary Support**: Analyze multiple counties or regions in one model
4. **Custom Aggregation**: Allow aggregating results by city, watershed, etc.
5. **Caching**: Cache boundary and analysis unit datasets for faster re-runs

## Related Documentation

- `docs/postgis_integration_summary.md` - PostGIS database integration
- `docs/configuration.md` - Database configuration guide
- `data/migrations/README.md` - Database migration instructions
- `core/model_specification.py` - Model specification API
- `core/execution_engine.py` - Execution engine implementation
