# Suitability Modeling Pipeline Redesign

**Status:** Concept / Draft
**Date:** 2025-02-10

## Problem

The current `suitability_modeling` module maintains its own dataset registry that duplicates and bridges `spatial_data`'s registry. It has hardcoded dataset assumptions (MN Geospatial, Hennepin County FGDB) baked into the model design and execution phases. This creates tight coupling, limits flexibility, and means users can only work with pre-cataloged datasets.

## Goal

Redesign the pipeline so that `suitability_modeling` has **zero internal datasets**. It only works with what users provide, and all data ingestion flows through `spatial_data`'s ETL pipeline.

## Proposed CLI Workflow

The pipeline runs as an interactive CLI tool with three input stages followed by ETL and analysis.

### Stage 1: Study Area

Prompt the user for a **file path** to the study area boundary dataset.

- Supported formats: Shapefile, GeoPackage, GeoParquet, GeoJSON, zipped shapefile
- Must contain polygon/multipolygon geometry defining the analysis boundary
- Example: a county boundary, watershed outline, or custom AOI

### Stage 2: Analysis Units

Prompt the user for the spatial units over which suitability scores are calculated. Two options:

**Option A — User-provided dataset:**
A file path to a dataset containing discrete spatial units (parcels, cities, counties, census tracts, etc.)

**Option B — Generated grid:**
If the user doesn't have a unit dataset, offer to generate a regular grid covering the study area. Prompt for cell size (default: 100m x 100m). Grid generation is handled by the `spatial_data` module as part of the ETL pipeline.

### Stage 3: Suitability Variable Datasets

Prompt the user for input datasets to use as variables/criteria in the suitability analysis. Accepted inputs:

- **File Geodatabase (FGDB)** path — all layers extracted as separate datasets
- **Zipped folder** path — extract and discover spatial files inside
- **Directory** path — discover all spatial files in the directory

Each discovered dataset becomes an available variable for the suitability model.

### Stage 4: ETL via `spatial_data`

All three categories of input (study area, analysis units, variable datasets) are run through the `spatial_data` module's ETL pipeline:

1. **Extract** — Read from source format
2. **Load** — Into standardized GeoDataFrames
3. **Transform** — Validate geometry, standardize CRS (EPSG:4326), check completeness
4. If the user requested a generated grid, `spatial_data` creates it from the study area boundary at this stage

No intermediate caching — validated GeoDataFrames are held in memory and passed directly to the modeling stage.

### Stage 5: Model Design (via Claude AI with Structured Outputs)

With the validated datasets in hand:

1. Present a minimal summary of available variable datasets to Claude (dataset names, geometry types, and column names only — bare minimum for the LLM call)
2. Along with the user's natural language requirements/objective
3. Claude designs a weighted overlay model selecting from the available variables
4. The API call uses **structured outputs** (`output_config.format`) to hard-constrain Claude's response to exactly match the `ModelSpecification` schema — no freeform JSON parsing needed
5. Output: a ModelSpecification (YAML) for review/editing
6. The CLI presents the generated spec to the user for interactive review and editing before proceeding to execution

#### Structured Output Enforcement

The `ModelSpecification` class (in `model_specification.py`) is the single source of truth for the output schema. Rather than prompting Claude to "return only valid JSON" and hoping for the best, we use the Anthropic API's structured outputs feature:

- Convert `ModelSpecification` and its nested dataclasses (`ScoringFunction`, `ModelCriterion`, `StudyAreaConfig`, `AnalysisUnitsConfig`) to **Pydantic models**
- Use `client.messages.parse(output_format=ModelSpecification)` which:
  - Automatically derives a JSON schema from the Pydantic model
  - Enforces the schema via constrained decoding at the API level
  - Returns a validated `response.parsed_output` object directly
- This eliminates the brittle `_extract_json()` parsing and "return ONLY valid JSON" prompt hacks in the current `claude_client.py`
- No separate template.yaml file is needed — the Python class IS the template

### Stage 6: Model Execution

Execute the model specification against the validated data:

1. Load analysis units (user-provided or generated grid)
2. For each criterion, score against the corresponding variable dataset
3. Combine scores using weighted overlay
4. Export results

## Architecture Changes

### Remove from `suitability_modeling`

- `core/dataset_registry.py` — no longer needed; datasets come from user input
- Hardcoded dataset dictionaries and FGDB references
- Any direct data loading logic (all goes through `spatial_data`)

### Enhance in `spatial_data`

- Ensure `LocalFileExtractor` handles FGDB layer discovery, zip extraction, and directory scanning robustly
- Add a batch extraction mode: given a directory/FGDB, extract all layers and return a dict of validated GeoDataFrames
- Add grid generation as a utility within the ETL pipeline (given a study area boundary and cell size, produce analysis unit GeoDataFrame)
- Add a minimal schema introspection function (dataset name, geometry type, column names) for LLM consumption

### Refactor in `suitability_modeling`

- Convert `ModelSpecification` and nested dataclasses to Pydantic models (required for structured outputs)
- Replace freeform JSON prompting in `claude_client.py` with `client.messages.parse(output_format=ModelSpecification)`
- Remove `_extract_json()` and markdown-stripping hacks

### New in `suitability_modeling`

- Interactive CLI flow (Click-based prompts for the three input stages)
- Updated model designer prompt that includes actual column names from the validated data (minimal metadata only)
- Interactive review/edit step after Claude generates the model spec, before execution
- Non-interactive config-file mode: accept a YAML config with all file paths and parameters for scripted/reproducible runs

## Modes of Operation

### Interactive Mode (default)

The CLI walks the user through each stage with prompts, previews, and the model review/edit step.

### Non-Interactive Mode (config file)

A YAML config file provides all inputs upfront for scripted or reproducible runs:

```yaml
study_area: /path/to/boundary.shp
analysis_units:
  type: file  # or "grid"
  path: /path/to/parcels.gpkg  # if type: file
  cell_size: 100  # if type: grid
variables:
  path: /path/to/datasets/  # directory, FGDB, or zip
requirements: /path/to/requirements.txt
output:
  directory: ./results
  format: geoparquet
```

## Data Flow Diagram

```
User Input (CLI prompts or config file)
  |
  |-- 1. Study area file path
  |-- 2. Analysis units file path (or grid config)
  |-- 3. Variables: FGDB path / zip path / directory path
  |
  v
spatial_data ETL Pipeline
  |-- Extract from source formats
  |-- Validate geometry
  |-- Standardize CRS
  |-- Generate grid (if requested)
  |-- Return validated GeoDataFrames + minimal schemas
  |
  v
suitability_modeling
  |-- Present datasets + minimal metadata to Claude AI
  |-- Claude designs weighted overlay model
  |-- User reviews/edits YAML specification
  |-- Execute model against validated data
  |-- Export scored results
  |
  v
Output (GeoParquet / Shapefile / GeoJSON)
```
