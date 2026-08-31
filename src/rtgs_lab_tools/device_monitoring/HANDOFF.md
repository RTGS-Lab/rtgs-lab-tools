# Device Monitoring — new device families: handoff

**Date:** 2026-07-28 · **Branch:** `feature/device-monitoring-updates` · **Status:** design validated by prototype; no production code written yet.

Give this file to Claude to resume. It replaces re-reading the prior conversation.

---

## Where the prototype lives

`device_monitoring/prototype/` (untracked, **not wired into the pipeline** — nothing imports it):

```
prototype/
    README.md             how to run it + expected numbers
    packet_adapters.py    family detection + 3 adapters
    metric_specs.py       declarative per-family metric table (FAMILY_SPECS)
    run_prototype.py      runner
    full_run.txt          last 50k-row run output
```

Run it (requires the repo `.venv` — system Python lacks `dotenv`):

```bash
cd src/rtgs_lab_tools/device_monitoring/prototype
PYTHONPATH="../../.." PYTHONIOENCODING=utf-8 \
  ../../../../.venv/Scripts/python.exe -u run_prototype.py raw_data.csv
```

Omit the argument for the fast `raw_data_new.csv` regression. Expected numbers are in `prototype/README.md`; if they differ, something regressed.

---

## 🔴 SEPARATE PRE-EXISTING BUG — fix independently of this work

**The production report's error counts are inflated ~2.19× by duplicate rows, today, right now.**
This has nothing to do with the new device families. It can and probably should be fixed on its own,
ahead of everything else in this document.

### Root cause

`sensing_data/data_extractor.py:438` (and the near-identical query at :446):

```sql
SELECT r.id, r.node_id, r.publish_time, r.ingest_time, r.event, r.message, r.message_id
FROM raw r
JOIN node n ON r.node_id = n.node_id
WHERE ...
```

Nothing in the query needs a column from `node` in all-projects mode — the join exists only to filter
by project. If a `node_id` has more than one row in `node` (a node registered under multiple
projects), the join **fans out** and emits every raw row once per matching `node` row.

### Evidence

In the 50k-row `raw_data.csv` sample: **7,932 duplicate copies of 50,000 rows (15.9%)**, byte-identical
on `id` + `node_id` + `event` + `message` — same device timestamp, same everything. No duplicated `id`
ever carries two different messages or spans two nodes.

Multiplicity is **exactly constant per node**, which is the fan-out signature (random duplication
cannot produce this): 1 node at ×4, 5 nodes at ×3, 17 nodes at ×2, the rest ×1. A node either
duplicates all of its packets or none.

The per-event-type rates look arbitrary until you realise they just reflect *which nodes* emit that
type — all the fanned-out nodes are Particle (`e00fce68…`):

```
diagnostic/v2   47.3% duplicate copies
error/v2        39.5%
data/v2         36.4%
json             0.0%   <- Campbell/Zentra nodes; single registration each
```

### Measured impact on the existing pipeline

Running the current `error/v2` + `diagnostic/v2` path over the same file, with and without dedup:

```
AS-IS (today)   parsed_measurements = 185,861   total_error_count = 19,011
DEDUPED         parsed_measurements = 101,665   total_error_count =  8,695
```

`data_formatter.create_error_count_dataframe` uses `groupby().size()`, which counts every copy. A node
registered in three projects reports every error three times.

### To confirm before fixing

```sql
SELECT node_id, COUNT(*) FROM node GROUP BY node_id HAVING COUNT(*) > 1;
```

The fan-out is inferred from the query text plus the constant-multiplicity signature; this confirms it
directly. Expect the counts to match the ×2/×3/×4 groups above.

### The fix — DECIDED: dedup locally in `device_monitoring/data_getter.py`

**User constraint: the fix must live in `device_monitoring/`. Do not modify `sensing_data/` (or any
other directory) — other people's work depends on it.** See "Scope constraint" under The goal.

So: dedup the DataFrame returned by `get_raw_data` inside `device_monitoring/data_getter.py:get_data`,
right after the call and before returning:

```python
raw_data_df = raw_data_df.drop_duplicates(
    subset=["id", "node_id", "event", "message"]
)
```

