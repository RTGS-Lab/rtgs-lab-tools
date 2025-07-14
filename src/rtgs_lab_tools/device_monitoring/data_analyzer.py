# should take parsed dataframes of different packet types
# should implement thresholds depending on the value that is being analyzed
# should return formatted data for notification and visualization


# evaluate formatted data based on Anns parameters
# inputs: dictionary of formatted data
#         - node_id as key
#         - battery_voltage, errors, and system usage as values
# outputs: notification ready data


def analyze_battery_data(data):
    if not data:
        return {"status": "no_data", "message": "No battery data available."}

    if data["voltage"] < 3.6:
        return {
            "status": "flagged",
            "message": f"Battery LOW at {data['voltage']}V on node {data['node_id']} at {data['timestamp']}."
        }
    else:
        return {
            "status": "ok",
            "message": f"Battery is healthy at {data['voltage']}V on node {data['node_id']}."
        }

# prev
def analyze_data(data):
    if not data:
        return {"status": "no_data", "message": "No data available."}

    # Initialize analysis results
    analysis_results = {}

    for node_id, node_data in data.items():
        errors = node_data.get("errors", {})
        battery_voltage = node_data.get("battery_voltage")

        # Analyze battery voltage
        if battery_voltage is not None and battery_voltage < 3.6:
            status = "flagged"
            message = f"Battery LOW at {battery_voltage}V on node {node_id}."
        else:
            status = "ok"
            message = f"Battery is healthy at {battery_voltage}V on node {node_id}."

        # Count errors
        error_count = sum(errors.values())

        # Store analysis result
        analysis_results[node_id] = {
            "status": status,
            "message": message,
            "error_count": error_count
        }

    return analysis_results


