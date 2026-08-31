"""PROTOTYPE - packet adapters for the new device families.

Turns a raw GEMS row (node_id / event / message / publish_time) into the same
normalized measurement records the existing data_parser emits:

    {node_id, timestamp, device_family, device_type, device_position,
     measurement_path, measurement_name, value, unit}

Families A (GEMS/Particle CSV) and C (Campbell JSON) delegate to parser classes
that already exist in data_parser but are never registered by parse_gems_data.
Family B (Zentra/METER CSV) needs a local header parser: its headers contain no
dots, so CSVEventParser would dump every column into its "malformed header"
fallback.

Nothing in data_parser/ is modified.
"""

import contextlib
import csv
import io
import json
import os
import re

import pandas as pd

from rtgs_lab_tools.data_parser.parsers.csv_parser import CSVEventParser
from rtgs_lab_tools.data_parser.parsers.json_parser import JSONEventParser


@contextlib.contextmanager
def _quiet():
    """Silence the delegated parsers.

    CSVEventParser reports unrecognized headers with a bare print() to stdout,
    not the logger. Family A trips it on every packet (see parse_gems_csv), so
    in the daily cron job that would be hundreds of junk lines per run.
    """
    with open(os.devnull, "w") as devnull:
        with contextlib.redirect_stdout(devnull):
            yield

# --------------------------------------------------------------------------
# Family detection
# --------------------------------------------------------------------------
# `event` alone is not enough: "CSV" covers two unrelated formats, so we sniff
# the header row to tell them apart.

GEMS_CSV = "gems_csv"        # Family A - e00fce68...
ZENTRA_CSV = "zentra_csv"    # Family B - z6-*
CAMPBELL_JSON = "campbell_json"  # Family C - mda_*, *roc_campbell_*
HEADERLESS = "headerless_csv"    # positional values, schema unknown

# Both "CSV" and "Data" (capital D) carry the same Family A payload. "Data" is
# NOT the same thing as "data/v2", which the existing pipeline already handles.
_CSV_EVENTS = {"csv", "data"}


def _lines(message):
    if not isinstance(message, str):
        return []
    return [line for line in message.strip().split("\n") if line.strip()]


def _looks_numeric(line):
    """True if a line is all values - i.e. this packet has no header row."""
    tokens = [t.strip() for t in line.split(",")]
    numeric = 0
    for token in tokens:
        try:
            float(token)
            numeric += 1
        except ValueError:
            pass
    return numeric / max(len(tokens), 1) > 0.8


def detect_family(row):
    """Return a family constant, or None if we have no adapter for this row."""
    event = str(row.get("event") or "").strip().lower()

    if event == "json":
        return CAMPBELL_JSON

    if event in _CSV_EVENTS:
        lines = _lines(row.get("message"))
        if not lines:
            return None
        # Some packets are bare value rows with no header at all.
        if _looks_numeric(lines[0]):
            return HEADERLESS
        columns = [c.strip() for c in lines[0].split(",")]
        # Family A headers are Sensor.Instance.MEASUREMENT -> at least 2 dots.
        if any(c.count(".") >= 2 for c in columns):
            return GEMS_CSV
        if columns[0].lower() == "timestamp_utc":
            return ZENTRA_CSV
        return None

    return None


# --------------------------------------------------------------------------
# Sentinel handling
# --------------------------------------------------------------------------
# Loggers report "no reading" as an out-of-band number rather than a null.
# These must be dropped before any threshold comparison, or a dead sensor
# reads as a wildly healthy one.

SENTINEL_NUMBERS = {-9999.0, 9999.0, -99999.0, 99999.0, -6999.0}
SENTINEL_STRINGS = {"nan", "null", "none", ""}


def is_sentinel(value):
    if value is None:
        return True
    if isinstance(value, str):
        if value.strip().lower() in SENTINEL_STRINGS:
            return True
        try:
            return float(value) in SENTINEL_NUMBERS
        except ValueError:
            return False
    if isinstance(value, (int, float)):
        return float(value) in SENTINEL_NUMBERS
    return False


def is_inline_error(value):
    """Family A reports sensor faults in-band as a value of `err.<code>`."""
    return isinstance(value, str) and value.strip().lower().startswith("err.")


# --------------------------------------------------------------------------
# Family A - GEMS/Particle CSV (delegates to data_parser's CSVEventParser)
# --------------------------------------------------------------------------

_csv_parser = CSVEventParser()

# CSVEventParser only understands 3-part headers (Sensor.Instance.MEASUREMENT).
# Family A also uses 2-part headers for single-value sensors - DS18.0,
# SoilMoisture.0, "Wind Direction.0", SolarRadiation.0 - which it dumps into its
# device_type="Unknown" fallback. We repair those here rather than patch
# data_parser.
_TWO_PART_HEADER = re.compile(r"^(?P<sensor>.+)\.(?P<instance>\d+)$")


