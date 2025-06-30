# should utilize parse_gems_data to parse specific packets that are needed to analyze
# shoudl return df


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

def format_data_with_parser(data_frame):
    # input: data_frame (pandas DataFrame)
    # output: formatted data dictionary

    # get parsed dataframe from parse_gems_data
    parsed_df = parse_gems_data(data_frame, packet_types="all")

    pprint.pprint(parsed_df)

    return None


# if __name__ == "__main__":
