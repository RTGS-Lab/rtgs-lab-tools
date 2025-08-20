"""Core SD card dumping functions for Particle devices."""

import binascii
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import serial
import serial.tools.list_ports
from tqdm import tqdm

from ..core.postgres_logger import PostgresLogger

logger = logging.getLogger(__name__)


class SDDumpError(Exception):
    """Custom exception for SD dump operations."""

    pass


def calculate_crc32(data: bytes) -> int:
    """Calculate CRC32 checksum."""
    return binascii.crc32(data) & 0xFFFFFFFF


def find_particle_device() -> Optional[str]:
    """Find connected Particle device serial port."""
    ports = serial.tools.list_ports.comports()

    for port in ports:
        # Look for common Particle device identifiers
        if any(
            keyword in (port.description or "").lower()
            for keyword in ["particle", "photon", "electron", "boron", "argon", "xenon"]
        ):
            return port.device

        # Check VID/PID for Particle devices
        if port.vid == 0x2B04:  # Particle VID
            return port.device

    return None


def clear_output_directory(output_dir: Path, logger_func: callable = None) -> bool:
    """Clear the output directory if it exists.

    Args:
        output_dir: Directory to clear
        logger_func: Optional logging function

    Returns:
        True if directory was cleared or didn't exist, False on error
    """

    def log(message: str):
        if logger_func:
            logger_func(message)
        else:
            logger.info(message)

    try:
        if output_dir.exists():
            if output_dir.is_dir():
                # Remove all contents
                for item in output_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                log(f"Cleared existing output directory: {output_dir}")
            else:
                # It's a file, not a directory
                output_dir.unlink()
                log(f"Removed existing file: {output_dir}")

        # Create the directory
        output_dir.mkdir(parents=True, exist_ok=True)
        return True

    except Exception as e:
        log(f"Error clearing output directory: {e}")
        return False


def wait_for_trigger_response(ser: serial.Serial, timeout: float = 60.0) -> bool:
    """Send trigger and wait for device to enter command mode."""
    start_time = time.time()
    device_output_seen = False
    trigger_sent = False

    logger.info("Waiting for device to boot...")
    logger.info("Power cycle the device now, or press reset button...")

    while (time.time() - start_time) < timeout:
        # Check for response
        while ser.in_waiting > 0:
            try:
                response = ser.readline().decode("utf-8", errors="ignore").strip()
                if response:
                    device_output_seen = True

                    if "Command Mode" in response or "Here be Dragons" in response:
                        logger.info("Device entered command mode successfully")
                        return True
            except:
                continue

        # Send trigger as soon as we see device output (early in boot)
        if device_output_seen and not trigger_sent:
            logger.info("Device booting detected, sending trigger...")
            # Send dual carriage returns to trigger command mode and clear buffer
            ser.write(b"\r\r")
            ser.flush()
            trigger_sent = True

        time.sleep(0.1)

    return False


def send_dump_command(ser: serial.Serial, recent_count: Optional[int] = None) -> bool:
    """Send the dump SD command."""
    if recent_count:
        logger.info(f"Sending 'Dump SD Recent {recent_count}' command...")
        command = f"Dump SD Recent {recent_count}\r"
        ser.write(command.encode())
    else:
        logger.info("Sending 'Dump SD' command...")
        ser.write(b"Dump SD\r")
    ser.flush()

    # Wait for acknowledgment
    start_time = time.time()
    command_echoed = False

    while (time.time() - start_time) < 10.0:
        if ser.in_waiting > 0:
            response = ser.readline().decode("utf-8", errors="ignore").strip()

            # Look for command echo first
            if response.startswith(">Dump SD"):
                command_echoed = True
                continue

            # Then look for actual start of dump
            if "SD_DUMP_START" in response:
                return True

            # Also accept if we see recent count (means dump started)
            if "RECENT_COUNT:" in response:
                return True

            # Accept if we see total files (means dump started)
            if "TOTAL_FILES:" in response:
                return True

        time.sleep(0.1)

    if command_echoed:
        logger.warning(
            "Command was acknowledged but SD dump didn't start within timeout"
        )

    return False


