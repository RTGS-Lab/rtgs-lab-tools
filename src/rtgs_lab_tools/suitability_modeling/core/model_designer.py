"""Model designer - creates suitability models from requirements and dataset schemas."""

import logging
from typing import Any, Dict, List, Optional

from .model_specification import ModelSpecification
from ..llm.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


def design_model(
    requirements: str,
    dataset_schemas: List[Dict[str, Any]],
    output_file: Optional[str] = None,
    api_key: Optional[str] = None,
) -> ModelSpecification:
    """Design a suitability model from requirements text and dataset schemas.

    Args:
        requirements: Natural language requirements text
        dataset_schemas: List of dataset schema dicts from get_dataset_schema()
        output_file: Optional path to save model YAML (default: {model_id}.yaml)
        api_key: Optional Anthropic API key

    Returns:
        ModelSpecification object
    """
    logger.info("Designing model with Claude AI...")
    claude = ClaudeClient(api_key=api_key)
    model_spec_dict = claude.design_model(requirements, dataset_schemas)

    # Convert to ModelSpecification object
    model_spec = ModelSpecification.from_dict(model_spec_dict)

    # Validate
    logger.info("Validating model specification...")
    model_spec.validate()
    logger.info(f"Model validated: {model_spec.model_id}")

    # Save to file
    if output_file:
        logger.info(f"Saving model specification to: {output_file}")
        model_spec.to_yaml(output_file)
    else:
        default_file = f"{model_spec.model_id}.yaml"
        logger.info(f"Saving model specification to: {default_file}")
        model_spec.to_yaml(default_file)

    return model_spec


def print_model_summary(spec: ModelSpecification) -> str:
    """Generate a human-readable summary of the model.

    Args:
        spec: ModelSpecification to summarize

    Returns:
        Formatted summary string
    """
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("SUITABILITY MODEL SPECIFICATION")
    lines.append("=" * 70)
    lines.append(f"\nModel ID: {spec.model_id}")
    lines.append(f"Objective: {spec.objective}")
    lines.append(f"Study Area: {spec.study_area}")
    lines.append(f"Model Type: {spec.model_type}")
    lines.append(f"\nCriteria ({len(spec.criteria)}):")

    for i, criterion in enumerate(spec.criteria, 1):
        lines.append(f"\n  {i}. {criterion.criterion_name} ({criterion.weight}%)")
        lines.append(f"     Dataset: {criterion.dataset_name}")
        lines.append(f"     Scoring: {criterion.scoring_function.type}")
        params = criterion.scoring_function.params
        if params:
            if params.max_distance is not None:
                lines.append(f"       - max_distance: {params.max_distance}m")
            if params.decay_rate is not None:
                lines.append(f"       - decay_rate: {params.decay_rate}")
            if params.column is not None:
                lines.append(f"       - column: {params.column}")
            if params.category_mappings:
                mappings = {cm.category: cm.score for cm in params.category_mappings}
                lines.append(f"       - mappings: {mappings}")
            if (criterion.scoring_function.type == "direct_value"
                    and params.column is not None
                    and not params.category_mappings):
                lines.append(f"       (uses raw column values as scores)")

    lines.append(f"\nOutput Range: {spec.output_range[0]} - {spec.output_range[1]}")
    lines.append("")
    lines.append("=" * 70)
    lines.append("")

    return "\n".join(lines)
