# implementation of the core functionality of device monitoring
# should organize all the functions from within data_getter, date_formatter, data_analyzer, notification system
# data_getter->data_fromatter->data_analyzer->notification_system
# should create the function that the cli.py wraps
# To run: python -m rtgs_lab_tools.device_monitoring.core


# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from data_getter import fetch_latest_battery
# from data_formater import format_battery_data, format_data
from .data_getter import get_data
from .data_formatter import format_data_with_parser
from .data_analyzer import analyze_battery_data, analyze_data
from .notification_system import notify
from datetime import datetime, timedelta

# node_id = "e00fce68243ac35987c6c910" 

# raw_battery_data = fetch_latest_battery(node_id)


start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
end_date = datetime.now().strftime('%Y-%m-%d')
node_ids = None  # Example node ID
# project = 'Roadside Turf'
project = "ALL"


# Step 1: Get the data
data_frame = get_data(start_date, end_date, project, node_ids)
# if data_path:
#     print(f"Data file created: {data_path}")
# else:
#     print("No data was retrieved.")


# Step 2: Format the data
# formatted_battery_data = format_battery_data(raw_battery_data)
formatted_data = format_data_with_parser(data_frame)

# Print the formatted data for debugging
# for node, data in formatted_data.items():
#     print(f"Node: {node}")
#     print(f"  Battery Voltage: {data['battery_voltage']}")
#     for error, count in sorted(data['errors'].items(), key=lambda x: x[1], reverse=True):
#         print(f"    Error: {error}, Count: {count}")
#     print("\n")


# Step 3: Analyze the data
# analysis_result = analyze_battery_data(formatted_battery_data)
analysis_result = analyze_data(formatted_data)


# Step 4: Notify the user with the analysis result
print("\n--Notification Results--\n")
notify(analysis_result)