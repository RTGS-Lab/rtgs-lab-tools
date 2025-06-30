# RTGS Lab Tools - Technical Specification

## Overview

RTGS Lab Tools is a comprehensive Python package for environmental sensing data analysis, gridded climate data access, IoT device management, and data visualization. This document provides detailed technical specifications for each tool module, including input/output requirements, data formats, and API interfaces.

## System Architecture

```
rtgs-lab-tools/
├── Core Infrastructure
│   ├── Database Management (PostgreSQL)
│   ├── Configuration Management (.env)
│   ├── Git Logging (Automated audit trails)
│   └── CLI Framework (Click-based)
├── Tool Modules
│   ├── Sensing Data Extraction
│   ├── Visualization & Plotting
│   ├── Gridded Climate Data (ERA5)
│   ├── Device Configuration Management
│   ├── Error Analysis & Diagnostics
│   └── Agricultural Modeling
└── Interfaces
    ├── Command Line Interface (CLI)
    ├── MCP Server (Natural Language)
    └── Python API
```

## Common Infrastructure

### CLI Framework
All tools share common CLI parameters and error handling:

#### Common Parameters
- `--verbose, -v`: Enable verbose (DEBUG) logging
- `--log-file`: Specify log file path
- `--no-git-log`: Disable automatic git logging
- `--note`: Descriptive note for operation tracking

#### Error Handling
- **ConfigError**: Configuration/credentials issues
- **DatabaseError**: Database connection/query failures
- **APIError**: External API communication failures
- **ValidationError**: Input data validation failures

### Git Logging
All operations are automatically logged to a dedicated `logs` branch for audit trails and reproducibility.

## Tool Module Specifications

### 1. Sensing Data Extraction (`sensing-data`)

#### Purpose
Extract and export environmental sensor data from the GEMS PostgreSQL database.

#### CLI Commands

##### `rtgs sensing-data extract`

**Input Requirements:**
- **Project name** (required): String matching database project names
- **Start date** (optional): YYYY-MM-DD format, defaults to 2018-01-01
- **End date** (optional): YYYY-MM-DD format, defaults to today
- **Node IDs** (optional): Comma-separated list of specific sensor nodes
- **Output format** (optional): "csv" or "parquet", defaults to "csv"
- **Output directory** (optional): Target directory, defaults to "./data"

**Parameters:**
```bash
--project, -p TEXT          Project name to query [required]
--start-date TEXT           Start date (YYYY-MM-DD) [default: 2018-01-01]
--end-date TEXT             End date (YYYY-MM-DD) [default: today]
--node-id TEXT              Comma-separated list of node IDs
--output-dir TEXT           Output directory [default: ./data]
--output [csv|parquet]      Output format [default: csv]
--create-zip                Create zip archive with metadata
--retry-count INTEGER       Maximum retry attempts [default: 3]
```

**Output Files:**
- **Data File**: `ProjectName_YYYY-MM-DD_to_YYYY-MM-DD_YYYYMMDDHHMMSS.{csv|parquet}`
- **Metadata File**: `ProjectName_YYYY-MM-DD_to_YYYY-MM-DD_YYYYMMDDHHMMSS_metadata.json`
- **Zip Archive** (optional): Contains data file, metadata, and SHA-256 checksums

**Data Schema:**
```
Columns: id, node_id, publish_time, ingest_time, event, message,message_id
```

**Return Values:**
```python
{
    "success": bool,
    "records_extracted": int,
    "output_file": str,
    "zip_file": str | None,
    "metadata": dict
}
```

##### `rtgs sensing-data list-projects`

**Output:** List of all available projects with node counts

### 2. Visualization (`visualization`)

#### Purpose
Create time-series plots and multi-parameter visualizations from sensor data.

#### CLI Commands

##### `rtgs visualization create`

**Input Requirements:**
- **Data file** (required): CSV file with sensor data
- **Parameter specification**: Either single parameter or multi-parameter mode
- **Output format**: PNG, PDF, or SVG

**Parameters:**
```bash
--file, -f PATH                    CSV file with sensor data [required]
--parameter, -p TEXT               Parameter path (e.g., "Data.Devices.0.Temperature")
--node-id TEXT                     Specific node ID for single parameter plots
--multi-param TEXT                 Multiple parameters as "node_id,parameter_path" (can be repeated)
--output-dir TEXT                  Output directory [default: figures]
--output-file TEXT                 Output filename (without extension)
--format [png|pdf|svg]             Output format [default: png]
--title TEXT                       Plot title
--list-params                      List available parameters and exit
--no-markers                       Disable data point markers
```

