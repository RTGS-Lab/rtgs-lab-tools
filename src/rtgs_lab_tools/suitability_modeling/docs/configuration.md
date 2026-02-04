# Suitability Modeling - Configuration Guide

## Data Source Configuration

The suitability modeling module uses datasets from two sources:

1. **FGDB (File Geodatabase)** - Hennepin County analysis datasets (16 layers)
2. **MN Geospatial Commons** - Public Minnesota datasets via spatial_data module

### FGDB Setup (Required for Hennepin County Data)

To use Hennepin County datasets, you need access to the File Geodatabase:
- `HC_EasementAnalysis_Model_Inputs_2020.gdb`

#### Environment Variable Configuration

Set the `RTGS_FGDB_PATH` environment variable to point to your FGDB:

**Linux/macOS:**
```bash
export RTGS_FGDB_PATH="/path/to/HC_EasementAnalysis_Model_Inputs_2020.gdb"
```

**Windows PowerShell:**
```powershell
$env:RTGS_FGDB_PATH="C:\path\to\HC_EasementAnalysis_Model_Inputs_2020.gdb"
```

**Windows CMD:**
```cmd
set RTGS_FGDB_PATH=C:\path\to\HC_EasementAnalysis_Model_Inputs_2020.gdb
```

**For persistent configuration (Windows):**
1. Open Environment Variables settings (search "environment variables" in Start)
2. Add `RTGS_FGDB_PATH` as a user or system variable
3. Restart terminal/IDE

#### Verify Configuration

Check that the FGDB is configured correctly:

```bash
rtgs suitability list-datasets
```

You should see output like:
```
FGDB Status: Configured and available

Hennepin County Datasets (FGDB)
----------------------------------------
  bee_habitat
    Bee Habitat Analysis - Hennepin County pollinator habitat suitability scores
    Features: 2
  ...
```

### Available Datasets

#### FGDB Datasets (16 datasets from Hennepin County)

| Dataset Name | Description | Features |
|--------------|-------------|----------|
| `bee_habitat` | Pollinator habitat suitability scores | 2 |
| `floodplains` | Floodplain scoring | 2 |
| `hennepin_wetland_inventory` | Comprehensive wetland mapping | 56,018 |
| `habitat_diversity` | Ecosystem diversity scoring | 51 |
| `headwaters` | Stream headwater catchment areas | 1,447 |
| `important_bird_areas` | Audubon designated bird areas | 6 |
| `mbs_sites` | MN Biological Survey sites | 318 |
| `land_cover` | MLCCS land cover classification | 46,745 |
| `groundwater_recharge_hc` | Groundwater recharge rates | 2,884 |
| `natural_spaces` | Protected natural areas | 1 |
| `protected_areas_hc` | Protected lands composite | 1 |
| `quality_community` | Community quality metrics | 1 |
| `risk_of_development` | Development pressure scoring | 3 |
| `shoreland_buffers` | Lake and stream buffer zones | 1 |
| `groundwater_susceptibility` | Aquifer vulnerability zones | 976 |
| `wildlife_action_network` | Wildlife corridor ranking | 1,564 |

#### MN Geospatial Commons Datasets (Public)

These are always available without configuration:

| Dataset Name | Description |
|--------------|-------------|
| `wildlife_areas` | DNR Wildlife Management Areas |
| `scientific_and_natural_areas` | DNR Scientific and Natural Areas |
| `aquatic_areas` | DNR Aquatic Management Areas |
| `MBS_sites` | MN Biological Survey Sites |
| `WAN` | Wildlife Action Network |
| `land_use` | Generalized Land Use 2020 |
| `watersheds` | DNR Level 9 Watersheds |
| `groundwater_recharge` | Groundwater recharge rates |
| `TNC_lands` | The Nature Conservancy lands |
| `cemeteries` | Regional cemeteries |

### Using Mixed Data Sources

You can design models that use datasets from **both** sources. The system automatically determines where each dataset comes from.

**Example requirements.txt:**

```
Objective:
Identify suitable conservation easement locations in Hennepin County.

Criteria:
1. Proximity to protected areas (protected_areas_hc from FGDB)
2. Habitat diversity (habitat_diversity from FGDB)
3. Groundwater recharge importance (groundwater_recharge_hc from FGDB)
4. Avoid high development risk (risk_of_development from FGDB)
5. Connection to wildlife corridors (wildlife_areas from MN Geospatial)

Weights:
- Protected area proximity: 25%
- Habitat diversity: 25%
- Groundwater recharge: 20%
- Development risk: 15%
- Wildlife corridor connection: 15%
```

## Claude AI Configuration

### API Key Setup

The model designer uses Claude AI to interpret requirements. Configure your API key:

```bash
# Environment variable (recommended)
export ANTHROPIC_API_KEY="sk-ant-..."

# Or pass via command line
rtgs suitability design --input requirements.txt --api-key "sk-ant-..."
```

**Get an API key:** https://console.anthropic.com/

## Troubleshooting

### FGDB Not Found

**Error:** `FGDB path not configured`

**Solution:** Set the `RTGS_FGDB_PATH` environment variable:
```bash
export RTGS_FGDB_PATH="/path/to/HC_EasementAnalysis_Model_Inputs_2020.gdb"
```

---

**Error:** `FGDB not found at: /path/to/file.gdb`

**Solution:**
1. Verify the path is correct
2. Check that the .gdb folder exists and is accessible
3. On Windows, ensure no lock files are blocking access

---

### Dataset Not Found

**Error:** `Dataset 'dataset_name' not found`

**Solution:** The dataset name doesn't match any available dataset. Check available datasets:

```bash
rtgs suitability list-datasets
```

Or in Python:
```python
from rtgs_lab_tools.spatial_data import list_available_datasets

datasets = list_available_datasets()
for name in sorted(datasets.keys()):
    print(f"- {name}: {datasets[name]['description']}")
```

### Performance Tips

For large areas or many datasets:

1. **Start with smaller study areas** - Test with a subset before running full county
2. **Limit grid resolution** - Use larger cell sizes (e.g., 500m instead of 100m) for testing
3. **Use sampling** - The engine automatically samples if grid exceeds max_cells limit

## Security Notes

The FGDB file contains local data and doesn't require password configuration.

For the Anthropic API key:
- **Never commit API keys to git!**
- Use environment variables
- Consider using a secrets manager for production deployments
