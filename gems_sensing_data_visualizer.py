#!/usr/bin/env python3
"""
GEMS Data Visualizer - Enhanced version
A command line tool for visualizing data from GEMS sensors.

This tool parses JSON data from CSV files containing GEMS sensor data
and generates time-series visualizations for selected parameters.

Usage:
    python gems_visualizer.py --file <filename> [--node-parameter <node_id, parameter_path>]
                             [--output <output_file>] [--type <type_filter>] 
                             [--explore] [--list] [--multi-node-param node_id1,PARAM1 node_id2,PARAM2...]

Examples:
    # Plot a single parameter for a specific device
    python gems_visualizer.py --file data.csv --node-parameter "e00fce68442f64414269c7d8, Diagnostic.Devices.1.GONK.Temperature"
    
    # Plot multiple parameters on the same graph from different devices
    python gems_visualizer.py --file data.csv --multi-node-param "e00fce68442f64414269c7d8, Data.Devices.3.Acclima Soil.VWC" "e00fce68616772391f284037, Data.Devices.4.Acclima Soil.VWC"
    
    # Plot the same parameter for all devices (separately)
    python gems_visualizer.py --file data.csv --node-parameter "all, Data.Devices.0.Acclima Soil.VWC"
    
    # Explore the data structure
    python gems_visualizer.py --file data.csv --explore
    
    # List available parameters
    python gems_visualizer.py --file data.csv --list
    
    # Filter by message type
    python gems_visualizer.py --file data.csv --node-parameter "e00fce68616772391f284037, Data.Devices.2.Kestrel.ALS.Clear" --type data
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
import numpy as np
from typing import Dict, List, Union, Any, Optional, Tuple, Set
import re

# Set non-interactive backend before importing matplotlib
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend by default
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Visualize GEMS sensor data over time.')
    parser.add_argument('--file', required=True, help='Input CSV file path')
    parser.add_argument('--node-parameter', 
                        help='Node ID and Parameter path (e.g., "e00fce68616772391f284037, Data.Devices.0.Acclima Soil.VWC"). Use "all" as node_id to plot for all devices.')
    parser.add_argument('--output', help='Output file path for the graph')
    parser.add_argument('--type', choices=['data', 'diagnostic', 'error', 'metadata'],
                        help='Filter by message type')
    parser.add_argument('--list', action='store_true', 
                        help='List available parameters instead of plotting')
    parser.add_argument('--explore', action='store_true',
                        help='Explore data structure and show available parameters')
    parser.add_argument('--multi-node-param', nargs='+',
                        help='Plot multiple node parameters on the same graph. Format: "node_id, parameter_path"')
    parser.add_argument('--format', choices=['png', 'pdf', 'svg', 'jpg'], default='png',
                        help='Output file format (default: png)')
    parser.add_argument('--no-markers', action='store_true',
                        help='Disable markers on the plot')
    parser.add_argument('--time-range', nargs=2, metavar=('START', 'END'),
                        help='Filter data by time range (format: YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--search', help='Search for parameters containing the given string')
    parser.add_argument('--backend', default='Agg', 
                        help='Matplotlib backend to use (default: Agg for non-interactive)')
    
    args = parser.parse_args()
    
    # Ensure we have a parameter or an exploration option
    if not (args.node_parameter or args.list or args.explore or args.multi_node_param or args.search):
        parser.error("You must specify either a parameter to plot (--node-parameter), multiple parameters (--multi-node-param), "
                    "or use --list or --explore to explore the data structure.")
    
    return args


def read_csv_file(file_path: str) -> List[Dict]:
    """Read CSV file and return a list of dictionaries."""
    data = []
    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)


def parse_json_message(message: str) -> Dict:
    """Parse JSON message from a string."""
    if not message:
        return {}
    
    try:
        # Handle escaped JSON strings
        if message.startswith('"') and message.endswith('"'):
            message = json.loads(message)
        
        # Parse the JSON message
        return json.loads(message)
    except json.JSONDecodeError:
        # Try to clean up the string
        try:
            # Remove escape characters
            message = message.replace('\\', '')
            # Sometimes the message is double-escaped
            if message.startswith('"') and message.endswith('"'):
                message = message[1:-1]
            return json.loads(message)
        except:
            # If all fails, return an empty dict
            return {}


def extract_parameter(data: Dict, param_path: str) -> Any:
    """Extract a parameter from a nested dictionary using a dot-separated path."""
    keys = param_path.split('.')
    current = data
    
    for key in keys:
        # Handle array indices
        if key.isdigit():
            idx = int(key)
            if isinstance(current, list) and 0 <= idx < len(current):
                current = current[idx]
            else:
                return None
        else:
            # Handle dictionary keys with spaces
            if isinstance(current, dict):
                if key in current:
                    current = current[key]
                else:
                    # Try to find a key that matches ignoring case
                    matching_keys = [k for k in current.keys() if k.lower() == key.lower()]
                    if matching_keys:
                        current = current[matching_keys[0]]
                    else:
                        return None
            else:
                return None
                
    return current


def get_timestamp(row: Dict) -> datetime:
    """Extract and parse timestamp from a row."""
    try:
        # Try to parse the publish_time field
        timestamp_str = row.get('publish_time')
        if timestamp_str:
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        
        # If publish_time is not available, try to extract from the message
        message_data = parse_json_message(row.get('message', '{}'))
        
        # Check for 'Time' field in different message types
        time_fields = ['Data', 'Diagnostic', 'Error', 'Metadata']
        for field in time_fields:
            if field in message_data and 'Time' in message_data[field]:
                # This seems to be a Unix timestamp
                unix_time = message_data[field]['Time']
                return datetime.fromtimestamp(unix_time)
        
        # If all else fails, use ingest_time
        ingest_time = row.get('ingest_time')
        if ingest_time:
            return datetime.strptime(ingest_time, '%Y-%m-%d %H:%M:%S.%f')
            
        # If nothing works, return None
        return None
    except Exception as e:
        print(f"Error parsing timestamp: {e}")
        return None


def get_device_id_from_row(row: Dict) -> Optional[str]:
    """Extract device ID from a row."""
    # First, check the node_id field in the CSV
    device_id = row.get('node_id')
    
    # If not found, extract device ID from the message
    if not device_id:
        message_str = row.get('message', '{}')
        message_data = parse_json_message(message_str)
        
        for key in message_data:
            if key in ['Data', 'Diagnostic', 'Error', 'Metadata'] and 'Device ID' in message_data[key]:
                device_id = message_data[key]['Device ID']
                break
    
    return device_id


def filter_data(data: List[Dict], device_id: Optional[str] = None, 
                message_type: Optional[str] = None, 
                time_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
    """Filter data by device ID, message type, and/or time range."""
    filtered_data = []
    
    for row in data:
        # Get the timestamp
        timestamp = get_timestamp(row)
        
        # Filter by time range if specified
        if time_range and timestamp:
            start_time, end_time = time_range
            if timestamp < start_time or timestamp > end_time:
                continue
        
        # Parse the message
        message_str = row.get('message', '{}')
        message_data = parse_json_message(message_str)
        
        # Check if we need to filter by device ID
        if device_id and device_id.lower() != 'all':
            row_device_id = get_device_id_from_row(row)
            if row_device_id != device_id:
                continue
        
        # Check if we need to filter by message type
        if message_type:
            # Extract message type from the event field or from the message itself
            row_message_type = row.get('event', '').split('/')[0] if '/' in row.get('event', '') else ''
            
            # If the message type is specified directly in the message
            if not row_message_type and message_data:
                row_message_type = next((k.lower() for k in message_data.keys() 
                                         if k.lower() in ['data', 'diagnostic', 'error', 'metadata']), '')
            
            if row_message_type.lower() != message_type.lower():
                continue
        
        # If we get here, the row passed all filters
        filtered_data.append(row)
    
    return filtered_data


def explore_data_structure(data: List[Dict]) -> Dict:
    """Explore the data structure and return available parameters."""
    structure = {}
    device_ids = set()
    message_types = set()
    
    for row in data:
        message_str = row.get('message', '{}')
        message_data = parse_json_message(message_str)
        
        # Collect device IDs
        device_id = get_device_id_from_row(row)
        if device_id:
            device_ids.add(device_id)
        
        # Collect message types
        event_type = row.get('event', '').split('/')[0] if '/' in row.get('event', '') else ''
        if event_type:
            message_types.add(event_type)
        
        # Iterate through message types (Data, Diagnostic, Error, Metadata)
        for message_type, type_data in message_data.items():
            if message_type not in structure:
                structure[message_type] = {}
            
            message_types.add(message_type)
            
            # Extract device ID from the message
            if isinstance(type_data, dict) and 'Device ID' in type_data:
                device_ids.add(type_data['Device ID'])
            
            # Add all fields from this message type
            _add_to_structure(structure[message_type], type_data)
    
    return structure, device_ids, message_types


def _add_to_structure(current_dict: Dict, data: Union[Dict, List, Any]) -> None:
    """Helper function for explore_data_structure to recursively build the structure."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key not in current_dict:
                current_dict[key] = {}
            _add_to_structure(current_dict[key], value)
    elif isinstance(data, list) and data:
        # For lists, we'll add each item type we find
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                if i not in current_dict:
                    current_dict[i] = {}
                _add_to_structure(current_dict[i], item)
    else:
        # Leaf node (simple value)
        pass


