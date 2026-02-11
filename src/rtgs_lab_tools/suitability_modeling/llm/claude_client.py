"""Claude API client for model design using structured outputs."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Claude API client that uses structured outputs for suitability model design."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: pip install anthropic"
            )

    def design_model(
        self,
        requirements_text: str,
        dataset_schemas: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Design a suitability model from requirements using Claude structured outputs.

        Args:
            requirements_text: User's natural language requirements
            dataset_schemas: List of dataset schema dicts from get_dataset_schema()

        Returns:
            Dict with model specification (can be passed to ModelSpecification.from_dict())
        """
        from ..core.model_specification import ModelSpecification

        prompt = self._build_design_prompt(requirements_text, dataset_schemas)

        logger.info("Sending model design request to Claude...")

        # Get JSON schema from Pydantic model
        json_schema = ModelSpecification.model_json_schema()

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "ModelSpecification",
                        "schema": json_schema,
                    },
                }
            },
        )

        # Parse structured response
        response_text = response.content[0].text
        model_spec_dict = json.loads(response_text)

        # Validate through Pydantic
        spec = ModelSpecification.model_validate(model_spec_dict)
        logger.info(f"Successfully designed model: {spec.model_id}")

        return spec.to_dict()

    def _build_design_prompt(
        self,
        requirements: str,
        dataset_schemas: List[Dict[str, Any]],
    ) -> str:
        """Build the prompt for Claude to design a model.

        Args:
            requirements: User's requirements text
            dataset_schemas: Dataset schema dicts with name, geometry_type, columns, feature_count

        Returns:
            Formatted prompt string
        """
        # Format dataset info
        datasets_info = []
        for schema in dataset_schemas:
            name = schema["name"]
            geom = schema["geometry_type"]
            count = schema["feature_count"]
            cols = [c["name"] for c in schema.get("columns", [])]
            cols_str = ", ".join(cols[:15])
            if len(cols) > 15:
                cols_str += f", ... ({len(cols)} total)"
            datasets_info.append(f"- {name} ({geom}, {count:,} features): columns [{cols_str}]")

        datasets_str = "\n".join(datasets_info)

        prompt = f"""You are a GIS expert designing a suitability analysis model.

User Requirements:
{requirements}

Available Datasets:
{datasets_str}

Design a weighted overlay suitability model. Instructions:
1. Select appropriate datasets from the available list (use ONLY dataset names listed above)
2. For each criterion, design a scoring function:
   - "distance_decay": Score based on proximity to features (closer = higher)
     Parameters: max_distance (meters), decay_rate (default 0.001)
   - "categorical": Map attribute values to scores
     Parameters: column (attribute name), mapping (dict of value: score)
3. Assign weights to each criterion (MUST sum to exactly 100)
4. Set a clear model_id (snake_case, descriptive)
5. Include at least 2 criteria

Return a complete model specification JSON object."""

        return prompt