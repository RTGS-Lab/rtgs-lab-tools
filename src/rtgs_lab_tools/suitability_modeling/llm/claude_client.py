"""Claude API client for model design."""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Simple Claude API client for suitability model design."""

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
        available_datasets: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Design a suitability model from requirements using Claude.

        Args:
            requirements_text: User's natural language requirements
            available_datasets: Dict of available spatial datasets

        Returns:
            Dict with model specification (can be converted to ModelSpecification)
        """
        prompt = self._build_design_prompt(requirements_text, available_datasets)

        logger.info("Sending model design request to Claude...")

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract JSON from response
            response_text = response.content[0].text
            logger.debug(f"Claude response: {response_text}")

            # Parse JSON from response
            model_spec_dict = self._extract_json(response_text)

            logger.info("Successfully received model specification from Claude")
            return model_spec_dict

        except Exception as e:
            logger.error(f"Failed to design model with Claude: {e}")
            raise

    def _build_design_prompt(
        self,
        requirements: str,
        available_datasets: Dict[str, Any]
    ) -> str:
        """Build the prompt for Claude to design a model.

        Args:
            requirements: User's requirements text
            available_datasets: Available spatial datasets

        Returns:
            Formatted prompt string
        """
        # Format available datasets for the prompt
        datasets_info = []
        for name, info in available_datasets.items():
            datasets_info.append(
                f"- {name}: {info.get('description', 'No description')}"
            )
        datasets_str = "\n".join(datasets_info)

        prompt = f"""You are a GIS expert designing a suitability analysis model.

User Requirements:
{requirements}

Available Datasets from spatial_data module:
{datasets_str}

Your task is to design a weighted overlay suitability model that meets the user's requirements.

Instructions:
1. Analyze the user's objective and criteria
2. Select appropriate datasets from the available list (use ONLY datasets listed above)
3. For each criterion, design a scoring function:
   - "distance_decay": Score based on proximity to features (closer = higher score)
     Parameters: max_distance (meters), decay_rate (default 0.001)
   - "categorical": Map categories to scores
     Parameters: mapping (dict of category: score)

4. Assign weights to each criterion (must sum to 100)
5. Set a clear model_id (snake_case, descriptive)

Return ONLY a JSON object (no markdown, no explanation) with this exact structure:
{{
  "model_id": "descriptive_model_name",
  "model_type": "weighted_overlay",
  "objective": "Clear description of what this model does",
  "study_area": "Hennepin County",
  "criteria": [
    {{
      "dataset_name": "dataset_name_from_available_list",
      "criterion_name": "Human readable criterion name",
      "weight": 35,
      "scoring_function": {{
        "type": "distance_decay",
        "params": {{
          "max_distance": 2000,
          "decay_rate": 0.001
        }},
        "output_range": [0, 10]
      }}
    }}
  ],
  "output_range": [0, 100],
  "metadata": {{
    "created_by": "Claude AI",
    "method": "weighted_overlay"
  }}
}}

Important:
- Use ONLY datasets from the available list
- Weights MUST sum to exactly 100
- Include at least 2 criteria
- scoring_function type must be "distance_decay" or "categorical"
- Return ONLY valid JSON, no additional text"""

        return prompt

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from Claude's response.

        Args:
            text: Response text from Claude

        Returns:
            Parsed JSON dictionary
        """
        # Try to find JSON in the text
        text = text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last line (```json and ```)
            text = "\n".join(lines[1:-1])

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {text}")
            raise ValueError(f"Invalid JSON in Claude response: {e}")