This is what the prototype does (`run_prototype.py`), and it is verified against both sample files.
Log the number dropped — a sudden change in that count is a useful signal that something moved in the
`node` table.

**Rejected (both would edit `sensing_data/data_extractor.py`, out of scope):**

- `SELECT DISTINCT` in `get_raw_data` — masks the cause and costs a sort.
- Replacing the join with `WHERE EXISTS (SELECT 1 FROM node n WHERE n.node_id = r.node_id AND
  n.project LIKE :project)` — this is the *correct* fix (a semi-join cannot fan out), and worth
  raising with whoever owns `sensing_data`, but it is not ours to make. Note it also fixes the bug for
  every other consumer of `get_raw_data`, which local dedup does not.

⚠️ Whichever lands, **error counts across the whole fleet will drop sharply** (measured 19,011 →
8,695). That is the bug being fixed, not a regression, but it will be conspicuous in the daily report
— warn users before it ships.

---

## The goal

Extend the daily monitoring report (`device_monitoring/core.py`) to cover devices that publish
`CSV` / `Data` / `json` events, alongside the existing `diagnostic/v2` + `error/v2` Kestrel path.

### Scope constraint (hard)

**All changes live in `device_monitoring/`. Do not modify `data_parser/`, `sensing_data/`, `core/`, or
any other directory — other people's work depends on them.**

This applies to *every* problem found in this project, including ones whose root cause is elsewhere
(see the `JOIN node` fan-out above: the correct fix is in `sensing_data/`, but we work around it
locally instead). Where an external fix would be better, note it for the owning team rather than
making it.

This is satisfiable for the parsing work — see "Key insight" below.

---

## Key insight

`data_parser/parsers/` **already contains** `csv_parser.py` (`CSVEventParser`) and `json_parser.py`
(`JSONEventParser`). They are fully implemented but **never registered** in `data_parser/core.py:79-82`,
which only wires up `data/v2`, `diagnostic/v2`, `metadata/v2`, `error/v2`.

So `device_monitoring` can import and drive them directly with its own `ParserFactory` — reusing the
code with zero edits to `data_parser`. Both need post-processing (see "Limitations" below).

---

## The families

| Family | const | Nodes | Event | Message shape |
|---|---|---|---|---|
| A. GEMS/Particle CSV | `gems_csv` | `e00fce68…` | `CSV` **and** `Data` | header + N data lines; `Sensor.Instance.MEASUREMENT` |
| B. Zentra/METER CSV | `zentra_csv` | `z6-*` | `CSV` | header + N data lines; `<Measurement> (<unit>) <Sensor> P<port>`, **no dots** |
| C. Campbell JSON | `campbell_json` | `mda_*`, `*roc_campbell_*` | `json` | flat `{"BattV_Avg(Volts)": "13.58", …}` |
| — headerless | `headerless_csv` | `e00fce68963fa0b8f3fc6ece` only | `Data` | bare positional values, no header — **parked, see below** |

`event` alone is insufficient: `CSV` and `Data` both carry Family A **and** Family B payloads, so
detection sniffs the header row. Family B is detected by `columns[0] == "timestamp_utc"`.

**`Data` (capital D) ≠ `data/v2`.** Different format entirely; `data/v2` stays with the existing pipeline.

---

## Verified state (last run, 50k-row `raw_data.csv`)

```
Loaded 50000 raw rows / dropped 7932 exact duplicates -> 42068
packets parsed : 32584
packets skipped: 9484  {diagnostic/v2: 4574, data/v2: 2491, error/v2: 1883, metadata/v2: 536}
packets failed : 0
measurements   : 72903 kept of 459964 seen (15.8%)
parse time     : 26.7s

nodes with a record    : 37
nodes with any metric  : 36
nodes with battery     : 36
staleness-only nodes   : 1   (the headerless node)
```

Regression on `raw_data_new.csv` (148 rows): 19/19 nodes, all with battery, 0 failures.

**Node sets are disjoint.** 37 new-family nodes, 24 old-family nodes, **zero overlap**, 61 total.
The new path and the existing Kestrel path never touch the same node — no merge conflict in the
`Monitoring` table. This materially de-risks the change.

