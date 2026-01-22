# Suitability Modeling Module - Architecture Design

**Status:** Planning Phase
**Branch:** TBD
**Purpose:** AI-powered suitability analysis model builder and executor

---

## Executive Summary

The `suitability_modeling` module is an AI-powered spatial analysis framework that enables users to define suitability analyses in natural language, which are then automatically translated into executable spatial models using LLM interpretation and the existing `spatial_data` infrastructure.

### Core Capabilities

1. **Natural Language Input** - Accept text descriptions of suitability analyses
2. **LLM-Powered Interpretation** - Use Claude to parse requirements and design models
3. **Automated Model Design** - Generate complete suitability model specifications
4. **Dataset Integration** - Leverage vetted datasets from `spatial_data` module
5. **Model Execution** - Run designed models and produce results
6. **Flexible Output** - Export results in GeoParquet, Shapefile, GeoJSON, CSV

---

## Architecture Overview

### High-Level Data Flow

```
┌─────────────────────┐
│  User Input File    │
│  (Natural Language) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Requirement Parser │ ← Parse text file
│  (LLM Integration)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Model Designer    │ ← Claude interprets requirements
│   (LLM-Powered)     │ ← Generates model specification
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Dataset Matcher    │ ← Maps requirements to spatial_data datasets
│  (Registry Lookup)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Model Specification │ ← JSON/YAML model definition
│  (Validation)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Execution Engine   │ ← Loads datasets via spatial_data
│  (GeoPandas-based)  │ ← Applies scoring/weighting
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Results Exporter   │ ← GeoParquet/Shapefile/GeoJSON/CSV
│  (Multi-format)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Database Logger   │ ← PostgreSQL audit trail
│   (PostgreSQL)      │
└─────────────────────┘
```

---

## Module Structure

```
suitability_modeling/
├── __init__.py                      # Lazy loading interface
├── README.md                        # User documentation
├── ARCHITECTURE.md                  # This file
├── cli.py                           # CLI commands
├── db_schema.sql                    # PostgreSQL schema for model catalog
├── db_logger.py                     # Database integration
├── core/
│   ├── __init__.py
│   ├── requirement_parser.py       # Parse input text files
│   ├── model_designer.py           # LLM-powered model design
│   ├── dataset_matcher.py          # Match requirements to spatial_data
│   ├── model_specification.py      # Model spec data structures
│   ├── execution_engine.py         # Execute suitability models
│   └── results_exporter.py         # Export results to files
├── llm/
│   ├── __init__.py
│   ├── claude_client.py            # Claude API integration
│   ├── prompts.py                  # LLM prompt templates
│   └── response_parser.py          # Parse LLM responses
├── models/
│   ├── __init__.py
│   ├── base.py                     # BaseSuitabilityModel class
│   ├── weighted_overlay.py         # Weighted overlay model
│   ├── boolean_overlay.py          # Boolean/constraint-based model
│   └── fuzzy_logic.py             # Fuzzy logic model (future)
├── registry/
│   ├── __init__.py
│   ├── model_registry.py           # Saved model catalog
│   └── templates/                  # Pre-built model templates
│       ├── wildlife_habitat.yaml
│       ├── urban_development.yaml
│       └── conservation_priority.yaml
└── docs/
    ├── user_guide.md
    ├── model_specification_schema.md
    └── examples/
        ├── wildlife_corridor_analysis.txt
        ├── solar_farm_siting.txt
        └── wetland_restoration.txt
```

---

## Core Components

### 1. Requirement Parser (`core/requirement_parser.py`)

**Purpose:** Parse user input text file and extract key information.

**Input:** Text file describing suitability analysis
**Output:** Structured requirements object

```python
class RequirementParser:
    """Parse natural language suitability analysis requirements."""

    def parse(self, input_file: str) -> Dict[str, Any]:
        """Parse input file and extract requirements.

        Returns:
            {
                "objective": "Find suitable locations for wildlife corridors",
                "constraints": ["Must connect existing protected areas"],
                "criteria": ["Minimize human disturbance", "Maximize habitat quality"],
                "study_area": "Hennepin County, Minnesota",
                "output_format": "geoparquet"
            }
        """
        pass
```

---

### 2. LLM Integration (`llm/claude_client.py`)

**Purpose:** Interface with Claude API to interpret requirements and design models.

