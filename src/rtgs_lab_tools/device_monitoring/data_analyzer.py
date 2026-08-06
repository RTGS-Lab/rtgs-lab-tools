"""
Overview:
    - Analyze formatted data and return notification-ready results (python dictionary).
    - Analysis and notification thresholds are based on Field Technician feedback.
Input:
    - data: Dictionary with DataFrames from data_formatter.
Output:
    - Dictionary with analysis results for each node, including:
        - flagged status (True/False)
        - battery voltage (float)
        - system usage (float)
        - errors dictionary with: (dict)
            - error type as key
            - count as value
"""

from datetime import timedelta

import pandas as pd

from .timezones import as_utc, now_utc

from .config import (
    BATTERY_VOLTAGE_MIN,
    CRITICAL_ERRORS,
    INBOX_HUMIDITY_MAX,
    MISSING_NODE_THRESHOLD_HOURS,
    SYSTEM_POWER_MAX,
)


def _error_node_ids(error_df):
    """Return the set of node_ids present in the error dataframe.

    error_data_new is indexed by (node_id, device_type, device_position), so we
    pull node_ids from the first level of the MultiIndex. Falls back to the raw
    index for the (empty / no-error) case where no MultiIndex was built.
    """
    if error_df is None or not hasattr(error_df, "index"):
        return set()
    idx = error_df.index
    if isinstance(idx, pd.MultiIndex):
        return set(idx.get_level_values("node_id"))
    return set(idx)


