#!/usr/bin/env python3
"""Checks for the three suitability_modeling defects fixed on this branch.

Run:  python3 test_suitability_fixes.py

Dependency-free by design. `execution_engine.py` imports geopandas/numpy at
module scope, so the dataset-name resolver cannot be imported directly on a
machine without them (and `pytest` cannot run at all here — tests/conftest.py
imports sqlalchemy). This extracts the resolver's two methods from the source
with `ast` and exercises them standalone, which is enough to pin the behaviour.

Covers:
  1. pyyaml declared in pyproject.toml   — clean install broke every command
  2. no deprecated/date-suffixed model id — claude_client.py
  3. dataset-name resolution             — FGDB `_ANALYSIS` suffix vs bare names
  4. run-config passes id_column         — output had unnamed polygons
"""

import ast
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent
ENGINE = ROOT / "src" / "rtgs_lab_tools" / "suitability_modeling" / "core" / "execution_engine.py"
CLIENT = ROOT / "src" / "rtgs_lab_tools" / "suitability_modeling" / "llm" / "claude_client.py"
CLI = ROOT / "src" / "rtgs_lab_tools" / "suitability_modeling" / "cli.py"

failures = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        failures.append(message)


def load_resolver():
    """Pull the resolver methods out of execution_engine.py without importing it."""
    tree = ast.parse(ENGINE.read_text())
    wanted = {"_normalize_dataset_name", "_resolve_dataset_name"}
    methods = [
        node
        for cls in tree.body
        if isinstance(cls, ast.ClassDef)
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    if len(methods) != len(wanted):
        return None
    module = ast.Module(body=methods, type_ignores=[])
    ast.fix_missing_locations(module)

    class _Logger:
        def info(self, *a, **k):
            pass

    namespace = {"logger": _Logger()}
    exec(compile(module, "<resolver>", "exec"), namespace)

    class Resolver:
        _normalize_dataset_name = staticmethod(namespace["_normalize_dataset_name"])
        _resolve_dataset_name = namespace["_resolve_dataset_name"]

        def __init__(self, datasets):
            self.datasets = datasets

    return Resolver


def main():
    # --- 1. pyyaml dependency -------------------------------------------------
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    check(
        any(d.lower().startswith("pyyaml") for d in deps),
        "pyproject.toml [project].dependencies is missing pyyaml — "
        "model_specification.py imports yaml at module scope, so a clean "
        "install breaks every `rtgs suitability` command",
    )

    # --- 2. model id ----------------------------------------------------------
    client_src = CLIENT.read_text()
    check(
        'model="claude-sonnet-4-20250514"' not in client_src,
        "claude_client.py still hardcodes the deprecated claude-sonnet-4-20250514",
    )
    check("DEFAULT_MODEL" in client_src, "claude_client.py should route the model id through DEFAULT_MODEL")
    check(
        '"claude-sonnet-5"' in client_src,
        "claude_client.py DEFAULT_MODEL should be claude-sonnet-5",
    )
    # Current model ids carry no date suffix; catch a reintroduced one.
    tree = ast.parse(client_src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value
            if v.startswith("claude-"):
                tail = v.rsplit("-", 1)[-1]
                check(
                    not (len(tail) == 8 and tail.isdigit()),
                    f"date-suffixed model id in claude_client.py: {v!r}",
                )

    # --- 3. dataset-name resolution ------------------------------------------
    Resolver = load_resolver()
    check(Resolver is not None, "could not find the resolver methods in execution_engine.py")
    if Resolver is not None:
        r = Resolver({
            "Protected_Areas_ANALYSIS": object(),
            "Natural_Spaces_ANALYSIS": object(),
            "Important_Bird_Areas_ANALYSIS": object(),
            "MBS_ANALYSIS": object(),
            "hennepin_county_ctus": object(),
        })
        # The four model-spec names used by the shipped Hennepin YAMLs.
        for bare, actual in (
            ("protected_areas", "Protected_Areas_ANALYSIS"),
            ("natural_spaces", "Natural_Spaces_ANALYSIS"),
            ("important_bird_areas", "Important_Bird_Areas_ANALYSIS"),
            ("MBS", "MBS_ANALYSIS"),
        ):
            got = r._resolve_dataset_name(bare)
            check(got == actual, f"resolver: {bare!r} -> {got!r}, expected {actual!r}")

        # Exact names must still win untouched.
        check(
            r._resolve_dataset_name("hennepin_county_ctus") == "hennepin_county_ctus",
            "resolver broke an exact match",
        )
        check(
            r._resolve_dataset_name("MBS_ANALYSIS") == "MBS_ANALYSIS",
            "resolver broke an exact _ANALYSIS match",
        )

        # A miss must name the alternatives rather than raise a bare KeyError.
        try:
            r._resolve_dataset_name("does_not_exist")
            check(False, "resolver should raise on an unknown dataset")
        except ValueError as exc:
            check("Available" in str(exc), "resolver error should list available datasets")
        except KeyError:
            check(False, "resolver raised a bare KeyError instead of a helpful ValueError")

        # Ambiguity must be an error, not a silent pick.
        r2 = Resolver({"foo": object(), "Foo_ANALYSIS": object()})
        try:
            r2._resolve_dataset_name("FOO")
            check(False, "resolver should raise on an ambiguous match")
        except ValueError as exc:
            check("ambiguous" in str(exc), "ambiguous-match error should say so")

    # --- 4. run-config id_column ---------------------------------------------
    cli_src = CLI.read_text()
    check("--id-column" in cli_src, "run-config is missing the --id-column option")
    check(
        "id_column=final_id_column" in cli_src,
        "run-config still does not pass id_column to execute_model",
    )
    check(
        'config.get("id_column")' in cli_src,
        "run-config should also read id_column from the config file",
    )

    print(f"{checks} checks run")
    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
