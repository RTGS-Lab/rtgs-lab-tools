#!/usr/bin/env python3
"""
GEMS Data Visualizer - Enhanced version
A command line tool for visualizing data from GEMS sensors.

This tool parses JSON data from CSV files containing GEMS sensor data
and generates time-series visualizations for selected parameters.

Usage:
    python gems_visualizer.py -f <filename> [-p <parameter_path>] [-o <output_file>] 
                             [-d <device_filter>] [-t <type_filter>] 
                             [--explore] [--list] [--multi-param PARAM1 PARAM2...]

Examples:
    # Plot a single parameter
    python gems_visualizer.py -f data.csv -p Diagnostic.Devices.1.GONK.Temperature
    
    # Plot multiple parameters on the same graph
    python gems_visualizer.py -f data.csv --multi-param "Data.Devices.3.Acclima Soil.VWC" "Data.Devices.4.Acclima Soil.VWC"
    
    # Explore the data structure
    python gems_visualizer.py -f data.csv --explore
    
    # List available parameters
    python gems_visualizer.py -f data.csv --list
    
    # Filter by message type and device
    python gems_visualizer.py -f data.csv -p Data.Devices.2.Kestrel.ALS.Clear -t data -d e00fce68f374e425e2d6b891
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
    parser.add_argument('-f', '--file', required=True, help='Input CSV file path')
    parser.add_argument('-p', '--parameter', help='Parameter path (e.g., "Data.Devices.0.Acclima Soil.VWC")')
    parser.add_argument('-o', '--output', help='Output file path for the graph')
    parser.add_argument('-d', '--device', help='Filter by device ID')
    parser.add_argument('-t', '--type', choices=['data', 'diagnostic', 'error', 'metadata'],
                        help='Filter by message type')
    parser.add_argument('-l', '--list', action='store_true', 
                        help='List available parameters instead of plotting')
    parser.add_argument('--explore', action='store_true',
                        help='Explore data structure and show available parameters')
    parser.add_argument('--multi-param', nargs='+',
                        help='Plot multiple parameters on the same graph')
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
    if not (args.parameter or args.list or args.explore or args.multi_param or args.search):
        parser.error("You must specify either a parameter to plot (-p), multiple parameters (--multi-param), "
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
        if device_id:
            # First, check the node_id field in the CSV
            row_device_id = row.get('node_id')
            
            # If not found, extract device ID from the message
            if not row_device_id:
                for key in message_data:
                    if key in ['Data', 'Diagnostic', 'Error', 'Metadata'] and 'Device ID' in message_data[key]:
                        row_device_id = message_data[key]['Device ID']
                        break
            
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
        node_id = row.get('node_id')
        if node_id:
            device_ids.add(node_id)
        
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


def extract_data_points(data: List[Dict], parameter: str) -> Tuple[List[datetime], List[float]]:
    """Extract timestamps and values for a given parameter."""
    timestamps = []
    values = []
    
    for row in data:
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
                timestamps.append(timestamp)
                values.append(value)
            except (ValueError, TypeError):
                # If conversion fails, skip this point
                continue
    
    return timestamps, values


def plot_data(data_points: List[Tuple[List[datetime], List[float], str]], 
              output_file: Optional[str] = None, 
              use_markers: bool = True,
              title: Optional[str] = None,
              format: str = 'png') -> None:
    """Plot multiple time-series data sets and save or display the plot."""
    if not data_points:
        print("No data points to plot.")
        return
    
    # Create the plot
    plt.figure(figsize=(12, 6))
    
    # Plot each data set
    for timestamps, values, parameter in data_points:
        # Filter out None values
        valid_data = [(t, v) for t, v in zip(timestamps, values) if t is not None and v is not None]
        if not valid_data:
            print(f"No valid data points for parameter: {parameter}")
            continue
        
        timestamps_filtered, values_filtered = zip(*valid_data)
        
        # Choose the marker style based on whether markers are enabled
        marker_style = 'o' if use_markers else None
        
        # Create a label from the parameter path
        label = parameter.split('.')[-1] if '.' in parameter else parameter
        
        # Plot the data
        plt.plot(timestamps_filtered, values_filtered, marker=marker_style, markersize=4, label=label)
    
    # Format the x-axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    
    # Add title and labels
    if title:
        plt.title(title)
    else:
        if len(data_points) == 1:
            plt.title(f"Time Series for {data_points[0][2]}")
        else:
            plt.title(f"Time Series for Multiple Parameters")
    
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.grid(True)
    
    # Add legend
    if len(data_points) > 1:
        plt.legend()
    
    # Rotate date labels for better readability
    plt.gcf().autofmt_xdate()
    
    # Tight layout to use space efficiently
    plt.tight_layout()
    
    # If no output file is specified, create a default one
    if not output_file:
        # Generate a filename based on the parameter
        if len(data_points) == 1:
            param_name = data_points[0][2].split('.')[-1].replace(' ', '_')
            output_file = f"plot_{param_name}"
        else:
            output_file = f"multi_parameter_plot_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Add file extension if not present
    if not output_file.lower().endswith(f'.{format}'):
        output_file = f"{output_file}.{format}"
    
    # Save the plot
    plt.savefig("figures/"+output_file, format=format, dpi=300)
    print(f"Plot saved to {output_file}")
    
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
    
    # Apply filters if specified
    if args.device or args.type or time_range:
        print("Applying filters...")
        data = filter_data(data, args.device, args.type, time_range)
    
    if not data:
        print("No data found after applying filters.")
        return
    
    print(f"Loaded {len(data)} rows of data.")
    
    # Explore the data structure
    print("Analyzing data structure...")
    structure, device_ids, message_types = explore_data_structure(data)
    
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
    if args.multi_param:
        # Plot multiple parameters
        print("Extracting multiple parameters...")
        data_points = []
        
        for param in args.multi_param:
            print(f"Processing parameter: {param}")
            timestamps, values = extract_data_points(data, param)
            
            if not timestamps or not values:
                print(f"No data points found for parameter: {param}")
                continue
                
            data_points.append((timestamps, values, param))
        
        if not data_points:
            print("No valid data points found for any parameter.")
            return
            
        print("Plotting data...")
        plot_data(data_points, args.output, not args.no_markers, format=args.format)
    
    elif args.parameter:
        # Plot a single parameter
        print(f"Processing parameter: {args.parameter}")
        timestamps, values = extract_data_points(data, args.parameter)
        
        if not timestamps or not values:
            print(f"No data points found for parameter: {args.parameter}")
            return
            
        print("Plotting data...")
        plot_data([(timestamps, values, args.parameter)], args.output, not args.no_markers, format=args.format)
    
    print("Done!")


if __name__ == "__main__":
    main()