# Suitability Modeling Module

**Status:** Active Development

**Version:** 0.2.0

**Model Type:** Weighted Overlay

## Overview

The suitability modeling module is an AI-powered spatial analysis framework that enables users to design and execute suitability analyses using natural language requirements and Claude AI (or any other LLM with API access) with structured outputs.

### Key Features

- **Natural Language Input** - Describe your analysis in plain text
- **AI-Powered Design** - Claude designs models constrained to a Pydantic JSON schema (structured outputs)
- **Bring Your Own Data** - Point the CLI at any spatial files, directories, or FGDBs
- **Weighted Overlay** - Classic suitability modeling method
- **Multiple Export Formats** - GeoParquet, Shapefile, GeoJSON, CSV
- **Transparent & Editable** - Models saved as human-readable YAML
- **Reproducible** - `run-config` command replays analysis from a YAML config

## Quick Start

### Prerequisites

```bash
# Install required packages (included in pyproject.toml)
pip install anthropic pydantic geopandas fiona pyyaml

# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"
```

### Basic Workflow

```bash
# Interactive pipeline — prompts for study area, datasets, and requirements
rtgs suitability run

# Non-interactive — all paths and parameters in a YAML config
rtgs suitability run-config --config pipeline_config.yaml

# Validate a model YAML without executing
rtgs suitability validate model.yaml
```

## CLI Commands

### `run` - Interactive Pipeline

Walks through a 7-step pipeline: study area, analysis units, datasets, requirements, AI model design, review, and execution.

```bash
rtgs suitability run
rtgs suitability run --output-dir ./my_results --output-format shapefile
```

**Options:**
- `--api-key` - Anthropic API key (or set `ANTHROPIC_API_KEY` env var)
- `--output-dir, -o` - Output directory (default: `./results`)
- `--output-format, -f` - `geoparquet` | `shapefile` | `geojson` | `csv`

**Pipeline flow:**

```
=== Step 1: Study Area ===
Path to study area boundary file: path/to/boundary.shp
  Loaded 1 features, CRS: EPSG:4326

=== Step 2: Analysis Units ===
Generate a regular grid? [Y/n]: y
Grid cell size in meters [100]: 200

=== Step 3: Variable Datasets ===
Path to datasets (directory, .gdb, or file): path/to/data/
  Loaded 5 datasets:
    - wetlands: 230 features
    - land_cover: 15,400 features
    ...

=== Step 4: Requirements ===
Type objective OR path to .txt file: Find suitable areas for wildlife corridors...

=== Step 5: AI Model Design ===
Calling Claude AI...
  Model designed in 3.2 seconds

=== Step 6: Review ===
Accept this model? [Y/n]: y

=== Step 7: Executing ===
  Done in 12.3 seconds

=== Results ===
Output: ./results/wildlife_corridor_model_results.parquet
Model:  ./results/wildlife_corridor_model.yaml
```

If you reject the model at Step 6, the YAML is saved so you can edit it and re-run via `run-config`.

### `run-config` - Non-interactive Pipeline

Run a suitability analysis from a YAML configuration file. This is the reproducible mode — all file paths and parameters are specified in the config.

```bash
rtgs suitability run-config --config pipeline_config.yaml
rtgs suitability run-config --config pipeline_config.yaml --output-format shapefile
```

**Options:**
- `--config, -c` (required) - YAML configuration file
- `--output-dir, -o` - Override output directory from config
- `--output-format, -f` - Override output format from config

**Config file format:**

```yaml
study_area_path: path/to/boundary.shp
datasets_path: path/to/datasets_dir
model_spec_path: path/to/model.yaml
output_dir: ./results
output_format: geoparquet

# Grid-based analysis units (optional)
grid:
  cell_size: 100
  max_cells: 50000

# Or use a file for analysis units instead of grid
# analysis_units_path: path/to/parcels.shp
```

### `validate` - Check Model Specification

Validate a model YAML file without executing it. Checks Pydantic types, weights sum to 100, and scoring function configuration.

```bash
rtgs suitability validate model.yaml
```

## Model Specification (YAML) Example

Models are saved as human-readable YAML files:

```yaml
model_id: wildlife_corridor_model
model_type: weighted_overlay
objective: "Identify suitable areas for wildlife corridors"
study_area: "Study Area"

criteria:
  - dataset_name: protected_areas
    criterion_name: "Protected Area Proximity"
    weight: 40
    scoring_function:
      type: distance_decay
      params:
        max_distance: 2000
        decay_rate: 0.001
      output_range: [0, 10]

  - dataset_name: land_cover
    criterion_name: "Habitat Quality"
    weight: 35
    scoring_function:
      type: categorical
      params:
        column: LEVEL_3
        mapping:
          Forest: 10
          Wetland: 9
          Grassland: 7
          Agriculture: 4
          Urban: 0
      output_range: [0, 10]

  - dataset_name: wildlife_areas
    criterion_name: "Wildlife Area Connection"
    weight: 25
    scoring_function:
      type: distance_decay
      params:
        max_distance: 1000
        decay_rate: 0.002
      output_range: [0, 10]

output_range: [0, 100]
```

**You can edit this file!** Adjust weights, add criteria, change parameters, then run with `run-config`.

## Scoring Functions

### Distance Decay

Scores based on proximity to features. Closer = higher score.

**Use for:** Proximity to protected areas, water, infrastructure