---

## Design decisions (locked)

**Storage — Option B, generic metrics blob.** Add `device_family` (String) and `metrics` (Text, JSON)
to `Monitoring`; keep `battery`/`system`/`humidity` as legacy columns so the Kestrel path doesn't
regress. `metrics` holds self-describing records:

```json
[{"key":"battery_voltage","label":"Battery","value":8.432,"unit":"V",
  "threshold_key":"battery_voltage_min","source":"Battery Voltage (mV) Battery P7",
  "packets_ago":0,"measured_at":"2026-07-24T21:05:00","stale_seconds":0}]
```

Rejected: Option A (widen schema — a column per device type forever, migration each time);
Option C (table per family — multiplies endpoints/joins for a 61-node fleet).

**All per-family knowledge lives in `FAMILY_SPECS`**, a table of `MetricSpec` dataclasses
(`key`, `label`, `unit`, `paths` alias-list, `scale`, `threshold_key`, `note`). Cost of extension:

| Change | Cost |
|---|---|
| New metric on an existing family | **1 `MetricSpec` entry.** Nothing else. |
| New family, format already CSV/JSON-shaped | 1 `FamilySpec` + 1 detection rule (~3 lines) |
| New family, novel wire format | above + 1 adapter fn (~40 lines) |

In all cases: **no DB migration, no analyzer change, no frontend change.**

**Thresholds must be per-family.** Battery voltage is on three incompatible scales:
Kestrel ~4.1 V (Li-ion) · Zentra ~8.1 V (**reported in mV**) · Campbell ~13.4 V (12 V lead-acid).
`BATTERY_VOLTAGE_MIN = 3.6` is meaningless across them. Reuse the existing `AppConfig`/`ProductConfig`
override machinery — a "family" is a product-like config scope.

**Metrics resolve per-metric, not per-packet.** A node publishes multiple table schemas
(`mda_perham` has 7; only one carries battery). Walk that node's packets newest-first and take the
first that contains each metric. Naive "latest packet" made healthy nodes look metric-less.

