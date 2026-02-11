"""Tests for spatial_data extract_from_path and batch extraction functions."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon


@pytest.fixture
def sample_gdf():
    """Create a simple GeoDataFrame for testing."""
    return gpd.GeoDataFrame(
        {"name": ["a", "b", "c"]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_geojson(sample_gdf, tmp_path):
    """Write a sample GeoJSON file and return its path."""
    path = tmp_path / "test_data.geojson"
    sample_gdf.to_file(str(path), driver="GeoJSON")
    return path


@pytest.fixture
def sample_parquet(sample_gdf, tmp_path):
    """Write a sample GeoParquet file and return its path."""
    path = tmp_path / "test_data.parquet"
    sample_gdf.to_parquet(str(path))
    return path


class TestExtractFromPath:
    """Tests for extract_from_path()."""

    def test_extract_geojson(self, sample_geojson):
        from rtgs_lab_tools.spatial_data.core.extractor import extract_from_path

        gdf = extract_from_path(str(sample_geojson))
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 3
        assert str(gdf.crs) == "EPSG:4326"

    def test_extract_parquet(self, sample_parquet):
        from rtgs_lab_tools.spatial_data.core.extractor import extract_from_path

        gdf = extract_from_path(str(sample_parquet))
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 3

    def test_extract_with_target_crs(self, sample_geojson):
        from rtgs_lab_tools.spatial_data.core.extractor import extract_from_path

        gdf = extract_from_path(str(sample_geojson), target_crs="EPSG:3857")
        assert "3857" in str(gdf.crs)

    def test_file_not_found(self):
        from rtgs_lab_tools.spatial_data.core.extractor import extract_from_path

        with pytest.raises(FileNotFoundError):
            extract_from_path("/nonexistent/path.geojson")

    def test_unsupported_format(self, tmp_path):
        from rtgs_lab_tools.spatial_data.core.extractor import extract_from_path

        bad_file = tmp_path / "data.xyz"
        bad_file.write_text("not spatial data")
        with pytest.raises(ValueError, match="Unsupported file format"):
            extract_from_path(str(bad_file))


class TestExtractAllFromDirectory:
    """Tests for extract_all_from_directory()."""

    def test_extract_directory(self, sample_gdf, tmp_path):
        from rtgs_lab_tools.spatial_data.sources.local_file import (
            extract_all_from_directory,
        )

        # Write two files
        (sample_gdf).to_file(str(tmp_path / "dataset_a.geojson"), driver="GeoJSON")
        (sample_gdf).to_parquet(str(tmp_path / "dataset_b.parquet"))

        result = extract_all_from_directory(tmp_path)
        assert isinstance(result, dict)
        assert len(result) == 2
        assert "dataset_a" in result
        assert "dataset_b" in result
        for gdf in result.values():
            assert isinstance(gdf, gpd.GeoDataFrame)
            assert len(gdf) == 3

    def test_empty_directory(self, tmp_path):
        from rtgs_lab_tools.spatial_data.sources.local_file import (
            extract_all_from_directory,
        )

        result = extract_all_from_directory(tmp_path)
        assert result == {}

    def test_nonexistent_directory(self):
        from rtgs_lab_tools.spatial_data.sources.local_file import (
            extract_all_from_directory,
        )

        with pytest.raises(FileNotFoundError):
            extract_all_from_directory(Path("/nonexistent/dir"))
