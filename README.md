# RTGS Lab Tools

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive Python package for environmental sensing data tools, gridded climate data access, IoT device management, and data visualization.

Built and maintained by the RTGS Lab, please email radli009@umn.edu for database access and any questions or issues. Also feel free to open issues on GitHub.

## Overview

RTGS Lab Tools consolidates multiple environmental data analysis workflows into a unified toolkit with both command-line and natural language interfaces. The package provides tools for extracting sensor data from the GEMS database, downloading climate reanalysis data, visualizing time series, managing IoT devices, and parsing data packets.

## Installation

### Prerequisites

Before installing RTGS Lab Tools, ensure you have the following software installed:

#### 1. Python 3.10+
**Installation:**
- **Download:** [Python.org Downloads](https://www.python.org/downloads/) - Get the latest Python 3.10+ version
- **Verify installation:** Open a terminal and run:
  ```bash
  python --version
  # or
  python3 --version
  ```
  You should see Python 3.10 or higher.

#### 2. Git
**Installation:**
- **Windows:** Download [Git for Windows](https://git-scm.com/download/win) 
  - ⚠️ **Important:** Use **Git Bash** (included with Git for Windows) instead of PowerShell or Command Prompt for all commands
- **macOS:** 
  - Install via Homebrew: `brew install git`
  - Or download from [Git website](https://git-scm.com/download/mac)
- **Linux:** Install via package manager:
  ```bash
  # Ubuntu/Debian:
  sudo apt update && sudo apt install git
  
  # CentOS/RHEL/Fedora:
  sudo yum install git
  # or
  sudo dnf install git
  ```
- **Verify installation:**
  ```bash
  git --version
  ```

#### 3. pip (Python Package Installer)
**Installation:**
- **Usually included** with Python 3.10+ installations
- **If missing:** Download [get-pip.py](https://bootstrap.pypa.io/get-pip.py) and run:
  ```bash
  python get-pip.py
  ```
- **Verify installation:**
  ```bash
  pip --version
  # or
  pip3 --version
  ```

#### 4. Additional Requirements
- **PostgreSQL client libraries** (for GEMS database access)
- **[UMN VPN connection](https://it.umn.edu/services-technologies/virtual-private-network-vpn)** (for database access)

#### Windows Users: Important Note
🚨 **Always use Git Bash** instead of PowerShell or Command Prompt when running installation commands. Git Bash provides a Unix-like environment that ensures compatibility with the installation scripts.

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
- Configure MCP servers for Claude Desktop integration

**For existing installations:** The script automatically detects existing setups and performs updates instead of fresh installations.

### Updating an Existing Installation

To update your existing RTGS Lab Tools installation:

```bash
# Navigate to your rtgs-lab-tools directory
cd rtgs-lab-tools

# Run the install script (it will automatically detect and update)
bash install.sh
```

The update process will:
- Check for uncommitted local changes (must be clean to update)
- Fetch the latest release from GitHub
- Update to the latest stable version
- Reinstall dependencies
- Reconfigure MCP servers

**Alternative update method (post v0.1.0):**
```bash
# Using the built-in update command
rtgs core update
```

### Post-Installation Setup

After running the installation script, follow these steps to complete your setup:

#### 1. Activate the Virtual Environment
```bash
# Linux/macOS:
source venv/bin/activate

# Windows (Git Bash/WSL):
source venv/Scripts/activate
```

#### 2. Configure Your Credentials

**Option 1: Google Cloud Authentication (Recommended for Lab Users)**

For lab users with Google Cloud access, authenticate with Google Cloud for automatic credential management:

```bash
rtgs auth login
```

This will:
- Open your browser for Google Cloud authentication
- Set up Application Default Credentials
- Enable automatic retrieval of database credentials from Google Secret Manager

Check your authentication status:
```bash
rtgs auth status
```

**Option 2: Environment Variables (For External Users)**

If you don't have Google Cloud access, edit the `.env` file with your credentials:
```bash
nano .env  # or use your preferred editor
```

**Required Environment Variables:**

**GEMS Database (required for sensor data):**
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

**Logging Database (optional for audit features):**
- `LOGGING_DB_HOST`, `LOGGING_DB_PORT`, `LOGGING_DB_NAME`
- `LOGGING_DB_USER`, `LOGGING_DB_PASSWORD`
- `LOGGING_INSTANCE_CONNECTION_NAME` (GCP Cloud SQL)
- `POSTGRES_LOGGING_STATUS` (True/False)

**Google Earth Engine (optional for satellite data):**
- `GEE_PROJECT` (Google Cloud project name)
- `BUCKET_NAME` (Google Cloud Storage bucket)

**PlanetLabs (optional for high-res satellite imagery):**
- `PL_API_KEY` (PlanetLabs API key)

**Device Management (optional for IoT devices):**
- `PARTICLE_ACCESS_TOKEN`

#### 3. Test the Installation
```bash
rtgs --help
```

#### 4. List Available Projects
```bash
rtgs sensing-data list-projects
```

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

### 0. Check Installation and Version
```bash
# Check current version
rtgs core version

# Check for updates
rtgs core update
```

### 1. List Available Projects
```bash
rtgs sensing-data list-projects
```

### 2. Extract Sensor Data
```bash
rtgs sensing-data extract --project "Winter Turf - v3" --start-date 2023-01-01 --end-date 2023-01-31
```

### 3. Parse Sensor Data (Optional: the visualization tool will parse automatically)
```bash
rtgs data-parser parse data/Winter_Turf_v3_2023-01-01_to_2023-01-31.csv
```

### 4. Create Visualizations
```bash
rtgs visualization create --file data/parsed/Winter_Turf_v3_2023-01-01_to_2023-01-31_20240407153045_parsed.csv --parameter "Kestrel.PORT_V[0]" --node-id "e00fce68c148e3450a925509"
```

### 5. Download Climate Data
```bash
rtgs gridded-data get-gee-point --source MOD --variables "sur_refl_b01,sur_refl_b02" --start-date 2023-01-01 --end-date 2023-01-31
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
- **[Authentication](auth)** - Google Cloud authentication for secure credential management

### Command Overview

Get help for any module:
```bash
rtgs <module-name> --help
```

List all available commands:
```bash
rtgs --help
```

### Core System Commands

```bash
# Version and update management
rtgs core version          # Show current version information
rtgs core update           # Update to latest release

# Authentication management  
rtgs auth login            # Authenticate with Google Cloud
rtgs auth logout           # Logout from Google Cloud
rtgs auth status           # Check authentication status
```

## Natural Language Interface (MCP)

The package includes a FastMCP server that enables natural language interaction with all tools through Claude or other LLM clients. For detailed setup instructions, see the [MCP Server documentation](src/rtgs_lab_tools/mcp_server/README.md).

### Quick Setup with Claude Code
1. Install as normal with `bash install.sh`
2. Start Claude Code with `claude` in the repository directory
3. The included `.mcp.json` configuration will be automatically recognized

### Quick Setup with Gemini CLI
1. Install as normal with `bash install.sh`
2. Start Gemini CLI with `gemini` in the repository directory
3. The included `.gemini/settings.json` (same file as .mcp.json) configuration will be automatically recognized

### Use with Claude Desktop
See the [MCP Server documentation](src/rtgs_lab_tools/mcp_server/README.md) for Claude Desktop configuration details.

## Configuration

The package requires a `.env` file for database and API access. The installation script creates a template that you can edit with your credentials.

### Required for Database Access
- **UMN VPN**: Required for GEMS database access
- **Database Credentials**: Contact Bryan Runck (runck014@umn.edu) for access

### Authentication Methods

**Primary Method - Google Cloud Authentication:**
1. Lab users should use `rtgs auth login` for automatic credential management
2. Credentials are securely retrieved from Google Cloud Secret Manager
3. No need to manage `.env` files for database credentials

**Fallback Method - Environment Variables:**
1. External users or those without Google Cloud access use `.env` files
2. Manual credential management required
3. Automatically used when Google Cloud authentication is unavailable

### Credential Resolution Priority

The system automatically tries credentials in this order:
1. **Google Cloud Secret Manager** (if authenticated with `rtgs auth login`)
2. **Environment Variables** (from `.env` file or system environment)
3. **Error** (if neither method provides required credentials)

This allows lab users to use managed secrets while external users can use local environment variables seamlessly.

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