"""Dataset registry for MN Geospatial Commons, FGDB, local files, and other spatial data sources."""

import logging
from pathlib import Path
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
        # Easement-scoring crosswalk rows 14 & 16: the 2020 model selects only the
        # three highest biodiversity-significance classes. Filter was carried in the
        # xlsx but never in the registry.
        "attribute_filter": {
            "description": "Sites of Outstanding, High or Moderate biodiversity significance",
            "columns": ["biodiv_sig"],
            "values": ["Outstanding", "High", "Moderate"],
            "match_type": "any",
        },
        "crosswalk_rows": [14, 16],
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
        # Easement-scoring crosswalk row 25: the model uses Generalized Land Use only
        # to pick out land that is still undeveloped.
        "attribute_filter": {
            "description": "Undeveloped land only",
            "columns": ["LUSE_DESC"],
            "values": ["Undeveloped"],
            "match_type": "any",
        },
        "crosswalk_rows": [25],
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
        # Easement-scoring crosswalk row 34: the Headwater Area criterion uses only the
        # Level 9 auto-catchments positioned at the head of their drainage network.
        "attribute_filter": {
            "description": "Level 9 auto-catchments in headwater position",
            "columns": ["CATCH_POS"],
            "values": ["HEADWATER"],
            "match_type": "any",
        },
        "crosswalk_rows": [34],
    },
    # ------------------------------------------------------------------
    # Added 2026-09-21 from Meaghan Dietrich's easement-scoring-to-registry
    # crosswalk. Every download_url below returned HTTP 200 on 2026-09-21.
    # ------------------------------------------------------------------
    "state_administered_lands": {
        "description": (
            "State Administered Lands - DNR Management Units. Lands acquired, "
            "administered or managed by MN DNR: WMAs, SNAs, AMAs, State Forests, "
            "State Parks and Waysides in one layer."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/bdry-dnr-managed-areas",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/bdry_dnr_managed_areas/gpkg_bdry_dnr_managed_areas.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "yearly",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "last_updated": "2026-09-20",
        # Crosswalk rows 5, 6, 9 propose collapsing wildlife_areas,
        # scientific_and_natural_areas and aquatic_areas into this one layer.
        # Added alongside them, not in place of them: those three carry
        # expected_features integrity checks that would be lost on deletion.
        "consolidates": ["wildlife_areas", "scientific_and_natural_areas", "aquatic_areas"],
        "consolidation_status": "candidate - verify feature-type coverage before retiring the three",
        "crosswalk_rows": [5, 6, 9],
    },
    "regionally_significant_ecological_areas": {
        "description": (
            "Regionally Significant Ecological Areas - Imagine 2050. Terrestrial and "
            "wetland ecological areas in and around the 7-county Twin Cities metro, "
            "built to support Met Council comprehensive planning."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/us-mn-state-metc-plan-img2050-significantecoareas",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_metc/plan_img2050_significantecoareas/gpkg_plan_img2050_significantecoareas.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "data_source": "Metropolitan Council",
        "published": "2025-08-11",
        "last_updated": "2026-05-13",
        # ------------------------------------------------------------------
        # IMPORTANT. Crosswalk row 10 asks to "Remove all MLCCS / replace with
        # Imagine 2050". This layer is NOT a replacement for land_cover (MLCCS).
        # It is DOWNSTREAM of it. Met Council's own FGDC metadata lists the
        # lineage below, and DNR's RSEA page states "2008: Updated assessment
        # using MLCCS data". A public layer named "MLCCS Regionally Significant
        # Ecological Areas 2008" exists on the Commons.
        #
        # It also does not carry M_34X (the MLCCS native plant community quality
        # grade), which is what rows 10, 15 and 17 actually score on.
        # ------------------------------------------------------------------
        "derived_from_external": [
            "DNR RSEA 2008",
            "DNR RSEA 2014",
            "MLCCS (2011 Natural Land Cover Dataset used only where MLCCS unavailable)",
            "National Wetlands Inventory 2019",
            "Met Council Generalized Land Use 2020 (development mask)",
            "Regional Planned Land Use 2025",
        ],
        "not_a_replacement_for": "land_cover",
        "crosswalk_rows": [10],
    },
    "mlccs_npc_prediction": {
        "description": (
            "MLCCS/NPC model prediction layer - Random Forest prediction of MLCCS / "
            "Native Plant Community class for the 7-county metro."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/biota-mlccs-npc-model-results",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/biota_mlccs_npc_model_results/gpkg_biota_mlccs_npc_model_results.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "last_updated": "2026-09-16",
        # Proposed at crosswalk rows 15 and 17 as the "MLCCS substitute". Note it
        # is itself an MLCCS product - a prediction of MLCCS classes - so it does
        # not support row 10's "remove all MLCCS".
        "relates_to": "land_cover",
        "crosswalk_rows": [15, 17],
    },
    "swap_habitats": {
        "description": (
            "State Wildlife Action Plan Habitats - statewide coverage of habitats for "
            "Species in Greatest Conservation Need, supporting the 2025-2035 Minnesota "
            "Wildlife Action Plan."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/env-swap-habitats",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/env_swap_habitats/gpkg_env_swap_habitats.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "last_updated": "2026-05-13",
        # Proposed at crosswalk row 13 as an MLCCS substitute for habitat quality
        # ranking. Its own lineage is DNR Native Plant Communities, stream routes,
        # shallow lakes, lake basin morphology, NWI and the USFWS Midwest
        # Terrestrial Habitat System - it carries no M_34X-equivalent quality grade.
        "crosswalk_rows": [13],
    },
    "conservation_opportunity_areas": {
        "description": (
            "State Wildlife Action Plan - Conservation Opportunity Areas (COAs). "
            "Priority areas for implementing Minnesota's Wildlife Action Plan "
            "2025-2035, where high biodiversity and active partnerships overlap."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/env-swap-coa",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/env_swap_coa/gpkg_env_swap_coa.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "last_updated": "2026-09-16",
        # NOT the same as the older SNA/Marxan "MNDNR SNA Conservation Opportunity
        # Areas" layer (env-sna-conserv-opportunity-area), which targets SNA
        # acquisition and is also still live. Do not conflate the two.
        "not_to_be_confused_with": "env-sna-conserv-opportunity-area (SNA/Marxan acquisition layer)",
        "crosswalk_rows": [37],
    },
    "public_waters_basins_watercourses": {
        "description": (
            "DNR Public Waters (PW) Basin and Watercourse Delineations - regulatory "
            "delineations digitized from the scanned Public Waters Inventory (PWI) "
            "maps, including shoreland classifications."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/water-mn-public-waters",
        "download_url": "https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/water_mn_public_waters/gpkg_water_mn_public_waters.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "continuous",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
        "last_updated": "2026-09-20",
        # One dataset serving three crosswalk rows: 27 (Risk of Conversion
        # exclusion), 30 (shoreland buffer from watercourses), 31 (shoreland
        # buffer from basins). It is the missing INPUT behind shoreland_buffers.
        "feeds": ["shoreland_buffers"],
        "open_question": (
            "Meaghan flags that PWI basins include public-water wetlands that are "
            "largely redundant with NWI; a de-duplication rule is still needed."
        ),
        "crosswalk_rows": [27, 30, 31],
    },
    "nwi_wetlands": {
        "description": (
            "USFWS National Wetlands Inventory - seamless wetlands and deepwater "
            "habitat data, Minnesota state extract."
        ),
        "source_type": "direct_download",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://www.fws.gov/program/national-wetlands-inventory/download-state-wetlands-data",
        "download_url": "https://documentst.ecosphere.fws.gov/wetlands/data/State-Downloads/MN_geopackage_wetlands.zip",
        "download_url_gdb": "https://documentst.ecosphere.fws.gov/wetlands/data/State-Downloads/MN_geodatabase_wetlands.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "unknown",  # determine during extraction
        "data_source": "U.S. Fish and Wildlife Service",
        # Crosswalk row 26 asks to "replace by the regular NWI - include
        # everything". Registered as ADDITIVE to hennepin_wetland_inventory: HCWI's
        # LEGEND field distinguishes "Probable Wetland - HCWI" from "Probable
        # Wetland - NWI", so a straight swap discards Hennepin's own delineation.
        "additive_to": "hennepin_wetland_inventory",
        "crosswalk_rows": [26],
    },
    "pad_us": {
        "description": (
            "USGS PAD-US 4.1 - Protected Areas Database of the United States, "
            "Minnesota state extract. National inventory of terrestrial and marine "
            "protected areas."
        ),
        "source_type": "direct_download",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://www.sciencebase.gov/catalog/item/6759abcfd34edfeb8710a004",
        "download_url": "https://sciencebase.usgs.gov/manager/download/cm8rlfcwt001w0uphfpod8hzi",
        "access_method": "download",
        "file_format": "filegdb",  # PADUS4_1_State_MN_GDB_KMZ.zip, ~213.6 MB
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "unknown",  # determine during extraction
        "data_source": "U.S. Geological Survey Gap Analysis Project",
        "version": "4.1",
        "last_updated": "2025-03-27",
        # Crosswalk rows 29 and 39. CAVEAT: PAD-US aggregates public and NGO
        # holdings from the same state sources already registered. It does NOT
        # contain Hennepin County, Minnesota Land Trust or BWSR conservation
        # easements, so it does not substitute for the row 2 delivery.
        "does_not_cover": "Hennepin County / MLT / BWSR conservation easements (crosswalk row 2)",
        "crosswalk_rows": [29, 39],
    },
    "usfws_national_realty_boundaries": {
        "description": (
            "USFWS National Realty Boundaries - external boundary of all FWS "
            "administered lands and waters: National Wildlife Refuges, fish "
            "hatcheries, administrative sites and other conservation areas."
        ),
        "source_type": "rest_api",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gis-fws.opendata.arcgis.com/datasets/fws::fws-national-realty-boundaries",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:4326",  # determine during extraction
        "data_source": "U.S. Fish and Wildlife Service",
        # Crosswalk row 3 replaces the dead 2020 link
        # (fws.gov/gis/data/CadastralDB/links_cadastral.html) with this. No single
        # static download URL: it is an ArcGIS Hub item exported on demand.
        "service_url": None,  # [NEEDS CONFIRM] exact FeatureServer endpoint
        "notes": (
            "Hub item confirmed live 2026-09-21; the specific FeatureServer layer id "
            "and whether any refuge unit intersects Hennepin County are unconfirmed."
        ),
        "crosswalk_rows": [3],
    },
    "tnc_resilient_lands": {
        "description": (
            "TNC Resilient and Connected Network (customized detailed) - modelled "
            "climate-resilience and connectivity network. Distinct from TNC_lands, "
            "which is ownership."
        ),
        "source_type": "rest_api",
        "extractor_class": "MNGeospatialExtractor",
        "service_url": "https://tiles.arcgis.com/tiles/F7DSX1DSNSiWmOqh/arcgis/rest/services/Resilient_and_Connected_Network_TNC_Customized_Detailed/MapServer",
        "access_method": "rest_api",
        "file_format": "mapserver",
        "update_frequency": "periodic",
        "spatial_type": "raster",
        "model_critical": False,
        "coordinate_system": "EPSG:3857",  # determine during extraction
        "data_source": "The Nature Conservancy",
        # Service URL supplied by Hennepin in crosswalk row 38 and used as given.
        "url_provenance": "crosswalk row 38 (Meaghan Dietrich), not independently discovered",
        "crosswalk_rows": [38],
    },
    "midwest_conservation_blueprint": {
        "description": (
            "Midwest Conservation Blueprint 2026 - basemap of priority lands and "
            "waters for conservation in the Midwest, combining 20+ social and "
            "environmental values."
        ),
        "source_type": "rest_api",
        "extractor_class": "MNGeospatialExtractor",
        "service_url": "https://tiledimageservices.arcgis.com/QVENGdaPbd4LUkLV/arcgis/services/Midwest_Conservation_Blueprint_2026/ImageServer",
        "access_method": "rest_api",
        "file_format": "imageserver",
        "update_frequency": "periodic",
        "spatial_type": "raster",
        "model_critical": False,
        "coordinate_system": "unknown",  # determine during extraction
        "version": "2026",
        # Service URL supplied by Hennepin in crosswalk row 40 and used as given.
        # Hennepin has not decided whether this is a model input or a toggleable
        # display layer; registered either way.
        "url_provenance": "crosswalk row 40 (Meaghan Dietrich), not independently discovered",
        "usage_undecided": "model input vs interactive-map display layer (crosswalk row 40)",
        "crosswalk_rows": [40],
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
        # Easement-scoring crosswalk row 32. Public source is the FEMA National Flood
        # Hazard Layer; the two flood bands are separate queries over it.
        "public_source_agency": "Federal Emergency Management Agency (FEMA)",
        "public_source_url": "https://www.fema.gov/flood-maps/national-flood-hazard-layer",
        "derived_selections": {
            "100_year": "FLD_ZONE <> 'X' AND FLD_ZONE <> 'AREA NOT INCLUDED'",
            "500_year": "ZONE_SUBTY = '0.2 PCT ANNUAL CHANCE FLOOD HAZARD'",
        },
        "update_frequency": "periodic",  # FEMA restudies the metro every 5-7 years
        "crosswalk_rows": [32],
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
        # Easement-scoring crosswalk rows 26 & 33: both the Risk-of-Development and the
        # NWI Area criteria select only probable-wetland polygons.
        "attribute_filter": {
            "description": "Probable wetland polygons only (HCWI or NWI provenance)",
            "columns": ["LEGEND"],
            "values": ["Probable Wetland - HCWI", "Probable Wetland - NWI"],
            "match_type": "any",
        },
        "crosswalk_rows": [26, 33],
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
        # Easement-scoring crosswalk row 17: Gini-Simpson diversity is computed over
        # MLCCS level-3 boundaries restricted to natural/semi-natural cover.
        "derived_from": "land_cover",
        "source_query": 'CNUM > 30000',
        "source_query_note": (
            "MLCCS codes >= 30000 are the natural/semi-natural cover types; the query is "
            "baked into the delivered ANALYSIS layer and cannot be re-run without the "
            "MLCCS source."
        ),
        "crosswalk_rows": [17],
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
        # ------------------------------------------------------------------
        # PROVENANCE. MLCCS is not a new dataset and has not recently changed.
        #
        #  - Created 2004 by MN DNR Metro Region. Five-level hierarchical system
        #    classifying urban/built-up land by COVER rather than USE; hybrid of the
        #    National Vegetation Classification System, MN Natural Heritage native
        #    plant community types, and a cultural classification.
        #    https://www.dnr.state.mn.us/mlccs/index.html
        #  - Code set last revised 2023. Bart Richardson (MNIT, on behalf of DNR) to
        #    Kristine Maurer, 2025-02-04: "Attached is the latest version of the MLCCS
        #    codes. Nothing has changed since our final meeting in 2023." Forwarded to
        #    Bryan Runck 2026-07-31, mail thread:0000000000035b11, attachment
        #    "mlccs-npc_natural_codes - level details - top row.xlsx".
        #  - Public record: https://gisdata.mn.gov/dataset/biota-landcover-mlccs
        #
        # DO NOT treat the Imagine 2050 RSEA layer as a newer replacement for this.
        # RSEA is DOWNSTREAM of MLCCS, not a successor to it -- see the
        # "regionally_significant_ecological_areas" entry in MN_GEOSPATIAL_DATASETS.
        # ------------------------------------------------------------------
        "vintage": "2004 system; Hennepin County edited; code set frozen since 2023",
        "public_source_url": "https://gisdata.mn.gov/dataset/biota-landcover-mlccs",
        "public_source_agency": "Minnesota DNR (Metro Region) / Hennepin County edits",
        "superseded_by": None,  # explicitly: nothing
        "key_attributes": {
            "C_NUM": "numeric MLCCS cover code; >= 30000 is natural/semi-natural",
            "C_ALPHA": "alphanumeric cover code; '.nAT.' marks altered/non-native",
            "M_34X": "native plant community quality grade, A (best) to D",
        },
        "downstream_selections": ["natural_spaces", "quality_community", "habitat_diversity"],
        "crosswalk_rows": [10, 13, 15, 17],
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
        # Easement-scoring crosswalk row 10 (Ecologically Significant Areas). The ESA
        # selection is an MLCCS query, not a separate dataset.
        "derived_from": "land_cover",
        "source_query": (
            "(C_NUM >= 30000 AND C_ALPHA NOT LIKE '%.nAT.%') "
            "AND (M_34X = 'A' OR M_34X = 'B' OR M_34X = 'C')"
        ),
        "source_query_note": (
            "Natural/semi-natural MLCCS cover (C_NUM >= 30000), excluding non-native "
            "altered communities (.nAT.), graded A/B/C on quality. Hennepin's "
            "'Ecologically Significant Areas' layer IS this query over MLCCS."
        ),
        "crosswalk_rows": [10],
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
        # Easement-scoring crosswalk row 15: "quality community" means an MLCCS polygon
        # graded A or B on the M_34X quality field.
        "derived_from": "land_cover",
        "source_query": "M_34X = 'A' OR M_34X = 'B'",
        "source_query_note": (
            "M_34X is the MLCCS native-plant-community quality grade (A best - D worst). "
            "No published replacement layer carries this attribute; see land_cover."
        ),
        "crosswalk_rows": [15],
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


# ============================================================================
# Configuration-based Dataset Discovery
# ============================================================================


def list_datasets_by_mode(mode: str = "built-in", local_directory: Optional[Path] = None,
                          local_prefix: str = "local") -> Dict[str, Dict[str, Any]]:
    """
    List datasets based on operational mode.

    Args:
        mode: Operational mode - 'built-in', 'local', or 'hybrid'
        local_directory: Path to directory containing local files (required for local/hybrid)
        local_prefix: Prefix to add to local dataset names (default: 'local')

    Returns:
        Dictionary of dataset_name: config

    Raises:
        ValueError: If mode is invalid or required directory is missing
    """
    if mode not in ["built-in", "local", "hybrid"]:
        raise ValueError(f"Invalid mode: {mode}. Must be 'built-in', 'local', or 'hybrid'")

    datasets = {}

    # Built-in datasets
    if mode in ["built-in", "hybrid"]:
        datasets.update(list_available_datasets())

    # Local datasets
    if mode in ["local", "hybrid"]:
        if local_directory is None:
            raise ValueError(f"Mode '{mode}' requires local_directory to be specified")

        from ..sources.local_file import discover_local_datasets

        local_datasets = discover_local_datasets(local_directory)

        # Add prefix to local dataset names in hybrid mode
        if mode == "hybrid":
            local_datasets = {
                f"{local_prefix}:{name}": config
                for name, config in local_datasets.items()
            }

        # Add source field
        for config in local_datasets.values():
            config["source"] = "local"

        datasets.update(local_datasets)

    return datasets


def get_dataset_config_by_mode(dataset_name: str, mode: str = "built-in",
                              local_directory: Optional[Path] = None,
                              local_prefix: str = "local") -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific dataset based on mode.

    Args:
        dataset_name: Name of the dataset
        mode: Operational mode
        local_directory: Path to local files directory
        local_prefix: Prefix for local datasets in hybrid mode

    Returns:
        Dataset configuration dictionary or None if not found
    """
    datasets = list_datasets_by_mode(mode, local_directory, local_prefix)
    return datasets.get(dataset_name)


def get_dataset_source_by_mode(dataset_name: str, mode: str = "built-in",
                               local_directory: Optional[Path] = None,
                               local_prefix: str = "local") -> str:
    """
    Determine source of a dataset based on mode.

    Args:
        dataset_name: Name of the dataset
        mode: Operational mode
        local_directory: Path to local files directory
        local_prefix: Prefix for local datasets

    Returns:
        'mn_geospatial', 'fgdb', 'local', or 'unknown'
    """
    # Check if it's a local dataset (has prefix or mode is local)
    if mode == "local":
        return "local"

    if mode == "hybrid" and dataset_name.startswith(f"{local_prefix}:"):
        return "local"

    # Otherwise check built-in sources
    return get_dataset_source(dataset_name)


def format_dataset_list_by_mode(mode: str = "built-in",
                                local_directory: Optional[Path] = None,
                                local_prefix: str = "local") -> str:
    """
    Format dataset list for display based on mode.

    Args:
        mode: Operational mode
        local_directory: Path to local files directory
        local_prefix: Prefix for local datasets

    Returns:
        Formatted string describing available datasets
    """
    datasets = list_datasets_by_mode(mode, local_directory, local_prefix)

    # Group by source
    mn_datasets = {k: v for k, v in datasets.items() if v.get("source") == "mn_geospatial"}
    fgdb_datasets = {k: v for k, v in datasets.items() if v.get("source") == "fgdb"}
    local_datasets = {k: v for k, v in datasets.items() if v.get("source") == "local"}

    output = []
    output.append(f"# Available Datasets (Mode: {mode})")
    output.append("")

    if local_datasets:
        output.append("## Local Datasets")
        output.append("")
        for name, info in sorted(local_datasets.items()):
            desc = info.get("description", "No description")
            file_size = info.get("file_size_mb", 0)
            output.append(f"- **{name}**: {desc}")
            if file_size:
                output.append(f"  - Size: {file_size:.2f} MB")
        output.append("")

    if fgdb_datasets:
        output.append("## Hennepin County Analysis Datasets (FGDB)")
        output.append("")
        for name, info in sorted(fgdb_datasets.items()):
            desc = info.get("description", "No description")
            output.append(f"- **{name}**: {desc}")
        output.append("")

    if mn_datasets:
        output.append("## Public Minnesota Datasets (MN Geospatial Commons)")
        output.append("")
        for name, info in sorted(mn_datasets.items()):
            desc = info.get("description", "No description")
            output.append(f"- **{name}**: {desc}")
        output.append("")

    output.append(f"**Total Datasets Available: {len(datasets)}**")
    if local_datasets:
        output.append(f"- Local: {len(local_datasets)}")
    if fgdb_datasets:
        output.append(f"- FGDB (Hennepin County): {len(fgdb_datasets)}")
    if mn_datasets:
        output.append(f"- MN Geospatial Commons: {len(mn_datasets)}")

    return "\n".join(output)