**Parameters:**
- `max_distance` (meters) - Distance beyond which score = 0
- `decay_rate` (default: 0.001) - How quickly score decreases

**Formula:** `score = 10 * exp(-decay_rate * distance)`

```yaml
scoring_function:
  type: distance_decay
  params:
    max_distance: 2000
    decay_rate: 0.001
```

### Categorical Mapping

Scores based on categorical attributes.

**Use for:** Land use, habitat quality, soil type

**Parameters:**
- `column` - Attribute column name
- `mapping` - Dictionary of category to score (0-10)

```yaml
scoring_function:
  type: categorical
  params:
    column: land_use_type
    mapping:
      Forest: 10
      Wetland: 9
      Grassland: 7
      Agriculture: 4
      Urban: 0
```

## Python API

### Design and Execute a Model

```python
from rtgs_lab_tools.suitability_modeling import design_model, execute_model
from rtgs_lab_tools.spatial_data import (
    extract_from_path,
    extract_all_from_directory,
    generate_grid,
    get_dataset_schema,
)

# Load data
boundary = extract_from_path("boundary.shp")
datasets = extract_all_from_directory("./data/")
grid = generate_grid(boundary, cell_size=200)

# Build schemas for AI
schemas = [get_dataset_schema(name, gdf) for name, gdf in datasets.items()]

# Design model with Claude AI
model_spec = design_model(
    requirements="Find suitable areas for wildlife corridors",
    dataset_schemas=schemas,
)

# Execute
results = execute_model(
    model_spec=model_spec,
    datasets=datasets,
    study_area_boundary=boundary,
    analysis_units=grid,
    output_dir="./results",
    output_format="geoparquet",
)

print(f"Output: {results['output_file']}")
print(f"Features: {results['num_features']}")
```

### Work with Model Specifications Directly

```python
from rtgs_lab_tools.suitability_modeling import (
    ModelSpecification,
    ModelCriterion,
    ScoringFunction,
    print_model_summary,
)

# Load from YAML
spec = ModelSpecification.from_yaml("model.yaml")

# Inspect
print(print_model_summary(spec))

# Validate
spec.validate()

# Modify and save
spec.to_yaml("modified_model.yaml")

# Create programmatically
spec = ModelSpecification(
    model_id="my_model",
    objective="Test analysis",
    criteria=[
        ModelCriterion(
            dataset_name="wetlands",
            criterion_name="Wetland Proximity",
            weight=100,
            scoring_function=ScoringFunction(
                type="distance_decay",
                params={"max_distance": 1000, "decay_rate": 0.002},
            ),
        )
    ],
)

# Generate JSON schema (used by Claude structured outputs)
schema = ModelSpecification.model_json_schema()
```

## Configuration

### Environment Variables

```bash
# Required for AI model design
export ANTHROPIC_API_KEY="sk-ant-..."
```

See `docs/configuration.md` for detailed setup instructions.

## Architecture

### Data Flow

```
User file paths (CLI prompts)
         │
         ▼
┌──────────────────┐
│   spatial_data   │  extract_from_path, extract_all_from_directory
│   extractors     │  generate_grid, get_dataset_schema
└────────┬─────────┘
         │ GeoDataFrames + schemas
         ▼
┌──────────────────┐
│  model_designer  │ ──► Claude AI (structured outputs)
└────────┬─────────┘
         │ ModelSpecification (Pydantic)
         ▼
┌──────────────────┐
│ execution_engine │  pre-loaded GeoDataFrames
└────────┬─────────┘
         │
         ▼
   results.parquet + model.yaml
```

### Key Design Decisions

- **Pydantic ModelSpecification** — Enables structured outputs (Claude's response is hard-constrained to the JSON schema), validation, and clean serialization
- **Pre-loaded data** — GeoDataFrames stay in memory; no temp files or disk I/O round-trips
- **No internal dataset registry** — Data comes from user-provided file paths routed through `spatial_data`'s extractors
- **Linear CLI flow** — No menus, no back-navigation; each step validates before moving on

### Module Structure

```
suitability_modeling/
├── __init__.py                    # v0.2.0, lazy imports
├── README.md                      # This file
├── cli.py                         # run, run-config, validate commands
├── core/
│   ├── __init__.py
│   ├── model_specification.py    # Pydantic models (ModelSpecification, etc.)
│   ├── model_designer.py         # design_model(), print_model_summary()
│   └── execution_engine.py       # SuitabilityEngine, execute_model()
├── llm/
│   ├── __init__.py
│   └── claude_client.py          # ClaudeClient with structured outputs
├── examples/
│   └── wildlife_corridor_requirements.txt
└── docs/
    ├── dev-notes.md              # Development notes and changelog
    ├── pipeline_redesign.md      # v0.2.0 design document
    └── *.md                      # Additional documentation
```

## Limitations

**Current:**
- Only weighted overlay method (no boolean or other options)
- Only 2 scoring functions (distance decay, categorical)
- Grid or feature-based analysis units
- No interactive refinement (edit YAML manually)

**Future:**
- Boolean constraints
- More scoring functions (linear, threshold, fuzzy)
- Interactive refinement via chat
- Other MCDA methods

## Troubleshooting

### "Anthropic API key required"

Set your API key:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### Model execution is slow

Large study areas with small grid cells create many cells. Increase the cell size or set a lower `max_cells` limit.

### Validation failed: weights must sum to 100

All criterion weights in the YAML must sum to exactly 100. Check your `weight` values.

---