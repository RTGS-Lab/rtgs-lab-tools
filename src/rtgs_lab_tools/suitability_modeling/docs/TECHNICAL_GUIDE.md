# Suitability Modeling Module - Technical Guide

**Version:** 0.2.0 (MVP + Bug Fixes)
**Status:** Alpha (Core functionality working, some limitations)
**Last Updated:** 2026-02-04

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Flow](#data-flow)
4. [Core Components](#core-components)
5. [How to Use](#how-to-use)
6. [Model Specification Format](#model-specification-format)
7. [Scoring Functions](#scoring-functions)
8. [Study Area & Analysis Units](#study-area--analysis-units)
9. [Recent Bug Fixes](#recent-bug-fixes)
10. [Known Limitations](#known-limitations)
11. [Extending the Module](#extending-the-module)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The `suitability_modeling` module enables AI-powered suitability analysis for environmental and land-use planning. It uses Claude AI to convert natural language requirements into executable weighted overlay models, making spatial suitability analysis accessible to non-GIS experts.

### Key Features

- **Natural Language Design**: Describe your analysis goals, Claude generates the model
- **Weighted Overlay Analysis**: Multi-criteria decision analysis with customizable weights
- **Dataset Integration**: Seamless integration with `spatial_data` module
- **Multiple Scoring Functions**: Distance decay, categorical, and more
- **Flexible Analysis Units**: Grid cells, parcels, or custom boundaries
- **Study Area Support**: Clip analysis to specific boundaries
- **Multiple Export Formats**: GeoParquet, Shapefile, GeoJSON, CSV
- **YAML Model Specifications**: Human-readable, version-controllable

### Design Philosophy

1. **AI-Assisted Design**: Claude AI helps translate requirements into models
2. **Transparency**: Models saved as human-readable YAML files
3. **Reproducibility**: Version control models, track analyses
4. **Modularity**: Separate design, execution, and export phases
5. **Extensibility**: Easy to add new scoring functions

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                suitability_modeling Module                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐│
│  │  MODEL DESIGN PHASE                                         ││
│  │  ┌──────────────────┐                                       ││
│  │  │ User Requirements│                                       ││
│  │  │ (Natural Language)│                                       ││
│  │  └─────────┬─────────┘                                       ││
│  │            │                                                 ││
│  │            ▼                                                 ││
│  │  ┌──────────────────┐     ┌────────────────┐              ││
│  │  │  Model Designer  │────▶│  Claude AI     │              ││
│  │  │ (model_designer.py)│◀───│ (Claude Client)│              ││
│  │  └─────────┬─────────┘     └────────────────┘              ││
│  │            │                                                 ││
│  │            ▼                                                 ││
│  │  ┌──────────────────┐                                       ││
│  │  │ YAML Model Spec  │                                       ││
│  │  │(human-editable)  │                                       ││
│  │  └──────────────────┘                                       ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐│
│  │  EXECUTION PHASE                                            ││
│  │  ┌──────────────────┐                                       ││
│  │  │  YAML Model Spec │                                       ││
│  │  └─────────┬─────────┘                                       ││
│  │            │                                                 ││
│  │            ▼                                                 ││
│  │  ┌──────────────────┐                                       ││
│  │  │ Execution Engine │                                       ││
│  │  │(execution_engine.py)│                                     ││
│  │  └─────────┬─────────┘                                       ││
│  │            │                                                 ││
│  │            ├──────────────────────────────────┐             ││
│  │            ▼                                  ▼             ││
│  │  ┌──────────────────┐              ┌──────────────────┐   ││
│  │  │ Load Study Area  │              │  Load Datasets   │   ││
│  │  │ Boundary (opt)   │              │(via spatial_data)│   ││
│  │  └─────────┬─────────┘              └─────────┬───────┘   ││
│  │            │                                  │             ││
│  │            └────────────┬─────────────────────┘             ││
│  │                        ▼                                   ││
│  │              ┌──────────────────┐                           ││
│  │              │ Create Analysis  │                           ││
│  │              │ Units (Grid/     │                           ││
│  │              │ Parcels/Custom)  │                           ││
│  │              └─────────┬─────────┘                           ││
│  │                        │                                   ││
│  │                        ▼                                   ││
│  │              ┌──────────────────┐                           ││
│  │              │ Score Each       │                           ││
│  │              │ Criterion        │                           ││
│  │              │ (distance_decay, │                           ││
│  │              │  categorical)    │                           ││
│  │              └─────────┬─────────┘                           ││
│  │                        │                                   ││
│  │                        ▼                                   ││
│  │              ┌──────────────────┐                           ││
│  │              │ Combine Scores   │                           ││
│  │              │ (Weighted Sum)   │                           ││
│  │              └─────────┬─────────┘                           ││
│  │                        │                                   ││
│  │                        ▼                                   ││
│  │              ┌──────────────────┐                           ││
│  │              │ GeoDataFrame with│                           ││
│  │              │ Suitability Score│                           ││
│  │              └─────────┬─────────┘                           ││
│  │                        │                                   ││
│  │                        ▼                                   ││
│  │              ┌──────────────────┐                           ││
│  │              │ Export Results   │                           ││
│  │              │(GeoParquet, SHP, │                           ││
│  │              │ GeoJSON, CSV)    │                           ││
│  │              └──────────────────┘                           ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Module Structure

```
suitability_modeling/
├── __init__.py                    # Module interface
├── README.md                      # User documentation
├── cli.py                         # CLI commands
│
├── core/
│   ├── __init__.py
│   ├── model_specification.py     # Data classes for models
│   ├── model_designer.py          # AI-powered model design
│   ├── execution_engine.py        # Weighted overlay execution
│   └── dataset_registry.py        # Dataset access (delegates to spatial_data)
│
├── llm/
│   ├── __init__.py
│   └── claude_client.py           # Claude API integration
│
├── docs/
│   ├── TECHNICAL_GUIDE.md         # This file
│   ├── README.md
│   ├── architecture.md            # Detailed architecture
│   ├── issues_and_limitations.md  # Known issues (pre-fixes)
│   ├── configuration.md
│   └── planning.md
│
├── examples/
│   └── wildlife_corridor_requirements.txt
│
└── test_boundary_integration.py   # Integration tests
```

---

## Data Flow

### Complete Analysis Flow

```
┌────────────────────────────────────────────────────────────────┐
│ 1. Design Model (Optional - can also write YAML directly)      │
│    rtgs suitability-modeling design requirements.txt           │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ 2. Model Designer Calls Claude AI                              │
│    - Reads requirements                                         │
│    - Sends to Claude with dataset context                      │
│    - Claude generates model specification                       │
│    - Saves as YAML file                                         │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ 3. User Reviews/Edits YAML (optional)                          │
│    - Adjust weights                                             │
│    - Change scoring parameters                                  │
│    - Modify criteria                                            │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ 4. Execute Model                                                │
│    rtgs suitability-modeling execute model.yaml                │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ 5. Load Study Area Boundary (if specified)                     │
│    - Loads boundary dataset from spatial_data                  │
│    - Creates spatial extent for analysis                        │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ 6. Load Required Datasets                                      │
│    - For each criterion, extract dataset via spatial_data      │
│    - Clip to study area boundary (if specified)                │
│    - Store in memory                                            │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ 7. Create Analysis Units                                       │
│    Grid Mode:                                                   │
│    - Generate regular grid cells                                │
│    - Clip cells to study area boundary                         │
│    - Cell size configurable (default: 100m)                    │
│                                                                 │
│    Parcel Mode (future):                                        │
│    - Load parcel dataset                                        │
│    - Clip to study area                                         │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ 8. Score Each Criterion                                        │
│    For each criterion:                                          │
│    - Get dataset features                                       │
│    - Apply scoring function:                                    │
│                                                                 │
│      Distance Decay:                                            │
│      - Reproject to projected CRS (EPSG:5070)                  │
│      - Calculate distance to nearest feature (meters)          │
│      - Apply exponential decay formula                          │
│      - Scores: 10 (closest) → 0 (far)                          │
│                                                                 │
│      Categorical:                                               │
│      - Spatial join analysis units with features               │
│      - Map categories to scores via lookup                      │
│      - Scores: user-defined per category                        │
│                                                                 │
│    - Return array of scores for analysis units                 │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ 9. Combine Scores (Weighted Sum)                               │
│    final_score = Σ(criterion_score * weight)                   │
│                                                                 │
│    Example:                                                     │
│    - Criterion 1: score=8, weight=60% → 8 * 0.6 = 4.8         │
│    - Criterion 2: score=6, weight=40% → 6 * 0.4 = 2.4         │
│    - Final: 4.8 + 2.4 = 7.2                                    │
│                                                                 │
│    Scale to output range (0-100):                               │
│    - Multiply by 10: 7.2 * 10 = 72                             │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ 10. Create Output GeoDataFrame                                 │
│     Columns:                                                    │
│     - geometry: Analysis unit geometry (grid cells, etc.)      │
│     - suitability_score: Final score (0-100)                   │
│     - [criterion_name]_score: Individual criterion scores      │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ 11. Export Results                                             │
│     - GeoParquet (default, best performance)                   │
│     - Shapefile (GIS compatibility)                            │
│     - GeoJSON (web mapping)                                     │
│     - CSV (spreadsheet analysis)                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Model Specification (`core/model_specification.py`)

**Data Classes** defining model structure:

```python
@dataclass
class ScoringFunction:
    type: str                           # "distance_decay", "categorical"
    params: Dict[str, Any]              # Function-specific parameters
    output_range: Tuple[float, float]   # (min, max) e.g., (0, 10)

@dataclass
class ModelCriterion:
    dataset_name: str                   # Dataset to use
    criterion_name: str                 # Human-readable name
    scoring_function: ScoringFunction   # How to score this criterion
    weight: float                       # Importance (0-100%)

@dataclass
class StudyAreaConfig:
    dataset: Optional[str]              # Dataset for boundary
    description: str                    # Description of study area

@dataclass
class AnalysisUnitsConfig:
    type: str                           # "grid", "parcels", "dataset"
    dataset: Optional[str]              # Dataset for units (if applicable)
    cell_size: float = 100.0            # Grid cell size in meters
    max_cells: int = 10000              # Maximum cells to prevent memory issues

@dataclass
class ModelSpecification:
    model_id: str
    model_type: str                     # "weighted_overlay"
    objective: str                      # Analysis goal
    study_area: str                     # Study area description
    study_area_config: StudyAreaConfig
    analysis_units_config: AnalysisUnitsConfig
    criteria: List[ModelCriterion]
    output_range: Tuple[float, float]   # (0, 100)
    metadata: Dict[str, Any]            # Additional info

    def to_yaml(self, filepath: str) -> None:
        """Save model to YAML file"""
        pass

    @classmethod
    def from_yaml(cls, filepath: str) -> "ModelSpecification":
        """Load model from YAML file"""
        pass

    def validate(self) -> None:
        """Validate model specification"""
        # Check weights sum to 100
        # Verify datasets exist
        # Validate scoring function parameters
        pass
```

### 2. Model Designer (`core/model_designer.py`)

**AI-Powered Model Generation**:

```python
class ModelDesigner:
    def __init__(self, claude_client: ClaudeClient):
        self.claude = claude_client

    def design_model(self, requirements: str, available_datasets: Dict) -> ModelSpecification:
        """
        Convert natural language requirements to model specification.

        Process:
        1. Build prompt with requirements + dataset context
        2. Send to Claude AI
        3. Parse response into ModelSpecification
        4. Validate generated model
        5. Return specification
        """
        pass

    def _build_design_prompt(self, requirements: str, datasets: Dict) -> str:
        """Create prompt for Claude with context"""
        pass
```

### 3. Claude Client (`llm/claude_client.py`)

**API Integration**:

```python
class ClaudeClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate_model(self, prompt: str, max_tokens: int = 4096) -> str:
        """Send prompt to Claude and get response"""
        pass

    def parse_yaml_from_response(self, response: str) -> Dict:
        """Extract YAML from Claude's response"""
        pass
```

### 4. Execution Engine (`core/execution_engine.py`)

**Main Execution Class**:

```python
class SuitabilityEngine:
    def __init__(self, model_spec: ModelSpecification):
        self.model_spec = model_spec
        self.datasets = {}  # Loaded datasets

    def execute(self) -> gpd.GeoDataFrame:
        """
        Execute weighted overlay analysis.

        Steps:
        1. Load study area boundary (if specified)
        2. Load required datasets
        3. Create analysis units (grid/parcels)
        4. Score each criterion
        5. Combine scores with weights
        6. Return GeoDataFrame with results
        """
        pass

    def _load_datasets(self, study_area_boundary):
        """Load datasets via spatial_data module"""
        pass

    def _create_analysis_units(self, study_area_boundary):
        """Create grid cells or load parcels"""
        pass

    def _score_criterion(self, criterion, study_area):
        """Score one criterion for all analysis units"""
        pass

    def _score_distance_decay(self, study_area, features, scoring_func):
        """
        Distance-based scoring with exponential decay.

        Formula: score = 10 * exp(-decay_rate * distance)

        CRS Handling (FIXED):
        - Detects if CRS is geographic (degrees)
        - Reprojects to EPSG:5070 (NAD83 Conus Albers) for accurate distances
        - Calculates distances in meters
        - Returns scores (0-10 scale)
        """
        pass

    def _score_categorical(self, study_area, features, scoring_func):
        """
        Category-based scoring.

        Process:
        - Spatial join analysis units with features
        - Map categories to scores via lookup
        - Return scores (0-10 scale)

        FIXED: Returns np.asarray() to handle both Series and ndarray
        """
        pass

    def _combine_scores(self, criterion_scores):
        """Weighted sum of criterion scores"""
        pass

    def export_results(self, results_gdf, output_dir, output_format):
        """Export to file"""
        pass
```

**Main Entry Point**:

```python
def execute_model(
    model_spec: ModelSpecification,
    output_dir: str,
    output_format: str = "geoparquet"
) -> Dict:
    """
    Execute suitability model and export results.

    Returns:
        Dict with execution metadata:
        {
            "success": true,
            "model_id": "wildlife_corridor",
            "output_file": "./results/wildlife_corridor_results.parquet",
            "num_features": 500,
            "duration_seconds": 45.2,
            "timestamp": "2026-02-04T14:30:00"
        }
    """
    engine = SuitabilityEngine(model_spec)
    results_gdf = engine.execute()
    output_file = engine.export_results(results_gdf, output_dir, output_format)
    return {...}
```

---

## How to Use

### Workflow Overview

```
Design Model → (Review/Edit) → Execute → Analyze Results
```

### 1. Design Model (AI-Assisted)

**Create requirements file** (`requirements.txt`):

```text
Objective:
Identify suitable locations for wildlife corridors in Hennepin County.

Requirements:
Find areas that could serve as wildlife corridors between protected areas.

Criteria:
1. Close to existing protected areas (wildlife_areas dataset)
   - Within 2km is best
   - Use exponential decay

2. Suitable habitat (land_use dataset)
   - Prefer natural land cover

3. Near water resources (watersheds dataset)
   - Wildlife needs water access

Weights:
- Protected area proximity: 40%
- Habitat quality: 35%
- Water access: 25%

Study Area:
Hennepin County, Minnesota
```

**Run design command**:

```bash
rtgs suitability-modeling design \
  --requirements requirements.txt \
  --output wildlife_corridor_model.yaml
```

**Claude generates**:

```yaml
model_id: wildlife_corridor
model_type: weighted_overlay
objective: Identify suitable wildlife corridor locations

study_area: Hennepin County, Minnesota
study_area_config:
  dataset: null
  description: Hennepin County

analysis_units_config:
  type: grid
  cell_size: 100.0
  max_cells: 10000

criteria:
  - dataset_name: wildlife_areas
    criterion_name: Proximity to Protected Areas
    scoring_function:
      type: distance_decay
      params:
        max_distance: 2000
        decay_rate: 0.002
      output_range: [0, 10]
    weight: 40.0

  - dataset_name: watersheds
    criterion_name: Proximity to Water
    scoring_function:
      type: distance_decay
      params:
        max_distance: 1000
        decay_rate: 0.003
      output_range: [0, 10]
    weight: 25.0

  # ... more criteria

output_range: [0, 100]
```

### 2. Review and Edit (Optional)

Edit the YAML file to adjust:
- Weights
- Scoring parameters
- Add/remove criteria

### 3. Validate Model

```bash
rtgs suitability-modeling validate wildlife_corridor_model.yaml
```

### 4. Execute Model

```bash
rtgs suitability-modeling execute \
  wildlife_corridor_model.yaml \
  --output-dir ./results \
  --output-format geoparquet
```

### 5. Analyze Results

Load results in Python:

```python
import geopandas as gpd

# Load results
results = gpd.read_parquet("./results/wildlife_corridor_results.parquet")

# View suitability scores
print(results["suitability_score"].describe())

# Filter high suitability areas
high_suitability = results[results["suitability_score"] > 70]

# Export for GIS
high_suitability.to_file("high_suitability_areas.shp")
```

Or load in QGIS/ArcGIS for visualization.

---

## Model Specification Format

### Complete YAML Example

```yaml
model_id: example_analysis
model_type: weighted_overlay

objective: Find suitable locations for solar farms

study_area: Hennepin County
study_area_config:
  dataset: county_boundaries        # Optional: boundary dataset
  description: Hennepin County, MN

analysis_units_config:
  type: grid                        # "grid", "parcels", or "dataset"
  dataset: null                     # Dataset name if type="dataset"
  cell_size: 500.0                  # Grid cell size in meters
  max_cells: 5000                   # Limit for performance

criteria:
  - dataset_name: protected_areas
    criterion_name: Distance from Protected Areas
    scoring_function:
      type: distance_decay
      params:
        max_distance: 5000          # Meters
        decay_rate: 0.001           # Decay coefficient
      output_range: [0, 10]
    weight: 30.0

  - dataset_name: land_cover
    criterion_name: Land Cover Suitability
    scoring_function:
      type: categorical
      params:
        column: cover_type          # Column with categories
        mapping:                    # Category → score
          agricultural: 10.0
          grassland: 8.0
          forest: 2.0
          urban: 0.0
      output_range: [0, 10]
    weight: 40.0

  - dataset_name: transmission_lines
    criterion_name: Proximity to Grid
    scoring_function:
      type: distance_decay
      params:
        max_distance: 10000
        decay_rate: 0.0005
      output_range: [0, 10]
    weight: 30.0

output_range: [0, 100]

metadata:
  created_by: user_name
  created_date: "2026-02-04"
  version: "1.0"
```

---

## Scoring Functions

### Distance Decay

**Purpose**: Score based on proximity to features

**Formula**:
```
score = 10 * exp(-decay_rate * distance)
if distance > max_distance: score = 0
```

**Parameters**:
- `max_distance` (float): Maximum distance to consider (meters)
- `decay_rate` (float): Rate of exponential decay (higher = faster decay)

**YAML Example**:
```yaml
scoring_function:
  type: distance_decay
  params:
    max_distance: 2000      # 2km
    decay_rate: 0.001       # Moderate decay
  output_range: [0, 10]
```

**Decay Rate Guidelines**:
- `0.0001`: Very slow decay (gentle gradient)
- `0.001`: Moderate decay (default)
- `0.01`: Fast decay (sharp gradient)

**CRS Handling** (FIXED in v0.2.0):
- Automatically detects geographic CRS (lat/lon)
- Reprojects to EPSG:5070 for accurate distance calculations
- Returns scores on 0-10 scale

---

### Categorical

**Purpose**: Score based on attribute categories

**Process**:
1. Spatial join analysis units with features
2. Get category value from specified column
3. Map category to score via lookup table

**Parameters**:
- `column` (str): Column name containing categories
- `mapping` (Dict[str, float]): Category → score mapping

**YAML Example**:
```yaml
scoring_function:
  type: categorical
  params:
    column: land_cover_type
    mapping:
      forest: 10.0
      wetland: 9.0
      grassland: 7.0
      agricultural: 5.0
      urban: 0.0
  output_range: [0, 10]
```

**FIXED in v0.2.0**:
- Handles both pandas Series and numpy arrays correctly
- No more AttributeError when returning scores

---

## Study Area & Analysis Units

### Study Area Boundary

**Purpose**: Define the spatial extent of analysis

**Configuration**:
```yaml
study_area_config:
  dataset: wildlife_areas      # Use this dataset as boundary
  description: Wildlife management areas
```

**Behavior** (FIXED in v0.2.0):
- Loads boundary dataset via `spatial_data`
- Clips all criterion datasets to boundary
- Clips analysis grid cells to boundary
- Ensures analysis units don't extend outside study area

**If not specified**:
- Uses combined bounds of all datasets
- No clipping performed

---

### Analysis Units

**Grid Mode** (Default):

```yaml
analysis_units_config:
  type: grid
  cell_size: 100.0        # 100m × 100m cells
  max_cells: 10000        # Limit for large areas
```

**Behavior**:
- Creates regular grid covering study area
- Cell size in meters
- If grid would exceed `max_cells`, samples uniformly
- Each cell scored independently

**Parcel Mode** (Partially Implemented):

```yaml
analysis_units_config:
  type: dataset
  dataset: hennepin_parcels
```

**Behavior**:
- Loads dataset as analysis units
- Each feature (parcel) scored independently
- Useful for property-based analyses

---

## Recent Bug Fixes

### Bug #1: Categorical Scoring AttributeError (FIXED)

**Issue**: `execution_engine.py:519`
```python
# Old code:
return scores.values  # AttributeError if scores is ndarray
```

**Problem**: Inconsistent return types from pandas operations caused crashes

**Fix**:
```python
# New code:
return np.asarray(scores)  # Handles both Series and ndarray
```

**Status**: ✅ Fixed and tested

---

### Bug #2: Study Area Boundary Not Enforced (FIXED)

**Issue**: Grid cells that intersected boundaries were included in full, extending outside study area

**Problem**: Inaccurate analysis results, areas outside study area included

**Fix**:
```python
# Old code:
if boundary_geom is None or cell.intersects(boundary_geom):
    geometries.append(cell)

# New code:
if boundary_geom is None:
    geometries.append(cell)
elif cell.intersects(boundary_geom):
    # Clip cell to boundary
    clipped_cell = cell.intersection(boundary_geom)
    if not clipped_cell.is_empty:
        geometries.append(clipped_cell)
```

**Status**: ✅ Fixed and tested

---

### Bug #3: Distance Calculations in Wrong CRS (FIXED)

**Issue**: Distances calculated in geographic CRS (degrees) instead of projected CRS (meters)

**Problem**: Incorrect distance-based scoring, especially at higher latitudes

**Fix**:
```python
# New code:
if study_area.crs and study_area.crs.is_geographic:
    logger.warning(
        f"Converting from geographic CRS ({study_area.crs}) to projected CRS"
    )
    target_crs = "EPSG:5070"  # NAD83 Conus Albers
    study_area_proj = study_area.to_crs(target_crs)
    features_proj = features.to_crs(target_crs)
else:
    study_area_proj = study_area
    features_proj = features

# Calculate distances in meters
distances = study_area_proj.geometry.apply(
    lambda geom: features_proj.distance(geom).min()
)
```

**Status**: ✅ Fixed and tested

---

## Known Limitations

See `docs/issues_and_limitations.md` for comprehensive list. Key limitations:

### 1. Limited Scoring Functions

**Current**: distance_decay, categorical
**Missing**: linear, threshold, fuzzy logic, Gaussian

**Workaround**: Use distance_decay with appropriate decay_rate

---

### 2. No Boolean Constraints

**Issue**: Cannot apply hard filters (e.g., "exclude urban areas")

**Current**: All criteria contribute to score
**Needed**: Ability to exclude areas that fail constraints

**Workaround**: Use categorical scoring with 0 for excluded categories

---

### 3. Grid Size Limitation

**Issue**: Max 10,000 cells prevents high-resolution analysis of large areas

**Impact**: Large study areas get sampled instead of full coverage

**Workaround**:
- Reduce study area size
- Increase cell size
- Run multiple analyses for sub-regions

---

### 4. Dataset Schema Unknown to Claude

**Issue**: Claude doesn't know column names in datasets

**Impact**: Categorical scoring defaults to generic column names

**Workaround**: Manually edit YAML after generation to specify correct column names

---

### 5. Analysis Units Incomplete

**Issue**: Only grid units fully tested

**Impact**: Parcel-based and custom unit analyses may have issues

**Workaround**: Use grid mode for reliable results

---

## Extending the Module

### Adding New Scoring Functions

**1. Add scoring method to `SuitabilityEngine`**:

```python
def _score_linear(
    self,
    study_area: gpd.GeoDataFrame,
    features: gpd.GeoDataFrame,
    scoring_func: ScoringFunction,
) -> np.ndarray:
    """
    Linear scoring based on distance.

    Formula: score = max_score * (1 - distance / max_distance)
    """
    params = scoring_func.params
    max_distance = params.get("max_distance", 1000)
    max_score = params.get("max_score", 10)

    # Calculate distances (with CRS handling)
    if study_area.crs and study_area.crs.is_geographic:
        target_crs = "EPSG:5070"
        study_area_proj = study_area.to_crs(target_crs)
        features_proj = features.to_crs(target_crs)
    else:
        study_area_proj = study_area
        features_proj = features

    distances = study_area_proj.geometry.apply(
        lambda geom: features_proj.distance(geom).min()
    )

    # Linear scoring
    scores = max_score * (1 - distances / max_distance)
    scores = scores.clip(lower=0)  # No negative scores

    return np.asarray(scores)
```

**2. Register in `_score_criterion` method**:

```python
def _score_criterion(self, criterion, study_area):
    scoring_func = criterion.scoring_function

    if scoring_func.type == "distance_decay":
        scores = self._score_distance_decay(study_area, dataset, scoring_func)
    elif scoring_func.type == "categorical":
        scores = self._score_categorical(study_area, dataset, scoring_func)
    elif scoring_func.type == "linear":  # Add here
        scores = self._score_linear(study_area, dataset, scoring_func)
    else:
        raise ValueError(f"Unsupported scoring function: {scoring_func.type}")
```

**3. Update Claude prompt** in `claude_client.py`:

Add new scoring function to the list Claude can use:

```python
AVAILABLE_SCORING_FUNCTIONS:
- distance_decay: Exponential decay with distance
- categorical: Map categories to scores
- linear: Linear decrease with distance  # Add description
```

---

### Adding New Analysis Unit Types

**1. Add method to `SuitabilityEngine`**:

```python
def _create_hexagon_units(self, study_area_boundary, analysis_config):
    """Create hexagonal grid cells for analysis."""
    from shapely.geometry import Polygon
    import math

    cell_size = analysis_config.cell_size
    # ... hexagon generation logic
    return grid_gdf
```

**2. Register in `_create_study_area` method**:

```python
if analysis_config.type == "grid":
    study_area = self._create_grid_units(boundary, analysis_config)
elif analysis_config.type == "hexagon":  # Add here
    study_area = self._create_hexagon_units(boundary, analysis_config)
# ... more types
```

---

## Troubleshooting

### Common Issues

**1. "Claude API key not found"**

```
Error: ANTHROPIC_API_KEY environment variable not set
```

**Solution**:
```bash
export ANTHROPIC_API_KEY=your_key_here
```

---

**2. "Dataset not found"**

```
ValueError: Unknown dataset: my_dataset
```

**Solution**:
- Check dataset name spelling
- Run `rtgs spatial-data list-datasets` to see available datasets
- Ensure `spatial_data` configuration is correct

---

**3. "Model validation failed: weights don't sum to 100"**

```
ValidationError: Criterion weights must sum to 100, got 95.0
```

**Solution**: Adjust weights in YAML:
```yaml
criteria:
  - weight: 40.0
  - weight: 35.0
  - weight: 25.0  # Total: 100.0
```

---

**4. Grid too large**

```
WARNING: Grid would have 50000 cells, sampling 10000 instead
```

**Solution**:
- Increase `max_cells` in config
- Reduce study area size
- Increase `cell_size`

---

**5. CRS transformation warnings**

```
WARNING: Converting from geographic CRS (EPSG:4326) to projected CRS for distance calculation
```

**Solution**: This is expected behavior (Bug #3 fix). Distances are now calculated correctly in meters.

---

**6. Categorical scoring returns all same score**

```
WARNING: Column 'category' not found, using default score of 5
```

**Solution**:
- Check column name in dataset
- Update YAML with correct column name:
  ```yaml
  params:
    column: correct_column_name  # Update this
  ```

---

## API Reference

### Main Functions

**`execute_model(model_spec, output_dir, output_format)`**

Execute suitability model and export results.

**Parameters**:
- `model_spec` (ModelSpecification): Model to execute
- `output_dir` (str): Output directory path
- `output_format` (str): "geoparquet", "shapefile", "geojson", "csv"

**Returns**: Dict with execution results

---

**`ModelSpecification.from_yaml(filepath)`**

Load model from YAML file.

**Parameters**:
- `filepath` (str): Path to YAML file

**Returns**: ModelSpecification instance

---

**`ModelSpecification.validate()`**

Validate model specification.

**Raises**: ValidationError if invalid

---

## Related Documentation

- **README.md**: User guide and quick start
- **architecture.md**: Detailed architecture documentation
- **issues_and_limitations.md**: Known issues (many now fixed!)
- **configuration.md**: Configuration guide
- **planning.md**: Development planning

---

## Version History

**v0.2.0 (2026-02-04)** - Bug Fix Release
- Fixed Bug #1: Categorical scoring AttributeError
- Fixed Bug #2: Study area boundary enforcement
- Fixed Bug #3: Distance calculations in correct CRS
- All critical bugs resolved

**v0.1.0 (2025-11-18)** - MVP Release
- Claude AI integration for model design
- Weighted overlay execution
- Distance decay and categorical scoring
- YAML model specifications
- CLI commands

---
