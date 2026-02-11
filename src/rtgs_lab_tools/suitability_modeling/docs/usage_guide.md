# Suitability Modeling — Usage Guide

## Prerequisites

```bash
pip install -e .
export ANTHROPIC_API_KEY="sk-ant-..."
```

## What You Need

| Input | Format | Example |
|-------|--------|---------|
| **Study area boundary** | Any spatial file (.shp, .gpkg, .parquet, .geojson) | `county_boundary.shp` |
| **Variable datasets** | Directory of spatial files, a .gdb, or a single file | `./datasets/` |
| **Requirements** | Plain text or a .txt file | `"Find areas suitable for wetland restoration"` |

## Commands

### 1. `rtgs suitability run` — Interactive Pipeline

The main command. Prompts you for everything step by step.

```bash
rtgs suitability run
```

The pipeline walks through 7 steps:

```
Step 1  Study Area         →  You provide a boundary file path
Step 2  Analysis Units     →  Generate a grid (cell size + max cells) or load a file
Step 3  Datasets           →  You provide a path to a directory, .gdb, or file
Step 4  Requirements       →  Type your objective or point to a .txt file
Step 5  AI Model Design    →  Claude designs the model (structured outputs)
Step 6  Review             →  Accept, or save the YAML to edit manually
Step 7  Execute            →  Scores are calculated and results exported
```

**Output:** A results file (GeoParquet by default) and a model YAML in `./results/`.

**Options:**

```bash
rtgs suitability run --output-dir ./my_results
rtgs suitability run --output-format shapefile
rtgs suitability run --api-key sk-ant-...
```

### 2. `rtgs suitability run-config` — Non-interactive Pipeline

Runs from a YAML config file. Use this for reproducibility or after editing a model YAML from Step 6.

```bash
rtgs suitability run-config --config pipeline_config.yaml
```

**Config file format:**

```yaml
study_area_path: ./data/boundary.shp
datasets_path: ./data/variables/
model_spec_path: ./results/my_model.yaml
output_dir: ./results
output_format: geoparquet

grid:
  cell_size: 200
  max_cells: 50000
```

To use a pre-built analysis units file instead of a grid:

```yaml
# analysis_units_path: ./data/parcels.shp   # instead of grid:
```

**Options:**

```bash
rtgs suitability run-config -c config.yaml --output-dir ./v2_results
rtgs suitability run-config -c config.yaml --output-format geojson
```

### 3. `rtgs suitability validate` — Validate a Model YAML

Check that a model file is valid without executing it.

```bash
rtgs suitability validate model.yaml
```

Checks: YAML syntax, Pydantic types, weights sum to 100, scoring function params.

## End-to-End Example

### Prepare your data

```
my_project/
├── boundary.shp          # study area polygon
├── datasets/
│   ├── wetlands.shp      # variable dataset
│   ├── land_cover.gpkg   # variable dataset
│   └── streams.parquet   # variable dataset
└── requirements.txt      # plain-text objective
```

`requirements.txt`:
```
Find areas suitable for wetland restoration. Prioritize proximity to existing
wetlands, areas with appropriate land cover (grassland, agriculture), and
distance from streams for hydrological connectivity.
```

### Run interactively

```bash
cd my_project
rtgs suitability run
```

```
=== Step 1: Study Area ===
Path to study area boundary file: boundary.shp
  Loaded 1 features, CRS: EPSG:4326

=== Step 2: Analysis Units ===
Generate a regular grid? [Y/n]: y
Grid cell size in meters [100]: 200
Maximum number of cells [50000]: 50000
  Generated grid: 12,400 cells

=== Step 3: Variable Datasets ===
Path to datasets (directory, .gdb, or file): datasets/
  Loaded 3 datasets:
    - wetlands: 230 features
    - land_cover: 15,400 features
    - streams: 1,200 features

=== Step 4: Requirements ===
Type objective OR path to .txt file: requirements.txt
  Read requirements from: requirements.txt

=== Step 5: AI Model Design ===
Calling Claude AI...
  Model designed in 3.1 seconds

  Model: wetland_restoration_suitability
  Objective: Find areas suitable for wetland restoration
  Criteria:
    1. Wetland Proximity (40%) - distance_decay
    2. Land Cover Suitability (35%) - categorical
    3. Stream Connectivity (25%) - distance_decay

=== Step 6: Review ===
Accept this model? [Y/n]: y

=== Step 7: Executing ===
  Done in 8.4 seconds

=== Results ===
Output: ./results/wetland_restoration_suitability_results.parquet
Model:  ./results/wetland_restoration_suitability.yaml
```

### Edit and re-run

If you rejected the model at Step 6, or want to tweak weights/params after seeing results:

1. Open the saved YAML (`./results/wetland_restoration_suitability.yaml`)
2. Edit weights, scoring params, add/remove criteria
3. Create a config file:

```yaml
# pipeline_config.yaml
study_area_path: boundary.shp
datasets_path: datasets/
model_spec_path: ./results/wetland_restoration_suitability.yaml
output_dir: ./results_v2
output_format: geoparquet
grid:
  cell_size: 200
  max_cells: 50000
```

4. Re-run:

```bash
rtgs suitability run-config --config pipeline_config.yaml
```

## Quick Reference

| Task | Command |
|------|---------|
| Run full pipeline interactively | `rtgs suitability run` |
| Re-run from config file | `rtgs suitability run-config -c config.yaml` |
| Validate a model YAML | `rtgs suitability validate model.yaml` |
| List spatial_data registry datasets | `rtgs spatial-data list-datasets` |
| Extract a registry dataset to file | `rtgs spatial-data extract --dataset wildlife_areas -o ./data` |
