"""Configuration for device monitoring thresholds and settings."""

# Battery voltage threshold (Volts)
BATTERY_VOLTAGE_MIN = 3.6

# System power threshold 0.364W (double the average of 0.182)
SYSTEM_POWER_MAX = 0.364

# Critical errors that trigger alerts
CRITICAL_ERRORS = ["SD_ACCESS_FAIL", "FRAM_ACCESS_FAIL"]

# Email settings
EMAIL_SUBJECT_PREFIX = "Device Monitoring Report"