**Input Data Format:**
- CSV file with columns: `publish_time`, `device_id`, `message`, `node_id`
- JSON messages in `message` column containing nested sensor data

**Parameter Path Format:**
- Dot-notation for nested JSON fields: `"Data.Devices.0.Temperature"`
- Multi-parameter format: `"node_id,Data.Devices.0.Temperature"`

**Output Files:**
- **Plot File**: `{output_file}.{format}` or auto-generated name
- **Format**: PNG (default), PDF, or SVG

**Return Values:**
```python
{
    "success": bool,
    "output_file": str,
    "records_processed": int,
    "parameters_plotted": list
}
```

##### `rtgs visualization list-parameters`

**Input:** CSV file path
**Output:** Hierarchical list of available parameters by node

### 3. Gridded Climate Data (`gridded-data`)

#### Purpose
Download and process ERA5 climate reanalysis data from Copernicus Climate Data Store.

#### CLI Commands

##### `rtgs gridded-data era5`

**Input Requirements:**
- **Variables** (required): List of ERA5 variable names
- **Date range** (required): Start and end dates
- **Geographic bounds** (optional): Bounding box coordinates
- **API credentials**: CDS API key in .env file

**Parameters:**
```bash
--variables, -v TEXT            ERA5 variables to download [required, multiple]
--start-date TEXT               Start date (YYYY-MM-DD) [required]
--end-date TEXT                 End date (YYYY-MM-DD) [required]
--area TEXT                     Bounding box as "north,west,south,east"
--output-file, -o TEXT          Output NetCDF file path
--pressure-levels TEXT          Pressure levels (comma-separated)
--time-hours TEXT               Specific hours (comma-separated, e.g., "00:00,12:00")
--list-variables                List available variables and exit
--process                       Process downloaded data (basic statistics)
```

**Variable Examples:**
- Surface: `2m_temperature`, `total_precipitation`, `10m_u_component_of_wind`
- Pressure levels: `temperature`, `geopotential`, `relative_humidity`

**Area Format:** `"north,west,south,east"` (e.g., `"45,-94,44,-93"`)

**Output Files:**
- **NetCDF File**: ERA5 data in NetCDF4 format
- **Processed File** (optional): `{filename}.processed.nc`

**Data Schema:**
```
Dimensions: time, latitude, longitude, [level]
Variables:  Selected ERA5 variables with metadata
Format:     NetCDF4 with CF conventions
```

**Return Values:**
```python
{
    "success": bool,
    "output_file": str,
    "variables": list,
    "time_range": tuple,
    "spatial_extent": dict
}
```

##### `rtgs gridded-data list-variables`

**Output:** Comprehensive list of available ERA5 variables by category

### 4. Device Configuration (`device-configuration`)

#### Purpose
Manage configuration updates for Particle IoT devices with batch operations and monitoring.

#### CLI Commands

##### `rtgs device-configuration update-config`

**Input Requirements:**
- **Configuration data**: JSON file or JSON string
- **Device list**: File with device IDs or comma-separated string
- **Particle API access**: Token in .env file

**Parameters:**
```bash
--config TEXT                    Path to configuration JSON file OR JSON string [required]
--devices TEXT                   Path to device list file OR comma/space separated device IDs [required]
--output TEXT                    Output file for results [default: update_results.json]
--max-retries INTEGER            Maximum retry attempts per device [default: 3]
--restart-wait INTEGER           Seconds to wait for device restart [default: 30]
--online-timeout INTEGER         Seconds to wait for device to come online [default: 120]
--max-concurrent INTEGER         Maximum concurrent devices to process [default: 5]
--dry-run                        Validate inputs without making changes
--no-particle-git-log            Disable Particle-specific git logging
```

**Configuration Format:**
```json
{
    "system": {
        "sampleRate": 300,
        "transmitRate": 900
    },
    "sensors": {
        "temperature": {"enabled": true},
        "humidity": {"enabled": true}
    }
}
```

**Device List Format:**
- Text file: One device ID per line
- Command line: Comma or space separated IDs

**Output Files:**
- **Results File**: JSON with success/failure details per device
- **Git Log**: Automatic commit with operation details

**Return Values:**
```python
{
    "summary": {
        "total_devices": int,
        "successful": int,
        "failed": int,
        "expected_system_uid": str,
        "expected_sensor_uid": str
    },
    "device_results": [
        {
            "device_id": str,
            "success": bool,
            "system_uid": str,
            "sensor_uid": str,
            "error": str | None
        }
    ]
}
```

