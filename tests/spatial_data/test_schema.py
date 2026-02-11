"""Tests for spatial_data schema introspection utilities."""

import pytest
import geopandas as gpd
from shapely.geometry import Point, Polygon


@pytest.fixture
def point_gdf():
    """GeoDataFrame with Point geometry and mixed columns."""
    return gpd.GeoDataFrame(
        {
            "name": ["park_a", "park_b", "park_c"],
            "area_sqm": [1000.0, 2500.0, 500.0],
            "category": ["urban", "suburban", "rural"],
        },
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        crs="EPSG:4326",
    )


@pytest.fixture
def polygon_gdf():
    """GeoDataFrame with Polygon geometry."""
    polys = [
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
    ]
    return gpd.GeoDataFrame(
        {"land_use": ["residential", "commercial"]},
        geometry=polys,
        crs="EPSG:4326",
    )


class TestGetDatasetSchema:
    """Tests for get_dataset_schema()."""

    def test_basic_schema(self, point_gdf):
        from rtgs_lab_tools.spatial_data.core.schema import get_dataset_schema

        schema = get_dataset_schema("parks", point_gdf)
        assert schema["name"] == "parks"
        assert schema["geometry_type"] == "Point"
        assert schema["feature_count"] == 3
        assert len(schema["columns"]) == 3  # name, area_sqm, category

    def test_column_dtypes(self, point_gdf):
        from rtgs_lab_tools.spatial_data.core.schema import get_dataset_schema

        schema = get_dataset_schema("test", point_gdf)
        col_names = [c["name"] for c in schema["columns"]]
        assert "name" in col_names
        assert "area_sqm" in col_names
        assert "geometry" not in col_names  # geometry excluded

    def test_polygon_geometry_type(self, polygon_gdf):
        from rtgs_lab_tools.spatial_data.core.schema import get_dataset_schema

        schema = get_dataset_schema("land", polygon_gdf)
        assert schema["geometry_type"] == "Polygon"

    def test_empty_geodataframe(self):
        from rtgs_lab_tools.spatial_data.core.schema import get_dataset_schema

        empty = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        schema = get_dataset_schema("empty", empty)
        assert schema["feature_count"] == 0
        assert schema["geometry_type"] == "Unknown"


class TestFormatSchemasForLlm:
    """Tests for format_schemas_for_llm()."""

    def test_formatting(self, point_gdf, polygon_gdf):
        from rtgs_lab_tools.spatial_data.core.schema import (
            get_dataset_schema,
            format_schemas_for_llm,
        )

        schemas = [
            get_dataset_schema("parks", point_gdf),
            get_dataset_schema("land_use", polygon_gdf),
        ]

        result = format_schemas_for_llm(schemas)
        assert isinstance(result, str)
        assert "parks" in result
        assert "land_use" in result
        assert "Point" in result
        assert "Polygon" in result
        assert "3 features" in result

    def test_empty_list(self):
        from rtgs_lab_tools.spatial_data.core.schema import format_schemas_for_llm

        result = format_schemas_for_llm([])
        assert result == ""
