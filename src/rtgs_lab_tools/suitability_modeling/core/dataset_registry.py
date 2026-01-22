"""Unified dataset registry combining PostGIS and spatial_data sources.

This module provides a single interface to query datasets from both:
- PostGIS database (private Hennepin County data)
- spatial_data module (public Minnesota data)
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def get_all_available_datasets(db_url: Optional[str] = None) -> Dict[str, Dict]:
    """Get all available datasets from both PostGIS and spatial_data sources.

    Args:
        db_url: Optional PostGIS database URL. If None, uses environment config.

    Returns:
        Dictionary of dataset_name: {description, source, ...}
        where 'source' is either 'postgis' or 'spatial_data'

    Example:
        >>> datasets = get_all_available_datasets()
        >>> for name, info in datasets.items():
        ...     print(f"{name}: {info['description']} (from {info['source']})")
    """
    all_datasets = {}

    # 1. Try to load PostGIS datasets
    try:
        from .postgis_data_manager import PostGISDataManager

        manager = PostGISDataManager(db_url=db_url)
        if manager.is_available():
            postgis_datasets = manager.list_available_datasets()
            all_datasets.update(postgis_datasets)
            logger.info(f"Loaded {len(postgis_datasets)} datasets from PostGIS")
        else:
            logger.warning("PostGIS database not available")
    except Exception as e:
        logger.warning(f"Failed to load PostGIS datasets: {e}")

    # 2. Try to load spatial_data datasets
    try:
        from ...spatial_data.registry import list_available_datasets

        spatial_data_datasets = list_available_datasets()

        # Mark source and add to combined registry
        for name, info in spatial_data_datasets.items():
            # Avoid overwriting PostGIS datasets with same name
            if name not in all_datasets:
                info['source'] = 'spatial_data'
                all_datasets[name] = info

        logger.info(f"Loaded {len(spatial_data_datasets)} datasets from spatial_data module")
    except Exception as e:
        logger.warning(f"Failed to load spatial_data datasets: {e}")

    if not all_datasets:
        logger.error("No datasets available from any source!")
        # Provide minimal fallback
        all_datasets = _get_fallback_datasets()

    logger.info(f"Total datasets available: {len(all_datasets)}")
    return all_datasets


def _get_fallback_datasets() -> Dict[str, Dict]:
    """Fallback dataset list if both sources fail.

    Returns:
        Minimal dataset dictionary for testing
    """
    return {
        "wildlife_areas": {
            "description": "DNR Wildlife Management Areas (placeholder - database not available)",
            "source": "fallback"
        },
        "land_use": {
            "description": "Land Use Classification (placeholder - database not available)",
            "source": "fallback"
        }
    }


def get_dataset_source(dataset_name: str, db_url: Optional[str] = None) -> str:
    """Determine which source a dataset comes from.

    Args:
        dataset_name: Name of the dataset
        db_url: Optional PostGIS database URL

    Returns:
        'postgis', 'spatial_data', or 'unknown'
    """
    datasets = get_all_available_datasets(db_url=db_url)

    if dataset_name in datasets:
        return datasets[dataset_name].get('source', 'unknown')

    return 'unknown'


def format_dataset_list_for_llm(db_url: Optional[str] = None) -> str:
    """Format dataset list for Claude AI to understand.

    Creates a human-readable list of datasets with descriptions,
    organized by source (PostGIS vs spatial_data).

    Args:
        db_url: Optional PostGIS database URL

    Returns:
        Formatted string describing available datasets
    """
    datasets = get_all_available_datasets(db_url=db_url)

    # Group by source
    postgis_datasets = {k: v for k, v in datasets.items() if v.get('source') == 'postgis'}
    spatial_data_datasets = {k: v for k, v in datasets.items() if v.get('source') == 'spatial_data'}

    output = []

    if postgis_datasets:
        output.append("## Private Hennepin County Datasets (PostGIS Database)")
        output.append("")
        for name, info in sorted(postgis_datasets.items()):
            desc = info.get('description', 'No description')
            feature_count = info.get('feature_count', 'Unknown')
            geom_type = info.get('geometry_type', 'Unknown')
            output.append(f"- **{name}**: {desc}")
            output.append(f"  - Features: {feature_count}, Type: {geom_type}")
            if info.get('columns'):
                output.append(f"  - Columns: {', '.join(info['columns'][:10])}")
        output.append("")

    if spatial_data_datasets:
        output.append("## Public Minnesota Datasets (spatial_data module)")
        output.append("")
        for name, info in sorted(spatial_data_datasets.items()):
            desc = info.get('description', 'No description')
            output.append(f"- **{name}**: {desc}")
        output.append("")

    output.append(f"**Total Datasets Available: {len(datasets)}**")
    output.append(f"- PostGIS: {len(postgis_datasets)}")
    output.append(f"- spatial_data: {len(spatial_data_datasets)}")

    return "\n".join(output)
