"""Configuration for device monitoring thresholds and settings."""

# Battery voltage threshold (Volts)
BATTERY_VOLTAGE_MIN = 3.6

# System power threshold 0.364W (double the average of 0.182)
SYSTEM_POWER_MAX = 0.364

# inbox relative humidity threshold
INBOX_HUMIDITY_MAX = 65

# Critical errors that trigger alerts
CRITICAL_ERRORS = [
    "SD_ACCESS_FAIL",
    "FRAM_ACCESS_FAIL",
    "FIND_FAIL",
    "FRAM_SPACE_CRITICAL",
    "FRAM_SPACE_WARNING",
    "FRAM_OVERRUN",
]

# Timezone handling. GEMS `raw.publish_time` -- the source of every device
# timestamp in the pipeline -- is UTC, so the pipeline computes and stores
# everything in UTC. DISPLAY_TIMEZONE is applied only at the edges, when
# rendering for people (the email, the terminal output, the web app).
DISPLAY_TIMEZONE = "America/Chicago"

# Historic monitoring thresholds
MISSING_NODE_THRESHOLD_HOURS = 24  # Hours since last contact to mark node as missing
DATA_COLLECTION_WINDOW_DAYS = 3  # Days of historical data to analyze
DECOMMISSIONED_NODE_THRESHOLD_DAYS = (
    10  # Days after which missing nodes are ignored (assumed decommissioned)
)

# Display formatting
BATTERY_DECIMAL_PRECISION = 2  # Battery voltage decimal places (.2f)
SYSTEM_POWER_DECIMAL_PRECISION = 3  # System power decimal places (.3f)
UNKNOWN_VALUE_TEXT = "Unknown"  # Text for missing/unknown values
VOLTAGE_UNIT = "V"  # Voltage unit suffix
POWER_UNIT = "W"  # Power unit suffix

# Message formatting
MISSING_NODES_SEPARATOR_LENGTH = 60  # "=" * 60 for missing nodes section
ACTIVE_NODES_SEPARATOR_LENGTH = 40  # "=" * 40 for active nodes section
SECONDS_PER_HOUR = 3600  # For time calculations

# Particle Cloud API
PARTICLE_API_BASE_URL = "https://api.particle.io/v1"
PARTICLE_CONSOLE_BASE_URL = "https://console.particle.io"
HTTP_SUCCESS_CODE = 200

# Timeout for each Particle API call, as (connect, read) seconds. requests has
# no default timeout, so without this a single unresponsive call blocks forever.
# The report makes a few of these per node, so keep it short: a slow lookup
# should degrade to a missing device name, not stall the whole run.
PARTICLE_API_TIMEOUT = (10, 20)

# API endpoints (format strings)
PARTICLE_DEVICE_ENDPOINT = "/devices/{node_id}"
PARTICLE_PRODUCT_ENDPOINT = "/products/{product_id}"

# Message text templates
MISSING_NODES_HEADER = "🚨 MISSING NODES (Not heard from in {hours}+ hours):"
ACTIVE_NODES_HEADER = "✅ ACTIVE NODES (Recent activity):"
SUMMARY_HEADER = "📊 SUMMARY:"

# Email settings
EMAIL_SUBJECT_PREFIX = "Device Monitoring Report"

# Per-step watchdog limits (seconds). None disables the watchdog for a step.
# None of the clients the pipeline uses (the GEMS engine, the Cloud SQL
# connector, smtplib) set a socket timeout of their own, so without these a
# stalled remote leaves the daily run hanging indefinitely instead of failing
# and being retried. Values are generous multiples of a healthy run, which
# takes roughly 80 seconds end to end.
STEP_TIMEOUT_DATA_RETRIEVAL = 900  # GEMS query for the analysis window
STEP_TIMEOUT_DATA_FORMATTING = 900  # local parsing, no network
STEP_TIMEOUT_DATA_ANALYSIS = 300  # local analysis, no network
STEP_TIMEOUT_DATABASE_WRITE = 600  # Cloud SQL connect + commits
STEP_TIMEOUT_MESSAGE_BUILD = 600  # includes Particle API lookups
STEP_TIMEOUT_NOTIFY = 300  # SMTP handshake + send

# Socket timeout for the outgoing SMTP connection (seconds).
SMTP_TIMEOUT = 60

# The Cloud SQL connect timeout lives in web_app/models.py as the
# DEVICEMON_DB_CONNECT_TIMEOUT environment variable, because that module is
# deployed to Cloud Run in an image that cannot import this file.
