"""Claude API client for model design using structured outputs."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _add_additional_properties_false(schema: dict) -> dict:
    """Recursively add 'additionalProperties': false to all object types in a JSON schema.

    The Anthropic structured outputs API requires this on every object type.
    Skips objects that are pure dict types (no 'properties' key) since those
    represent arbitrary key-value mappings.
    """
    if not isinstance(schema, dict):
        return schema

    # Process $defs (Pydantic puts model definitions here)
    if "$defs" in schema:
        for key, defn in schema["$defs"].items():
            schema["$defs"][key] = _add_additional_properties_false(defn)

    # Strip unsupported array constraints (API only allows minItems 0 or 1)
    if schema.get("type") == "array":
        for key in ("minItems", "maxItems"):
            if key in schema and schema[key] > 1:
                del schema[key]
        # Also strip prefixItems (from Tuple types) — use items instead
        if "prefixItems" in schema:
            # Use the first item type as the general items type
            schema["items"] = schema["prefixItems"][0]
            del schema["prefixItems"]

    # If this is an object type with defined properties, lock it down
    if schema.get("type") == "object" and "properties" in schema:
        schema["additionalProperties"] = False
        for prop_name, prop_schema in schema["properties"].items():
            schema["properties"][prop_name] = _add_additional_properties_false(prop_schema)

    # Handle anyOf, allOf, oneOf
    for keyword in ("anyOf", "allOf", "oneOf"):
        if keyword in schema:
            schema[keyword] = [_add_additional_properties_false(s) for s in schema[keyword]]

    # Handle items (arrays)
    if "items" in schema:
        schema["items"] = _add_additional_properties_false(schema["items"])

    return schema


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

        # Get JSON schema from Pydantic model, make it API-compatible
        json_schema = ModelSpecification.model_json_schema()

        # Remove freeform Dict[str, Any] fields that the API can't handle
        if "properties" in json_schema and "metadata" in json_schema["properties"]:
            del json_schema["properties"]["metadata"]
            if "required" in json_schema and "metadata" in json_schema["required"]:
                json_schema["required"].remove("metadata")

        json_schema = _add_additional_properties_false(json_schema)

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            # Use cheaper model
            # Haiku 3.5(?)
            # DeepSeek maybe?? Smaller model??
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
            tools=[{
                "name": "design_model",
                "description": "Output the complete suitability model specification",
                "input_schema": json_schema,
            }],
            tool_choice={"type": "tool", "name": "design_model"},
        )

        # Extract model spec from tool use response
        tool_use_block = next(
            b for b in response.content if b.type == "tool_use"
        )
        model_spec_dict = tool_use_block.input

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
            col_parts = []
            for c in schema.get("columns", []):
                part = c["name"]
                if "unique_values" in c:
                    vals = c["unique_values"]
                    vals_str = ", ".join(str(v) for v in vals[:10])
                    part += f" (values: [{vals_str}])"
                col_parts.append(part)
            cols_str = ", ".join(col_parts[:15])
            if len(col_parts) > 15:
                cols_str += f", ... ({len(col_parts)} total)"
            datasets_info.append(f"- {name} ({geom}, {count:,} features): columns [{cols_str}]")

        datasets_str = "\n".join(datasets_info)

        prompt = f"""You are a GIS expert designing a suitability analysis model.

User Requirements:
{requirements}

Available Datasets:
{datasets_str}

Design a weighted overlay suitability model. Instructions:
1. Select appropriate datasets from the available list (use ONLY dataset names listed above)
2. For each criterion, choose ONE scoring function:
   - "distance_decay": Score based on proximity to features (closer = higher score).
     Parameters: max_distance (meters), decay_rate.
     Use when the dataset has point or polygon features and proximity matters.
   - "categorical": Map specific attribute values to scores via a lookup.
     Parameters: column (attribute name), category_mappings (list of {{category, score}} objects).
     Use when a text/string column needs to be translated to numeric scores.
   - "direct_value": Read a numeric column value directly as the score (no remapping).
     Parameters: column (the numeric attribute column to read).
     Use when the dataset already has a pre-computed numeric score or rating column.
3. IMPORTANT: Look at the actual column values shown in parentheses. Use those exact values
   for categorical mappings. If a column already contains numeric scores, prefer "direct_value".
4. Assign weights to each criterion (MUST sum to exactly 100)
5. Set a clear model_id (snake_case, descriptive)
6. Include at least 2 criteria

Return a complete model specification JSON object."""

        return prompt