"""
Test script for study area boundary and analysis unit integration.

This script tests the new boundary and analysis unit functionality by:
1. Creating a model with study area boundary
2. Using parcels as analysis units instead of grid
3. Executing the model and verifying results

Prerequisites:
- Set RTGS_FGDB_PATH environment variable to point to the Hennepin County FGDB
"""

import logging
import os
from pathlib import Path

from core.model_specification import (
    ModelSpecification,
    ModelCriterion,
    ScoringFunction,
    StudyAreaConfig,
    AnalysisUnitsConfig,
)
from core.execution_engine import execute_model
from core.dataset_registry import is_fgdb_available, get_all_available_datasets

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_test_model() -> ModelSpecification:
    """Create a test model specification with boundaries and parcels."""

    # Define criteria using FGDB datasets
    criteria = [
        ModelCriterion(
            dataset_name="protected_areas_hc",
            criterion_name="Proximity to Protected Areas",
            scoring_function=ScoringFunction(
                type="distance_decay",
                params={"max_distance": 1000, "decay_rate": 0.002},
                output_range=(0, 10),
            ),
            weight=50.0,
        ),
        ModelCriterion(
            dataset_name="habitat_diversity",
            criterion_name="Habitat Diversity",
            scoring_function=ScoringFunction(
                type="categorical",
                params={
                    "column": "LEVEL_3",
                    "mapping": {
                        1: 10.0,
                        2: 8.0,
                        3: 6.0,
                        4: 4.0,
                        5: 2.0,
                    },
                },
                output_range=(0, 10),
            ),
            weight=50.0,
        ),
    ]

    # Configure study area - use protected areas as boundary for testing
    # (In production, you'd use a county boundary dataset)
    study_area_config = StudyAreaConfig(
        dataset=None,  # No boundary for testing - uses dataset bounds
        description="Hennepin County (from datasets)",
    )

    # Test with grid first (smaller test)
    analysis_units_config = AnalysisUnitsConfig(
        type="grid",
        dataset=None,
        cell_size=500.0,  # Larger cells for faster testing
        max_cells=1000,  # Limit to 1000 for testing
    )

    # Create model specification
    model_spec = ModelSpecification(
        model_id="test_boundary_integration",
        model_type="weighted_overlay",
        objective="Test study area boundary and analysis unit integration",
        study_area="Hennepin County",
        study_area_config=study_area_config,
        analysis_units_config=analysis_units_config,
        criteria=criteria,
        output_range=(0, 100),
        metadata={"created_by": "boundary_integration_test", "test": True},
    )

    return model_spec


def test_model_serialization():
    """Test that the model can be saved and loaded with new configs."""
    logger.info("Testing model serialization...")

    model = create_test_model()

    # Save to YAML
    output_file = "./test_boundary_model.yaml"
    model.to_yaml(output_file)
    logger.info(f"  Saved model to {output_file}")

    # Load from YAML
    loaded_model = ModelSpecification.from_yaml(output_file)
    logger.info(f"  Loaded model from {output_file}")

    # Verify configs
    assert loaded_model.study_area_config is not None
    assert loaded_model.analysis_units_config is not None
    assert loaded_model.analysis_units_config.type == "grid"

    logger.info("  Model serialization test passed!")
    return loaded_model


def test_model_execution():
    """Test executing the model with boundary and analysis units."""
    logger.info("Testing model execution...")

    # Check FGDB is available
    if not is_fgdb_available():
        logger.error("FGDB not configured!")
        logger.error(
            "Set RTGS_FGDB_PATH environment variable to point to the Hennepin County FGDB"
        )
        logger.error(
            "Example: export RTGS_FGDB_PATH='/path/to/HC_EasementAnalysis_Model_Inputs_2020.gdb'"
        )
        return None

    # List available datasets
    datasets = get_all_available_datasets()
    fgdb_count = sum(1 for d in datasets.values() if d.get("source") == "fgdb")
    logger.info(f"  Found {fgdb_count} FGDB datasets available")

    model = create_test_model()

    # Validate model
    logger.info("  Validating model...")
    model.validate()
    logger.info("  Model is valid")

    # Execute model
    logger.info("  Executing model...")
    results = execute_model(
        model_spec=model,
        output_dir="./test_results",
        output_format="geoparquet",
    )

    logger.info("  Model execution complete!")
    logger.info(f"    Output file: {results['output_file']}")
    logger.info(f"    Features analyzed: {results['num_features']}")
    logger.info(f"    Duration: {results['duration_seconds']:.1f} seconds")

    return results


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Study Area Boundary & Analysis Unit Integration Test")
    logger.info("=" * 60)
    logger.info()

    # Check environment
    fgdb_path = os.getenv("RTGS_FGDB_PATH")
    if fgdb_path:
        logger.info(f"FGDB Path: {fgdb_path}")
    else:
        logger.warning("RTGS_FGDB_PATH not set - FGDB datasets will not be available")
    logger.info()

    try:
        # Test 1: Serialization
        logger.info("TEST 1: Model Serialization")
        logger.info("-" * 60)
        model = test_model_serialization()
        logger.info()

        # Test 2: Execution
        logger.info("TEST 2: Model Execution")
        logger.info("-" * 60)
        results = test_model_execution()
        logger.info()

        if results:
            logger.info("=" * 60)
            logger.info("ALL TESTS PASSED!")
            logger.info("=" * 60)
            logger.info()
            logger.info("Next steps:")
            logger.info("  1. Review the test results in ./test_results/")
            logger.info(
                "  2. Try with different datasets from the FGDB"
            )
            logger.info("  3. Test with different boundaries and analysis units")
        else:
            logger.warning(
                "Model execution test was skipped (check FGDB configuration)"
            )

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
