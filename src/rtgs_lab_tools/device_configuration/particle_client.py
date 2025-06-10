"""Particle Cloud API client and utilities."""

import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..core.config import Config
from ..core.exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)


class ParticleClient:
    """Client for interacting with Particle Cloud API."""

    def __init__(self, config: Optional[Config] = None):
        if config is None:
            config = Config()

        self.access_token = config.particle_access_token
        if not self.access_token:
            raise APIError(
                "PARTICLE_ACCESS_TOKEN not found in configuration. Please add it to your .env file."
            )

        self.base_url = "https://api.particle.io/v1"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )

    def _create_session(self) -> requests.Session:
        """Create a new session for thread safety."""
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        return session

    def call_function(
        self,
        device_id: str,
        function_name: str,
        argument: str = "",
        session: Optional[requests.Session] = None,
    ) -> Tuple[bool, Any, bool]:
        """Call a Particle cloud function and return success status, response, and timeout flag."""
        if session is None:
            session = self.session

        url = f"{self.base_url}/devices/{device_id}/{function_name}"
        data = {"arg": argument}

        try:
            response = session.post(url, data=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get("connected") == False:
                logger.warning(f"Device {device_id} is offline")
                return False, "Device offline", False

            return_value = result.get("return_value")
            logger.info(
                f"Function {function_name} on {device_id} returned: {return_value}"
            )

            return True, return_value, False

        except requests.exceptions.Timeout:
            logger.info(
                f"Timeout calling {function_name} on {device_id} - this is expected if device is restarting"
            )
            return True, "timeout", True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling {function_name} on {device_id}: {e}")
            return False, str(e), False

    def check_device_online(
        self, device_id: str, session: Optional[requests.Session] = None
    ) -> bool:
        """Check if a device is online."""
        if session is None:
            session = self.session

        url = f"{self.base_url}/devices/{device_id}"

        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            device_info = response.json()
            return device_info.get("connected", False)
        except Exception as e:
            logger.error(f"Error checking device {device_id} status: {e}")
            return False

    def wait_for_device_online(
        self,
        device_id: str,
        timeout: int = 120,
        session: Optional[requests.Session] = None,
    ) -> bool:
        """Wait for device to come back online after restart."""
        logger.info(f"Waiting for device {device_id} to come back online...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_device_online(device_id, session):
                logger.info(f"Device {device_id} is back online")
                return True

            time.sleep(5)  # Check every 5 seconds

        logger.error(
            f"Device {device_id} did not come back online within {timeout} seconds"
        )
        return False


def calculate_config_uid(config: Dict[str, Any]) -> Tuple[int, int]:
    """Calculate system and sensor configuration UIDs based on the config."""
    try:
        system = config["config"]["system"]
        sensors = config["config"]["sensors"]

        # System UID calculation (based on ConfigurationManager.cpp)
        system_uid = (
            (system.get("logPeriod", 300) << 16)
            | (system.get("backhaulCount", 4) << 12)
            | (system.get("powerSaveMode", 1) << 10)
            | (system.get("loggingMode", 0) << 8)
            | (system.get("numAuxTalons", 1) << 6)
            | (system.get("numI2CTalons", 1) << 4)
            | (system.get("numSDI12Talons", 1) << 2)
        )

        # Sensor UID calculation
        sensor_uid = (
            (sensors.get("numET", 0) << 28)
            | (sensors.get("numHaar", 0) << 24)
            | (sensors.get("numSoil", 3) << 20)
            | (sensors.get("numApogeeSolar", 0) << 16)
            | (sensors.get("numCO2", 0) << 12)
            | (sensors.get("numO2", 0) << 8)
            | (sensors.get("numPressure", 0) << 4)
        )

        return system_uid, sensor_uid

    except KeyError as e:
        logger.error(f"Invalid configuration structure: missing {e}")
        raise ValidationError(f"Invalid configuration structure: missing {e}")


def parse_config_input(config_input: str) -> Dict[str, Any]:
    """Parse configuration input - either a file path or JSON string."""
    # First, try to treat it as JSON string
    try:
        config = json.loads(config_input)
        logger.info("Configuration parsed as JSON string")

        # Basic validation
        if "config" not in config:
            raise ValidationError("Configuration must have a 'config' root element")

        if "system" not in config["config"]:
            raise ValidationError("Configuration must have a 'system' section")

        if "sensors" not in config["config"]:
            raise ValidationError("Configuration must have a 'sensors' section")

        return config
    except json.JSONDecodeError:
        # If JSON parsing fails, treat as file path
        logger.info("Configuration input treated as file path")
        return load_config_file(config_input)


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load and validate configuration file."""
    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        # Basic validation
        if "config" not in config:
            raise ValidationError("Configuration must have a 'config' root element")

        if "system" not in config["config"]:
            raise ValidationError("Configuration must have a 'system' section")

        if "sensors" not in config["config"]:
            raise ValidationError("Configuration must have a 'sensors' section")

        logger.info(f"Loaded configuration from {config_path}")
        return config

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise ValidationError(f"Configuration file not found: {config_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        raise ValidationError(f"Invalid JSON in configuration file: {e}")
    except Exception as e:
        logger.error(f"Error loading configuration file: {e}")
        raise ValidationError(f"Error loading configuration file: {e}")


def parse_device_input(device_input: str) -> List[str]:
    """Parse device input - either a file path or comma/space separated list."""
    # Check if it looks like a list of device IDs (contains device ID patterns)
    # Particle device IDs are typically 24 character hex strings
    device_id_pattern = r"[a-f0-9]{24}"

    # Remove any brackets if present and clean up the string
    cleaned_input = device_input.strip().strip("[]")

    # Try to find device IDs in the input
    potential_devices = re.findall(device_id_pattern, cleaned_input, re.IGNORECASE)

    if potential_devices:
        # Looks like a list of device IDs
        logger.info(
            f"Device input parsed as device ID list: {len(potential_devices)} devices found"
        )
        return potential_devices

    # Check if input contains comma or space separated values that might be device IDs
    # Split by comma, semicolon, or whitespace
    tokens = re.split(r"[,;\s]+", cleaned_input)
    tokens = [token.strip() for token in tokens if token.strip()]

    # Check if all tokens look like device IDs (at least 20 chars, alphanumeric)
    if all(
        len(token) >= 20 and re.match(r"^[a-f0-9]+$", token, re.IGNORECASE)
        for token in tokens
    ):
        logger.info(
            f"Device input parsed as separated device ID list: {len(tokens)} devices found"
        )
        return tokens

    # If we can't parse as device list, treat as file path
    logger.info("Device input treated as file path")
    return load_device_list(device_input)


def load_device_list(device_list_path: str) -> List[str]:
    """Load device list from file."""
    try:
        with open(device_list_path, "r") as f:
            # Support both JSON array and line-separated device IDs
            content = f.read().strip()

            if content.startswith("["):
                # JSON array format
                device_ids = json.loads(content)
            else:
                # Line-separated format
                device_ids = [
                    line.strip() for line in content.split("\n") if line.strip()
                ]

        if not device_ids:
            raise ValidationError("Device list is empty")

        logger.info(f"Loaded {len(device_ids)} device IDs from {device_list_path}")
        return device_ids

    except FileNotFoundError:
        logger.error(f"Device list file not found: {device_list_path}")
        raise ValidationError(f"Device list file not found: {device_list_path}")
    except Exception as e:
        logger.error(f"Error loading device list: {e}")
        raise ValidationError(f"Error loading device list: {e}")


def save_results(results: Dict[str, Any], output_path: str):
    """Save results to JSON file."""
    try:
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        raise ValidationError(f"Failed to save results: {e}")
