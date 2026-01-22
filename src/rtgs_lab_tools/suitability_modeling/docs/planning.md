# Suitability Modeling Module - Planning Document

**Status:** Planning Phase

**Branch:** TBD

**Created:** 2025-10-05

**Target Users:** Mixed audience (GIS experts, domain scientists, non-technical stakeholders)

---

## Table of Contents

1. [Vision & Goals](#vision--goals)
2. [User Workflows](#user-workflows)
3. [Technical Architecture](#technical-architecture)
4. [Implementation Roadmap](#implementation-roadmap)
5. [Design Decisions](#design-decisions)
6. [Success Criteria](#success-criteria)

---

## Vision & Goals

### Primary Vision

Create an **AI-powered suitability analysis framework** that enables users to describe their analysis needs in natural language, which are then automatically translated into executable, scientifically-sound suitability models using vetted spatial datasets.

### Core Goals

1. **Lower Barriers to Entry**
   - Enable non-GIS experts to perform sophisticated spatial analysis
   - Reduce time from idea to results from days to minutes
   - Leverage natural language instead of requiring GIS software expertise

2. **Ensure Scientific Rigor**
   - Use only vetted, quality-controlled datasets (via `spatial_data` module)
   - Generate transparent, reviewable model specifications
   - Follow established suitability modeling best practices
   - Provide full audit trail for reproducibility

3. **Enable Iterative Refinement**
   - Chat-based model improvement workflow
   - LLM assists with refinement suggestions
   - Users can manually edit model specifications
   - Version control for model evolution

4. **Flexible & Extensible**
   - Support multiple suitability modeling methods
   - Accommodate diverse use cases (conservation, urban planning, agriculture)
   - Export results in standard GIS formats
   - Integrate with existing workflows

### Target Use Cases

**Conservation Planning:**
- Natural resource preservation prioritization
- Wildlife corridor identification
- Habitat restoration site selection
- Protected area network expansion
- Ecosystem connectivity analysis

---

## User Workflows

### Workflow 1: Quick Analysis (Novice User)

**User:** Domain scientist with minimal GIS experience

**Goal:** Identify suitable wetland restoration sites in Hennepin County

**Steps:**

1. **Write Requirements**
   ```bash
   # Create requirements.txt
   Objective: Find suitable wetland restoration sites in Hennepin County

   Criteria:
   - Near existing water bodies
   - Avoid urban areas
   - Prefer low-lying areas with poor drainage
   - Consider proximity to wildlife areas

   Output: Top 10 most suitable sites as shapefile
   ```

2. **Design Model** 
   ```bash
   rtgs suitability design --input requirements.txt
   ```

   **Output:**
   - LLM generates initial model specification
   - Shows model summary in terminal
   - Enters interactive refinement mode

3. **Refine Model**
   ```
   [Model Summary]
   Weighted Overlay Model: Wetland Restoration Suitability

   Criteria:
   - Water Proximity (40%): Distance to watersheds
   - Land Use Suitability (30%): Avoid urban areas
   - Wildlife Connectivity (30%): Proximity to wildlife areas

   Study Area: Hennepin County (auto-detected)
   Resolution: 50m grid cells (auto-selected)

   [Refine?] (y/n/chat):
   ```

   User: `chat`
   ```
   > Can you increase the wildlife connectivity weight to 40% and reduce water to 30%?

   [Updated Model]
   - Wildlife Connectivity: 40% ✓
   - Water Proximity: 30% ✓
   - Land Use: 30% ✓

   [Looks good?] (y/n/chat):
   ```

   User: `y`

4. **Execute & Export** 
   ```bash
   # Automatically triggered after approval
   [Executing model...]
   Loading datasets: watersheds, land_use, wildlife_areas
   Calculating criterion scores...
   Applying weighted overlay...
   Identifying top 10 sites...
   Exporting results...

   ✓ Complete! Results saved to:
     - results/wetland_restoration_suitability.shp
     - results/wetland_restoration_model.yaml
     - results/wetland_restoration_report.html
   ```

**Total Time:** ~10 minutes from idea to results

---

### Workflow 2: Advanced Analysis (GIS Expert)

**User:** GIS analyst with specific modeling requirements

**Goal:** Build precise wildlife corridor model with custom scoring functions

**Steps:**

1. **Write Detailed Requirements** (10 min)
   ```
   Objective: Identify wildlife corridors connecting DNR Wildlife Management Areas

   Study Area: Hennepin County, Minnesota
   Resolution: 30m grid cells (to match land cover data)

   Criteria:
   - Protected Area Proximity (35%):
     * Distance decay to wildlife_areas dataset
     * Max influence distance: 2000m
     * Exponential decay rate: 0.001

   - Habitat Quality (30%):
     * Based on land_use dataset
     * Forest=10, Wetland=9, Grassland=7, Agriculture=3, Urban=0

   - Human Disturbance (20%):
     * Inverse distance to urban areas
     * Maximum avoidance distance: 1000m

   - Water Access (15%):
     * Distance to watersheds dataset
     * Linear scoring, closer = better

   Constraints:
   - Must be within 3km of existing protected areas
   - Exclude areas classified as Urban or Industrial
   - Minimum corridor width: 100m

   Output:
   - Suitability raster (0-100 scale)
   - Top 5 corridor opportunities as polygons
   - GeoParquet format for further analysis
   ```

2. **Design Model with Review**
   ```bash
   rtgs suitability design --input requirements.txt --output-spec corridor_model.yaml
   ```

   LLM generates model, saves to `corridor_model.yaml`

3. **Manual Refinement** (5 min)
   ```bash
   # User opens corridor_model.yaml in text editor
   # Makes precise adjustments to scoring functions
   # Tweaks weights, thresholds, parameters
   ```

4. **Validate Model**
   ```bash
   rtgs suitability validate --model-spec corridor_model.yaml

   ✓ All datasets available
   ✓ Weights sum to 100%
   ✓ Scoring functions valid
   ✓ Study area resolvable
   ✓ Model ready for execution
   ```

5. **Execute & Export**
   ```bash
   rtgs suitability execute \
     --model-spec corridor_model.yaml \
     --output-dir ./results/corridors \
     --output-format geoparquet
   ```

**Total Time:** ~20 minutes for production-ready analysis

---

### Workflow 3: Template-Based Analysis (Any User)

**User:** Urban planner reusing a common analysis type

**Goal:** Solar farm siting analysis using pre-built template

**Steps:**

1. **Browse Templates**
   ```bash
   rtgs suitability list-templates

   Available Templates:
   - wildlife_corridor: Wildlife corridor identification
   - solar_siting: Solar farm suitability analysis ✓
   - wetland_restoration: Wetland restoration site selection
   - urban_greenspace: Urban green space prioritization
   - flood_risk: Flood hazard assessment
   ```

2. **Customize Template**
   ```bash
   rtgs suitability use-template solar_siting \
     --study-area "Hennepin County" \
     --output-spec my_solar_model.yaml

   [Template Loaded: Solar Farm Siting]
   Criteria: Slope, solar radiation, land use, infrastructure proximity

   Customize? (y/n): y

   > What study area? Hennepin County
   > Minimum site size (acres)? 50
   > Maximum distance to transmission lines (meters)? 5000
   > Exclude agricultural land? y

   ✓ Model customized and saved to my_solar_model.yaml
   ```

3. **Review & Execute**
   ```bash
   rtgs suitability execute --model-spec my_solar_model.yaml
   ```

**Total Time:** ~5 minutes using template

---

## Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input Layer                         │
│  - Text file requirements                                   │
│  - Interactive CLI prompts                                  │
│  - Template selection                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Requirement Parser (NLP)                       │
│  - Extract objective, criteria, constraints                │
│  - Parse study area description                            │
│  - Identify output preferences                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         LLM-Powered Model Designer (Claude API)             │
│  - Interpret requirements semantically                      │
│  - Map to available spatial datasets                        │
│  - Design scoring functions                                 │
│  - Assign weights and combination logic                     │
│  - Generate ModelSpecification (YAML)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│          Interactive Refinement Engine                      │
│  - Present model to user                                    │
│  - Chat-based modification interface                        │
│  - LLM assists with refinement                              │
│  - Validate changes                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Model Validation                               │
│  - Check dataset availability (via spatial_data)            │
│  - Validate scoring function parameters                     │
│  - Verify weights sum to 100%                               │
│  - Ensure study area is resolvable                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Execution Engine (GeoPandas)                     │
│  1. Study Area Resolution                                   │
│     - Parse location (Hennepin County, City of Minneapolis) │
│     - Determine extent and resolution                       │
│     - Create analysis grid or use boundaries                │
│                                                              │
│  2. Dataset Loading (via spatial_data)                      │
│     - Extract required datasets                             │
│     - Ensure CRS consistency                                │
│     - Clip to study area                                    │
│                                                              │
│  3. Criterion Scoring                                       │
│     - Apply scoring functions:                              │
│       * Distance decay                                      │
│       * Categorical mapping                                 │
│       * Linear rescaling                                    │
│       * Threshold functions                                 │
│                                                              │
│  4. Constraint Application                                  │
│     - Apply hard constraints                                │
│     - Filter unsuitable areas                               │
│                                                              │
│  5. Weighted Overlay                                        │
│     - Combine criterion scores                              │
│     - Apply weights                                         │
│     - Generate final suitability scores                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Results Exporter                               │
│  - Export suitability surface (GeoParquet/Shapefile/etc)   │
│  - Generate top-N site recommendations                      │
│  - Create HTML report with summary statistics               │
│  - Save model specification (YAML) with results             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Database Logger (PostgreSQL)                   │
│  - Log model specifications                                 │
│  - Log executions with performance metrics                  │
│  - Log LLM interactions (prompts/responses)                 │
│  - Track model versions and refinements                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components Detail

### 1. Study Area Resolution System

**Problem:** User provides location as text (e.g., "Hennepin County", "City of Minneapolis")
**Solution:** Multi-stage resolution process

**Stage 1: Geocoding & Boundary Lookup**

```python
class StudyAreaResolver:
    """Resolve textual study area descriptions to geographic boundaries."""

    def __init__(self):
        # Use spatial_data datasets for boundary matching
        self.boundary_datasets = {
            "county": "counties",  # If we have this dataset
            "city": "cities",      # If we have this dataset
            "watershed": "watersheds"
        }

    def resolve(self, location_text: str) -> Dict[str, Any]:
        """Resolve location text to geographic extent.

        Examples:
            "Hennepin County" → Match to county boundaries
            "City of Minneapolis" → Match to city boundaries
            "Study area: 45.0,-93.5 to 45.2,-93.2" → Parse bbox
            "Custom shapefile: /path/to/area.shp" → Load file

        Returns:
            {
                "geometry": GeoDataFrame with boundary,
                "extent": [minx, miny, maxx, maxy],
                "resolution": 30,  # meters, auto-determined
                "area_km2": 1500.2,
                "method": "county_match"
            }
        """

        # Try different resolution strategies

        # 1. Named boundary match
        result = self._try_boundary_match(location_text)
        if result:
            return result

        # 2. Coordinate parsing
        result = self._try_coordinate_parsing(location_text)
        if result:
            return result

        # 3. File path parsing
        result = self._try_file_path(location_text)
        if result:
            return result

        # 4. LLM-assisted interpretation
        result = self._llm_resolve(location_text)
        if result:
            return result

        # 5. Prompt user for clarification
        return self._prompt_user_for_clarification(location_text)

    def _try_boundary_match(self, location_text: str) -> Optional[Dict]:
        """Try to match location to existing boundaries."""
        # Search through available boundary datasets
        # Use fuzzy matching (e.g., "hennepin" matches "Hennepin County")
        pass

    def _llm_resolve(self, location_text: str) -> Optional[Dict]:
        """Use LLM to interpret ambiguous location descriptions."""
        # Send to Claude: "User wants to analyze: {location_text}"
        # "Can you identify the geographic area and suggest how to define it?"
        pass

    def determine_resolution(self, area_km2: float, analysis_type: str) -> float:
        """Auto-determine appropriate cell size based on area and analysis type.

        Rules:
        - Small areas (<10 km²): 10m resolution
        - Medium areas (10-1000 km²): 30m resolution
        - Large areas (>1000 km²): 100m resolution
        - Corridor analysis: Prefer finer resolution (30m)
        - Regional planning: Coarser ok (100m)
        """
        pass
```

**Fallback Behavior:**

If study area cannot be resolved automatically:
```
[Study Area Not Resolved]

I couldn't automatically determine the study area from: "metro area"

Please provide one of the following:
1. A specific county name (e.g., "Hennepin County")
2. A city name (e.g., "Minneapolis")
3. A bounding box (e.g., "45.0,-93.5 to 45.2,-93.2")
4. A shapefile path (e.g., "/path/to/study_area.shp")

Study area:
```

---

### 2. Interactive Refinement Engine

**Purpose:** Enable chat-based model improvement

**Implementation:**

```python
class ModelRefiner:
    """Interactive chat-based model refinement."""

    def __init__(self, model_spec: ModelSpecification):
        self.model_spec = model_spec
        self.conversation_history = []
        self.llm_client = ClaudeClient()

    def start_refinement_session(self):
        """Begin interactive refinement."""
        self._display_model_summary()

        while True:
            user_input = click.prompt("\n[Refine?] (y=approve, n=cancel, or type request)")

            if user_input.lower() == 'y':
                click.echo("✓ Model approved! Proceeding to execution...")
                return self.model_spec

            elif user_input.lower() == 'n':
                click.echo("✗ Model design cancelled.")
                return None

            else:
                # User provided refinement request
                updated_spec = self._refine_with_llm(user_input)
                self.model_spec = updated_spec
                self._display_model_summary()

    def _display_model_summary(self):
        """Display current model in readable format."""
        click.echo("\n" + "="*60)
        click.echo(f"Model: {self.model_spec.objective}")
        click.echo("="*60)
        click.echo(f"\nStudy Area: {self.model_spec.study_area}")
        click.echo(f"Model Type: {self.model_spec.model_type}")
        click.echo(f"\nCriteria ({len(self.model_spec.criteria)}):")

        for criterion in self.model_spec.criteria:
            click.echo(f"  • {criterion.criterion_name}: {criterion.weight}%")
            click.echo(f"    Dataset: {criterion.dataset_name}")
            click.echo(f"    Scoring: {criterion.scoring_function.type}")

        click.echo(f"\nConstraints ({len(self.model_spec.constraints)}):")
        for constraint in self.model_spec.constraints:
            click.echo(f"  • {constraint.constraint_type} on {constraint.dataset_name}")

    def _refine_with_llm(self, user_request: str) -> ModelSpecification:
        """Send refinement request to LLM."""

        prompt = f"""
        The user wants to refine the suitability model.

        Current Model:
        {self.model_spec.to_yaml()}

        User Request:
        {user_request}

        Please update the model specification to accommodate the user's request.
        Return the complete updated model specification as YAML.
        """

        response = self.llm_client.chat(
            messages=self.conversation_history + [{"role": "user", "content": prompt}]
        )

        # Parse response into updated ModelSpecification
        updated_spec = self._parse_llm_response(response)

        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_request})
        self.conversation_history.append({"role": "assistant", "content": response})

        # Show what changed
        self._display_changes(self.model_spec, updated_spec)

        return updated_spec

    def _display_changes(self, old_spec: ModelSpecification, new_spec: ModelSpecification):
        """Highlight what changed between specs."""
        click.echo("\n[Changes Applied]")

        # Compare weights
        for old_crit, new_crit in zip(old_spec.criteria, new_spec.criteria):
            if old_crit.weight != new_crit.weight:
                click.echo(f"  • {new_crit.criterion_name}: {old_crit.weight}% → {new_crit.weight}%")

        # etc.
```

**Example Refinement Session:**

```
[Model Summary]
Wildlife Corridor Suitability Model

Study Area: Hennepin County
Model Type: weighted_overlay

Criteria (3):
  • Protected Area Proximity: 40%
    Dataset: wildlife_areas
    Scoring: distance_decay
  • Habitat Quality: 35%
    Dataset: land_use
    Scoring: categorical
  • Water Access: 25%
    Dataset: watersheds
    Scoring: distance_decay

Constraints (1):
  • filter on land_use

[Refine?] (y=approve, n=cancel, or type request): increase habitat quality to 45%

[Changes Applied]
  • Habitat Quality: 35% → 45%
  • Protected Area Proximity: 40% → 30% (auto-adjusted to maintain 100%)

[Updated Model Summary]
...

[Refine?] (y=approve, n=cancel, or type request): y

✓ Model approved! Proceeding to execution...
```

---

### 3. Scoring Functions Library

**Purpose:** Convert raw spatial data to suitability scores (0-10 scale)

**Implementation:**

```python
class ScoringFunctions:
    """Library of scoring functions for suitability analysis."""

    @staticmethod
    def distance_decay(
        study_area: gpd.GeoDataFrame,
        feature_dataset: gpd.GeoDataFrame,
        max_distance: float,
        decay_rate: float = 0.001,
        invert: bool = False
    ) -> np.ndarray:
        """Score based on distance to features with exponential decay.

        Args:
            study_area: Analysis grid or polygons
            feature_dataset: Features to calculate distance from
            max_distance: Distance beyond which score = 0
            decay_rate: Exponential decay rate (higher = faster decay)
            invert: If True, score decreases with proximity (for avoidance)

        Returns:
            Array of scores (0-10)
        """
        # Calculate distance from each study area cell to nearest feature
        distances = study_area.geometry.apply(
            lambda x: feature_dataset.distance(x).min()
        )

        # Apply exponential decay: score = 10 * exp(-decay_rate * distance)
        scores = 10 * np.exp(-decay_rate * distances)

        # Cap at max_distance
        scores[distances > max_distance] = 0

        # Invert if needed (for avoidance criteria)
        if invert:
            scores = 10 - scores

        return scores

    @staticmethod
    def categorical_mapping(
        study_area: gpd.GeoDataFrame,
        category_dataset: gpd.GeoDataFrame,
        category_column: str,
        score_mapping: Dict[str, float]
    ) -> np.ndarray:
        """Score based on categorical attribute values.

        Args:
            study_area: Analysis grid
            category_dataset: Dataset with categorical attributes
            category_column: Column containing categories
            score_mapping: Dict mapping categories to scores
                Example: {"Forest": 10, "Urban": 0, "Agriculture": 5}

        Returns:
            Array of scores (0-10)
        """
        # Spatial join to get category for each study area cell
        joined = gpd.sjoin(study_area, category_dataset, how="left")

        # Map categories to scores
        scores = joined[category_column].map(score_mapping).fillna(0)

        return scores.values

    @staticmethod
    def linear_rescale(
        values: np.ndarray,
        min_value: float,
        max_value: float,
        invert: bool = False,
        output_range: Tuple[float, float] = (0, 10)
    ) -> np.ndarray:
        """Linear rescaling from input range to output range.

        Args:
            values: Input values
            min_value: Minimum of input range
            max_value: Maximum of input range
            invert: If True, invert the scaling
            output_range: Output score range

        Returns:
            Rescaled values
        """
        # Normalize to 0-1
        normalized = (values - min_value) / (max_value - min_value)
        normalized = np.clip(normalized, 0, 1)

        if invert:
            normalized = 1 - normalized

        # Scale to output range
        out_min, out_max = output_range
        scores = out_min + normalized * (out_max - out_min)

        return scores

    @staticmethod
    def threshold(
        values: np.ndarray,
        threshold: float,
        above_score: float = 10,
        below_score: float = 0
    ) -> np.ndarray:
        """Binary threshold scoring.

        Args:
            values: Input values
            threshold: Threshold value
            above_score: Score for values >= threshold
            below_score: Score for values < threshold

        Returns:
            Binary scores
        """
        scores = np.where(values >= threshold, above_score, below_score)
        return scores

    @staticmethod
    def fuzzy_gaussian(
        values: np.ndarray,
        optimal_value: float,
        spread: float,
        output_range: Tuple[float, float] = (0, 10)
    ) -> np.ndarray:
        """Fuzzy gaussian membership function.

        Scores are highest at optimal_value and decay with distance.

        Args:
            values: Input values
            optimal_value: Value with maximum score
            spread: Controls width of the gaussian curve
            output_range: Output score range

        Returns:
            Fuzzy membership scores
        """
        # Gaussian function
        normalized = np.exp(-((values - optimal_value) ** 2) / (2 * spread ** 2))

        # Scale to output range
        out_min, out_max = output_range
        scores = out_min + normalized * (out_max - out_min)

        return scores
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Basic module structure and core infrastructure

**Tasks:**
- [ ] Create module directory structure
- [ ] Set up `__init__.py` with lazy loading
- [ ] Create database schema for model catalog
- [ ] Implement `ModelSpecification` data classes
- [ ] Set up basic CLI commands structure
- [ ] Configure logging and error handling
- [ ] Write initial README with examples

**Deliverables:**
- Module scaffolding complete
- Database tables created
- Basic data structures defined
- Initial documentation

---

### Phase 2: LLM Integration (Weeks 3-4)

**Goal:** Claude API integration for model design

**Tasks:**
- [ ] Create `ClaudeClient` wrapper class
- [ ] Design and test prompt templates
- [ ] Implement requirement parsing
- [ ] Build model design workflow
- [ ] Add response validation
- [ ] Test with various requirement examples
- [ ] Implement cost tracking for API calls

**Deliverables:**
- Working LLM integration
- Tested prompts for model design
- Can generate model specs from text input
- API cost logging

---

### Phase 3: Execution Engine - Weighted Overlay (Weeks 5-6)

**Goal:** Execute weighted overlay models

**Tasks:**
- [ ] Implement `StudyAreaResolver` class
- [ ] Build dataset loading via `spatial_data`
- [ ] Implement scoring functions:
  - [ ] Distance decay
  - [ ] Categorical mapping
  - [ ] Linear rescaling
  - [ ] Threshold
- [ ] Build weighted overlay combination
- [ ] Add constraint application
- [ ] Implement results exporter (GeoParquet, Shapefile)
- [ ] Test end-to-end execution

**Deliverables:**
- Can execute weighted overlay models
- Results export in multiple formats
- Study area resolution working

---

### Phase 4: Interactive Refinement (Week 7)

**Goal:** Chat-based model refinement

**Tasks:**
- [ ] Implement `ModelRefiner` class
- [ ] Build interactive CLI session
- [ ] Add change detection and display
- [ ] Test refinement workflows
- [ ] Add conversation history logging

**Deliverables:**
- Interactive refinement working
- Users can chat to modify models
- Changes clearly displayed

---

### Phase 5: Boolean/Constraint Models (Week 8)

**Goal:** Support constraint-based suitability

**Tasks:**
- [ ] Implement boolean overlay logic
- [ ] Add constraint filtering
- [ ] Support multi-constraint combinations
- [ ] Test constraint-based models

**Deliverables:**
- Boolean overlay model type working
- Constraint combinations functional

---

### Phase 6: Templates & Examples (Week 9)

**Goal:** Pre-built model templates

**Tasks:**
- [ ] Create template system
- [ ] Build 5 example templates:
  - [ ] Wildlife corridor
  - [ ] Solar farm siting
  - [ ] Wetland restoration
  - [ ] Urban greenspace
  - [ ] Flood risk assessment
- [ ] Add template customization
- [ ] Test template workflow

**Deliverables:**
- 5 working templates
- Template customization CLI
- Template documentation

---

### Phase 7: Documentation & Testing (Week 10)

**Goal:** Comprehensive docs and validation

**Tasks:**
- [ ] Write user guide
- [ ] Create example workflows
- [ ] Add API documentation
- [ ] Write unit tests
- [ ] Integration testing
- [ ] Performance testing
- [ ] Create tutorial videos

**Deliverables:**
- Complete documentation
- Test suite
- Tutorial materials

---

### Phase 8: Multi-Criteria Decision Analysis (Future)

**Goal:** Advanced MCDA methods (AHP, TOPSIS)

**Tasks:**
- [ ] Implement AHP (Analytic Hierarchy Process)
- [ ] Add pairwise comparison interface
- [ ] Implement consistency checking
- [ ] Add TOPSIS method
- [ ] Test with complex decision scenarios

---

## Design Decisions

### Decision 1: Iterative Refinement Approach

**Choice:** Interactive chat-based refinement after initial model generation

**Rationale:**
- **User Answer:** Selected "Iterative Refinement"
- Balances automation with user control
- Allows users to guide model improvement
- LLM can suggest refinements based on domain knowledge
- Maintains transparency - users see and approve all changes

**Implementation:**
```
Design → Present → Refine (chat) → Approve → Execute
         ↑__________________|
```

---

### Decision 2: Mixed Audience Design

**Choice:** Build for all expertise levels

**Rationale:**
- **User Answer:** Selected "Mixed Audience"
- Need simple workflows for novices (templates, auto-design)
- Need manual control for experts (YAML editing, custom functions)
- Provide progressive disclosure of complexity

**Implementation Strategy:**
- **Novice:** Template-based or full auto-design
- **Intermediate:** Auto-design with interactive refinement
- **Expert:** Manual YAML editing, custom scoring functions

---

### Decision 3: Location-Based Study Area Resolution

**Choice:** User provides location text, module resolves extent and resolution

**Rationale:**
- **User Answer:** "User provides location like 'Hennepin County', module deciphers"
- More natural for users than providing coordinates
- LLM can help interpret ambiguous locations
- Fallback to prompt if unclear

**Resolution Hierarchy:**
1. Named boundary match (county, city)
2. Coordinate parsing
3. File path (shapefile)
4. LLM interpretation
5. User prompt

---

### Decision 4: Model Type Priorities

**Choice:** Implement in order: Weighted Overlay → Boolean/Constraint → AHP

**Rationale:**
- **User Answer:** Selected weighted overlay, boolean, and AHP
- **Weighted Overlay:** Most common and intuitive (Phase 3)
- **Boolean/Constraint:** Simpler, good for screening (Phase 5)
- **AHP:** More complex, for advanced users (Phase 8)

**Progression:**
- Start simple (weighted overlay)
- Add constraint filtering
- Later add sophisticated MCDA methods

---

### Decision 5: LLM API Provider

**Choice:** Use Anthropic Claude API

**Rationale:**
- Long context window (200k tokens)
- Strong reasoning capabilities
- Good at structured output (JSON/YAML)
- Can handle complex spatial analysis concepts
- Existing rtgs-lab-tools may already use Anthropic

**API Key Management:**
- Use existing `Config` system
- Environment variable: `ANTHROPIC_API_KEY`
- Fallback to prompting user for key

---

### Decision 6: Model Specification Format

**Choice:** YAML for human readability, JSON internally

**Rationale:**
- YAML is human-readable and editable
- Comments possible in YAML
- Standard for configuration
- Easy to convert to/from JSON for LLM
- Version control friendly

**Example:**
```yaml
model_id: wildlife_corridor_001
model_type: weighted_overlay
objective: "Identify wildlife corridors"

criteria:
  - dataset_name: wildlife_areas
    criterion_name: "Protected Area Proximity"
    weight: 40
    scoring_function:
      type: distance_decay
      params:
        max_distance: 2000
        decay_rate: 0.001
```

---

### Decision 7: Infrastructure Reuse (90%+ target)

**Choice:** Maximum reuse from existing modules

**Reused Components:**
- `Config` - Configuration management
- `DatabaseManager` - PostgreSQL connections
- `PostgresLogger` - Audit logging
- Exception handling - Standard error classes
- CLI patterns - Click-based commands
- `spatial_data` module - All dataset access

**New Components (10%):**
- LLM integration (`llm/`)
- Scoring functions (`models/`)
- Interactive refinement (`core/model_refiner.py`)
- Execution engine (`core/execution_engine.py`)

---

## Success Criteria

### Technical Success Metrics

1. **LLM Accuracy**
   - [ ] 90%+ of natural language requirements correctly interpreted
   - [ ] Generated models are scientifically valid
   - [ ] Dataset matching accuracy >95%

2. **Execution Reliability**
   - [ ] 95%+ model execution success rate
   - [ ] Results match manual GIS analysis (validation cases)
   - [ ] Handle datasets up to 100k features efficiently

3. **Performance**
   - [ ] Model design: <30 seconds
   - [ ] Model execution: <5 minutes for county-scale analysis
   - [ ] Interactive refinement: <5 second response time

4. **Usability**
   - [ ] Novice user completes analysis in <10 minutes
   - [ ] Expert user has full control and transparency
   - [ ] Clear error messages and recovery paths

### User Success Metrics

1. **Adoption**
   - [ ] 3 different user types successfully use module
   - [ ] Positive feedback from >80% of test users
   - [ ] Users prefer this over manual GIS workflow

2. **Reproducibility**
   - [ ] All analyses fully documented (YAML + logs)
   - [ ] Can re-run past analyses and get same results
   - [ ] Model specs shareable between users

3. **Educational Value**
   - [ ] Users learn suitability modeling concepts
   - [ ] Generated models teach best practices
   - [ ] Clear explanations of scoring choices

---

## Risk Mitigation

### Risk 1: LLM Misinterpretation

**Risk:** LLM generates invalid or scientifically unsound models

**Mitigation:**
- Always show model spec for user review
- Validate all parameters programmatically
- Provide expert templates as starting points
- Allow manual YAML editing
- Log all LLM interactions for debugging

### Risk 2: Dataset Availability

**Risk:** Required datasets not in `spatial_data` registry

**Mitigation:**
- Start with well-defined use cases using existing datasets
- Expand `spatial_data` registry alongside module development
- Allow user-provided datasets as fallback
- LLM suggests alternatives if dataset missing

### Risk 3: Study Area Resolution Failure

**Risk:** Can't automatically determine study area

**Mitigation:**
- Multi-stage resolution with fallbacks
- Clear prompts when resolution fails
- Allow manual boundary file upload
- LLM assistance for ambiguous cases

### Risk 4: Computational Performance

**Risk:** Large study areas cause slow execution

**Mitigation:**
- Auto-adjust resolution based on area size
- Implement spatial indexing
- Use GeoPandas/NumPy vectorization
- Add progress indicators
- Consider Dask for very large analyses (future)

---

## Future Enhancements (Post-MVP)

1. **Sensitivity Analysis**
   - Test model stability with varying weights
   - Monte Carlo uncertainty quantification
   - Identify critical parameters

2. **Visualization**
   - Interactive maps (Folium/Leaflet)
   - Comparison visualizations
   - Report generation with charts

3. **Temporal Analysis**
   - Multi-year suitability trends
   - Before/after scenario comparison
   - Predictive modeling

4. **Model Optimization**
   - Genetic algorithms for weight optimization
   - Machine learning-assisted calibration
   - Automated model selection

5. **Collaboration Features**
   - Model sharing repository
   - Version control for models
   - Peer review workflow

6. **Web Interface**
   - Visual model builder
   - Drag-and-drop criteria
   - Real-time preview

---

## Next Steps

1. **Review & Approve Planning Document** ✓ (you are here)
2. **Set Up Module Structure** (create files/folders)
3. **Create Database Schema**
4. **Implement Core Data Structures** (ModelSpecification, etc.)
5. **Begin LLM Integration** (Claude API client)
6. **Build First Prototype** (simple weighted overlay)
7. **Test with Real Use Case** (wildlife corridor example)
8. **Iterate Based on Feedback**

---

## Questions for Further Discussion

1. **LLM Cost Management**: Set usage limits? Implement caching?
2. **Dataset Expansion**: Which spatial_data datasets to add first?
3. **Scoring Function Extensibility**: How to support custom user functions?
4. **Output Visualization**: Include maps in results or separate tool?
5. **Model Repository**: Build sharing platform for models?
6. **Validation**: How to validate model outputs against expert knowledge?

---

**Ready to begin implementation?** Let me know if you'd like to proceed with creating the module structure!
