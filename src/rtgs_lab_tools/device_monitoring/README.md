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
27 4 * * 1-5 /home/$USER/code/scripts/scheduled_device_monitoring.sh
```

#### Script Location and Setup

The monitoring script is located at:
```
/home/$USER/code/scripts/scheduled_device_monitoring.sh
```

This script automatically:
- Loads required MSI modules (Python, Git)
- Clones/updates the rtgs-lab-tools repository
- Sets up the virtual environment
- Loads credentials from the MSI home directory
- Runs the device monitoring
- Logs all activities to `~/logs/device-monitoring-logs/`

### MSI Credentials Configuration

#### Credentials File Setup

Create a secure credentials file in your MSI home directory:

```bash
# Create credentials file with restricted permissions
touch ~/.rtgs_creds
chmod 600 ~/.rtgs_creds
```

#### Required Credentials

Edit `~/.rtgs_creds` with your actual credentials:

```bash
# GEMS Database Configuration
export DB_HOST=sensing-0.msi.umn.edu
export DB_PORT=5433
export DB_NAME=gems
export DB_USER=your_username
export DB_PASSWORD=your_password

# Logging Database (optional)
export LOGGING_DB_HOST=34.170.80.6
export LOGGING_DB_PORT=5432
export LOGGING_DB_NAME=logs
export LOGGING_DB_USER=your_logging_username
export LOGGING_DB_PASSWORD=your_logging_password

# Particle Cloud API
export PARTICLE_ACCESS_TOKEN=your_particle_token

# Email Notifications (optional)
export GMAIL_USER=your_email@gmail.com
export GMAIL_APP_PASSWORD="your_gmail_app_password"
export GMAIL_RECIPIENT=notification_recipient@umn.edu
```

#### Security Notes

- **File permissions**: The credentials file has `600` permissions (readable only by you)
- **No VPN required**: MSI infrastructure has direct access to the database
- **Secure storage**: Credentials are stored locally on MSI, not in version control
- **Alternative names**: The script also checks for `~/.rtgs_credentials` as a fallback

### MSI Monitoring Workflow

#### Daily Execution Process

1. **Before 5:00 AM daily**: SLURM crontab triggers the monitoring script
2. **Environment setup**: Script loads Python and Git modules
3. **Code update**: Repository is updated with `git pull`
4. **Credential loading**: Secure credentials are loaded from `~/.rtgs_creds`
5. **Monitoring execution**: Device monitoring runs across all projects
6. **Logging**: Results and logs are saved to `~/logs/device-monitoring-logs/`
7. **Cleanup**: Virtual environment is properly deactivated

#### Log File Management

Monitoring logs are stored in:
```
~/logs/device-monitoring-logs/device_monitoring_YYYYMMDD_HHMMSS.log
```

Each log file contains:
- Execution timestamps
- Git repository updates
- Credential loading status
- Monitoring command output
- Error messages and debugging information
- Cleanup status

#### Manual Execution

You can also run monitoring manually on MSI:

```bash
# Load required modules
module load python
module load git

# Run the monitoring script directly
/home/$USER/code/scripts/scheduled_device_monitoring.sh

# Or run specific monitoring with parameters
/home/$USER/code/scripts/scheduled_device_monitoring.sh 2024-01-01 2024-01-31 "e00fce68c7f2c2b634bb4b7d" LCCMR
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