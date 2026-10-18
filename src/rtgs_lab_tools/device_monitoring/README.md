# Device Monitoring Module

Monitor IoT device status, connectivity, and health metrics for Particle Cloud devices across multiple projects.

## CLI Usage

### Basic Monitoring

```bash
# Monitor all devices across all projects
rtgs device-monitoring monitor

# Monitor specific project
rtgs device-monitoring monitor --project LCCMR
```

### Command Options

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `--project` | String | Project name to monitor (or "ALL" for all projects) | ALL |
| `--start_date` | String | Start date in YYYY-MM-DD format | 10 days ago |
| `--end_date` | String | End date in YYYY-MM-DD format | Today |
| `--node_ids` | String | Comma-separated list of specific node IDs to monitor | All nodes |
| `--no-email` | Flag | Skip sending email notifications | False |

## Scheduled Monitoring on MSI Infrastructure

### SLURM scrontab Setup

The device monitoring system runs automatically on MSI (Minnesota Supercomputing Institute) infrastructure using SLURM's `scrontab` scheduler.

#### Cron Schedule Configuration

```bash
# Edit your scrontab on MSI
scrontab -e

# Add this line to run monitoring daily at 4:27 AM
# The line lives in scrontab.msi (versioned); install it with
scrontab /projects/standard/runck014/shared/device_monitoring/rtgs-lab-tools-cron/rtgs-lab-tools/src/rtgs_lab_tools/device_monitoring/scrontab.msi
```

#### Script Location and Setup

The monitoring script runs from the lab's shared workspace on Bryan's scrontab:
```
/projects/standard/runck014/shared/device_monitoring/scripts/scheduled_device_monitoring.sh
```
Paths are overridable from the scrontab environment (never from the credentials file):
DEVICEMON_BASE_DIR, DEVICEMON_WORK_DIR, DEVICEMON_LOG_DIR, DEVICEMON_CREDS_FILE,
DEVICEMON_RELEASE_FILE, DEVICEMON_SA_KEY, DEVICEMON_TOKEN_SECRET, DEVICEMON_PYTHON_MODULE
(default `python3/3.12.4_anaconda2024.06-1_libmamba`), DEVICEMON_PYTHON (absolute path),
DEVICEMON_EMAIL (`1` sends the notification email after each run; off by default).

Ownership (the script refuses to run if the code side is group- or world-writable):
```
scripts/, rtgs-lab-tools-cron/ (checkout + venv)   Bryan, 2750 dirs, 640/750 files
logs/, logs/batches/                               Bryan, group runck014, 2770 (the one
                                                   group-writable place)
credentials/.rtgs_credentials                      660, group runck014 -- data, never sourced
~/.config/devmon/ (700): sa.json (600), release (600)    Bryan's home, not shared
```

