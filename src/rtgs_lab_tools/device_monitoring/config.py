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

# Display formatting
BATTERY_DECIMAL_PRECISION = 2          # Battery voltage decimal places (.2f)
SYSTEM_POWER_DECIMAL_PRECISION = 3     # System power decimal places (.3f)
UNKNOWN_VALUE_TEXT = "Unknown"         # Text for missing/unknown values
VOLTAGE_UNIT = "V"                     # Voltage unit suffix
POWER_UNIT = "W"                       # Power unit suffix

# Message formatting  
MISSING_NODES_SEPARATOR_LENGTH = 60    # "=" * 60 for missing nodes section
ACTIVE_NODES_SEPARATOR_LENGTH = 40     # "=" * 40 for active nodes section
SECONDS_PER_HOUR = 3600                # For time calculations

# Particle Cloud API
PARTICLE_API_BASE_URL = "https://api.particle.io/v1"
PARTICLE_CONSOLE_BASE_URL = "https://console.particle.io"
HTTP_SUCCESS_CODE = 200

# API endpoints (format strings)
PARTICLE_DEVICE_ENDPOINT = "/devices/{node_id}"
PARTICLE_PRODUCT_ENDPOINT = "/products/{product_id}"

# Message text templates
MISSING_NODES_HEADER = "🚨 MISSING NODES (Not heard from in {hours}+ hours):"
ACTIVE_NODES_HEADER = "✅ ACTIVE NODES (Recent activity):"
SUMMARY_HEADER = "📊 SUMMARY:"

# Email settings
EMAIL_SUBJECT_PREFIX = "Device Monitoring Report"
