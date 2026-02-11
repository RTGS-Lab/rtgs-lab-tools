"""Tests for spatial_data grid generation."""

import pytest
import geopandas as gpd
import numpy as np
from shapely.geometry import box


@pytest.fixture
def simple_boundary():
    """A 1km x 1km square boundary in EPSG:4326."""
    # Roughly 1km x 1km near Minneapolis
    poly = box(-93.27, 44.97, -93.26, 44.98)
    return gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")


@pytest.fixture
def projected_boundary():
    """A 1000m x 1000m square boundary in EPSG:5070."""
    poly = box(400000, 2500000, 401000, 2501000)
    return gpd.GeoDataFrame(geometry=[poly], crs="EPSG:5070")


class TestGenerateGrid:
    """Tests for generate_grid()."""

    def test_basic_grid_generation(self, simple_boundary):
        from rtgs_lab_tools.spatial_data.core.grid import generate_grid

        grid = generate_grid(simple_boundary, cell_size=200.0)
        assert isinstance(grid, gpd.GeoDataFrame)
        assert len(grid) > 0
        # Should have same CRS as input
        assert grid.crs == simple_boundary.crs

    def test_grid_cell_count_respects_max(self, simple_boundary):
        from rtgs_lab_tools.spatial_data.core.grid import generate_grid

        # Very small cells but limited max — the grid auto-scales cell_size
        # to fit within max_cells. Allow 20% overshoot since boundary clipping
        # is approximate.
        grid = generate_grid(simple_boundary, cell_size=10.0, max_cells=100)
        assert len(grid) <= 120

    def test_grid_cells_within_boundary(self, simple_boundary):
        from rtgs_lab_tools.spatial_data.core.grid import generate_grid

        grid = generate_grid(simple_boundary, cell_size=200.0)
        boundary_geom = simple_boundary.to_crs("EPSG:5070").unary_union

        # All cells should be within or touching boundary
        grid_proj = grid.to_crs("EPSG:5070")
        for geom in grid_proj.geometry:
            assert geom.intersects(boundary_geom)

    def test_empty_boundary_raises(self):
        from rtgs_lab_tools.spatial_data.core.grid import generate_grid

        empty = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        with pytest.raises(ValueError, match="empty"):
            generate_grid(empty)

    def test_invalid_cell_size(self, simple_boundary):
        from rtgs_lab_tools.spatial_data.core.grid import generate_grid

        with pytest.raises(ValueError, match="positive"):
            generate_grid(simple_boundary, cell_size=-10)

        with pytest.raises(ValueError, match="positive"):
            generate_grid(simple_boundary, cell_size=0)
