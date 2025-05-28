#should take a config file and a list of device ids
#should call updateConfig(config.json as string) for each device
#should check return value, if any return value then retry
#should wait for restart and device to come back online
#should verify the UID matches the uploaded config file
#if it doesn't then retry

#!/usr/bin/env python3
"""
Particle Device Configuration Updater

This script updates configurations on multiple Particle devices and verifies the updates.
It handles retries, waits for device restarts, and validates configuration UIDs.
"""

import json
import time
import argparse
import sys
import requests
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('particle_config_update.log')
    ]
)
logger = logging.getLogger(__name__)

class ParticleConfigUpdater:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.particle.io/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        # Configuration for retries and timeouts
        self.max_retries = 3
        self.restart_wait_time = 30  # seconds to wait for device restart
        self.online_check_timeout = 120  # seconds to wait for device to come online
        self.uid_check_retries = 5
        self.max_concurrent_devices = 5  # Maximum devices to process simultaneously
        
        # Thread-safe counters
        self._lock = threading.Lock()
        self._processed_count = 0
        
    def _create_session(self) -> requests.Session:
        """Create a new session for thread safety."""
        session = requests.Session()
        session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        return session
        
    def calculate_config_uid(self, config: Dict[str, Any]) -> Tuple[int, int]:
        """Calculate system and sensor configuration UIDs based on the config."""
        try:
            system = config['config']['system']
            sensors = config['config']['sensors']
            
            # System UID calculation (based on your ConfigurationManager.cpp)
            system_uid = (
                (system.get('logPeriod', 300) << 16) |
                (system.get('backhaulCount', 4) << 12) |
                (system.get('powerSaveMode', 1) << 10) |
                (system.get('loggingMode', 0) << 8) |
                (system.get('numAuxTalons', 1) << 6) |
                (system.get('numI2CTalons', 1) << 4) |
                (system.get('numSDI12Talons', 1) << 2)
            )
            
            # Sensor UID calculation
            sensor_uid = (
                (sensors.get('numET', 0) << 28) |
                (sensors.get('numHaar', 0) << 24) |
                (sensors.get('numSoil', 3) << 20) |
                (sensors.get('numApogeeSolar', 0) << 16) |
                (sensors.get('numCO2', 0) << 12) |
                (sensors.get('numO2', 0) << 8) |
                (sensors.get('numPressure', 0) << 4)
            )
            
            return system_uid, sensor_uid
            
        except KeyError as e:
            logger.error(f"Invalid configuration structure: missing {e}")
            raise ValueError(f"Invalid configuration structure: missing {e}")
    
    def call_particle_function(self, device_id: str, function_name: str, argument: str = "", session: Optional[requests.Session] = None) -> Tuple[bool, Any, bool]:
        """Call a Particle cloud function and return success status, response, and timeout flag."""
        if session is None:
            session = self.session
            
        url = f"{self.base_url}/devices/{device_id}/{function_name}"
        data = {'arg': argument}
        
        try:
            response = session.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('connected') == False:
                logger.warning(f"Device {device_id} is offline")
                return False, "Device offline", False
            
            return_value = result.get('return_value')
            logger.info(f"Function {function_name} on {device_id} returned: {return_value}")
            
            return True, return_value, False
            
        except requests.exceptions.Timeout:
            logger.info(f"Timeout calling {function_name} on {device_id} - this is expected if device is restarting")
            return True, "timeout", True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling {function_name} on {device_id}: {e}")
            return False, str(e), False
    
    def check_device_online(self, device_id: str, session: Optional[requests.Session] = None) -> bool:
        """Check if a device is online."""
        if session is None:
            session = self.session
            
        url = f"{self.base_url}/devices/{device_id}"
        
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            device_info = response.json()
            return device_info.get('connected', False)
        except Exception as e:
            logger.error(f"Error checking device {device_id} status: {e}")
            return False
    
    def wait_for_device_online(self, device_id: str, session: Optional[requests.Session] = None) -> bool:
        """Wait for device to come back online after restart."""
        logger.info(f"Waiting for device {device_id} to come back online...")
        
        start_time = time.time()
        while time.time() - start_time < self.online_check_timeout:
            if self.check_device_online(device_id, session):
                logger.info(f"Device {device_id} is back online")
                return True
            
            time.sleep(5)  # Check every 5 seconds
        
        logger.error(f"Device {device_id} did not come back online within {self.online_check_timeout} seconds")
        return False
    
    def verify_configuration_uid(self, device_id: str, expected_system_uid: int, expected_sensor_uid: int, session: Optional[requests.Session] = None) -> bool:
        """Verify that the device has the expected configuration UIDs."""
        logger.info(f"Verifying configuration UIDs for device {device_id}")
        
        for attempt in range(self.uid_check_retries):
            # Check system configuration UID
            success, system_uid, timeout = self.call_particle_function(device_id, "getSystemConfig", session=session)
            if not success:
                logger.warning(f"Failed to get system config UID from {device_id}, attempt {attempt + 1}")
                time.sleep(5)
                continue
            
            # Check sensor configuration UID
            success, sensor_uid, timeout = self.call_particle_function(device_id, "getSensorConfig", session=session)
            if not success:
                logger.warning(f"Failed to get sensor config UID from {device_id}, attempt {attempt + 1}")
                time.sleep(5)
                continue
            
            try:
                system_uid = int(system_uid)
                sensor_uid = int(sensor_uid)
                
                if system_uid == expected_system_uid and sensor_uid == expected_sensor_uid:
                    logger.info(f"Configuration UIDs verified for {device_id}")
                    logger.info(f"  System UID: {system_uid} (expected: {expected_system_uid})")
                    logger.info(f"  Sensor UID: {sensor_uid} (expected: {expected_sensor_uid})")
                    return True
                else:
                    logger.warning(f"Configuration UID mismatch for {device_id}")
                    logger.warning(f"  System UID: {system_uid} (expected: {expected_system_uid})")
                    logger.warning(f"  Sensor UID: {sensor_uid} (expected: {expected_sensor_uid})")
                    
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid UID response from {device_id}: {e}")
            
            if attempt < self.uid_check_retries - 1:
                logger.info(f"Retrying UID verification in 10 seconds...")
                time.sleep(10)
        
        return False
    
    def update_device_config(self, device_id: str, config: Dict[str, Any], expected_system_uid: int, expected_sensor_uid: int, config_json_str: str) -> Dict[str, Any]:
        """Update configuration on a single device with full verification."""
        # Create a session for this thread
        session = self._create_session()
        
        # Update progress counter
        with self._lock:
            self._processed_count += 1
            current_progress = self._processed_count
        
        logger.info(f"[{current_progress}] Starting configuration update for device {device_id}")
        
        result = {
            'device_id': device_id,
            'success': False,
            'attempts': 0,
            'error': None,
            'response_code': None,
            'uid_verified': False,
            'timestamp': datetime.now().isoformat(),
            'thread_name': threading.current_thread().name
        }
        
        for attempt in range(self.max_retries):
            result['attempts'] = attempt + 1
            logger.info(f"[{current_progress}] Attempt {attempt + 1}/{self.max_retries} for device {device_id}")
            
            # Check if device is online before attempting update
            if not self.check_device_online(device_id, session):
                logger.warning(f"[{current_progress}] Device {device_id} is offline, skipping...")
                result['error'] = "Device offline"
                continue
            
            # Call updateConfig function
            success, response, timeout = self.call_particle_function(device_id, "updateConfig", config_json_str, session)
            
            if not success and not timeout:
                result['error'] = f"Failed to call updateConfig: {response}"
                logger.warning(f"[{current_progress}] Failed to call updateConfig on {device_id}: {response}")
                time.sleep(10)  # Wait before retry
                continue
            
            # Handle timeout case - this is expected when device restarts successfully
            if timeout:
                logger.info(f"[{current_progress}] Request timed out for {device_id} - assuming successful restart")
                result['response_code'] = "timeout"
                
                # Wait for device restart
                logger.info(f"[{current_progress}] Waiting {self.restart_wait_time} seconds for device restart...")
                time.sleep(self.restart_wait_time)
                
                # Wait for device to come back online
                if not self.wait_for_device_online(device_id, session):
                    result['error'] = "Device did not come back online after restart"
                    continue
                
                # Verify configuration UIDs
                if self.verify_configuration_uid(device_id, expected_system_uid, expected_sensor_uid, session):
                    result['success'] = True
                    result['uid_verified'] = True
                    logger.info(f"[{current_progress}] Configuration update completed successfully for {device_id} (timeout case)")
                    break
                else:
                    result['error'] = "Configuration UID verification failed after timeout"
                    logger.warning(f"[{current_progress}] UID verification failed for {device_id} after timeout, will retry")
                    continue
            
            # Handle non-timeout response
            result['response_code'] = response
            
            # Check response code (based on your FlightControl implementation)
            if response == 1:
                logger.info(f"[{current_progress}] Configuration update successful for {device_id}, device will restart")
                
                # Wait for device restart
                logger.info(f"[{current_progress}] Waiting {self.restart_wait_time} seconds for device restart...")
                time.sleep(self.restart_wait_time)
                
                # Wait for device to come back online
                if not self.wait_for_device_online(device_id, session):
                    result['error'] = "Device did not come back online after restart"
                    continue
                
                # Verify configuration UIDs
                if self.verify_configuration_uid(device_id, expected_system_uid, expected_sensor_uid, session):
                    result['success'] = True
                    result['uid_verified'] = True
                    logger.info(f"[{current_progress}] Configuration update completed successfully for {device_id}")
                    break
                else:
                    result['error'] = "Configuration UID verification failed"
                    logger.warning(f"[{current_progress}] UID verification failed for {device_id}, will retry")
                    
            elif response == 0:
                logger.info(f"[{current_progress}] Configuration removed successfully for {device_id}")
                result['success'] = True
                break
            else:
                # Handle error codes (based on your implementation)
                error_messages = {
                    -1: "Failed to remove configuration from SD card",
                    -2: "Invalid configuration format - Missing 'config' element",
                    -3: "Invalid configuration format - Missing 'system' element", 
                    -4: "Invalid configuration format - Missing 'sensors' element",
                    -5: "Failed to write test file to SD card",
                    -6: "Failed to remove current configuration from SD card",
                    -7: "Failed to write new configuration to SD card"
                }
                
                error_msg = error_messages.get(response, f"Unknown error code: {response}")
                result['error'] = error_msg
                logger.error(f"[{current_progress}] Configuration update failed for {device_id}: {error_msg}")
                
                # Some errors are not worth retrying
                if response in [-2, -3, -4]:  # Configuration format errors
                    logger.error(f"[{current_progress}] Configuration format error for {device_id}, not retrying")
                    break
            
            if attempt < self.max_retries - 1:
                logger.info(f"[{current_progress}] Retrying in 15 seconds...")
                time.sleep(15)
        
        if not result['success']:
            logger.error(f"[{current_progress}] Failed to update configuration for {device_id} after {result['attempts']} attempts")
        
        return result
    
    def update_multiple_devices(self, device_ids: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration on multiple devices using parallel processing."""
        logger.info(f"Starting parallel configuration update for {len(device_ids)} devices")
        logger.info(f"Using {self.max_concurrent_devices} concurrent threads")
        logger.info(f"Configuration: {json.dumps(config, indent=2)}")
        
        # Calculate expected UIDs once for all devices
        try:
            expected_system_uid, expected_sensor_uid = self.calculate_config_uid(config)
            logger.info(f"Expected UIDs - System: {expected_system_uid}, Sensor: {expected_sensor_uid}")
        except Exception as e:
            logger.error(f"Failed to calculate expected UIDs: {e}")
            return {
                'summary': {
                    'total_devices': len(device_ids),
                    'successful': 0,
                    'failed': len(device_ids),
                    'start_time': datetime.now().isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'error': f"Failed to calculate expected UIDs: {e}"
                },
                'device_results': []
            }
        
        # Convert config to JSON string once
        config_json_str = json.dumps(config, separators=(',', ':'))  # Compact JSON
        
        results = {
            'summary': {
                'total_devices': len(device_ids),
                'successful': 0,
                'failed': 0,
                'start_time': datetime.now().isoformat(),
                'end_time': None,
                'concurrent_threads': self.max_concurrent_devices
            },
            'device_results': []
        }
        
        # Reset progress counter
        with self._lock:
            self._processed_count = 0
        
        # Process devices in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_concurrent_devices, thread_name_prefix="DeviceUpdater") as executor:
            # Submit all device update tasks
            future_to_device = {
                executor.submit(
                    self.update_device_config, 
                    device_id, 
                    config, 
                    expected_system_uid, 
                    expected_sensor_uid, 
                    config_json_str
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
                    results['device_results'].append(device_result)
                    
                    if device_result['success']:
                        results['summary']['successful'] += 1
                        logger.info(f"✅ [{completed_count}/{len(device_ids)}] Device {device_id} updated successfully")
                    else:
                        results['summary']['failed'] += 1
                        logger.error(f"❌ [{completed_count}/{len(device_ids)}] Device {device_id} failed: {device_result.get('error', 'Unknown error')}")
                    
                except Exception as e:
                    logger.error(f"❌ [{completed_count}/{len(device_ids)}] Unexpected error processing device {device_id}: {e}")
                    error_result = {
                        'device_id': device_id,
                        'success': False,
                        'attempts': 0,
                        'error': f"Thread execution error: {e}",
                        'response_code': None,
                        'uid_verified': False,
                        'timestamp': datetime.now().isoformat(),
                        'thread_name': threading.current_thread().name
                    }
                    results['device_results'].append(error_result)
                    results['summary']['failed'] += 1
        
        results['summary']['end_time'] = datetime.now().isoformat()
        
        # Calculate timing statistics
        start_time = datetime.fromisoformat(results['summary']['start_time'])
        end_time = datetime.fromisoformat(results['summary']['end_time'])
        total_duration = (end_time - start_time).total_seconds()
        
        logger.info(f"📊 Parallel configuration update completed in {total_duration:.1f} seconds:")
        logger.info(f"  Total devices: {results['summary']['total_devices']}")
        logger.info(f"  Successful: {results['summary']['successful']}")
        logger.info(f"  Failed: {results['summary']['failed']}")
        logger.info(f"  Success rate: {(results['summary']['successful'] / results['summary']['total_devices'] * 100):.1f}%")
        logger.info(f"  Average time per device: {(total_duration / results['summary']['total_devices']):.1f}s")
        logger.info(f"  Concurrent threads used: {self.max_concurrent_devices}")
        
        return results

def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load and validate configuration file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Basic validation
        if 'config' not in config:
            raise ValueError("Configuration must have a 'config' root element")
        
        if 'system' not in config['config']:
            raise ValueError("Configuration must have a 'system' section")
        
        if 'sensors' not in config['config']:
            raise ValueError("Configuration must have a 'sensors' section")
        
        logger.info(f"Loaded configuration from {config_path}")
        return config
        
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration file: {e}")
        raise

def load_device_list(device_list_path: str) -> List[str]:
    """Load device list from file."""
    try:
        with open(device_list_path, 'r') as f:
            # Support both JSON array and line-separated device IDs
            content = f.read().strip()
            
            if content.startswith('['):
                # JSON array format
                device_ids = json.loads(content)
            else:
                # Line-separated format
                device_ids = [line.strip() for line in content.split('\n') if line.strip()]
        
        if not device_ids:
            raise ValueError("Device list is empty")
        
        logger.info(f"Loaded {len(device_ids)} device IDs from {device_list_path}")
        return device_ids
        
    except FileNotFoundError:
        logger.error(f"Device list file not found: {device_list_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading device list: {e}")
        raise

def save_results(results: Dict[str, Any], output_path: str):
    """Save results to JSON file."""
    try:
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")

def main():
    parser = argparse.ArgumentParser(description="Update Particle device configurations")
    parser.add_argument("--config", required=True, help="Path to configuration JSON file")
    parser.add_argument("--devices", required=True, help="Path to device list file (JSON array or line-separated)")
    parser.add_argument("--token", required=True, help="Particle access token")
    parser.add_argument("--output", default="update_results.json", help="Output file for results")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum retry attempts per device")
    parser.add_argument("--restart-wait", type=int, default=30, help="Seconds to wait for device restart")
    parser.add_argument("--online-timeout", type=int, default=120, help="Seconds to wait for device to come online")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Maximum concurrent devices to process")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without making changes")
    
    args = parser.parse_args()
    
    try:
        # Load configuration and device list
        config = load_config_file(args.config)
        device_ids = load_device_list(args.devices)
        
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
        updater = ParticleConfigUpdater(args.token)
        updater.max_retries = args.max_retries
        updater.restart_wait_time = args.restart_wait
        updater.online_check_timeout = args.online_timeout
        updater.max_concurrent_devices = args.max_concurrent
        
        results = updater.update_multiple_devices(device_ids, config)
        
        # Save results
        save_results(results, args.output)
        
        # Return appropriate exit code
        if results['summary']['failed'] > 0:
            logger.error(f"Some devices failed to update ({results['summary']['failed']}/{results['summary']['total_devices']})")
            return 1
        else:
            logger.info("All devices updated successfully!")
            return 0
            
    except Exception as e:
        logger.error(f"Script failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())