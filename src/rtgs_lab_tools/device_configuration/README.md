# Device Configuration Module

Manage IoT device configurations and settings for Particle Cloud devices.

## CLI Usage

### Configuration Management

```bash
# Update configurations on multiple devices
rtgs device-configuration update-config \
  --config config.json \
  --devices devices.txt

# Dry run to validate without making changes
rtgs device-configuration update-config \
  --config config.json \
  --devices devices.txt \
  --dry-run

# Update with custom settings
rtgs device-configuration update-config \
  --config config.json \
  --devices "device001,device002" \
  --max-retries 5 \
  --restart-wait 45 \
  --max-concurrent 3
```

### Configuration Creation

```bash
# Create a basic configuration file
rtgs device-configuration create-config --output my_config.json

# Create configuration with custom parameters
rtgs device-configuration create-config \
  --output sensor_config.json \
  --log-period 600 \
  --power-save-mode 1 \
  --num-soil 2 \
  --num-et 1

# Create devices list file
rtgs device-configuration create-devices \
  --output my_devices.txt \
  --devices-list "device001,device002,device003"
```

### UID Decoding

```bash
# Decode system configuration UID
rtgs device-configuration decode-system 0x12345678

# Decode sensor configuration UID  
rtgs device-configuration decode-sensor 0x87654321

# Decode both UIDs at once
rtgs device-configuration decode-both \
  --system-uid 0x12345678 \
  --sensor-uid 0x87654321
```

### Command Options

**update-config:**
- `--config TEXT`: Path to configuration JSON file OR JSON string (required)
- `--devices TEXT`: Path to device list file OR comma/space separated device IDs (required)
- `--output TEXT`: Output file for results (default: update_results.json)
- `--max-retries INTEGER`: Maximum retry attempts per device (default: 3)
- `--restart-wait INTEGER`: Seconds to wait for device restart (default: 30)
- `--online-timeout INTEGER`: Seconds to wait for device to come online (default: 120)
- `--max-concurrent INTEGER`: Maximum concurrent devices to process (default: 5)
- `--dry-run`: Validate inputs without making changes

**create-config:**
- `--output TEXT`: Output file path (default: config.json)
- `--log-period INTEGER`: Logging period in seconds (default: 300)
- `--power-save-mode INTEGER`: Power save mode (default: 2)
- `--num-soil INTEGER`: Number of soil sensors (default: 1)
- `--num-et INTEGER`: Number of ET sensors (default: 0)
- Various other sensor count options

## Python API Usage

### Import and Basic Usage

```python
from rtgs_lab_tools.device_configuration import update_device_configuration, create_configuration

# Create configuration
config = create_configuration(
    log_period=600,
    power_save_mode=1,
    num_soil=2,
    num_et=1
)

# Update devices
devices = ["device001", "device002", "device003"]
results = update_device_configuration(
    config=config,
    device_ids=devices,
    max_retries=3,
    dry_run=False
)

print(f"Successfully updated {results['success_count']} devices")
print(f"Failed updates: {results['failure_count']}")
```

### Advanced Configuration Management

```python
from rtgs_lab_tools.device_configuration.update_configuration import ConfigurationUpdater
from rtgs_lab_tools.device_configuration.particle_client import ParticleClient

# Initialize clients
particle_client = ParticleClient()
updater = ConfigurationUpdater(particle_client)

# Create custom configuration
config = {
    "LogPeriod": 300,
    "BackhaulCount": 1,
    "PowerSaveMode": 2,
    "LoggingMode": 2,
    "NumAuxTalons": 1,
    "NumI2CTalons": 1,
    "NumSDI12Talons": 1,
    "NumSoil": 2,
    "NumET": 1
}

# Update single device
device_id = "device001"
try:
    result = updater.update_single_device(
        device_id=device_id,
        config=config,
        max_retries=3
    )
    print(f"Device {device_id} updated successfully")
except Exception as e:
    print(f"Failed to update {device_id}: {e}")
```

### UID Decoding Functions

