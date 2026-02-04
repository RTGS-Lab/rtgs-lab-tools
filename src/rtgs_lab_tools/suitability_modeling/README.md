# Suitability Modeling Module

**Status:** MVP - Minimum Viable Product
**Version:** 0.1.0
**Model Type:** Weighted Overlay

## Overview

The suitability modeling module is an AI-powered spatial analysis framework that enables users to design and execute suitability analyses using natural language requirements and Claude AI.

### Key Features

- **Natural Language Input** - Describe your analysis in plain text
- **AI-Powered Design** - Claude interprets requirements and designs models
- **Unified Data Access** - Uses `spatial_data` module for all datasets
- **Weighted Overlay** - Classic suitability modeling method
- **Multiple Export Formats** - GeoParquet, Shapefile, GeoJSON, CSV
- **Transparent & Editable** - Models saved as human-readable YAML

## Quick Start

### Prerequisites

```bash
# Install required packages
pip install anthropic geopandas fiona pyyaml

# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"

# Set path to Hennepin County FGDB (for HC datasets)
export RTGS_FGDB_PATH="/path/to/HC_EasementAnalysis_Model_Inputs_2020.gdb"
```

### Basic Workflow

```bash
# 1. Check available datasets
rtgs suitability list-datasets

# 2. Write requirements (see examples/wildlife_corridor_requirements.txt)

# 3. Design model with Claude AI
rtgs suitability design --input requirements.txt

# 4. Review and edit the generated YAML file

# 5. Execute the model
rtgs suitability execute --model model.yaml
```

## CLI Commands

### `list-datasets` - Dataset Discovery

List all available datasets from both FGDB and MN Geospatial Commons.

```bash
rtgs suitability list-datasets
```

**Output:**
```
Available Spatial Datasets
============================================================

FGDB Status: Configured and available

Hennepin County Datasets (FGDB)
----------------------------------------
  bee_habitat
    Bee Habitat Analysis - pollinator habitat suitability scores
    Features: 2
  habitat_diversity
    Habitat Diversity Level 3 Analysis
    Features: 51
  ...

MN Geospatial Commons (Public)
----------------------------------------
  wildlife_areas
    DNR Wildlife Management Areas
  ...

Total: 26 datasets
  - FGDB: 16
  - MN Geospatial: 10
```

### `design` - Create Model with AI

Design a suitability model from natural language requirements.

```bash
rtgs suitability design --input requirements.txt --output model.yaml
```

**Options:**
- `--input, -i` (required) - Requirements text file
- `--output, -o` - Output YAML file (default: `{model_id}.yaml`)
- `--api-key` - Anthropic API key (or set `ANTHROPIC_API_KEY` env var)

**What happens:**
1. Reads your requirements
2. Loads available datasets from spatial_data
3. Sends to Claude AI for interpretation
4. Generates validated model specification
5. Saves as human-readable YAML

### `execute` - Run the Model

Execute a suitability model and generate results.

```bash
rtgs suitability execute --model model.yaml --output-format geoparquet
```

**Options:**
- `--model, -m` (required) - Model specification YAML file
- `--output-dir, -o` - Output directory (default: `./results`)
- `--output-format, -f` - `geoparquet` | `shapefile` | `geojson` | `csv`

**Output:**
- Suitability scores (0-100) for each grid cell
- Individual criterion scores for transparency
- Spatial metadata (CRS, bounds, geometry)

### `validate` - Check Model Specification

Validate a model before execution.

```bash
rtgs suitability validate model.yaml
```

Checks:
- Weights sum to 100%
- All datasets are available
- Scoring functions are valid

## Available Datasets

### Hennepin County FGDB (requires RTGS_FGDB_PATH)

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

### MN Geospatial Commons (always available)

| Dataset | Description |
|---------|-------------|
| `wildlife_areas` | DNR Wildlife Management Areas |
| `scientific_and_natural_areas` | DNR SNAs |
| `aquatic_areas` | DNR Aquatic Management Areas |
| `MBS_sites` | Sites of Biodiversity Significance |
| `WAN` | Wildlife Action Network |
| `land_use` | Generalized Land Use 2020 |
| `watersheds` | DNR Level 9 Watersheds |
| `groundwater_recharge` | Groundwater recharge rates |
| `TNC_lands` | The Nature Conservancy lands |
| `cemeteries` | Regional cemeteries |

