"""REST extraction reads the response body as bytes.

gpd.read_file(response.text) failed on a valid 5.76 MB GeoJSON page from the
HennepinCounty_PublicWaterBasins_Clipped FeatureServer (2026-11-04); reading
io.BytesIO(response.content) parsed the same page. These tests pin the bytes path
with a mocked session, so they need no network.
"""

import json
from unittest.mock import MagicMock

import pytest

gpd = pytest.importorskip("geopandas")


def _response(payload):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = payload
    body = json.dumps(payload).encode()
    r.content = body
    # A text attribute that GDAL cannot parse: the extractor must not use it.
    r.text = "not geojson"
    return r


def _feature_collection(n):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"i": i},
                "geometry": {"type": "Point", "coordinates": [-93.4 + i * 1e-4, 45.0]},
            }
            for i in range(n)
        ],
    }


def _extractor(responses):
    from rtgs_lab_tools.spatial_data.sources.mn_geospatial import MNGeospatialExtractor

    ext = MNGeospatialExtractor(
        {
            "source_type": "mn_geospatial",
            "access_method": "rest_api",
            "service_url": "https://example.invalid/arcgis/rest/services/X/FeatureServer/0",
        }
    )
    ext.session = MagicMock()
    ext.session.get.side_effect = responses
    return ext


def test_single_page_reads_bytes():
    ext = _extractor([_response({"count": 3}), _response(_feature_collection(3))])
    gdf = ext.extract()
    assert len(gdf) == 3
    assert str(gdf.crs) == "EPSG:4326"


def test_paginated_reads_bytes():
    pages = [_response({"count": 2001}), _response(_feature_collection(2000)),
             _response(_feature_collection(1))]
    ext = _extractor(pages)
    gdf = ext.extract()
    assert len(gdf) == 2001