```python
class ClaudeModelDesigner:
    """Use Claude to design suitability models from requirements."""

    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def design_model(self, requirements: Dict[str, Any]) -> ModelSpecification:
        """Design a suitability model using Claude.

        Sends requirements to Claude with context about:
        - Available spatial datasets (from spatial_data registry)
        - Suitability modeling methods (weighted overlay, boolean, etc.)
        - Best practices for spatial analysis

        Returns:
            ModelSpecification object with:
            - Model type (weighted overlay, boolean, etc.)
            - Dataset selections
            - Scoring functions
            - Weighting scheme
            - Combination logic
        """
        pass
```

**Prompt Template:**

```python
DESIGN_PROMPT_TEMPLATE = """
You are a GIS expert designing a suitability analysis model.

User Requirements:
{requirements}

Available Datasets (from spatial_data module):
{available_datasets}

Task:
1. Analyze the user's requirements
2. Select appropriate datasets from the available list
3. Design scoring functions for each dataset (how to convert data to suitability scores 0-10)
4. Assign weights to each criterion (must sum to 100%)
5. Define combination method (weighted overlay, boolean constraints, etc.)

Return a JSON model specification following this schema:
{
  "model_type": "weighted_overlay",
  "objective": "...",
  "datasets": [
    {
      "name": "wildlife_areas",
      "criterion": "Protected area proximity",
      "scoring_function": {
        "type": "distance_decay",
        "max_distance": 1000,
        "units": "meters"
      },
      "weight": 30
    }
  ],
  "constraints": [
    {
      "dataset": "land_use",
      "filter": "land_use_type NOT IN ['Urban', 'Industrial']"
    }
  ],
  "output_range": [0, 100]
}
"""
```

---

### 3. Dataset Matcher (`core/dataset_matcher.py`)

**Purpose:** Match model requirements to available datasets from `spatial_data`.

```python
class DatasetMatcher:
    """Match suitability requirements to available spatial datasets."""

    def __init__(self):
        from ..spatial_data.registry import list_available_datasets
        self.available_datasets = list_available_datasets()

    def find_relevant_datasets(self, requirements: Dict[str, Any]) -> List[str]:
        """Find spatial_data datasets relevant to requirements.

        Uses keyword matching, semantic similarity, and LLM assistance.
        """
        pass

    def validate_dataset_selection(self, dataset_names: List[str]) -> bool:
        """Ensure all selected datasets exist and are accessible."""
        pass
```

---

### 4. Model Specification (`core/model_specification.py`)

**Purpose:** Define the data structure for suitability models.

```python
@dataclass
class ScoringFunction:
    """How to convert dataset values to suitability scores."""
    type: str  # "linear", "distance_decay", "categorical", "threshold"
    params: Dict[str, Any]
    output_range: Tuple[float, float] = (0, 10)

@dataclass
class ModelCriterion:
    """Single criterion in suitability model."""
    dataset_name: str
    criterion_name: str
    scoring_function: ScoringFunction
    weight: float  # 0-100
    preprocessing: Optional[Dict[str, Any]] = None

@dataclass
class ModelConstraint:
    """Hard constraint that must be satisfied."""
    dataset_name: str
    constraint_type: str  # "filter", "mask", "buffer"
    params: Dict[str, Any]

@dataclass
class ModelSpecification:
    """Complete suitability model specification."""
    model_id: str
    model_type: str  # "weighted_overlay", "boolean_overlay", "fuzzy_logic"
    objective: str
    study_area: Optional[str] = None
    criteria: List[ModelCriterion] = field(default_factory=list)
    constraints: List[ModelConstraint] = field(default_factory=list)
    combination_method: str = "weighted_sum"
    output_range: Tuple[float, float] = (0, 100)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate model specification."""
        # Check weights sum to 100
        total_weight = sum(c.weight for c in self.criteria)
        if not (99.9 <= total_weight <= 100.1):
            raise ValueError(f"Weights must sum to 100, got {total_weight}")

        # Check all datasets exist
        # etc.
        return True

    def to_yaml(self, file_path: str):
        """Save model specification to YAML file."""
        pass

    @classmethod
    def from_yaml(cls, file_path: str) -> "ModelSpecification":
        """Load model specification from YAML file."""
        pass
```

---

### 5. Execution Engine (`core/execution_engine.py`)

**Purpose:** Execute suitability models on spatial data.

