# SD Dump Module

This module provides tools for both reading from and writing to SD cards on Particle devices over serial communication with CRC verification. The module follows the standard rtgs-lab-tools architecture with a `core.py` module containing the main functionality and a thin CLI wrapper.

### Complete Workflow

1. Connect Particle device to computer via USB with switch turned off.
2. Power the device on with the switch.
2. Run the dump command quickly after power-on:
   ```bash
   rtgs sd-dump dump --recent 3
   ```
3. Tool will:
   - Auto-detect the device
   - Send trigger to enter command mode
   - Download all files with integrity verification
   - Save files to specified directory
   - Report progress and completion status

The most common commands are:
```bash
rtgs sd-dump dump                # Dump all files from device SD card
rtgs sd-dump dump --recent 3     # Dump only the most recent 3 files of each type
rtgs sd-dump dump --recent 3 --skip-trigger  # Dump recent files if already in command mode
rtgs sd-dump write <filepath>    # Upload config.json to device SD card
rtgs sd-dump write <filepath> --skip-trigger  # Upload if already in command mode
```


### Troubleshooting

**Already in command mode: (if the lights on the device are already slow blinking)**
```bash
rtgs sd-dump dump --skip-trigger
```

**Slow loading or hangs during detection:**
- cancel the operation with Ctrl+C and try again

**Device not detected:**
```bash
rtgs sd-dump list-ports
rtgs sd-dump dump --port /dev/ttyUSB0
```

**Upload configuration file:**
```bash
rtgs sd-dump write config.json
```

**Recent files only:**
```bash
rtgs sd-dump dump --recent 5
```

**Different baud rate:**
```bash
rtgs sd-dump dump --baudrate 115200
rtgs sd-dump write config.json --baudrate 115200
```

## Features

- **Auto-detection** of Particle devices on serial ports
- **Bidirectional file transfer**: Download (dump) and upload (write) files
- **Recursive directory traversal** - preserves complete folder structure when dumping
- **CRC32 verification** for data integrity in both directions
- **Chunk-based transfer** with automatic retry logic
- **Modern progress tracking** with tqdm progress bars
- **Integrated logging** using standard rtgs-lab-tools logging system
- **Robust error handling** and recovery
- **Recent files filtering** based on numbered file convention
- **Configuration file uploading** - perfect for updating device config.json

## Usage

### SD Card Dump (Download Files)

```bash
# Auto-detect device and dump SD contents
rtgs sd-dump dump

# Specify custom output directory
rtgs sd-dump dump --output-dir ./my_sd_backup

# Use specific serial port
rtgs sd-dump dump --port /dev/ttyUSB0

# Only dump recent 3 files of each type (data, error, diag, meta)
rtgs sd-dump dump --recent 3

# Verbose output with logging
rtgs sd-dump dump --verbose

# Skip device trigger (device already in command mode)
rtgs sd-dump dump --skip-trigger
```

### SD Card Write (Upload Files)

```bash
# Upload config.json to device SD card root directory
rtgs sd-dump write config.json

# Upload with custom filename on device
rtgs sd-dump write local_config.json --filename config.json

# Use specific serial port
rtgs sd-dump write config.json --port /dev/ttyUSB0

# Skip device trigger (device already in command mode)
rtgs sd-dump write config.json --skip-trigger

# Verbose output with logging
rtgs sd-dump write config.json --verbose
```

### List Available Ports

```bash
rtgs sd-dump list-ports
```

## Protocol

The module implements a robust serial communication protocol for both directions:

### SD Dump Protocol (Device → Host)

**Message Format:**
1. **Directory Start**: `DIR_START:<dir_path>`
2. **Directory End**: `DIR_END:<dir_path>`
3. **File Start**: `FILE_START:<full_path>:<size>:<chunks>:<file_num>:<total_files>`
4. **Chunk Data**: `CHUNK:<full_path>:<chunk_num>:<total_chunks>:<length>:<crc32>:<hex_data>`
5. **File End**: `FILE_END:<full_path>:<file_crc32>`
6. **Acknowledgment**: `ACK:<chunk_num>` or `NAK:<chunk_num>:<reason>`

**Data Flow:**

1. Host sends trigger word repeatedly until device enters command mode
2. Host sends "Dump SD" command
3. Device responds with total file count  
4. Device recursively traverses all directories:
   - Device sends DIR_START when entering a directory
   - For each file in directory:
     - Device sends FILE_START message with full path
     - Device sends file data in chunks with CRC
     - Host verifies each chunk CRC and sends ACK/NAK
     - Device retries failed chunks up to 3 times
     - Device sends FILE_END with complete file CRC
     - Host creates directory structure and saves file
   - Device sends DIR_END when leaving directory