def receive_sd_dump(
    ser: serial.Serial, output_dir: Path, logger_func: callable = None
) -> Tuple[bool, dict]:
    """Receive and process SD dump data.

    Args:
        ser: Serial connection
        output_dir: Directory to save files
        logger_func: Optional logging function

    Returns:
        Tuple of (success, results_dict)
    """

    def log(message: str):
        if logger_func:
            logger_func(message)
        else:
            logger.info(message)

    progress_bar = None
    file_progress_bar = None
    current_file = None
    file_data = bytearray()
    files_processed = 0
    total_files = 0
    total_bytes_transferred = 0
    start_time = datetime.now()

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()

            if not line:
                continue

            if line.startswith("RECENT_COUNT:"):
                recent_count = int(line.split(":")[1])
                log(
                    f"Filtering files: only most recent {recent_count} files of each type"
                )

            elif line.startswith("TOTAL_FILES:"):
                total_files = int(line.split(":")[1])
                log(f"Total files to transfer: {total_files}")
                if progress_bar:
                    progress_bar.close()
                progress_bar = tqdm(total=total_files, desc="Files", unit="file")

            elif line.startswith("DIR_START:"):
                dir_path = line.split(":", 1)[1]
                log(f"Entering directory: {dir_path}")

            elif line.startswith("DIR_END:"):
                dir_path = line.split(":", 1)[1]
                log(f"Finished directory: {dir_path}")

            elif line.startswith("FILE_START:"):
                parts = line.split(":")
                full_path = parts[1]
                if "System Volume Information" in full_path:
                    log(f"Sanitizing protected path: {full_path}")
                    full_path = full_path.replace(
                        "System Volume Information", "_System Volume Information_"
                    )

                file_size = int(parts[2])
                total_chunks = int(parts[3])
                file_num = int(parts[4])

                # Create directory structure if needed
                # This robustly removes the leading slash on any OS
                relative_path_str = full_path.lstrip("/")
                file_path = Path(relative_path_str)

                output_file_path = output_dir / file_path
                output_file_path.parent.mkdir(parents=True, exist_ok=True)

                current_file = {
                    "name": full_path,
                    "local_path": output_file_path,
                    "size": file_size,
                    "data": bytearray(),
                    "chunks_received": 0,
                    "total_chunks": total_chunks,
                }

                log(
                    f"Starting file {file_num}/{total_files}: {full_path} ({file_size} bytes)"
                )

                if file_progress_bar:
                    file_progress_bar.close()
                file_progress_bar = tqdm(
                    total=total_chunks,
                    desc=f"Chunks ({file_path.name})",
                    unit="chunk",
                    leave=False,
                )

            elif line.startswith("CHUNK:"):
                if current_file is None:
                    continue

                try:
                    parts = line.split(":")
                    filename = parts[1]
                    chunk_num = int(parts[2])
                    total_chunks = int(parts[3])
                    data_length = int(parts[4])
                    chunk_crc_hex = parts[5]
                    hex_data = parts[6]

                    # Convert hex data back to bytes
                    chunk_data = bytes.fromhex(hex_data)

                    # Verify chunk CRC
                    calculated_crc = calculate_crc32(chunk_data)
                    expected_chunk_crc = int(chunk_crc_hex, 16)

                    if calculated_crc == expected_chunk_crc:
                        # Send ACK
                        ack_msg = f"ACK:{chunk_num}\n"
                        ser.write(ack_msg.encode())
                        ser.flush()

                        # Add data to file
                        current_file["data"].extend(chunk_data)
                        current_file["chunks_received"] += 1
                        total_bytes_transferred += len(chunk_data)

                        if file_progress_bar:
                            file_progress_bar.update(1)
                    else:
                        # Send NAK
                        nak_msg = f"NAK:{chunk_num}:CRC_MISMATCH\n"
                        ser.write(nak_msg.encode())
                        ser.flush()
                        log(f"CRC mismatch in chunk {chunk_num}")

                except (ValueError, IndexError) as e:
                    log(f"Error parsing chunk: {e}")
                    # Send NAK
                    nak_msg = f"NAK:0:PARSE_ERROR\n"
                    ser.write(nak_msg.encode())
                    ser.flush()

            elif line.startswith("FILE_END:"):
                if current_file is None:
                    continue

                parts = line.split(":")
                full_path = parts[1]
                file_crc_hex = parts[2]
                expected_file_crc = int(file_crc_hex, 16)

                # Verify complete file CRC
                calculated_file_crc = calculate_crc32(bytes(current_file["data"]))

                if calculated_file_crc == expected_file_crc:
                    # Write file to disk using the prepared path
                    with open(current_file["local_path"], "wb") as f:
                        f.write(current_file["data"])

                    log(
                        f"File saved: {current_file['local_path']} ({len(current_file['data'])} bytes)"
                    )
                else:
                    log(f"File CRC mismatch for '{full_path}' - file corrupted")

                files_processed += 1
                if progress_bar:
                    progress_bar.update(1)
                if file_progress_bar:
                    file_progress_bar.close()
                    file_progress_bar = None

                current_file = None

            elif line == "SD_DUMP_COMPLETE":
                log("SD dump completed successfully!")
                break

            elif line.startswith("ERROR:"):
                log(f"Device error: {line}")
                return False, {"error": line}

    except serial.SerialException as e:
        log(f"Serial communication error: {e}")
        return False, {"error": f"Serial communication error: {e}"}
    except KeyboardInterrupt:
        log("Operation cancelled by user")
        return False, {"error": "Operation cancelled by user"}
    except Exception as e:
        log(f"Unexpected error: {e}")
        return False, {"error": f"Unexpected error: {e}"}
    finally:
        if progress_bar:
            progress_bar.close()
        if file_progress_bar:
            file_progress_bar.close()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    results = {
        "success": True,
        "files_processed": files_processed,
        "total_files": total_files,
        "bytes_transferred": total_bytes_transferred,
        "duration": duration,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "output_directory": str(output_dir.absolute()),
    }

    return True, results


