#!/usr/bin/env python3
"""Standalone integrity checks for the spatial dataset registry.

Run:  python3 test_registry_integrity.py

Deliberately dependency-free. The pytest suite cannot run on every machine
because tests/conftest.py imports sqlalchemy and several modules import
geopandas; the registry is pure data and should be checkable without either.
This loads dataset_registry.py directly by path, so it does not import the
rtgs_lab_tools package and does not need its dependencies installed.

Added 2026-09-21 alongside the easement-scoring-to-registry crosswalk updates.
"""

import importlib.util
import sys
from pathlib import Path

REGISTRY_PATH = (
    Path(__file__).parent
    / "src"
    / "rtgs_lab_tools"
    / "spatial_data"
    / "registry"
    / "dataset_registry.py"
)

REQUIRED_FIELDS = ("description", "source_type", "spatial_type")
VALID_ACCESS = {"download", "rest_api"}

failures = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        failures.append(message)


def load_registry():
    spec = importlib.util.spec_from_file_location("dataset_registry", REGISTRY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    if not REGISTRY_PATH.exists():
        print(f"FAIL: registry not found at {REGISTRY_PATH}")
        return 1

    reg = load_registry()
    mn = reg.MN_GEOSPATIAL_DATASETS
    fgdb = reg.FGDB_DATASETS
    pending = reg.PENDING_HENNEPIN_DATASETS
    forthcoming = reg.FORTHCOMING_DATASETS

    # --- structural ---------------------------------------------------------
    for group_name, group in (("MN_GEOSPATIAL", mn), ("FGDB", fgdb)):
        for name, cfg in group.items():
            for field in REQUIRED_FIELDS:
                check(field in cfg, f"{group_name}[{name}] missing required field '{field}'")
            check(
                isinstance(cfg.get("description", ""), str) and cfg.get("description"),
                f"{group_name}[{name}] has an empty description",
            )

    # --- keys must be unique across groups ----------------------------------
    overlap = set(mn) & set(fgdb)
    check(not overlap, f"keys defined in BOTH groups (get_dataset_config resolves to MN): {overlap}")

    # --- acquisition ---------------------------------------------------------
    for name, cfg in mn.items():
        method = cfg.get("access_method")
        check(method in VALID_ACCESS, f"MN_GEOSPATIAL[{name}] invalid access_method {method!r}")
        if method == "download":
            check(
                bool(cfg.get("download_url")),
                f"MN_GEOSPATIAL[{name}] access_method=download but no download_url",
            )
        elif method == "rest_api":
            check(
                bool(cfg.get("service_url")),
                f"MN_GEOSPATIAL[{name}] access_method=rest_api but no service_url",
            )

    for name, cfg in fgdb.items():
        check(bool(cfg.get("layer_name")), f"FGDB[{name}] missing layer_name")
        check(
            cfg.get("source_type") == "fgdb",
            f"FGDB[{name}] source_type should be 'fgdb', is {cfg.get('source_type')!r}",
        )

    # --- attribute_filter shape ---------------------------------------------
    for group_name, group in (("MN_GEOSPATIAL", mn), ("FGDB", fgdb)):
        for name, cfg in group.items():
            af = cfg.get("attribute_filter")
            if af is None:
                continue
            for field in ("description", "columns", "values", "match_type"):
                check(field in af, f"{group_name}[{name}].attribute_filter missing '{field}'")
            check(
                isinstance(af.get("columns"), list) and af["columns"],
                f"{group_name}[{name}].attribute_filter.columns must be a non-empty list",
            )
            check(
                isinstance(af.get("values"), list) and af["values"],
                f"{group_name}[{name}].attribute_filter.values must be a non-empty list",
            )

    # --- cross-references must resolve --------------------------------------
    all_keys = set(mn) | set(fgdb)
    ref_fields = (
        "derived_from",
        "additive_to",
        "computed_from",
        "not_a_replacement_for",
        "relates_to",
    )
    for group_name, group in (("MN_GEOSPATIAL", mn), ("FGDB", fgdb)):
        for name, cfg in group.items():
            for field in ref_fields:
                target = cfg.get(field)
                if target:
                    check(
                        target in all_keys,
                        f"{group_name}[{name}].{field} points at unknown key {target!r}",
                    )
            for field in ("consolidates", "feeds", "downstream_selections"):
                for target in cfg.get(field) or []:
                    check(
                        target in all_keys,
                        f"{group_name}[{name}].{field} points at unknown key {target!r}",
                    )

    # --- pending / forthcoming must NOT be acquirable ------------------------
    for name in pending:
        check(
            name not in all_keys,
            f"PENDING_HENNEPIN_DATASETS[{name}] also appears as an acquirable dataset",
        )
    for name in forthcoming:
        check(
            name not in all_keys,
            f"FORTHCOMING_DATASETS[{name}] also appears as an acquirable dataset",
        )
    for name, cfg in forthcoming.items():
        for target in cfg.get("would_supersede") or []:
            check(
                target in all_keys,
                f"FORTHCOMING_DATASETS[{name}].would_supersede unknown key {target!r}",
            )

    # --- crosswalk coverage --------------------------------------------------
    # Meaghan Dietrich's easement-scoring crosswalk has 41 data rows (2-42).
    covered = set()
    for group in (mn, fgdb, pending, forthcoming):
        for cfg in group.values():
            covered.update(cfg.get("crosswalk_rows") or [])
    check(
        covered <= set(range(2, 43)),
        f"crosswalk_rows outside the sheet's 2-42 range: {sorted(covered - set(range(2, 43)))}",
    )
    # Rows 11 and 41 are deliberately unrepresented in the acquirable registry
    # (row 11 removed as redundant; row 41 not yet published but recorded in
    # FORTHCOMING). Everything else should be traceable to something.
    expected_uncovered = {11}
    missing = set(range(2, 43)) - covered - expected_uncovered
    check(
        not missing,
        f"crosswalk rows with no registry entry, pending entry or forthcoming entry: {sorted(missing)}",
    )

    # --- Scoring Review coverage (2026-11-10 sheet) ---------------------------
    # The 2026-11-10 "Scoring Review and Recommendations" tab of Meaghan Dietrich's sheet has 46
    # dataset rows, 2-47. scoring_review_rows numbers that tab; crosswalk_rows (above) still
    # numbers the 2026-09-21 version. Every dataset row must trace to at least one entry.
    review_rows = set(range(2, 48))
    review_groups = {
        "MN_GEOSPATIAL": mn, "FGDB": fgdb, "PENDING": pending, "FORTHCOMING": forthcoming,
        "HENNEPIN_DELIVERED": reg.HENNEPIN_DELIVERED_DATASETS,
        "NRPC_PARTNER": reg.NRPC_PARTNER_SUBMISSIONS,
    }
    review_covered = set()
    for group_name, group in review_groups.items():
        for name, cfg in group.items():
            rows = cfg.get("scoring_review_rows")
            if rows is None:
                continue
            check(
                isinstance(rows, list) and rows and all(isinstance(r, int) for r in rows),
                f"{group_name}[{name}].scoring_review_rows must be a non-empty list of ints",
            )
            check(rows == sorted(set(rows)),
                  f"{group_name}[{name}].scoring_review_rows must be sorted and unique: {rows}")
            check(set(rows) <= review_rows,
                  f"{group_name}[{name}].scoring_review_rows outside 2-47: "
                  f"{sorted(set(rows) - review_rows)}")
            review_covered.update(rows)
    check(
        not (review_rows - review_covered),
        f"Scoring Review rows with no registry entry: {sorted(review_rows - review_covered)}",
    )
    # Datasets the 11/10 tab added that the 9/21 sheet did not name.
    for name, rows in (
        ("metro_conservation_corridors", [16]),
        ("dnr_native_plant_communities", [18, 20]),
        ("rpbb_high_potential_zones", [29, 30]),
        ("important_bird_areas_public", [31]),
        ("audubon_migratory_stopover_water_mn", [32]),
        ("lakes_of_biological_significance", [33]),
        ("shallow_lakes_dnr_wildlife", [34]),
        ("land_use_2025", [37]),
        ("fema_nfhl_flood_hazard_zones", [43]),
        ("water_table_aquifer_vulnerability", [47]),
    ):
        check(name in mn, f"MN_GEOSPATIAL['{name}'] (Scoring Review rows {rows}) is missing")
        check(mn.get(name, {}).get("scoring_review_rows") == rows,
              f"MN_GEOSPATIAL['{name}'].scoring_review_rows should be {rows}")
    glu = forthcoming.get("generalized_land_use_2025", {})
    if glu.get("now_acquirable_as"):
        check(glu["now_acquirable_as"] in mn,
              "FORTHCOMING['generalized_land_use_2025'].now_acquirable_as unknown key")
    # Every resources.gisdata.mn.gov bulk path returned HTTP 404 on 2026-11-10.
    for name, cfg in mn.items():
        check("resources.gisdata.mn.gov" not in str(cfg.get("download_url", "")),
              f"MN_GEOSPATIAL[{name}] download_url uses the retired resources.gisdata.mn.gov path")

    # --- MLCCS provenance must not be quietly reverted -----------------------
    land_cover = fgdb.get("land_cover", {})
    check("land_cover" in fgdb, "FGDB['land_cover'] (MLCCS) is missing")
    check(
        land_cover.get("superseded_by") is None,
        "FGDB['land_cover'].superseded_by must stay None: Imagine 2050 RSEA is "
        "downstream of MLCCS, not a successor to it",
    )
    check(
        "M_34X" in (land_cover.get("key_attributes") or {}),
        "FGDB['land_cover'].key_attributes must document M_34X: three model criteria score on it",
    )
    rsea = mn.get("regionally_significant_ecological_areas", {})
    check(
        rsea.get("not_a_replacement_for") == "land_cover",
        "regionally_significant_ecological_areas must record that it does not replace land_cover",
    )

    # --- NRPC additions (2026-11-04): delivered, partner submissions, map layers --
    delivered = reg.HENNEPIN_DELIVERED_DATASETS
    partners = reg.NRPC_PARTNER_SUBMISSIONS
    catalog_only = {"HENNEPIN_DELIVERED": delivered, "NRPC_PARTNER": partners}
    for group_name, group in catalog_only.items():
        for name in group:
            check(name not in all_keys,
                  f"{group_name}[{name}] also appears as an acquirable dataset")
            check(name not in pending and name not in forthcoming,
                  f"{group_name}[{name}] reuses a PENDING/FORTHCOMING key")
    check(not (set(delivered) & set(partners)), "a key is in both DELIVERED and PARTNER groups")

    for name, cfg in delivered.items():
        check(cfg.get("source_type") == "hennepin_delivery",
              f"HENNEPIN_DELIVERED[{name}] source_type should be 'hennepin_delivery'")
        check(str(cfg.get("delivery", "")).startswith("thread:"),
              f"HENNEPIN_DELIVERED[{name}] delivery must cite the mail thread")
        check(bool(cfg.get("file_name")) and bool(cfg.get("layer_name")),
              f"HENNEPIN_DELIVERED[{name}] needs file_name and layer_name")
        check(isinstance(cfg.get("expected_features"), int),
              f"HENNEPIN_DELIVERED[{name}] expected_features must be an int")
        for field in ("fulfils", "candidate_for"):
            if cfg.get(field):
                check(cfg[field] in pending,
                      f"HENNEPIN_DELIVERED[{name}].{field} unknown PENDING key {cfg[field]!r}")
        if cfg.get("relates_to"):
            check(cfg["relates_to"] in all_keys,
                  f"HENNEPIN_DELIVERED[{name}].relates_to unknown key {cfg['relates_to']!r}")
    for name, cfg in pending.items():
        for target in cfg.get("delivered_as") or []:
            check(target in delivered,
                  f"PENDING[{name}].delivered_as unknown DELIVERED key {target!r}")
        if cfg.get("delivered_as"):
            check(cfg.get("status") in {"delivered", "candidate_delivered",
                                        "derived_product_delivered"},
                  f"PENDING[{name}] has delivered_as but status {cfg.get('status')!r}")

    for name, cfg in partners.items():
        check(cfg.get("source_type") == "nrpc_partner_submission",
              f"NRPC_PARTNER[{name}] source_type should be 'nrpc_partner_submission'")
        check(cfg.get("agol_upload") in {"ready", "on_hold"},
              f"NRPC_PARTNER[{name}] agol_upload must be 'ready' or 'on_hold'")
        report = str(cfg.get("qaqc_report", ""))
        check(report.startswith("QAQC Reports/") and report.endswith("/report.html"),
              f"NRPC_PARTNER[{name}] qaqc_report must be 'QAQC Reports/<org>/<dataset>/report.html'")
        for field in ("jurisdiction", "file_stem", "submission_date", "qaqc_assessment"):
            check(bool(cfg.get(field)), f"NRPC_PARTNER[{name}] missing {field}")
    ready = sum(1 for c in partners.values() if c.get("agol_upload") == "ready")
    held = sum(1 for c in partners.values() if c.get("agol_upload") == "on_hold")
    # 2026-10-13 upload checklist: 26 ready, 26 on hold (MCWD 14, RPBCWD 11, Wayzata 1).
    check(ready == 26, f"expected 26 partner layers ready for upload, found {ready}")
    check(held == 26, f"expected 26 partner layers on hold, found {held}")

    webmap = {k: c for k, c in mn.items() if c.get("nrpc_webmap_item")}
    for name, cfg in webmap.items():
        check(cfg.get("access_method") == "rest_api" and cfg.get("service_url") == cfg.get("url"),
              f"MN_GEOSPATIAL[{name}] web-map layer must be rest_api with service_url == url")
        check(cfg.get("source_type") == "mn_geospatial",
              f"MN_GEOSPATIAL[{name}] web-map layer must use source_type 'mn_geospatial' "
              "(the only REST source the extractor maps)")
    # 21 layer URLs in web map d664f1d1 (2026-11-02 pull) -> 21 entries.
    check(len(webmap) == 21, f"expected 21 NRPC web-map layers, found {len(webmap)}")
    v2 = forthcoming.get("hennepin_suitability_v2_results", {})
    check(set(v2.get("would_supersede") or []) == {"hennepin_suitability_v1_countywide",
                                                    "hennepin_suitability_v1_parcel_detail"},
          "FORTHCOMING['hennepin_suitability_v2_results'] must supersede both v1 layers")

    # --- accessors still work ------------------------------------------------
    check(callable(reg.get_pending_datasets), "get_pending_datasets is not callable")
    check(callable(reg.get_forthcoming_datasets), "get_forthcoming_datasets is not callable")
    check(reg.get_delivered_datasets() is delivered, "get_delivered_datasets broken")
    check(reg.get_nrpc_partner_submissions() is partners, "get_nrpc_partner_submissions broken")
    check(isinstance(reg.format_gaps_for_llm(), str), "format_gaps_for_llm did not return a string")
    # NB: only exercise paths that do not reach the FGDB branch. That branch does
    # `from ..sources.fgdb import is_fgdb_available`, a package-relative import
    # that cannot resolve when this file is loaded by path.
    check(
        reg.get_dataset_source("wildlife_areas") == "mn_geospatial",
        "get_dataset_source('wildlife_areas') should be 'mn_geospatial'",
    )
    check(
        reg.get_dataset_source("does_not_exist_anywhere") == "unknown",
        "get_dataset_source should return 'unknown' for an unregistered name",
    )

    # --- report --------------------------------------------------------------
    print(f"registry: {len(mn)} MN_GEOSPATIAL, {len(fgdb)} FGDB, "
          f"{len(pending)} pending, {len(forthcoming)} forthcoming, "
          f"{len(delivered)} delivered, {len(partners)} partner submissions")
    print(f"crosswalk rows traceable: {len(covered)}/41")
    print(f"Scoring Review rows traceable: {len(review_covered & review_rows)}/46")
    print(f"{checks} checks run")
    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
