"""
Overview:
    - Analyze formatted data and return notification-ready results (python dictionary).
    - Analysis and notification thresholds are based on Field Technician feedback.
Input:
    - data: Dictionary with DataFrames from data_formatter.
Output:
    - Dictionary with analysis results for each node, including:
        - flagged status (True/False)
        - battery voltage
        - system usage
        - errors dictionary with:
            - error type as key
            - count as value
"""

import pandas as pd

from .config import BATTERY_VOLTAGE_MIN, CRITICAL_ERRORS, SYSTEM_CURRENT_MAX


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

    # Get all unique node_ids from all DataFrames
    all_node_ids = set()
    if battery_df is not None and hasattr(battery_df, "index"):
        all_node_ids.update(battery_df.index)
    if error_df is not None and hasattr(error_df, "index"):
        all_node_ids.update(error_df.index)
    if system_df is not None and hasattr(system_df, "index"):
        all_node_ids.update(system_df.index)

    for node_id in all_node_ids:
        flagged = False
        battery_val = None
        system_val = None
        errors_dict = {}

        # Get battery voltage
        if battery_df is not None and node_id in battery_df.index:
            battery_val = float(battery_df.loc[node_id, "port_v_0"])
            if battery_val < BATTERY_VOLTAGE_MIN:
                flagged = True

        # Get system usage
        if system_df is not None and node_id in system_df.index:
            system_val = float(system_df.loc[node_id, "avg_p_1"])
            if system_val > SYSTEM_CURRENT_MAX:
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
        
        if battery_df is not None and node_id in battery_df.index:
            battery_timestamp = battery_df.loc[node_id, "timestamp"]
            
        if system_df is not None and node_id in system_df.index:
            system_timestamp = system_df.loc[node_id, "timestamp"]

        analyzed_data[node_id] = {
            "flagged": flagged,
            "battery": battery_val,
            "system": system_val,
            "errors": errors_dict,
            "battery_timestamp": battery_timestamp,
            "system_timestamp": system_timestamp,
        }

    return analyzed_data