def dump_sd_card(
    port: Optional[str] = None,
    baudrate: int = 1000000,
    output_dir: str = "./sd_dump_output",
    timeout: int = 60,
    skip_trigger: bool = False,
    recent: Optional[int] = None,
    logger_func: Optional[callable] = None,
    auto_commit_postgres_log: bool = True,
    note: Optional[str] = None,
) -> Tuple[bool, dict]:
    """Dump SD card contents from Particle device over serial.

    Args:
        port: Serial port (auto-detected if None)
        baudrate: Serial baud rate
        output_dir: Output directory for files
        timeout: Connection timeout in seconds
        skip_trigger: Skip trigger phase (device already in command mode)
        recent: Only dump the most recent N files of each type
        logger_func: Optional logging function
        auto_commit_postgres_log: Whether to log to postgres
        note: Optional note for logging

    Returns:
        Tuple of (success, results_dict)
    """

    def log(message: str):
        if logger_func:
            logger_func(message)
        else:
            logger.info(message)

    # Initialize postgres logger
    postgres_logging_enabled = (
        os.getenv("POSTGRES_LOGGING_STATUS", "true").lower() == "true"
    )
    postgres_logger = (
        PostgresLogger("sd-dump")
        if auto_commit_postgres_log and postgres_logging_enabled
        else None
    )
    start_time = datetime.now()

    try:
        output_path = Path(output_dir)

        # Clear output directory if it exists
        if not clear_output_directory(output_path, logger_func):
            raise SDDumpError(f"Failed to clear output directory: {output_path}")

        # Auto-detect port if not specified
        if not port:
            port = find_particle_device()
            if not port:
                raise SDDumpError(
                    "No Particle device found. Please specify --port manually."
                )
            log(f"Auto-detected device on port: {port}")

        # Open serial connection
        log(f"Connecting to {port} at {baudrate} baud...")
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # Allow device to reset

        try:
            # Send trigger and wait for command mode (unless skipped)
            if not skip_trigger:
                if not wait_for_trigger_response(ser, timeout):
                    raise SDDumpError(
                        "Failed to enter command mode. Try using --skip-trigger if device is already in command mode, or power cycle the device."
                    )
            else:
                log("Skipping trigger phase - assuming device already in command mode")

            # Send dump command
            if not send_dump_command(ser, recent):
                raise SDDumpError("Failed to initiate SD dump command.")

            # Receive dump data
            log(f"Saving files to: {output_path.absolute()}")
            success, results = receive_sd_dump(ser, output_path, logger_func)

            if not success:
                raise SDDumpError(
                    f"SD dump failed: {results.get('error', 'Unknown error')}"
                )

            # Add note to results
            if note:
                results["note"] = note

            # Log execution to postgres if enabled
            if postgres_logger:
                try:
                    operation = f"SD Card Dump ({'recent ' + str(recent) if recent else 'all'} files)"
                    parameters = {
                        "port": port,
                        "baudrate": baudrate,
                        "output_dir": output_dir,
                        "timeout": timeout,
                        "skip_trigger": skip_trigger,
                        "recent": recent,
                    }
                    postgres_logger.log_execution(
                        operation=operation,
                        parameters=parameters,
                        results=results,
                        script_path=__file__,
                    )
                except Exception as e:
                    log(f"Failed to create postgres log: {e}")

            return True, results

        finally:
            ser.close()

    except Exception as e:
        # Prepare error results
        end_time = datetime.now()
        error_results = {
            "success": False,
            "error": str(e),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": (end_time - start_time).total_seconds(),
        }

        # Add note to results if provided
        if note:
            error_results["note"] = note

        # Log execution to postgres if enabled (even for failures)
        if postgres_logger:
            try:
                operation = f"SD Card Dump ({'recent ' + str(recent) if recent else 'all'} files) - FAILED"
                parameters = {
                    "port": port,
                    "baudrate": baudrate,
                    "output_dir": output_dir,
                    "timeout": timeout,
                    "skip_trigger": skip_trigger,
                    "recent": recent,
                }
                postgres_logger.log_execution(
                    operation=operation,
                    parameters=parameters,
                    results=error_results,
                    script_path=__file__,
                )
            except Exception as log_e:
                logger.warning(f"Failed to create postgres log for error: {log_e}")

        return False, error_results


