"""Grid generation utilities for spatial analysis."""

import logging
from typing import Optional

import geopandas as gpd
import numpy as np
from shapely.geometry import box

logger = logging.getLogger(__name__)


def generate_grid(
    boundary: gpd.GeoDataFrame,
    cell_size: float = 100.0,
    max_cells: int = 50000,
) -> gpd.GeoDataFrame:
    """Generate a regular grid clipped to a boundary polygon.

    Projects to an equal-area CRS (EPSG:5070 - NAD83 / Conus Albers) for
    accurate meter-based cell sizing, creates the grid, clips to boundary,
    then reprojects back to the boundary's original CRS.

    Args:
        boundary: GeoDataFrame with boundary polygon(s)
        cell_size: Grid cell size in meters (default: 100.0)
        max_cells: Maximum number of cells to generate (default: 50000)

    Returns:
        GeoDataFrame with grid cell polygons clipped to boundary

    Raises:
        ValueError: If boundary is empty or cell_size is invalid
    """
    if boundary.empty:
        raise ValueError("Boundary GeoDataFrame is empty")

    if cell_size <= 0:
        raise ValueError(f"cell_size must be positive, got {cell_size}")

    original_crs = boundary.crs

    # Project to equal-area CRS for accurate meter-based cells
    projected_crs = "EPSG:5070"
    boundary_proj = boundary.to_crs(projected_crs)

    # Get the union of all boundary geometries
    boundary_geom = boundary_proj.unary_union
    minx, miny, maxx, maxy = boundary_geom.bounds

    logger.info(
        f"Grid bounds (projected): [{minx:.0f}, {miny:.0f}, {maxx:.0f}, {maxy:.0f}]"
    )
    logger.info(f"Cell size: {cell_size}m")

    # Calculate grid dimensions
    x_coords = np.arange(minx, maxx, cell_size)
    y_coords = np.arange(miny, maxy, cell_size)
    total_possible = len(x_coords) * len(y_coords)

    if total_possible > max_cells:
        logger.warning(
            f"Grid would have {total_possible} cells, exceeds max_cells={max_cells}. "
            f"Increasing cell size to fit."
        )
        # Scale cell size to fit within max_cells
        area = (maxx - minx) * (maxy - miny)
        cell_size = np.sqrt(area / max_cells)
        x_coords = np.arange(minx, maxx, cell_size)
        y_coords = np.arange(miny, maxy, cell_size)
        logger.info(f"Adjusted cell size to {cell_size:.1f}m")

    # Create grid cells clipped to boundary
    geometries = []
    for x in x_coords:
        for y in y_coords:
            cell = box(x, y, x + cell_size, y + cell_size)
            if cell.intersects(boundary_geom):
                clipped = cell.intersection(boundary_geom)
                if not clipped.is_empty:
                    geometries.append(clipped)

    logger.info(f"Generated {len(geometries)} grid cells")

    # Create GeoDataFrame in projected CRS, then reproject back
    grid_gdf = gpd.GeoDataFrame(geometry=geometries, crs=projected_crs)

    if original_crs is not None:
        grid_gdf = grid_gdf.to_crs(original_crs)

    return grid_gdf
