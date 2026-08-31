# Prototype — new device family parsing

**Not wired into the pipeline.** Nothing in `device_monitoring/` imports this. It exists to validate
the design against real data before production code is written. See `../HANDOFF.md` for the full
context, decisions, and next steps.

Deliberately kept out of the `device_monitoring` package namespace (flat sibling imports, no
`__init__.py`) so it can't be accidentally imported by `core.py` or picked up by the CLI.

## Files

| File | What it is |
|---|---|
| `packet_adapters.py` | Family detection + one adapter per family. Reuses `data_parser`'s unregistered `CSVEventParser` / `JSONEventParser` without modifying that package. |
| `metric_specs.py` | `FAMILY_SPECS` — the declarative table where all per-family knowledge lives. Adding a metric is one entry here. |
| `run_prototype.py` | Runner. Prints detection, normalized rows, per-node records, and a coverage summary. |
| `full_run.txt` | Output of the last 50k-row run, for reference. |

## Running

Requires the repo `.venv` (system Python lacks `dotenv`, which `rtgs_lab_tools/__init__.py` pulls in).

```bash
cd src/rtgs_lab_tools/device_monitoring/prototype

# 50k-row sample (~27s)
PYTHONPATH="../../.." PYTHONIOENCODING=utf-8 \
  ../../../../.venv/Scripts/python.exe -u run_prototype.py raw_data.csv

# 148-row regression (<1s)
PYTHONPATH="../../.." PYTHONIOENCODING=utf-8 \
  ../../../../.venv/Scripts/python.exe -u run_prototype.py
```

`PYTHONIOENCODING=utf-8` matters — output contains `°`, `²`, and other non-CP1252 characters.

## Expected results

`raw_data.csv` (50,000 rows): 7,932 duplicates dropped, 32,584 packets parsed, **0 failures**,
37 nodes with a record / 36 with metrics / 1 staleness-only.

`raw_data_new.csv` (148 rows): 19/19 nodes, all with battery, 0 failures.

If these numbers change, something regressed.