def list_available_ports() -> list:
    """List all available serial ports with Particle device detection."""
    ports = serial.tools.list_ports.comports()

    port_info = []
    for port in ports:
        particle_device = port.vid == 0x2B04 or any(
            keyword in (port.description or "").lower()
            for keyword in ["particle", "photon", "electron", "boron", "argon", "xenon"]
        )

        port_info.append(
            {
                "device": port.device,
                "description": port.description or "Unknown",
                "is_particle": particle_device,
            }
        )

    return port_info


def send_write_command(ser: serial.Serial, filename: str) -> bool:
    """Send the write SD command."""
    logger.info(f"Sending 'Write SD {filename}' command...")
    command = f"Write SD {filename}\r"
    ser.write(command.encode())
    ser.flush()

    # Wait for acknowledgment and SD_WRITE_START
    start_time = time.time()
    command_echoed = False

    while (time.time() - start_time) < 10.0:
        if ser.in_waiting > 0:
            response = ser.readline().decode("utf-8", errors="ignore").strip()

            # Look for command echo first
            if response.startswith(f">Write SD {filename}"):
                command_echoed = True
                continue

            # Look for device ready to receive
            if "SD_WRITE_START" in response:
                return True

        time.sleep(0.1)

    if command_echoed:
        logger.warning(
            "Command was acknowledged but SD write didn't start within timeout"
        )

    return False


