# Suitability Modeling Module

**Status:** MVP - Minimum Viable Product
**Model Type:** Weighted Overlay (only)
**Version:** 0.1.0

## Overview

The suitability modeling module is an AI-powered spatial analysis framework that enables users to design and execute suitability analyses using natural language requirements and Claude AI.

### Key Features

✅ **Natural Language Input** - Describe your analysis in plain text
✅ **AI-Powered Design** - Claude interprets requirements and designs models
✅ **Vetted Datasets** - Uses only quality-controlled data from `spatial_data` module
✅ **Weighted Overlay** - Classic suitability modeling method
✅ **Multiple Export Formats** - GeoParquet, Shapefile, GeoJSON, CSV
✅ **Transparent & Editable** - Models saved as human-readable YAML

---

## Quick Start

### Prerequisites

```bash
# Install required packages
pip install anthropic geopandas pyyaml

# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"
```

### Basic Workflow

1. **Write Requirements** (see `examples/wildlife_corridor_requirements.txt`)
2. **Design Model** - Claude AI creates model specification
3. **Review & Edit** - Check the generated YAML file
4. **Execute Model** - Run the analysis and get results

---

## Usage

### Step 1: Design a Model

```bash
rtgs suitability design --input requirements.txt --output model.yaml
```

**What happens:**
- Reads your requirements
- Sends to Claude AI for interpretation
- Generates a model specification (YAML file)
- Shows model summary

**Output:** `model.yaml` file with complete model specification

### Step 2: Review the Model

Open `model.yaml` in a text editor:

```yaml
model_id: wildlife_corridor_hennepin
model_type: weighted_overlay
objective: "Identify wildlife corridor locations"
study_area: Hennepin County

criteria:
  - dataset_name: wildlife_areas
    criterion_name: "Protected Area Proximity"
    weight: 40
    scoring_function:
      type: distance_decay
      params:
        max_distance: 2000
        decay_rate: 0.001
      output_range: [0, 10]

  - dataset_name: land_use
    criterion_name: "Habitat Quality"
    weight: 35
    scoring_function:
      type: categorical
      params:
        column: land_use_type
        mapping:
          Forest: 10
          Wetland: 9
          Grassland: 7
          Agriculture: 3
          Urban: 0
      output_range: [0, 10]

  - dataset_name: watersheds
    criterion_name: "Water Access"
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

### Step 3: Validate (Optional)

```bash
rtgs suitability validate model.yaml
```

Checks:
- ✓ Weights sum to 100%
- ✓ All datasets are available
- ✓ Scoring functions are valid

### Step 4: Execute the Model

```bash
rtgs suitability execute --model model.yaml --output-format geoparquet
```

**Output:**
- `./results/wildlife_corridor_hennepin_results.parquet`
- Contains suitability scores (0-100) for each grid cell
- Includes individual criterion scores for transparency

---

## CLI Reference

### `rtgs suitability design`

Design a suitability model from requirements.

**Options:**
- `--input, -i` (required) - Requirements text file
- `--output, -o` - Output YAML file (default: `{model_id}.yaml`)
- `--api-key` - Anthropic API key (or set `ANTHROPIC_API_KEY` env var)

**Example:**
```bash
rtgs suitability design \
  --input wildlife_corridor_requirements.txt \
  --output my_model.yaml
```

### `rtgs suitability execute`

Execute a suitability model.

**Options:**
- `--model, -m` (required) - Model specification YAML file
- `--output-dir, -o` - Output directory (default: `./results`)
- `--output-format, -f` - Format: `geoparquet`, `shapefile`, `geojson`, `csv` (default: `geoparquet`)

**Example:**
```bash
rtgs suitability execute \
  --model my_model.yaml \
  --output-dir ./results \
  --output-format geoparquet
```

### `rtgs suitability validate`

Validate a model specification.

**Example:**
```bash
rtgs suitability validate my_model.yaml
```

---

## Scoring Functions

### Distance Decay

Scores based on proximity to features. Closer = higher score.

**Use for:** Proximity to protected areas, water, infrastructure, etc.

**Parameters:**
- `max_distance` (meters) - Distance beyond which score = 0
- `decay_rate` (default: 0.001) - How quickly score decreases with distance

**Formula:** `score = 10 * exp(-decay_rate * distance)`

**Example:**
```yaml
scoring_function:
  type: distance_decay
  params:
    max_distance: 2000  # 2km
    decay_rate: 0.001
```

### Categorical Mapping

Scores based on categorical attributes (land use, soil type, etc.).

**Use for:** Land use suitability, habitat quality, soil suitability, etc.

**Parameters:**
- `column` - Attribute column name
- `mapping` - Dictionary mapping categories to scores (0-10)

**Example:**
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
      Industrial: 0
```

---

## Python API

You can also use the module programmatically:

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

print(f"Results saved to: {results['output_file']}")
```

---

## Available Datasets

The module uses datasets from the `spatial_data` module. Current available datasets:

- `wildlife_areas` - DNR Wildlife Management Areas (1,731 polygons)
- `groundwater_recharge` - Groundwater recharge rates (201k grid cells)
- `scientific_and_natural_areas` - DNR SNAs (237 polygons)
- `TNC_lands` - The Nature Conservancy lands (383 polygons)
- `aquatic_areas` - DNR Aquatic Management Areas (1,571 polygons)
- `MBS_sites` - Sites of Biodiversity Significance (12,591 polygons)
- `WAN` - Wildlife Action Network (133,283 polygons)
- `land_use` - Generalized Land Use 2020 (22 categories)
- `cemeteries` - Cemeteries (108 parcels)
- `watersheds` - DNR Level 9 Watersheds (131,411 polygons)

See `rtgs spatial-data list-datasets` for full list with descriptions.

---

## Examples

See the `examples/` directory for complete examples:

- `wildlife_corridor_requirements.txt` - Wildlife corridor identification
- More examples coming soon!

---

## Limitations (MVP)

**Current limitations:**
- Only weighted overlay method (no boolean constraints, no AHP)
- Only 2 scoring functions (distance decay, categorical)
- Simple grid-based analysis (100m cells)
- No interactive refinement (edit YAML manually)
- No study area auto-resolution (assumes Hennepin County)

**Coming soon:**
- Boolean constraints
- More scoring functions (linear, threshold, fuzzy)
- Interactive refinement via chat
- Custom study areas
- AHP and other MCDA methods

---

## Troubleshooting

### "No module named 'anthropic'"

Install the package:
```bash
pip install anthropic
```

### "Anthropic API key required"

Set your API key:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

Or pass it directly:
```bash
rtgs suitability design --input requirements.txt --api-key "your-key"
```

### "Dataset not found"

The dataset might not be in the `spatial_data` registry. Check available datasets:
```bash
rtgs spatial-data list-datasets
```

### Model execution is slow

The MVP uses a simple grid (100m cells). For very large areas, this can create many cells. Future versions will optimize this.

---

## Contributing

This is an MVP. Contributions welcome!

**Priority improvements:**
1. Add more scoring functions
2. Implement boolean constraints
3. Add interactive refinement
4. Improve study area resolution
5. Performance optimization

---

## Contact

**RTGS Lab:** https://rtgs.umn.edu/
**Repository:** https://github.com/RTGS-Lab/rtgs-lab-tools
**Issues:** Use GitHub issue tracker

---

## License

MIT License - see main project LICENSE file
