"""Schema introspection utilities for LLM-assisted analysis."""

import logging
from typing import Any, Dict, List

import geopandas as gpd

logger = logging.getLogger(__name__)


def get_dataset_schema(name: str, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    """Extract schema information from a GeoDataFrame for LLM consumption.

    Args:
        name: Human-readable name for this dataset
        gdf: GeoDataFrame to introspect

    Returns:
        Dictionary with schema information:
        - name: Dataset name
        - geometry_type: Dominant geometry type (e.g. "Polygon", "Point")
        - columns: List of {name, dtype} dicts for non-geometry columns
        - feature_count: Number of features
    """
    # Get dominant geometry type
    if gdf.empty:
        geometry_type = "Unknown"
    else:
        geometry_type = gdf.geometry.geom_type.mode().iloc[0]

    # Get column info (exclude geometry column)
    columns = []
    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        col_info = {
            "name": col,
            "dtype": str(gdf[col].dtype),
        }
        # Include unique values for columns with few distinct values
        # (most useful for categorical scoring)
        try:
            nunique = gdf[col].nunique()
            if nunique <= 20:
                unique_vals = sorted(
                    [v for v in gdf[col].dropna().unique().tolist()],
                    key=lambda x: str(x),
                )
                col_info["unique_values"] = unique_vals
        except (TypeError, ValueError):
            pass
        columns.append(col_info)

    return {
        "name": name,
        "geometry_type": geometry_type,
        "columns": columns,
        "feature_count": len(gdf),
    }


def format_schemas_for_llm(schemas: List[Dict[str, Any]]) -> str:
    """Format dataset schemas into a minimal string for LLM prompts.

    Args:
        schemas: List of schema dicts from get_dataset_schema()

    Returns:
        Formatted string describing available datasets
    """
    lines = []
    for schema in schemas:
        name = schema["name"]
        geom = schema["geometry_type"]
        count = schema["feature_count"]
        cols = [c["name"] for c in schema["columns"]]
        cols_str = ", ".join(cols[:15])
        if len(cols) > 15:
            cols_str += f", ... ({len(cols)} total)"

        lines.append(f"- {name} ({geom}, {count:,} features)")
        lines.append(f"  Columns: {cols_str}")

    return "\n".join(lines)