def send_file_over_serial(
    ser: serial.Serial, file_path: Path, filename: str, logger_func: callable = None
) -> Tuple[bool, dict]:
    """Send a file to the device over serial.

    Args:
        ser: Serial connection
        file_path: Path to local file to send
        filename: Filename to save on device SD card
        logger_func: Optional logging function

    Returns:
        Tuple of (success, results_dict)
    """

    def log(message: str):
        if logger_func:
            logger_func(message)
        else:
            logger.info(message)

    try:
        # Read file data
        with open(file_path, "rb") as f:
            file_data = f.read()

        file_size = len(file_data)
        chunk_size = 512
        total_chunks = (file_size + chunk_size - 1) // chunk_size  # Ceiling division

        log(f"Sending file: {file_path} ({file_size} bytes, {total_chunks} chunks)")

        # Send ACK to device's SD_WRITE_START
        ser.write(b"ACK\n")
        ser.flush()

        # Wait for SD_WRITE_READY
        start_time = time.time()
        while (time.time() - start_time) < 10.0:
            if ser.in_waiting > 0:
                response = ser.readline().decode("utf-8", errors="ignore").strip()
                log(f"Device response: {response}")
                if response.startswith("SD_WRITE_READY:"):
                    break
        else:
            return False, {"error": "Device did not send SD_WRITE_READY"}

        # Send file info
        file_info = f"FILE_INFO:{filename}:{file_size}:{total_chunks}\n"
        log(f"Sending: {file_info.strip()}")
        ser.write(file_info.encode())
        ser.flush()

        # Wait for FILE_INFO_ACK
        start_time = time.time()
        while (time.time() - start_time) < 10.0:
            if ser.in_waiting > 0:
                response = ser.readline().decode("utf-8", errors="ignore").strip()
                log(f"Device response: {response}")
                if response.startswith("FILE_INFO_ACK:"):
                    break
        else:
            return False, {"error": "Device did not acknowledge file info"}

        # Wait for READY_FOR_CHUNKS
        start_time = time.time()
        while (time.time() - start_time) < 10.0:
            if ser.in_waiting > 0:
                response = ser.readline().decode("utf-8", errors="ignore").strip()
                log(f"Device response: {response}")
                if response == "READY_FOR_CHUNKS":
                    break
        else:
            return False, {"error": "Device not ready for chunks"}

        # Send file in chunks with progress bar
        progress_bar = tqdm(
            total=total_chunks, desc=f"Uploading {filename}", unit="chunk"
        )
        bytes_sent = 0

        try:
            for chunk_num in range(1, total_chunks + 1):
                start_pos = (chunk_num - 1) * chunk_size
                end_pos = min(start_pos + chunk_size, file_size)
                chunk_data = file_data[start_pos:end_pos]
                chunk_length = len(chunk_data)

                # Calculate CRC for chunk
                chunk_crc = calculate_crc32(chunk_data)

                # Convert to hex
                hex_data = chunk_data.hex().upper()

                # Send chunk
                chunk_msg = f"CHUNK:{filename}:{chunk_num}:{total_chunks}:{chunk_length}:{chunk_crc:08X}:{hex_data}\n"
                ser.write(chunk_msg.encode())
                ser.flush()

                # Wait for ACK/NAK with retry logic
                retry_count = 0
                max_retries = 3

                while retry_count < max_retries:
                    start_time = time.time()
                    ack_received = False

                    while (
                        time.time() - start_time
                    ) < 30.0:  # 30 second timeout per chunk
                        if ser.in_waiting > 0:
                            response = (
                                ser.readline().decode("utf-8", errors="ignore").strip()
                            )

                            if response.startswith(f"ACK:{chunk_num}"):
                                ack_received = True
                                bytes_sent += chunk_length
                                progress_bar.update(1)
                                break
                            elif response.startswith(f"NAK:{chunk_num}"):
                                log(f"NAK received for chunk {chunk_num}, retrying...")
                                retry_count += 1
                                break
                            elif response.startswith("PROGRESS:"):
                                # Device sending progress updates
                                continue
                            elif response.startswith("ERROR:"):
                                return False, {"error": f"Device error: {response}"}

                    if ack_received:
                        break
                    else:
                        retry_count += 1
                        if retry_count < max_retries:
                            log(
                                f"Timeout waiting for ACK on chunk {chunk_num}, retrying..."
                            )
                            # Resend the chunk
                            ser.write(chunk_msg.encode())
                            ser.flush()

                if retry_count >= max_retries:
                    return False, {
                        "error": f"Failed to send chunk {chunk_num} after {max_retries} attempts"
                    }

            # Wait for completion message
            start_time = time.time()
            while (time.time() - start_time) < 30.0:
                if ser.in_waiting > 0:
                    response = ser.readline().decode("utf-8", errors="ignore").strip()
                    if response.startswith("SD_WRITE_COMPLETE:"):
                        log("File upload completed successfully!")
                        return True, {
                            "success": True,
                            "filename": filename,
                            "bytes_sent": bytes_sent,
                            "chunks_sent": total_chunks,
                        }
                    elif response.startswith("ERROR:"):
                        return False, {"error": f"Device error: {response}"}

            return False, {"error": "Timeout waiting for completion message"}

        finally:
            progress_bar.close()

    except Exception as e:
        return False, {"error": f"Upload error: {str(e)}"}