**Packets order by the logger's own clock, not by `id`.** `id` is not monotonic with device time
(2.2% of `mda_perham`'s 30k packets arrive out of order).

---

## Seven bugs the 50k file caught — do not reintroduce

The small `raw_data_new.csv` sample passed all of these. Only `raw_data.csv` exposed them.

1. **`Data` event type skipped entirely.** 1305 rows / 13 nodes. Detection matched only `event == "csv"`.
2. **Multi-row messages → 29% data loss.** `CSVEventParser` reads `lines[0]`/`lines[1]` only
   (`csv_parser.py:65-66`); 1026 of 3516 data rows live on line 3+. Fix: drive the parser once per
   data row, each becoming its own logical packet via `packet_key = (id, row_offset)`.
3. **Headerless packets.** See "Parked" below.
4. **Memory blowup.** 460k measurement rows × 12 object cols exhausted memory building the DataFrame.
   Fix: `make_keeper()` derives a column filter from the specs — 15.8% retained, self-maintaining.
5. **`id` not chronological** → negative staleness (`-46 min old`) and a garbage `Record #` of
   7,691,276 (correct: 192,304). Fix: sort packets by device clock.
6. **Exact duplicate rows** — 7,932 copies in 50k rows. Inflate error counts and packet totals.
   Dedup on `(id, node_id, event, message)`. **Root cause is the `JOIN node` fan-out — see the
   SEPARATE PRE-EXISTING BUG section at the top; it affects the existing pipeline too.**
7. **`packets_ago` is the wrong staleness unit.** `mda_perham` publishes ~22 packets/min; the other
   `mda_*` loggers publish hourly. Report `stale_seconds` from the device clock.

---

## Limitations of the reused `data_parser` classes

- **`CSVEventParser` only understands 3-part headers.** Family A also uses 2-part headers for
  single-value sensors (`DS18.0`, `SoilMoisture.0`, `Wind Direction.0`, `SolarRadiation.0`), which
  fall into its `device_type="Unknown"` fallback. Repaired in `parse_gems_csv`.
- **It reports unknown headers with a bare `print()`**, not the logger → ~60 junk lines/run in cron.
  Wrapped in `redirect_stdout` (`_quiet()`).
- **It reads only the first data row** — see bug #2.
- **`JSONEventParser` silently drops `TIMESTAMP(TS)` and `RECORD(RN)`** — it lumps them with lat/lon
  as `geo_fields` and skips them (`json_parser.py:91-97`). These are the two most valuable fields
  (logger clock + record counter). Re-added from the raw message in `parse_campbell_json`.
- **Family C has genuinely double-encoded field names** (`MJ/mÂ²`); repaired via
  `.encode("latin-1").decode("utf-8")`.
- **Family B needs no encoding work** — the files are clean UTF-8. (An earlier claim of mojibake there
  was a terminal console artifact, not a data problem.)

---

## Resolved: `err.772`

**User decision: report as a dead Hedorah-NDIR sensor.**

Family A reports sensor faults in-band as a value of `err.<code>` in any data column — a completely
separate channel from `error/v2` packets. 240 occurrences in the 50k file, all on node
`e00fce684b197e6f48ddf33d`, sensor `Hedorah-NDIR [0]`, across 3 columns (CO2, HUMIDITY, TEMPERATURE).
`ERRORCODES.md` is a 32-bit namespace and 772 (0x304) is not in it.

**TODO:** change the generated `error_name` from the current placeholder `SENSOR_772` to something
like `HEDORAH_NDIR_DEAD`, and add it to `CRITICAL_ERRORS` so it flags. Confirm the desired exact
name and whether other `err.*` codes should map to a table.

**Error counts are summed per `(device_type, device_position, error_name)`** across the whole window —
matching how `create_error_count_dataframe` aggregates today. Three failed columns on one sensor is
one broken sensor, not three problems. Current output:

```
e00fce684b197e6f48ddf33d  [GEMS v3 (CSV)]
  error : SENSOR_772 on Hedorah-NDIR [0]  count=240  cols=3
```

---

## Parked: the headerless node

**User decision: ignore it. Treat as staleness-only. It's one device.**
The prototype already does exactly this — no code change needed.

`e00fce68963fa0b8f3fc6ece` sends 87 unique packets (261 with duplicates) of 19 bare positional
values and **never sends a headered packet** in 50k rows. Nothing in-band recovers the schema.
It still gets a `Monitoring` record via an `__unparseable__` marker so the node stays **visible**
for staleness monitoring rather than silently vanishing — deliberately *not* guessing a mapping,
since wrong readings are worse than no readings.

**Why the supplied header was rejected.** A candidate header was provided:

```
Time,DPS368.0.PRESSURE(Pa),DPS368.0.TEMPERATURE(C),DS18.0(C),PAC1720.0.CURRENT(mA),
PAC1720.0.CURRENT_2(mA),PAC1720.0.VOLTAGE(V),PAC1720.0.VOLTAGE_2(V),
Rain.0.COUNT_OVER_TIME(mm/hr),Rain.0.Count(mm),SHT31.0.HUMIDITY(%),SHT31.0.TEMPERATURE(C),
SHTC3.0.HUMIDITY(%),SHTC3.0.TEMPERATURE(C),SoilMoisture.0(V),TCS3400.LIGHT_BLUE(Counts),
TCS3400.LIGHT_GREEN(Counts),TCS3400.LIGHT_RED(Counts),Wind.0(mV)
```

Column count matches (19/19), but **it is sorted alphabetically after `Time`** (verified:
`supplied[1:] == sorted(supplied[1:])`) while the data is in the device's native emission order.
Applied positionally it yields physically impossible values — 78 Pa atmospheric pressure,
2555 °C on a DS18, 51 V on a Li-ion pack.

The data is very likely in the **native Family A order** instead, which produces plausible values in
every column — median pressure **98,241 Pa**, battery **4.141 V**, wind ADC pinned at **4095**
(12-bit rail). This is recorded only in case the node is ever revisited; per user decision it is
**not** being implemented.

---

## What breaks in the existing pipeline (unstarted — this is step 1)

Fix these first; nothing else runs until they're done.

1. `data_formatter.py:30` — hard-filters `packet_types="error/v2, diagnostic/v2"`; new rows dropped.
2. `data_formatter.py:73-221` — every extractor hardcoded to `device_type == "Kestrel"` +
   `measurement_name in {PORT_V, AVG_P, RH}` with `ast.literal_eval` array indexing.
3. `data_analyzer.py` — output dict is a fixed 4-slot shape (battery/system/humidity/errors).
4. `produce_db.py:51-53` — `(battery_ts or system_ts or humidity_ts).strftime(...)` →
   **`AttributeError`, pipeline dies** when all three are `None` for a new node.
5. `produce_db.py:65-86` — `get_device_info("mda_becker")` hits the Particle API, returns
   `(None, None)`; `LoggerInfo.product_name`/`particle_url` are `nullable=False` →
   **`IntegrityError`, whole commit rolls back.** `Monitoring.battery/system/humidity` are also
   `nullable=False`.
6. Frontend `utils.js:136-151` hardcodes 3.6 / 3.4 / 0.364 / 65 in the gauge colors, outside the
   config system. `deriveProblems` only knows battery/system/humidity/critical_errors.

---

## Next steps

0. **(Independent) Fix the `JOIN node` fan-out** — see the SEPARATE PRE-EXISTING BUG section. Not a
   prerequisite for anything below, but it is currently corrupting the live report and is a much
   smaller change than the rest of this work.
1. **Wire the prototype in** — promote `prototype/packet_adapters.py` + `metric_specs.py` to
   production modules in `device_monitoring/`.
2. **Unbreak the pipeline** (~1 hr) — make metric columns nullable, guard the `device_timestamp`
   chain, make `build_logger_info` tolerate non-Particle nodes (fall back to `node_id` as
   `field_name`, family name as `product_name`, `particle_url=""`).
3. **Rename the `err.772` error** to the agreed Hedorah-NDIR name; add to `CRITICAL_ERRORS`.
4. **Wire adapters into `data_formatter`** — route by family, run alongside the Kestrel path, keep
   the Kestrel output byte-identical.
5. **Extend config + DB** — per-family threshold defaults in `config.py` published via
   `build_app_config()`; add `device_family` / `metrics` columns.
6. **Frontend** — generalize `deriveProblems` and `GaugeBars` to iterate `metrics`; move hardcoded
   colors into config; add family grouping.
7. **Email / `message_builder`** — same generalization or a family-specific section.
8. **Validate against a full production window** before trusting any of it.

---

## Open questions

- Exact `error_name` for the dead Hedorah-NDIR; whether other `err.*` codes need a decode table.
- **`PAC1720` channel assignment and current units are assumed.** Channel 1 reads a flat 0.0 on
  some nodes (unused channel or dead shunt?); `CURRENT_2` units inferred as mA from magnitude.
- Per-family threshold values — currently only the config *keys* exist
  (`battery_percent_min`, `tilt_angle_max`), not vetted numbers.
- **Node `e00fce683130d013246034f3` reports 99.998% inbox humidity on every packet.** Under
  `INBOX_HUMIDITY_MAX = 65` it will alarm every day forever. Almost certainly a failed SHTC3.
  Worth checking before it trains people to ignore the dashboard.

---

## Effort estimate

**5-7 focused days.** Parsing is the easy part. The cost is breadth: "battery voltage" is currently a
load-bearing concept threaded through the DB schema, config, flagging logic, email, and three React
components — and it stops being universal the moment a Campbell logger shows up on a 13 V rail.

Suggested de-risking: start new families in **staleness-only mode** (which is free — `publish_time`
already flows through `_extract_common_fields`), then layer per-family thresholds after watching real
data for a week.

---

## Process note for future me

The small 148-row sample validated a design that was **wrong in seven ways** against the 50k file.
Two claims I stated as fact from first-packet-per-node sampling turned out false (that
`nwroc_campbell_1`/`rroc_campbell_1` had no battery field — they do). **Verify every per-family claim
in this document against a full window before writing production code.** The metric picks in
`FAMILY_SPECS` come from the same sampling that produced those errors.
