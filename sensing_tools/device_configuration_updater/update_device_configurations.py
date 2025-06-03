#!/usr/bin/env python3
"""
Particle Device Configuration Updater with Git Logging

This script updates configurations on multiple Particle devices, verifies the updates,
and automatically commits execution logs to the repository for audit purposes.
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
import os
import re
import subprocess
import getpass
import socket
import platform

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

class GitLogger:
    """Handle git operations for logging configuration updates."""
    
    def __init__(self, repo_path: str = None):
        self.repo_path = repo_path or self._find_git_repo()
        self.logs_dir = os.path.join(self.repo_path, 'logs', 'configuration-updates')
        self.ensure_logs_directory()
        
    def _find_git_repo(self) -> str:
        """Find the git repository root."""
        current_dir = os.getcwd()
        while current_dir != '/':
            if os.path.exists(os.path.join(current_dir, '.git')):
                return current_dir
            current_dir = os.path.dirname(current_dir)
        
        # If not found, use current directory
        return os.getcwd()
    
    def ensure_logs_directory(self):
        """Ensure the logs directory exists."""
        os.makedirs(self.logs_dir, exist_ok=True)
        
    def _run_git_command(self, command: List[str], cwd: str = None) -> Tuple[bool, str]:
        """Run a git command and return success status and output."""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Git command timed out"
        except Exception as e:
            return False, f"Git command failed: {e}"
    
    def _get_execution_context(self) -> Dict[str, Any]:
        """Get context information about the script execution."""
        context = {
            'timestamp': datetime.now().isoformat(),
            'user': getpass.getuser(),
            'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'working_directory': os.getcwd(),
            'script_path': os.path.abspath(__file__),
            'environment_variables': {
                'CI': os.environ.get('CI', 'false'),
                'GITHUB_ACTIONS': os.environ.get('GITHUB_ACTIONS', 'false'),
                'GITHUB_ACTOR': os.environ.get('GITHUB_ACTOR'),
                'GITHUB_WORKFLOW': os.environ.get('GITHUB_WORKFLOW'),
                'GITHUB_RUN_ID': os.environ.get('GITHUB_RUN_ID'),
                'MCP_SESSION': os.environ.get('MCP_SESSION', 'false')  # You can set this for LLM executions
            }
        }
        
        # Determine execution source
        if context['environment_variables']['GITHUB_ACTIONS'] == 'true':
            context['execution_source'] = 'GitHub Actions'
            context['triggered_by'] = context['environment_variables']['GITHUB_ACTOR']
        elif context['environment_variables']['MCP_SESSION'] == 'true':
            context['execution_source'] = 'LLM/MCP'
            context['triggered_by'] = f"LLM via {context['user']}@{context['hostname']}"
        else:
            context['execution_source'] = 'Manual/Local'
            context['triggered_by'] = f"{context['user']}@{context['hostname']}"
            
        return context
    
    def create_execution_log(self, results: Dict[str, Any], config: Dict[str, Any], 
                           device_ids: List[str], args: argparse.Namespace) -> str:
        """Create a detailed execution log."""
        context = self._get_execution_context()
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_filename = f"{timestamp}_{context['execution_source'].lower().replace('/', '_')}_{args.note.lower().replace(' ','_')}_config_update.md"
        log_path = os.path.join(self.logs_dir, log_filename)
        
        # Create log content
        log_content = f"""# Configuration Update Execution Log

## Execution Context
- **Timestamp**: {context['timestamp']}
- **Execution Source**: {context['execution_source']}
- **Triggered By**: {context['triggered_by']}
- **Hostname**: {context['hostname']}
- **Platform**: {context['platform']}
- **Working Directory**: {context['working_directory']}

## Update Details
- **Configuration Source**: {getattr(args, 'config', 'N/A')}
- **Device Source**: {getattr(args, 'devices', 'N/A')}
- **Total Devices**: {len(device_ids)}
- **Max Retries**: {getattr(args, 'max_retries', 3)}
- **Restart Wait**: {getattr(args, 'restart_wait', 30)}s
- **Online Timeout**: {getattr(args, 'online_timeout', 120)}s
- **Max Concurrent**: {getattr(args, 'max_concurrent', 5)}
- **Dry Run**: {getattr(args, 'dry_run', False)}

