# Suitability Modeling Module - Development Notes

**Last Updated**: 2026-02-12
**Branch**: `ben/etl-pipeline-v0`

---

## Recent Development Progress

### 2026-02-12 - CLI Hardening & Scoring Improvements (v0.2.1)

End-to-end testing of the `rtgs suitability run` pipeline against real Hennepin County data (county boundary shapefile, CTU analysis units, FGDB variable datasets). This session fixed API integration issues, improved the CLI for cross-platform use, and added a new scoring function.

#### Test Configuration

- **Study area**: Hennepin County boundary (shapefile, 1 feature)
- **Analysis units**: 46 CTUs within Hennepin County (shapefile, pre-built polygons — no grid generation)
- **Variable datasets**: 4 layers extracted from `HC_EasementAnalysis_Model_Inputs_2020.gdb` — `protected_areas`, `natural_spaces`, `important_bird_areas`, `MBS`
- **Requirements**: Natural resource conservation suitability based on proximity to protected areas/natural spaces/bird areas and MBS biodiversity significance scores

#### API Integration Fixes

The Claude structured outputs integration (`output_config.format` with `json_schema`) required multiple fixes to work with the Anthropic API:

1. **Schema nesting**: `name` and `schema` needed to be direct children of `format`, not nested inside a `json_schema` wrapper
2. **`additionalProperties`**: The API requires `"additionalProperties": false` on every object type. Added `_add_additional_properties_false()` recursive post-processor to the schema
3. **Tuple constraints**: Pydantic generates `minItems`/`maxItems` > 1 for `Tuple[float, float]` fields (`output_range`). The API only supports `minItems` of 0 or 1. Added stripping of unsupported array constraints and conversion of `prefixItems` to `items`
4. **Freeform dicts**: `Dict[str, Any]` fields (`params`, `metadata`) generate `{"type": "object"}` without `properties`, which the API rejects. Fixed by:
   - Replacing `params: Dict[str, Any]` with a concrete `ScoringParams` Pydantic model
   - Stripping `metadata` from the schema before sending (it has a default and Claude doesn't need to generate it)
5. **Model compatibility**: `claude-sonnet-4-20250514` does not support `output_config` structured outputs. Switched to **tool-use pattern**: define a tool with `input_schema` matching the Pydantic JSON schema and force it via `tool_choice`. This works on all Claude models and provides equivalent schema enforcement
6. **`name` field rejected**: After fixing the schema, the `name` field inside `format` was rejected as an extra input. Removed it — only `type` and `schema` are needed

**Final working API call pattern:**
```python
response = self.client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4000,
    messages=[{"role": "user", "content": prompt}],
    tools=[{
        "name": "design_model",
        "description": "Output the complete suitability model specification",
        "input_schema": json_schema,
    }],
    tool_choice={"type": "tool", "name": "design_model"},
)
tool_use_block = next(b for b in response.content if b.type == "tool_use")
model_spec_dict = tool_use_block.input
```

#### Model Specification Changes

**New `ScoringParams` model** (`core/model_specification.py`):

Replaced `params: Dict[str, Any]` on `ScoringFunction` with a concrete Pydantic model:

```python
class CategoryMapping(BaseModel):
    category: str
    score: float

class ScoringParams(BaseModel):
    max_distance: Optional[float]   # distance_decay
    decay_rate: Optional[float]     # distance_decay
    column: Optional[str]           # categorical / direct_value
    category_mappings: Optional[List[CategoryMapping]]  # categorical
```

Key design decisions:
- **`get()` method** provides dict-like access (`params.get("max_distance", 2000)`) for backward compatibility with the execution engine — no changes needed there
- **`convert_mapping_dict` validator** (`mode="before"`) converts legacy `{"mapping": {"High": 10}}` dict format to `category_mappings` list, so old YAML files still load correctly
- **`metadata`** field changed to `Optional[Dict[str, Any]]` with `default=None` and stripped from the API schema (Claude doesn't generate it)

#### New Scoring Function: `direct_value`

Added a third scoring function type to handle datasets with pre-computed numeric scores.

**Problem**: The FGDB datasets are pre-computed analysis layers with score columns (`Bio_Sig_Sc` with values 1-4, `Recharge_Score`, etc.). The `categorical` scorer requires mapping each value through a lookup, which is unnecessary and error-prone — Claude was guessing category names ("Outstanding", "High") instead of using the actual numeric values.

**Solution**: `direct_value` reads a numeric column value directly via spatial join, no remapping:

```python
def _score_direct_value(self, study_area, features, scoring_func):
    column = params.get("column")
    joined = gpd.sjoin(study_area, features, how="left", predicate="intersects")
    scores = pd.to_numeric(joined[column], errors="coerce").fillna(0)
    scores = scores.groupby(scores.index).max().reindex(study_area.index, fill_value=0)
    return np.asarray(scores)
```

Updated the prompt to describe all three scoring functions and instruct Claude to prefer `direct_value` when columns already contain numeric scores.

#### Schema Enrichment: Sample Values

`get_dataset_schema()` (`spatial_data/core/schema.py`) now includes unique values for columns with ≤20 distinct values. This gives Claude visibility into actual data content:

Before: `columns [Bio_Sig_Sc, biodiv_sig, site_name, ...]`
After: `columns [Bio_Sig_Sc (values: [1, 2, 3, 4]), biodiv_sig (values: [Below, High, Moderate, Outstanding]), ...]`

This prevents Claude from guessing category values and enables informed decisions about scoring function type.

#### CLI Improvements

**Cross-platform path handling** (`cli.py`):

Added `_normalize_path()` applied to all 4+ path prompts:
- Converts MINGW64/Git Bash paths (`/c/Users/...`) to Windows paths (`C:\Users\...`) on Windows
- Strips surrounding quotes from pasted paths (Windows Explorer copy)
- Strips leading/trailing whitespace

**New Step 1 — Output Options**:

Moved output format and directory prompts to the beginning of the pipeline so users set these upfront:

```
=== Step 1: Output Options ===
Output format (geoparquet, shapefile, geojson, csv): shapefile
Output directory: C:\Users\...\results
```

**Identifier column prompt**:

After loading analysis units (non-grid), the CLI lists available columns and asks which one to keep as an identifier:

```
  Loaded 46 analysis units
  Columns: CTU_NAME, COUNTY, Shape_Area, ...
Identifier column for output (or 'none' to skip):
```

No default value — the user must explicitly choose.

**Clean output data**:

The output GeoDataFrame is stripped to only: identifier column (if chosen) + geometry + suitability_score + individual score columns. All original attribute columns from the analysis units are dropped.

**Score column naming**:

Changed from verbose criterion names to dataset names:
- Before: `score_proximity_to_protected_areas` (truncated to `score_prox` in shapefile)
- After: `score_protected_areas`, `score_natural_spaces`, `score_important_bird_areas`, `score_MBS`

**Updated interactive pipeline flow:**
```
Step 1: Output Options → format + directory
Step 2: Study Area     → Path to boundary file
Step 3: Analysis Units → Generate grid or load file + identifier column
Step 4: Datasets       → Path to directory, .gdb, or file
Step 5: Requirements   → Type objective or path to .txt
Step 6: AI Design      → Claude designs model (tool-use structured outputs)
Step 7: Review         → Accept or save YAML for editing
Step 8: Execute        → Score criteria, combine weights, export
```

#### File Changes (v0.2.1)

**Modified:**
- `suitability_modeling/cli.py` — path normalization, output options step, identifier column prompt, step renumbering
- `suitability_modeling/llm/claude_client.py` — tool-use pattern, schema post-processing, `direct_value` in prompt, sample values in dataset info
- `suitability_modeling/core/model_specification.py` — `CategoryMapping`, `ScoringParams` models, `metadata` made optional
- `suitability_modeling/core/model_designer.py` — `print_model_summary` updated for `ScoringParams` and `direct_value`
- `suitability_modeling/core/execution_engine.py` — `direct_value` scoring, `id_column` support, dataset-name score columns, clean output
- `spatial_data/core/schema.py` — unique values included in column schema for LLM consumption

---

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