##### UID Decoding Commands

**`rtgs device-configuration decode-system UID`**
- Input: System configuration UID (hex or decimal)
- Output: Decoded system configuration details

**`rtgs device-configuration decode-sensor UID`**
- Input: Sensor configuration UID (hex or decimal)
- Output: Decoded sensor configuration details

**`rtgs device-configuration decode-both SYSTEM_UID SENSOR_UID`**
- Input: Both system and sensor UIDs
- Output: Combined configuration analysis

### 5. Error Analysis (`error-analysis`)

#### Purpose
Parse, analyze, and visualize error codes from GEMS device data with pattern recognition.

#### CLI Commands

##### `rtgs error-analysis analyze`

**Input Requirements:**
- **Data file**: CSV or JSON file containing error data
- **Error column**: Column name containing error codes/messages
- **Node filtering** (optional): Specific nodes to analyze

**Parameters:**
```bash
--file, -f PATH                CSV or JSON file with error data [required]
--error-column TEXT            Column containing error data [default: message]
--generate-graph               Generate error frequency graphs
--nodes TEXT                   Comma-separated list of node IDs to analyze
--output-dir TEXT              Output directory for plots [default: figures]
--output-analysis TEXT         Save analysis results to JSON file
```

**Input Data Format:**
- CSV/JSON with error codes in specified column
- Supported formats: Hex codes (0xF00C), decimal, or embedded in JSON messages

**Error Code Structure:**
```
Format: 0xABCD
A: Error Class (0-F)
B: Hardware Device (0-F)
C: Hardware Sub-device (0-F)
D: Specific Error Code (0-F)
```

**Output Files:**
- **Error frequency plots**: PNG files by node and overall
- **Analysis JSON**: Detailed error statistics and patterns
- **Enhanced analysis**: Error translations and categorization

**Return Values:**
```python
{
    "total_errors": int,
    "unique_error_codes": int,
    "error_breakdown": dict,
    "temporal_patterns": dict,
    "node_analysis": dict,
    "plot_files": list
}
```

##### `rtgs error-analysis decode ERROR_CODE`

**Input:** Single hex error code (e.g., "0xF00C" or "F00C")
**Output:** Detailed error code breakdown with descriptions

### 6. Agricultural Modeling (`agricultural-modeling`)

#### Purpose
Agricultural calculations, unit conversions, and crop modeling tools.

#### CLI Command Groups

##### Temperature Conversions
```bash
rtgs agricultural-modeling temperature celsius-to-fahrenheit VALUE
rtgs agricultural-modeling temperature fahrenheit-to-celsius VALUE
```

##### Distance & Speed Conversions
```bash
rtgs agricultural-modeling distance feet-to-meters VALUE
rtgs agricultural-modeling distance degrees-to-radians VALUE
rtgs agricultural-modeling speed ms-to-mph VALUE
rtgs agricultural-modeling speed mph-to-ms VALUE
```

##### Crop Calculations

**`rtgs agricultural-modeling crops parameters`**
- **Input:** Optional crop name
- **Output:** Crop parameters for GDD calculations or list of all crops

**`rtgs agricultural-modeling crops gdd T_MIN T_MAX --crop CROP_NAME`**
- **Input:** Min/max temperatures (°C) and crop name
- **Parameters:** `--method [original|modified]` (default: modified)
- **Output:** Growing Degree Days calculation

**`rtgs agricultural-modeling crops chu T_MIN T_MAX`**
- **Input:** Min/max temperatures (°C)
- **Parameters:** `--t-base FLOAT` (default: 10.0°C)
- **Output:** Corn Heat Units calculation

##### Evapotranspiration

**`rtgs agricultural-modeling evapotranspiration calculate INPUT_FILE`**
- **Input:** CSV file with weather data
- **Required columns:** Date, Tmax, Tmin, RH_max, RH_min, Rs, u2, Latitude
- **Parameters:** `--output PATH`, `--validate-only`
- **Output:** CSV with added ETo and ETr columns

**`rtgs agricultural-modeling evapotranspiration requirements`**
- **Output:** List of required columns for ET calculation

## MCP Server Interface

### Natural Language Interface
The MCP server provides conversational access to all tools through Claude or other LLM clients.