def print_structure(structure: Dict, prefix: str = "", depth: int = 0) -> None:
    """Print the data structure in a hierarchical format."""
    if depth > 10:  # Limit the recursion depth to avoid infinite loops
        print(f"{prefix}...")
        return
    
    for key, value in sorted(structure.items()):
        if isinstance(value, dict) and value:
            print(f"{prefix}{key}")
            print_structure(value, prefix + "  ", depth + 1)
        else:
            print(f"{prefix}{key}")


def get_available_parameters(structure: Dict, prefix: str = "") -> List[str]:
    """Get a list of available parameters from the data structure."""
    parameters = []
    
    for key, value in structure.items():
        current_path = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict) and value:
            # This is a nested structure, explore it
            parameters.extend(get_available_parameters(value, current_path))
        else:
            # This is a leaf node, add it to the list
            parameters.append(current_path)
    
    return parameters


def search_parameters(parameters: List[str], search_term: str) -> List[str]:
    """Search for parameters containing the given string."""
    return [p for p in parameters if search_term.lower() in p.lower()]


def extract_data_points(data: List[Dict], parameter: str, specific_device_id: Optional[str] = None) -> Dict[str, Tuple[List[datetime], List[float]]]:
    """
    Extract timestamps and values for a given parameter, organized by device ID.
    
    Returns a dictionary mapping device IDs to (timestamps, values) tuples.
    """
    device_data_points = {}
    
    for row in data:
        # Get the device ID
        device_id = get_device_id_from_row(row)
        
        # Skip if we're looking for a specific device and this isn't it
        if specific_device_id and specific_device_id.lower() != 'all' and device_id != specific_device_id:
            continue
        
        # Skip if we couldn't determine the device ID
        if not device_id:
            continue
        
        # Get the timestamp
        timestamp = get_timestamp(row)
        
        # Parse the message
        message_str = row.get('message', '{}')
        message_data = parse_json_message(message_str)
        
        # Extract the parameter value
        value = extract_parameter(message_data, parameter)
        
        # Only add if both timestamp and value are valid
        if timestamp is not None and value is not None:
            try:
                # Try to convert the value to a float
                value = float(value)
                
                # Initialize device entry if it doesn't exist
                if device_id not in device_data_points:
                    device_data_points[device_id] = ([], [])
                
                # Add data point
                device_data_points[device_id][0].append(timestamp)
                device_data_points[device_id][1].append(value)
            except (ValueError, TypeError):
                # If conversion fails, skip this point
                continue
    
    return device_data_points


