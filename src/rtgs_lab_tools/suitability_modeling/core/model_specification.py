"""Model specification data structures for suitability analysis."""

import json
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ScoringFunction:
    """
    How to convert dataset values to suitability scores.

    Attributes:
        type: Scoring function type ("distance_decay", "categorical", "linear")
        params: Parameters specific to the scoring function type
        output_range: Min and max output scores (default: 0-10)
    """
    type: str
    params: Dict[str, Any] = field(default_factory=dict)
    output_range: Tuple[float, float] = (0, 10)


@dataclass
class ModelCriterion:
    """
    Single criterion in a suitability model.

    Attributes:
        dataset_name: Name of spatial dataset from spatial_data registry
        criterion_name: Human-readable name for this criterion
        scoring_function: How to score this criterion
        weight: Importance weight (0-100), must sum to 100 across all criteria
    """
    dataset_name: str
    criterion_name: str
    scoring_function: ScoringFunction
    weight: float

    def __post_init__(self):
        """Validate criterion after initialization."""
        if not 0 <= self.weight <= 100:
            raise ValueError(f"Weight must be 0-100, got {self.weight}")


@dataclass
class StudyAreaConfig:
    """
    Configuration for study area boundary.

    Attributes:
        dataset: Dataset name for boundary (e.g., "hennepin_county_boundary")
        description: Human-readable description (e.g., "Hennepin County")
    """
    dataset: Optional[str] = None
    description: str = "Hennepin County"


@dataclass
class AnalysisUnitsConfig:
    """
    Configuration for analysis units.

    Attributes:
        type: Type of units ("grid", "parcels", "cities", "dataset")
        dataset: Dataset name if using parcels/cities/custom dataset
        cell_size: Grid cell size in meters if type="grid"
        max_cells: Maximum number of cells/features to analyze
    """
    type: str = "grid"
    dataset: Optional[str] = None
    cell_size: float = 100.0
    max_cells: int = 10000


@dataclass
class ModelSpecification:
    """
    Complete suitability model specification.

    This is the core data structure that defines a suitability analysis model.
    It can be saved to/loaded from YAML files for reproducibility.

    Attributes:
        model_id: Unique identifier for this model
        model_type: Type of model ("weighted_overlay" for MVP)
        objective: Description of what this model does
        study_area: Description of study area (backward compatibility)
        study_area_config: Detailed study area configuration
        analysis_units_config: Analysis unit configuration
        criteria: List of weighted criteria
        output_range: Min and max final suitability scores
        metadata: Additional information (created_by, date, etc.)
    """
    model_id: str
    model_type: str
    objective: str
    study_area: str = "Hennepin County"
    study_area_config: Optional[StudyAreaConfig] = None
    analysis_units_config: Optional[AnalysisUnitsConfig] = None
    criteria: List[ModelCriterion] = field(default_factory=list)
    output_range: Tuple[float, float] = (0, 100)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default configs if not provided."""
        if self.study_area_config is None:
            self.study_area_config = StudyAreaConfig(
                dataset="hennepin_county_boundary",
                description=self.study_area
            )
        if self.analysis_units_config is None:
            self.analysis_units_config = AnalysisUnitsConfig(type="grid")

    def validate(self) -> bool:
        """
        Validate model specification.

        Checks:
        - Model type is supported
        - Weights sum to 100
        - All criteria are valid

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        # Check model type
        if self.model_type != "weighted_overlay":
            raise ValueError(f"Only 'weighted_overlay' supported in MVP, got '{self.model_type}'")

        # Check we have criteria
        if not self.criteria:
            raise ValueError("Model must have at least one criterion")

        # Check weights sum to 100
        total_weight = sum(c.weight for c in self.criteria)
        if not (99.9 <= total_weight <= 100.1):  # Allow small floating point errors
            raise ValueError(f"Weights must sum to 100, got {total_weight}")

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            'model_id': self.model_id,
            'model_type': self.model_type,
            'objective': self.objective,
            'study_area': self.study_area,
            'criteria': [
                {
                    'dataset_name': c.dataset_name,
                    'criterion_name': c.criterion_name,
                    'weight': c.weight,
                    'scoring_function': {
                        'type': c.scoring_function.type,
                        'params': c.scoring_function.params,
                        'output_range': list(c.scoring_function.output_range)
                    }
                }
                for c in self.criteria
            ],
            'output_range': list(self.output_range),
            'metadata': self.metadata
        }

        # Add new configs
        if self.study_area_config:
            result['study_area_config'] = {
                'dataset': self.study_area_config.dataset,
                'description': self.study_area_config.description
            }

        if self.analysis_units_config:
            result['analysis_units_config'] = {
                'type': self.analysis_units_config.type,
                'dataset': self.analysis_units_config.dataset,
                'cell_size': self.analysis_units_config.cell_size,
                'max_cells': self.analysis_units_config.max_cells
            }

        return result

    def to_yaml(self, file_path: str):
        """
        Save model specification to YAML file.

        Args:
            file_path: Path to output YAML file
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelSpecification":
        """
        Load model specification from dictionary.

        Args:
            data: Dictionary with model specification

        Returns:
            ModelSpecification object
        """
        # Parse criteria
        criteria = []
        for c_data in data.get('criteria', []):
            sf_data = c_data['scoring_function']
            scoring_func = ScoringFunction(
                type=sf_data['type'],
                params=sf_data['params'],
                output_range=tuple(sf_data['output_range'])
            )
            criterion = ModelCriterion(
                dataset_name=c_data['dataset_name'],
                criterion_name=c_data['criterion_name'],
                scoring_function=scoring_func,
                weight=c_data['weight']
            )
            criteria.append(criterion)

        # Parse study area config
        study_area_config = None
        if 'study_area_config' in data:
            sa_data = data['study_area_config']
            study_area_config = StudyAreaConfig(
                dataset=sa_data.get('dataset'),
                description=sa_data.get('description', 'Hennepin County')
            )

        # Parse analysis units config
        analysis_units_config = None
        if 'analysis_units_config' in data:
            au_data = data['analysis_units_config']
            analysis_units_config = AnalysisUnitsConfig(
                type=au_data.get('type', 'grid'),
                dataset=au_data.get('dataset'),
                cell_size=au_data.get('cell_size', 100.0),
                max_cells=au_data.get('max_cells', 10000)
            )

        return cls(
            model_id=data['model_id'],
            model_type=data['model_type'],
            objective=data['objective'],
            study_area=data.get('study_area', 'Hennepin County'),
            study_area_config=study_area_config,
            analysis_units_config=analysis_units_config,
            criteria=criteria,
            output_range=tuple(data.get('output_range', [0, 100])),
            metadata=data.get('metadata', {})
        )

    @classmethod
    def from_yaml(cls, file_path: str) -> "ModelSpecification":
        """Load model specification from YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            ModelSpecification object
        """
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)
