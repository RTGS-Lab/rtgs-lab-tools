# RTGS Lab Tools

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive Python package for environmental sensing data tools, gridded climate data access, IoT device management, and data visualization. Developed by the RTGS Lab at the University of Minnesota.

## Overview

RTGS Lab Tools consolidates multiple environmental data analysis workflows into a unified toolkit with both command-line and natural language interfaces. The package provides tools for extracting sensor data from the GEMS database, downloading climate reanalysis data, visualizing time series, managing IoT devices, and parsing data packets.

## Installation

### Prerequisites
- Python 3.10+
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
- Verify Python 3.10+ installation
- Install `uv` package manager if needed
- Initialize git submodules
- Create and activate a virtual environment
- Install the package in development mode
- Set up credential templates

After installation, edit the generated `.env` file with your actual credentials.

#### MSI (Minnesota Supercomputing Institute) Users

Before running the installation script on MSI infrastructure, load the required modules:

```bash
module load python
module load git
# Then proceed with installation
git clone https://github.com/RTGS-Lab/rtgs-lab-tools.git
cd rtgs-lab-tools
bash install.sh
```

### Manual Installation
```bash
git clone https://github.com/RTGS-Lab/rtgs-lab-tools.git
cd rtgs-lab-tools
python -m venv venv
source venv/bin/activate
# On macOS with zsh, use quotes:
pip install -e ".[all]"
# On other systems:
pip install -e .[all]
```

## Quick Start

### 1. List Available Projects
```bash
rtgs sensing-data list-projects
```

### 2. Extract Sensor Data
```bash
rtgs sensing-data extract --project "Winter Turf - v3" --start-date 2023-01-01 --end-date 2023-01-31
```

### 3. Create Visualizations
```bash
rtgs visualization create --file data/Winter_Turf_v3_2023-01-01_to_2023-01-31_20240407153045.csv --parameter "Temperature" --node-id "e00fce68f374e425e2d6b891"
```

### 4. Download Climate Data
```bash
rtgs gridded-data get-gee-point --source MOD --variables "sur_refl_b01,sur_refl_b02" --start-date 2023-01-01 --end-date 2023-01-31
```

### 5. Parse Data Files
```bash
rtgs data-parser parse --input-file raw_data.csv --output-file parsed_data.csv
```

## Available Tools

The package is organized into specialized modules, each with its own detailed documentation:

### Core Modules

- **[Sensing Data](src/rtgs_lab_tools/sensing_data/README.md)** - Extract and manage environmental sensor data from the GEMS database
- **[Visualization](src/rtgs_lab_tools/visualization/README.md)** - Create time-series plots and multi-parameter visualizations
- **[Gridded Data](src/rtgs_lab_tools/gridded_data/README.md)** - Download and process climate data from Google Earth Engine
- **[Data Parser](src/rtgs_lab_tools/data_parser/README.md)** - Parse and process raw sensor data files
- **[Device Configuration](src/rtgs_lab_tools/device_configuration/README.md)** - Manage IoT device configurations and settings

### Additional Tools

- **[Agricultural Modeling](src/rtgs_lab_tools/agricultural_modeling/README.md)** - Crop calculations, unit conversions, and agricultural modeling
- **[Audit](src/rtgs_lab_tools/audit/README.md)** - Track and analyze tool usage and generate reports

### Command Overview

Get help for any module:
```bash
rtgs <module-name> --help
```

List all available commands:
```bash
rtgs --help
```

## Natural Language Interface (MCP)

The package includes a FastMCP server that enables natural language interaction with all tools through Claude or other LLM clients. For detailed setup instructions, see the [MCP Server documentation](src/rtgs_lab_tools/mcp_server/README.md).

### Quick Setup with Claude Code
1. Install as normal with `bash install.sh`
2. Start Claude Code with `claude` in the repository directory
3. The included `.mcp.json` configuration will be automatically recognized

### Use with Claude Desktop
See the [MCP Server documentation](src/rtgs_lab_tools/mcp_server/README.md) for Claude Desktop configuration details.

## Configuration

The package requires a `.env` file for database and API access. The installation script creates a template that you can edit with your credentials.

### Required for Database Access
- **UMN VPN**: Required for GEMS database access
- **Database Credentials**: Contact Bryan Runck (runck014@umn.edu) for access

### Optional API Keys
- **Google Earth Engine**: For satellite data access
- **Particle Cloud API**: For IoT device management

For detailed configuration instructions, see individual module documentation.

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

## Contributing

We welcome contributions! For detailed guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

### Quick Start for Contributors
1. Fork and clone the repository
2. Run `bash install.sh` to set up your development environment
3. Make your changes with appropriate tests
4. Run `pytest` and formatting checks
5. Submit a pull request with a clear description

## Documentation

- [Module Documentation](src/rtgs_lab_tools/) - Detailed guides for each tool module
- [Contributing Guidelines](CONTRIBUTING.md) - Development workflow and standards
- [MCP Server Setup](src/rtgs_lab_tools/mcp_server/README.md) - Natural language interface configuration

## Contact

- **RTGS Lab**: https://rtgs.umn.edu/
- **Repository**: https://github.com/RTGS-Lab/rtgs-lab-tools
- **Issues**: Use GitHub issue tracker
- **Database Access**: Bryan Runck (runck014@umn.edu)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*For detailed API documentation and advanced usage, see the module-specific README files in the [src/rtgs_lab_tools/](src/rtgs_lab_tools/) directory.*