def plot_data_by_device(data_points_by_device: Dict[str, Tuple[List[datetime], List[float], str]], 
                       output_file: Optional[str] = None, 
                       use_markers: bool = True,
                       format: str = 'png') -> None:
    """Plot multiple time-series data sets organized by device and save or display the plot."""
    if not data_points_by_device:
        print("No data points to plot.")
        return
    
    # Create the plot
    plt.figure(figsize=(12, 6))
    
    # Plot each data set
    for device_id, (timestamps, values, parameter) in data_points_by_device.items():
        # Filter out None values
        valid_data = [(t, v) for t, v in zip(timestamps, values) if t is not None and v is not None]
        if not valid_data:
            print(f"No valid data points for device: {device_id}, parameter: {parameter}")
            continue
        
        timestamps_filtered, values_filtered = zip(*valid_data)
        
        # Choose the marker style based on whether markers are enabled
        marker_style = 'o' if use_markers else None
        
        # Create a label from the device ID and parameter path
        param_label = parameter.split('.')[-1] if '.' in parameter else parameter
        label = f"{device_id} - {param_label}"
        
        # Plot the data
        plt.plot(timestamps_filtered, values_filtered, marker=marker_style, markersize=4, label=label)
    
    # Format the x-axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    
    # Add title and labels
    param_name = next(iter(data_points_by_device.values()))[2]
    plt.title(f"Time Series for {param_name} by Device")
    
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.grid(True)
    
    # Add legend
    plt.legend()
    
    # Rotate date labels for better readability
    plt.gcf().autofmt_xdate()
    
    # Tight layout to use space efficiently
    plt.tight_layout()
    
    # If no output file is specified, create a default one
    if not output_file:
        # Generate a filename based on the parameter
        param_name_clean = param_name.split('.')[-1].replace(' ', '_')
        output_file = f"plot_{param_name_clean}_by_device"
    
    # Add file extension if not present
    if not output_file.lower().endswith(f'.{format}'):
        output_file = f"{output_file}.{format}"
    
    # Create figures directory if it doesn't exist
    os.makedirs("figures", exist_ok=True)
    
    # Save the plot
    plt.savefig(f"figures/{output_file}", format=format, dpi=300)
    print(f"Plot saved to figures/{output_file}")
    
    # Close the plot to free memory
    plt.close()