## Results Summary
- **Successful Updates**: {results['summary']['successful']}
- **Failed Updates**: {results['summary']['failed']}
- **Success Rate**: {(results['summary']['successful'] / results['summary']['total_devices'] * 100):.1f}%
- **Total Duration**: {self._calculate_duration(results)}
- **Expected System UID**: {results['summary'].get('expected_system_uid', 'N/A')}
- **Expected Sensor UID**: {results['summary'].get('expected_sensor_uid', 'N/A')}

## Device List
"""
        
        # Add device results
        for device_result in results['device_results']:
            status = "✅" if device_result['success'] else "❌"
            log_content += f"- {status} `{device_result['device_id']}` - "
            if device_result['success']:
                log_content += f"Success (System UID: {device_result.get('system_uid', 'N/A')}, Sensor UID: {device_result.get('sensor_uid', 'N/A')})\n"
            else:
                log_content += f"Failed: {device_result.get('error', 'Unknown error')}\n"
        
        # Add configuration details
        log_content += f"""
## Configuration Applied
```json
{json.dumps(config, indent=2)}
```

## Detailed Results
<details>
<summary>Full Results JSON</summary>

```json
{json.dumps(results, indent=2)}
```
</details>

## Execution Environment
<details>
<summary>Environment Details</summary>

```json
{json.dumps(context, indent=2)}
```
</details>