Each run:
- loads MSI modules (Python, Git) and picks a Python >= 3.10 by absolute path; an older one
  (agate's `/usr/bin/python3` is 3.6.8) stops the run with a message, before any install
- builds `venv/` lean on first run and once per release: `pip install -r
  device_monitoring/requirements-cron.txt` then `pip install --no-deps -e .` -- never
  `install.sh` or the package's full base dependencies (minutes, not 25+)
- parses the credentials file against an allowlist (no `source`)
- checks out the release pinned in `~/.config/devmon/release` (`<tag> <commit sha>`; both
  checked; git runs with hooks disabled; an existing tag is never force-moved)
- fetches the ingest token from Secret Manager with `~/.config/devmon/sa.json`
  (`check-ingest` preflight), runs the monitor, publishes the batch -- all through
  `venv/bin/python -m rtgs_lab_tools.device_monitoring.cli`, not the `rtgs` router
- logs to `logs/device_monitoring_<stamp>_<random>.log`; the lock is in `~/.cache/devmon/`

### MSI Credentials Configuration

#### Shared credentials file (data only)

`credentials/.rtgs_credentials` holds KEY=VALUE lines (an `export ` prefix and one pair of
outer quotes are accepted; `$(...)` and `$VAR` are taken literally). Accepted names:
DEVICEMON_INGEST_URL, PARTICLE_ACCESS_TOKEN, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
LOGGING_DB_HOST, LOGGING_DB_PORT, LOGGING_DB_NAME, LOGGING_DB_USER, LOGGING_DB_PASSWORD,
POSTGRES_LOGGING_STATUS, GMAIL_USER, GMAIL_APP_PASSWORD, GMAIL_RECIPIENT. Everything else is
ignored and named in the log -- in particular DEVICEMON_INGEST_TOKEN (now from Secret
Manager), DEVICEMON_RELEASE, *_DIR, *_FILE, PATH, LD_*, PYTHON*, GOOGLE_*.

```bash
# GEMS Database Configuration
DB_HOST=sensing-0.msi.umn.edu
DB_PORT=5433
DB_NAME=gems
DB_USER=your_username
DB_PASSWORD=your_password

# Publish target: device-monitoring-ingest-prod (or -test). The token is NOT here.
DEVICEMON_INGEST_URL=https://device-monitoring-ingest-prod-685278787484.us-central1.run.app

# Particle Cloud API
PARTICLE_ACCESS_TOKEN=your_particle_token

# Email Notifications (optional)
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD="your_gmail_app_password"
GMAIL_RECIPIENT=notification_recipient@umn.edu
```

Check what a run would accept (names and value lengths only, never values):
```bash
scripts/scheduled_device_monitoring.sh --check-creds credentials/.rtgs_credentials
```

#### Ingest token (Secret Manager)

The token is read each run from `devicemon-ingest-token` (prod URL) or
`devicemon-ingest-token-test` (test URL) in project rtgslab, as the service account
`device-monitoring-msi@rtgslab.iam.gserviceaccount.com`, whose only grant is
secretAccessor on those two secrets. Its key is `~/.config/devmon/sa.json`, owned by the
running user, mode 600 -- anything else is refused. The token is sent only to the known
ingest hosts and is never logged or written to disk.

#### Release pin

`~/.config/devmon/release`, one line: `devmon-v0.1.0 <40-hex commit sha of that tag>`.
Changing this line is the deploy.

### Log File Management

Logs: `logs/device_monitoring_YYYYMMDD_HHMMSS_<random>.log`; batches:
`logs/batches/<run>Z-<batch id>.json` (contain no credentials).

#### Manual Execution

```bash
/projects/standard/runck014/shared/device_monitoring/scripts/scheduled_device_monitoring.sh
# or with parameters
.../scripts/scheduled_device_monitoring.sh 2024-01-01 2024-01-31 "e00fce68c7f2c2b634bb4b7d" LCCMR
```

## Python API Usage

### Basic Monitoring

```python
from rtgs_lab_tools.device_monitoring.core import monitor
from datetime import datetime, timedelta

# Monitor all devices for the last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

monitor(
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d")
)

# Monitor specific project
monitor(
    start_date="2024-01-01",
    end_date="2024-01-31",
    project="LCCMR"
)

# Monitor specific devices
monitor(
    start_date="2024-01-01",
    end_date="2024-01-31",
    node_ids="e00fce68c7f2c2b634bb4b7d,e00fce68aa3c0a3b7b4b4b5d"
)
```

### Advanced Monitoring with Email Notifications

```python
from rtgs_lab_tools.device_monitoring.core import monitor

# Monitor with email notifications enabled (default)
monitor(
    start_date="2024-01-01",
    end_date="2024-01-31",
    project="LCCMR",
    no_email=False  # Send email notifications
)

# Monitor without email notifications
monitor(
    start_date="2024-01-01",
    end_date="2024-01-31",
    project="LCCMR",
    no_email=True  # Skip email notifications
)
```

### Using Individual Components

```python
from rtgs_lab_tools.device_monitoring.data_getter import get_data
from rtgs_lab_tools.device_monitoring.data_formatter import format_data_with_parser
from rtgs_lab_tools.device_monitoring.data_analyzer import analyze_data
from rtgs_lab_tools.device_monitoring.notification_system import notify

# Step 1: Get raw data
raw_data = get_data(
    start_date="2024-01-01",
    end_date="2024-01-31",
    node_ids="e00fce68c7f2c2b634bb4b7d",
    project="LCCMR"
)

# Step 2: Format the data
formatted_data = format_data_with_parser(raw_data)

# Step 3: Analyze the data
analysis_results = analyze_data(formatted_data)

# Step 4: Send notifications
notify(analysis_results, no_email=False)
```

### Batch Monitoring Multiple Projects

```python
from rtgs_lab_tools.device_monitoring.core import monitor

# Monitor multiple projects
projects = ["LCCMR", "GEMS", "WATERSHED"]

for project in projects:
    print(f"Monitoring project: {project}")
    monitor(
        start_date="2024-01-01",
        end_date="2024-01-31",
        project=project,
        no_email=True  # Skip individual emails, send summary later
    )
    print(f"Completed monitoring for {project}")
```

## Core Features

### Device Status Monitoring
- **Connectivity checks**: Verify devices are online and responding
- **Last communication tracking**: Monitor when devices last reported data
- **Health metrics**: Battery levels, signal strength, and system vitals
- **Project-based organization**: Monitor devices grouped by research projects

### Data Collection Monitoring
- **Data freshness checks**: Verify recent data collection
- **Missing data detection**: Identify gaps in sensor readings
- **Data quality metrics**: Assess completeness and consistency
- **Historical trend analysis**: Compare current vs. historical performance

### Alert and Notification System
- **Threshold-based alerts**: Configurable warning and critical thresholds
- **Email notifications**: Automated alerts for device issues
- **Status reporting**: Daily/weekly summary reports
- **Escalation procedures**: Multi-level alert system

### Multi-Project Support
- **Cross-project monitoring**: Monitor devices across multiple research projects
- **Project-specific configurations**: Custom monitoring rules per project
- **Unified reporting**: Combined views across all projects
- **Permission-based access**: Project-specific access controls

### Network Requirements

- **MSI Infrastructure**: Direct database access (no VPN required)
- **External Networks**: UMN VPN connection required for database access
- **Internet Access**: Required for Particle Cloud API communication
- **Google Cloud access**: Outbound HTTPS access to Google APIs is required to write results to the device monitoring Postgres database (Cloud SQL) via the Cloud SQL connector. The web dashboard that reads this data runs separately on Cloud Run and cannot reach the GEMS database directly (it's not on the UMN/MSI network) — that's why this script, not a cloud job, is what writes to Postgres.

## Known Bugs

- **--node-ids flag**: Currently not working - all nodes are monitored regardless of this parameter
- **Missing node error**: Node is marked as missing in report but it is sending data to grafana. Maybe if it sends data packets but no diagnostic packets it gets marked as missing? (reference report on 08/18/2025 node: PepsiCo_001)

## Planned Future Improvements

### High Priority (Ann's Requests)
- **Dynamic thresholds and error configuration**: Allow Ann to add/remove critical error codes and modify battery, system usage, and humidity thresholds
- **Include humidity in reports**: Add humidity data to monitoring output
- **V2 device support**: Implement logic for handling non-v3 devices, with V2 devices as priority

### Medium Priority
- **HTML email notifications**: Implement unused HTML methods to send static HTML emails with readable "node cards" for better data display
- **Fix node-ids flag**: Resolve the issue with node ID filtering
- **Online portal for Ann**: Create web interface for checking device status (pending approval from B, prototyping okay)

### Low Priority
- **Rename formatter to preprocessing**: More accurate naming for the data processing phase
- **React app migration**: Migrate to React app with components library for better Claude integration

For more information on other modules, see:
- [Sensing Data Module](../sensing_data/README.md) - Data extraction and management
- [Visualization Module](../visualization/README.md) - Data plotting and visualization
- [Device Configuration Module](../device_configuration/README.md) - Device settings management