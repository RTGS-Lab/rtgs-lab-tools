# RTGS Lab Tools - Project Context

## Project Overview

**RTGS Lab Tools** is a Python package that consolidates environmental sensing data tools, gridded climate data access, IoT device management, and data visualization into a unified toolkit. The goal is to wrap all functionality in an MCP server for natural language interaction.

## Current State

### Existing Code Structure
```
rtgs-lab-tools/
├── sensing_tools/
│   ├── device_data_getter/
│   │   └── get_sensing_data.py           # 400+ lines, needs refactoring
│   ├── time_series_visualizer/
│   │   └── gems_sensing_data_visualizer.py
│   ├── error_code_translator/
│   │   └── error_code_parser.py
│   └── device_configuration_updater/
│       ├── configuration_updater.py
│       └── uid_decoder.py
├── girdded_data_pullers/                 # Empty - new functionality
├── device_diagnostic_tools/              # Empty - future expansion
└── mcp_server/                          # Has basic implementation
```

### Key Components to Migrate
1. **get_sensing_data.py** - Main data extraction tool (most important)
2. **gems_sensing_data_visualizer.py** - Time series plotting
3. **error_code_parser.py** - Device error analysis
4. **configuration_updater.py** - Device configuration management
5. **uid_decoder.py** - Device UID utilities

## Target Structure

```
src/rtgs_lab_tools/
├── core/                    # Shared utilities
├── sensing_data/            # GEMS database tools
├── gridded_data/            # Climate data (ERA5, etc.)
├── visualization/           # Plotting tools
├── device_management/       # Particle device tools
└── mcp_server/             # Natural language interface
```

## Migration Strategy

### Phase 1: Foundation (Current Focus)
1. **Create package structure** with `pyproject.toml`
2. **Set up core utilities** (database, logging, config)
3. **Migrate sensing_data module** from `get_sensing_data.py`
4. **Basic MCP server** integration

### Phase 2: Expand
1. Add gridded data capabilities (starting with ERA5)
2. Migrate visualization and device management
3. Complete MCP server with all tools

## Key Requirements

### Database Connection
- PostgreSQL database at `sensing-0.msi.umn.edu:5433`
- Requires UMN VPN connection
- Credentials in `.env` file

### API Integrations
- **Particle API**: Device management
- **Copernicus CDS**: ERA5 climate data
- **Various satellite APIs**: MODIS, Landsat, Sentinel

### Dependencies
- Core: `pandas`, `numpy`, `sqlalchemy`, `psycopg2-binary`
- Climate: `xarray`, `cdsapi`, `netcdf4`
- Visualization: `matplotlib`, `seaborn`, `plotly`
- MCP: `mcp[cli]`, `fastmcp`

## Code Style Guidelines

### Package Organization
- **CLI separation**: Keep CLI interfaces in `cli.py`, core logic in separate modules
- **Pure functions**: Business logic should be importable and testable
- **Shared utilities**: Common code goes in `core/` module
- **Error handling**: Custom exceptions in `core/exceptions.py`

### Naming Conventions
- **Package**: `rtgs_lab_tools`
- **CLI commands**: `rtgs-data`, `rtgs-era5`, `rtgs-visualize`
- **Functions**: Descriptive names like `get_raw_data()`, `pull_era5_data()`

### Function Signatures
```python
# Good - pure function, easy to test and use in MCP
def get_raw_data(
    database_manager: DatabaseManager,
    project: str,
    start_date: str,
    end_date: str,
    node_ids: Optional[List[str]] = None
) -> pd.DataFrame:
    """Extract raw sensor data from GEMS database."""
    pass

# Bad - mixed concerns, hard to test
def main():
    args = parse_args()
    db = create_connection()
    data = query_database()
    save_file()
    print_results()
```

## MCP Integration Goals

### Target User Experience
```
Human: "Get temperature data from Winter Turf project for last month"

Claude: I'll extract the sensor data for you.
[Uses: get_sensing_data tool with project="Winter Turf", dates=last_month]

Result: Retrieved 5,247 records from 8 nodes
```

### Tool Categories
1. **Data Extraction**: `get_sensing_data`, `list_projects`
2. **Climate Data**: `download_era5_data`, `get_satellite_imagery`
3. **Visualization**: `create_time_series_plot`, `create_spatial_map`
4. **Device Management**: `list_devices`, `update_configuration`
5. **Analysis**: `analyze_error_codes`, `calculate_statistics`

## Current Challenges

### Code Quality Issues
- **Monolithic files**: `get_sensing_data.py` has 400+ lines mixing CLI, DB, and logic
- **Hardcoded values**: Database credentials, file paths scattered throughout
- **Poor error handling**: Generic try/catch blocks, unclear error messages
- **No testing**: Existing code lacks unit tests

### Missing Functionality
- **Gridded data access**: Need ERA5, GFS, satellite data pulling
- **Spatial analysis**: Coordinate transformations, map projections
- **Advanced visualization**: Interactive plots, web maps
- **Workflow automation**: Data pipelines, scheduled tasks

## Technical Specifications

### Database Schema (GEMS)
```sql
-- Main tables
raw           -- Raw sensor data (id, node_id, publish_time, message, etc.)
node          -- Node metadata (node_id, project, location, etc.)
parsed        -- Parsed sensor readings
```

### Configuration Format
```yaml
# .env file
DB_HOST=sensing-0.msi.umn.edu
DB_PORT=5433
DB_NAME=gems
DB_USER=username
DB_PASSWORD=password

# API keys
PARTICLE_ACCESS_TOKEN=token
CDS_API_KEY=key
```

### Output Formats
- **CSV**: Default for data exports
- **Parquet**: For large datasets
- **NetCDF**: For gridded climate data
- **GeoJSON**: For spatial data

## Development Workflow

### Setup Commands
```bash
# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

### Testing Strategy
- **Unit tests**: Pure functions, isolated logic
- **Integration tests**: Database connections, API calls
- **MCP tests**: Tool execution, response formatting
- **Mock external services**: Database, APIs for testing

## Success Criteria

### Phase 1 Complete When:
- [ ] Package installs with `pip install rtgs-lab-tools`
- [ ] `rtgs-data` command works (replaces `get_sensing_data.py`)
- [ ] Core utilities (database, config, logging) are shared
- [ ] Basic MCP server exposes sensing data tools
- [ ] CI/CD pipeline runs tests automatically

### Long-term Goals:
- [ ] All existing tools migrated and improved
- [ ] ERA5 and satellite data access working
- [ ] Comprehensive natural language interface via MCP
- [ ] Published on PyPI for easy installation
- [ ] Full documentation and examples

## Notes for Claude Code

- **Focus on incremental progress**: Start small, build up functionality
- **Maintain backward compatibility**: Existing users should not be disrupted
- **Prioritize code quality**: This is a chance to improve the existing codebase
- **Test everything**: New structure should be more testable than current code
- **Document decisions**: Explain why architectural choices were made

## Contact & Resources

- **Repository**: `https://github.com/RTGS-Lab/rtgs-lab-tools`
- **RTGS Lab**: `https://rtgs.umn.edu/`
- **Database Access**: Requires UMN VPN connection
- **API Documentation**: Copernicus CDS, Particle Cloud API docs