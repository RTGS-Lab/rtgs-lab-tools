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
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item 275daac450844f55bbd2efbc6a51584e).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/627/bdry_dnr_wildlife_mgmt_areas_pub.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "yearly",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
        "expected_features": 1731,  # Actual count from test
        "scoring_review_rows": [5],
    },
    "groundwater_recharge": {
        "description": "Mean annual potential groundwater recharge rates from 1996-2010 for Minnesota",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/id/dataset/geos-gw-recharge-1996-2010-mean",
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item 4c7faa8f4005420c95b750ce07fc593a).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/342/geos_gw_recharge_1996_2010_mean.zip",
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
        "scoring_review_rows": [46],
    },
    "scientific_and_natural_areas": {
        "description": "DNR Scientific and Natural Areas",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/bdry-scientific-and-nat-areas",
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item efb2f468b7dc440f8f60143456b978d2).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/650/bdry_scientific_and_nat_areas.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "yearly",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
        "expected_features": 237,  # Actual count from test
        "layer_name": "scientific_and_natural_area_boundaries",  # Specific layer in multi-layer GeoPackage
        "scoring_review_rows": [7],
    },
    "TNC_lands": {
        "description": "The Nature Conservancy lands and waters in Minnesota, North Dakota, & South Dakota",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://geospatial.tnc.org/datasets/53441934d168434e8ff255bda7fd1e3e_1/explore",
        # 2026-11-10: the MNDK 2024 service answers "Invalid URL" (HTTP 200, error 400 body).
        # Switched to the service sheet row 8 names, which answers; 12 features meet the Hennepin bbox.
        "service_url": "https://services.arcgis.com/F7DSX1DSNSiWmOqh/arcgis/rest/services/TNC_Lands_Public_Layer/FeatureServer/0",
        "service_url_retired": "https://services.arcgis.com/F7DSX1DSNSiWmOqh/arcgis/rest/services/TNC_Lands_MNDK_Public_Layer_2024/FeatureServer/1",
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
        "scoring_review_rows": [8, 11],
    },
    "aquatic_areas": {
        "description": "DNR Fisheries Acquisition - Aquatic Management Areas",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/plan-mndnr-fisheries-acquisition",
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item 5e8a2e67f2954268ac8f88cefb09f0df).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/802/plan_mndnr_fisheries_acquisition.zip",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "yearly",
        "spatial_type": "multipolygon",
        "model_critical": True,
        "coordinate_system": "EPSG:26915",
        "scoring_review_rows": [6],
    },
    "MBS_sites": {
        "description": "Minnesota Biological Survey (MBS) - Sites of Biodiversity Significance",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/biota-mcbs-sites-of-biodiversity",
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item cfb2da4b8adb4fa88654cd6e7b604b9b).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/687/biota_mcbs_sites_of_biodiversity.zip",
        # 2026-11-10: the Commons zips now hold compressed FileGDBs (CDF) that GDAL's OpenFileGDB
        # driver cannot read; the feature service answers bbox queries.
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/biota_mcbs_sites_of_biodiversity/FeatureServer/0",
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
        "scoring_review_rows": [19, 21],
    },
    "WAN": {
        "description": "WAN (Wildlife Action Network) - Minnesota Wildlife Action Plan Network",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/env-mnwap-wildlife-action-netwrk",
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item 0c75d22b85254bd79a46d061fb16b035).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/748/env_mnwap_wildlife_action_netwrk.zip",
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/env_mnwap_wildlife_action_netwrk/FeatureServer/0",
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
        "scoring_review_rows": [26],
    },
    "land_use": {
        "description": "Generalized Land Use 2020 - Metropolitan Council Regional Land Use",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/us-mn-state-metc-plan-generl-lnduse2020",
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item 02083b659b744f3e8f0867cf06c8fdb4).
        "download_url": "https://gisdata.metc.state.mn.us/gisdata/Planning/generalized_landuse_2020.zip",
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
        "scoring_review_rows": [37],
    },
    "cemeteries": {
        "description": "Cemeteries - Regional Parcels Dataset (filtered)",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/us-mn-state-metrogis-plan-regional-parcels",
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item 136b28bd0d874076b702ca55b9aafffc).
        "download_url": "https://gisdata.metc.state.mn.us/gisdata/Parcels/plan_regional_parcels.zip",
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
        "scoring_review_rows": [36],
    },
    "watersheds": {
        "description": "DNR Level 9 Watersheds - Hydrologic Unit Boundaries",
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/geos-dnr-watersheds",
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item 9152888e541347428ce4ca6a718c8fd0).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/875/geos_dnr_watersheds.zip",
        # 2026-11-10: layer 4 is DNR Level 08 All Catchments. The current suite has no Level 9
        # auto-catchment layer and no CATCH_POS field (sheet row 45 query); up_count and upadj_cat
        # give upstream links instead.
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/geos_dnr_watersheds/FeatureServer/4",
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
        "scoring_review_rows": [45],
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
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item a1f0f05706f34506879494c218216d16).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/622/bdry_dnr_managed_areas.zip",
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/bdry_dnr_managed_areas/FeatureServer/3",
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
        "scoring_review_rows": [5, 6, 7, 9],
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
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item a5b34c1fbc874f33a5fe09f22a7e836a).
        "download_url": "https://gisdata.metc.state.mn.us/gisdata/Planning/imagine2050_significantecologicalareas.zip",
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
        "scoring_review_rows": [13],
    },
    "mlccs_npc_prediction": {
        "description": (
            "MLCCS/NPC model prediction layer - Random Forest prediction of MLCCS / "
            "Native Plant Community class for the 7-county metro."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gisdata.mn.gov/dataset/biota-mlccs-npc-model-results",
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item 7dfc0f065481429697114cf4894366a7).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/688/biota_mlccs_npc_model_results.zip",
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
        "scoring_review_rows": [20, 22],
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
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item f70069de20464372b75f3edcab7db3a5).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/887/env_swap_habitats.zip",
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/env_swap_habitats/FeatureServer/0",
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
        "scoring_review_rows": [22],
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
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item 8688b4b04b104e4fa104dc855281c6d6).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/886/env_swap_coa.zip",
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/env_swap_coa/FeatureServer/0",
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
        "scoring_review_rows": [27],
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
        # 2026-11-10: the resources.gisdata.mn.gov path returned HTTP 404; current Commons link (item 8159243e8b024922b3a2ea19b0c899dd).
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/866/water_mn_public_waters.zip",
        # 2026-11-10: layer 1 basins (pwi_class P basin / W wetland); watercourses are layer 0.
        "service_url_watercourses": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/water_mn_public_waters/FeatureServer/0",
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/water_mn_public_waters/FeatureServer/1",
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
        "scoring_review_rows": [39, 41, 42],
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
        # 2026-11-10: the state zip is 4.14 GB (Content-Length). For one county, query the FWS
        # Wetlands Mapper service by bbox instead: 43,193 polygons meet the Hennepin bbox
        # (WETLAND_TYPE: Freshwater Emergent 21,299, Pond 12,519, Forested/Shrub 6,134,
        # Riverine 2,433, Lake 808). maxRecordCount 500.
        "service_url": "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0",
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
        "scoring_review_rows": [38, 44],
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
        "scoring_review_rows": [12, 40],
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
        # 2026-11-10: FWS interest tracts (item 6305bf7644f54733980623449617100c, "USFWS National
        # Realty Boundaries", FWS org services.arcgis.com/QVENGdaPbd4LUkLV). 25 tracts meet the
        # Hennepin bbox, all Minnesota Valley NWR or Litchfield WMD. The approved external
        # boundary is National_Wildlife_Refuge_System_Boundaries (item 745ed874c1394da3a9aae50267c9e049).
        "service_url": "https://services.arcgis.com/QVENGdaPbd4LUkLV/arcgis/rest/services/FWSInterest_Simplified_Authoritative/FeatureServer/0",
        "notes": (
            "Hub item confirmed live 2026-09-21; the specific FeatureServer layer id "
            "and whether any refuge unit intersects Hennepin County are unconfirmed."
        ),
        "crosswalk_rows": [3],
        "scoring_review_rows": [3],
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
        # 2026-11-10: the MapServer is TilesOnly (rendered tiles, no values). The TNC vector
        # service Resilient_and_Connected_Network/FeatureServer/0 has 0 features in the
        # Hennepin bbox. No public download of the classes found: model input NOT AVAILABLE.
        "model_availability": "tiles only; no downloadable classes found 2026-11-10",
        "crosswalk_rows": [38],
        "scoring_review_rows": [15],
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
        "scoring_review_rows": [23, 24],
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
        "scoring_review_rows": [39, 41, 42],
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
        "scoring_review_rows": [10],
    },
    # ------------------------------------------------------------------
    # Added 2026-11-10 from the Scoring Review and Recommendations tab (Meaghan Dietrich,
    # Hennepin County; sheet rows in scoring_review_rows). Every URL below answered HTTP 200 and
    # its Hennepin feature count is from a bbox returnCountOnly query, 2026-11-10.
    # ------------------------------------------------------------------
    "metro_conservation_corridors": {
        "description": (
            "Metro Conservation Corridors (MeCC) - DNR regional corridors for conservation and "
            "restoration in the 7-county metro; LCCMR uses them to site grants."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gis.data.mn.gov/datasets/minnesota::metro-conservation-corridors-1/about",
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/706/env_conservation_corridors.zip",
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/env_conservation_corridors/FeatureServer/0",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "last_updated": "2026-09-16",
        "agol_item_id": "f8e488bd709244ab99d3dc864a362bd3",
        # Fields: mecc only. 3 features meet the Hennepin bbox.
        "scoring_review_rows": [16],
    },
    "priority_natural_resource_corridors": {
        "description": (
            "Hennepin County Priority Natural Resource Corridors (22 corridors). Sheet row 14 "
            "removes this layer from the model: the corridors are meant to be a model result."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gis.data.mn.gov/datasets/f066ef57b3fe40ebbfefaa318a261d75_2/about",
        "service_url": "https://gis.hennepin.us/arcgis/rest/services/HennepinData/ENVIRONMENT/MapServer/2",
        "access_method": "rest_api",
        "file_format": "mapserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "expected_features": 22,
        "agol_item_id": "f066ef57b3fe40ebbfefaa318a261d75",
        "model_use": "removed per sheet row 14",
        "scoring_review_rows": [14],
    },
    "dnr_native_plant_communities": {
        "description": (
            "MNDNR Native Plant Communities - mapped NPC polygons with class, condition rank, "
            "biodiversity significance and state (S) / global (G) conservation ranks."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gis.data.mn.gov/maps/a451392396c74acc921a3d2f3f32c5b2/about",
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/876/biota_dnr_native_plant_comm.zip",
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/biota_dnr_native_plant_comm/FeatureServer/7",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "last_updated": "2026-11-10",
        "agol_item_id": "a451392396c74acc921a3d2f3f32c5b2",
        # Service layer 7 "Dnr Native Plant Communities": 876 polygons meet the Hennepin bbox.
        # Fields the sheet scores on: s_rank_highest_risk (S1-S5; row 18 proposal),
        # biodiversity_significance_rank, condition_rank (A-D).
        "key_attributes": {
            "s_rank_highest_risk": "S1..S5, parenthesised when uncertain",
            "condition_rank": "A, AB, B, BC, C, CD, D, NR",
            "biodiversity_significance_rank": "Outstanding, High, Moderate, Below",
        },
        "replaces": "land_cover (MLCCS) for sheet rows 18 and 20",
        "scoring_review_rows": [18, 20],
    },
    "rpbb_high_potential_zones": {
        "description": (
            "USFWS Rusty Patched Bumble Bee (Bombus affinis) High Potential Zone model, 2025 "
            "update: high and low potential zones around recent records."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://www.arcgis.com/home/item.html?id=b2e7e0c1ddad4f50a20bcfc1bfcfbbcb",
        "service_url": "https://services.arcgis.com/QVENGdaPbd4LUkLV/arcgis/rest/services/RPBB_HPZModel_Update/FeatureServer/0",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:3857",
        "data_source": "U.S. Fish and Wildlife Service",
        "agol_item_id": "b2e7e0c1ddad4f50a20bcfc1bfcfbbcb",
        # Field Zone: "High Potential Zone" (gridcode 1) / "Low Potential Zone" (gridcode 4).
        # 12 features meet the Hennepin bbox. Layer of web map 2716d871 (sheet row 30 link);
        # the same service is the "other link" of row 29.
        "scoring_review_rows": [29, 30],
    },
    "important_bird_areas_public": {
        "description": (
            "National Audubon Society Important Bird Areas (IBA) public polygons, current "
            "boundaries (item modified 2026-11-05)."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://www.arcgis.com/home/item.html?id=087b591fd12d4dc482a4d9a3e2b60246",
        "service_url": "https://services1.arcgis.com/lDFzr3JyGEn5Eymu/arcgis/rest/services/iba_polygons_public/FeatureServer/0",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:3857",
        "data_source": "National Audubon Society",
        "agol_item_id": "087b591fd12d4dc482a4d9a3e2b60246",
        # 6 IBAs meet the Hennepin bbox (status Identified 4, Recognized 2).
        "supersedes": "important_bird_areas (2020 geodatabase, Summer 2019)",
        "scoring_review_rows": [31],
    },
    "audubon_migratory_stopover_water_mn": {
        "description": (
            "National Audubon Society Migratory Stopover Importance for Water System Species "
            "(Minnesota), eBird Zonation priority, published 2026-10-09."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://www.arcgis.com/home/item.html?id=db7f5dee9ac84ed5b5f6abafd8281778",
        "service_url": "https://services1.arcgis.com/lDFzr3JyGEn5Eymu/arcgis/rest/services/CEST_MN_eBird_Zonation_Water/FeatureServer/0",
        "access_method": "rest_api",
        "file_format": "featureserver",
        "update_frequency": "static",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "unknown",
        "data_source": "National Audubon Society",
        "agol_item_id": "db7f5dee9ac84ed5b5f6abafd8281778",
        # Fields: gridcode (sheet: importance rank 0-99). 385 polygons meet the Hennepin bbox.
        "scoring_review_rows": [32],
    },
    "lakes_of_biological_significance": {
        "description": (
            "DNR Lakes of Biological Significance - lakes classed outstanding, high or moderate "
            "for aquatic plants, fish, birds or herptiles."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gis.data.mn.gov/datasets/dc159f8d412848f8819044a649577be6_0/about",
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/733/env_lakes_of_biological_signific.zip",
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/env_lakes_of_biological_signific/FeatureServer/0",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "last_updated": "2026-09-16",
        "agol_item_id": "dc159f8d412848f8819044a649577be6",
        # Field lbs_class: Outstanding / High / Moderate. 46 lakes meet the Hennepin bbox.
        "scoring_review_rows": [33],
    },
    "shallow_lakes_dnr_wildlife": {
        "description": (
            "Shallow Lakes Identified by DNR Wildlife - shallow lakes for wildlife habitat "
            "restoration and enhancement (layer 0) and the priority subset (layer 1)."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gis.data.mn.gov/maps/ad5983f428b84b4fbc8adfb946a06c3b/about",
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/847/water_shallow_lakes_id_by_wldlif.zip",
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/water_shallow_lakes_id_by_wldlif/FeatureServer/0",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "last_updated": "2026-09-17",
        "agol_item_id": "ad5983f428b84b4fbc8adfb946a06c3b",
        # 211 shallow lakes meet the Hennepin bbox (40 in the priority layer).
        "scoring_review_rows": [34],
    },
    "land_use_2025": {
        "description": (
            "Metropolitan Council Generalized Land Use 2025 (field Dscrpt2025). Supersedes "
            "land_use (2020) for sheet row 37."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gis.data.mn.gov/datasets/c0bca5584e704731880b81c646d5e271_2/about",
        "download_url": "https://gisdata.metc.state.mn.us/gisdata/Planning/generalized_landuse_2025.zip",
        "service_url": "https://arcgis.metc.state.mn.us/data1/rest/services/planning/Land_Use/FeatureServer/2",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "periodic",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "temporal_coverage": "2025",
        "agol_item_id": "c0bca5584e704731880b81c646d5e271",
        # 2026-11-10: the zip answers HTTP 200 (25.6 MB). FORTHCOMING generalized_land_use_2025
        # recorded it as not downloadable on 2026-09-21.
        "scoring_review_rows": [37],
    },
    "fema_nfhl_flood_hazard_zones": {
        "description": (
            "FEMA National Flood Hazard Layer (NFHL), flood hazard zones: 1% annual chance "
            "(100-year) and 0.2% annual chance (500-year) areas."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://www.fema.gov/flood-maps/national-flood-hazard-layer",
        "service_url": "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28",
        "access_method": "rest_api",
        "file_format": "mapserver",
        "update_frequency": "continuous",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:4269",
        "data_source": "Federal Emergency Management Agency",
        # Fields FLD_ZONE and ZONE_SUBTY: 100-year = A* zones; 500-year = X with ZONE_SUBTY
        # "0.2 PCT ANNUAL CHANCE FLOOD HAZARD". Statewide pull is too large: query a bbox.
        "supersedes": "floodplains (2020 geodatabase)",
        "scoring_review_rows": [43],
    },
    "water_table_aquifer_vulnerability": {
        "description": (
            "Minnesota Water Table Aquifer Vulnerability (MDA) - vulnerability rating of the "
            "water table aquifer, after Porcher (1989)."
        ),
        "source_type": "mn_geospatial",
        "extractor_class": "MNGeospatialExtractor",
        "url": "https://gis.data.mn.gov/datasets/minnesota::minnesota-water-table-aquifer-vulnerability-1/about",
        "download_url": "https://operations.gis.data.mn.gov/api/publicdownload/download/262/water_aquifer_vulnerability.zip",
        "service_url": "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_mda/water_aquifer_vulnerability/FeatureServer/0",
        "access_method": "download",
        "file_format": "geopackage",
        "update_frequency": "static",
        "spatial_type": "multipolygon",
        "model_critical": False,
        "coordinate_system": "EPSG:26915",
        "data_source": "Minnesota Department of Agriculture",
        "agol_item_id": "12e18d9bb4db4a1fa5385de26c1d4101",
        # Field combined_vulnerabilityrating: High 271, Medium 391, Low 14, Unrated 145 polygons
        # in the Hennepin bbox. Sheet row 47 names it "Combined_VulnerabilityRating".
        "replaces": "groundwater_susceptibility (2020 geodatabase) for sheet row 47",
        "scoring_review_rows": [47],
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
        "scoring_review_rows": [29],
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
        "scoring_review_rows": [43],
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
        "scoring_review_rows": [38, 44],
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
        "scoring_review_rows": [22],
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
        "scoring_review_rows": [45],
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
        "scoring_review_rows": [31],
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
        "scoring_review_rows": [19, 21],
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
        "scoring_review_rows": [13, 18, 20, 22],
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
        "scoring_review_rows": [46],
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
        "scoring_review_rows": [13, 14],
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
        "scoring_review_rows": [2, 3, 5, 6, 7, 8, 40],
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
        "scoring_review_rows": [20],
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
        "scoring_review_rows": [35, 36, 37, 38, 39, 40],
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
        "scoring_review_rows": [41, 42],
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
        "scoring_review_rows": [47],
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
        "scoring_review_rows": [26],
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
        "status": "delivered",  # 2026-10-06, see HENNEPIN_DELIVERED_DATASETS
        "delivered_as": ["hc_all_known_easements_combined_2026"],
        "blocking": ["protected_areas_hc"],
        "note": (
            "Compiled database of Hennepin County, Minnesota Land Trust and BWSR "
            "easements. PAD-US does NOT contain these - it is the one gap no public "
            "dataset closes. Sheet says 'Need to update regularly'."
        ),
        "crosswalk_rows": [2],
        "scoring_review_rows": [2],
    },
    "parks_natural_resource_significance": {
        "description": "Hennepin County Parks of Natural Resource Significance",
        "owner": "Hennepin County GIS (Meaghan to ask Alex how the layer is generated)",
        "storage_location": "File network",
        "layer_query": "NaturalResources_Category <> 'Amenities'",
        "status": "delivered",  # 2026-10-06
        "delivered_as": ["parks_natural_resources_analysis"],
        # 2026-11-03: Hennepin found Three Rivers Park District parks missing from this layer
        # and from PAD-US (trpd_park_boundaries, trpd_gap_subset).
        "blocking": ["protected_areas_hc"],
        "note": (
            "Built on the HC parks layer; Kristine identified regionally significant "
            "parks using standard criteria."
        ),
        "crosswalk_rows": [4],
        "scoring_review_rows": [4],
    },
    "potential_easements": {
        "description": "Hennepin County potential easements - the candidate sites the model scores",
        "owner": "Meaghan Dietrich, Hennepin County",
        "storage_location": "File network",
        "layer_query": "Status IN ('Current Applicant', 'On-Hold', 'Selected')",
        "status": "candidate_delivered",  # Easement_Inquiries, not confirmed as this layer
        "delivered_as": ["hc_easement_inquiries"],
        "blocking": ["the model's analysis units"],
        "note": (
            "Highest priority of the pending deliveries: this is the candidate-site "
            "layer the whole suitability model scores against."
        ),
        "crosswalk_rows": [12],
        "scoring_review_rows": [17],
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
        "scoring_review_rows": [23, 24],
    },
    "nhis_rare_features": {
        "description": "DNR Natural Heritage Information System (NHIS) rare features polygons",
        "owner": "Minnesota DNR (restricted; Hennepin plans to meet DNR)",
        "storage_location": "GIS warehouse (restricted)",
        "layer_query": {
            "0-1 mile": "name_cat NOT IN ('Other (Ecological)')",
            "1-3 mile": "name_cat NOT IN ('Other (Ecological)', 'Vascular Plant')",
        },
        "status": "derived_product_delivered",  # NHIS per PLS section, 2026-11-02
        "delivered_as": ["nhis_summary_by_section"],
        "blocking": ["NHIS Occurrence criterion (both distance bands)"],
        "note": (
            "Restricted data by direct request, so no public registry entry is "
            "possible. Open question: does Hennepin GIS process NHIS into a shareable "
            "derived product, or does the lab need its own DNR licence? Public viewer "
            "only: https://osaportal.gisdata.mn.gov/public-map"
        ),
        "crosswalk_rows": [20],
        "scoring_review_rows": [25],
    },
    "pollinator_suitability": {
        "description": "Replacement for the Ryan Noe bee pollination habitat layer",
        "owner": "[NEEDS CONFIRM] Bryan Runck - Meaghan asks directly whether he holds this",
        "storage_location": None,
        "layer_query": None,
        "status": "candidate_delivered",  # Bee_Habitat_Areas 2026-10-06, classes unexplained
        "delivered_as": ["bee_habitat_areas_2026"],
        "blocking": ["bee_habitat"],
        "note": (
            "Sheet: 'RPBB high potential zones/pollinator suitability analysis (Bryan "
            "you have this?) abandon unless we can find an equivalent for pollinator "
            "suitability OR take the bee data as it stands but update to remove any "
            "land use that is no longer compatible'."
        ),
        "crosswalk_rows": [23],
        "scoring_review_rows": [29],
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
        "scoring_review_rows": [35],
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
        "checked": "2026-11-10",
        # 2026-11-10: Commons hub search "Conservation Action Network" returns only WAN, COA
        # and the SNA Marxan layer. Still not published.
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
        "scoring_review_rows": [26, 28],
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
        "status": "published",  # 2026-11-10: zip answers HTTP 200
        "now_acquirable_as": "land_use_2025",
        "checked": "2026-11-10",
        "evidence": (
            "ArcGIS Hub item c0bca5584e704731880b81c646d5e271 exists, created "
            "2026-07-24, but carries no download links; the bulk path "
            "plan_generl_lnduse2025 returns 404. plan_generl_lnduse2020 remains the "
            "newest downloadable release. Also confirm the product: 'Generalized Land "
            "Use' (existing use, carries LUSE_DESC) differs from 'Regional Planned "
            "Land Use' (planned use)."
        ),
        "crosswalk_rows": [25],
        "scoring_review_rows": [37],
    },
    # --- NRPC webinar 2026-11-20 ---
    "hennepin_suitability_v2_results": {
        "description": (
            "Hennepin County Parcel Prioritization Model results, V2: re-run on the "
            "2026 inputs (overall plus the six categories), to replace the v1 layers "
            "in the NRPC map for the 2026-11-20 webinar."
        ),
        "would_supersede": [
            "hennepin_suitability_v1_countywide",
            "hennepin_suitability_v1_parcel_detail",
        ],
        "status": "not_published",
        "checked": "2026-11-04",
        "evidence": (
            "The UMN org's public services list (services.arcgis.com/8df8p0NlLFEShl0r) "
            "has only the two v1 services; an AGOL search of runck* items for "
            "suitability/prioritization/NRPC returns no V2 item. V2 scope (Natural "
            "Spaces fix, Water outlier, NHIS rule, breaks) is Bryan's open decision."
        ),
    },
}


# Datasets Hennepin County has DELIVERED to UMN by email (private; not acquirable by URL).
# The extractor cannot fetch these; they live where the lab files deliveries (see each entry's
# `delivery`). Kept outside MN_GEOSPATIAL_DATASETS / FGDB_DATASETS so list_available_datasets()
# never offers something unfetchable -- same rule as PENDING_HENNEPIN_DATASETS. An entry here
# whose `fulfils` names a PENDING key is the delivery that pending row was waiting for.
HENNEPIN_DELIVERED_DATASETS = {
    # --- Delivered 2026-10-06 (EDA: W41WED00 12-context-20261007-eda-findings.md) ---
    "hc_all_known_easements_combined_2026": {
        "description": (
            "All known conservation easements in Hennepin County, combined 2026 "
            "(fields EasementID, EasementHolder, Acres only); layer "
            "All_Known_Easements_Combined_2026 of All Easement Data Compilation.gdb."
        ),
        "source_type": "hennepin_delivery",
        "spatial_type": "multipolygon",
        "coordinate_system": "ESRI:103734",
        "expected_features": 227,
        "file_name": "All Easement Data Compilation.gdb.zip",
        "layer_name": "All_Known_Easements_Combined_2026",
        "delivery": "thread:00000000000366cd, Meaghan Dietrich, 2026-10-06 13:12 CDT",
        "fulfils": "established_conservation_easements",
        # Overlaps itself: summed 6,967 ac vs dissolved union 6,874.3 ac -- dissolve first.
        "scoring_review_rows": [2],
    },
    "hc_easement_inquiries": {
        "description": (
            "Hennepin County easement inquiries (layer Easement_Inquiries of the same "
            "gdb): the only candidate for the potential-easements layer."
        ),
        "source_type": "hennepin_delivery",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 29,
        "file_name": "All Easement Data Compilation.gdb.zip",
        "layer_name": "Easement_Inquiries",
        "delivery": "thread:00000000000366cd, Meaghan Dietrich, 2026-10-06 13:12 CDT",
        "candidate_for": "potential_easements",
        # AcquisStatus vocabulary does not match the registry query; ContactName holds
        # landowner names -- never screen-share the attribute table. [NEEDS CONFIRM, Bryan]
        "scoring_review_rows": [17],
    },
    "padus_county_clip_nrvalue": {
        "description": (
            "PAD-US clipped to Hennepin County with an undocumented 'NRValue' filter, "
            "prepared by Hennepin County."
        ),
        "source_type": "hennepin_delivery",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:3857",
        "expected_features": 105,
        "file_name": "PADUS_CountyClip_NRValue.zip",
        "layer_name": "PADUS_CountyClip_NRValue",
        "delivery": "thread:00000000000366cd, Meaghan Dietrich, 2026-10-06 13:12 CDT",
        "relates_to": "pad_us",
        # 88 of 105 are GAP 4; the NRValue filter is undocumented [NEEDS CONFIRM].
        "scoring_review_rows": [12, 40],
    },
    "bee_habitat_areas_2026": {
        "description": (
            "Bee habitat areas, classes 1 and 2 (Hennepin County delivery; Noe layer "
            "as-is or updated is not stated)."
        ),
        "source_type": "hennepin_delivery",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 2,
        "file_name": "Bee_Habitat_Areas.zip",
        "layer_name": "Bee_Habitat_Areas",
        "delivery": "thread:00000000000366cd, Meaghan Dietrich, 2026-10-06 13:12 CDT",
        "candidate_for": "pollinator_suitability",
        # Both polygons invalid; ~2.96M vertices; no field explains classes 1/2.
        "scoring_review_rows": [29],
    },
    "parks_natural_resources_analysis": {
        "description": (
            "Hennepin County parks with NaturalResources_Category, layer "
            "Parks_NaturalResources_Analysis of LandCover2011_Parks.gdb."
        ),
        "source_type": "hennepin_delivery",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 1044,
        "file_name": "LandCover2011_Parks.gdb.zip",
        "layer_name": "Parks_NaturalResources_Analysis",
        "delivery": "thread:00000000000366cd, Meaghan Dietrich, 2026-10-06 13:20 CDT",
        "fulfils": "parks_natural_resource_significance",
        "attribute_filter": {"description": "Parks of natural resource significance", "columns": ["NaturalResources_Category"], "values": ["Natural Area Park", "Regionally Significant", "Nature Preserve"], "match_type": "any"},
        # Equivalent to the sheet's NaturalResources_Category <> 'Amenities' (keeps 402).
        "scoring_review_rows": [4],
    },
    "landcover2011_parks_composition": {
        "description": (
            "2011 land-cover composition inside Hennepin County parks, layer "
            "LandCover2011_Parks_Composition of LandCover2011_Parks.gdb."
        ),
        "source_type": "hennepin_delivery",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 3664,
        "file_name": "LandCover2011_Parks.gdb.zip",
        "layer_name": "LandCover2011_Parks_Composition",
        "delivery": "thread:00000000000366cd, Meaghan Dietrich, 2026-10-06 13:20 CDT",
        # 246 invalid geometries; 2011 basis.
    },
    # --- Delivered 2026-11-02 / 2026-11-03 ---
    "nhis_summary_by_section": {
        "description": (
            "NHIS observations summarised per PLS section by Hennepin County (derived "
            "product of the restricted DNR NHIS data)."
        ),
        "source_type": "hennepin_delivery",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 746,
        "file_name": "NHIS_Summary_by_Section.zip",
        "layer_name": "NHIS_Summary_by_Section",
        "delivery": "thread:0000000000036996, Meaghan Dietrich, 2026-11-02 15:33 CST",
        "fulfils": "nhis_rare_features",
        "scoring_rule": (
            "area-weighted: 'the parcel should receive a score based on the weight by "
            "percent of total acreage in each section' (Meaghan, 2026-11-02)"
        ),
        # Her email names the field Count_of_SpObs; the delivered .dbf has no such field --
        # columns include Polygon_Co and sum_Area_S. Which is the count? [NEEDS CONFIRM]
        "scoring_review_rows": [25],
    },
    "trpd_gap_subset": {
        "description": (
            "Three Rivers Park District parks missing from both the county parks layer "
            "and PAD-US, subset exported by Hennepin County."
        ),
        "source_type": "hennepin_delivery",
        "spatial_type": "multipolygon",
        "coordinate_system": "EPSG:26915",
        "expected_features": 6,
        "file_name": "TRPD_GAP_data.zip",
        "layer_name": "TRPD_GAP_data",
        "delivery": "thread:0000000000036996, Meaghan Dietrich, 2026-11-03 14:02 CST",
        "relates_to": "trpd_park_boundaries",
        # Her email: seven features not captured, Hopkins Depot and a golf course removed.
        # The file holds 6: Big Island, Goose, Wawatasso, Kingswood, North Corridor,
        # South Corridor (7 - 2 = 5, so one is extra [NEEDS CONFIRM]).
        "scoring_review_rows": [10],
    },
}


def get_delivered_datasets() -> Dict[str, Dict[str, Any]]:
    """Private datasets Hennepin County has sent by email, with delivery provenance."""
    return HENNEPIN_DELIVERED_DATASETS

# NRPC partner datasets submitted through the 'NRPC Data Submission' Survey123
# (item 8c0788a5475d46c7bf314f57c55b2278) and QA/QC'd by UMN. One entry per QA/QC report in
# the UMN shared drive folder 'QAQC Reports/<org>/<dataset>/report.html'. The data files are
# survey attachments (AGOL sign-in), so these are catalog entries: not acquirable by the
# extractor, never returned by list_available_datasets(). `agol_upload` is 'ready' for the 26
# layers on the 2026-10-13 upload checklist and 'on_hold' for the 26 Audrey Robeson is
# following up (thread:00000000000365b6, 2026-09-30). None is among the UMN org's public
# items on 2026-11-04 (an anonymous search cannot see group-only shares).
NRPC_PARTNER_SUBMISSIONS = {
    # --- Bloomington (2) ---
    "nrpc_bloomington_barr_engineering_prioritization_plan": {
        "description": (
            "Bloomington - Barr Engineering Prioritization Plan (NRPC partner "
            "submission, file stem Bloomington_Resto_Prty)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 256,
        "jurisdiction": "Bloomington",
        "file_stem": "Bloomington_Resto_Prty",
        "submission_date": "2026-01-21",
        "qaqc_report": "QAQC Reports/Bloomington/Barr Engineering Prioritization Plan/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.0,
        "agol_upload": "ready",
    },
    "nrpc_bloomington_natural_resources_data": {
        "description": (
            "Bloomington - Natural Resources Data (NRPC partner submission, file stem "
            "Land_Cover)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 496,
        "jurisdiction": "Bloomington",
        "file_stem": "Land_Cover",
        "submission_date": "2026-03-11",
        "qaqc_report": "QAQC Reports/Bloomington/Natural Resources Data/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.8,
        "agol_upload": "ready",
    },
    # --- Champlin (1) ---
    "nrpc_champlin_parks": {
        "description": (
            "Champlin - Parks (NRPC partner submission, file stem Parks_Map)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 34,
        "jurisdiction": "Champlin",
        "file_stem": "Parks_Map",
        "submission_date": "2026-03-18",
        "qaqc_report": "QAQC Reports/Champlin/Parks/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.33,
        "agol_upload": "ready",
    },
    # --- Eden Prairie (16) ---
    "nrpc_eden_prairie_archeological_buffers": {
        "description": (
            "Eden Prairie - Archeological Buffers (NRPC partner submission, file stem "
            "ArcheologicalBuffers)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 42,
        "jurisdiction": "Eden Prairie",
        "file_stem": "ArcheologicalBuffers",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Archeological Buffers/report.html",
        "qaqc_report_date": "2026-06-15",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.4,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_bluffs": {
        "description": (
            "Eden Prairie - Bluffs (NRPC partner submission, file stem Bluffs)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 1082,
        "jurisdiction": "Eden Prairie",
        "file_stem": "Bluffs",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Bluffs/report.html",
        "qaqc_report_date": "2026-06-15",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.4,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_cultural_resources_buffer": {
        "description": (
            "Eden Prairie - Cultural Resources Buffer (NRPC partner submission, file "
            "stem CulturalResourcesBuffer)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 1,
        "jurisdiction": "Eden Prairie",
        "file_stem": "CulturalResourcesBuffer",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Cultural Resources Buffer/report.html",
        "qaqc_report_date": "2026-06-17",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.4,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_easements": {
        "description": (
            "Eden Prairie - Easements (NRPC partner submission, file stem "
            "easements_lyr)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 363,
        "jurisdiction": "Eden Prairie",
        "file_stem": "easements_lyr",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Easements/report.html",
        "qaqc_report_date": "2026-07-07",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.67,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_floodplains": {
        "description": (
            "Eden Prairie - Floodplains (NRPC partner submission, file stem "
            "Floodplains)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 1206,
        "jurisdiction": "Eden Prairie",
        "file_stem": "Floodplains",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Floodplains/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.4,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_guideplan_aspire": {
        "description": (
            "Eden Prairie - Guideplan Aspire (NRPC partner submission, file stem "
            "Guideplan_Aspire)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 19751,
        "jurisdiction": "Eden Prairie",
        "file_stem": "Guideplan_Aspire",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Guideplan Aspire/report.html",
        "qaqc_report_date": "2026-06-30",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.17,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_he_epc_locations": {
        "description": (
            "Eden Prairie - HE EPC Locations (NRPC partner submission, file stem "
            "HE_EPC_Locations)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "unknown",
        "coordinate_system": "unknown",
        "expected_features": 31,
        "jurisdiction": "Eden Prairie",
        "file_stem": "HE_EPC_Locations",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/HE EPC Locations/report.html",
        "qaqc_report_date": "2026-06-30",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.2,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_hpc_sites": {
        "description": (
            "Eden Prairie - HPC Sites (NRPC partner submission, file stem HPCSites)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "unknown",
        "coordinate_system": "unknown",
        "expected_features": 17,
        "jurisdiction": "Eden Prairie",
        "file_stem": "HPCSites",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/HPC Sites/report.html",
        "qaqc_report_date": "2026-06-30",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 4.8,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_natural_resources_management": {
        "description": (
            "Eden Prairie - Natural Resources Management (NRPC partner submission, "
            "file stem NR_Management)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 164,
        "jurisdiction": "Eden Prairie",
        "file_stem": "NR_Management",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Natural Resources Management/report.html",
        "qaqc_report_date": "2026-06-30",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.0,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_shoreland_buffer": {
        "description": (
            "Eden Prairie - Shoreland Buffer (NRPC partner submission, file stem "
            "Shoreland_Buffer)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 1,
        "jurisdiction": "Eden Prairie",
        "file_stem": "Shoreland_Buffer",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Shoreland Buffer/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 5.0,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_social_trails": {
        "description": (
            "Eden Prairie - Social Trails (NRPC partner submission, file stem "
            "SocialTrails)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multilinestring",
        "coordinate_system": "unknown",
        "expected_features": 147,
        "jurisdiction": "Eden Prairie",
        "file_stem": "SocialTrails",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Social Trails/report.html",
        "qaqc_report_date": "2026-06-30",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.6,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_trails": {
        "description": (
            "Eden Prairie - Trails (NRPC partner submission, file stem Trail_System)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multilinestring",
        "coordinate_system": "unknown",
        "expected_features": 2600,
        "jurisdiction": "Eden Prairie",
        "file_stem": "Trail_System",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Trails/report.html",
        "qaqc_report_date": "2026-06-30",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.67,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_tree_inventory": {
        "description": (
            "Eden Prairie - Tree Inventory (NRPC partner submission, file stem "
            "TreeInventory)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "point",
        "coordinate_system": "unknown",
        "expected_features": 31164,
        "jurisdiction": "Eden Prairie",
        "file_stem": "TreeInventory",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Tree Inventory/report.html",
        "qaqc_report_date": "2026-06-30",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.0,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_watersheds": {
        "description": (
            "Eden Prairie - Watersheds (NRPC partner submission, file stem "
            "Watersheds)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 15,
        "jurisdiction": "Eden Prairie",
        "file_stem": "Watersheds",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Watersheds/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.2,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_wetlands": {
        "description": (
            "Eden Prairie - Wetlands (NRPC partner submission, file stem Wetlands)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 651,
        "jurisdiction": "Eden Prairie",
        "file_stem": "Wetlands",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Wetlands/report.html",
        "qaqc_report_date": "2026-07-08",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.8,
        "agol_upload": "ready",
    },
    "nrpc_eden_prairie_zoning": {
        "description": (
            "Eden Prairie - Zoning (NRPC partner submission, file stem Zoning)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 19824,
        "jurisdiction": "Eden Prairie",
        "file_stem": "Zoning",
        "submission_date": "2026-04-14",
        "qaqc_report": "QAQC Reports/Eden Prairie/Zoning/report.html",
        "qaqc_report_date": "2026-06-29",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.4,
        "agol_upload": "ready",
    },
    # --- MWMO (3) ---
    "nrpc_mwmo_boundary": {
        "description": (
            "MISSISSIPPI - Boundary (NRPC partner submission, file stem "
            "MWMOBoundary_July2024)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 1,
        "jurisdiction": "MISSISSIPPI",
        "file_stem": "MWMOBoundary_July2024",
        "submission_date": "2025-10-27",
        "qaqc_report": "QAQC Reports/MWMO/Boundary/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 4.8,
        "agol_upload": "ready",
        # Upload copy: W42 task dir 02-08-output-20261012-MWMO_Boundary_fixed.zip (NAME field
        # added by UMN; Aaron Goemann to confirm, thread:0000000000034652).
    },
    "nrpc_mwmo_soils_anoka_county": {
        "description": (
            "MISSISSIPPI - Soils - Anoka County (NRPC partner submission, file stem "
            "MWMO_Soils_Anoka)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 130,
        "jurisdiction": "MISSISSIPPI",
        "file_stem": "MWMO_Soils_Anoka",
        "submission_date": "2026-03-20",
        "qaqc_report": "QAQC Reports/MWMO/Soils - Anoka County/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.4,
        "agol_upload": "ready",
    },
    "nrpc_mwmo_soils_hennepin_county": {
        "description": (
            "MISSISSIPPI - Soils - Hennepin County (NRPC partner submission, file stem "
            "MWMO_Soils_Hennepin_Ramsey)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 921,
        "jurisdiction": "MISSISSIPPI",
        "file_stem": "MWMO_Soils_Hennepin_Ramsey",
        "submission_date": "2026-03-20",
        "qaqc_report": "QAQC Reports/MWMO/Soils - Hennepin County/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.4,
        "agol_upload": "ready",
    },
    # --- NMCWD (4) ---
    "nrpc_nmcwd_habitat_corridor": {
        "description": (
            "NINE MILE CREEK - Habitat Corridor (NRPC partner submission, file stem "
            "Habitat_Corridor)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 3,
        "jurisdiction": "NINE MILE CREEK",
        "file_stem": "Habitat_Corridor",
        "submission_date": "2026-06-25",
        "qaqc_report": "QAQC Reports/NMCWD/Habitat Corridor/report.html",
        "qaqc_report_date": "2026-07-09",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 4.6,
        "agol_upload": "ready",
    },
    "nrpc_nmcwd_habitat_patches": {
        "description": (
            "NINE MILE CREEK - Habitat Patches (NRPC partner submission, file stem "
            "Habitat_patches)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 261,
        "jurisdiction": "NINE MILE CREEK",
        "file_stem": "Habitat_patches",
        "submission_date": "2026-06-25",
        "qaqc_report": "QAQC Reports/NMCWD/Habitat Patches/report.html",
        "qaqc_report_date": "2026-07-09",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.4,
        "agol_upload": "ready",
    },
    "nrpc_nmcwd_stream_erosion_risk": {
        "description": (
            "NINE MILE CREEK - Stream Erosion Risk (NRPC partner submission, file stem "
            "Stream_erosion_risk)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "unknown",
        "coordinate_system": "unknown",
        "expected_features": 73,
        "jurisdiction": "NINE MILE CREEK",
        "file_stem": "Stream_erosion_risk",
        "submission_date": "2026-06-25",
        "qaqc_report": "QAQC Reports/NMCWD/Stream Erosion Risk/report.html",
        "qaqc_report_date": "2026-07-09",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.4,
        "agol_upload": "ready",
    },
    "nrpc_nmcwd_vulnerability_scoring": {
        "description": (
            "NINE MILE CREEK - Vulnerability Scoring (NRPC partner submission, file "
            "stem Vulnerability_Scoring)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 164,
        "jurisdiction": "NINE MILE CREEK",
        "file_stem": "Vulnerability_Scoring",
        "submission_date": "2026-06-25",
        "qaqc_report": "QAQC Reports/NMCWD/Vulnerability Scoring/report.html",
        "qaqc_report_date": "2026-07-09",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.4,
        "agol_upload": "ready",
    },
    # --- MCWD (14) ---
    "nrpc_mcwd_administrative_boundary": {
        "description": (
            "MINNEHAHA CREEK - Administrative Boundary (NRPC partner submission, file "
            "stem MCWD_Administrative_Boundary)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 1,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MCWD_Administrative_Boundary",
        "submission_date": "2025-10-08",
        "qaqc_report": "QAQC Reports/MCWD/Administrative Boundary/report.html",
        "qaqc_report_date": "2026-06-10",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 4.8,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_capital_improvement_projects": {
        "description": (
            "MINNEHAHA CREEK - Capital Improvement Projects (NRPC partner submission, "
            "file stem MCWD_Capital_Improvement_Projects)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "point",
        "coordinate_system": "unknown",
        "expected_features": 117,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MCWD_Capital_Improvement_Projects",
        "submission_date": "2026-03-13",
        "qaqc_report": "QAQC Reports/MCWD/Capital Improvement Projects/report.html",
        "qaqc_report_date": "2026-06-09",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.0,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_functional_assessments_of_wetlands": {
        "description": (
            "MINNEHAHA CREEK - Functional Assessments of Wetlands (NRPC partner "
            "submission, file stem MCWD_Functional_Assessments_of_Wetlands)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 6752,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MCWD_Functional_Assessments_of_Wetlands",
        "submission_date": "2025-10-08",
        "qaqc_report": "QAQC Reports/MCWD/Functional Assessments of Wetlands/report.html",
        "qaqc_report_date": "2026-06-10",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.17,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_hydrologic_boundary": {
        "description": (
            "MINNEHAHA CREEK - Hydrologic Boundary (NRPC partner submission, file stem "
            "MCWD_Hydrologic_Boundary)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 1,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MCWD_Hydrologic_Boundary",
        "submission_date": "2025-10-08",
        "qaqc_report": "QAQC Reports/MCWD/Hydrologic Boundary/report.html",
        "qaqc_report_date": "2026-06-10",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 5.0,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_ms4_ditch": {
        "description": (
            "MINNEHAHA CREEK - MS4 Ditch (NRPC partner submission, file stem "
            "MS4_DITCH)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multilinestring",
        "coordinate_system": "unknown",
        "expected_features": 18,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MS4_DITCH",
        "submission_date": "2025-10-08",
        "qaqc_report": "QAQC Reports/MCWD/MS4 Ditch/report.html",
        "qaqc_report_date": "2026-07-08",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.4,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_ms4_drainage_area": {
        "description": (
            "MINNEHAHA CREEK - MS4 Drainage Area (NRPC partner submission, file stem "
            "MS4_DRAINAGE_AREA)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 10,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MS4_DRAINAGE_AREA",
        "submission_date": "2025-10-08",
        "qaqc_report": "QAQC Reports/MCWD/MS4 Drainage Area/report.html",
        "qaqc_report_date": "2026-07-08",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.8,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_ms4_outfalls": {
        "description": (
            "MINNEHAHA CREEK - MS4 Outfalls (NRPC partner submission, file stem "
            "MS4_OUTFALLS)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "unknown",
        "coordinate_system": "unknown",
        "expected_features": 1,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MS4_OUTFALLS",
        "submission_date": "2025-10-08",
        "qaqc_report": "QAQC Reports/MCWD/MS4 Outfalls/report.html",
        "qaqc_report_date": "2026-07-08",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.2,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_ms4_ponds": {
        "description": (
            "MINNEHAHA CREEK - MS4 Ponds (NRPC partner submission, file stem "
            "MS4_PONDS)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 2,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MS4_PONDS",
        "submission_date": "2025-10-08",
        "qaqc_report": "QAQC Reports/MCWD/MS4 Ponds/report.html",
        "qaqc_report_date": "2026-07-08",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.4,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_ms4_receiving_waters": {
        "description": (
            "MINNEHAHA CREEK - MS4 Receiving Waters (NRPC partner submission, file "
            "stem MS4_REC_WATERS)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 2,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MS4_REC_WATERS",
        "submission_date": "2025-10-08",
        "qaqc_report": "QAQC Reports/MCWD/MS4 Receiving Waters/report.html",
        "qaqc_report_date": "2026-07-08",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.4,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_ms4_stormwater_pipes": {
        "description": (
            "MINNEHAHA CREEK - MS4 Stormwater Pipes (NRPC partner submission, file "
            "stem MS4_STRMWTR_PIPES)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "unknown",
        "coordinate_system": "unknown",
        "expected_features": 2,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MS4_STRMWTR_PIPES",
        "submission_date": "2025-10-08",
        "qaqc_report": "QAQC Reports/MCWD/MS4 Stormwater Pipes/report.html",
        "qaqc_report_date": "2026-07-08",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.0,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_property_and_easements": {
        "description": (
            "MINNEHAHA CREEK - Property and Easements (NRPC partner submission, file "
            "stem MCWD_Property_and_Easements)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 66,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MCWD_Property_and_Easements",
        "submission_date": "2026-03-13",
        "qaqc_report": "QAQC Reports/MCWD/Property and Easements/report.html",
        "qaqc_report_date": "2026-06-10",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.2,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_resnet_monitoring_stations": {
        "description": (
            "MINNEHAHA CREEK - RESNET Monitoring Stations (NRPC partner submission, "
            "file stem RESNET_Monitoring_Stations)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "point",
        "coordinate_system": "unknown",
        "expected_features": 25,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "RESNET_Monitoring_Stations",
        "submission_date": "2026-03-13",
        "qaqc_report": "QAQC Reports/MCWD/RESNET Monitoring Stations/report.html",
        "qaqc_report_date": "2026-06-11",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 4.8,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_stream_order": {
        "description": (
            "MINNEHAHA CREEK - Stream Order (NRPC partner submission, file stem "
            "MCWD_Stream_Order)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "unknown",
        "coordinate_system": "unknown",
        "expected_features": 2211,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MCWD_Stream_Order",
        "submission_date": "2025-10-08",
        "qaqc_report": "QAQC Reports/MCWD/Stream Order/report.html",
        "qaqc_report_date": "2026-06-11",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.6,
        "agol_upload": "on_hold",
    },
    "nrpc_mcwd_subwatersheds": {
        "description": (
            "MINNEHAHA CREEK - Subwatersheds (NRPC partner submission, file stem "
            "MCWD_Subwatersheds)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 11,
        "jurisdiction": "MINNEHAHA CREEK",
        "file_stem": "MCWD_Subwatersheds",
        "submission_date": "2025-10-08",
        "qaqc_report": "QAQC Reports/MCWD/Subwatersheds/report.html",
        "qaqc_report_date": "2026-06-11",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 5.0,
        "agol_upload": "on_hold",
    },
    # --- RPBCWD (11) ---
    "nrpc_rpbcwd_ann_subwatershed": {
        "description": (
            "RILEY-PURGATORY-BLUFF CREEK - Ann Subwatershed (NRPC partner submission, "
            "file stem Ann_2025_P8_Subwatersheds)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 3,
        "jurisdiction": "RILEY-PURGATORY-BLUFF CREEK",
        "file_stem": "Ann_2025_P8_Subwatersheds",
        "submission_date": "2026-01-27",
        "qaqc_report": "QAQC Reports/RPBCWD/Ann Subwatershed/report.html",
        "qaqc_report_date": "2026-06-15",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 4.67,
        "agol_upload": "on_hold",
    },
    "nrpc_rpbcwd_cras_reaches_2021": {
        "description": (
            "RILEY-PURGATORY-BLUFF CREEK - CRAS Reaches 2021 (NRPC partner submission, "
            "file stem CRAS_Reaches_2021)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "unknown",
        "coordinate_system": "unknown",
        "expected_features": 97,
        "jurisdiction": "RILEY-PURGATORY-BLUFF CREEK",
        "file_stem": "CRAS_Reaches_2021",
        "submission_date": "2026-01-26",
        "qaqc_report": "QAQC Reports/RPBCWD/CRAS Reaches 2021/report.html",
        "qaqc_report_date": "2026-06-15",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.4,
        "agol_upload": "on_hold",
    },
    "nrpc_rpbcwd_flood_risk": {
        "description": (
            "RILEY-PURGATORY-BLUFF CREEK - Flood Risk (NRPC partner submission, file "
            "stem EP_Inundation_100Yr)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 1733,
        "jurisdiction": "RILEY-PURGATORY-BLUFF CREEK",
        "file_stem": "EP_Inundation_100Yr",
        "submission_date": "2026-01-27",
        "qaqc_report": "QAQC Reports/RPBCWD/Flood Risk/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.8,
        "agol_upload": "on_hold",
    },
    "nrpc_rpbcwd_high_risk_erosion_areas": {
        "description": (
            "RILEY-PURGATORY-BLUFF CREEK - High Risk Erosion Areas (NRPC partner "
            "submission, file stem High_Risk_Erosion_Areas)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 6,
        "jurisdiction": "RILEY-PURGATORY-BLUFF CREEK",
        "file_stem": "High_Risk_Erosion_Areas",
        "submission_date": "2026-01-27",
        "qaqc_report": "QAQC Reports/RPBCWD/High Risk Erosion Areas/report.html",
        "qaqc_report_date": "2026-06-30",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.6,
        "agol_upload": "on_hold",
    },
    "nrpc_rpbcwd_lake_lucy_subwatershed": {
        "description": (
            "RILEY-PURGATORY-BLUFF CREEK - Lake Lucy Subwatershed (NRPC partner "
            "submission, file stem Lucy_2025_P8_Subwatersheds)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 58,
        "jurisdiction": "RILEY-PURGATORY-BLUFF CREEK",
        "file_stem": "Lucy_2025_P8_Subwatersheds",
        "submission_date": "2026-01-27",
        "qaqc_report": "QAQC Reports/RPBCWD/Lake Lucy Subwatershed/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.17,
        "agol_upload": "on_hold",
    },
    "nrpc_rpbcwd_lake_mitchell_subwatershed": {
        "description": (
            "RILEY-PURGATORY-BLUFF CREEK - Lake Mitchell Subwatershed (NRPC partner "
            "submission, file stem Mitchell_2025_P8_Subwatersheds)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 50,
        "jurisdiction": "RILEY-PURGATORY-BLUFF CREEK",
        "file_stem": "Mitchell_2025_P8_Subwatersheds",
        "submission_date": "2026-01-27",
        "qaqc_report": "QAQC Reports/RPBCWD/Lake Mitchell Subwatershed/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 4.5,
        "agol_upload": "on_hold",
    },
    "nrpc_rpbcwd_lake_susan_subwatershed": {
        "description": (
            "RILEY-PURGATORY-BLUFF CREEK - Lake Susan Subwatershed (NRPC partner "
            "submission, file stem Susan_2025_P8_Subwatersheds)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 88,
        "jurisdiction": "RILEY-PURGATORY-BLUFF CREEK",
        "file_stem": "Susan_2025_P8_Subwatersheds",
        "submission_date": "2026-01-27",
        "qaqc_report": "QAQC Reports/RPBCWD/Lake Susan Subwatershed/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 4.67,
        "agol_upload": "on_hold",
    },
    "nrpc_rpbcwd_mnram": {
        "description": (
            "RILEY-PURGATORY-BLUFF CREEK - MnRAM (NRPC partner submission, file stem "
            "MnRAM_RPBCWD)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 2015,
        "jurisdiction": "RILEY-PURGATORY-BLUFF CREEK",
        "file_stem": "MnRAM_RPBCWD",
        "submission_date": "2026-01-27",
        "qaqc_report": "QAQC Reports/RPBCWD/MnRAM/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.4,
        "agol_upload": "on_hold",
    },
    "nrpc_rpbcwd_red_rock_lake_subwatershed": {
        "description": (
            "RILEY-PURGATORY-BLUFF CREEK - Red Rock Lake Subwatershed (NRPC partner "
            "submission, file stem RedRock_2025_P8_Subwatersheds)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 69,
        "jurisdiction": "RILEY-PURGATORY-BLUFF CREEK",
        "file_stem": "RedRock_2025_P8_Subwatersheds",
        "submission_date": "2026-01-27",
        "qaqc_report": "QAQC Reports/RPBCWD/Red Rock Lake Subwatershed/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted",
        "qaqc_overall_score": 4.5,
        "agol_upload": "on_hold",
    },
    "nrpc_rpbcwd_residential_soil_samples_overview": {
        "description": (
            "RILEY-PURGATORY-BLUFF CREEK - Residential Soil Samples Overview (NRPC "
            "partner submission, file stem SoilsGISDataSample_XYTableToPoint)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "unknown",
        "coordinate_system": "unknown",
        "expected_features": 206,
        "jurisdiction": "RILEY-PURGATORY-BLUFF CREEK",
        "file_stem": "SoilsGISDataSample_XYTableToPoint",
        "submission_date": "2026-01-26",
        "qaqc_report": "QAQC Reports/RPBCWD/Residential Soil Samples Overview/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 4.0,
        "agol_upload": "on_hold",
    },
    "nrpc_rpbcwd_wetland_inventory": {
        "description": (
            "RILEY-PURGATORY-BLUFF CREEK - Wetland Inventory (NRPC partner submission, "
            "file stem Wetland_Inventory)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "multipolygon",
        "coordinate_system": "unknown",
        "expected_features": 1973,
        "jurisdiction": "RILEY-PURGATORY-BLUFF CREEK",
        "file_stem": "Wetland_Inventory",
        "submission_date": "2026-01-26",
        "qaqc_report": "QAQC Reports/RPBCWD/Wetland Inventory/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.4,
        "agol_upload": "on_hold",
    },
    # --- Wayzata (1) ---
    "nrpc_wayzata_tree_inventory": {
        "description": (
            "Wayzata - Tree Inventory (NRPC partner submission, file stem "
            "Wayzata_Tree_Inventory_Use)."
        ),
        "source_type": "nrpc_partner_submission",
        "spatial_type": "unknown",
        "coordinate_system": "unknown",
        "expected_features": 1885,
        "jurisdiction": "Wayzata",
        "file_stem": "Wayzata_Tree_Inventory_Use",
        "submission_date": "2026-04-08",
        "qaqc_report": "QAQC Reports/Wayzata/Tree Inventory/report.html",
        "qaqc_report_date": "2026-07-06",
        "qaqc_assessment": "Accepted with Comments",
        "qaqc_overall_score": 3.67,
        "agol_upload": "on_hold",
    },
}


def get_nrpc_partner_submissions() -> Dict[str, Dict[str, Any]]:
    """QA/QC'd NRPC partner datasets (catalog only; files are Survey123 attachments)."""
    return NRPC_PARTNER_SUBMISSIONS

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
