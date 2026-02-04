"""Dataset registry for MN Geospatial Commons, FGDB, and other spatial data sources."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

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

# Hennepin County File Geodatabase (FGDB) datasets
# These are private datasets from HC_EasementAnalysis_Model_Inputs_2020.gdb
# Path configured via RTGS_FGDB_PATH environment variable
FGDB_DATASETS = {
    "bee_habitat": {
        "description": "Bee Habitat Analysis - Hennepin County pollinator habitat suitability scores",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Bee_Habitat_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 2,
        "score_column": "Bee_Habitat_SCORE",
        "model_critical": True,
    },
    "floodplains": {
        "description": "Floodplain Analysis - Hennepin County floodplain scoring",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Floodplains_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 2,
        "score_column": "Floodplain_Score",
        "model_critical": True,
    },
    "hennepin_wetland_inventory": {
        "description": "Hennepin County Wetland Inventory (HCWI) - Comprehensive wetland mapping",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "HCWI_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 56018,
        "model_critical": True,
    },
    "habitat_diversity": {
        "description": "Habitat Diversity Level 3 Analysis - Ecosystem diversity scoring",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "HabitatDiversity_Lvl3_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 51,
        "model_critical": True,
    },
    "headwaters": {
        "description": "Headwaters Analysis - Stream headwater catchment areas",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Headwaters_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 1447,
        "model_critical": True,
    },
    "important_bird_areas": {
        "description": "Important Bird Areas - Audubon designated bird conservation areas",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Important_Bird_Areas_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 6,
        "model_critical": True,
    },
    "mbs_sites": {
        "description": "Minnesota Biological Survey Sites - Sites of biodiversity significance",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "MBS_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 318,
        "score_column": "Bio_Sig_Score",
        "model_critical": True,
    },
    "land_cover": {
        "description": "Minnesota Land Cover Classification System (MLCCS) - Detailed land cover",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "MLCCS_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 46745,
        "model_critical": True,
    },
    "groundwater_recharge_hc": {
        "description": "Mean Groundwater Recharge 1996-2010 - Hennepin County recharge rates",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Mean_GW_Recharge_1996_2010_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 2884,
        "score_column": "Recharge_Score",
        "model_critical": True,
    },
    "natural_spaces": {
        "description": "Natural Spaces Analysis - Protected natural areas composite",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Natural_Spaces_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 1,
        "model_critical": True,
    },
    "protected_areas_hc": {
        "description": "Protected Areas Analysis - Hennepin County protected lands composite",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Protected_Areas_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 1,
        "model_critical": True,
    },
    "quality_community": {
        "description": "Quality Community Analysis - Community quality metrics composite",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Quality_Community_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 1,
        "model_critical": True,
    },
    "risk_of_development": {
        "description": "Risk of Development Analysis - Development pressure scoring",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Risk_of_Development_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 3,
        "score_column": "Risk_of_Development_Score",
        "model_critical": True,
    },
    "shoreland_buffers": {
        "description": "Shoreland Buffer Areas - Lake and stream buffer zones",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Shoreland_BufferAreas_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 1,
        "model_critical": True,
    },
    "groundwater_susceptibility": {
        "description": "Groundwater Contamination Susceptibility - Aquifer vulnerability zones",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Susceptibility_Contamination_Groundwater_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 976,
        "score_column": "Code_Score",
        "model_critical": True,
    },
    "wildlife_action_network": {
        "description": "Wildlife Action Network Analysis - Wildlife corridor ranking",
        "source_type": "fgdb",
        "extractor_class": "FGDBExtractor",
        "layer_name": "Wildlife_Action_Network_ANALYSIS",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 1564,
        "score_column": "RankNum_Model",
        "model_critical": True,
    },
}


def get_dataset_config(dataset_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific dataset.

    Searches both MN Geospatial Commons and FGDB datasets.

    Args:
        dataset_name: Name of the dataset

    Returns:
        Dataset configuration dict, or None if not found
    """
    # Check MN Geospatial first
    if dataset_name in MN_GEOSPATIAL_DATASETS:
        config = MN_GEOSPATIAL_DATASETS[dataset_name].copy()
        config["source"] = "mn_geospatial"
        return config

    # Check FGDB datasets
    if dataset_name in FGDB_DATASETS:
        # Only return FGDB config if FGDB is available
        from ..sources.fgdb import is_fgdb_available

        if is_fgdb_available():
            config = FGDB_DATASETS[dataset_name].copy()
            config["source"] = "fgdb"
            return config
        else:
            logger.warning(
                f"Dataset '{dataset_name}' is from FGDB but FGDB is not configured. "
                f"Set RTGS_FGDB_PATH environment variable."
            )
            return None

    return None


