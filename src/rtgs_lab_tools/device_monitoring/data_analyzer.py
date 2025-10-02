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

from datetime import datetime, timedelta

import pandas as pd

from .config import (
    BATTERY_VOLTAGE_MIN,
    CRITICAL_ERRORS,
    INBOX_HUMIDITY_MAX,
    MISSING_NODE_THRESHOLD_HOURS,
    SYSTEM_POWER_MAX,
)


def analyze_data(data):
    """
    Analyze formatted data and return notification-ready results.

    Input: Dictionary with DataFrames from data_formatter
    Output: Dictionary with analysis results for each node
    """

    if not data:
        return {}

    analyzed_data = {}

    # Extract DataFrames
    battery_df = data.get("battery_data")
    error_df = data.get("error_data")
    system_df = data.get("system_current_data")
    humidity_df = data.get("inbox_humidity_data")

    # Get all unique node_ids from all DataFrames
    all_node_ids = set()
    if battery_df is not None and hasattr(battery_df, "index"):
        all_node_ids.update(battery_df.index)
    if error_df is not None and hasattr(error_df, "index"):
        all_node_ids.update(error_df.index)
    if system_df is not None and hasattr(system_df, "index"):
        all_node_ids.update(system_df.index)
    if humidity_df is not None and hasattr(humidity_df, "index"):
        all_node_ids.update(humidity_df.index)

    # Identify nodes that haven't been heard from in the last X hours
    cutoff_time = datetime.now() - timedelta(hours=MISSING_NODE_THRESHOLD_HOURS)
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
        if most_recent_timestamp and most_recent_timestamp > cutoff_time:
            recent_node_ids.add(node_id)

    for node_id in all_node_ids:
        flagged = False
        battery_val = None
        system_val = None
        humidity_val = None
        errors_dict = {}

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

        # Get errors
        if error_df is not None and node_id in error_df.index:
            error_row = error_df.loc[node_id]
            # Convert to dict, excluding NaN values
            errors_dict = {
                col: int(val)
                for col, val in error_row.items()
                if not pd.isna(val) and val > 0
            }

            # Check for critical errors
            for critical_error in CRITICAL_ERRORS:
                if critical_error in errors_dict and errors_dict[critical_error] > 0:
                    flagged = True
                    break

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

        analyzed_data[node_id] = {
            "flagged": flagged or is_missing_node,  # Flag missing nodes
            "battery": battery_val,
            "system": system_val,
            "humidity": humidity_val,
            "errors": errors_dict,
            "battery_timestamp": battery_timestamp,
            "system_timestamp": system_timestamp,
            "humidity_timestamp": humidity_timestamp,
            "is_missing": is_missing_node,
            "last_heard": last_heard,
        }

    return analyzed_data
