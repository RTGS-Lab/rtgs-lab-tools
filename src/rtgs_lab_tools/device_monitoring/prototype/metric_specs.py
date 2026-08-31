"""PROTOTYPE - declarative per-family metric extraction.

This is the whole point of the design: all per-device-type knowledge lives in
one table of data, not in code. Onboarding "family #4" means adding one entry
to METRIC_SPECS - no new columns, no new backend branches, no frontend edit.

Each spec maps raw measurement paths -> a canonical metric key that the
existing threshold/config/ignore machinery can key on.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional

from packet_adapters import (
    CAMPBELL_JSON,
    GEMS_CSV,
    HEADERLESS,
    UNPARSEABLE_PATH,
    ZENTRA_CSV,
    is_inline_error,
    is_sentinel,
)


@dataclass
class MetricSpec:
    """How to pull one canonical metric out of a family's measurements."""

    key: str                      # canonical name, e.g. "battery_voltage"
    label: str                    # what the dashboard shows
    unit: str                     # canonical unit AFTER scaling
    paths: List[str]              # candidate measurement_path values, in priority order
    scale: float = 1.0            # multiply raw value (e.g. mV -> V)
    threshold_key: Optional[str] = None   # which config key gates it
    note: str = ""                # assumptions worth reviewing


@dataclass
class FamilySpec:
    family: str
    display_name: str
    metrics: List[MetricSpec] = field(default_factory=list)
    device_time: Optional[Callable] = None   # extract the logger's own clock


# --- device-clock extractors ------------------------------------------------
# Separate from publish_time: a gateway can keep publishing while the logger
# behind it has frozen, so the device's own clock is the better staleness test.


def _unix(values):
    raw = values.get("ParticleTime.0.TIME") or values.get("timestamp_utc")
    if raw is None:
        return None
    try:
        return datetime.fromtimestamp(float(raw), tz=timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OSError):
        return None


def _campbell_clock(values):
    raw = values.get("TIMESTAMP(TS)")
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


# --- the table ---------------------------------------------------------------

FAMILY_SPECS = {
    GEMS_CSV: FamilySpec(
        family=GEMS_CSV,
        display_name="GEMS v3 (CSV)",
        device_time=_unix,
        metrics=[
            MetricSpec(
                key="battery_voltage",
                label="Battery",
                unit="V",
                paths=["PAC1720.0.VOLTAGE_2"],
                threshold_key="battery_voltage_min",
                note="VOLTAGE (ch 1) reads a flat 0.0 in the sample; ch 2 "
                     "carries the ~4.1V pack. CONFIRM channel assignment.",
            ),
            MetricSpec(
                key="battery_current",
                label="Battery current",
                unit="mA",
                paths=["PAC1720.0.CURRENT_2"],
                note="Units assumed mA from magnitude (26-99). CONFIRM.",
            ),
            MetricSpec(
                key="inbox_humidity",
                label="Inbox humidity",
                unit="%",
                paths=["SHTC3.0.HUMIDITY"],
                threshold_key="inbox_humidity_max",
                note="One node pins at 99.998% across every packet - likely a "
                     "failed sensor rather than a real reading.",
            ),
        ],
    ),
    ZENTRA_CSV: FamilySpec(
        family=ZENTRA_CSV,
        display_name="METER ZL6 / ATMOS 41",
        device_time=_unix,
        metrics=[
            MetricSpec(
                key="battery_voltage",
                label="Battery",
                unit="V",
                paths=["Battery Voltage (mV) Battery P7"],
                scale=0.001,                      # mV -> V
                threshold_key="battery_voltage_min",
            ),
            MetricSpec(
                key="battery_percent",
                label="Battery %",
                unit="%",
                paths=["Battery Percent (%) Battery P7"],
                threshold_key="battery_percent_min",
                note="Better cross-family health signal than raw volts.",
            ),
            MetricSpec(
                key="logger_temperature",
                label="Logger temp",
                unit="F",
                paths=["Logger Temperature (°F) Barometer P8"],
            ),
            MetricSpec(
                key="tilt_angle",
                label="Tilt",
                unit="deg",
                paths=["Tilt Angle (°) ATMOS 41 G2 P1"],
                threshold_key="tilt_angle_max",
                note="Large tilt = station knocked over. Only present on G2 units.",
            ),
        ],
    ),
    CAMPBELL_JSON: FamilySpec(
        family=CAMPBELL_JSON,
        display_name="Campbell Scientific",
        device_time=_campbell_clock,
        metrics=[
            MetricSpec(
                key="battery_voltage",
                label="Battery",
                unit="V",
                # Same metric, three different field names across loggers.
                # This alias list is exactly the kind of per-family knowledge
                # that must not be hardcoded in the analyzer.
                paths=[
                    "BATT_hourly_min_V(vdc)",
                    "BattV_Avg(Volts)",
                    "BATT_Min(unitless)",
                ],
                threshold_key="battery_voltage_min",
                note="Every Campbell node in the sample reports battery in at "
                     "least one of its tables - but not in every table, which "
                     "is why resolution is per-metric, not per-packet.",
            ),
            MetricSpec(
                key="panel_temperature",
                label="Panel temp",
                unit="C",
                paths=["PTemp_C_Avg(Deg C)"],
            ),
            MetricSpec(
                key="record_number",
                label="Record #",
                unit="",
                paths=["RECORD(RN)"],
                note="Gaps between consecutive runs indicate lost records.",
            ),
        ],
    ),
    # Headerless packets: no schema, so no metrics can be extracted. The node
    # still gets a record so it stays visible for staleness monitoring.
    HEADERLESS: FamilySpec(
        family=HEADERLESS,
        display_name="Unknown schema (headerless CSV)",
        device_time=None,
        metrics=[],
    ),
    # --- family #4 would be added here, and ONLY here. ---
}


