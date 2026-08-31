"""PROTOTYPE runner - parse raw_data_new.csv and show the normalized output."""

import json
import sys
import time
from pathlib import Path

import pandas as pd

from metric_specs import build_node_records, make_keeper
from packet_adapters import detect_family, parse_new_families

# Sample CSVs live in device_monitoring/, one level up from this prototype dir.
BASE = Path(__file__).resolve().parent.parent


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "raw_data_new.csv"
    raw = pd.read_csv(BASE / name, encoding="utf-8")
    print(f"Loaded {len(raw)} raw rows from {name}")

    # The source feed contains exact duplicate rows - 13,069 of 50,000 in this
    # sample, identical on every field. Left in, they inflate error counts and
    # packet totals. (The existing error/v2 path has the same exposure, since
    # its groupby().size() counts duplicates too.)
    before = len(raw)
    raw = raw.drop_duplicates(subset=["id", "node_id", "event", "message"])
    print(f"Dropped {before - len(raw)} exact duplicate rows -> {len(raw)}\n")

    print("=" * 78)
    print("STEP 1  family detection")
    print("=" * 78)
    raw["family"] = raw.apply(detect_family, axis=1)
    detected = raw.groupby(["event", "family"], dropna=False).agg(
        rows=("id", "size"), nodes=("node_id", "nunique")
    )
    print(detected.to_string(), "\n")

    print("=" * 78)
    print("STEP 2  parse to normalized measurements")
    print("=" * 78)
    started = time.time()
    parsed, stats = parse_new_families(raw, keep_record=make_keeper())
    elapsed = time.time() - started
    print(f"packets parsed : {stats['parsed']}")
    print(f"packets skipped: {stats['skipped']}  {stats['skipped_events']}")
    print(f"packets failed : {stats['failed']}")
    print(f"by family      : {stats['by_family']}")
    print(f"measurements   : {stats['measurements_kept']} kept "
          f"of {stats['measurements_seen']} seen "
          f"({stats['measurements_kept'] / max(stats['measurements_seen'], 1):.1%})")
    print(f"parse time     : {elapsed:.1f}s")
    if stats["unparseable_nodes"]:
        print("\n  !! headerless packets - no schema available, NOT parsed:")
        for node, count in stats["unparseable_nodes"].items():
            print(f"     {node}: {count} packets")
    print()

    print("--- sample normalized rows, one per family ---")
    cols = [
        "node_id", "device_family", "device_type",
        "device_position", "measurement_name", "value", "unit",
    ]
    for family in parsed["device_family"].unique():
        sub = parsed[parsed["device_family"] == family].head(4)
        print(f"\n[{family}]")
        print(sub[cols].to_string(index=False))

    print("\n" + "=" * 78)
    print("STEP 3  collapse to one monitoring record per node")
    print("=" * 78)
    records = build_node_records(parsed)

    for rec in sorted(records, key=lambda r: (r["device_family"], r["node_id"])):
        print(f"\n{rec['node_id']}  [{rec['display_name']}]  "
              f"{rec['packets']} packets / {rec['schemas']} schema(s)")
        dt = rec["device_time"]
        print(f"  device clock : {dt if dt else '(none)'}")
        if rec["metrics"]:
            for m in rec["metrics"]:
                gate = f"  gated by {m['threshold_key']}" if m["threshold_key"] else ""
                stale = ""
                if m["stale_seconds"]:
                    stale = (f"  [{m['stale_seconds'] // 60} min old, "
                             f"{m['packets_ago']} packets back]")
                print(f"  {m['label']:<16} {str(m['value']):>12}  {m['unit']:<4}"
                      f"  <- {m['source']}{gate}{stale}")
        else:
            print("  metrics      : NONE -> staleness-only monitoring")
        for e in rec["errors"]:
            where = f"{e['device_type']} [{e['device_position']}]" if e["device_position"] else e["device_type"]
            print(f"  error        : {e['error_name']} on {where}"
                  f"  count={e['count']}  cols={len(e['columns'])}")
        if rec["unusable"]:
            print(f"  dropped      : {'; '.join(rec['unusable'])}")

    print("\n" + "=" * 78)
    print("STEP 4  what a Monitoring row would look like (Option B)")
    print("=" * 78)
    example = next(r for r in records if r["node_id"].startswith("z6"))
    row = {
        "node_id": example["node_id"],
        "device_family": example["device_family"],
        "metrics": json.dumps(example["metrics"]),
        "errors": json.dumps(example["errors"]),
    }
    for key, value in row.items():
        print(f"  {key:<15} {value}")

    print("\n" + "=" * 78)
    print("COVERAGE SUMMARY")
    print("=" * 78)
    total_nodes = raw["node_id"].nunique()
    with_metrics = sum(1 for r in records if r["metrics"])
    with_battery = sum(
        1 for r in records if any(m["key"] == "battery_voltage" for m in r["metrics"])
    )
    print(f"  nodes in file          : {total_nodes}")
    print(f"  nodes with a record    : {len(records)}")
    print(f"  nodes with any metric  : {with_metrics}")
    print(f"  nodes with battery     : {with_battery}")
    print(f"  staleness-only nodes   : {len(records) - with_metrics}")


if __name__ == "__main__":
    sys.exit(main())