def plot_multi_params(data_points: List[Tuple[List[datetime], List[float], str, str]], 
                      output_file: Optional[str] = None, 
                      use_markers: bool = True,
                      format: str = 'png') -> None:
    """Plot multiple time-series data sets and save or display the plot."""
    if not data_points:
        print("No data points to plot.")
        return
    
    # Create the plot
    plt.figure(figsize=(12, 6))
    
    # Plot each data set
    for timestamps, values, parameter, device_id in data_points:
        # Filter out None values
        valid_data = [(t, v) for t, v in zip(timestamps, values) if t is not None and v is not None]
        if not valid_data:
            print(f"No valid data points for device: {device_id}, parameter: {parameter}")
            continue
        
        timestamps_filtered, values_filtered = zip(*valid_data)
        
        # Choose the marker style based on whether markers are enabled
        marker_style = 'o' if use_markers else None
        
        # Create a label from the device ID and parameter path
        param_label = parameter.split('.')[-1] if '.' in parameter else parameter
        label = f"{device_id} - {param_label}"
        
        # Plot the data
        plt.plot(timestamps_filtered, values_filtered, marker=marker_style, markersize=4, label=label)
    
    # Format the x-axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    
    # Add title and labels
    plt.title("Multi-Parameter Time Series")
    
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.grid(True)
    
    # Add legend
    plt.legend()
    
    # Rotate date labels for better readability
    plt.gcf().autofmt_xdate()
    
    # Tight layout to use space efficiently
    plt.tight_layout()
    
    # If no output file is specified, create a default one
    if not output_file:
        output_file = f"multi_parameter_plot_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Add file extension if not present
    if not output_file.lower().endswith(f'.{format}'):
        output_file = f"{output_file}.{format}"
    
    # Create figures directory if it doesn't exist
    os.makedirs("figures", exist_ok=True)
    
    # Save the plot
    plt.savefig(f"figures/{output_file}", format=format, dpi=300)
    print(f"Plot saved to figures/{output_file}")
    
    # Close the plot to free memory
    plt.close()


