# RTGS Lab Tools

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive Python package for environmental sensing data tools, gridded climate data access, IoT device management, and data visualization. Developed by the RTGS Lab at the University of Minnesota.

## Overview

RTGS Lab Tools consolidates multiple environmental data analysis workflows into a unified toolkit with both command-line and natural language interfaces. The package provides tools for extracting sensor data from the GEMS database, downloading climate reanalysis data, visualizing time series, managing IoT devices, and analyzing error codes.

## Features

### Sensing Data Tools
- **Data Extraction**: Query and export raw sensor data from the GEMS database
- **Project Management**: List available projects and node configurations
- **Multiple Formats**: Export data as CSV or Parquet with compression options
- **Data Integrity**: SHA-256 hashing and metadata generation for archival

### Gridded Data Tools
- **ERA5 Reanalysis**: Download and process ERA5 climate data via Copernicus CDS
- **Variable Support**: Access temperature, precipitation, wind, radiation, and more
- **Spatial/Temporal Filtering**: Custom bounding boxes and time ranges
- **Data Processing**: Regridding, aggregation, and statistical analysis

### Visualization Tools
- **Time Series Plots**: Automated plotting of sensor parameters over time
- **Multi-Parameter Comparison**: Compare data across nodes and variables
- **Multiple Formats**: Export plots as PNG, PDF, or SVG
- **Interactive Parameter Discovery**: Automatically detect available parameters in data

### Device Configuration
- **Batch Operations**: Update multiple device configurations concurrently with verification
- **Configuration Templates**: Pre-defined settings for different sensor types
- **Audit Trails**: Comprehensive logging of all device operations

### Error Analysis
- **Error Code Parsing**: Decode and analyze hex error codes from GEMS devices using ERRORCODES.md database
- **Pattern Recognition**: Identify common errors and temporal trends
- **Visualization**: Generate frequency plots and statistical summaries
- **Device Diagnostics**: Track errors by node and hardware component with full error translations

### Packet Parser
- **Universal**: Packet parser for parsing new and historical JSON packets from in field devices

### Natural Language Interface
- **MCP Server**: FastMCP-based server for natural language interaction
- **Claude Integration**: Use conversational AI to operate all tools
- **Automated Logging**: Every operation creates detailed audit logs
- **Git Integration**: Automatic commit and tracking of all tool executions

### Universal Logging
- **Automatic Logging**: Automatically creates logs and commits them to dedicated `logs` branch for auditing purposes and tool use analysis
- **Orphan Branch**: Logs are stored in a separate orphan branch to keep the main codebase clean

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL client libraries (for GEMS database access)
- UMN VPN connection (for database access)

### Quick Installation (Recommended)

Use the automated installation script for cross-platform setup:

```bash
git clone https://github.com/RTGS-Lab/rtgs-lab-tools.git
cd rtgs-lab-tools
bash install.sh
```

The install script will:
- Detect your operating system (Windows/macOS/Linux)
- Verify Python 3.8+ installation
- Install `uv` package manager if needed
- Initialize git submodules
- Create and activate a virtual environment
- Install the package in development mode
- Set up credential templates

After installation, edit the generated `.env` file with your actual credentials.

### Manual Installation
```bash
git clone https://github.com/RTGS-Lab/rtgs-lab-tools.git
cd rtgs-lab-tools
python -m venv venv
source venv/bin/activate
pip install -e .[all]
```

### Optional Dependencies (only if you only want specific parts of the tool)
```bash
# For climate data access
pip install rtgs-lab-tools[climate]

# For visualization enhancements
pip install rtgs-lab-tools[visualization]

# For MCP server functionality
pip install rtgs-lab-tools[mcp]

# Install everything
pip install rtgs-lab-tools[all]
```

## Quick Start

### 1. Setup Credentials
```bash
rtgs data --setup-credentials
```
Edit the created `.env` file with your database credentials.

### 2. List Available Projects
```bash
rtgs data --list-projects
```

### 3. Extract Sensor Data
```bash
rtgs data --project "Winter Turf - v3" --start-date 2023-01-01 --end-date 2023-01-31
```

### 4. Create Visualizations
```bash
rtgs visualize --file data/Winter_Turf_v3_2023-01-01_to_2023-01-31_20240407153045.csv --parameter "Data.Devices.0.Temperature"
```

### 5. Download Climate Data
```bash
rtgs era5 --variables 2m_temperature --start-date 2023-01-01 --end-date 2023-01-31 --area "45,-94,44,-93"
```

## Command Reference

### Data Extraction
```bash
# Basic extraction
rtgs data --project "My Project" --start-date 2023-01-01

# Filter by specific nodes
rtgs data --project "My Project" --node-id "node001,node002"

# Create compressed archive
rtgs data --project "My Project" --create-zip

# Export as Parquet
rtgs data --project "My Project" --output parquet
```

### Visualization
```bash
# Single parameter plot
rtgs visualize --file data.csv --parameter "Data.Temperature" --node-id node001

# Multi-parameter comparison
rtgs visualize --file data.csv --multi-param "node001,Data.Temperature" --multi-param "node002,Data.Temperature"

# List available parameters
rtgs visualize --file data.csv --list-params
```

### ERA5 Climate Data
```bash
# Download temperature and precipitation
rtgs era5 --variables 2m_temperature total_precipitation --start-date 2023-01-01 --end-date 2023-12-31

# Specific region and time
rtgs era5 --variables 2m_temperature --start-date 2023-06-01 --end-date 2023-08-31 --area "49,-97,43,-89" --time-hours "00:00,12:00"

# List available variables
rtgs era5 --list-variables
```

