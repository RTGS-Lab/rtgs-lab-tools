"""MN Geospatial Commons data extractor."""

import logging
from typing import Any, Dict

import requests

from .base import SpatialSourceExtractor

try:
    import geopandas as gpd
except ImportError:
    gpd = None

logger = logging.getLogger(__name__)


class MNGeospatialExtractor(SpatialSourceExtractor):
    """Handles gisdata.mn.gov REST API and direct downloads."""

    def __init__(self, dataset_config: Dict[str, Any], **kwargs):
        """Initialize MN Geospatial extractor.

        Args:
            dataset_config: Configuration dictionary for the dataset
            **kwargs: Additional configuration options
        """
        super().__init__(dataset_config, **kwargs)
        self.session = requests.Session()
        # Set a reasonable timeout and user agent
        self.session.headers.update(
            {"User-Agent": "RTGS-Lab-Tools Spatial Data Extractor"}
        )

    def extract(self) -> "gpd.GeoDataFrame":
        """Extract from MN Geospatial Commons.

        Returns:
            GeoDataFrame containing the spatial features
        """
        access_method = self.dataset_config.get("access_method", "rest_api")

        if access_method == "rest_api":
            return self._extract_from_rest_api()
        elif access_method == "download":
            return self._extract_from_download()
        else:
            raise ValueError(f"Unsupported access method: {access_method}")

    def _extract_from_rest_api(self) -> "gpd.GeoDataFrame":
        """Extract from ArcGIS REST API service.

        Returns:
            GeoDataFrame with extracted features
        """
        service_url = self.dataset_config.get("service_url")
        if not service_url:
            raise ValueError("No service_url provided in dataset configuration")

        # For ArcGIS REST services, we can often read directly with geopandas
        # by appending '/query' and query parameters
        query_url = f"{service_url}/query"

        # Basic query to get all features
        params = {
            "where": "1=1",  # Get all features
            "outFields": "*",  # Get all fields
            "f": "geojson",  # Return as GeoJSON
            "returnGeometry": "true",
        }

        try:
            self.logger.info(f"Extracting data from: {query_url}")

            # Make the request
            response = self.session.get(query_url, params=params, timeout=30)
            response.raise_for_status()

            # Read directly from the response
            gdf = gpd.read_file(response.text)

            self.logger.info(f"Successfully extracted {len(gdf)} features")

            # Validate and standardize
            if not self.validate_spatial_integrity(gdf):
                self.logger.warning("Spatial integrity validation failed")

            gdf = self.standardize_crs(gdf)

            return gdf

        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch data from {query_url}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to process spatial data: {e}")
            raise

    def _extract_from_download(self) -> "gpd.GeoDataFrame":
        """Extract from direct file download (GeoPackage, Shapefile, etc.).

        Returns:
            GeoDataFrame with extracted features
        """
        import os
        import tempfile
        import zipfile

        download_url = self.dataset_config.get("download_url")
        if not download_url:
            raise ValueError("No download_url provided in dataset configuration")

        try:
            self.logger.info(f"Downloading data from: {download_url}")

            # Download the file
            response = self.session.get(download_url, timeout=60)
            response.raise_for_status()

            self.logger.info(f"Downloaded {len(response.content)} bytes")

            # Handle zipped files
            if download_url.endswith(".zip"):
                return self._extract_from_zip(response.content)
            else:
                # Direct file (GeoPackage, Shapefile, etc.)
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(response.content)
                    temp_path = temp_file.name

                try:
                    gdf = gpd.read_file(temp_path)
                    return self._process_extracted_data(gdf)
                finally:
                    os.unlink(temp_path)

        except Exception as e:
            self.logger.error(f"Failed to download from {download_url}: {e}")
            raise

    def _extract_from_zip(self, zip_content: bytes) -> "gpd.GeoDataFrame":
        """Extract spatial data from zip file content.

        Args:
            zip_content: Raw zip file bytes

        Returns:
            GeoDataFrame with extracted features
        """
        import os
        import tempfile
        import zipfile

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
            temp_zip.write(zip_content)
            temp_zip_path = temp_zip.name

        try:
            with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
                file_list = zip_ref.namelist()
                self.logger.debug(f"Files in zip: {file_list}")

                # Look for spatial files (priority order)
                # Vector formats first, then raster formats
                spatial_extensions = [
                    ".gpkg",
                    ".shp",
                    ".geojson",
                    ".gml",
                    ".asc",
                    ".grid",
                ]
                spatial_file = None

                for ext in spatial_extensions:
                    matching_files = [f for f in file_list if f.endswith(ext)]
                    if matching_files:
                        spatial_file = matching_files[0]  # Take first match
                        break

                # Special handling for AAIGRID format (ASCII Grid)
                if not spatial_file:
                    # Look for typical AAIGRID files
                    aaigrid_files = [
                        f
                        for f in file_list
                        if any(
                            keyword in f.lower() for keyword in ["grid", "asc", "ascii"]
                        )
                    ]
                    if aaigrid_files:
                        spatial_file = aaigrid_files[0]

                if not spatial_file:
                    raise ValueError(
                        f"No spatial files found in zip. Files: {file_list}"
                    )

                self.logger.info(f"Found spatial file: {spatial_file}")

                # Extract and read
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_ref.extract(spatial_file, temp_dir)
                    spatial_path = os.path.join(temp_dir, spatial_file)

                    # Handle raster files differently
                    if any(
                        ext in spatial_file.lower() for ext in [".asc", "grid", "ascii"]
                    ):
                        gdf = self._read_raster_as_geodataframe(spatial_path)
                    else:
                        gdf = gpd.read_file(spatial_path)

                    return self._process_extracted_data(gdf)

        finally:
            os.unlink(temp_zip_path)

    def _read_raster_as_geodataframe(self, raster_path: str) -> "gpd.GeoDataFrame":
        """Read raster file and convert to GeoDataFrame with grid cell polygons.

        Args:
            raster_path: Path to the raster file

        Returns:
            GeoDataFrame with raster cells as polygons
        """
        try:
            import numpy as np
            import rasterio
            from shapely.geometry import box
        except ImportError as e:
            raise ImportError(f"rasterio is required for raster processing: {e}")

        try:
            with rasterio.open(raster_path) as src:
                # Read the data
                data = src.read(1)  # Read first band
                transform = src.transform
                crs = src.crs

                self.logger.info(f"Raster shape: {data.shape}, CRS: {crs}")

                # Get non-null cells
                rows, cols = np.where(~np.isnan(data) & (data != src.nodata))

                if len(rows) == 0:
                    self.logger.warning("No valid data found in raster")
                    return gpd.GeoDataFrame()

                # Convert pixel coordinates to geographic coordinates
                geometries = []
                values = []

                for row, col in zip(rows, cols):
                    # Get pixel bounds
                    left, top = rasterio.transform.xy(transform, row, col, offset="ul")
                    right, bottom = rasterio.transform.xy(
                        transform, row + 1, col + 1, offset="ul"
                    )

                    # Create polygon for this cell
                    geom = box(left, bottom, right, top)
                    geometries.append(geom)
                    values.append(data[row, col])

                # Create GeoDataFrame
                gdf = gpd.GeoDataFrame(
                    {"value": values, "geometry": geometries}, crs=crs
                )

                self.logger.info(f"Converted raster to {len(gdf)} polygon features")
                return gdf

        except Exception as e:
            self.logger.error(f"Failed to read raster file {raster_path}: {e}")
            raise

    def _process_extracted_data(self, gdf: "gpd.GeoDataFrame") -> "gpd.GeoDataFrame":
        """Process extracted GeoDataFrame with validation and standardization.

        Args:
            gdf: Raw extracted GeoDataFrame

        Returns:
            Processed and validated GeoDataFrame
        """
        self.logger.info(f"Processing {len(gdf)} extracted features")

        # Validate and standardize
        if not self.validate_spatial_integrity(gdf):
            self.logger.warning("Spatial integrity validation failed")

        gdf = self.standardize_crs(gdf)

        # Log summary
        self.logger.info(f"Successfully processed {len(gdf)} features")
        self.logger.info(f"CRS: {gdf.crs}")
        self.logger.info(f"Geometry types: {gdf.geom_type.value_counts().to_dict()}")

        return gdf