## Model Specification (YAML)

Models are saved as human-readable YAML files:

```yaml
model_id: wildlife_corridor_hennepin
model_type: weighted_overlay
objective: "Identify wildlife corridor locations"
study_area: Hennepin County

criteria:
  - dataset_name: protected_areas_hc
    criterion_name: "Protected Area Proximity"
    weight: 40
    scoring_function:
      type: distance_decay
      params:
        max_distance: 2000
        decay_rate: 0.001
      output_range: [0, 10]

  - dataset_name: habitat_diversity
    criterion_name: "Habitat Quality"
    weight: 35
    scoring_function:
      type: categorical
      params:
        column: LEVEL_3
        mapping:
          1: 10
          2: 8
          3: 6
          4: 4
          5: 2
      output_range: [0, 10]

  - dataset_name: wildlife_areas
    criterion_name: "Wildlife Corridor Connection"
    weight: 25
    scoring_function:
      type: distance_decay
      params:
        max_distance: 1000
        decay_rate: 0.002
      output_range: [0, 10]

output_range: [0, 100]
```

**You can edit this file!** Adjust weights, add criteria, change parameters.

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
- `mapping` - Dictionary of category → score (0-10)

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

```python
from rtgs_lab_tools.suitability_modeling import design_model, execute_model

# Design a model
model_spec = design_model(
    requirements_file="requirements.txt",
    output_file="model.yaml"
)

# Execute the model
results = execute_model(
    model_spec="model.yaml",
    output_dir="./results",
    output_format="geoparquet"
)

print(f"Results: {results['output_file']}")
print(f"Features: {results['num_features']}")
```

## Configuration

### Environment Variables

```bash
# Required for model design
export ANTHROPIC_API_KEY="sk-ant-..."

# Required for Hennepin County datasets
export RTGS_FGDB_PATH="/path/to/HC_EasementAnalysis_Model_Inputs_2020.gdb"
```

See `docs/configuration.md` for detailed setup instructions.

## Architecture

### Data Flow

```
requirements.txt
       │
       ▼
┌──────────────────┐
│  model_designer  │ ──► Claude AI
└────────┬─────────┘
         │
         ▼
    model.yaml
         │
         ▼
┌──────────────────┐     ┌──────────────┐
│ execution_engine │ ◄── │ spatial_data │
└────────┬─────────┘     └──────────────┘
         │                     │
         │              ┌──────┴──────┐
         │              │             │
         ▼              ▼             ▼
   results.parquet   FGDB      MN Geospatial
```

### Module Integration

The `suitability_modeling` module uses `spatial_data` as its data layer:

- **spatial_data** handles all data extraction (FGDB + MN Geospatial)
- **suitability_modeling** focuses on model design and execution
- Unified dataset registry provides seamless access to all sources

## Limitations (MVP)

**Current:**
- Only weighted overlay method (no boolean constraints, no AHP)
- Only 2 scoring functions (distance decay, categorical)
- Simple grid-based analysis (100m cells default)
- No interactive refinement (edit YAML manually)

**Coming soon:**
- Boolean constraints
- More scoring functions (linear, threshold, fuzzy)
- Interactive refinement via chat
- Custom study areas
- AHP and other MCDA methods

## Troubleshooting

### "FGDB path not configured"

Set the environment variable:
```bash
export RTGS_FGDB_PATH="/path/to/HC_EasementAnalysis_Model_Inputs_2020.gdb"
```

### "Anthropic API key required"

Set your API key:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### "Dataset not found"

Check available datasets:
```bash
rtgs suitability list-datasets
```

### Model execution is slow

The MVP uses 100m grid cells. For large areas, this creates many cells. Use larger cell sizes for testing or limit study area.

## Examples

See `examples/wildlife_corridor_requirements.txt` for a complete example.

## Contributing

This is an MVP. Contributions welcome!

**Priority improvements:**
1. Add more scoring functions
2. Implement boolean constraints
3. Add interactive refinement
4. Performance optimization
5. Additional MCDA methods

## Contact

**RTGS Lab:** https://rtgs.umn.edu/
**Repository:** https://github.com/RTGS-Lab/rtgs-lab-tools

## License

MIT License - see main project LICENSE file
