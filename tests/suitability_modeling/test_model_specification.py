"""Tests for Pydantic-based ModelSpecification."""

import pytest
import tempfile
from pathlib import Path

from rtgs_lab_tools.suitability_modeling.core.model_specification import (
    ScoringFunction,
    ModelCriterion,
    StudyAreaConfig,
    AnalysisUnitsConfig,
    ModelSpecification,
)


@pytest.fixture
def sample_spec_dict():
    """A valid model specification as a dictionary."""
    return {
        "model_id": "test_model",
        "model_type": "weighted_overlay",
        "objective": "Find suitable areas for testing",
        "study_area": "Test Area",
        "criteria": [
            {
                "dataset_name": "wetlands",
                "criterion_name": "Proximity to Wetlands",
                "weight": 60,
                "scoring_function": {
                    "type": "distance_decay",
                    "params": {"max_distance": 2000, "decay_rate": 0.001},
                    "output_range": [0, 10],
                },
            },
            {
                "dataset_name": "land_cover",
                "criterion_name": "Land Cover Type",
                "weight": 40,
                "scoring_function": {
                    "type": "categorical",
                    "params": {
                        "column": "lc_type",
                        "mapping": {"forest": 10, "grassland": 7, "urban": 1},
                    },
                    "output_range": [0, 10],
                },
            },
        ],
        "output_range": [0, 100],
        "metadata": {"created_by": "test"},
    }


class TestScoringFunction:
    def test_create(self):
        sf = ScoringFunction(type="distance_decay", params={"max_distance": 1000})
        assert sf.type == "distance_decay"
        assert sf.output_range == (0, 10)

    def test_defaults(self):
        sf = ScoringFunction(type="categorical")
        assert sf.params == {}
        assert sf.output_range == (0, 10)


class TestModelCriterion:
    def test_create(self):
        mc = ModelCriterion(
            dataset_name="test",
            criterion_name="Test Criterion",
            scoring_function=ScoringFunction(type="distance_decay"),
            weight=50,
        )
        assert mc.weight == 50

    def test_weight_bounds(self):
        with pytest.raises(Exception):
            ModelCriterion(
                dataset_name="test",
                criterion_name="Bad",
                scoring_function=ScoringFunction(type="distance_decay"),
                weight=150,
            )

        with pytest.raises(Exception):
            ModelCriterion(
                dataset_name="test",
                criterion_name="Bad",
                scoring_function=ScoringFunction(type="distance_decay"),
                weight=-10,
            )


class TestModelSpecification:
    def test_from_dict(self, sample_spec_dict):
        spec = ModelSpecification.from_dict(sample_spec_dict)
        assert spec.model_id == "test_model"
        assert len(spec.criteria) == 2
        assert spec.criteria[0].weight == 60
        assert spec.criteria[1].weight == 40

    def test_to_dict_roundtrip(self, sample_spec_dict):
        spec = ModelSpecification.from_dict(sample_spec_dict)
        result = spec.to_dict()
        assert result["model_id"] == "test_model"
        assert len(result["criteria"]) == 2

        # Roundtrip back
        spec2 = ModelSpecification.from_dict(result)
        assert spec2.model_id == spec.model_id
        assert len(spec2.criteria) == len(spec.criteria)

    def test_yaml_roundtrip(self, sample_spec_dict, tmp_path):
        spec = ModelSpecification.from_dict(sample_spec_dict)
        yaml_path = str(tmp_path / "model.yaml")
        spec.to_yaml(yaml_path)

        spec2 = ModelSpecification.from_yaml(yaml_path)
        assert spec2.model_id == spec.model_id
        assert len(spec2.criteria) == len(spec.criteria)
        assert spec2.criteria[0].weight == spec.criteria[0].weight

    def test_validate_valid(self, sample_spec_dict):
        spec = ModelSpecification.from_dict(sample_spec_dict)
        assert spec.validate() is True

    def test_validate_bad_weights(self):
        with pytest.raises(Exception):
            ModelSpecification(
                model_id="bad",
                model_type="weighted_overlay",
                objective="test",
                criteria=[
                    ModelCriterion(
                        dataset_name="a",
                        criterion_name="A",
                        scoring_function=ScoringFunction(type="distance_decay"),
                        weight=30,
                    ),
                    ModelCriterion(
                        dataset_name="b",
                        criterion_name="B",
                        scoring_function=ScoringFunction(type="distance_decay"),
                        weight=30,
                    ),
                ],
            )

    def test_validate_no_criteria(self):
        spec = ModelSpecification(
            model_id="empty",
            model_type="weighted_overlay",
            objective="test",
            criteria=[],
        )
        with pytest.raises(ValueError, match="at least one criterion"):
            spec.validate()

    def test_default_configs(self, sample_spec_dict):
        spec = ModelSpecification.from_dict(sample_spec_dict)
        assert spec.study_area_config is not None
        assert spec.analysis_units_config is not None

    def test_json_schema_generation(self):
        """Verify Pydantic can generate JSON schema (needed for structured outputs)."""
        schema = ModelSpecification.model_json_schema()
        assert "properties" in schema
        assert "model_id" in schema["properties"]
        assert "criteria" in schema["properties"]