```python
from rtgs_lab_tools.device_configuration.uid_decoding import decode_system_uid, decode_sensor_uid

# Decode system configuration
system_config = decode_system_uid("0x12345678")
print(f"Log Period: {system_config['LogPeriod']}")
print(f"Power Save Mode: {system_config['PowerSaveMode']}")

# Decode sensor configuration
sensor_config = decode_sensor_uid("0x87654321")
print(f"Number of Soil Sensors: {sensor_config['NumSoil']}")
print(f"Number of ET Sensors: {sensor_config['NumET']}")

# Working with decimal UIDs
system_config_decimal = decode_system_uid(305419896)  # Decimal equivalent
```

### Batch Operations

```python
from rtgs_lab_tools.device_configuration import update_device_configuration
import json

# Load device list from file
with open("devices.txt", "r") as f:
    devices = [line.strip() for line in f if line.strip()]

# Load configuration from file
with open("config.json", "r") as f:
    config = json.load(f)

# Batch update with progress tracking
results = update_device_configuration(
    config=config,
    device_ids=devices,
    max_concurrent=5,
    progress_callback=lambda completed, total: print(f"Progress: {completed}/{total}")
)

# Analyze results
successful = [r for r in results['device_results'] if r['success']]
failed = [r for r in results['device_results'] if not r['success']]

print(f"Update Summary:")
print(f"  Successful: {len(successful)}")
print(f"  Failed: {len(failed)}")

if failed:
    print("\nFailed Devices:")
    for device in failed:
        print(f"  {device['device_id']}: {device['error']}")
```

## Configuration Format

### Standard Configuration Structure

```json
{
    "LogPeriod": 300,
    "BackhaulCount": 1,
    "PowerSaveMode": 2,
    "LoggingMode": 2,
    "NumAuxTalons": 1,
    "NumI2CTalons": 1,
    "NumSDI12Talons": 1,
    "NumET": 0,
    "NumHaar": 0,
    "NumSoil": 1,
    "NumApogeeSolar": 0,
    "NumCO2": 0,
    "NumO2": 0,
    "NumPressure": 0
}
```

### Configuration Parameters

**System Settings:**
- `LogPeriod`: Data logging interval in seconds
- `BackhaulCount`: Number of data transmission attempts
- `PowerSaveMode`: Power management mode (0-3)
- `LoggingMode`: Data logging mode (0-3)

**Hardware Configuration:**
- `NumAuxTalons`: Number of auxiliary sensor connections
- `NumI2CTalons`: Number of I2C sensor connections
- `NumSDI12Talons`: Number of SDI-12 sensor connections

**Sensor Counts:**
- `NumSoil`: Number of soil sensors
- `NumET`: Number of evapotranspiration sensors
- `NumHaar`: Number of Haar wavelet sensors
- `NumApogeeSolar`: Number of Apogee solar sensors
- `NumCO2`: Number of CO2 sensors
- `NumO2`: Number of oxygen sensors
- `NumPressure`: Number of pressure sensors

### Device List Format

Create a `devices.txt` file with one device ID per line:

```
device001
device002
device003
LCCMR_01
LCCMR_02
```

## Particle Cloud Integration

### API Authentication

Environment variables (in `.env` file):
```env
PARTICLE_ACCESS_TOKEN=your_particle_access_token
```

### Device Management

```python
from rtgs_lab_tools.device_configuration.particle_client import ParticleClient

# Initialize client
client = ParticleClient()

# List devices
devices = client.list_devices()
for device in devices:
    print(f"{device['name']}: {device['id']} ({device['status']})")

# Check device status
device_info = client.get_device_info("device001")
print(f"Device online: {device_info['online']}")
print(f"Last seen: {device_info['last_heard']}")

# Call device function
result = client.call_function("device001", "getConfig")
print(f"Current config: {result}")
```

### Error Handling and Retry Logic

```python
from rtgs_lab_tools.device_configuration.update_configuration import ConfigurationUpdater

# Configure retry behavior
updater = ConfigurationUpdater(
    particle_client=client,
    default_max_retries=5,
    default_restart_wait=45,
    default_online_timeout=180
)

# Update with custom retry settings
result = updater.update_single_device(
    device_id="device001",
    config=config,
    max_retries=10,  # Override default
    restart_wait=60  # Wait longer for restart
)
```

## Examples

### Sensor Network Deployment