def parse_time_range(time_range_str: List[str]) -> Tuple[datetime, datetime]:
    """Parse time range strings to datetime objects."""
    try:
        start_time = datetime.strptime(time_range_str[0], '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(time_range_str[1], '%Y-%m-%d %H:%M:%S')
        return start_time, end_time
    except ValueError:
        print("Error: Invalid time range format. Use 'YYYY-MM-DD HH:MM:SS'.")
        sys.exit(1)


def parse_node_parameter(node_param_str: str) -> Tuple[str, str]:
    """
    Parse a node_parameter string into device ID and parameter path.
    Format: "device_id, parameter_path"
    """
    try:
        parts = node_param_str.split(',', 1)
        if len(parts) != 2:
            raise ValueError("Invalid format. Expected 'device_id, parameter_path'")
        
        device_id = parts[0].strip()
        parameter = parts[1].strip()
        
        return device_id, parameter
    except Exception as e:
        print(f"Error parsing node parameter string: {e}")
        sys.exit(1)


def main():
    """Main function."""
    args = parse_args()
    
    # Set matplotlib backend
    if args.backend:
        import matplotlib
        matplotlib.use(args.backend)
    
    # Read the CSV file
    print(f"Reading data from {args.file}...")
    data = read_csv_file(args.file)
    
    # Parse time range if specified
    time_range = None
    if args.time_range:
        time_range = parse_time_range(args.time_range)
    
    # Apply type filter if specified
    filtered_data = data
    if args.type:
        print(f"Filtering by message type: {args.type}...")
        filtered_data = filter_data(data, None, args.type, time_range)
    
    if not filtered_data:
        print("No data found after applying filters.")
        return
    
    print(f"Loaded {len(filtered_data)} rows of data.")
    
    # Explore the data structure
    print("Analyzing data structure...")
    structure, device_ids, message_types = explore_data_structure(filtered_data)
    
    # Print available devices and message types
    if device_ids:
        print("\nAvailable devices:")
        for device_id in sorted(device_ids):
            print(f"  {device_id}")
    
    if message_types:
        print("\nAvailable message types:")
        for msg_type in sorted(message_types):
            print(f"  {msg_type}")
    
    # Explore mode - just print the data structure and available parameters
    if args.explore:
        print("\nData structure:")
        print_structure(structure)
        return
    
    # Get available parameters
    parameters = get_available_parameters(structure)
    
    # Search mode - search for parameters containing the given string
    if args.search:
        matching_params = search_parameters(parameters, args.search)
        print(f"\nParameters matching '{args.search}':")
        for param in sorted(matching_params):
            print(f"  {param}")
        return
    
    # List mode - print the available parameters
    if args.list:
        print("\nAvailable parameters:")
        for param in sorted(parameters):
            print(f"  {param}")
        return
    
    # Plot data
    if args.multi_node_param:
        # Plot multiple parameters
        print("Extracting multiple node parameters...")
        data_points = []
        
        for node_param_str in args.multi_node_param:
            device_id, parameter = parse_node_parameter(node_param_str)
            print(f"Processing device: {device_id}, parameter: {parameter}")
            
            # Filter by device if not "all"
            device_specific_data = filtered_data
            if device_id.lower() != 'all':
                device_specific_data = filter_data(filtered_data, device_id)
            
            # Extract data points for this parameter
            device_data_points = extract_data_points(device_specific_data, parameter, device_id)
            
            if device_id.lower() == 'all':
                # If "all" devices, add each device's data as a separate series
                for dev_id, (timestamps, values) in device_data_points.items():
                    if timestamps and values:
                        data_points.append((timestamps, values, parameter, dev_id))
            else:
                # For a specific device, add if data exists
                if device_id in device_data_points:
                    timestamps, values = device_data_points[device_id]
                    if timestamps and values:
                        data_points.append((timestamps, values, parameter, device_id))
        
        if not data_points:
            print("No valid data points found for any parameter.")
            return
            
        print("Plotting data...")
        plot_multi_params(data_points, args.output, not args.no_markers, format=args.format)
    
    elif args.node_parameter:
        # Plot a single parameter
        device_id, parameter = parse_node_parameter(args.node_parameter)
        print(f"Processing device: {device_id}, parameter: {parameter}")
        
        if device_id.lower() == 'all':
            # Plot for all devices separately
            # We don't need to filter the data
            device_data_points = extract_data_points(filtered_data, parameter)
            
            # Convert to format for plotting
            plot_data = {}
            for dev_id, (timestamps, values) in device_data_points.items():
                if timestamps and values:
                    plot_data[dev_id] = (timestamps, values, parameter)
            
            if not plot_data:
                print(f"No data points found for parameter: {parameter}")
                return
                
            print("Plotting data by device...")
            plot_data_by_device(plot_data, args.output, not args.no_markers, format=args.format)
        else:
            # Plot for a specific device
            device_specific_data = filter_data(filtered_data, device_id)
            
            device_data_points = extract_data_points(device_specific_data, parameter, device_id)
            
            if not device_data_points:
                print(f"No data points found for device: {device_id}, parameter: {parameter}")
                return
            
            # For a specific device, we only expect one entry in the dictionary
            if device_id in device_data_points:
                timestamps, values = device_data_points[device_id]
                
                if not timestamps or not values:
                    print(f"No valid data points for device: {device_id}, parameter: {parameter}")
                    return
                
                print("Plotting data...")
                # Use the multi_params plot with a single entry
                plot_multi_params([(timestamps, values, parameter, device_id)], 
                                 args.output, not args.no_markers, format=args.format)
            else:
                print(f"No data points found for device: {device_id}, parameter: {parameter}")
    
    print("Done!")


if __name__ == "__main__":
    main()