```python
class SuitabilityEngine:
    """Execute suitability analysis models."""

    def __init__(self, model_spec: ModelSpecification):
        self.model_spec = model_spec
        self.datasets = {}

    def load_datasets(self):
        """Load all required datasets using spatial_data module."""
        from ..spatial_data import extract_spatial_data

        for criterion in self.model_spec.criteria:
            dataset_name = criterion.dataset_name
            if dataset_name not in self.datasets:
                # Extract dataset (returns GeoDataFrame)
                result = extract_spatial_data(
                    dataset_name=dataset_name,
                    note=f"Loading for suitability model: {self.model_spec.model_id}"
                )
                # Load the GeoDataFrame
                self.datasets[dataset_name] = gpd.read_parquet(result['output_file'])

    def apply_scoring_function(
        self,
        gdf: gpd.GeoDataFrame,
        scoring_func: ScoringFunction
    ) -> np.ndarray:
        """Apply scoring function to convert data to suitability scores.

        Types:
        - "linear": Linear rescaling
        - "distance_decay": Exponential decay with distance
        - "categorical": Map categories to scores
        - "threshold": Binary threshold
        - "gaussian": Gaussian membership function
        """
        if scoring_func.type == "linear":
            # Linear rescaling from input range to output range
            pass
        elif scoring_func.type == "distance_decay":
            # Calculate distance, apply decay function
            pass
        elif scoring_func.type == "categorical":
            # Map categories to scores
            pass
        # etc.
        return scores

    def apply_constraints(self, study_area_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Apply hard constraints to filter study area."""
        for constraint in self.model_spec.constraints:
            # Apply each constraint
            pass
        return filtered_gdf

    def execute(self, study_area: Optional[gpd.GeoDataFrame] = None) -> gpd.GeoDataFrame:
        """Execute the suitability model.

        Returns:
            GeoDataFrame with suitability scores added
        """
        self.load_datasets()

        # 1. Define study area
        if study_area is None:
            study_area = self._create_study_area_grid()

        # 2. Apply constraints
        study_area = self.apply_constraints(study_area)

        # 3. Calculate scores for each criterion
        criterion_scores = {}
        for criterion in self.model_spec.criteria:
            scores = self._calculate_criterion_score(study_area, criterion)
            criterion_scores[criterion.criterion_name] = scores

        # 4. Combine scores (weighted overlay)
        final_scores = self._combine_scores(criterion_scores)

        # 5. Add to study area GeoDataFrame
        study_area['suitability_score'] = final_scores

        return study_area

    def _create_study_area_grid(self, cell_size: float = 100) -> gpd.GeoDataFrame:
        """Create a grid of analysis cells."""
        # Create regular grid based on datasets' extent
        pass

    def _calculate_criterion_score(
        self,
        study_area: gpd.GeoDataFrame,
        criterion: ModelCriterion
    ) -> np.ndarray:
        """Calculate suitability score for a single criterion."""
        dataset = self.datasets[criterion.dataset_name]

        # Spatial operation (e.g., distance to features, overlay, etc.)
        # Then apply scoring function
        scores = self.apply_scoring_function(dataset, criterion.scoring_function)

        return scores

    def _combine_scores(self, criterion_scores: Dict[str, np.ndarray]) -> np.ndarray:
        """Combine criterion scores using weighted sum."""
        final_scores = np.zeros(len(next(iter(criterion_scores.values()))))

        for criterion in self.model_spec.criteria:
            scores = criterion_scores[criterion.criterion_name]
            weight = criterion.weight / 100.0
            final_scores += scores * weight

        return final_scores
```

---

### 6. CLI Interface (`cli.py`)

**Purpose:** Command-line interface for suitability modeling.