_EPOCH = datetime(1970, 1, 1)


# --- column filtering --------------------------------------------------------
# Paths carrying the logger's own clock. Kept regardless of the metric specs.
CLOCK_PATHS = {"ParticleTime.0.TIME", "timestamp_utc", "TIMESTAMP(TS)"}


def make_keeper():
    """Build the predicate that decides which measurements are worth keeping.

    Monitoring reads ~4 columns per family out of the 20-70 each packet
    carries. Keeping everything means ~480k object-dtype rows for a 3-day
    window, which is both slow and (measured) enough to blow up DataFrame
    construction. The specs already declare exactly what's needed, so this
    derives the filter from them - add a MetricSpec and its column is retained
    automatically, with no second list to keep in sync.

    Inline `err.*` values are always kept: they can appear in ANY column, so
    they can't be selected by path.
    """
    wanted = set(CLOCK_PATHS) | {UNPARSEABLE_PATH}
    for spec in FAMILY_SPECS.values():
        for metric in spec.metrics:
            wanted.update(metric.paths)

    def keep(record):
        if record.get("measurement_path") in wanted:
            return True
        return is_inline_error(record.get("value"))

    return keep


# --- extraction --------------------------------------------------------------


def collect_inline_errors(group):
    """Sum Family A's in-band `err.<code>` faults per sensor.

    Three failed columns on one Hedorah-NDIR are one broken sensor seen three
    times, not three problems, so counts are summed per
    (device_type, device_position, error_name) - matching how the existing
    error/v2 path aggregates in data_formatter.create_error_count_dataframe.

    Counted across every packet in the window, not just the newest, so the
    count means "occurrences in the window" exactly as it does today.
    """
    tally = {}
    for row in group.itertuples():
        if not is_inline_error(row.value):
            continue
        position = row.device_position
        if isinstance(position, (list, tuple)):
            position = ",".join(str(p) for p in position)
        key = (
            row.device_type or "",
            position or "",
            f"SENSOR_{str(row.value).strip().split('.')[-1]}",
        )
        entry = tally.setdefault(
            key,
            {
                "device_type": key[0],
                "device_position": key[1],
                "error_name": key[2],
                "count": 0,
                "columns": set(),
            },
        )
        entry["count"] += 1
        entry["columns"].add(row.measurement_path)

    errors = []
    for entry in tally.values():
        entry["columns"] = sorted(entry["columns"])
        errors.append(entry)
    return sorted(errors, key=lambda e: -e["count"])


