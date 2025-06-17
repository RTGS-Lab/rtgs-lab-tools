"""
Particle Device Configuration Updater

This module provides functionality to update configurations on multiple Particle devices,
verify the updates, and log execution details.
"""

import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..core.config import Config
from ..core.postgres_logger import PostgresLogger as CorePostgresLogger
from .particle_client import ParticleClient, calculate_config_uid

logger = logging.getLogger(__name__)


class ParticleConfigUpdater:
    """Main class for updating Particle device configurations."""

    def __init__(
        self,
        enable_postgres_logging: bool = True,
        repo_path: str = None,
        config: Optional[Config] = None,
    ):
        if config is None:
            config = Config()
        self.config = config
        self.client = ParticleClient(config)

        # Configuration for retries and timeouts
        self.max_retries = 3
        self.restart_wait_time = 30  # seconds to wait for device restart
        self.online_check_timeout = 120  # seconds to wait for device to come online
        self.uid_check_retries = 5
        self.max_concurrent_devices = 5  # Maximum devices to process simultaneously

        # Thread-safe counters
        self._lock = threading.Lock()
        self._processed_count = 0

        # Postgres logging
        self.enable_postgres_logging = enable_postgres_logging
        self.postgres_logger = (
            CorePostgresLogger(tool_name="device-configuration")
            if enable_postgres_logging
            else None
        )

    def get_configuration_uids(
        self, device_id: str, session: Optional[requests.Session] = None
    ) -> Tuple[Optional[int], Optional[int], bool]:
        """Get the current configuration UIDs from the device."""
        logger.info(f"Getting configuration UIDs for device {device_id}")

        for attempt in range(self.uid_check_retries):
            # Check system configuration UID
            success, system_uid, timeout = self.client.call_function(
                device_id, "getSystemConfig", session=session
            )
            if not success:
                logger.warning(
                    f"Failed to get system config UID from {device_id}, attempt {attempt + 1}"
                )
                time.sleep(5)
                continue

            # Check sensor configuration UID
            success, sensor_uid, timeout = self.client.call_function(
                device_id, "getSensorConfig", session=session
            )
            if not success:
                logger.warning(
                    f"Failed to get sensor config UID from {device_id}, attempt {attempt + 1}"
                )
                time.sleep(5)
                continue

            try:
                system_uid_int = int(system_uid) if system_uid != "timeout" else None
                sensor_uid_int = int(sensor_uid) if sensor_uid != "timeout" else None

                logger.info(
                    f"Retrieved UIDs for {device_id}: System={system_uid_int}, Sensor={sensor_uid_int}"
                )
                return system_uid_int, sensor_uid_int, True

            except (ValueError, TypeError) as e:
                logger.error(
                    f"Invalid UID response from {device_id}: system={system_uid}, sensor={sensor_uid}, error={e}"
                )

            if attempt < self.uid_check_retries - 1:
                logger.info(f"Retrying UID retrieval in 10 seconds...")
                time.sleep(10)

        return None, None, False

    def verify_configuration_uid(
        self,
        device_id: str,
        expected_system_uid: int,
        expected_sensor_uid: int,
        session: Optional[requests.Session] = None,
    ) -> Tuple[bool, Optional[int], Optional[int]]:
        """Verify that the device has the expected configuration UIDs and return actual UIDs."""
        system_uid, sensor_uid, success = self.get_configuration_uids(
            device_id, session
        )

        if not success:
            return False, system_uid, sensor_uid

        if system_uid == expected_system_uid and sensor_uid == expected_sensor_uid:
            logger.info(f"Configuration UIDs verified for {device_id}")
            logger.info(f"  System UID: {system_uid} (expected: {expected_system_uid})")
            logger.info(f"  Sensor UID: {sensor_uid} (expected: {expected_sensor_uid})")
            return True, system_uid, sensor_uid
        else:
            logger.warning(f"Configuration UID mismatch for {device_id}")
            logger.warning(
                f"  System UID: {system_uid} (expected: {expected_system_uid})"
            )
            logger.warning(
                f"  Sensor UID: {sensor_uid} (expected: {expected_sensor_uid})"
            )
            return False, system_uid, sensor_uid

    def update_device_config(
        self,
        device_id: str,
        config: Dict[str, Any],
        expected_system_uid: int,
        expected_sensor_uid: int,
        config_json_str: str,
    ) -> Dict[str, Any]:
        """Update configuration on a single device with full verification."""
        # Create a session for this thread
        session = self.client._create_session()

        # Update progress counter
        with self._lock:
            self._processed_count += 1
            current_progress = self._processed_count

        logger.info(
            f"[{current_progress}] Starting configuration update for device {device_id}"
        )

        result = {
            "device_id": device_id,
            "success": False,
            "attempts": 0,
            "error": None,
            "response_code": None,
            "system_uid": None,
            "sensor_uid": None,
            "expected_system_uid": expected_system_uid,
            "expected_sensor_uid": expected_sensor_uid,
            "uid_match": False,
            "timestamp": datetime.now().isoformat(),
            "thread_name": threading.current_thread().name,
            "config_json": config_json_str,
        }

        for attempt in range(self.max_retries):
            result["attempts"] = attempt + 1
            logger.info(
                f"[{current_progress}] Attempt {attempt + 1}/{self.max_retries} for device {device_id}"
            )

            # Check if device is online before attempting update
            if not self.client.check_device_online(device_id, session):
                logger.warning(
                    f"[{current_progress}] Device {device_id} is offline, skipping..."
                )
                result["error"] = "Device offline"
                continue

            # Call updateConfig function
            success, response, timeout = self.client.call_function(
                device_id, "updateConfig", config_json_str, session
            )

            if not success and not timeout:
                result["error"] = f"Failed to call updateConfig: {response}"
                logger.warning(
                    f"[{current_progress}] Failed to call updateConfig on {device_id}: {response}"
                )
                time.sleep(10)  # Wait before retry
                continue

            # Handle timeout case - this is expected when device restarts successfully
            if timeout:
                logger.info(
                    f"[{current_progress}] Request timed out for {device_id} - assuming successful restart"
                )
                result["response_code"] = "timeout"

                # Wait for device restart
                logger.info(
                    f"[{current_progress}] Waiting {self.restart_wait_time} seconds for device restart..."
                )
                time.sleep(self.restart_wait_time)

                # Wait for device to come back online
                if not self.client.wait_for_device_online(
                    device_id, self.online_check_timeout, session
                ):
                    result["error"] = "Device did not come back online after restart"
                    continue

                # Get and verify configuration UIDs
                uid_match, system_uid, sensor_uid = self.verify_configuration_uid(
                    device_id, expected_system_uid, expected_sensor_uid, session
                )
                result["system_uid"] = system_uid
                result["sensor_uid"] = sensor_uid
                result["uid_match"] = uid_match

                if uid_match:
                    result["success"] = True
                    logger.info(
                        f"[{current_progress}] Configuration update completed successfully for {device_id} (timeout case)"
                    )
                    break
                else:
                    result["error"] = (
                        "Configuration UID verification failed after timeout"
                    )
                    logger.warning(
                        f"[{current_progress}] UID verification failed for {device_id} after timeout, will retry"
                    )
                    continue

            # Handle non-timeout response
            result["response_code"] = response

            # Check response code (based on FlightControl implementation)
            if response == 1:
                logger.info(
                    f"[{current_progress}] Configuration update successful for {device_id}, device will restart"
                )

                # Wait for device restart
                logger.info(
                    f"[{current_progress}] Waiting {self.restart_wait_time} seconds for device restart..."
                )
                time.sleep(self.restart_wait_time)

                # Wait for device to come back online
                if not self.client.wait_for_device_online(
                    device_id, self.online_check_timeout, session
                ):
                    result["error"] = "Device did not come back online after restart"
                    continue

                # Get and verify configuration UIDs
                uid_match, system_uid, sensor_uid = self.verify_configuration_uid(
                    device_id, expected_system_uid, expected_sensor_uid, session
                )
                result["system_uid"] = system_uid
                result["sensor_uid"] = sensor_uid
                result["uid_match"] = uid_match

                if uid_match:
                    result["success"] = True
                    logger.info(
                        f"[{current_progress}] Configuration update completed successfully for {device_id}"
                    )
                    break
                else:
                    result["error"] = "Configuration UID verification failed"
                    logger.warning(
                        f"[{current_progress}] UID verification failed for {device_id}, will retry"
                    )

            elif response == 0:
                logger.info(
                    f"[{current_progress}] Configuration removed successfully for {device_id}"
                )
                result["success"] = True
                # Still get current UIDs for reporting
                _, system_uid, sensor_uid = self.get_configuration_uids(
                    device_id, session
                )
                result["system_uid"] = system_uid
                result["sensor_uid"] = sensor_uid
                break
            else:
                # Handle error codes (based on implementation)
                error_messages = {
                    -1: "Failed to remove configuration from SD card",
                    -2: "Invalid configuration format - Missing 'config' element",
                    -3: "Invalid configuration format - Missing 'system' element",
                    -4: "Invalid configuration format - Missing 'sensors' element",
                    -5: "Failed to write test file to SD card",
                    -6: "Failed to remove current configuration from SD card",
                    -7: "Failed to write new configuration to SD card",
                }

                error_msg = error_messages.get(
                    response, f"Unknown error code: {response}"
                )
                result["error"] = error_msg
                logger.error(
                    f"[{current_progress}] Configuration update failed for {device_id}: {error_msg}"
                )

                # Some errors are not worth retrying
                if response in [-2, -3, -4]:  # Configuration format errors
                    logger.error(
                        f"[{current_progress}] Configuration format error for {device_id}, not retrying"
                    )
                    break

            if attempt < self.max_retries - 1:
                logger.info(f"[{current_progress}] Retrying in 15 seconds...")
                time.sleep(15)

        if not result["success"]:
            logger.error(
                f"[{current_progress}] Failed to update configuration for {device_id} after {result['attempts']} attempts"
            )

        return result

    def update_multiple_devices(
        self, device_ids: List[str], config: Dict[str, Any], args=None
    ) -> Dict[str, Any]:
        """Update configuration on multiple devices using parallel processing."""
        logger.info(
            f"Starting parallel configuration update for {len(device_ids)} devices"
        )
        logger.info(f"Using {self.max_concurrent_devices} concurrent threads")
        logger.info(f"Configuration: {json.dumps(config, indent=2)}")

        # Calculate expected UIDs once for all devices
        try:
            expected_system_uid, expected_sensor_uid = calculate_config_uid(config)
            logger.info(
                f"Expected UIDs - System: {expected_system_uid}, Sensor: {expected_sensor_uid}"
            )
        except Exception as e:
            logger.error(f"Failed to calculate expected UIDs: {e}")
            return {
                "summary": {
                    "total_devices": len(device_ids),
                    "successful": 0,
                    "failed": len(device_ids),
                    "start_time": datetime.now().isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "error": f"Failed to calculate expected UIDs: {e}",
                    "config_json": json.dumps(config, separators=(",", ":")),
                },
                "device_results": [],
            }

        # Convert config to JSON string once
        config_json_str = json.dumps(config, separators=(",", ":"))  # Compact JSON

        results = {
            "summary": {
                "total_devices": len(device_ids),
                "successful": 0,
                "failed": 0,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "concurrent_threads": self.max_concurrent_devices,
                "expected_system_uid": expected_system_uid,
                "expected_sensor_uid": expected_sensor_uid,
                "config_json": config_json_str,
            },
            "device_results": [],
        }

        # Reset progress counter
        with self._lock:
            self._processed_count = 0

        # Process devices in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(
            max_workers=self.max_concurrent_devices, thread_name_prefix="DeviceUpdater"
        ) as executor:
            # Submit all device update tasks
            future_to_device = {
                executor.submit(
                    self.update_device_config,
                    device_id,
                    config,
                    expected_system_uid,
                    expected_sensor_uid,
                    config_json_str,
                ): device_id
                for device_id in device_ids
            }

            # Process completed futures as they finish
            completed_count = 0
            for future in as_completed(future_to_device):
                device_id = future_to_device[future]
                completed_count += 1

                try:
                    device_result = future.result()
                    results["device_results"].append(device_result)

                    if device_result["success"]:
                        results["summary"]["successful"] += 1
                        logger.info(
                            f"✅ [{completed_count}/{len(device_ids)}] Device {device_id} updated successfully"
                        )
                    else:
                        results["summary"]["failed"] += 1
                        logger.error(
                            f"❌ [{completed_count}/{len(device_ids)}] Device {device_id} failed: {device_result.get('error', 'Unknown error')}"
                        )

                except Exception as e:
                    logger.error(
                        f"❌ [{completed_count}/{len(device_ids)}] Unexpected error processing device {device_id}: {e}"
                    )
                    error_result = {
                        "device_id": device_id,
                        "success": False,
                        "attempts": 0,
                        "error": f"Thread execution error: {e}",
                        "response_code": None,
                        "system_uid": None,
                        "sensor_uid": None,
                        "expected_system_uid": expected_system_uid,
                        "expected_sensor_uid": expected_sensor_uid,
                        "uid_match": False,
                        "timestamp": datetime.now().isoformat(),
                        "thread_name": threading.current_thread().name,
                        "config_json": config_json_str,
                    }
                    results["device_results"].append(error_result)
                    results["summary"]["failed"] += 1

        results["summary"]["end_time"] = datetime.now().isoformat()

        # Calculate timing statistics
        start_time = datetime.fromisoformat(results["summary"]["start_time"])
        end_time = datetime.fromisoformat(results["summary"]["end_time"])
        total_duration = (end_time - start_time).total_seconds()

        logger.info(
            f"  Parallel configuration update completed in {total_duration:.1f} seconds:"
        )
        logger.info(f"  Total devices: {results['summary']['total_devices']}")
        logger.info(f"  Successful: {results['summary']['successful']}")
        logger.info(f"  Failed: {results['summary']['failed']}")
        logger.info(
            f"  Success rate: {(results['summary']['successful'] / results['summary']['total_devices'] * 100):.1f}%"
        )
        logger.info(
            f"  Average time per device: {(total_duration / results['summary']['total_devices']):.1f}s"
        )
        logger.info(f"  Concurrent threads used: {self.max_concurrent_devices}")

        # Create and commit postgres log if enabled
        if self.enable_postgres_logging and self.postgres_logger and args:
            try:
                # Convert to the format expected by the core PostgresLogger
                operation = f"Update configuration on {len(device_ids)} devices"

                parameters = {
                    "config_source": getattr(args, "config", "N/A"),
                    "device_source": getattr(args, "devices", "N/A"),
                    "total_devices": len(device_ids),
                    "max_retries": getattr(args, "max_retries", 3),
                    "restart_wait": getattr(args, "restart_wait", 30),
                    "online_timeout": getattr(args, "online_timeout", 120),
                    "max_concurrent": getattr(args, "max_concurrent", 5),
                    "dry_run": getattr(args, "dry_run", False),
                    "note": getattr(args, "note", ""),
                }

                cli_results = {
                    "success": results["summary"]["failed"] == 0,
                    "total_devices": results["summary"]["total_devices"],
                    "successful_updates": results["summary"]["successful"],
                    "failed_updates": results["summary"]["failed"],
                    "success_rate": (
                        results["summary"]["successful"]
                        / results["summary"]["total_devices"]
                        * 100
                    ),
                    "expected_system_uid": results["summary"].get(
                        "expected_system_uid"
                    ),
                    "expected_sensor_uid": results["summary"].get(
                        "expected_sensor_uid"
                    ),
                    "start_time": results["summary"]["start_time"],
                    "end_time": results["summary"]["end_time"],
                    "note": getattr(args, "note", ""),
                }

                # Create device summary
                device_summary = ""
                for device_result in results["device_results"]:
                    status = "✅" if device_result["success"] else "❌"
                    device_summary += f"- {status} `{device_result['device_id']}` - "
                    if device_result["success"]:
                        device_summary += f"Success (System UID: {device_result.get('system_uid', 'N/A')}, Sensor UID: {device_result.get('sensor_uid', 'N/A')})\\n"
                    else:
                        device_summary += (
                            f"Failed: {device_result.get('error', 'Unknown error')}\\n"
                        )

                additional_sections = {
                    "Update Summary": f"- **Successful**: {results['summary']['successful']}/{results['summary']['total_devices']} devices\\n- **Success Rate**: {cli_results['success_rate']:.1f}%\\n- **Expected System UID**: {results['summary'].get('expected_system_uid', 'N/A')}\\n- **Expected Sensor UID**: {results['summary'].get('expected_sensor_uid', 'N/A')}",
                    "Device Results": device_summary,
                    "Configuration Applied": f"```json\\n{json.dumps(config, indent=2)}\\n```",
                }

                log_path = self.postgres_logger.log_execution(
                    operation=operation,
                    parameters=parameters,
                    results=cli_results,
                    script_path=__file__,
                    additional_sections=additional_sections,
                )
                logger.info("✅ Execution log committed to repository")
            except Exception as e:
                logger.error(f"Failed to create/commit git log: {e}")

        return results


