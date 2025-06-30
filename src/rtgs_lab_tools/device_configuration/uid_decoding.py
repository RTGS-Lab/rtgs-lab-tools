"""UID decoding utilities for device configuration.

Decodes system and sensor configuration UIDs from ConfigurationManager.
"""

from typing import Dict, Union


def decode_system_configuration_uid(uid: int) -> Dict[str, int]:
    """
    Decode the system configuration UID created by updateSystemConfigurationUid()

    Args:
        uid (int): The encoded system configuration UID

    Returns:
        dict: Dictionary containing decoded configuration values
    """
    config = {}

    # Extract each field using bit masks and shifts
    config["log_period"] = (uid >> 16) & 0xFFFF  # Upper 16 bits
    config["backhaul_count"] = (uid >> 12) & 0xF  # 4 bits at position 12-15
    config["power_save_mode"] = (uid >> 10) & 0x3  # 2 bits at position 10-11
    config["logging_mode"] = (uid >> 8) & 0x3  # 2 bits at position 8-9
    config["num_aux_talons"] = (uid >> 6) & 0x3  # 2 bits at position 6-7
    config["num_i2c_talons"] = (uid >> 4) & 0x3  # 2 bits at position 4-5
    config["num_sdi12_talons"] = (uid >> 2) & 0x3  # 2 bits at position 2-3

    return config


def decode_sensor_configuration_uid(uid: int) -> Dict[str, int]:
    """
    Decode the sensor configuration UID created by updateSensorConfigurationUid()

    Args:
        uid (int): The encoded sensor configuration UID

    Returns:
        dict: Dictionary containing decoded sensor counts
    """
    config = {}

    # Extract each field using bit masks and shifts
    config["num_et"] = (uid >> 28) & 0xF  # 4 bits at position 28-31
    config["num_haar"] = (uid >> 24) & 0xF  # 4 bits at position 24-27
    config["num_soil"] = (uid >> 20) & 0xF  # 4 bits at position 20-23
    config["num_apogee_solar"] = (uid >> 16) & 0xF  # 4 bits at position 16-19
    config["num_co2"] = (uid >> 12) & 0xF  # 4 bits at position 12-15
    config["num_o2"] = (uid >> 8) & 0xF  # 4 bits at position 8-11
    config["num_pressure"] = (uid >> 4) & 0xF  # 4 bits at position 4-7

    return config


def format_system_config(uid: int) -> str:
    """Format system configuration for display.

    Args:
        uid: The encoded system configuration UID

    Returns:
        Formatted string representation of the configuration
    """
    config = decode_system_configuration_uid(uid)
    lines = [
        f"System Configuration UID: 0x{uid:08X} ({uid})",
        "=" * 50,
        f"Log Period:           {config['log_period']}",
        f"Backhaul Count:       {config['backhaul_count']}",
        f"Power Save Mode:      {config['power_save_mode']}",
        f"Logging Mode:         {config['logging_mode']}",
        f"Num Aux Talons:       {config['num_aux_talons']}",
        f"Num I2C Talons:       {config['num_i2c_talons']}",
        f"Num SDI12 Talons:     {config['num_sdi12_talons']}",
    ]
    return "\n".join(lines)


def format_sensor_config(uid: int) -> str:
    """Format sensor configuration for display.

    Args:
        uid: The encoded sensor configuration UID

    Returns:
        Formatted string representation of the configuration
    """
    config = decode_sensor_configuration_uid(uid)
    lines = [
        f"Sensor Configuration UID: 0x{uid:08X} ({uid})",
        "=" * 50,
        f"Num ET Sensors:       {config['num_et']}",
        f"Num Haar Sensors:     {config['num_haar']}",
        f"Num Soil Sensors:     {config['num_soil']}",
        f"Num Apogee Solar:     {config['num_apogee_solar']}",
        f"Num CO2 Sensors:      {config['num_co2']}",
        f"Num O2 Sensors:       {config['num_o2']}",
        f"Num Pressure Sensors: {config['num_pressure']}",
    ]
    return "\n".join(lines)


def parse_uid(uid_str: str) -> int:
    """Parse UID from string, supporting both decimal and hexadecimal.

    Args:
        uid_str: UID string in decimal or hexadecimal format

    Returns:
        Parsed UID as integer

    Raises:
        ValueError: If UID format is invalid
    """
    try:
        if uid_str.lower().startswith("0x"):
            return int(uid_str, 16)
        else:
            return int(uid_str)
    except ValueError:
        raise ValueError(
            f"Invalid UID format: {uid_str}. Use decimal or hexadecimal (0x prefix)"
        )


def decode_both_configs(system_uid: int, sensor_uid: int) -> str:
    """Format both system and sensor configurations for display.

    Args:
        system_uid: The encoded system configuration UID
        sensor_uid: The encoded sensor configuration UID

    Returns:
        Formatted string representation of both configurations
    """
    system_output = format_system_config(system_uid)
    sensor_output = format_sensor_config(sensor_uid)
    return f"{system_output}\n\n{sensor_output}"
