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
                bool(cfg.get("service_url")) or name == "usfws_national_realty_boundaries",
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

    # --- accessors still work ------------------------------------------------
    check(callable(reg.get_pending_datasets), "get_pending_datasets is not callable")
    check(callable(reg.get_forthcoming_datasets), "get_forthcoming_datasets is not callable")
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
          f"{len(pending)} pending, {len(forthcoming)} forthcoming")
    print(f"crosswalk rows traceable: {len(covered)}/41")
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
