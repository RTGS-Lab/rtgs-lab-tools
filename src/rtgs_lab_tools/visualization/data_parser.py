"""Data parsing utilities for sensor visualization."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

import pandas as pd

from ..core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def parse_sensor_messages(df: pd.DataFrame) -> pd.DataFrame:
    """Parse JSON messages in sensor data DataFrame.

    Args:
        df: DataFrame with 'message' column containing JSON strings

    Returns:
        DataFrame with parsed message data and extracted parameters

    Raises:
        ValidationError: If DataFrame doesn't have required columns
    """
    if "message" not in df.columns:
        raise ValidationError("DataFrame must have 'message' column")

    parsed_data = []

    for _, row in df.iterrows():
        try:
            parsed_message = json.loads(row["message"])

            # Create new row with parsed data
            new_row = row.to_dict()
            new_row["parsed_message"] = parsed_message

            # Extract timestamp
            if "publish_time" in row:
                if isinstance(row["publish_time"], str):
                    new_row["timestamp"] = pd.to_datetime(row["publish_time"])
                else:
                    new_row["timestamp"] = row["publish_time"]

            parsed_data.append(new_row)

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                f"Failed to parse message for row {row.get('id', 'unknown')}: {e}"
            )
            continue

    if not parsed_data:
        logger.warning("No valid JSON messages found in data")
        return pd.DataFrame()

    return pd.DataFrame(parsed_data)


def extract_parameter_from_json(data: Dict[str, Any], param_path: str) -> Any:
    """Extract a parameter value from nested JSON data using dot notation.

    Args:
        data: Parsed JSON data
        param_path: Parameter path like "Data.Devices.0.Temperature"

    Returns:
        Parameter value or None if not found
    """
    try:
        current = data
        for part in param_path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index] if 0 <= index < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None

            if current is None:
                return None

        return current
    except Exception as e:
        logger.debug(f"Failed to extract parameter {param_path}: {e}")
        return None


def get_available_parameters(
    df: pd.DataFrame, max_depth: int = 5
) -> Dict[str, Set[str]]:
    """Get all available parameters from parsed sensor data.

    Args:
        df: DataFrame with parsed sensor messages
        max_depth: Maximum depth to explore in JSON structure

    Returns:
        Dictionary mapping node_ids to sets of available parameters
    """
    parameters_by_node = {}

    for _, row in df.iterrows():
        node_id = row.get("node_id", "unknown")

        if "parsed_message" in row and row["parsed_message"]:
            params = _extract_all_parameters(row["parsed_message"], max_depth=max_depth)

            if node_id not in parameters_by_node:
                parameters_by_node[node_id] = set()

            parameters_by_node[node_id].update(params)

    return parameters_by_node


def _extract_all_parameters(
    data: Union[Dict, List, Any], prefix: str = "", max_depth: int = 5
) -> Set[str]:
    """Recursively extract all parameter paths from JSON data.

    Args:
        data: JSON data to explore
        prefix: Current parameter path prefix
        max_depth: Maximum recursion depth

    Returns:
        Set of all parameter paths
    """
    if max_depth <= 0:
        return set()

    parameters = set()

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key

            # Add current path if it has a simple value
            if isinstance(value, (int, float, str, bool)):
                parameters.add(current_path)

            # Recurse into nested structures
            if isinstance(value, (dict, list)):
                nested_params = _extract_all_parameters(
                    value, current_path, max_depth - 1
                )
                parameters.update(nested_params)

    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{prefix}.{i}" if prefix else str(i)

            # Add current path if it has a simple value
            if isinstance(item, (int, float, str, bool)):
                parameters.add(current_path)

            # Recurse into nested structures
            if isinstance(item, (dict, list)):
                nested_params = _extract_all_parameters(
                    item, current_path, max_depth - 1
                )
                parameters.update(nested_params)

    return parameters


def extract_time_series_data(
    df: pd.DataFrame, parameter_path: str, node_ids: Optional[List[str]] = None
) -> Dict[str, pd.DataFrame]:
    """Extract time series data for a specific parameter.

    Args:
        df: DataFrame with parsed sensor data
        parameter_path: Parameter path to extract
        node_ids: Optional list of node IDs to filter

    Returns:
        Dictionary mapping node_ids to DataFrames with time series data
    """
    if "parsed_message" not in df.columns:
        raise ValidationError(
            "DataFrame must have 'parsed_message' column. Run parse_sensor_messages() first."
        )

    time_series_by_node = {}

    # Filter by node IDs if specified
    if node_ids:
        df = df[df["node_id"].isin(node_ids)]

    for node_id in df["node_id"].unique():
        node_data = df[df["node_id"] == node_id].copy()

        # Extract parameter values
        values = []
        timestamps = []

        for _, row in node_data.iterrows():
            if "parsed_message" in row and row["parsed_message"]:
                value = extract_parameter_from_json(
                    row["parsed_message"], parameter_path
                )

                if value is not None:
                    try:
                        # Convert to numeric if possible
                        numeric_value = float(value)
                        values.append(numeric_value)
                        timestamps.append(row["timestamp"])
                    except (ValueError, TypeError):
                        logger.debug(f"Non-numeric value for {parameter_path}: {value}")
                        continue

        if values:
            time_series_df = pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "value": values,
                    "parameter": parameter_path,
                    "node_id": node_id,
                }
            )
            time_series_by_node[node_id] = time_series_df.sort_values("timestamp")

    return time_series_by_node
