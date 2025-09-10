"""MN Geospatial Commons data extractor."""

import requests
import logging
from typing import Dict, Any
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
        self.session.headers.update({
            'User-Agent': 'RTGS-Lab-Tools Spatial Data Extractor'
        })
        
    def extract(self) -> "gpd.GeoDataFrame":
        """Extract from MN Geospatial Commons.
        
        Returns:
            GeoDataFrame containing the spatial features
        """
        access_method = self.dataset_config.get("access_method", "rest_api")
        
        if access_method == "rest_api":
            return self._extract_from_rest_api()
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
            'where': '1=1',  # Get all features
            'outFields': '*',  # Get all fields
            'f': 'geojson',    # Return as GeoJSON
            'returnGeometry': 'true'
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