### Error Analysis
```bash
# Basic error analysis (shows all nodes by default)
rtgs error-analysis analyze --file data.csv --generate-graph

# Filter by specific nodes
rtgs error-analysis analyze --file data.csv --nodes "node001,node002" --generate-graph

# Decode a single error code
rtgs error-analysis decode 0xF00C00F8

# List error classes and hardware types
rtgs error-analysis error-classes

# Save analysis results
rtgs error-analysis analyze --file data.csv --output-analysis error_report.json
```

## Natural Language Interface (MCP)

The package includes a FastMCP server that enables natural language interaction with all tools through Claude or other LLM clients.

### Dependencies
1. The particle-mcp-server submodule requires uv package manager, install it with:
mac/linux
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

windows
```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Use with Claude Code
1. Clone and install as normal
2. Navigate to repository and start Claude Code with 'claude'
3. .mcp.json includes all configuration and Claude Code should recognize
4. verify the mcps are running with /mcp once in Claude Code

### Setup with Claude Desktop
1. Install the package with MCP support:
   ```bash
   pip install rtgs-lab-tools[mcp]
   ```

2. Add to Claude Desktop configuration:
  ```json
    {
    "mcpServers": {
      "particle": {
        "command": "uv",
        "args": [
          "--directory",
          "/ABSOLUTE_PATH_TO_REPOSITORY/src/rtgs_lab_tools/mcp_server/particle-mcp-server/",
          "run",
          "particle.py"
        ]
      },
      "rtgs_lab_tools": {
        "command": "/ABSOLUTE_PATH_TO_REPOSITORY/venv/bin/python",
        "args": ["-m", "rtgs_lab_tools.mcp_server.rtgs_lab_tools_mcp_server"]
      }
     }
    }
  ```

3. Use natural language to operate tools:
   ```
   "Extract temperature data from Winter Turf project for last week"
   "Create a plot showing soil moisture trends for node001"
   "Download ERA5 precipitation data for Minnesota in June 2023"
   ```

## Configuration

### Database Connection
The package requires connection to the GEMS PostgreSQL database. Create a `.env` file:

```env
# GEMS Database Configuration
DB_HOST=sensing-0.msi.umn.edu
DB_PORT=5433
DB_NAME=gems
DB_USER=your_username
DB_PASSWORD=your_password

# Optional API Keys
PARTICLE_ACCESS_TOKEN=your_particle_token
CDS_API_KEY=your_cds_api_key
```

### Network Requirements
- **UMN VPN**: Required for GEMS database access
- **Internet**: Required for ERA5 downloads and Particle device management

## Data Output

### File Naming Convention
```
Project_Name_YYYY-MM-DD_to_YYYY-MM-DD_YYYYMMDD_HHMMSS.csv
```

### Supported Formats
- **CSV**: Human-readable, Excel-compatible
- **Parquet**: Efficient binary format for large datasets
- **NetCDF**: For gridded climate data
- **PNG/PDF/SVG**: For visualizations

### Metadata and Integrity
All outputs include:
- SHA-256 hash verification
- Detailed metadata files
- Query parameters and statistics
- Automated git logging for audit trails

## Architecture

```
src/rtgs_lab_tools/
├── core/                   # Shared utilities (database, config, logging)
├── sensing_data/           # GEMS database extraction tools
├── gridded_data/           # Climate data access (ERA5, etc.)
├── visualization/          # Time series and spatial plotting
├── device_configuration/   # Particle IoT device configuration tools
├── device_monitoring/      # Reserved for future device monitoring tools
├── error_analysis/         # Error code analysis and device diagnostics
└── mcp_server/            # Natural language interface
```

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black src/ tests/
isort src/ tests/
```

### Building Documentation
```bash
# Documentation is auto-generated from docstrings
python -m pydoc rtgs_lab_tools
```

## API Keys and Access

### GEMS Database
Contact Bryan Runck (runck014@umn.edu) for database credentials.

### Copernicus CDS (ERA5)
1. Register at [CDS](https://cds.climate.copernicus.eu/)
2. Get your API key from the user profile
3. Add to `.env` file or configure `~/.cdsapirc`

### Particle Cloud API
1. Create account at [Particle Console](https://console.particle.io/)
2. Generate access token in settings
3. Add to `.env` file

## Troubleshooting

### Database Connection Issues
- Ensure UMN VPN is connected
- Verify credentials in `.env` file
- Check firewall settings

### ERA5 Download Issues
- Verify CDS API key configuration
- Check data availability (5-day delay for recent data)
- Monitor CDS queue status

### Device Management Issues
- Verify Particle access token
- Ensure devices are online and responsive
- Check device firmware compatibility

## Contributing

We welcome contributions to RTGS Lab Tools! Whether you're fixing bugs, adding features, improving documentation, or suggesting enhancements, your help is appreciated.

### Quick Start for Contributors

1. Fork the repository and clone your fork
2. Run `bash install.sh` to set up your development environment
3. Create a feature branch following our naming conventions
4. Make your changes with appropriate tests
5. Run quality checks and ensure all tests pass
6. Submit a pull request with a clear description

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/rtgs-lab-tools.git
cd rtgs-lab-tools

# Install in development mode
bash install.sh

# Run tests
pytest

# Run quality checks
black src/ tests/
isort src/ tests/
mypy src/
```

For detailed contributing guidelines, branch structure, PR formatting, and development workflows, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **RTGS Lab**: https://rtgs.umn.edu/
- **Repository**: https://github.com/RTGS-Lab/gems_sensing_db_tools
- **Issues**: Use GitHub issue tracker
- **Database Access**: Bryan Runck (runck014@umn.edu)

## Acknowledgments

- University of Minnesota RTGS Lab
- Minnesota Supercomputing Institute (MSI)
- Copernicus Climate Data Store
- Particle IoT platform

---

*For detailed API documentation and advanced usage, see the inline documentation and examples in the source code.*