def build_node_records(parsed_df):
    """Collapse parsed measurements into one monitoring record per node.

    NOT "take the latest packet". A single logger can publish several different
    table schemas - Campbell nodes in the sample emit up to 3, and only one of
    them carries the battery reading. Taking the newest packet wholesale makes
    a healthy node look metric-less whenever its most recent publish happened
    to be a different table.

    So each metric is resolved independently: walk that node's packets
    newest-first and take the first one that actually contains the metric. We
    record `packets_ago` so a metric that has silently stopped updating is
    visible rather than looking current.
    """
    records = []

    for (node_id, family), group in parsed_df.groupby(
        ["node_id", "device_family"], dropna=False
    ):
        spec = FAMILY_SPECS.get(family)
        if spec is None:
            continue

        # Packets newest-first, keyed by (message id, row offset) so the extra
        # data rows inside a multi-row message count as separate samples.
        # publish_time is absent from the offline sample, so the key stands in
        # for arrival order; the real pipeline would sort on publish_time.
        # groupby once rather than re-filtering per key: at 50k raw rows the
        # naive `group[group.packet_key == key]` inside the loop is O(n^2) and
        # turns a ~20s run into minutes.
        packets = [
            (key, rows, dict(zip(rows["measurement_path"], rows["value"])))
            for key, rows in group.groupby("packet_key", sort=False)
        ]

        # Order by the logger's OWN clock, not by row id. Measured: id is not
        # monotonic with device time (2.2% of mda_perham's 30k packets arrive
        # out of order), so id-ordering picked a "newest" packet that was
        # actually 46 minutes older than another - which surfaced as negative
        # staleness. Packets with no clock keep id order as a fallback.
        def _order(packet):
            clock = spec.device_time(packet[2]) if spec.device_time else None
            return (clock is not None, clock or _EPOCH, packet[0])

        packets.sort(key=_order, reverse=True)

        # Device clock: newest packet that carries one.
        device_time = None
        if spec.device_time:
            for _pid, _rows, values in packets:
                device_time = spec.device_time(values)
                if device_time:
                    break

        metrics, dropped = [], []
        for metric in spec.metrics:
            resolved = None
            for age, (_pid, _rows, values) in enumerate(packets):
                raw, source = None, None
                for path in metric.paths:
                    if path in values:
                        raw, source = values[path], path
                        break
                if source is None:
                    continue                  # not in this table; try older
                if is_inline_error(raw) or is_sentinel(raw):
                    dropped.append(f"{metric.key} ({source} = {raw!r})")
                    continue
                try:
                    measured_at = spec.device_time(values) if spec.device_time else None
                    resolved = (float(raw) * metric.scale, source, age, measured_at)
                except (TypeError, ValueError):
                    dropped.append(f"{metric.key} ({source} = {raw!r})")
                    continue
                break

            if resolved is None:
                continue                      # this logger truly never reports it

            value, source, age, measured_at = resolved

            # Staleness in TIME, not packets. Publish rates differ by three
            # orders of magnitude across these families - mda_perham emits
            # ~22 packets/min while the other mda_* loggers emit hourly - so
            # "217 packets back" is meaningless while "4 minutes old" is not.
            stale_seconds = None
            if measured_at and device_time:
                stale_seconds = int((device_time - measured_at).total_seconds())

            metrics.append(
                {
                    "key": metric.key,
                    "label": metric.label,
                    "value": round(value, 4),
                    "unit": metric.unit,
                    "threshold_key": metric.threshold_key,
                    "source": source,
                    "packets_ago": age,
                    "measured_at": measured_at.isoformat() if measured_at else None,
                    "stale_seconds": stale_seconds,
                }
            )

        records.append(
            {
                "node_id": node_id,
                "device_family": family,
                "display_name": spec.display_name,
                "device_time": device_time,
                "packets": len(packets),
                "schemas": len({frozenset(v) for _p, _r, v in packets}),
                "metrics": metrics,
                "errors": collect_inline_errors(group),
                "unusable": dropped,
            }
        )

    return records
