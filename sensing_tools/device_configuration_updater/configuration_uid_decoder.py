#!/usr/bin/env python3
"""
UID Decoder Command Line Tool

Decodes system and sensor configuration UIDs from ConfigurationManager.

Usage:
    python uid_decoder.py system <uid>
    python uid_decoder.py sensor <uid>
    python uid_decoder.py both <system_uid> <sensor_uid>
    
UID can be provided in decimal or hexadecimal format (with 0x prefix).
"""

import argparse
import sys

def decode_system_configuration_uid(uid):
    """
    Decode the system configuration UID created by updateSystemConfigurationUid()
    
    Args:
        uid (int): The encoded system configuration UID
        
    Returns:
        dict: Dictionary containing decoded configuration values
    """
    config = {}
    
    # Extract each field using bit masks and shifts
    config['log_period'] = (uid >> 16) & 0xFFFF          # Upper 16 bits
    config['backhaul_count'] = (uid >> 12) & 0xF         # 4 bits at position 12-15
    config['power_save_mode'] = (uid >> 10) & 0x3        # 2 bits at position 10-11
    config['logging_mode'] = (uid >> 8) & 0x3            # 2 bits at position 8-9
    config['num_aux_talons'] = (uid >> 6) & 0x3          # 2 bits at position 6-7
    config['num_i2c_talons'] = (uid >> 4) & 0x3          # 2 bits at position 4-5
    config['num_sdi12_talons'] = (uid >> 2) & 0x3        # 2 bits at position 2-3
    
    return config

def decode_sensor_configuration_uid(uid):
    """
    Decode the sensor configuration UID created by updateSensorConfigurationUid()
    
    Args:
        uid (int): The encoded sensor configuration UID
        
    Returns:
        dict: Dictionary containing decoded sensor counts
    """
    config = {}
    
    # Extract each field using bit masks and shifts
    config['num_et'] = (uid >> 28) & 0xF                 # 4 bits at position 28-31
    config['num_haar'] = (uid >> 24) & 0xF               # 4 bits at position 24-27
    config['num_soil'] = (uid >> 20) & 0xF               # 4 bits at position 20-23
    config['num_apogee_solar'] = (uid >> 16) & 0xF       # 4 bits at position 16-19
    config['num_co2'] = (uid >> 12) & 0xF                # 4 bits at position 12-15
    config['num_o2'] = (uid >> 8) & 0xF                  # 4 bits at position 8-11
    config['num_pressure'] = (uid >> 4) & 0xF            # 4 bits at position 4-7
    
    return config

def print_system_config(uid):
    """Pretty print system configuration"""
    config = decode_system_configuration_uid(uid)
    print(f"System Configuration UID: 0x{uid:08X} ({uid})")
    print("=" * 50)
    print(f"Log Period:           {config['log_period']}")
    print(f"Backhaul Count:       {config['backhaul_count']}")
    print(f"Power Save Mode:      {config['power_save_mode']}")
    print(f"Logging Mode:         {config['logging_mode']}")
    print(f"Num Aux Talons:       {config['num_aux_talons']}")
    print(f"Num I2C Talons:       {config['num_i2c_talons']}")
    print(f"Num SDI12 Talons:     {config['num_sdi12_talons']}")

def print_sensor_config(uid):
    """Pretty print sensor configuration"""
    config = decode_sensor_configuration_uid(uid)
    print(f"Sensor Configuration UID: 0x{uid:08X} ({uid})")
    print("=" * 50)
    print(f"Num ET Sensors:       {config['num_et']}")
    print(f"Num Haar Sensors:     {config['num_haar']}")
    print(f"Num Soil Sensors:     {config['num_soil']}")
    print(f"Num Apogee Solar:     {config['num_apogee_solar']}")
    print(f"Num CO2 Sensors:      {config['num_co2']}")
    print(f"Num O2 Sensors:       {config['num_o2']}")
    print(f"Num Pressure Sensors: {config['num_pressure']}")

def parse_uid(uid_str):
    """Parse UID from string, supporting both decimal and hexadecimal"""
    try:
        if uid_str.lower().startswith('0x'):
            return int(uid_str, 16)
        else:
            return int(uid_str)
    except ValueError:
        raise ValueError(f"Invalid UID format: {uid_str}. Use decimal or hexadecimal (0x prefix)")

def main():
    parser = argparse.ArgumentParser(
        description='Decode ConfigurationManager UIDs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s system 0x12345678
  %(prog)s sensor 305419896
  %(prog)s both 0x12345678 0xABCDEF12
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # System command
    system_parser = subparsers.add_parser('system', help='Decode system configuration UID')
    system_parser.add_argument('uid', help='System configuration UID (decimal or 0x hex)')
    
    # Sensor command
    sensor_parser = subparsers.add_parser('sensor', help='Decode sensor configuration UID')
    sensor_parser.add_argument('uid', help='Sensor configuration UID (decimal or 0x hex)')
    
    # Both command
    both_parser = subparsers.add_parser('both', help='Decode both system and sensor UIDs')
    both_parser.add_argument('system_uid', help='System configuration UID (decimal or 0x hex)')
    both_parser.add_argument('sensor_uid', help='Sensor configuration UID (decimal or 0x hex)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'system':
            uid = parse_uid(args.uid)
            print_system_config(uid)
            
        elif args.command == 'sensor':
            uid = parse_uid(args.uid)
            print_sensor_config(uid)
            
        elif args.command == 'both':
            system_uid = parse_uid(args.system_uid)
            sensor_uid = parse_uid(args.sensor_uid)
            print_system_config(system_uid)
            print("\n")
            print_sensor_config(sensor_uid)
            
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()