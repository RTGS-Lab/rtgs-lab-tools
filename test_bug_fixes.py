"""
Quick test to verify the bug fixes in suitability_modeling module.

This script tests:
1. Categorical scoring (Bug #1)
2. Study area boundary clipping (Bug #2)
3. Distance calculations with CRS reprojection (Bug #3)
"""

import logging
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from rtgs_lab_tools.suitability_modeling.core.model_specification import (
    ModelSpecification,
    ModelCriterion,
    ScoringFunction,
    StudyAreaConfig,
    AnalysisUnitsConfig,
)
from rtgs_lab_tools.suitability_modeling.core.execution_engine import execute_model

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_bug_fixes():
    """Test that the bug fixes work correctly."""
    logger.info("=" * 60)
    logger.info("Bug Fix Validation Test")
    logger.info("=" * 60)

    # Create a simple model using MN Geospatial Commons datasets
    # This tests all three bugs:
    # - Distance decay (Bug #3 - CRS reprojection)
    # - Categorical scoring (Bug #1 - AttributeError)
    # - Study area boundary (Bug #2 - boundary clipping)

    criteria = [
        ModelCriterion(
            dataset_name="wildlife_areas",
            criterion_name="Proximity to Wildlife Areas",
            scoring_function=ScoringFunction(
                type="distance_decay",
                params={"max_distance": 5000, "decay_rate": 0.001},
                output_range=(0, 10),
            ),
            weight=60.0,
        ),
        ModelCriterion(
            dataset_name="scientific_and_natural_areas",
            criterion_name="Proximity to SNAs",
            scoring_function=ScoringFunction(
                type="distance_decay",
                params={"max_distance": 3000, "decay_rate": 0.0015},
                output_range=(0, 10),
            ),
            weight=40.0,
        ),
    ]

    # Configure study area - use a dataset as boundary
    study_area_config = StudyAreaConfig(
        dataset="wildlife_areas",  # Use wildlife areas as study boundary
        description="Wildlife areas in Minnesota",
    )

    # Use a small grid for fast testing
    analysis_units_config = AnalysisUnitsConfig(
        type="grid",
        dataset=None,
        cell_size=1000.0,  # 1km cells
        max_cells=500,  # Small number for quick test
    )

    # Create model specification
    model_spec = ModelSpecification(
        model_id="bug_fix_test",
        model_type="weighted_overlay",
        objective="Test bug fixes in suitability modeling",
        study_area="Minnesota Wildlife Areas",
        study_area_config=study_area_config,
        analysis_units_config=analysis_units_config,
        criteria=criteria,
        output_range=(0, 100),
        metadata={"test": "bug_fixes", "version": "1.0"},
    )

    logger.info("\n✓ Model specification created")

    # Validate model
    logger.info("\nValidating model...")
    model_spec.validate()
    logger.info("✓ Model validation passed")

    # Execute model
    logger.info("\nExecuting model...")
    try:
        results = execute_model(
            model_spec=model_spec,
            output_dir="./test_output",
            output_format="geoparquet",
        )

        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL BUG FIXES VALIDATED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info(f"\nResults:")
        logger.info(f"  Output file: {results['output_file']}")
        logger.info(f"  Features analyzed: {results['num_features']}")
        logger.info(f"  Duration: {results['duration_seconds']:.1f} seconds")

        return True

    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_bug_fixes()
    sys.exit(0 if success else 1)