```python
@click.group()
def suitability_cli():
    """Suitability analysis model builder and executor."""
    pass

@suitability_cli.command()
@click.option('--input', required=True, help='Input text file with requirements')
@click.option('--output-spec', default=None, help='Output YAML file for model spec')
@click.option('--auto-execute', is_flag=True, help='Automatically execute after design')
def design(input, output_spec, auto_execute):
    """Design a suitability model from natural language requirements.

    Example:
        rtgs suitability design --input requirements.txt --output-spec model.yaml
    """
    # 1. Parse requirements
    parser = RequirementParser()
    requirements = parser.parse(input)

    # 2. Design model using Claude
    designer = ClaudeModelDesigner()
    model_spec = designer.design_model(requirements)

    # 3. Validate model
    model_spec.validate()

    # 4. Save model specification
    if output_spec:
        model_spec.to_yaml(output_spec)
        click.echo(f"Model specification saved to: {output_spec}")

    # 5. Auto-execute if requested
    if auto_execute:
        # Execute the model
        pass

@suitability_cli.command()
@click.option('--model-spec', required=True, help='Model specification YAML file')
@click.option('--output-dir', default='./results', help='Output directory')
@click.option('--output-format', default='geoparquet',
              type=click.Choice(['geoparquet', 'shapefile', 'geojson', 'csv']))
def execute(model_spec, output_dir, output_format):
    """Execute a suitability model.

    Example:
        rtgs suitability execute --model-spec model.yaml --output-format geoparquet
    """
    # 1. Load model specification
    spec = ModelSpecification.from_yaml(model_spec)

    # 2. Execute model
    engine = SuitabilityEngine(spec)
    results = engine.execute()

    # 3. Export results
    exporter = ResultsExporter(results)
    output_file = exporter.export(output_dir, output_format)

    click.echo(f"Suitability analysis complete!")
    click.echo(f"Results saved to: {output_file}")

@suitability_cli.command()
def list_templates():
    """List available model templates."""
    # Show pre-built templates
    pass

@suitability_cli.command()
@click.argument('template_name')
@click.option('--output-spec', required=True, help='Output YAML file')
def use_template(template_name, output_spec):
    """Create a model from a template.

    Example:
        rtgs suitability use-template wildlife_corridor --output-spec my_model.yaml
    """
    # Load template and customize
    pass
```

---

## Database Schema

```sql
-- suitability_models table
CREATE TABLE IF NOT EXISTS suitability_models (
    id SERIAL PRIMARY KEY,
    model_id VARCHAR(100) NOT NULL UNIQUE,
    model_name VARCHAR(200),
    model_type VARCHAR(50),  -- weighted_overlay, boolean_overlay, etc.
    objective TEXT,
    specification JSONB,     -- Full model spec as JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    version INTEGER DEFAULT 1
);

-- suitability_executions table
CREATE TABLE IF NOT EXISTS suitability_executions (
    id SERIAL PRIMARY KEY,
    model_id VARCHAR(100) NOT NULL,
    execution_start TIMESTAMP NOT NULL,
    execution_end TIMESTAMP NOT NULL,
    duration_seconds NUMERIC(10,3),
    success BOOLEAN NOT NULL,
    output_file TEXT,
    output_format VARCHAR(20),
    study_area_features INTEGER,
    datasets_used TEXT[],
    error_message TEXT,
    note TEXT,
    git_commit_hash VARCHAR(40),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_model FOREIGN KEY (model_id)
        REFERENCES suitability_models(model_id) ON DELETE CASCADE
);

-- llm_interactions table (for audit/debugging)
CREATE TABLE IF NOT EXISTS llm_interactions (
    id SERIAL PRIMARY KEY,
    model_id VARCHAR(100),
    interaction_type VARCHAR(50),  -- design, refine, validate
    prompt_text TEXT,
    response_text TEXT,
    tokens_used INTEGER,
    cost_usd NUMERIC(10,4),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Example User Input

**File:** `wildlife_corridor_analysis.txt`

```
Objective:
Identify suitable locations for wildlife corridors connecting existing protected areas in Hennepin County.

Requirements:
- Must connect DNR Wildlife Management Areas and Scientific & Natural Areas
- Prioritize areas with high habitat quality
- Minimize human disturbance (avoid urban areas, roads)
- Consider proximity to water resources
- Account for existing land use constraints

Constraints:
- Exclude urban and industrial areas
- Exclude areas within 100m of major roads
- Must be within 2km of existing protected areas

Output:
- Suitability scores from 0-100
- Export as GeoParquet
- Include map visualization
```

---

## Example Model Specification (Generated)

**File:** `wildlife_corridor_model.yaml`

```yaml
model_id: "wildlife_corridor_hennepin_2025"
model_type: "weighted_overlay"
objective: "Identify suitable wildlife corridor locations"
study_area: "Hennepin County, Minnesota"

