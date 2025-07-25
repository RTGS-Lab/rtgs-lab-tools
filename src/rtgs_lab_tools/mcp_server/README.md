# RTGS Lab Tools MCP Server

Model Context Protocol (MCP) server providing natural language interface for RTGS Lab Tools. This server enables interaction with environmental sensing data, climate data, device management, and visualization tools through Claude Code CLI, Claude Desktop, or other MCP clients.

## Overview

The MCP server exposes all RTGS Lab Tools functionality through a conversational interface, allowing you to:

- Extract and analyze environmental sensor data from the GEMS database
- Download and process climate data (ERA5, satellite imagery)
- Create professional visualizations and time-series plots
- Manage IoT device configurations
- Parse and process sensor data files
- Calculate agricultural metrics (GDD, CHU, ET)
- Track tool usage and generate audit reports

## Installation

### Prerequisites

1. **RTGS Lab Tools installed**: Complete the main package installation first:
   ```bash
   git clone https://github.com/RTGS-Lab/rtgs-lab-tools.git
   cd rtgs-lab-tools
   bash install.sh
   source venv/bin/activate
   ```

2. **Node.js and npm** (for Claude Code CLI):
   ```bash
   # Install nodeenv in your virtual environment
   pip install nodeenv
   nodeenv -p
   
   # Test npm installation
   npm install -g npm
   npm -v
   ```

### Claude Code CLI Installation

After setting up the Python environment, install Claude Code CLI:

```bash
npm install -g @anthropic-ai/claude-code
```

**Note**: Claude Code CLI requires an active Anthropic API key. Set your API key as an environment variable:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Claude Desktop Installation

Download and install Claude Desktop from the official website:
- **Download**: https://claude.ai/download

## Configuration

### Using with Claude Code CLI

The repository includes a `.mcp.json` file that Claude Code CLI will automatically detect when you run `claude` from the project directory.

**Configuration file structure** (`.mcp.json`):
```json
{
  "mcpServers": {
    "particle": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "./src/rtgs_lab_tools/mcp_server/particle-mcp-server/",
        "run",
        "particle.py"
      ]
    },
    "rtgs_lab_tools": {
      "type": "stdio",
      "command": "./venv/bin/python",
      "args": ["-m", "rtgs_lab_tools.mcp_server.rtgs_lab_tools_mcp_server"]
    }
  }
}
```

**Usage**:
1. Navigate to the project directory
2. Ensure virtual environment is activated: `source venv/bin/activate`
3. Start Claude Code CLI: `claude`
4. The MCP servers will be automatically loaded

### Using with Claude Desktop

The installation script (`install.sh`) automatically configures Claude Desktop by creating or updating the `claude_desktop_config.json` file.

**Configuration file location**:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%USERPROFILE%\AppData\Roaming\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**Generated configuration**:
```json
{
  "mcpServers": {
    "particle": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/rtgs-lab-tools/src/rtgs_lab_tools/mcp_server/particle-mcp-server/",
        "run",
        "particle.py"
      ]
    },
    "rtgs_lab_tools": {
      "command": "/path/to/rtgs-lab-tools/venv/bin/python",
      "args": ["-m", "rtgs_lab_tools.mcp_server.rtgs_lab_tools_mcp_server"]
    }
  }
}
```

**Manual configuration** (if needed):
1. Replace `/path/to/rtgs-lab-tools` with your actual project path
2. Ensure the Python path points to your virtual environment
3. Restart Claude Desktop after making changes

### Using with Other MCP Clients

The server can be used with any MCP-compatible client by running:
```bash
python -m rtgs_lab_tools.mcp_server.rtgs_lab_tools_mcp_server
```

## Available MCP Tools

The server provides these tool categories:

### Environmental Data
- **sensing_data_extract**: Extract sensor data from GEMS database
- **sensing_data_list_projects**: List available monitoring projects
- **gridded_data_era5**: Download ERA5 climate reanalysis data
- **gridded_data_list_variables**: List available climate variables

### Data Analysis & Visualization  
- **visualization_create**: Generate time-series plots and visualizations
- **visualization_list_parameters**: Discover available data parameters
- **agricultural_calculate_gdd**: Calculate Growing Degree Days
- **agricultural_calculate_chu**: Calculate Corn Heat Units
- **agricultural_calculate_et**: Calculate evapotranspiration

### Device Management
- **device_configuration_update_config**: Update IoT device configurations
- **device_configuration_verify_config**: Check current device settings
- **device_configuration_decode_system_uid**: Decode system configuration UIDs
- **device_configuration_decode_sensor_uid**: Decode sensor configuration UIDs

### Particle Cloud Integration
- **particle_list_devices**: List all devices in Particle organization
- **particle_find_device_by_name**: Find devices using fuzzy name matching
- **particle_get_device_vitals**: Check device status and vitals
- **particle_call_function**: Execute functions on devices

### Audit & Reporting
- **audit_recent_logs**: View recent tool usage
- **audit_generate_report**: Create detailed audit reports
- **audit_create_reproduction_script**: Generate scripts to reproduce workflows

## Usage Examples

### Starting Claude Code CLI
```bash
cd rtgs-lab-tools
source venv/bin/activate
claude
```

### Example Conversations

**Extract sensor data**:
> "List the available projects in the GEMS database, then extract temperature data from the Winter Turf project for January 2023"

**Create visualizations**:
> "Create a visualization showing soil temperature trends from the extracted data file"

**Device management**:
> "Show me the status of device LCCMR_47 and update its logging configuration"

**Climate data analysis**:
> "Download ERA5 temperature and precipitation data for Minnesota in 2023, then create a comparison plot"

## Troubleshooting

### Common Issues

**MCP server not loading**:
- Ensure virtual environment is activated
- Check that all dependencies are installed: `pip install -e ".[all]"`
- Verify Python path in configuration files

**Claude Code CLI not finding configuration**:
- Ensure `.mcp.json` is in the project root directory  
- Run `claude` from the project directory
- Check that the virtual environment path is correct

**Claude Desktop not connecting**:
- Restart Claude Desktop after configuration changes
- Check configuration file syntax (valid JSON)
- Ensure absolute paths are used in configuration

**Permission errors**:
- Ensure the virtual environment has proper permissions
- On Windows, try running as administrator
- Check that Python executable is accessible

### Environment Variables

Ensure your `.env` file contains the necessary credentials:

**Required for sensor data**:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

**Optional for extended features**:
- `PARTICLE_ACCESS_TOKEN` (device management - use `rtgs auth particle-login` to create)
- `GEE_PROJECT` (satellite data)
- `ANTHROPIC_API_KEY` (Claude Code CLI)

### Logging

Enable debug logging to troubleshoot issues:
```bash
export RTGS_LOG_LEVEL=DEBUG
python -m rtgs_lab_tools.mcp_server.rtgs_lab_tools_mcp_server
```

## Architecture

The MCP server consists of two main components:

1. **RTGS Lab Tools MCP Server**: Core environmental data tools
2. **Particle MCP Server**: Particle Cloud device management

Both servers run independently and can be configured separately. The combined setup provides comprehensive access to environmental sensing workflows through natural language interaction.

## Development

To extend the MCP server with new tools:

1. Add new functions to `rtgs_lab_tools_mcp_server.py`
2. Follow the existing pattern for argument handling and git logging  
3. Update tool descriptions for clear natural language interaction
4. Test with Claude Code CLI or Claude Desktop

For detailed development guidelines, see [CONTRIBUTING.md](../../../CONTRIBUTING.md).