def list_available_datasets(include_fgdb: bool = True) -> Dict[str, Dict[str, Any]]:
    """List all available spatial datasets.

    Args:
        include_fgdb: Whether to include FGDB datasets (if available)

    Returns:
        Dictionary of dataset_name: config, with 'source' field added
    """
    datasets = {}

    # Add MN Geospatial datasets
    for name, config in MN_GEOSPATIAL_DATASETS.items():
        cfg = config.copy()
        cfg["source"] = "mn_geospatial"
        datasets[name] = cfg

    # Add FGDB datasets if available
    if include_fgdb:
        from ..sources.fgdb import is_fgdb_available

        if is_fgdb_available():
            for name, config in FGDB_DATASETS.items():
                cfg = config.copy()
                cfg["source"] = "fgdb"
                datasets[name] = cfg
            logger.debug(f"Loaded {len(FGDB_DATASETS)} FGDB datasets")
        else:
            logger.debug("FGDB not available, skipping FGDB datasets")

    return datasets


def get_mn_geospatial_datasets() -> Dict[str, Dict[str, Any]]:
    """Get only MN Geospatial Commons datasets."""
    return MN_GEOSPATIAL_DATASETS


def get_fgdb_datasets() -> Dict[str, Dict[str, Any]]:
    """Get only FGDB datasets (if FGDB is available).

    Returns:
        FGDB datasets dict if available, empty dict otherwise
    """
    from ..sources.fgdb import is_fgdb_available

    if is_fgdb_available():
        return FGDB_DATASETS
    return {}


def get_dataset_source(dataset_name: str) -> str:
    """Determine which source a dataset comes from.

    Args:
        dataset_name: Name of the dataset

    Returns:
        'mn_geospatial', 'fgdb', or 'unknown'
    """
    if dataset_name in MN_GEOSPATIAL_DATASETS:
        return "mn_geospatial"

    if dataset_name in FGDB_DATASETS:
        from ..sources.fgdb import is_fgdb_available

        if is_fgdb_available():
            return "fgdb"
        else:
            logger.warning(
                f"Dataset '{dataset_name}' is in FGDB registry but FGDB not configured"
            )
            return "unknown"

    return "unknown"


def format_dataset_list_for_llm() -> str:
    """Format dataset list for Claude AI to understand.

    Creates a human-readable list of datasets with descriptions,
    organized by source.

    Returns:
        Formatted string describing available datasets
    """
    datasets = list_available_datasets()

    # Group by source
    mn_datasets = {k: v for k, v in datasets.items() if v.get("source") == "mn_geospatial"}
    fgdb_datasets = {k: v for k, v in datasets.items() if v.get("source") == "fgdb"}

    output = []

    if fgdb_datasets:
        output.append("## Hennepin County Analysis Datasets (FGDB)")
        output.append("")
        for name, info in sorted(fgdb_datasets.items()):
            desc = info.get("description", "No description")
            feature_count = info.get("expected_features", "Unknown")
            output.append(f"- **{name}**: {desc}")
            output.append(f"  - Features: {feature_count}")
            if info.get("score_column"):
                output.append(f"  - Score column: {info['score_column']}")
        output.append("")

    if mn_datasets:
        output.append("## Public Minnesota Datasets (MN Geospatial Commons)")
        output.append("")
        for name, info in sorted(mn_datasets.items()):
            desc = info.get("description", "No description")
            output.append(f"- **{name}**: {desc}")
        output.append("")

    output.append(f"**Total Datasets Available: {len(datasets)}**")
    output.append(f"- FGDB (Hennepin County): {len(fgdb_datasets)}")
    output.append(f"- MN Geospatial Commons: {len(mn_datasets)}")

    return "\n".join(output)