```python
from rtgs_lab_tools.device_configuration import create_configuration, update_device_configuration

# Create configuration for soil monitoring deployment
soil_config = create_configuration(
    log_period=900,      # 15-minute intervals
    power_save_mode=2,   # Balanced power saving
    num_soil=3,          # 3 soil sensors per node
    num_et=1,            # 1 ET sensor per node
    num_i2c_talons=2     # Additional I2C capacity
)

# Deploy to field devices
field_devices = [
    "FIELD_01", "FIELD_02", "FIELD_03", 
    "FIELD_04", "FIELD_05"
]

results = update_device_configuration(
    config=soil_config,
    device_ids=field_devices,
    max_concurrent=3  # Update 3 devices at a time
)

print(f"Deployment complete: {results['success_count']}/{len(field_devices)} devices configured")
```

### Configuration Verification

```python
from rtgs_lab_tools.device_configuration.uid_decoding import decode_system_uid, decode_sensor_uid
from rtgs_lab_tools.device_configuration.particle_client import ParticleClient

# Verify device configurations after update
client = ParticleClient()
devices = ["device001", "device002", "device003"]

for device_id in devices:
    try:
        # Get current configuration UIDs
        system_uid = client.call_function(device_id, "getSystemUID")
        sensor_uid = client.call_function(device_id, "getSensorUID")
        
        # Decode configurations
        system_config = decode_system_uid(system_uid)
        sensor_config = decode_sensor_uid(sensor_uid)
        
        print(f"\n{device_id} Configuration:")
        print(f"  Log Period: {system_config['LogPeriod']}s")
        print(f"  Power Mode: {system_config['PowerSaveMode']}")
        print(f"  Soil Sensors: {sensor_config['NumSoil']}")
        print(f"  ET Sensors: {sensor_config['NumET']}")
        
    except Exception as e:
        print(f"Failed to verify {device_id}: {e}")
```

### Maintenance and Updates

```python
from rtgs_lab_tools.device_configuration import update_device_configuration
import json
from datetime import datetime

# Load maintenance configuration
with open("maintenance_config.json", "r") as f:
    maintenance_config = json.load(f)

# Update log period for all devices during maintenance window
maintenance_config["LogPeriod"] = 60  # 1-minute logging during maintenance

# Get all online devices
client = ParticleClient()
all_devices = client.list_devices()
online_devices = [d['id'] for d in all_devices if d['online']]

print(f"Updating {len(online_devices)} online devices for maintenance...")

# Apply maintenance configuration
results = update_device_configuration(
    config=maintenance_config,
    device_ids=online_devices,
    note=f"Maintenance window configuration - {datetime.now().isoformat()}"
)

print(f"Maintenance update complete: {results['success_count']} devices updated")
```

## Troubleshooting

### Common Issues

**Device Offline:**
- Check device power and connectivity
- Verify last seen timestamp
- Consider increasing `online_timeout`

**Configuration Rejected:**
- Validate configuration JSON format
- Check sensor count limits
- Verify all required fields are present

**Particle API Errors:**
- Verify access token is valid
- Check API rate limits
- Ensure device ownership permissions

### Debugging

```python
import logging
from rtgs_lab_tools.device_configuration import update_device_configuration

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Run with detailed error reporting
results = update_device_configuration(
    config=config,
    device_ids=devices,
    dry_run=True  # Test configuration without applying
)

# Review detailed results
for device_result in results['device_results']:
    if not device_result['success']:
        print(f"Device {device_result['device_id']} failed:")
        print(f"  Error: {device_result['error']}")
        print(f"  Details: {device_result.get('error_details', 'N/A')}")
```

## Integration

### With Sensing Data Module
```python
from rtgs_lab_tools import sensing_data, device_configuration

# Update device configurations, then verify with data extraction
device_configuration.update_device_configuration(config, devices)

# Extract data to verify configuration changes
data = sensing_data.extract_data(
    project="Configuration Test",
    start_date="2023-01-01"
)

# Check data logging intervals match configuration
```

### With Audit Module
```python
from rtgs_lab_tools import device_configuration, audit

# Update devices with audit logging
results = device_configuration.update_device_configuration(
    config=config,
    device_ids=devices,
    note="Quarterly configuration update"
)

# Generate audit report
audit.generate_report(
    start_date="2023-01-01",
    end_date="2023-01-31",
    tool_name="device_configuration"
)
```