def analyze_data(data):
    """
    Analyze formatted data and return notification-ready results.

    Input: Dictionary with DataFrames from data_formatter
    Output: Dictionary with analysis results for each node
    """

    if not data:
        return {}

    analyzed_data = {}

    # Extract DataFrames. Errors now come from error_data_new, which is broken
    # out per (node_id, device_type, device_position) instead of just node_id.
    battery_df = data.get("battery_data")
    error_df = data.get("error_data_new")
    system_df = data.get("system_current_data")
    humidity_df = data.get("inbox_humidity_data")

    # node_ids present in the (MultiIndexed) error dataframe
    error_node_ids = _error_node_ids(error_df)

    # Get all unique node_ids from all DataFrames
    all_node_ids = set()
    if battery_df is not None and hasattr(battery_df, "index"):
        all_node_ids.update(battery_df.index)
    all_node_ids.update(error_node_ids)
    if system_df is not None and hasattr(system_df, "index"):
        all_node_ids.update(system_df.index)
    if humidity_df is not None and hasattr(humidity_df, "index"):
        all_node_ids.update(humidity_df.index)

    # Identify nodes that haven't been heard from in the last X hours.
    # Both sides of this comparison must be UTC: device timestamps come from
    # GEMS publish_time (UTC), so using local time here made every node look
    # five hours more recent than it was and pushed the effective missing
    # threshold out to ~29 hours.
    cutoff_time = now_utc() - timedelta(hours=MISSING_NODE_THRESHOLD_HOURS)
    recent_node_ids = set()

    # Check which nodes have recent data (within 24 hours)
    for node_id in all_node_ids:
        most_recent_timestamp = None

        if battery_df is not None and node_id in battery_df.index:
            battery_timestamp = battery_df.loc[node_id, "timestamp"]
            if battery_timestamp and pd.notna(battery_timestamp):
                if hasattr(battery_timestamp, "to_pydatetime"):
                    battery_timestamp = battery_timestamp.to_pydatetime()
                elif isinstance(battery_timestamp, str):
                    battery_timestamp = pd.to_datetime(
                        battery_timestamp
                    ).to_pydatetime()
                most_recent_timestamp = battery_timestamp

        if system_df is not None and node_id in system_df.index:
            system_timestamp = system_df.loc[node_id, "timestamp"]
            if system_timestamp and pd.notna(system_timestamp):
                if hasattr(system_timestamp, "to_pydatetime"):
                    system_timestamp = system_timestamp.to_pydatetime()
                elif isinstance(system_timestamp, str):
                    system_timestamp = pd.to_datetime(system_timestamp).to_pydatetime()
                if (
                    most_recent_timestamp is None
                    or system_timestamp > most_recent_timestamp
                ):
                    most_recent_timestamp = system_timestamp

        if humidity_df is not None and node_id in humidity_df.index:
            inbox_timestamp = humidity_df.loc[node_id, "timestamp"]
            if inbox_timestamp and pd.notna(inbox_timestamp):
                if hasattr(inbox_timestamp, "to_pydatetime"):
                    inbox_timestamp = inbox_timestamp.to_pydatetime()
                elif isinstance(inbox_timestamp, str):
                    inbox_timestamp = pd.to_datetime(inbox_timestamp).to_pydatetime()
                if (
                    most_recent_timestamp is None
                    or inbox_timestamp > most_recent_timestamp
                ):
                    most_recent_timestamp = inbox_timestamp

        # If node has data within last 24 hours, it's considered "recent"
        most_recent_timestamp = as_utc(most_recent_timestamp)
        if most_recent_timestamp and most_recent_timestamp > cutoff_time:
            recent_node_ids.add(node_id)

    for node_id in all_node_ids:
        flagged = False
        battery_val = None
        system_val = None
        humidity_val = None
        errors_records = []

        # Get battery voltage
        if battery_df is not None and node_id in battery_df.index:
            battery_val = float(battery_df.loc[node_id, "port_v_0"])
            if battery_val < BATTERY_VOLTAGE_MIN:
                flagged = True

        # Get system usage
        if system_df is not None and node_id in system_df.index:
            system_val = float(system_df.loc[node_id, "avg_p_1"])
            if system_val > SYSTEM_POWER_MAX:
                flagged = True

        # Get inbox humidity
        if humidity_df is not None and node_id in humidity_df.index:
            humidity_val = float(humidity_df.loc[node_id, "inbox_humidity"])
            if humidity_val > INBOX_HUMIDITY_MAX:
                flagged = True

        # Get errors, broken out per (device_type, device_position, error_name).
        # error_df.loc[node_id] drops the node_id level, leaving a frame indexed
        # by (device_type, device_position) with one column per error name.
        if error_df is not None and node_id in error_node_ids:
            node_errors = error_df.loc[node_id]
            for (device_type, device_position), row in node_errors.iterrows():
                for error_name, count in row.items():
                    if pd.isna(count) or count <= 0:
                        continue
                    errors_records.append(
                        {
                            "device_type": device_type,
                            "device_position": device_position,
                            "error_name": error_name,
                            "count": int(count),
                        }
                    )
                    if error_name in CRITICAL_ERRORS:
                        flagged = True

        # Get timestamps
        battery_timestamp = None
        system_timestamp = None
        humidity_timestamp = None

        if battery_df is not None and node_id in battery_df.index:
            battery_timestamp = battery_df.loc[node_id, "timestamp"]

        if system_df is not None and node_id in system_df.index:
            system_timestamp = system_df.loc[node_id, "timestamp"]

        if humidity_df is not None and node_id in humidity_df.index:
            humidity_timestamp = humidity_df.loc[node_id, "timestamp"]

        # Determine if this node is missing (not heard from in 24+ hours)
        is_missing_node = node_id not in recent_node_ids

        # Calculate time since last heard from
        most_recent_timestamp = (
            system_timestamp or battery_timestamp or humidity_timestamp
        )
        last_heard = None
        if most_recent_timestamp:
            if hasattr(most_recent_timestamp, "to_pydatetime"):
                last_heard = most_recent_timestamp.to_pydatetime()
            elif isinstance(most_recent_timestamp, str):
                last_heard = pd.to_datetime(most_recent_timestamp).to_pydatetime()
            else:
                last_heard = most_recent_timestamp

        # Every timestamp leaving this module is aware UTC, so downstream
        # arithmetic and storage never have to guess what clock it is on.
        last_heard = as_utc(last_heard)

        analyzed_data[node_id] = {
            "flagged": flagged or is_missing_node,  # Flag missing nodes
            "battery": battery_val,
            "system": system_val,
            "humidity": humidity_val,
            "errors": errors_records,
            "battery_timestamp": as_utc(battery_timestamp),
            "system_timestamp": as_utc(system_timestamp),
            "humidity_timestamp": as_utc(humidity_timestamp),
            "is_missing": is_missing_node,
            "last_heard": last_heard,
        }

    return analyzed_data
