"""Unified dataset registry for suitability modeling.

This module provides access to spatial datasets through the spatial_data module.
All data comes from either:
- MN Geospatial Commons (public Minnesota data)
- FGDB (Hennepin County private data via RTGS_FGDB_PATH environment variable)
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def get_all_available_datasets() -> Dict[str, Dict]:
    """Get all available datasets from spatial_data module.

    Returns:
        Dictionary of dataset_name: {description, source, ...}
        where 'source' is either 'mn_geospatial' or 'fgdb'

    Example:
        >>> datasets = get_all_available_datasets()
        >>> for name, info in datasets.items():
        ...     print(f"{name}: {info['description']} (from {info['source']})")
    """
    try:
        from ...spatial_data import list_available_datasets

        datasets = list_available_datasets()
        logger.info(f"Loaded {len(datasets)} datasets from spatial_data module")
        return datasets
    except Exception as e:
        logger.error(f"Failed to load datasets from spatial_data: {e}")
        return _get_fallback_datasets()


def _get_fallback_datasets() -> Dict[str, Dict]:
    """Fallback dataset list if spatial_data module fails.

    Returns:
        Minimal dataset dictionary for testing
    """
    return {
        "wildlife_areas": {
            "description": "DNR Wildlife Management Areas (fallback - spatial_data not available)",
            "source": "fallback",
        },
        "land_use": {
            "description": "Land Use Classification (fallback - spatial_data not available)",
            "source": "fallback",
        },
    }


def get_dataset_source(dataset_name: str) -> str:
    """Determine which source a dataset comes from.

    Args:
        dataset_name: Name of the dataset

    Returns:
        'mn_geospatial', 'fgdb', or 'unknown'
    """
    try:
        from ...spatial_data import get_dataset_source as _get_source

        return _get_source(dataset_name)
    except Exception as e:
        logger.warning(f"Failed to get dataset source: {e}")
        return "unknown"


def format_dataset_list_for_llm() -> str:
    """Format dataset list for Claude AI to understand.

    Creates a human-readable list of datasets with descriptions,
    organized by source (FGDB vs MN Geospatial Commons).

    Returns:
        Formatted string describing available datasets
    """
    try:
        from ...spatial_data import format_dataset_list_for_llm as _format

        return _format()
    except Exception as e:
        logger.warning(f"Failed to format dataset list: {e}")
        # Fallback formatting
        datasets = get_all_available_datasets()
        output = ["## Available Datasets", ""]
        for name, info in sorted(datasets.items()):
            desc = info.get("description", "No description")
            source = info.get("source", "unknown")
            output.append(f"- **{name}**: {desc} (source: {source})")
        return "\n".join(output)


def is_fgdb_available() -> bool:
    """Check if FGDB is configured and accessible.

    Returns:
        True if FGDB path is set and the file exists
    """
    try:
        from ...spatial_data import is_fgdb_available as _is_available

        return _is_available()
    except Exception:
        return False
