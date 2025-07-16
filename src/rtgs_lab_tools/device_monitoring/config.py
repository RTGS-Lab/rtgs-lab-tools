"""Configuration for device monitoring thresholds and settings."""

# Battery voltage threshold (Volts)
BATTERY_VOLTAGE_MIN = 3.6

# System current threshold (mA)
SYSTEM_CURRENT_MAX = 200

# Critical errors that trigger alerts
CRITICAL_ERRORS = ["SD_ACCESS_FAIL", "FRAM_ACCESS_FAIL"]

# Email settings
EMAIL_SUBJECT_PREFIX = "Device Monitoring Report"