5. Device sends SD_DUMP_COMPLETE when finished

### SD Write Protocol (Host → Device)

**Message Format:**
1. **Write Start**: `SD_WRITE_START` (device sends after receiving "Write SD filename" command)
2. **Ready Signal**: `SD_WRITE_READY:<filename>` (device ready to receive)
3. **File Info**: `FILE_INFO:<filename>:<filesize>:<total_chunks>` (host sends file metadata)
4. **Info Ack**: `FILE_INFO_ACK:<filesize>:<total_chunks>` (device acknowledges)
5. **Ready for Chunks**: `READY_FOR_CHUNKS` (device ready to receive file data)
6. **Chunk Data**: `CHUNK:<filename>:<chunk_num>:<total_chunks>:<length>:<crc32>:<hex_data>` (host sends)
7. **Acknowledgment**: `ACK:<chunk_num>` or `NAK:<chunk_num>:<reason>` (device responds)
8. **Completion**: `SD_WRITE_COMPLETE:<filename>:<bytes> bytes` (device confirms success)

**Data Flow:**
1. Host sends trigger word repeatedly until device enters command mode
2. Host sends "Write SD filename" command
3. Device responds with SD_WRITE_START
4. Host sends ACK, device responds with SD_WRITE_READY
5. Host sends FILE_INFO with file metadata
6. Device acknowledges with FILE_INFO_ACK
7. Device sends READY_FOR_CHUNKS
8. Host sends file data in chunks with CRC verification
9. Device verifies each chunk CRC and sends ACK/NAK
10. Device retries failed chunks up to 3 times
11. Device writes file to SD card root directory
12. Device sends SD_WRITE_COMPLETE when finished

## Firmware Requirements

The Particle device must be running firmware with both `dumpSDOverSerial()` and `writeFileOverSerial()` functions implemented in the KestrelFileHandler class. This means the device must be v40 or greater to ensure compatibility

### Required Firmware Commands

- **"Dump SD"**: Triggers `dumpSDOverSerial()` to send all files
- **"Dump SD Recent N"**: Triggers `dumpSDOverSerial(N)` to send recent N files of each type
- **"Write SD filename"**: Triggers `writeFileOverSerial(filename)` to receive a file

### Required Firmware Features

- Command mode entry on serial activity during startup
- SD card file enumeration, reading, and writing
- CRC32 calculation for chunks and complete files
- Chunk-based transmission with retry logic in both directions
- Progress reporting for uploads and downloads
- File creation in SD card root directory

## Error Handling

The tool handles various error conditions:

- **Serial communication errors**: Automatic reconnection attempts
- **CRC mismatches**: Automatic chunk retransmission
- **Device not found**: Clear error messages with suggestions
- **File system errors**: Graceful handling and reporting
- **User interruption**: Clean shutdown with Ctrl+C

## Configuration Options

- `--port`: Specify serial port (auto-detected by default)
- `--baudrate`: Serial communication speed (default: 1000000)
- `--output-dir`: Directory to save files (default: "./sd_dump_output")
- `--timeout`: Connection timeout in seconds (default: 60)
- `--skip-trigger`: Skip trigger phase (device already in command mode)
- `--recent N`: Only dump the most recent N files of each type
- `--verbose`: Enable verbose logging output
- `--log-file`: Log to file instead of console
- `--note`: Add note describing the operation purpose

## Examples

### Complete Workflow

1. Connect Particle device to computer via USB with switch turned off.
2. Power the device on with the switch.
2. Run the dump command quickly after power-on:
   ```bash
   rtgs sd-dump dump --output-dir /home/user/particle_backup
   ```
3. Tool will:
   - Auto-detect the device
   - Send trigger to enter command mode
   - Download all files with integrity verification
   - Save files to specified directory
   - Report progress and completion status

### Troubleshooting

**Device not detected:**
```bash
rtgs sd-dump list-ports
rtgs sd-dump dump --port /dev/ttyUSB0
```

**Upload configuration file:**
```bash
rtgs sd-dump write config.json
```

**Recent files only:**
```bash
rtgs sd-dump dump --recent 5
```

**Different baud rate:**
```bash
rtgs sd-dump dump --baudrate 115200
rtgs sd-dump write config.json --baudrate 115200
```

## Integration

This module integrates seamlessly with the RTGS Lab Tools ecosystem and can be used alongside other modules for comprehensive device management and data analysis workflows.