criteria:
  - dataset_name: "wildlife_areas"
    criterion_name: "Protected Area Proximity"
    scoring_function:
      type: "distance_decay"
      params:
        max_distance: 2000
        decay_rate: 0.001
        units: "meters"
    weight: 35

  - dataset_name: "scientific_and_natural_areas"
    criterion_name: "SNA Proximity"
    scoring_function:
      type: "distance_decay"
      params:
        max_distance: 2000
        decay_rate: 0.001
    weight: 25

  - dataset_name: "land_use"
    criterion_name: "Habitat Quality"
    scoring_function:
      type: "categorical"
      params:
        mapping:
          "Forest": 10
          "Wetland": 9
          "Grassland": 7
          "Agriculture": 4
          "Residential": 2
          "Urban": 0
    weight: 25

  - dataset_name: "watersheds"
    criterion_name: "Water Proximity"
    scoring_function:
      type: "distance_decay"
      params:
        max_distance: 500
        decay_rate: 0.002
    weight: 15

constraints:
  - dataset_name: "land_use"
    constraint_type: "filter"
    params:
      expression: "land_use_type NOT IN ['Urban', 'Industrial']"

  - dataset_name: "wildlife_areas"
    constraint_type: "buffer"
    params:
      max_distance: 2000
      units: "meters"
      operation: "within"

combination_method: "weighted_sum"
output_range: [0, 100]

metadata:
  created_by: "Claude AI Model Designer"
  created_date: "2025-10-20"
  version: "1.0"
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Module structure setup
- [ ] Database schema
- [ ] ModelSpecification data structures
- [ ] Basic CLI commands
- [ ] Integration with spatial_data

### Phase 2: LLM Integration (Week 3-4)
- [ ] Claude API client
- [ ] Prompt engineering
- [ ] Requirement parsing
- [ ] Model design automation
- [ ] Response validation

### Phase 3: Execution Engine (Week 5-6)
- [ ] Dataset loading
- [ ] Scoring functions (linear, distance, categorical)
- [ ] Weighted overlay
- [ ] Constraint application
- [ ] Results export

### Phase 4: Advanced Features (Week 7-8)
- [ ] Model templates
- [ ] Interactive refinement
- [ ] Visualization
- [ ] Sensitivity analysis
- [ ] Documentation

---

## Key Design Decisions

### 1. Why LLM-Powered Design?

**Advantages:**
- Lower barrier to entry for non-GIS experts
- Rapid prototyping of suitability models
- Leverages domain knowledge from Claude
- Flexible and adaptable to varied requirements

**Risks:**
- LLM may misinterpret requirements
- Need validation and user review
- API costs for complex analyses

**Mitigation:**
- Always generate human-readable model specs (YAML)
- Allow manual editing of specs before execution
- Provide template library for common analyses

### 2. Why YAML Model Specifications?

- Human-readable and editable
- Version control friendly
- Standard format for configuration
- Easy to template and share

### 3. Infrastructure Reuse Target: 90%+

Reuses from existing modules:
- Config, DatabaseManager, logging (from core)
- spatial_data module for all datasets
- Exception handling
- CLI patterns

---

## Success Metrics

- [ ] Can parse 90%+ of natural language requirements correctly
- [ ] Generates valid model specifications in <30 seconds
- [ ] Successfully executes models with 95%+ success rate
- [ ] Outputs match manual GIS analysis results (validation)
- [ ] Users can complete full workflow in <5 minutes

---

## Future Enhancements

1. **Interactive Model Refinement** - Chat-based model iteration
2. **Fuzzy Logic Models** - More sophisticated suitability functions
3. **Multi-Criteria Decision Analysis** - AHP, TOPSIS, etc.
4. **Uncertainty Analysis** - Monte Carlo sensitivity testing
5. **Temporal Analysis** - Suitability changes over time
6. **3D Suitability** - Incorporate elevation/depth
7. **Web Interface** - Visual model builder
8. **Model Sharing** - Community model repository

---

## Questions for Consideration

1. **LLM API Key Management**: Use existing Config system or separate?
2. **Default Study Area**: Grid-based or use existing geometries?
3. **Coordinate System**: Always EPSG:4326 or configurable?
4. **Output Resolution**: How to handle raster vs vector outputs?
5. **Caching**: Should we cache LLM responses for similar queries?
6. **Model Versioning**: How to handle model updates?

---

## Contact

**Module Owner:** Ben
**RTGS Lab:** https://rtgs.umn.edu/
**Documentation:** TBD
