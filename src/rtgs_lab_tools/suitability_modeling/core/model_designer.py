"""Model designer - creates suitability models from requirements."""

import logging
from pathlib import Path
from typing import Optional

from .model_specification import ModelSpecification
from ..llm.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


def design_model(
    requirements_file: str,
    output_file: Optional[str] = None,
    api_key: Optional[str] = None,
    db_url: Optional[str] = None
) -> ModelSpecification:
    """Design a suitability model from requirements text file.

    This function:
    1. Reads user requirements from text file
    2. Gets available datasets from BOTH PostGIS and spatial_data sources
    3. Uses Claude AI to design a model
    4. Validates the model specification
    5. Optionally saves to YAML file

    Args:
        requirements_file: Path to text file with requirements
        output_file: Optional path to save model YAML (default: {model_id}.yaml)
        api_key: Optional Anthropic API key
        db_url: Optional PostGIS database URL (uses env config if None)

    Returns:
        ModelSpecification object

    Raises:
        FileNotFoundError: If requirements file doesn't exist
        ValueError: If model validation fails

    Example:
        >>> spec = design_model("requirements.txt", "my_model.yaml")
        >>> print(f"Model: {spec.objective}")
        >>> print(f"Criteria: {len(spec.criteria)}")
    """
    # Read requirements file
    requirements_path = Path(requirements_file)
    if not requirements_path.exists():
        raise FileNotFoundError(f"Requirements file not found: {requirements_file}")

    logger.info(f"Reading requirements from: {requirements_file}")
    with open(requirements_path, 'r') as f:
        requirements_text = f.read()

    # Get available datasets from ALL sources (PostGIS + spatial_data)
    logger.info("Loading available datasets from all sources...")
    available_datasets = _get_available_datasets(db_url=db_url)
    logger.info(f"Found {len(available_datasets)} available datasets")

    # Design model using Claude
    logger.info("Designing model with Claude AI...")
    claude = ClaudeClient(api_key=api_key)
    model_spec_dict = claude.design_model(requirements_text, available_datasets)

    # Convert to ModelSpecification object
    model_spec = ModelSpecification.from_dict(model_spec_dict)

    # Validate
    logger.info("Validating model specification...")
    model_spec.validate()
    logger.info(f"✓ Model validated: {model_spec.model_id}")

    # Save to file if requested
    if output_file:
        logger.info(f"Saving model specification to: {output_file}")
        model_spec.to_yaml(output_file)
    else:
        # Default filename
        default_file = f"{model_spec.model_id}.yaml"
        logger.info(f"Saving model specification to: {default_file}")
        model_spec.to_yaml(default_file)

    # Print summary
    _print_model_summary(model_spec)

    return model_spec


def _get_available_datasets(db_url: Optional[str] = None) -> dict:
    """Get available datasets from ALL sources (PostGIS + spatial_data).

    Args:
        db_url: Optional PostGIS database URL

    Returns:
        Dict of dataset_name: dataset_info (includes 'source' field)
    """
    try:
        from .dataset_registry import get_all_available_datasets
        return get_all_available_datasets(db_url=db_url)
    except Exception as e:
        logger.warning(f"Failed to load datasets from unified registry: {e}")
        # FALLBACK FOR TESTING PURPOSES
        return {
            "wildlife_areas": {
                "description": "DNR Wildlife Management Areas",
                "source": "fallback"
            },
            "watersheds": {
                "description": "DNR Level 9 Watersheds",
                "source": "fallback"
            },
            "land_use": {
                "description": "Generalized Land Use 2020",
                "source": "fallback"
            }
        }


def _print_model_summary(spec: ModelSpecification):
    """Print a human-readable summary of the model.

    Args:
        spec: ModelSpecification to summarize
    """
    print("\n" + "=" * 70)
    print("SUITABILITY MODEL SPECIFICATION")
    print("=" * 70)
    print(f"\nModel ID: {spec.model_id}")
    print(f"Objective: {spec.objective}")
    print(f"Study Area: {spec.study_area}")
    print(f"Model Type: {spec.model_type}")
    print(f"\nCriteria ({len(spec.criteria)}):")

    for i, criterion in enumerate(spec.criteria, 1):
        print(f"\n  {i}. {criterion.criterion_name} ({criterion.weight}%)")
        print(f"     Dataset: {criterion.dataset_name}")
        print(f"     Scoring: {criterion.scoring_function.type}")
        if criterion.scoring_function.params:
            for key, value in criterion.scoring_function.params.items():
                print(f"       - {key}: {value}")

    print(f"\nOutput Range: {spec.output_range[0]} - {spec.output_range[1]}")
    print("\n" + "=" * 70)
    print()
