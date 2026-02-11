"""Model specification data structures for suitability analysis.

Uses Pydantic BaseModel for validation, serialization, and JSON schema
generation (used by Claude structured outputs).
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator


class ScoringFunction(BaseModel):
    """How to convert dataset values to suitability scores.

    Supports distance_decay (proximity-based) and categorical (attribute-based) scoring.
    """

    type: str = Field(
        description="Scoring function type: 'distance_decay' for proximity-based scoring, "
        "'categorical' for attribute-based scoring"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters specific to the scoring function type. "
        "For distance_decay: {max_distance: meters, decay_rate: float}. "
        "For categorical: {column: str, mapping: {category: score}}.",
    )
    output_range: Tuple[float, float] = Field(
        default=(0, 10),
        description="Min and max output scores for this criterion (default: 0-10)",
    )


class ModelCriterion(BaseModel):
    """Single criterion in a suitability model.

    Each criterion maps a spatial dataset to a scoring function with an importance weight.
    """

    dataset_name: str = Field(
        description="Name of the spatial dataset to use for this criterion"
    )
    criterion_name: str = Field(
        description="Human-readable name for this criterion (e.g. 'Proximity to Wetlands')"
    )
    scoring_function: ScoringFunction = Field(
        description="How to score this criterion"
    )
    weight: float = Field(
        ge=0,
        le=100,
        description="Importance weight (0-100). All criteria weights must sum to 100.",
    )


class StudyAreaConfig(BaseModel):
    """Configuration for the study area boundary."""

    dataset: Optional[str] = Field(
        default=None,
        description="Dataset name for the boundary polygon, or None if provided directly",
    )
    description: str = Field(
        default="Study Area",
        description="Human-readable description of the study area",
    )


class AnalysisUnitsConfig(BaseModel):
    """Configuration for analysis units (how the study area is divided for scoring)."""

    type: str = Field(
        default="grid",
        description="Type of analysis units: 'grid' for regular cells, "
        "'parcels', 'cities', or 'dataset' for feature-based units",
    )
    dataset: Optional[str] = Field(
        default=None,
        description="Dataset name if using parcels/cities/custom dataset units",
    )
    cell_size: float = Field(
        default=100.0,
        description="Grid cell size in meters (only used when type='grid')",
    )
    max_cells: int = Field(
        default=10000,
        description="Maximum number of analysis units to process",
    )


class ModelSpecification(BaseModel):
    """Complete suitability model specification.

    Defines a weighted overlay suitability analysis model that can be
    saved to/loaded from YAML files for reproducibility.
    """

    model_id: str = Field(
        description="Unique identifier for this model (snake_case, descriptive)"
    )
    model_type: str = Field(
        default="weighted_overlay",
        description="Type of suitability model (currently only 'weighted_overlay')",
    )
    objective: str = Field(
        description="Description of what this model evaluates (e.g. 'Find suitable areas for wildlife corridors')"
    )
    study_area: str = Field(
        default="Study Area",
        description="Short description of the study area",
    )
    study_area_config: Optional[StudyAreaConfig] = Field(
        default=None,
        description="Detailed study area boundary configuration",
    )
    analysis_units_config: Optional[AnalysisUnitsConfig] = Field(
        default=None,
        description="How the study area is divided for analysis",
    )
    criteria: List[ModelCriterion] = Field(
        default_factory=list,
        description="List of weighted criteria for the suitability model. Weights must sum to 100.",
    )
    output_range: Tuple[float, float] = Field(
        default=(0, 100),
        description="Min and max final suitability scores",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (created_by, date, notes, etc.)",
    )

    def model_post_init(self, __context: Any) -> None:
        """Initialize default configs if not provided."""
        if self.study_area_config is None:
            self.study_area_config = StudyAreaConfig(description=self.study_area)
        if self.analysis_units_config is None:
            self.analysis_units_config = AnalysisUnitsConfig(type="grid")

    @model_validator(mode="after")
    def validate_weights(self) -> "ModelSpecification":
        """Validate that criteria weights sum to 100."""
        if self.criteria:
            total_weight = sum(c.weight for c in self.criteria)
            if not (99.9 <= total_weight <= 100.1):
                raise ValueError(
                    f"Criteria weights must sum to 100, got {total_weight}"
                )
        return self

    def validate(self) -> bool:
        """Validate model specification (legacy interface).

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if self.model_type != "weighted_overlay":
            raise ValueError(
                f"Only 'weighted_overlay' supported, got '{self.model_type}'"
            )
        if not self.criteria:
            raise ValueError("Model must have at least one criterion")

        total_weight = sum(c.weight for c in self.criteria)
        if not (99.9 <= total_weight <= 100.1):
            raise ValueError(f"Weights must sum to 100, got {total_weight}")

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump(mode="python")

    def to_yaml(self, file_path: str) -> None:
        """Save model specification to YAML file.

        Args:
            file_path: Path to output YAML file
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # model_dump with mode="json" converts tuples to lists automatically,
        # which is needed because yaml.safe_load cannot handle Python tuples.
        data = self.model_dump(mode="json")
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelSpecification":
        """Load model specification from dictionary.

        Args:
            data: Dictionary with model specification

        Returns:
            ModelSpecification object
        """
        return cls.model_validate(data)

    @classmethod
    def from_yaml(cls, file_path: str) -> "ModelSpecification":
        """Load model specification from YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            ModelSpecification object
        """
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)
