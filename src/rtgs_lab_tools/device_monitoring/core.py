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
from .data_analyzer import analyze_data
from .notification_system import notify
from datetime import datetime, timedelta
import pprint

# node_id = "e00fce68243ac35987c6c910" 

# raw_battery_data = fetch_latest_battery(node_id)


start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
end_date = datetime.now().strftime('%Y-%m-%d')
node_ids = None  # Example node ID
# project = 'Roadside Turf'
# project = "ALL"
project = "Roadside Turf"  # Example project


# Step 1: Get the data
data_frame = get_data(start_date, end_date, project, node_ids)

# Step 2: Format the data
formatted_data = format_data_with_parser(data_frame)
'''
{ "parsed_data": pandas_df,
  "battery_data": pandas_df,
  "error_data": pandas_df,
  "system_current_data": pandas_df,
}
'''
# print("TEST: \n")
# pprint.pprint(formatted_data)

# Step 3: Analyze the data
analysis_dict = analyze_data(formatted_data)
print("\n--Analysis Results--\n")
pprint.pprint(analysis_dict)
print("\n--End of Analysis Results--\n")

# Step 4: Notify the user with the analysis result
print("\n--Notification Results--\n")
notify(analysis_dict)