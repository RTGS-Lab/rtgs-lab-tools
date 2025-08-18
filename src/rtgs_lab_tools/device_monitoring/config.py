"""Configuration for device monitoring thresholds and settings."""

# Battery voltage threshold (Volts)
BATTERY_VOLTAGE_MIN = 3.6

# System power threshold 0.364W (double the average of 0.182)
SYSTEM_POWER_MAX = 0.364

# Critical errors that trigger alerts
CRITICAL_ERRORS = ["SD_ACCESS_FAIL", "FRAM_ACCESS_FAIL"]

# Historic monitoring thresholds
MISSING_NODE_THRESHOLD_HOURS = 24  # Hours since last contact to mark node as missing
DATA_COLLECTION_WINDOW_DAYS = 10   # Days of historical data to analyze
DECOMMISSIONED_NODE_THRESHOLD_DAYS = 10  # Days after which missing nodes are ignored (assumed decommissioned)

# Email settings
EMAIL_SUBJECT_PREFIX = "Device Monitoring Report"