def write_file_to_sd(
    file_path: str,
    filename: Optional[str] = None,
    port: Optional[str] = None,
    baudrate: int = 1000000,
    timeout: int = 60,
    skip_trigger: bool = False,
    logger_func: Optional[callable] = None,
    auto_commit_postgres_log: bool = True,
    note: Optional[str] = None,
) -> Tuple[bool, dict]:
    """Write a file to SD card on Particle device over serial.

    Args:
        file_path: Path to local file to upload
        filename: Filename to save on device (defaults to original filename)
        port: Serial port (auto-detected if None)
        baudrate: Serial baud rate
        timeout: Connection timeout in seconds
        skip_trigger: Skip trigger phase (device already in command mode)
        logger_func: Optional logging function
        auto_commit_postgres_log: Whether to log to postgres
        note: Optional note for logging

    Returns:
        Tuple of (success, results_dict)
    """

    def log(message: str):
        if logger_func:
            logger_func(message)
        else:
            logger.info(message)

    # Initialize postgres logger
    postgres_logging_enabled = (
        os.getenv("POSTGRES_LOGGING_STATUS", "true").lower() == "true"
    )
    postgres_logger = (
        PostgresLogger("sd-dump")
        if auto_commit_postgres_log and postgres_logging_enabled
        else None
    )
    start_time = datetime.now()

    try:
        input_path = Path(file_path)
        if not input_path.exists():
            raise SDDumpError(f"File not found: {file_path}")

        if not filename:
            filename = input_path.name

        # Auto-detect port if not specified
        if not port:
            port = find_particle_device()
            if not port:
                raise SDDumpError(
                    "No Particle device found. Please specify --port manually."
                )
            log(f"Auto-detected device on port: {port}")

        # Open serial connection
        log(f"Connecting to {port} at {baudrate} baud...")
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # Allow device to reset

        try:
            # Send trigger and wait for command mode (unless skipped)
            if not skip_trigger:
                if not wait_for_trigger_response(ser, timeout):
                    raise SDDumpError(
                        "Failed to enter command mode. Try using --skip-trigger if device is already in command mode, or power cycle the device."
                    )
            else:
                log("Skipping trigger phase - assuming device already in command mode")

            # Send write command
            if not send_write_command(ser, filename):
                raise SDDumpError("Failed to initiate SD write command.")

            # Send the file
            log(f"Uploading file: {input_path} -> {filename}")
            success, results = send_file_over_serial(
                ser, input_path, filename, logger_func
            )

            if not success:
                raise SDDumpError(
                    f"SD write failed: {results.get('error', 'Unknown error')}"
                )

            # Add note to results
            if note:
                results["note"] = note

            # Add timing info
            end_time = datetime.now()
            results.update(
                {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": (end_time - start_time).total_seconds(),
                    "input_file": str(input_path),
                    "device_filename": filename,
                }
            )

            # Log execution to postgres if enabled
            if postgres_logger:
                try:
                    operation = f"SD Card Write: {filename}"
                    parameters = {
                        "file_path": file_path,
                        "filename": filename,
                        "port": port,
                        "baudrate": baudrate,
                        "timeout": timeout,
                        "skip_trigger": skip_trigger,
                    }
                    postgres_logger.log_execution(
                        operation=operation,
                        parameters=parameters,
                        results=results,
                        script_path=__file__,
                    )
                except Exception as e:
                    log(f"Failed to create postgres log: {e}")

            return True, results

        finally:
            ser.close()

    except Exception as e:
        # Prepare error results
        end_time = datetime.now()
        error_results = {
            "success": False,
            "error": str(e),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": (end_time - start_time).total_seconds(),
        }

        # Add note to results if provided
        if note:
            error_results["note"] = note

        # Log execution to postgres if enabled (even for failures)
        if postgres_logger:
            try:
                operation = f"SD Card Write: {filename or 'unknown'} - FAILED"
                parameters = {
                    "file_path": file_path,
                    "filename": filename,
                    "port": port,
                    "baudrate": baudrate,
                    "timeout": timeout,
                    "skip_trigger": skip_trigger,
                }
                postgres_logger.log_execution(
                    operation=operation,
                    parameters=parameters,
                    results=error_results,
                    script_path=__file__,
                )
            except Exception as log_e:
                logger.warning(f"Failed to create postgres log for error: {log_e}")

        return False, error_results