---
*Log generated automatically by Particle Configuration Updater*
"""
        
        # Write log file
        with open(log_path, 'w') as f:
            f.write(log_content)
            
        logger.info(f"Created execution log: {log_path}")
        return log_path
    
    def _calculate_duration(self, results: Dict[str, Any]) -> str:
        """Calculate and format execution duration."""
        try:
            start_time = datetime.fromisoformat(results['summary']['start_time'])
            end_time = datetime.fromisoformat(results['summary']['end_time'])
            duration = (end_time - start_time).total_seconds()
            
            if duration < 60:
                return f"{duration:.1f}s"
            elif duration < 3600:
                return f"{duration/60:.1f}m"
            else:
                return f"{duration/3600:.1f}h"
        except:
            return "Unknown"
    
    def commit_and_push_log(self, log_path: str, results: Dict[str, Any]) -> bool:
        """Commit and push the log file to the repository."""
        context = self._get_execution_context()
        
        try:
            # Check if we're in a git repository
            success, _ = self._run_git_command(['git', 'status'])
            if not success:
                logger.warning("Not in a git repository or git not available")
                return False
            
            # Add the log file
            success, output = self._run_git_command(['git', 'add', log_path])
            if not success:
                logger.error(f"Failed to add log file to git: {output}")
                return False
            
            # Check if there are changes to commit
            success, output = self._run_git_command(['git', 'diff', '--staged', '--quiet'])
            if success:  # No changes staged
                logger.info("No changes to commit (log file already exists)")
                return True
            
            # Create commit message
            success_rate = (results['summary']['successful'] / results['summary']['total_devices'] * 100)
            commit_message = (
                f"📝 Config update log: {results['summary']['successful']}/{results['summary']['total_devices']} "
                f"devices ({success_rate:.0f}%) - {context['execution_source']} by {context['triggered_by']}"
            )
            
            # Commit the changes
            success, output = self._run_git_command(['git', 'commit', '-m', commit_message])
            if not success:
                logger.error(f"Failed to commit log file: {output}")
                return False
            
            logger.info(f"Committed log file with message: {commit_message}")
            
            # Try to push (this might fail in some environments, which is ok)
            success, output = self._run_git_command(['git', 'push'])
            if success:
                logger.info("Successfully pushed log to remote repository")
            else:
                logger.warning(f"Failed to push to remote (this is normal in some environments): {output}")
                # Don't return False here - local commit is still valuable
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit/push log: {e}")
            return False

class ParticleConfigUpdater:
    def __init__(self, enable_git_logging: bool = True, repo_path: str = None):
        self.access_token = os.environ.get('PARTICLE_ACCESS_TOKEN')
        if not self.access_token:
            raise ValueError("PARTICLE_ACCESS_TOKEN env variable is required")
        self.base_url = "https://api.particle.io/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
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
        
        # Git logging
        self.enable_git_logging = enable_git_logging
        self.git_logger = GitLogger(repo_path) if enable_git_logging else None
        
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
    
    def get_configuration_uids(self, device_id: str, session: Optional[requests.Session] = None) -> Tuple[Optional[int], Optional[int], bool]:
        """Get the current configuration UIDs from the device."""
        logger.info(f"Getting configuration UIDs for device {device_id}")
        
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
                system_uid_int = int(system_uid) if system_uid != "timeout" else None
                sensor_uid_int = int(sensor_uid) if sensor_uid != "timeout" else None
                
                logger.info(f"Retrieved UIDs for {device_id}: System={system_uid_int}, Sensor={sensor_uid_int}")
                return system_uid_int, sensor_uid_int, True
                
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid UID response from {device_id}: system={system_uid}, sensor={sensor_uid}, error={e}")
            
            if attempt < self.uid_check_retries - 1:
                logger.info(f"Retrying UID retrieval in 10 seconds...")
                time.sleep(10)
        
        return None, None, False
    
    def verify_configuration_uid(self, device_id: str, expected_system_uid: int, expected_sensor_uid: int, session: Optional[requests.Session] = None) -> Tuple[bool, Optional[int], Optional[int]]:
        """Verify that the device has the expected configuration UIDs and return actual UIDs."""
        system_uid, sensor_uid, success = self.get_configuration_uids(device_id, session)
        
        if not success:
            return False, system_uid, sensor_uid
        
        if system_uid == expected_system_uid and sensor_uid == expected_sensor_uid:
            logger.info(f"Configuration UIDs verified for {device_id}")
            logger.info(f"  System UID: {system_uid} (expected: {expected_system_uid})")
            logger.info(f"  Sensor UID: {sensor_uid} (expected: {expected_sensor_uid})")
            return True, system_uid, sensor_uid
        else:
            logger.warning(f"Configuration UID mismatch for {device_id}")
            logger.warning(f"  System UID: {system_uid} (expected: {expected_system_uid})")
            logger.warning(f"  Sensor UID: {sensor_uid} (expected: {expected_sensor_uid})")
            return False, system_uid, sensor_uid
    
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
            'system_uid': None,
            'sensor_uid': None,
            'expected_system_uid': expected_system_uid,
            'expected_sensor_uid': expected_sensor_uid,
            'uid_match': False,
            'timestamp': datetime.now().isoformat(),
            'thread_name': threading.current_thread().name,
            'config_json': config_json_str
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
                
                # Get and verify configuration UIDs
                uid_match, system_uid, sensor_uid = self.verify_configuration_uid(device_id, expected_system_uid, expected_sensor_uid, session)
                result['system_uid'] = system_uid
                result['sensor_uid'] = sensor_uid
                result['uid_match'] = uid_match
                
                if uid_match:
                    result['success'] = True
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
                
                # Get and verify configuration UIDs
                uid_match, system_uid, sensor_uid = self.verify_configuration_uid(device_id, expected_system_uid, expected_sensor_uid, session)
                result['system_uid'] = system_uid
                result['sensor_uid'] = sensor_uid
                result['uid_match'] = uid_match
                
                if uid_match:
                    result['success'] = True
                    logger.info(f"[{current_progress}] Configuration update completed successfully for {device_id}")
                    break
                else:
                    result['error'] = "Configuration UID verification failed"
                    logger.warning(f"[{current_progress}] UID verification failed for {device_id}, will retry")
                    
            elif response == 0:
                logger.info(f"[{current_progress}] Configuration removed successfully for {device_id}")
                result['success'] = True
                # Still get current UIDs for reporting
                _, system_uid, sensor_uid = self.get_configuration_uids(device_id, session)
                result['system_uid'] = system_uid
                result['sensor_uid'] = sensor_uid
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
    
    def update_multiple_devices(self, device_ids: List[str], config: Dict[str, Any], 
                              args: argparse.Namespace = None) -> Dict[str, Any]:
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
                    'error': f"Failed to calculate expected UIDs: {e}",
                    'config_json': json.dumps(config, separators=(',', ':'))
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
                'concurrent_threads': self.max_concurrent_devices,
                'expected_system_uid': expected_system_uid,
                'expected_sensor_uid': expected_sensor_uid,
                'config_json': config_json_str
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
                        'system_uid': None,
                        'sensor_uid': None,
                        'expected_system_uid': expected_system_uid,
                        'expected_sensor_uid': expected_sensor_uid,
                        'uid_match': False,
                        'timestamp': datetime.now().isoformat(),
                        'thread_name': threading.current_thread().name,
                        'config_json': config_json_str
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
        
        # Create and commit git log if enabled
        if self.enable_git_logging and self.git_logger and args:
            try:
                log_path = self.git_logger.create_execution_log(results, config, device_ids, args)
                if self.git_logger.commit_and_push_log(log_path, results):
                    logger.info("✅ Execution log committed to repository")
                else:
                    logger.warning("⚠️ Failed to commit execution log to repository")
            except Exception as e:
                logger.error(f"Failed to create/commit git log: {e}")
        
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

def parse_config_input(config_input: str) -> Dict[str, Any]:
    """Parse configuration input - either a file path or JSON string."""
    # First, try to treat it as JSON string
    try:
        config = json.loads(config_input)
        logger.info("Configuration parsed as JSON string")
        
        # Basic validation
        if 'config' not in config:
            raise ValueError("Configuration must have a 'config' root element")
        
        if 'system' not in config['config']:
            raise ValueError("Configuration must have a 'system' section")
        
        if 'sensors' not in config['config']:
            raise ValueError("Configuration must have a 'sensors' section")
        
        return config
    except json.JSONDecodeError:
        # If JSON parsing fails, treat as file path
        logger.info("Configuration input treated as file path")
        return load_config_file(config_input)

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

def parse_device_input(device_input: str) -> List[str]:
    """Parse device input - either a file path or comma/space separated list."""
    # Check if it looks like a list of device IDs (contains device ID patterns)
    # Particle device IDs are typically 24 character hex strings
    device_id_pattern = r'[a-f0-9]{24}'
    
    # Remove any brackets if present and clean up the string
    cleaned_input = device_input.strip().strip('[]')
    
    # Try to find device IDs in the input
    potential_devices = re.findall(device_id_pattern, cleaned_input, re.IGNORECASE)
    
    if potential_devices:
        # Looks like a list of device IDs
        logger.info(f"Device input parsed as device ID list: {len(potential_devices)} devices found")
        return potential_devices
    
    # Check if input contains comma or space separated values that might be device IDs
    # Split by comma, semicolon, or whitespace
    tokens = re.split(r'[,;\s]+', cleaned_input)
    tokens = [token.strip() for token in tokens if token.strip()]
    
    # Check if all tokens look like device IDs (at least 20 chars, alphanumeric)
    if all(len(token) >= 20 and re.match(r'^[a-f0-9]+$', token, re.IGNORECASE) for token in tokens):
        logger.info(f"Device input parsed as separated device ID list: {len(tokens)} devices found")
        return tokens
    
    # If we can't parse as device list, treat as file path
    logger.info("Device input treated as file path")
    return load_device_list(device_input)

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
    parser.add_argument("--config", required=True, help="Path to configuration JSON file OR JSON string")
    parser.add_argument("--devices", required=True, help="Path to device list file OR comma/space separated device IDs")
    parser.add_argument("--output", default="update_results.json", help="Output file for results")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum retry attempts per device")
    parser.add_argument("--restart-wait", type=int, default=30, help="Seconds to wait for device restart")
    parser.add_argument("--online-timeout", type=int, default=120, help="Seconds to wait for device to come online")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Maximum concurrent devices to process")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without making changes")
    parser.add_argument("--no-git-log", action="store_true", help="Disable automatic git logging")
    parser.add_argument("--repo-path", help="Path to git repository (auto-detected if not specified)")
    parser.add_argument("--note", help="Note about what update is for")
    
    args = parser.parse_args()
    
    try:
        # Set MCP environment variable if not already set (for LLM detection)
        if 'MCP_SESSION' not in os.environ:
            # You can set this in your MCP server when calling the script
            os.environ['MCP_SESSION'] = 'false'
        
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
            enable_git_logging=not args.no_git_log,
            repo_path=args.repo_path
        )
        updater.max_retries = args.max_retries
        updater.restart_wait_time = args.restart_wait
        updater.online_check_timeout = args.online_timeout
        updater.max_concurrent_devices = args.max_concurrent
        
        results = updater.update_multiple_devices(device_ids, config, args)
        
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