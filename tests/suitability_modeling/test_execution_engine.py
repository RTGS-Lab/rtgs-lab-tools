"""Tests for suitability modeling execution engine with mock data."""

import pytest
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, Polygon, box

from rtgs_lab_tools.suitability_modeling.core.model_specification import (
    ScoringFunction,
    ModelCriterion,
    AnalysisUnitsConfig,
    ModelSpecification,
)
from rtgs_lab_tools.suitability_modeling.core.execution_engine import (
    SuitabilityEngine,
    execute_model,
)


@pytest.fixture
def study_area_boundary():
    """Simple rectangular boundary."""
    poly = box(-93.3, 44.9, -93.2, 45.0)
    return gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")


@pytest.fixture
def point_features():
    """Point features for distance_decay scoring."""
    points = [Point(-93.25, 44.95), Point(-93.28, 44.92)]
    return gpd.GeoDataFrame(
        {"name": ["feature_a", "feature_b"]},
        geometry=points,
        crs="EPSG:4326",
    )


@pytest.fixture
def categorical_features():
    """Polygon features for categorical scoring."""
    polys = [
        box(-93.3, 44.9, -93.25, 44.95),
        box(-93.25, 44.95, -93.2, 45.0),
    ]
    return gpd.GeoDataFrame(
        {"land_type": ["forest", "urban"]},
        geometry=polys,
        crs="EPSG:4326",
    )


@pytest.fixture
def grid_units(study_area_boundary):
    """Pre-built grid for analysis."""
    from rtgs_lab_tools.spatial_data.core.grid import generate_grid

    return generate_grid(study_area_boundary, cell_size=1000, max_cells=500)


@pytest.fixture
def distance_model_spec():
    """Model with one distance_decay criterion."""
    return ModelSpecification(
        model_id="test_distance",
        model_type="weighted_overlay",
        objective="Test distance scoring",
        criteria=[
            ModelCriterion(
                dataset_name="points",
                criterion_name="Proximity to Points",
                scoring_function=ScoringFunction(
                    type="distance_decay",
                    params={"max_distance": 5000, "decay_rate": 0.0005},
                ),
                weight=100,
            ),
        ],
        analysis_units_config=AnalysisUnitsConfig(
            type="grid", cell_size=1000, max_cells=500
        ),
    )


@pytest.fixture
def categorical_model_spec():
    """Model with one categorical criterion."""
    return ModelSpecification(
        model_id="test_categorical",
        model_type="weighted_overlay",
        objective="Test categorical scoring",
        criteria=[
            ModelCriterion(
                dataset_name="land",
                criterion_name="Land Type",
                scoring_function=ScoringFunction(
                    type="categorical",
                    params={
                        "column": "land_type",
                        "mapping": {"forest": 10, "urban": 2},
                    },
                ),
                weight=100,
            ),
        ],
        analysis_units_config=AnalysisUnitsConfig(
            type="grid", cell_size=1000, max_cells=500
        ),
    )


class TestSuitabilityEngine:
    def test_distance_decay_scoring(
        self, distance_model_spec, point_features, study_area_boundary, grid_units
    ):
        datasets = {"points": point_features}
        engine = SuitabilityEngine(
            distance_model_spec, datasets, study_area_boundary, grid_units
        )
        results = engine.execute()

        assert "suitability_score" in results.columns
        assert len(results) == len(grid_units)
        # Scores should be non-negative
        assert (results["suitability_score"] >= 0).all()

    def test_categorical_scoring(
        self, categorical_model_spec, categorical_features, study_area_boundary, grid_units
    ):
        datasets = {"land": categorical_features}
        engine = SuitabilityEngine(
            categorical_model_spec, datasets, study_area_boundary, grid_units
        )
        results = engine.execute()

        assert "suitability_score" in results.columns
        assert len(results) == len(grid_units)

    def test_individual_scores_included(
        self, distance_model_spec, point_features, study_area_boundary, grid_units
    ):
        datasets = {"points": point_features}
        engine = SuitabilityEngine(
            distance_model_spec, datasets, study_area_boundary, grid_units
        )
        results = engine.execute()

        # Should have individual criterion score column
        assert "score_proximity_to_points" in results.columns


class TestExecuteModel:
    def test_full_execution(
        self, distance_model_spec, point_features, study_area_boundary, grid_units, tmp_path
    ):
        datasets = {"points": point_features}
        results = execute_model(
            model_spec=distance_model_spec,
            datasets=datasets,
            study_area_boundary=study_area_boundary,
            analysis_units=grid_units,
            output_dir=str(tmp_path),
            output_format="geoparquet",
        )

        assert results["success"] is True
        assert results["num_features"] > 0
        assert "output_file" in results
        assert "model_yaml" in results

        # Output file should exist
        from pathlib import Path

        assert Path(results["output_file"]).exists()
        assert Path(results["model_yaml"]).exists()

    def test_export_formats(
        self, distance_model_spec, point_features, study_area_boundary, grid_units, tmp_path
    ):
        datasets = {"points": point_features}

        for fmt in ["geoparquet", "geojson", "csv"]:
            out_dir = tmp_path / fmt
            out_dir.mkdir()
            results = execute_model(
                model_spec=distance_model_spec,
                datasets=datasets,
                study_area_boundary=study_area_boundary,
                analysis_units=grid_units,
                output_dir=str(out_dir),
                output_format=fmt,
            )
            assert results["success"] is True