def parse_gems_csv(row):
    """Parse one Family A packet, which may contain SEVERAL data rows.

    CSVEventParser reads lines[0] and lines[1] only (csv_parser.py:65-66), so a
    3-line packet loses its final sample. In the 50k file that is 1026 of 3516
    data rows - 29% - silently dropped. We drive the parser once per data row
    instead, so its column logic is still reused but nothing is discarded.

    Each data row becomes its own logical packet via `packet_key`: the rows are
    distinct sample times (different ParticleTime), not one reading.
    """
    lines = _lines(row.get("message"))
    if len(lines) < 2:
        return []

    header, records = lines[0], []
    for offset, data_line in enumerate(lines[1:]):
        synthetic = row.copy()
        synthetic["message"] = f"{header}\n{data_line}"
        with _quiet():
            parsed = _csv_parser.parse(synthetic)

        for rec in parsed:
            rec["device_family"] = GEMS_CSV
            rec["packet_key"] = (row.get("id"), offset)
            if rec.get("device_type") == "Unknown":
                match = _TWO_PART_HEADER.match(rec.get("measurement_path") or "")
                if match:
                    rec["device_type"] = match.group("sensor")
                    rec["device_position"] = [match.group("instance")]
                    # Single-value sensor: the sensor name IS the measurement.
                    rec["measurement_name"] = match.group("sensor")
        records.extend(parsed)

    return records


# --------------------------------------------------------------------------
# Family B - Zentra/METER CSV (local; no dotted headers to key off of)
# --------------------------------------------------------------------------
# Header grammar:  "<Measurement> (<unit>) <Sensor> P<port>"
#   "Air Temperature (°F) ATMOS 41 G2 P1" -> ATMOS 41 G2, port 1,
#                                                 Air Temperature, °F
# Two columns don't follow it: timestamp_utc and MRID.

_ZENTRA_HEADER = re.compile(
    r"^(?P<name>.+?)\s*\((?P<unit>[^)]*)\)\s*(?P<sensor>.+?)\s*P(?P<port>\d+)$"
)


def parse_zentra_csv(row):
    lines = _lines(row.get("message"))
    if len(lines) < 2:
        return []

    headers = [h.strip() for h in lines[0].split(",")]
    common = {
        "id": row.get("id"),
        "node_id": row.get("node_id"),
        "event_type": row.get("event"),
        "timestamp": row.get("publish_time"),
        "message_id": row.get("message_id"),
        "device_family": ZENTRA_CSV,
    }

    records = []
    # Multi-row packets here too - same treatment as Family A.
    for offset, data_line in enumerate(lines[1:]):
        values = []
        for parsed_row in csv.reader(io.StringIO(data_line)):
            values = [v.strip() for v in parsed_row]

        cols, vals = headers, values
        if len(cols) != len(vals):
            limit = min(len(cols), len(vals))
            cols, vals = cols[:limit], vals[:limit]

        for header, value in zip(cols, vals):
            match = _ZENTRA_HEADER.match(header)
            if match:
                device_type = match.group("sensor")
                position = [match.group("port")]
                name = match.group("name")
                unit = match.group("unit")
            else:
                # timestamp_utc / MRID / Latitude - logger-level, not sensor-level
                device_type = "Logger"
                position = None
                name = header
                unit = None

            records.append(
                {
                    **common,
                    "packet_key": (row.get("id"), offset),
                    "device_type": device_type,
                    "device_position": position,
                    "measurement_path": header,
                    "measurement_name": name,
                    "value": _coerce(value),
                    "unit": unit,
                }
            )
    return records


