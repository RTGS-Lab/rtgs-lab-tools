# Suitability Modeling Module - Development Notes

**Last Updated**: 2026-02-11
**Branch**: `ben/etl-pipeline-v0`

---

## Recent Development Progress

### 2026-02-11 - Pipeline Refactor v0.2.0

Major refactor of the suitability modeling pipeline. The module previously maintained its own dataset registry (duplicating `spatial_data`'s), had hardcoded Hennepin County/MN assumptions, and used brittle freeform JSON parsing for Claude responses. This refactor converts it into a clean, linear CLI pipeline where users provide their own data via file paths.

See `docs/pipeline_redesign.md` for the full design document.

#### What Changed

**ModelSpecification — Pydantic rewrite** (`core/model_specification.py`)

Converted all 5 dataclasses (`ScoringFunction`, `ModelCriterion`, `StudyAreaConfig`, `AnalysisUnitsConfig`, `ModelSpecification`) to Pydantic `BaseModel` subclasses.

Key changes:
- Every field has `Field(description=...)` — these descriptions feed into the JSON schema used by Claude structured outputs
- `@model_validator(mode="after")` validates that criteria weights sum to 100
- `to_dict()` delegates to `model_dump()`
- `from_dict()` delegates to `model_validate()`
- `to_yaml()` uses `model_dump(mode="json")` to avoid Python tuple tags in YAML
- `model_json_schema()` generates the schema used by the Claude API
- Attribute access is unchanged — no impact on consuming code
- Removed hardcoded "Hennepin County" defaults

**ClaudeClient — Structured outputs** (`llm/claude_client.py`)

Full rewrite:
- `design_model()` now accepts `dataset_schemas: List[Dict]` (from `get_dataset_schema()`) instead of registry dataset names
- Uses `output_config.format` with JSON schema from `ModelSpecification.model_json_schema()` — Claude's response is hard-constrained to the schema
- Response is parsed with `json.loads()` + `ModelSpecification.model_validate()` — no more `_extract_json()` hack
- Prompt includes dataset metadata (name, geometry type, columns, feature count)

**Model Designer** (`core/model_designer.py`)

Simplified:
- `design_model(requirements, dataset_schemas, ...)` accepts text + schema dicts directly
- No file reading, no registry imports
- `print_model_summary(spec)` returns a string (CLI handles display) instead of printing directly

**Execution Engine** (`core/execution_engine.py`)

Refactored to accept pre-loaded data:
- `execute_model()` takes `datasets: Dict[str, GeoDataFrame]`, `study_area_boundary`, and optional `analysis_units` directly
- `SuitabilityEngine.__init__` takes the same pre-loaded data
- Removed `_load_dataset()`, `_load_datasets()`, `_load_study_area_boundary()` — data comes pre-loaded from the CLI
- Removed `_get_temp_dir()`, `_cleanup_temp_dir()` — no temp files needed
- Grid fallback calls `spatial_data.generate_grid()` instead of inline grid code
- Fixed categorical scoring to handle duplicate rows from `gpd.sjoin()` by grouping by index
- Model YAML is saved alongside results automatically

**Dataset Registry — Deleted** (`core/dataset_registry.py`)

This file was a thin wrapper around `spatial_data`'s registry. With the new pipeline, data comes from user-provided file paths routed through `spatial_data`'s extractors. The registry indirection is no longer needed.

**CLI — Full rewrite** (`cli.py`)

New commands:

| Command | Description |
|---------|-------------|
| `rtgs suitability run` | Interactive 7-step pipeline: study area, analysis units, datasets, requirements, AI design, review, execute |
| `rtgs suitability run-config --config file.yaml` | Non-interactive run from a YAML config file with all paths/params |
| `rtgs suitability validate model.yaml` | Pydantic validation only — checks YAML structure, weights, types |

Removed commands:
- `list-datasets` — no internal registry to list
- `design` — design is now part of `run`
- `execute` — execution is now part of `run` (or `run-config`)

Interactive pipeline flow:
```
Step 1: Study Area     → Path to boundary file
Step 2: Analysis Units → Generate grid or load file
Step 3: Datasets       → Path to directory, .gdb, or file
Step 4: Requirements   → Type objective or path to .txt
Step 5: AI Design      → Claude designs model (structured outputs)
Step 6: Review         → Accept or save YAML for editing
Step 7: Execute        → Score criteria, combine weights, export
```

**Module exports** (`__init__.py`)

Updated to v0.2.0. Added lazy imports for `print_model_summary`, `ModelSpecification`, `ScoringFunction`, `ModelCriterion`, `StudyAreaConfig`, `AnalysisUnitsConfig`.

#### Data Flow (Before vs After)

**Before:**
```
User → requirements.txt → model_designer → dataset_registry → spatial_data registry → extract_spatial_data → temp files → execution_engine → results
```

**After:**
```
User → file paths (CLI prompts) → spatial_data extractors → GeoDataFrames in memory → model_designer (schemas) → execution_engine (pre-loaded data) → results
```

#### Tests

New test files in `tests/suitability_modeling/`:
- `test_model_specification.py` — 12 tests: Pydantic creation, dict roundtrip, YAML roundtrip, validation (valid, bad weights, no criteria), JSON schema generation
- `test_execution_engine.py` — 5 tests: distance_decay scoring, categorical scoring, individual score columns, full execution, export formats

All 17 tests pass.

#### Bug Fixes During Refactor

1. **YAML tuple serialization**: `model_dump(mode="python")` preserved Python tuples, but `yaml.safe_load()` can't deserialize the `!!python/tuple` tag. Fixed by using `model_dump(mode="json")` which converts tuples to lists.

2. **Categorical scoring length mismatch**: `gpd.sjoin()` with `how="left"` produces duplicate rows when an analysis unit overlaps multiple features. The resulting score array was longer than the study area. Fixed by grouping by index and taking the max score per unit.

---

## Architecture Notes

### Why Pydantic for ModelSpecification?

1. **Structured outputs**: Anthropic's API can constrain Claude's JSON output to match a JSON schema. Pydantic generates this schema via `model_json_schema()`.
2. **Validation**: `@model_validator` and `Field(ge=0, le=100)` catch invalid models at parse time.
3. **Serialization**: `model_dump()` / `model_validate()` replace manual `to_dict()` / `from_dict()` logic.
4. **Descriptions**: `Field(description=...)` serves double duty — documents the code and feeds into the JSON schema that Claude sees.

### Why Pre-loaded Data?

The old pipeline extracted data to temp files and re-read them. The new pipeline keeps GeoDataFrames in memory:
- Faster — no disk I/O round-trip
- Simpler — no temp dir management
- Cleaner — the execution engine doesn't need to know about data sources
- Testable — tests pass in mock GeoDataFrames directly

### CLI Design Philosophy

The interactive `run` command follows a linear prompt flow — no menus, no back-navigation, no configuration files required. Each step validates its input before moving on. If the user rejects the model at Step 6, the YAML is saved so they can edit and re-run via `run-config`.

---

## File Change Summary (v0.2.0)

**Created:**
- `spatial_data/core/grid.py`
- `spatial_data/core/schema.py`
- `suitability_modeling/docs/dev-notes.md`
- `tests/spatial_data/__init__.py`, `test_extractor.py`, `test_grid.py`, `test_schema.py`
- `tests/suitability_modeling/__init__.py`, `test_model_specification.py`, `test_execution_engine.py`

**Modified:**
- `pyproject.toml` — added pydantic, anthropic
- `spatial_data/core/extractor.py` — added `extract_from_path()`
- `spatial_data/sources/fgdb.py` — `fgdb_path` param + `extract_all_fgdb_layers()`
- `spatial_data/sources/local_file.py` — `extract_all_from_directory()`
- `spatial_data/__init__.py`, `sources/__init__.py` — new exports
- `suitability_modeling/core/model_specification.py` — Pydantic rewrite
- `suitability_modeling/llm/claude_client.py` — structured outputs
- `suitability_modeling/core/model_designer.py` — simplified API
- `suitability_modeling/core/execution_engine.py` — pre-loaded data
- `suitability_modeling/cli.py` — full rewrite
- `suitability_modeling/__init__.py` — updated exports

**Deleted:**
- `suitability_modeling/core/dataset_registry.py`