**Available Functions:**
- `sensing_data_extract`: Extract sensor data with natural language parameters
- `visualization_create`: Create plots from descriptions
- `gridded_data_era5`: Download climate data
- `error_analysis_analyze`: Analyze error patterns
- `device_configuration_update_config`: Update device configurations
- All agricultural modeling functions

**Example Queries:**
- "Extract temperature data from Winter Turf project for last week"
- "Create a plot showing soil moisture trends for node001"
- "Download ERA5 precipitation data for Minnesota in June 2023"
- "Analyze error codes from the latest sensor data file"

## Data Formats & Standards

### File Naming Conventions
```
Data files:        ProjectName_YYYY-MM-DD_to_YYYY-MM-DD_YYYYMMDDHHMMSS.{csv|parquet}
Visualization:     parameter_node_YYYYMMDD_HHMMSS.{png|pdf|svg}
ERA5 data:         era5_variables_YYYY-MM-DD_to_YYYY-MM-DD.nc
Error analysis:    error_analysis_YYYYMMDD_HHMMSS.{png|json}
Configuration:     config_update_results_YYYYMMDD_HHMMSS.json
```

### Data Integrity
- **SHA-256 checksums** for all data files
- **Metadata files** with extraction parameters
- **Git logging** for all operations
- **Validation** of input data formats

### Output Directories
```
./data/          # Sensor data extractions
./figures/       # Visualizations and plots
./results/       # Analysis results and reports
./logs/          # Operation logs (git branch)
```

## Dependencies & Requirements

### System Requirements
- **Python**: 3.8+
- **Database**: PostgreSQL client libraries
- **Network**: UMN VPN for database access
- **Storage**: Variable based on data volume

### Key Dependencies
- **pandas**: Data manipulation and analysis
- **matplotlib**: Plotting and visualization
- **sqlalchemy**: Database operations
- **psycopg2**: PostgreSQL adapter
- **xarray**: NetCDF data handling
- **click**: CLI framework
- **requests**: HTTP requests for APIs

### Optional Dependencies
- **cdsapi**: ERA5 climate data access
- **fastmcp**: Natural language interface
- **pyarrow**: Parquet file support
- **plotly**: Interactive visualizations

## Configuration

### Environment Variables (.env)
```bash
# GEMS Database
DB_HOST=sensing-0.msi.umn.edu
DB_PORT=5433
DB_NAME=gems
DB_USER=username
DB_PASSWORD=password

# API Keys
PARTICLE_ACCESS_TOKEN=token
CDS_API_KEY=key
```

### Git Configuration
- Automatic logging to orphan `logs` branch
- Comprehensive operation tracking
- Reproducible analysis workflows

## Error Handling & Logging

### Error Types
1. **Configuration Errors**: Missing or invalid credentials
2. **Database Errors**: Connection or query failures
3. **API Errors**: External service communication issues
4. **Validation Errors**: Invalid input data or parameters
5. **Processing Errors**: Data transformation failures

### Logging Levels
- **INFO**: Normal operation status
- **DEBUG**: Detailed execution information (--verbose)
- **WARNING**: Non-fatal issues
- **ERROR**: Operation failures

### Recovery Mechanisms
- **Automatic retries** with exponential backoff
- **Partial failure handling** for batch operations
- **Graceful degradation** when optional features fail
- **Detailed error reporting** with suggested fixes

## Performance Considerations

### Database Operations
- **Connection pooling** for multiple queries
- **Batch processing** for large datasets
- **Retry logic** for network issues
- **Query optimization** for specific time ranges

### Large Dataset Handling
- **Streaming processing** for memory efficiency
- **Parquet format** for compressed storage
- **Chunked operations** for visualization
- **Parallel processing** for device operations

### API Rate Limiting
- **Respectful polling** of external APIs
- **Exponential backoff** for retry attempts
- **Concurrent request limits** for device management
- **Progress reporting** for long-running operations

## Security & Access Control

### Credential Management
- **Environment variable** configuration
- **No hardcoded secrets** in codebase
- **Template generation** for credential setup
- **Git ignore** patterns for sensitive files

### Database Security
- **VPN requirement** for database access
- **Read-only access** for data extraction
- **SQL injection prevention** through parameterized queries
- **Connection encryption** via SSL

### API Security
- **Token-based authentication** for external APIs
- **Secure credential storage** in environment
- **Request validation** and sanitization
- **Error message sanitization** to prevent information leakage

---

This specification provides comprehensive technical details for all RTGS Lab Tools modules. For implementation details, see the source code documentation and inline comments.