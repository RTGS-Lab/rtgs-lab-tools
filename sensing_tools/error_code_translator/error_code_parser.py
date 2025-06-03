#!/usr/bin/env python3
"""
GEMS Error Parser - A tool to parse error logs from data collectors
and map error codes to their human-readable names and descriptions.

Usage:
    python error_parser.py <input_file.csv>

The tool can handle either pure JSON files or CSV files where one column contains JSON data.
"""

import json
import sys
import re
import os
import csv
from typing import Dict, List, Any, Optional, Union
from collections import Counter
import matplotlib.pyplot as plt
from datetime import datetime

# Define main error code classes
ERROR_CLASSES = {
    "0": "Unknown",
    "1": "I2C",
    "2": "Power",
    "3": "IO",
    "4": "Memory",
    "5": "Timing",
    "6": "Coms",
    "7": "Disagree",
    "8": "Internal",
    "9": "Math/Logical",
    "A": "Sensor",
    "E": "System",
    "F": "Warning"
}

# Define hardware devices
HARDWARE_DEVICES = {
    "0": "System Wide",
    "1": "Port 1 Talon",
    "2": "Port 2 Talon",
    "3": "Port 3 Talon",
    "4": "Port 4 Talon",
    "E": "Gonk",
    "F": "Kestrel"
}

# Define hardware sub-devices
HARDWARE_SUB_DEVICES = {
    "0": "System Wide",
    "1": "Bus Routing",
    "2": "Power",
    "3": "Talon",
    "4": "SD",
    "5": "RTC",
    "6": "Cell",
    "7": "Sensors",
    "8": "GPS",
    "9": "FRAM",
    "A": "Actuation",
    "B": "Processor"
}

class ErrorCode:
    """Class to represent and decode an error code"""
    
    def __init__(self, hex_code: str, error_db: Dict[str, Dict[str, str]]):
        """Initialize with hex code and error database"""
        self.hex_code = hex_code.lower()
        self.error_db = error_db
        self.error_info = self._find_in_db()
    
    def _find_in_db(self) -> Dict[str, str]:
        """Find error in database, matching by base code"""
        # Try exact match first
        if self.hex_code in self.error_db:
            return self.error_db[self.hex_code]
        
        # Try matching first 6 characters (0xCccc)
        base_code = self.hex_code[:6]
        for code, info in self.error_db.items():
            if code.startswith(base_code):
                return info
        
        # Create default error info if not found
        return {
            "specific_name": "UNKNOWN_ERROR",
            "description": "Error code not found in database",
            "base_error_code_hex": self.hex_code,
            "code_name": "Unknown Error",
            "class": self._get_class(),
            "code": self._get_code_number(),
            "subtype": "Unknown",
            "hardware_device": self._get_hardware_device(),
            "hardware_subdevice": self._get_hardware_subdevice()
        }
    
    def _get_class(self) -> str:
        """Get the class from the error code"""
        if len(self.hex_code) >= 3:
            class_id = self.hex_code[2]
            return ERROR_CLASSES.get(class_id.upper(), "Unknown")
        return "Unknown"
    
    def _get_code_number(self) -> str:
        """Get the code number from the error code"""
        if len(self.hex_code) >= 6:
            return self.hex_code[3:6]
        return "000"
    
    def _get_hardware_device(self) -> str:
        """Get hardware device from the error code"""
        if len(self.hex_code) >= 8:
            device_id = self.hex_code[7]
            return HARDWARE_DEVICES.get(device_id.upper(), "Unknown Device")
        return "Unknown Device"
    
    def _get_hardware_subdevice(self) -> str:
        """Determine the hardware sub-device from the error code"""
        if len(self.hex_code) >= 7:
            subdevice_id = self.hex_code[6]
            return HARDWARE_SUB_DEVICES.get(subdevice_id.upper(), "Unknown Sub-device")
        return "Unknown Sub-device"
    
    def get_error_string(self) -> str:
        """Generate a human-readable error string"""
        if not self.error_info:
            return f"Unknown error: {self.hex_code}"
        
        # Format with all available information
        parts = [
            f"Error: {self.error_info.get('specific_name', 'UNKNOWN')} ({self.hex_code})",
            f"Class: {self.error_info.get('class', 'Unknown')}",
            f"Description: {self.error_info.get('description', 'No description available')}"
        ]
        
        # Add hardware information if available
        hw_device = self.error_info.get('hardware_device', '')
        hw_subdevice = self.error_info.get('hardware_subdevice', '')
        
        if hw_device and hw_device != "System Wide":
            parts.append(f"Device: {hw_device}")
        
        if hw_subdevice and hw_subdevice != "System Wide":
            parts.append(f"Sub-device: {hw_subdevice}")
        
        return " | ".join(parts)


