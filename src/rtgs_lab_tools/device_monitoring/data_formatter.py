# should utilize parse_gems_data to parse specific packets that are needed to analyze
# takes a dataframe from get_raw_data and formats to before passing to data_analyzer
# input: data_frame (pandas DataFrame)
# output: should return df


# data_formater.py
# takes a csv from get_sensing_data and formats it into a dictionary to pass to data_analyzer
# using error code parser methods
# input: csv filepath
# output: dictionary with node id as key and error counter with battery and systme info added

# from error_code_parser import load_error_database, parse_json_file, parse_csv_file
import csv
import json

from ..data_parser import parse_gems_data
import pprint
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
import ast

def format_battery_data(battery_row):
    if not battery_row:
        return None

    return {
        "node_id": battery_row["node_id"],
        "timestamp": battery_row["publish_time"],
        "voltage": battery_row["battery_voltage"]
    }

def format_data(filepath):
    #load error database from ERRORCODE.md file, or github
    #parse json file with the error database (two other params)
    #add battery info to dictionary
    #add system info to dictionary

    # Load error database (fetches from github if not found locally)
    error_db = load_error_database(None) # 
    if not error_db:
        print("Failed to load error database. Cannot continue.")
    generate_graph = False
    node_filter = "all"  # Use "all" to get counters for all nodes, or specify a list of node IDs

    error_counters = parse_csv_file(filepath, error_db, node_filter)

    # Initialize output dictionary
    formatted_data = {
        node: {
            "errors": error_counts,
            "battery_voltage": None
        } for node, error_counts in error_counters.items()
    }

    # Re-scan CSV to extract first PORT_V[0] (battery) from Kestrel device messages
    # Also ensure that only v3 nodes are included via valid v3 message types
    valid_message_types = {"diagnostic/v2", "data/v2", "metadata/v2", "error/v2"}

    with open(filepath, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            node_id = row["node_id"]
            event_type = row["event"]

            # If event type is invalid, remove the node from formatted_data and skip it
            # V3 nodes should only have specific event types
            if event_type not in valid_message_types:
                if node_id in formatted_data:
                    del formatted_data[node_id]
                continue

            try:
                msg_json = json.loads(row["message"])
                devices = msg_json.get("Diagnostic", {}).get("Devices", [])
                for device in devices:
                    if "Kestrel" in device:
                        port_v = device["Kestrel"].get("PORT_V", [])
                        if port_v and isinstance(port_v[0], (int, float)):
                            first_voltage = port_v[0]
                            # Only set if not already found
                            if node_id not in formatted_data:
                                formatted_data[node_id] = {
                                    "errors": {},
                                    "battery_voltage": first_voltage
                                }
                            elif formatted_data[node_id]["battery_voltage"] is None:
                                formatted_data[node_id]["battery_voltage"] = first_voltage
                            break  # No need to check other devices for this row
            except Exception as e:
                print(f"Error parsing battery info for node {node_id}: {e}")
                continue

    return formatted_data
'''
Ex)
Node: e00fce682ec3d30c0141b86a
  Battery Voltage: 4.021973
    Error: 0x500400f6, Count: 96
    Error: 0x5004f0f8, Count: 96
    Error: 0x80070030, Count: 11
    Error: 0x80090020, Count: 1
    Error: 0x70020033, Count: 1
'''

def explore_data_structure(df):
    """Explore the basic structure and content of the data."""
    print("\n=== DATA STRUCTURE EXPLORATION ===")
    
    # Check if df is actually a DataFrame
    if not hasattr(df, 'shape'):
        print(f"Error: Expected DataFrame but got {type(df).__name__}")
        print(f"Object: {df}")
        return df
    
    # Basic info
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Event types
    if 'event_type' in df.columns:
        print(f"\nEvent types distribution:")
        event_counts = df['event_type'].value_counts()
        print(event_counts)
    else:
        print(f"\nNo 'event_type' column found. Available columns: {list(df.columns)}")
    
    # Device types
    if 'device_type' in df.columns:
        print(f"\nDevice types:")
        device_counts = df['device_type'].value_counts()
        print(device_counts.head(10))
    else:
        print(f"\nNo 'device_type' column found.")
    
    # Unique nodes
    if 'node_id' in df.columns:
        print(f"\nNumber of unique node_ids: {df['node_id'].nunique()}")
        print(f"Node IDs: {df['node_id'].unique()}")
    else:
        print(f"\nNo 'node_id' column found.")
    
    return df

def format_data_with_parser(data_frame):
    # input: data_frame (pandas DataFrame)
    # output: formatted data dictionary

    # get parsed dataframe from parse_gems_data
    # parsed_df = parse_gems_data(data_frame, packet_types="all")
    parsed_result = parse_gems_data(data_frame, packet_types="all")

    # pprint.pprint(parsed_result)
    
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

    # pprint.pprint(parsed_df)

    # Comprehensive data analysis
    # print("Starting comprehensive data analysis...")
    
    # 1. Explore the basic structure and content of the data
    # explore_data_structure(parsed_df)
    
    # # 2. Filter and analyze different types of sensor data
    # data_records, soil_sensor_data = filter_sensor_data(parsed_df)
    
    # # 3. Analyze time-based patterns
    # analyze_time_series(parsed_df)
    
    # # 4. Analyze numeric sensor values
    # analyze_numeric_values(parsed_df)
    
    # # 5. Analyze data by device type
    # analyze_by_device_type(parsed_df)
    
    # # 6. Parse and analyze metadata
    # parse_metadata(parsed_df)
    
    # # 7. Create visualizations
    # create_visualizations(parsed_df)

    # error counts
    error_counts_df = create_error_count_dataframe(parsed_df)
    # print("\nError counts by node_id:")
    # pprint.pprint(error_counts_df)

    # battery voltages
    battery_voltages = create_battery_voltage_dataframe(parsed_df)
    # print("\nBattery voltages by node_id:")
    # pprint.pprint(battery_voltages)

    # system usage
    system_usage_df = create_system_usage_dataframe(parsed_df)
    # print("\nSystem usage by node_id:")
    # pprint.pprint(system_usage_df)
    
    # print("\nData analysis complete!")
    
    # TODO: Return properly formatted data for the analyzer
    final_dict = { "parsed_data" : parsed_df,
             "battery_data" : battery_voltages,
             "error_data" : error_counts_df,
             "system_current_data" : system_usage_df
            }
    
    return final_dict


def create_battery_voltage_dataframe(df):
    """Extract battery voltage (index 0 of PORT_V array) from Kestrel devices by node_id."""
    kestrel_portv = df[(df['device_type'] == 'Kestrel') & (df['measurement_name'] == 'PORT_V')].copy()
    kestrel_portv['timestamp'] = pd.to_datetime(kestrel_portv['timestamp'])
    
    # Used below in place of a lambda function
    def extract_first_value(x):
        return ast.literal_eval(str(x))[0] 
    
    kestrel_portv['port_v_0'] = kestrel_portv['value'].apply(extract_first_value)
    return kestrel_portv.sort_values('timestamp').groupby('node_id').last()[['port_v_0', 'timestamp']]


def create_system_usage_dataframe(df):
    """Extract system usage (index 1 of PORT_I array) from Kestrel devices by node_id."""
    kestrel_porti = df[(df['device_type'] == 'Kestrel') & (df['measurement_name'] == 'PORT_I')].copy()
    kestrel_porti['timestamp'] = pd.to_datetime(kestrel_porti['timestamp'])
    
    # Used below in place of a lambda function
    def extract_second_value(x):
        return ast.literal_eval(str(x))[1]
    
    kestrel_porti['port_i_1'] = kestrel_porti['value'].apply(extract_second_value)
    return kestrel_porti.sort_values('timestamp').groupby('node_id').last()[['port_i_1', 'timestamp']]


def filter_sensor_data(df):
    """Example of filtering data by different criteria."""
    print("\n=== DATA FILTERING EXAMPLES ===")
    
    # Check if df is actually a DataFrame
    if not hasattr(df, 'shape'):
        print(f"Error: Expected DataFrame but got {type(df).__name__}")
        return None, None
    
    # Filter by event type - get only actual sensor measurements
    if 'event_type' in df.columns:
        data_records = df[df['event_type'] == 'data/v2'].copy()
        print(f"Data records: {len(data_records)}")
    else:
        print("No 'event_type' column found")
        data_records = df.copy()
    
    # Filter by device type
    if 'device_type' in df.columns:
        soil_sensor_data = df[df['device_type'] == 'Acclima Soil'].copy()
        print(f"Soil sensor records: {len(soil_sensor_data)}")
    else:
        print("No 'device_type' column found")
        soil_sensor_data = df.copy()
    
    # Filter by time range
    if 'timestamp' in df.columns:
        try:
            # Ensure timestamp is datetime
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            recent_data = df[df['timestamp'] >= '2025-06-20'].copy()
            print(f"Recent data (since ___): {len(recent_data)}")
        except Exception as e:
            print(f"Error filtering by timestamp: {e}")
    
    # Filter by measurement name
    if 'measurement_name' in df.columns:
        temperature_data = df[df['measurement_name'].str.contains('Temperature', na=False)].copy()
        print(f"Temperature measurements: {len(temperature_data)}")
    else:
        print("No 'measurement_name' column found")
    
    return data_records, soil_sensor_data

def analyze_time_series(df):
    """Analyze time-based patterns in the data."""
    print("\n=== TIME SERIES ANALYSIS ===")
    
    # Check if df is actually a DataFrame
    if not hasattr(df, 'shape'):
        print(f"Error: Expected DataFrame but got {type(df).__name__}")
        return
    
    # Focus on actual sensor data
    if 'event_type' in df.columns:
        data_df = df[df['event_type'] == 'data/v2'].copy()
    else:
        data_df = df.copy()
    
    if len(data_df) == 0:
        print("No data/v2 records found for time series analysis")
        return
    
    # Ensure timestamp column exists and is datetime
    if 'timestamp' not in data_df.columns:
        print("No 'timestamp' column found")
        return
    
    try:
        if not pd.api.types.is_datetime64_any_dtype(data_df['timestamp']):
            data_df['timestamp'] = pd.to_datetime(data_df['timestamp'])
        
        # Group by time periods
        data_df['hour'] = data_df['timestamp'].dt.hour
        data_df['date'] = data_df['timestamp'].dt.date
        
        # Data frequency by hour
        hourly_counts = data_df.groupby('hour').size()
        print("Data points by hour of day:")
        print(hourly_counts)
        
        # Daily data summary
        agg_dict = {'node_id': 'count'} if 'node_id' in data_df.columns else {}
        if 'device_type' in data_df.columns:
            agg_dict['device_type'] = lambda x: x.nunique()
        
        if agg_dict:
            daily_summary = data_df.groupby('date').agg(agg_dict)
            if 'node_id' in daily_summary.columns:
                daily_summary = daily_summary.rename(columns={'node_id': 'total_records'})
            if 'device_type' in daily_summary.columns:
                daily_summary = daily_summary.rename(columns={'device_type': 'unique_devices'})
            
            print(f"\nDaily summary (last 5 days):")
            print(daily_summary.tail())
    except Exception as e:
        print(f"Error in time series analysis: {e}")

def analyze_numeric_values(df):
    """Analyze numeric sensor values."""
    print("\n=== NUMERIC VALUE ANALYSIS ===")
    
    # Check if df is actually a DataFrame
    if not hasattr(df, 'shape'):
        print(f"Error: Expected DataFrame but got {type(df).__name__}")
        return
    
    # Focus on data records with numeric values
    if 'event_type' in df.columns:
        data_df = df[df['event_type'] == 'data/v2'].copy()
    else:
        data_df = df.copy()
    
    if 'value' not in data_df.columns:
        print("No 'value' column found")
        return
    
    # Try to convert 'value' column to numeric where possible
    data_df['numeric_value'] = pd.to_numeric(data_df['value'], errors='coerce')
    
    # Get records with numeric values
    numeric_data = data_df[data_df['numeric_value'].notna()].copy()
    
    if len(numeric_data) > 0:
        print(f"Records with numeric values: {len(numeric_data)}")
        
        # Basic statistics
        print("\nNumeric value statistics:")
        print(numeric_data['numeric_value'].describe())
        
        # Value distribution by device type
        if 'device_type' in numeric_data.columns:
            print("\nValue statistics by device type:")
            device_stats = numeric_data.groupby('device_type')['numeric_value'].agg(['count', 'mean', 'std', 'min', 'max'])
            print(device_stats)
    
    # Handle array-like values (e.g., "[333.9375, 258.8249512, 0, 0.0]")
    array_values = data_df[data_df['value'].str.startswith('[', na=False)].copy()
    if len(array_values) > 0:
        print(f"\nRecords with array values: {len(array_values)}")
        print("Sample array values:")
        cols_to_show = ['device_type', 'measurement_name', 'value']
        available_cols = [col for col in cols_to_show if col in array_values.columns]
        if available_cols:
            print(array_values[available_cols].head())

def analyze_by_device_type(df):
    """Analyze data grouped by device type."""
    print("\n=== DEVICE TYPE ANALYSIS ===")
    
    # Check if df is actually a DataFrame
    if not hasattr(df, 'shape'):
        print(f"Error: Expected DataFrame but got {type(df).__name__}")
        return
    
    # Check required columns
    required_cols = ['device_type']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Missing required columns: {missing_cols}")
        return
    
    # Group by device type and measurement if measurement_name exists
    if 'measurement_name' in df.columns:
        group_cols = ['device_type', 'measurement_name']
        agg_dict = {'value': 'count'} if 'value' in df.columns else {}
        
        if 'timestamp' in df.columns:
            agg_dict['timestamp'] = ['min', 'max']
        
        if agg_dict:
            device_measurements = df.groupby(group_cols).agg(agg_dict).round(2)
            device_measurements.columns = ['count', 'first_timestamp', 'last_timestamp'] if 'timestamp' in agg_dict else ['count']
            device_measurements = device_measurements.reset_index()
            
            print("Measurements by device type:")
            print(device_measurements.head(20))
    
    # Focus on specific device types
    for device_type in ['Kestrel', 'Talon-Aux', 'Acclima Soil']:
        device_data = df[df['device_type'] == device_type]
        if len(device_data) > 0:
            print(f"\n{device_type} measurements:")
            if 'measurement_name' in device_data.columns:
                measurements = device_data['measurement_name'].value_counts()
                print(measurements.head(10))
            else:
                print(f"  Total records: {len(device_data)}")

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
    error_df = df[df['error_name'].notna() & (df['error_name'] != '')]
    
    # Create pivot table with node_id as index, error_name as columns, and count as values
    error_counts = error_df.groupby(['node_id', 'error_name']).size().unstack(fill_value=0)

    return error_counts

def parse_metadata(df):
    """Parse and analyze metadata column."""
    print("\n=== METADATA ANALYSIS ===")
    
    # Check if df is actually a DataFrame
    if not hasattr(df, 'shape'):
        print(f"Error: Expected DataFrame but got {type(df).__name__}")
        return
    
    if 'metadata' not in df.columns:
        print("No 'metadata' column found")
        return
    
    # Sample metadata parsing
    metadata_records = df[df['metadata'].notna()].copy()
    
    if len(metadata_records) > 0:
        print(f"Records with metadata: {len(metadata_records)}")
        
        # Try to parse metadata as JSON/dictionary
        def safe_parse_metadata(meta_str):
            try:
                # Handle string representation of dictionary
                if str(meta_str).startswith("{'") or str(meta_str).startswith('{"'):
                    return ast.literal_eval(str(meta_str))
                return None
            except:
                return None
        
        metadata_records['parsed_metadata'] = metadata_records['metadata'].apply(safe_parse_metadata)
        parsed_count = metadata_records['parsed_metadata'].notna().sum()
        
        print(f"Successfully parsed metadata: {parsed_count}")
        
        if parsed_count > 0:
            # Extract common metadata fields
            sample_metadata = metadata_records[metadata_records['parsed_metadata'].notna()]['parsed_metadata'].iloc[0]
            if isinstance(sample_metadata, dict):
                print(f"Sample metadata keys: {list(sample_metadata.keys())}")

def create_visualizations(df):
    """Create basic visualizations of the data."""
    print("\n=== CREATING VISUALIZATIONS ===")
    
    # Check if df is actually a DataFrame
    if not hasattr(df, 'shape'):
        print(f"Error: Expected DataFrame but got {type(df).__name__}")
        return
    
    try:
        # Set up the plotting style
        plt.style.use('default')
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Event type distribution
        if 'event_type' in df.columns:
            event_counts = df['event_type'].value_counts()
            axes[0, 0].pie(event_counts.values, labels=event_counts.index, autopct='%1.1f%%')
            axes[0, 0].set_title('Distribution of Event Types')
        else:
            axes[0, 0].text(0.5, 0.5, 'No event_type column', ha='center', va='center')
            axes[0, 0].set_title('Event Types - No Data')
        
        # 2. Device type distribution (top 10)
        if 'device_type' in df.columns:
            device_counts = df['device_type'].value_counts().head(10)
            axes[0, 1].bar(range(len(device_counts)), device_counts.values)
            axes[0, 1].set_xticks(range(len(device_counts)))
            axes[0, 1].set_xticklabels(device_counts.index, rotation=45)
            axes[0, 1].set_title('Top 10 Device Types')
            axes[0, 1].set_ylabel('Count')
        else:
            axes[0, 1].text(0.5, 0.5, 'No device_type column', ha='center', va='center')
            axes[0, 1].set_title('Device Types - No Data')
        
        # 3. Data over time (daily counts)
        if 'timestamp' in df.columns:
            try:
                if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['date'] = df['timestamp'].dt.date
                daily_counts = df.groupby('date').size()
                axes[1, 0].plot(daily_counts.index, daily_counts.values, marker='o')
                axes[1, 0].set_title('Data Points per Day')
                axes[1, 0].set_ylabel('Count')
                axes[1, 0].tick_params(axis='x', rotation=45)
            except Exception as e:
                axes[1, 0].text(0.5, 0.5, f'Timestamp error: {str(e)[:30]}...', ha='center', va='center')
                axes[1, 0].set_title('Time Series - Error')
        else:
            axes[1, 0].text(0.5, 0.5, 'No timestamp column', ha='center', va='center')
            axes[1, 0].set_title('Time Series - No Data')
        
        # 4. Hourly pattern
        if 'timestamp' in df.columns:
            try:
                df['hour'] = df['timestamp'].dt.hour
                hourly_counts = df.groupby('hour').size()
                axes[1, 1].bar(hourly_counts.index, hourly_counts.values)
                axes[1, 1].set_title('Data Points by Hour of Day')
                axes[1, 1].set_xlabel('Hour')
                axes[1, 1].set_ylabel('Count')
            except Exception as e:
                axes[1, 1].text(0.5, 0.5, f'Hour analysis error', ha='center', va='center')
                axes[1, 1].set_title('Hourly Pattern - Error')
        else:
            axes[1, 1].text(0.5, 0.5, 'No timestamp column', ha='center', va='center')
            axes[1, 1].set_title('Hourly Pattern - No Data')
        
        plt.tight_layout()
        plt.savefig('sensor_data_analysis.png', dpi=300, bbox_inches='tight')
        print("Visualizations saved as 'sensor_data_analysis.png'")
        plt.show()
        
    except Exception as e:
        print(f"Error creating visualizations: {e}")

# if __name__ == "__main__":
