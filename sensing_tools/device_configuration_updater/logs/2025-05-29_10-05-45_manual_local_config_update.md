# Configuration Update Execution Log

## Execution Context
- **Timestamp**: 2025-05-29T10:05:45.216708
- **Execution Source**: Manual/Local
- **Triggered By**: zach@zach-Z390-AORUS-PRO-WIFI
- **Hostname**: zach-Z390-AORUS-PRO-WIFI
- **Platform**: Linux-6.11.0-25-generic-x86_64-with-glibc2.39
- **Working Directory**: /home/zach/Code/gems_sensing_db_tools

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
    "start_time": "2025-05-29T10:04:43.210736",
    "end_time": "2025-05-29T10:05:45.215391",
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
      "timestamp": "2025-05-29T10:04:43.211068",
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
  "timestamp": "2025-05-29T10:05:45.216708",
  "user": "zach",
  "hostname": "zach-Z390-AORUS-PRO-WIFI",
  "platform": "Linux-6.11.0-25-generic-x86_64-with-glibc2.39",
  "python_version": "3.12.3",
  "working_directory": "/home/zach/Code/gems_sensing_db_tools",
  "script_path": "/home/zach/Code/gems_sensing_db_tools/update_configuration.py",
  "environment_variables": {
    "CI": "false",
    "GITHUB_ACTIONS": "false",
    "GITHUB_ACTOR": null,
    "GITHUB_WORKFLOW": null,
    "GITHUB_RUN_ID": null,
    "MCP_SESSION": "false"
  },
  "execution_source": "Manual/Local",
  "triggered_by": "zach@zach-Z390-AORUS-PRO-WIFI"
}
```
</details>

---
*Log generated automatically by Particle Configuration Updater*
