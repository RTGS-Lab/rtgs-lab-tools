# should take parsed dataframes of different packet types
# should implement thresholds depending on the value that is being analyzed
# should return formatted data for notification and visualization

import pandas as pd
import pprint

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

    # DELETE
    print("\nBattery Data:")
    pprint.pprint(battery_df)
    
    # Get all unique node_ids from all DataFrames
    all_node_ids = set()
    if battery_df is not None and hasattr(battery_df, 'index'):
        all_node_ids.update(battery_df.index)
    if error_df is not None and hasattr(error_df, 'index'):
        all_node_ids.update(error_df.index)
    if system_df is not None and hasattr(system_df, 'index'):
        all_node_ids.update(system_df.index)
    
    # Critical errors to flag
    critical_errors = ['SD_ACCESS_FAIL', 'FRAM_ACCESS_FAIL']
    
    for node_id in all_node_ids:
        flagged = False
        battery_val = None
        system_val = None
        errors_dict = {}
        
        # Get battery voltage
        if battery_df is not None and node_id in battery_df.index:
            battery_val = float(battery_df.loc[node_id, "port_v_0"])
            print(f"Battery voltage for {node_id}: {battery_val}")
            if battery_val < 3.6:
                flagged = True
        
        # Get system usage
        if system_df is not None and node_id in system_df.index:
            system_val = float(system_df.loc[node_id, "port_i_1"])
            print(f"System current for {node_id}: {system_val}")
            if system_val > 200:  # 200mA threshold
                flagged = True
        
        # Get errors
        if error_df is not None and node_id in error_df.index:
            error_row = error_df.loc[node_id]
            # Convert to dict, excluding NaN values
            errors_dict = {col: int(val) for col, val in error_row.items() 
                          if not pd.isna(val) and val > 0}
            print("\nErrors dict:")
            pprint.pprint(errors_dict)
            
            # Check for critical errors
            for critical_error in critical_errors:
                if critical_error in errors_dict and errors_dict[critical_error] > 0:
                    flagged = True
                    break
        
        analyzed_data[node_id] = {
            "flagged": flagged,
            "battery": battery_val,
            "system": system_val,
            "errors": errors_dict
        }
    
    return analyzed_data



