"""
Overview:
    - This file is responsible for formatting raw data into a structured format suitable for analysis.
Input:
    - data_frame: A pandas DataFrame containing raw data retrieved from the database.
Output:
    - A python dictionary of Pandas DataFrames containing formatted data including:
        - a battery voltages dataframe
        - a system usage dataframe
        - an error counts dataframe
        - and the aggregated parsed data dataframe (so that all data is still accessible in analysis)
"""

import ast

import pandas as pd

from ..data_parser import parse_gems_data


def format_data_with_parser(data_frame):
    """
    input: data_frame (pandas DataFrame)
    output: formatted data dictionary
    """

    # get parsed dataframe from parse_gems_data
    parsed_result = parse_gems_data(data_frame, packet_types="all")

    # Check if parse_gems_data returns a tuple or DataFrame
    if isinstance(parsed_result, tuple):
        print(f"parse_gems_data returned a tuple with {len(parsed_result)} elements")
        print(f"Types of elements: {[type(x).__name__ for x in parsed_result]}")
        # Assume the first element is the DataFrame
        parsed_df = parsed_result[0] if len(parsed_result) > 0 else None
    else:
        parsed_df = parsed_result

    if parsed_df is None:
        print("No parsed data available")
        return None

    # error counts
    error_counts_df = create_error_count_dataframe(parsed_df)

    # battery voltages
    battery_voltages_df = create_battery_voltage_dataframe(parsed_df)

    # system usage
    system_usage_df = create_system_usage_dataframe(parsed_df)

    final_dict = {
        "parsed_data": parsed_df,
        "battery_data": battery_voltages_df,
        "error_data": error_counts_df,
        "system_current_data": system_usage_df,
    }

    return final_dict


def create_battery_voltage_dataframe(df):
    """Extract battery voltage (index 0 of PORT_V array) from Kestrel devices by node_id."""
    kestrel_portv = df[
        (df["device_type"] == "Kestrel") & (df["measurement_name"] == "PORT_V")
    ].copy()
    kestrel_portv["timestamp"] = pd.to_datetime(kestrel_portv["timestamp"])

    # Used below in place of a lambda function
    def extract_first_value(x):
        return ast.literal_eval(str(x))[0]

    kestrel_portv["port_v_0"] = kestrel_portv["value"].apply(extract_first_value)
    return (
        kestrel_portv.sort_values("timestamp")
        .groupby("node_id")
        .last()[["port_v_0", "timestamp"]]
    )


def create_system_usage_dataframe(df):
    """Extract system usage (index 1 of PORT_I array) from Kestrel devices by node_id."""
    kestrel_porti = df[
        (df["device_type"] == "Kestrel") & (df["measurement_name"] == "PORT_I")
    ].copy()
    kestrel_porti["timestamp"] = pd.to_datetime(kestrel_porti["timestamp"])

    # Used below in place of a lambda function
    def extract_second_value(x):
        return ast.literal_eval(str(x))[1]

    kestrel_porti["port_i_1"] = kestrel_porti["value"].apply(extract_second_value)
    return (
        kestrel_porti.sort_values("timestamp")
        .groupby("node_id")
        .last()[["port_i_1", "timestamp"]]
    )


# Create a DataFrame with error counts by node_id
def create_error_count_dataframe(df):
    """
    Create a DataFrame with error counts by node_id.

    Args:
        df (pandas.DataFrame): Input dataframe with columns including 'node_id' and 'error_name'

    Returns:
        pandas.DataFrame: DataFrame with node_ids as index and error types as columns with counts
    """
    # Filter out rows where error_name is null/empty
    error_df = df[df["error_name"].notna() & (df["error_name"] != "")]

    # Create pivot table with node_id as index, error_name as columns, and count as values
    error_counts = (
        error_df.groupby(["node_id", "error_name"]).size().unstack(fill_value=0)
    )

    return error_counts
