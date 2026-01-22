"""Dataset registry for MN Geospatial Commons and other spatial data sources."""

from typing import Any, Dict, Optional

# Start with just MN Geospatial Commons datasets for MVP
MN_GEOSPATIAL_DATASETS = {
    "wildlife_areas": {
        "description": "DNR Wildlife Management Areas",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/bdry-dnr-wildlife-mgmt-areas-pub",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/bdry_dnr_wildlife_mgmt_areas_pub/gpkg_bdry_dnr_wildlife_mgmt_areas_pub.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "yearly",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
        "expected_features": 1731,  # Actual count from test
    },
    "groundwater_recharge": {
        "description": "Mean annual potential groundwater recharge rates from 1996-2010 for Minnesota",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/id/dataset/geos-gw-recharge-1996-2010-mean",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_pca/geos_gw_recharge_1996_2010_mean/aaigrid_geos_gw_recharge_1996_2010_mean.zip",
        "access_method": "download",
        "file_format": "aaigrid",
        "update_frequency": "static",
        "spatial_type": "raster",
        "model_critical": True,
        "coordinate_system": "unknown",  # Will be determined during extraction
        "data_source": "U.S. Geological Survey",
        "temporal_coverage": "1996-2010",
        "units": "inches/year",
    },
    "scientific_and_natural_areas": {
        "description": "DNR Scientific and Natural Areas",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/bdry-scientific-and-nat-areas",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/bdry_scientific_and_nat_areas/gpkg_bdry_scientific_and_nat_areas.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "yearly",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
        "expected_features": 237,  # Actual count from test
        "layer_name": "scientific_and_natural_area_boundaries",  # Specific layer in multi-layer GeoPackage
    },
    "TNC_lands": {
        "description": "The Nature Conservancy lands and waters in Minnesota, North Dakota, & South Dakota",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://geospatial.tnc.org/datasets/53441934d168434e8ff255bda7fd1e3e_1/explore",
        "service_url": "https://services.arcgis.com/F7DSX1DSNSiWmOqh/arcgis/rest/services/TNC_Lands_MNDK_Public_Layer_2024/FeatureServer/1",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "yearly",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:4326",  # Will be determined during extraction
        "expected_features": 383,  # Actual count from test
    },
    "aquatic_areas": {
        "description": "DNR Fisheries Acquisition - Aquatic Management Areas",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/plan-mndnr-fisheries-acquisition",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/plan_mndnr_fisheries_acquisition/gpkg_plan_mndnr_fisheries_acquisition.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "yearly",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
    },
    "MBS_sites": {
        "description": "Minnesota Biological Survey (MBS) - Sites of Biodiversity Significance",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/biota-mcbs-sites-of-biodiversity",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/biota_mcbs_sites_of_biodiversity/gpkg_biota_mcbs_sites_of_biodiversity.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "yearly",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
    },
    "WAN": {
        "description": "WAN (Wildlife Action Network) - Minnesota Wildlife Action Plan Network",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/env-mnwap-wildlife-action-netwrk",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/env_mnwap_wildlife_action_netwrk/gpkg_env_mnwap_wildlife_action_netwrk.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "yearly",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
    },
    "land_use": {
        "description": "Generalized Land Use 2020 - Metropolitan Council Regional Land Use",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/us-mn-state-metc-plan-generl-lnduse2020",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_metc/plan_generl_lnduse2020/gpkg_plan_generl_lnduse2020.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
        "temporal_coverage": "2020",
    },
    "cemeteries": {
        "description": "Cemeteries - Regional Parcels Dataset (filtered)",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/us-mn-state-metrogis-plan-regional-parcels",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_metrogis/plan_regional_parcels/gpkg_plan_regional_parcels.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "quarterly",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
        "layer_names": ["ParcelsAnoka", "ParcelsCarver", "ParcelsDakota", "ParcelsHennepin", "ParcelsRamsey", "ParcelsScott", "ParcelsWashington"],  # Load all county parcel layers
        "attribute_filter": {
            "description": "Extract only cemetery parcels",
            "columns": ["XUSECLASS1", "XUSECLASS2", "XUSECLASS3", "XUSECLASS4"],
            "values": ["PRIVATE CEMETERIES", "PUBLIC CEMETERIES"],
            "match_type": "any"  # Match if ANY column contains ANY of the values
        },
    },
    "watersheds": {
        "description": "DNR Level 9 Watersheds - Hydrologic Unit Boundaries",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/geos-dnr-watersheds",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/geos_dnr_watersheds/gpkg_geos_dnr_watersheds.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "static",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
    },
}


def get_dataset_config(dataset_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific dataset."""
    return MN_GEOSPATIAL_DATASETS.get(dataset_name)


def list_available_datasets() -> Dict[str, Dict[str, Any]]:
    """List all available spatial datasets."""
    return MN_GEOSPATIAL_DATASETS


def get_mn_geospatial_datasets() -> Dict[str, Dict[str, Any]]:
    """Get only MN Geospatial Commons datasets."""
    return MN_GEOSPATIAL_DATASETS