def load_error_database(md_file: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """
    Load error code database from the markdown file or fetch from GitHub if not provided.
    Returns a dictionary mapping error codes to their information.
    """
    markdown_content = ""
    
    # If md_file is provided and exists, load it
    if md_file and os.path.exists(md_file):
        with open(md_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    else:
        # Try to use local ERRORCODES.md file if it exists
        if os.path.exists('ERRORCODES.md'):
            with open('ERRORCODES.md', 'r', encoding='utf-8') as f:
                markdown_content = f.read()
        else:
            try:
                print("Fetching error codes from GitHub...")
                import requests
                url = "https://raw.githubusercontent.com/gemsiot/Firmware_-_FlightControl-Demo/refs/heads/master/ERRORCODES.md"
                response = requests.get(url, allow_redirects=False, timeout=10)
                if response.status_code == 200:
                    markdown_content = response.text
                    print("Got ERRORCODES.md from Github.")
                    # Save for future use
                    with open('ERRORCODES.md', 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                else:
                    print(f"Failed to fetch error codes: HTTP {response.status_code}")
                    return create_embedded_error_db()
            except Exception as e:
                print(f"Error fetching error codes: {e}")
                return create_embedded_error_db()
    
    # Parse the markdown table to extract error codes
    error_db = {}
    
    # Find the table section
    table_match = re.search(r'\| \*\*Base Error Code Hex\*\* \|.*?\n\|[-:|\s]+\|(.*?)(?:\n\n|$)', 
                            markdown_content, re.DOTALL)
    
    if not table_match:
        print("Error: Could not find error code table in the markdown file.")
        return create_embedded_error_db()
    
    table_content = table_match.group(1)
    
    # Process each row of the table
    for line in table_content.strip().split('\n'):
        if not line.startswith('|'):
            continue
        
        # Split the line into columns and remove leading/trailing whitespace
        columns = [col.strip() for col in line.split('|')[1:-1]]
        
        if len(columns) < 12:
            continue  # Skip malformed rows
        
        # Extract relevant information
        error_info = {
            "base_error_code_hex": columns[0].lower(),
            "specific_name": columns[1],
            "description": columns[2],
            "base_error_code_value": columns[3],
            "error_code_structure": columns[4],
            "class": columns[5],
            "code": columns[6],
            "subtype": columns[7],
            "hardware_device": columns[8],
            "hardware_subdevice": columns[9],
            "code_name": columns[10],
            "code_location": columns[11]
        }
        
        # Use the hex code as the key
        error_db[error_info["base_error_code_hex"]] = error_info
    
    return error_db


def create_embedded_error_db() -> Dict[str, Dict[str, str]]:
    """Create a built-in error database with common error codes"""
    error_db = {}
    
    # Define common error codes directly in the code
    error_codes_data = [
        # Format: [hex_code, name, description, class, code, subtype, hw_device, hw_subdevice]
        ["0x80070000", "ADC_TIMEOUT", "New reading not returned in time", "Internal", "7", "0", "Talon", "System Wide"],
        ["0x80070030", "ADC_TIMEOUT", "New reading not returned in time", "Internal", "7", "0", "Talon", "Port 3"],
        ["0x500400f6", "CLOCK_UNAVAILABLE", "Cell time unavailable", "Timing", "4", "0", "Kestrel", "Cell"],
        ["0xf00500f9", "FRAM_OVERRUN", "FRAM location beyond what is allocated", "Warning", "5", "0", "Kestrel", "FRAM"],
        ["0x400200f4", "SD_ACCESS_FAIL", "Failure to read/write from SD card", "Memory", "2", "Read/Write", "Kestrel", "SD"],
        ["0xe00200fa", "WDT_OFF_LEASH", "WDT has not been fed, expect a reset", "System", "2", "0", "Kestrel", "Actuation"],
        ["0xf00c00f8", "GPS_UNAVAILABLE", "No GPS lock available, even after wait period", "Warning", "12", "0", "Kestrel", "GPS"],
        ["0x20010000", "SENSOR_POWER_FAIL", "Failure of sensor port on Talon", "Power", "1", "0", "Talon", "Port"],
        ["0x20030000", "BUS_OUTOFRANGE", "General bus out of spec failure", "Power", "3", "0", "Talon", "Port"],
        ["0x60010000", "SDI12_COM_FAIL", "Communication failure with SDI-12 device", "Coms", "1", "Fail Type", "Talon", "Port"],
        ["0x70020000", "BUS_DISAGREE", "Input and output bus readings out of spec", "Disagree", "2", "0", "Talon", "Port"],
        ["0x70030000", "TIME_DISAGREE", "At least one time source disagrees with others", "Disagree", "3", "0", "System Wide", "System Wide"],
        ["0x500600f5", "ALARM_FAIL", "RTC failed to trigger wakeup alarm", "Timing", "6", "0", "Kestrel", "RTC"],
        ["0xff000000", "FIND_FAIL", "Failed to locate sensor", "Warning", "3840", "0", "System Wide", "System Wide"]
    ]
    
    for code_data in error_codes_data:
        error_db[code_data[0]] = {
            "base_error_code_hex": code_data[0],
            "specific_name": code_data[1],
            "description": code_data[2],
            "class": code_data[3],
            "code": code_data[4],
            "subtype": code_data[5],
            "hardware_device": code_data[6],
            "hardware_subdevice": code_data[7]
        }
    
    print(f"Using embedded error database with {len(error_db)} common codes")
    return error_db


def parse_error_file(file_path: str, error_db: Dict[str, Dict[str, str]], 
                   generate_graph: bool = False, node_filter: List[str] = None) -> None:
    """Parse error file (CSV or JSON) and print human-readable error information"""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    print(f"Processing {file_path}...")
    
    # Initialize error counters
    error_counters = {}
    
    if file_ext == '.json':
        error_counters = parse_json_file(file_path, error_db, node_filter)
    elif file_ext == '.csv':
        error_counters = parse_csv_file(file_path, error_db, node_filter)
    else:
        # Try to auto-detect the format
        with open(file_path, 'r') as f:
            first_line = f.readline().strip()
        
        if first_line.startswith('{'):
            # Looks like JSON
            error_counters = parse_json_file(file_path, error_db, node_filter)
        elif ',' in first_line:
            # Looks like CSV
            error_counters = parse_csv_file(file_path, error_db, node_filter)
        else:
            print(f"Unable to determine file format for {file_path}. Please specify a .json or .csv file.")
            return
    
    # Print error summary
    if not error_counters or not error_counters.get("all"):
        print("No errors found in the file.")
        return
    
    # If filtering by nodes, print summary for each node
    if node_filter:
        for node_id in error_counters:
            if node_id == "all":
                continue
            
            if not error_counters[node_id]:
                print(f"\nNode {node_id}: No errors found")
                continue
                
            print(f"\n=== ERROR SUMMARY FOR NODE {node_id} ===")
            print(f"Found {sum(error_counters[node_id].values())} errors of {len(error_counters[node_id])} distinct types:")
            
            # Get the most common errors for this node
            most_common = error_counters[node_id].most_common()
            
            # Print each error with count and description
            for code, count in most_common:
                print_error_details(code, count, error_db)
        
    # Always print overall summary
    print("\n=== OVERALL ERROR SUMMARY ===")
    print(f"Found {sum(error_counters['all'].values())} errors of {len(error_counters['all'])} distinct types:")
    
    # Get the most common errors
    most_common = error_counters["all"].most_common()
    
    # Print each error with count and description
    for code, count in most_common:
        print_error_details(code, count, error_db)
    
    # Generate error frequency graph if errors were found and graph generation is requested
    if generate_graph:
        # Generate overall graph
        generate_error_graph(error_counters["all"], error_db, "all")
        
        # If filtering by nodes, generate graph for each node
        if node_filter:
            for node_id in error_counters:
                if node_id != "all" and error_counters[node_id]:
                    generate_error_graph(error_counters[node_id], error_db, node_id)


def parse_json_file(file_path: str, error_db: Dict[str, Dict[str, str]], node_filter: List[str] = None) -> Dict[str, Counter]:
    """Parse a JSON file containing error records"""
    # Initialize error counter for each device
    error_counters = {"all": Counter()}  # "all" will track all errors regardless of device
    
    # Flag to indicate if we're tracking all nodes separately
    track_all_nodes = node_filter and "all" in node_filter
    
    try:
        # First pass to identify all unique node IDs if needed
        if track_all_nodes:
            unique_nodes = set()
            with open(file_path, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    try:
                        data = json.loads(line.strip())
                        if "Error" in data and "Device ID" in data["Error"]:
                            node_id = data["Error"]["Device ID"]
                            if node_id:
                                unique_nodes.add(node_id)
                    except:
                        pass
            
            # Initialize counters for all nodes
            for node_id in unique_nodes:
                error_counters[node_id] = Counter()
        
        # Process file for errors
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            try:
                # Try to parse the JSON
                data = json.loads(line.strip())
                
                # Get the node ID if present
                node_id = data.get("Error", {}).get("Device ID", "unknown") if "Error" in data else "unknown"
                
                # If node filter is active and not tracking all nodes and this node is not in the filter, skip it
                if node_filter and not track_all_nodes and node_id not in node_filter:
                    continue
                
                # Initialize counter for this node if needed
                if node_id not in error_counters and (track_all_nodes or (node_filter and node_id in node_filter)):
                    error_counters[node_id] = Counter()
                
                # Count errors for all devices
                process_error_data(data, error_counters["all"])
                
                # If tracking this node specifically, count its errors
                if node_id in error_counters:
                    process_error_data(data, error_counters[node_id])
            
            except json.JSONDecodeError:
                pass
            except Exception:
                pass
                
    except Exception as e:
        print(f"Error opening or reading file: {str(e)}")
    
    return error_counters


def parse_csv_file(file_path: str, error_db: Dict[str, Dict[str, str]], node_filter: List[str] = None) -> Dict[str, Counter]:
    """Parse a CSV file where one of the columns contains JSON error data"""
    # Initialize error counter for each device
    error_counters = {"all": Counter()}  # "all" will track all errors regardless of device
    
    # Flag to indicate if we're tracking all nodes separately
    track_all_nodes = node_filter and "all" in node_filter
    
    try:
        # First pass to identify all unique node IDs if needed
        if track_all_nodes:
            unique_nodes = set()
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) > 1:  # Node ID is in column 1
                        node_id = row[1].strip()
                        if node_id:
                            unique_nodes.add(node_id)
            
            # Initialize counters for all nodes
            for node_id in unique_nodes:
                error_counters[node_id] = Counter()
        
        # Process file for errors
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            
            # Hardcode JSON column to index 5
            json_column_index = 5
            # Node ID is in column 1
            node_id_index = 1
            
            # Skip header row
            next(reader, None)
            
            # Process each row
            for row_num, row in enumerate(reader, 2):  # Start at 2 to account for header
                if len(row) <= json_column_index:
                    continue
                
                # Get the node ID
                node_id = row[node_id_index].strip() if len(row) > node_id_index else "unknown"
                
                # If node filter is active and not tracking all nodes and this node is not in the filter, skip it
                if node_filter and not track_all_nodes and node_id not in node_filter:
                    continue
                
                # Initialize counter for this node if needed
                if node_id not in error_counters and (track_all_nodes or (node_filter and node_id in node_filter)):
                    error_counters[node_id] = Counter()
                
                json_cell = row[json_column_index]
                
                try:
                    # Clean the JSON string - handle escaped quotes
                    json_str = json_cell.strip()
                    
                    # If the JSON is wrapped in quotes, remove them
                    if json_str.startswith('"') and json_str.endswith('"'):
                        json_str = json_str[1:-1]
                    
                    # Replace escaped quotes with regular quotes
                    json_str = json_str.replace('\\"', '"').replace('""', '"')
                    
                    # Parse the JSON
                    data = json.loads(json_str)
                    
                    # Count errors for all devices
                    process_error_data(data, error_counters["all"], verbose=False)
                    
                    # If tracking this node specifically, count its errors
                    if node_id in error_counters:
                        process_error_data(data, error_counters[node_id], verbose=False)
                    
                except json.JSONDecodeError:
                    pass
                except Exception:
                    pass
                    
    except Exception as e:
        print(f"Error opening or reading CSV file: {str(e)}")
    
    return error_counters


def process_error_data(data: Dict[str, Any], error_counter: Counter, verbose: bool = True) -> None:
    """Process the error data from either JSON or CSV sources"""
    # Check if this is an error record
    if "Error" in data and "Devices" in data["Error"]:
        devices = data["Error"]["Devices"]
        
        # Process each device in the error record
        for device_entry in devices:
            for device_name, device_info in device_entry.items():
                # Process each error code for this device
                if "CODES" in device_info and isinstance(device_info["CODES"], list):
                    for code in device_info["CODES"]:
                        # Increment error counter
                        error_counter[code.lower()] += 1


def print_error_details(code: str, count: int, error_db: Dict[str, Dict[str, str]]) -> None:
    """Print details about an error code"""
    error = ErrorCode(code, error_db)
    
    # Get name from database or generate one from error components
    if error.error_info.get('specific_name', '') != 'UNKNOWN_ERROR':
        # Use the name from the database
        error_name = error.error_info.get('specific_name', '')
        error_desc = error.error_info.get('description', 'No description available')
    else:
        # Create a descriptive name from error components
        error_class = error.error_info.get('class', 'Unknown')
        hw_device = error.error_info.get('hardware_device', 'Unknown')
        hw_subdevice = error.error_info.get('hardware_subdevice', 'Unknown')
        
        if hw_device != "System Wide" and hw_subdevice != "System Wide":
            error_name = f"{error_class} Error - {hw_device} {hw_subdevice}"
        elif hw_device != "System Wide":
            error_name = f"{error_class} Error - {hw_device}"
        else:
            error_name = f"{error_class} Error"
            
        error_desc = "Unknown error code not found in database"
    
    print(f"{code} ({count}): {error_name} - {error_desc}")


def generate_error_graph(error_counter: Counter, error_db: Dict[str, Dict[str, str]], node_id: str = "all") -> None:
    """Generate a bar graph of error frequencies"""
    if not error_counter:
        print("No errors found to graph.")
        return
    
    # Create figures directory if it doesn't exist
    os.makedirs('figures', exist_ok=True)
    
    # Get the most common errors (all of them)
    most_common = error_counter.most_common()
    
    # If there are too many errors, limit to top 15 for readability
    if len(most_common) > 15:
        most_common = most_common[:15]
        print(f"Note: Limiting graph to top 15 most frequent errors for readability.")
    
    # Prepare data for plotting
    codes = []
    counts = []
    
    for code, count in most_common:
        codes.append(code)
        counts.append(count)
    
    # Create the plot with a larger figure size for readability
    plt.figure(figsize=(16, 10))
    
    # Add spacing between bars (adjust width)
    bar_width = 0.7
    bars = plt.bar(range(len(codes)), counts, color='royalblue', width=bar_width)
    
    # Configure plot
    graph_title = 'Error Code Frequency'
    if node_id != "all":
        graph_title += f' for Node {node_id}'
    
    plt.title(graph_title, fontsize=18)
    plt.xlabel('Error Codes', fontsize=14)
    plt.ylabel('Frequency', fontsize=14)
    
    # Increase font size and spacing for x-axis labels
    plt.xticks(range(len(codes)), codes, rotation=45, ha='right', fontsize=12)
    plt.yticks(fontsize=12)
    
    # Add count labels on top of bars with larger font
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                 f'{int(height)}', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Add more padding
    plt.subplots_adjust(bottom=0.15, left=0.1, right=0.95, top=0.9)
    
    # Add grid lines for better readability
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Save the figure with higher resolution
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"figures/error_frequency_{node_id}_{timestamp}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\nError frequency graph saved to {filename}")
    
    # Close the plot to free memory
    plt.close()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input_file.csv|json> [error_codes.md] [--graph] [--nodes=node1,node2,...]")
        print("  --graph: Optional flag to generate error frequency graph")
        print("  --nodes: Optional comma-separated list of node IDs to filter by")
        return 1
    
    input_file = sys.argv[1]
    
    # Check for --graph flag anywhere in arguments
    generate_graph = "--graph" in sys.argv
    
    # Check for --nodes flag
    node_filter = []
    for arg in sys.argv:
        if arg.startswith("--nodes="):
            node_ids = arg.split("=")[1].split(",")
            node_filter = [node_id.strip() for node_id in node_ids]
            break
    
    # Handle optional error_codes.md file (if it's not the --graph flag or --nodes)
    md_file = None
    for arg in sys.argv[2:]:
        if not arg.startswith("--") and os.path.exists(arg):
            md_file = arg
            break
    
    # Load error database
    error_db = load_error_database(md_file)
    if not error_db:
        print("Failed to load error database. Cannot continue.")
        return 1
    
    # Parse and display errors
    parse_error_file(input_file, error_db, generate_graph, node_filter)
    return 0


if __name__ == "__main__":
    sys.exit(main())