# Legacy standalone script functions for backward compatibility
def main():
    """Legacy main function for backward compatibility when run as a script."""
    import argparse
    import sys

    from .particle_client import parse_config_input, parse_device_input, save_results

    parser = argparse.ArgumentParser(
        description="Update Particle device configurations"
    )
    parser.add_argument(
        "--config", required=True, help="Path to configuration JSON file OR JSON string"
    )
    parser.add_argument(
        "--devices",
        required=True,
        help="Path to device list file OR comma/space separated device IDs",
    )
    parser.add_argument(
        "--output", default="update_results.json", help="Output file for results"
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, help="Maximum retry attempts per device"
    )
    parser.add_argument(
        "--restart-wait",
        type=int,
        default=30,
        help="Seconds to wait for device restart",
    )
    parser.add_argument(
        "--online-timeout",
        type=int,
        default=120,
        help="Seconds to wait for device to come online",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum concurrent devices to process",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate inputs without making changes"
    )
    parser.add_argument(
        "--no-postgres-log", action="store_true", help="Disable automatic postgres logging"
    )
    parser.add_argument(
        "--repo-path", help="Path to git repository (auto-detected if not specified)"
    )
    parser.add_argument("--note", help="Note about what update is for")

    args = parser.parse_args()

    try:
        # Set MCP environment variable if not already set (for LLM detection)
        if "MCP_SESSION" not in os.environ:
            os.environ["MCP_SESSION"] = "false"

        # Initialize configuration
        app_config = Config()

        # Load configuration and device list
        config = parse_config_input(args.config)
        device_ids = parse_device_input(args.devices)

        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            logger.info(f"Would update {len(device_ids)} devices with configuration:")
            logger.info(json.dumps(config, indent=2))
            logger.info("Device IDs:")
            for device_id in device_ids:
                logger.info(f"  - {device_id}")
            logger.info(f"Would use {args.max_concurrent} concurrent threads")
            return 0

        # Create updater and configure settings
        updater = ParticleConfigUpdater(
            enable_postgres_logging=not args.no_postgres_log,
            repo_path=args.repo_path,
            config=app_config,
        )
        updater.max_retries = args.max_retries
        updater.restart_wait_time = args.restart_wait
        updater.online_check_timeout = args.online_timeout
        updater.max_concurrent_devices = args.max_concurrent

        results = updater.update_multiple_devices(device_ids, config, args)

        # Save results
        save_results(results, args.output)

        # Return appropriate exit code
        if results["summary"]["failed"] > 0:
            logger.error(
                f"Some devices failed to update ({results['summary']['failed']}/{results['summary']['total_devices']})"
            )
            return 1
        else:
            logger.info("All devices updated successfully!")
            return 0

    except Exception as e:
        logger.error(f"Script failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
