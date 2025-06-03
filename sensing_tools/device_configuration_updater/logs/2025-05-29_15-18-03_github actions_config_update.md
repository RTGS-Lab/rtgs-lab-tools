# Configuration Update Execution Log

## Execution Context
- **Timestamp**: 2025-05-29T15:18:03.078785
- **Execution Source**: GitHub Actions
- **Triggered By**: zradlicz
- **Hostname**: pkrvmf6wy0o8zjz
- **Platform**: Linux-6.11.0-1014-azure-x86_64-with-glibc2.39
- **Working Directory**: /home/runner/work/gems_sensing_db_tools/gems_sensing_db_tools

## Update Details
- **Configuration Source**: configurations/config.json
- **Device Source**: e00fce6885951c63c0e86719
- **Total Devices**: 1
- **Max Retries**: 3
- **Restart Wait**: 30s
- **Online Timeout**: 120s
- **Max Concurrent**: 5
- **Dry Run**: False

## Results Summary
- **Successful Updates**: 1
- **Failed Updates**: 0
- **Success Rate**: 100.0%
- **Total Duration**: 1.0m
- **Expected System UID**: 59001428
- **Expected Sensor UID**: 1048576

## Device List
- ✅ `e00fce6885951c63c0e86719` - Success (System UID: 59001428, Sensor UID: 1048576)

## Configuration Applied
```json
{
  "config": {
    "system": {
      "logPeriod": 900,
      "backhaulCount": 4,
      "powerSaveMode": 2,
      "loggingMode": 2,
      "numAuxTalons": 1,
      "numI2CTalons": 1,
      "numSDI12Talons": 1
    },
    "sensors": {
      "numET": 0,
      "numHaar": 0,
      "numSoil": 1,
      "numApogeeSolar": 0,
      "numCO2": 0,
      "numO2": 0,
      "numPressure": 0
    }
  }
}
```

## Detailed Results
<details>
<summary>Full Results JSON</summary>

```json
{
  "summary": {
    "total_devices": 1,
    "successful": 1,
    "failed": 0,
    "start_time": "2025-05-29T15:17:00.688171",
    "end_time": "2025-05-29T15:18:03.078337",
    "concurrent_threads": 5,
    "expected_system_uid": 59001428,
    "expected_sensor_uid": 1048576,
    "config_json": "{\"config\":{\"system\":{\"logPeriod\":900,\"backhaulCount\":4,\"powerSaveMode\":2,\"loggingMode\":2,\"numAuxTalons\":1,\"numI2CTalons\":1,\"numSDI12Talons\":1},\"sensors\":{\"numET\":0,\"numHaar\":0,\"numSoil\":1,\"numApogeeSolar\":0,\"numCO2\":0,\"numO2\":0,\"numPressure\":0}}}"
  },
  "device_results": [
    {
      "device_id": "e00fce6885951c63c0e86719",
      "success": true,
      "attempts": 1,
      "error": null,
      "response_code": "timeout",
      "system_uid": 59001428,
      "sensor_uid": 1048576,
      "expected_system_uid": 59001428,
      "expected_sensor_uid": 1048576,
      "uid_match": true,
      "timestamp": "2025-05-29T15:17:00.688725",
      "thread_name": "DeviceUpdater_0",
      "config_json": "{\"config\":{\"system\":{\"logPeriod\":900,\"backhaulCount\":4,\"powerSaveMode\":2,\"loggingMode\":2,\"numAuxTalons\":1,\"numI2CTalons\":1,\"numSDI12Talons\":1},\"sensors\":{\"numET\":0,\"numHaar\":0,\"numSoil\":1,\"numApogeeSolar\":0,\"numCO2\":0,\"numO2\":0,\"numPressure\":0}}}"
    }
  ]
}
```
</details>

## Execution Environment
<details>
<summary>Environment Details</summary>

```json
{
  "timestamp": "2025-05-29T15:18:03.078785",
  "user": "runner",
  "hostname": "pkrvmf6wy0o8zjz",
  "platform": "Linux-6.11.0-1014-azure-x86_64-with-glibc2.39",
  "python_version": "3.12.10",
  "working_directory": "/home/runner/work/gems_sensing_db_tools/gems_sensing_db_tools",
  "script_path": "/home/runner/work/gems_sensing_db_tools/gems_sensing_db_tools/update_configuration.py",
  "environment_variables": {
    "CI": "true",
    "GITHUB_ACTIONS": "true",
    "GITHUB_ACTOR": "zradlicz",
    "GITHUB_WORKFLOW": "Update Particle Device Configurations",
    "GITHUB_RUN_ID": "15327180090",
    "MCP_SESSION": "false"
  },
  "execution_source": "GitHub Actions",
  "triggered_by": "zradlicz"
}
```
</details>

---
*Log generated automatically by Particle Configuration Updater*
