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
        "published_by": "Minnesota Pollution Control Agency (gisdata org path us_mn_state_pca)",
        "temporal_coverage": "1996-2010",
        "units": "inches/year",
        # Crosswalk row 35 offers an "updated link"; it resolves to this same
        # dataset. Authored by USGS, published on the Commons under MPCA.
        "crosswalk_rows": [35],
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
        # Crosswalk rows 7 and 8, reviewed 2026-09-21, KEPT AS IS.
        # Row 7 proposes https://services.arcgis.com/F7DSX1DSNSiWmOqh/arcgis/rest/
        # services/TNC_Lands_Public_Layer/FeatureServer. The service pinned above is
        # narrower and better: MN/ND/SD-scoped, vintage-stamped 2024, and matched to
        # the expected_features check. Kept the registry's.
        # Row 8 ("TNC Lands (Transferred)"): the separate transferred-lands layer used
        # by the 2020 model is not distinguished here. Meaghan's read that it is
        # folded into the broader layer is plausible but unverified.
        "transferred_lands_status": (
            "[NEEDS CONFIRM] which attribute marks lands transferred to public "
            "entities; needed only if the model scored them differently (row 8)"
        ),
        "crosswalk_rows": [7, 8],
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
        "last_updated": "2026-09-16",
        # Crosswalk row 21 says WAN "can be replaced with CAN". Not yet possible.
        # The Conservation Action Network is the 2025-2035 SWAP successor to the
        # 2015 WAN, but as of 2026-09-21 no CAN layer is published on the
        # Minnesota Geospatial Commons (catalog full-text search returns no CAN
        # item; DNR's WAP 2025-2035 page describes it without an availability
        # date). WAN itself is still live and was refreshed 2026-09-16.
        # Keep scoring on WAN. See FORTHCOMING_DATASETS["conservation_action_network"].
        "successor_status": "CAN expected, not published as of 2026-09-21 - do not retire",
        "crosswalk_rows": [21],
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
        # Vintage history for crosswalk row 25. The xlsx records the 2020 model as
        # having used Generalized Land Use 2016; this registry was already ahead
        # of the sheet at 2020. Meaghan asks for 2025 -- deliberately NOT done:
        # a catalog item exists (ArcGIS Hub c0bca5584e704731880b81c646d5e271,
        # created 2026-07-24) but it carries no download links and the bulk path
        # plan_generl_lnduse2025 returns 404. 2020 is the newest downloadable
        # release. Also confirm which product is meant: "Generalized Land Use"
        # (existing use) and "Regional Planned Land Use" (planned use) differ, and
        # only the former carries LUSE_DESC.
        "vintage_history": {
            "2016": "cited by the xlsx as the layer the 2020 model used",
            "2020": "CURRENT - plan_generl_lnduse2020",
            "2025": "catalogued 2026-07-24 but not downloadable as of 2026-09-21",
        },
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
        # Crosswalk row 28, reviewed 2026-09-21: NO CHANGE NEEDED. The sheet says
        # "Can't find a substitute or updated dataset", but nothing is required --
        # this entry already reproduces the full XUSECLASS1-4 cemetery filter,
        # enumerates all seven county parcel layers, and the underlying regional
        # parcels dataset is itself refreshed quarterly. Row closed.
        "crosswalk_rows": [28],
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
    # --- NRPC interactive map: v1 model results (web map d664f1d1) ---
    "hennepin_suitability_v1_countywide": {
        "description": (
            "Hennepin County Parcel Prioritization Model results, v1 (2020 inputs), "
            "county-wide view: every parcel with its six category scores and overall "
            "rank."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Hennepin_Suitability_Model_Results_PublicView/FeatureServer/96",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Hennepin_Suitability_Model_Results_PublicView/FeatureServer/96",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "static",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 445517,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-01-22",
        "agol_item_id": "01d9c39e16714ebdaa20af2008f532de",
        "nrpc_webmap_titles": ["Parcel Prioritization Model Results (County Wide View)"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # v1 = the model as run in 2023; the Natural Spaces centroid bug is in it
        # (W43THU01 35-output-20261022-notes-for-bryan.md). Superseded by V2 when published.
    },
    "hennepin_suitability_v1_parcel_detail": {
        "description": (
            "Hennepin County Parcel Prioritization Model results, v1, parcel-detail "
            "view used by the parcel report for per-parcel tier-2 values."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Hennepin_Suitability_Model_Results_parcel_detail/FeatureServer/97",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Hennepin_Suitability_Model_Results_parcel_detail/FeatureServer/97",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "static",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 445517,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-01-22",
        "agol_item_id": "3ed0717b29fe491e8b5cbcd548818925",
        "nrpc_webmap_titles": ["Parcel Prioritization Model Results (Parcel View)"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # Also read by js/report-maps.js for the report plates.
    },
    # --- NRPC interactive map: Metropolitan Council data ---
    "metc_protection_opportunities": {
        "description": (
            "Metropolitan Council natural-systems Protection Opportunities, Hennepin "
            "County cut, as served in the NRPC map (county and city views share this "
            "layer)."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Met_Council_Data_Protection_Opportunities/FeatureServer/103",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Met_Council_Data_Protection_Opportunities/FeatureServer/103",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 37,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-03-12",
        "agol_item_id": "73b722c7e92a428e85ba15d262f410dc",
        "nrpc_webmap_titles": ["Met Council - Protection Opportunities (County View)", "Met Council - Protection Opportunities (City View)"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # Hosted copy in the UMN org (runcklab_UMN), not Met Council's own service.
    },
    "metc_improvement_opportunities": {
        "description": (
            "Metropolitan Council natural-systems Improvement Opportunities, Hennepin "
            "County cut."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Met_Council_Data_Improvement_Opportunities/FeatureServer/104",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Met_Council_Data_Improvement_Opportunities/FeatureServer/104",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 60,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-03-12",
        "agol_item_id": "9b5143f9ba4e4692bd36b33cefc83ef4",
        "nrpc_webmap_titles": ["Met Council - Improvement Opportunities (County View)", "Met Council - Improvement Opportunities (City View)"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # Hosted copy in the UMN org (runcklab_UMN), not Met Council's own service.
    },
    "metc_existing_natural_systems": {
        "description": (
            "Metropolitan Council Existing Natural Systems (aquatic and terrestrial), "
            "Hennepin County cut; the map draws aquatic and terrestrial as two "
            "renderings of this layer."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Met_Council_Data_Existing_Natural_Systems/FeatureServer/105",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Met_Council_Data_Existing_Natural_Systems/FeatureServer/105",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 114,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-04-27",
        "agol_item_id": "39d718683b2a4615be582343d3a80531",
        "nrpc_webmap_titles": ["Met Council - Existing Natural Systems (County View) - Aquatic", "Met Council - Existing Natural Systems (County View) - Terrestrial", "Met Council - Existing Natural Systems (City View)"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # Hosted copy in the UMN org (runcklab_UMN), not Met Council's own service.
    },
    "metc_ecologically_significant_areas": {
        "description": (
            "Metropolitan Council Ecologically Significant Areas, Hennepin County cut."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Met_Council_Data_Ecologically_Significant_Areas/FeatureServer/106",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Met_Council_Data_Ecologically_Significant_Areas/FeatureServer/106",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 51,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-03-12",
        "agol_item_id": "bba2acb6b9ce4c66ae2d813b3f2a1348",
        "nrpc_webmap_titles": ["Met Council - Ecologically Significant Areas (County View)", "Met Council - Ecologically Significant Areas (City View)"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # Hosted copy in the UMN org (runcklab_UMN), not Met Council's own service.
    },
    "metc_ecologically_sensitive_areas": {
        "description": (
            "Metropolitan Council Ecologically Sensitive Areas, Hennepin County cut."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Met_Council_Data_Ecologically_Sensitive_Areas/FeatureServer/108",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Met_Council_Data_Ecologically_Sensitive_Areas/FeatureServer/108",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 60,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-03-12",
        "agol_item_id": "88362700d2a640df99f1eb6e540e7792",
        "nrpc_webmap_titles": ["Met Council - Ecologically Sensitive Areas (County View)", "Met Council - Ecologically Sensitive Areas (City View)"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # Hosted copy in the UMN org (runcklab_UMN), not Met Council's own service.
    },
    # --- NRPC interactive map: public natural-systems data ---
    "hc_public_water_basins_clipped": {
        "description": (
            "DNR public water basin delineations clipped to Hennepin County (NRPC map "
            "'Public Water Basins')."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/HennepinCounty_PublicWaterBasins_Clipped/FeatureServer/99",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/HennepinCounty_PublicWaterBasins_Clipped/FeatureServer/99",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 1036,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-02-11",
        "agol_item_id": "de61209bdef64edbbcbf6aeca9cb49fb",
        "nrpc_webmap_titles": ["Public Water Basins"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        "relates_to": "public_waters_basins_watercourses",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
    },
    "hc_public_parcels_clipped": {
        "description": (
            "Publicly owned parcels in Hennepin County (NRPC map 'Public Parcels')."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/HennepinCounty_PublicParcels_Clipped/FeatureServer/100",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/HennepinCounty_PublicParcels_Clipped/FeatureServer/100",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 14724,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-02-11",
        "agol_item_id": "a4e53a771ffa43e29e4b2ff3c1206625",
        "nrpc_webmap_titles": ["Public Parcels"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
    },
    "hc_parks_clipped": {
        "description": (
            "Parks in Hennepin County, clipped (NRPC map 'Public Parks')."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/HennepinCounty_Parks_Clipped/FeatureServer/101",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/HennepinCounty_Parks_Clipped/FeatureServer/101",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 1100,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-02-11",
        "agol_item_id": "c300f32677bb487a8983fa5326b2e7d8",
        "nrpc_webmap_titles": ["Public Parks"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
    },
    "regional_trails": {
        "description": (
            "Regional trails (NRPC map 'Regional Trails')."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Regional_Trails/FeatureServer/118",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Regional_Trails/FeatureServer/118",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multilinestring",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 240,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-03-19",
        "agol_item_id": "3f74c86a386b4e1bbc6c7a87e7edb0f1",
        "nrpc_webmap_titles": ["Regional Trails"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
    },
    # --- NRPC interactive map: NRPC member-engagement layers ---
    "nrpc_winter_workshop_activity_1": {
        "description": (
            "NRPC Winter Workshop 2025, Activity 1: points placed by members (service "
            "layer name 20250107_Activity_1)."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Winter_Workshop_Activity_1/FeatureServer/0",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Winter_Workshop_Activity_1/FeatureServer/0",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "continuous",
        "spatial_type": "point",
        "model_critical": False,
        "coordinate_system": "EPSG:3857",
        "expected_features": 162,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-04-02",
        "agol_item_id": "3f1b5e6c72c947e388e9422897dc966a",
        "nrpc_webmap_titles": ["Winter Workshop 2025 - Activity 1"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
    },
    "nrpc_winter_workshop_activity_2_thematic": {
        "description": (
            "NRPC Winter Workshop 2025, Activity 2: thematic connections drawn by "
            "members."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Winter_Workshop_Activity_2/FeatureServer/0",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Winter_Workshop_Activity_2/FeatureServer/0",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "continuous",
        "spatial_type": "multilinestring",
        "model_critical": False,
        "coordinate_system": "EPSG:3857",
        "expected_features": 49,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-04-02",
        "agol_item_id": "5b35b3ba75df4e3caafe7fdee1772af5",
        "nrpc_webmap_titles": ["Activity 2: Thematic Connection"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
    },
    "nrpc_winter_workshop_activity_2_physical": {
        "description": (
            "NRPC Winter Workshop 2025, Activity 2: physical connections drawn by "
            "members."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Winter_Workshop_Activity_2/FeatureServer/1",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Winter_Workshop_Activity_2/FeatureServer/1",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "continuous",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:3857",
        "expected_features": 21,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-04-02",
        "agol_item_id": "5b35b3ba75df4e3caafe7fdee1772af5",
        "nrpc_webmap_titles": ["Activity 2: Physical Connection"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
    },
    "nrpc_opportunity_areas_point": {
        "description": (
            "NRPC Opportunity Layer, point features: opportunity areas members submit."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/NRPC_Opportunity_Layer/FeatureServer/0",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/NRPC_Opportunity_Layer/FeatureServer/0",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "continuous",
        "spatial_type": "point",
        "model_critical": False,
        "coordinate_system": "EPSG:3857",
        "expected_features": 0,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-05-06",
        "agol_item_id": "8b041fc3953e44d38f667550a8f1d16a",
        "nrpc_webmap_titles": ["Opportunity Area (Point)"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # Anonymous returnCountOnly = 0 on 2026-11-04: empty or not shared publicly
        # [NEEDS CONFIRM]. The parcel report's Shared opportunities section reads it.
    },
    "nrpc_opportunity_areas_polygon": {
        "description": (
            "NRPC Opportunity Layer, polygon features: opportunity areas members "
            "submit."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/NRPC_Opportunity_Layer/FeatureServer/1",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/NRPC_Opportunity_Layer/FeatureServer/1",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "continuous",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:3857",
        "expected_features": 0,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-05-06",
        "agol_item_id": "8b041fc3953e44d38f667550a8f1d16a",
        "nrpc_webmap_titles": ["Opportunity Area (Polygon)"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # Anonymous returnCountOnly = 0 on 2026-11-04: empty or not shared publicly
        # [NEEDS CONFIRM].
    },
    # --- NRPC interactive map: boundaries ---
    "hc_watershed_districts": {
        "description": (
            "Watershed district / WMO administrative boundaries in Hennepin County "
            "(service layer PUBLICWORKS.PWGIS.Watershed_Admin_Boundaries)."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services1.arcgis.com/ziLNoRgqnICUM0q1/arcgis/rest/services/Watershed_Districts_2/FeatureServer/0",
        "service_url": "https://services1.arcgis.com/ziLNoRgqnICUM0q1/arcgis/rest/services/Watershed_Districts_2/FeatureServer/0",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "unknown",
        "expected_features": 16,  # returnCountOnly, 2026-11-04
        "last_updated": "2019-07-09",
        "agol_item_id": "7060522e3e534bc7bc9207bcc4c13da8",
        "nrpc_webmap_titles": ["Watershed Districts"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # Projection is a custom Hennepin County LCC (US feet) WKT with no EPSG;
        # the extractor reprojects to EPSG:4326. Local copy in nrpc-qaqc:
        # jurisdictions/watershed_districts.shp (QA/QC jurisdiction boundary).
    },
    "hennepin_parcels": {
        "description": (
            "Hennepin County parcel base (county GIS NATURALRESOURCES map service, "
            "layer 2 'Parcel Base'). Parcel geometry for the map, the parcel report "
            "and mobile.js."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gis.hennepin.us/arcgis/rest/services/Maps/NATURALRESOURCES/MapServer/2",
        "service_url": "https://gis.hennepin.us/arcgis/rest/services/Maps/NATURALRESOURCES/MapServer/2",
        "access_method": "rest_api",
        "file_format": "mapserver",
        "update_frequency": "continuous",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 379625,  # returnCountOnly, 2026-11-04
        "agol_item_id": "8bf37684d18440a59c4eb923427ee3fb",
        "nrpc_webmap_titles": ["Parcels"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # County-hosted MapServer; maxRecordCount 2000, geoJSON supported.
    },
    "hc_cities": {
        "description": (
            "Hennepin County cities and townships (NRPC map 'Cities'; service layer "
            "FindExistingLocationsOutput)."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Hennepin County Cities/FeatureServer/0",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/Hennepin County Cities/FeatureServer/0",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "static",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 47,  # returnCountOnly, 2026-11-04
        "last_updated": "2024-05-22",
        "agol_item_id": "3a098bd9dadf45088eb153c3e86cadfe",
        "nrpc_webmap_titles": ["Cities"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # The service name contains spaces; requests must percent-encode them.
        # Local copy in nrpc-qaqc: jurisdictions/cities.shp.
    },
    "hc_ctu_labels": {
        "description": (
            "City/township label polygons for Hennepin County (NRPC map 'Cities - "
            "Labels')."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/CTUs_labels/FeatureServer/123",
        "service_url": "https://services.arcgis.com/8df8p0NlLFEShl0r/arcgis/rest/services/CTUs_labels/FeatureServer/123",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "static",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 41,  # returnCountOnly, 2026-11-04
        "last_updated": "2026-03-26",
        "agol_item_id": "f73146604ab548b292b0849bfec9553b",
        "nrpc_webmap_titles": ["Cities - Labels"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
    },
    "hennepin_county_boundary": {
        "description": (
            "Hennepin County boundary (county GIS BOUNDARIES map service, layer 1)."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gis.hennepin.us/arcgis/rest/services/HennepinData/BOUNDARIES/MapServer/1",
        "service_url": "https://gis.hennepin.us/arcgis/rest/services/HennepinData/BOUNDARIES/MapServer/1",
        "access_method": "rest_api",
        "file_format": "mapserver",
        "update_frequency": "static",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 1,  # returnCountOnly, 2026-11-04
        "agol_item_id": "d47c495bda3f4458bdbfff0e6a842d70",
        "nrpc_webmap_titles": ["Hennepin County"],
        "nrpc_webmap_item": "d664f1d163544d25bb92921e5c4bf214",
        # Layer of the NRPC Interactive Map web map d664f1d1 (public, read 2026-11-02);
        # the same URL is hard-coded in nrpc-interactive-map js/parcel-report.js.
        # Local copy in nrpc-qaqc: jurisdictions/hennepin.shp (QA/QC boundary;
        # also the study area of the 2026-10-22 v1 replay run).
    },
    # --- Protected-areas gap source named by Hennepin, 2026-11-03 ---
    "trpd_park_boundaries": {
        "description": (
            "Three Rivers Park District park boundaries (open data). Fills parks that "
            "neither the county Parks of NR Significance layer nor PAD-US carries."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gis.trpdmn.org/traditional/rest/services/Park_Bndry_Public/FeatureServer/0",
        "service_url": "https://gis.trpdmn.org/traditional/rest/services/Park_Bndry_Public/FeatureServer/0",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 44,  # returnCountOnly, 2026-11-04
        "agol_item_id": "e0cba3b47bc1460297f6d0ec198f99c7",
        "relates_to": "pad_us",
        # Meaghan Dietrich, 2026-11-03 14:02 CST, thread:0000000000036996: 'there are a few Three
        # Rivers Park District properties that don't make it into the Parks of NR Significance layer
        # the county has on hand or the PAD-US data.' Her subset: trpd_gap_subset (delivered).
        # Owner gisadmin@trpd; hub page gis.threeriversparks.org/datasets/trpd::park-boundaries-open-data.
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
        # Crosswalk row 23. Two features for a county-wide pollinator layer means
        # this is a DISSOLVED SCORE SURFACE, not a habitat inventory: it cannot be
        # re-derived, re-weighted or updated from what is in the FGDB. That is the
        # structural problem, independent of whether the Ryan Noe methodology is
        # still defensible. Meaghan asks Bryan directly whether he holds the RPBB
        # high-potential-zones / pollinator suitability analysis. Unresolved.
        "layer_shape": "dissolved score surface - inputs not recoverable from the FGDB",
        "replacement_status": "[NEEDS CONFIRM] pending Bryan on RPBB / pollinator suitability",
        "crosswalk_rows": [23],
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
        # Crosswalk row 22: the 2019 layer came to Hennepin by direct request to
        # Audubon. A public feature service now exists, which removes a standing
        # dependency on Audubon staff. Verified live 2026-09-21.
        "public_source_agency": "National Audubon Society",
        "public_service_url": "https://services1.arcgis.com/lDFzr3JyGEn5Eymu/arcgis/rest/services/iba_polygons_public/FeatureServer",
        "public_service_item_id": "087b591fd12d4dc482a4d9a3e2b60246",
        "crosswalk_rows": [22],
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
        # Crosswalk row 29. One feature: this is a dissolved composite of the
        # protected-areas inputs, and those inputs were never registered
        # individually. It cannot be recomputed or reweighted when one input
        # changes, which is why rows 2, 3 and 4 all read MISSING.
        "layer_shape": "dissolved composite - constituent inputs not individually registered",
        "missing_inputs": [
            "Hennepin established conservation easements (row 2)",
            "USFWS refuge boundaries (row 3) - now usfws_national_realty_boundaries",
            "Parks of Natural Resource Significance (row 4)",
        ],
        "crosswalk_rows": [29],
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
        # Crosswalk row 24. Three features -- same dissolved-surface problem as
        # bee_habitat. The Ryan Noe methodology inputs (utility and road buffers,
        # sewer service areas) are not itemised anywhere in the registry, and
        # Meaghan holds the source dataset. Note the sheet's bee-habitat note
        # landed on this row by mistake.
        "layer_shape": "dissolved score surface - Noe methodology inputs not itemised",
        "pending_source": "Ryan Noe risk-of-development inputs (Meaghan to email)",
        "crosswalk_rows": [24],
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
        # Crosswalk rows 30 and 31: the buffer OUTPUT was registered, the PWI
        # watercourses and basins it was computed from were not. Now they are.
        "layer_shape": "dissolved buffer output",
        "computed_from": "public_waters_basins_watercourses",
        "crosswalk_rows": [30, 31],
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
        # Crosswalk row 36. The MGS geological sensitivity source URL was never
        # recorded. Meaghan proposes "Minnesota Water Table Aquifer Vulnerability"
        # -- which is NOT obviously the same product: it is published by the MN
        # Department of Agriculture (gisdata water-aquifer-vulnerability, org path
        # us_mn_state_mda, refreshed 2026-09-17), built on MN Geological Survey and
        # UMD geomorphology data via a 2011 MDH/MDA/DNR workgroup. Related
        # lineage, different agency, different product. Code_Score's class mapping
        # depends on which one it came from.
        "source_agency_recorded": "Minnesota Geological Survey (geological sensitivity)",
        "candidate_public_url": "https://gisdata.mn.gov/dataset/water-aquifer-vulnerability",
        "candidate_public_agency": "Minnesota Department of Agriculture",
        "candidate_status": "[NEEDS CONFIRM] same product as MGS geological sensitivity, or a successor?",
        "crosswalk_rows": [36],
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
        # Crosswalk row 21. Even once CAN publishes, this entry is what the 2020
        # scoring actually ran against and RankNum_Model has no guaranteed CAN
        # equivalent. Retire only after the score mapping is re-derived.
        "successor_status": "CAN expected, not published as of 2026-09-21 - do not retire",
        "crosswalk_rows": [21],
    },
}


# ============================================================================
# Datasets the model needs that CANNOT be acquired yet.
#
# These are deliberately kept out of MN_GEOSPATIAL_DATASETS and FGDB_DATASETS so
# that list_available_datasets() never offers something that cannot be fetched.
# They are recorded rather than dropped because each one is a live ask with a
# named owner, and a spreadsheet cell is not a durable place to keep that.
#
# Every field below is taken verbatim from Meaghan Dietrich's
# easement-scoring-to-registry crosswalk (2026-09-16). Nothing is inferred: where
# the sheet does not say, the value is None.
# ============================================================================

PENDING_HENNEPIN_DATASETS = {
    "established_conservation_easements": {
        "description": "Hennepin County established conservation easements",
        "owner": "Meaghan Dietrich, Hennepin County",
        "storage_location": "GIS warehouse",
        "layer_query": None,
        "status": "awaiting_delivery",
        "blocking": ["protected_areas_hc"],
        "note": (
            "Compiled database of Hennepin County, Minnesota Land Trust and BWSR "
            "easements. PAD-US does NOT contain these - it is the one gap no public "
            "dataset closes. Sheet says 'Need to update regularly'."
        ),
        "crosswalk_rows": [2],
    },
    "parks_natural_resource_significance": {
        "description": "Hennepin County Parks of Natural Resource Significance",
        "owner": "Hennepin County GIS (Meaghan to ask Alex how the layer is generated)",
        "storage_location": "File network",
        "layer_query": "NaturalResources_Category <> 'Amenities'",
        "status": "awaiting_delivery",
        "blocking": ["protected_areas_hc"],
        "note": (
            "Built on the HC parks layer; Kristine identified regionally significant "
            "parks using standard criteria."
        ),
        "crosswalk_rows": [4],
    },
    "potential_easements": {
        "description": "Hennepin County potential easements - the candidate sites the model scores",
        "owner": "Meaghan Dietrich, Hennepin County",
        "storage_location": "File network",
        "layer_query": "Status IN ('Current Applicant', 'On-Hold', 'Selected')",
        "status": "awaiting_delivery",
        "blocking": ["the model's analysis units"],
        "note": (
            "Highest priority of the pending deliveries: this is the candidate-site "
            "layer the whole suitability model scores against."
        ),
        "crosswalk_rows": [12],
    },
    "analysis_easements": {
        "description": "Hennepin County analysis easements - used for Relative and Absolute Size scoring",
        "owner": "Meaghan Dietrich, Hennepin County",
        "storage_location": "Public Works Env. SDE",
        "layer_query": None,
        "status": "awaiting_delivery",
        "blocking": ["Relative Size criterion", "Absolute Size criterion"],
        "note": (
            "Sheet names this separately from rows 2 and 12 and stores it in a "
            "different place (Public Works Env. SDE vs GIS warehouse). Confirm whether "
            "these are three views of one delivery or three files."
        ),
        "crosswalk_rows": [18, 19],
    },
    "nhis_rare_features": {
        "description": "DNR Natural Heritage Information System (NHIS) rare features polygons",
        "owner": "Minnesota DNR (restricted; Hennepin plans to meet DNR)",
        "storage_location": "GIS warehouse (restricted)",
        "layer_query": {
            "0-1 mile": "name_cat NOT IN ('Other (Ecological)')",
            "1-3 mile": "name_cat NOT IN ('Other (Ecological)', 'Vascular Plant')",
        },
        "status": "access_unresolved",
        "blocking": ["NHIS Occurrence criterion (both distance bands)"],
        "note": (
            "Restricted data by direct request, so no public registry entry is "
            "possible. Open question: does Hennepin GIS process NHIS into a shareable "
            "derived product, or does the lab need its own DNR licence? Public viewer "
            "only: https://osaportal.gisdata.mn.gov/public-map"
        ),
        "crosswalk_rows": [20],
    },
    "pollinator_suitability": {
        "description": "Replacement for the Ryan Noe bee pollination habitat layer",
        "owner": "[NEEDS CONFIRM] Bryan Runck - Meaghan asks directly whether he holds this",
        "storage_location": None,
        "layer_query": None,
        "status": "unresolved",
        "blocking": ["bee_habitat"],
        "note": (
            "Sheet: 'RPBB high potential zones/pollinator suitability analysis (Bryan "
            "you have this?) abandon unless we can find an equivalent for pollinator "
            "suitability OR take the bee data as it stands but update to remove any "
            "land use that is no longer compatible'."
        ),
        "crosswalk_rows": [23],
    },
    "risk_of_development_inputs": {
        "description": "Ryan Noe risk-of-development methodology inputs",
        "owner": "Meaghan Dietrich, Hennepin County",
        "storage_location": None,
        "layer_query": None,
        "status": "awaiting_delivery",
        "blocking": ["risk_of_development"],
        "note": (
            "Sheet: 'Buffer utilities and roads. Sewers etc. -- other simple metrics "
            "derived from literature.' Inputs are not itemised anywhere in the registry."
        ),
        "crosswalk_rows": [24],
    },
}

FORTHCOMING_DATASETS = {
    "conservation_action_network": {
        "description": (
            "Conservation Action Network (CAN) - the 2025-2035 Minnesota SWAP "
            "successor to the 2015 Wildlife Action Network. Adds plants as Species in "
            "Greatest Conservation Need and rescores cores and connectivity."
        ),
        "would_supersede": ["WAN", "wildlife_action_network"],
        "status": "not_published",
        "checked": "2026-09-21",
        "evidence": (
            "Full-text search of the Minnesota Geospatial Commons / ArcGIS catalog for "
            "'Conservation Action Network' returns no CAN item. DNR's Wildlife Action "
            "Plan 2025-2035 page describes CAN conceptually as a spatial prioritization "
            "tool but gives no availability date. The layer it would replace "
            "(env-mnwap-wildlife-action-netwrk) was refreshed 2026-09-16 and is not "
            "retired."
        ),
        "shipped_siblings": ["conservation_opportunity_areas", "swap_habitats"],
        "crosswalk_rows": [21, 42],
    },
    "audubon_umrb_dataset": {
        "description": (
            "Forthcoming Upper Mississippi River Basin Audubon Chapter dataset; "
            "Hennepin to obtain it from Audubon on release."
        ),
        "would_supersede": [],
        "status": "not_published",
        "checked": "2026-09-21",
        "evidence": (
            "Sheet says only 'This new dataset is soon to be released by the Audubon "
            "Society'. Note the Gap Notes text on this row actually describes the CAN, "
            "not this dataset - a paste slip in the sheet."
        ),
        "crosswalk_rows": [41],
    },
    "generalized_land_use_2025": {
        "description": "Met Council Generalized Land Use 2025 (Spring 2025 imagery)",
        "would_supersede": ["land_use"],
        "status": "catalogued_not_downloadable",
        "checked": "2026-09-21",
        "evidence": (
            "ArcGIS Hub item c0bca5584e704731880b81c646d5e271 exists, created "
            "2026-07-24, but carries no download links; the bulk path "
            "plan_generl_lnduse2025 returns 404. plan_generl_lnduse2020 remains the "
            "newest downloadable release. Also confirm the product: 'Generalized Land "
            "Use' (existing use, carries LUSE_DESC) differs from 'Regional Planned "
            "Land Use' (planned use)."
        ),
        "crosswalk_rows": [25],
    },
}


def get_pending_datasets() -> Dict[str, Dict[str, Any]]:
    """Datasets the model needs that Hennepin or DNR still has to supply.

    These are NOT acquirable and are deliberately excluded from
    list_available_datasets(). Each entry names an owner and what it blocks.
    """
    return PENDING_HENNEPIN_DATASETS


def get_forthcoming_datasets() -> Dict[str, Dict[str, Any]]:
    """Datasets announced or expected but not yet published anywhere.

    Kept separate from PENDING_HENNEPIN_DATASETS: nobody can send these, they
    simply do not exist yet. Re-check the `evidence` field's claims periodically.
    """
    return FORTHCOMING_DATASETS


def format_gaps_for_llm() -> str:
    """Human-readable summary of what the registry knows it is missing."""
    output = ["## Awaiting delivery (Hennepin County / DNR)", ""]
    for name, info in sorted(PENDING_HENNEPIN_DATASETS.items()):
        output.append(f"- **{name}**: {info['description']}")
        output.append(f"  - Owner: {info['owner']}")
        output.append(f"  - Status: {info['status']}")
        if info.get("layer_query"):
            output.append(f"  - Query: {info['layer_query']}")
        if info.get("blocking"):
            output.append(f"  - Blocks: {', '.join(info['blocking'])}")
    output.append("")
    output.append("## Not yet published anywhere")
    output.append("")
    for name, info in sorted(FORTHCOMING_DATASETS.items()):
        output.append(f"- **{name}**: {info['description']}")
        output.append(f"  - Status: {info['status']} (checked {info['checked']})")
        if info.get("would_supersede"):
            output.append(f"  - Would supersede: {', '.join(info['would_supersede'])}")
    output.append("")
    output.append(
        f"**Pending: {len(PENDING_HENNEPIN_DATASETS)} · "
        f"Forthcoming: {len(FORTHCOMING_DATASETS)}**"
    )
    return "\n".join(output)


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