def _coerce(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


# --------------------------------------------------------------------------
# Family C - Campbell JSON (delegates to data_parser's JSONEventParser)
# --------------------------------------------------------------------------
# One wrinkle: a few field names are double-encoded upstream
# ("MJ/mÂ²" instead of "MJ/m²"). Repair it so unit strings and
# metric keys stay stable across loggers.


def _repair_mojibake(text):
    if not isinstance(text, str) or "Â" not in text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


_json_parser = JSONEventParser()

# JSONEventParser deliberately drops TIMESTAMP(TS) and RECORD(RN) (it lumps
# them in with lat/lon as "geo_fields" and skips them). Those are exactly the
# two fields we need most - the logger's own clock and its record counter - so
# we re-add them from the raw message.
_CAMPBELL_PASSTHROUGH = ("TIMESTAMP(TS)", "RECORD(RN)")


def parse_campbell_json(row):
    with _quiet():
        records = _json_parser.parse(row)

    for rec in records:
        rec["device_family"] = CAMPBELL_JSON
        rec["packet_key"] = (row.get("id"), 0)
        rec["measurement_path"] = _repair_mojibake(rec.get("measurement_path"))
        rec["measurement_name"] = _repair_mojibake(rec.get("measurement_name"))
        rec["unit"] = _repair_mojibake(rec.get("unit"))
        # JSONEventParser labels every external logger "External"; split by
        # family so per-family config has something to key on.
        rec["device_type"] = "CampbellLogger"

    try:
        payload = json.loads(row.get("message") or "{}")
    except (ValueError, TypeError):
        payload = {}

    for field_name in _CAMPBELL_PASSTHROUGH:
        if field_name not in payload:
            continue
        records.append(
            {
                "id": row.get("id"),
                "node_id": row.get("node_id"),
                "event_type": row.get("event"),
                "timestamp": row.get("publish_time"),
                "message_id": row.get("message_id"),
                "device_family": CAMPBELL_JSON,
                "packet_key": (row.get("id"), 0),
                "device_type": "CampbellLogger",
                "device_position": None,
                "measurement_path": field_name,
                "measurement_name": field_name.split("(")[0],
                "value": payload[field_name],
                "unit": None,
            }
        )
    return records


UNPARSEABLE_PATH = "__unparseable__"


def parse_headerless(row):
    """Bare value rows with no header.

    The columns are positional and the packet carries no schema. In the 50k
    sample exactly one node does this - and it sends NO headered packet ever,
    so there is nothing in-band to recover the schema from. We deliberately do
    NOT guess a column mapping: inventing one would silently produce wrong
    readings, which is worse than no readings.

    But we still emit a marker record so the node stays VISIBLE. Dropping it
    outright would make a live device silently disappear from monitoring - the
    exact failure the dashboard exists to catch. With the marker it surfaces as
    staleness-only, which is honest and still useful.
    """
    return [
        {
            "id": row.get("id"),
            "node_id": row.get("node_id"),
            "event_type": row.get("event"),
            "timestamp": row.get("publish_time"),
            "message_id": row.get("message_id"),
            "device_family": HEADERLESS,
            "packet_key": (row.get("id"), 0),
            "device_type": "Unknown",
            "device_position": None,
            "measurement_path": UNPARSEABLE_PATH,
            "measurement_name": UNPARSEABLE_PATH,
            "value": None,
            "unit": None,
        }
    ]


ADAPTERS = {
    GEMS_CSV: parse_gems_csv,
    ZENTRA_CSV: parse_zentra_csv,
    CAMPBELL_JSON: parse_campbell_json,
    HEADERLESS: parse_headerless,
}


def parse_new_families(raw_df, keep_record=None):
    """Parse every row of raw_df we have an adapter for.

    Returns (parsed_df, stats). Rows from families we don't handle - including
    the existing diagnostic/v2 and error/v2 packets - are skipped untouched, so
    this runs alongside the current pipeline rather than replacing it.

    `keep_record` is an optional predicate applied to each measurement. Without
    it, a 50k-row window expands to ~480k measurement rows and building one
    object-dtype DataFrame exhausts memory. Monitoring only ever reads a
    handful of columns per family, so the caller passes a predicate built from
    the metric specs and the other ~97% is discarded at parse time.
    """
    records = []
    stats = {
        "parsed": 0,
        "skipped": 0,
        "failed": 0,
        "by_family": {},
        "unparseable_nodes": {},
        "skipped_events": {},
        "measurements_seen": 0,
    }

    for _, row in raw_df.iterrows():
        family = detect_family(row)
        if family is None:
            stats["skipped"] += 1
            event = str(row.get("event") or "")
            stats["skipped_events"][event] = stats["skipped_events"].get(event, 0) + 1
            continue
        try:
            parsed = ADAPTERS[family](row)
        except Exception as exc:  # noqa: BLE001 - prototype: surface, don't die
            stats["failed"] += 1
            print(f"  ! {family} row {row.get('id')}: {exc}")
            continue

        if family == HEADERLESS:
            node = row.get("node_id")
            stats["unparseable_nodes"][node] = (
                stats["unparseable_nodes"].get(node, 0) + 1
            )

        stats["measurements_seen"] += len(parsed)
        if keep_record is not None:
            parsed = [rec for rec in parsed if keep_record(rec)]
        records.extend(parsed)
        stats["parsed"] += 1
        stats["by_family"][family] = stats["by_family"].get(family, 0) + 1

    stats["measurements_kept"] = len(records)
    return pd.DataFrame(records), stats
