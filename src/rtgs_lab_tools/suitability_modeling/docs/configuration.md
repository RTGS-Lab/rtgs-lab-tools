# Suitability Modeling - Configuration Guide

## Database Configuration

The suitability modeling module can use datasets from two sources:

1. **PostGIS Database** - Private Hennepin County datasets (~110,000 features)
2. **spatial_data Module** - Public Minnesota datasets

### PostGIS Database Setup

#### Environment Variables

The easiest way to configure database access is through environment variables:

```bash
# Option 1: Full connection URL
export SUITABILITY_DB_URL="postgresql://postgres:yourpassword@localhost:5432/rtgs_suitability_data"

# Option 2: Individual components (will be combined automatically)
export SUITABILITY_DB_HOST="localhost"
export SUITABILITY_DB_PORT="5432"
export SUITABILITY_DB_NAME="rtgs_suitability_data"
export SUITABILITY_DB_USER="postgres"
export SUITABILITY_DB_PASSWORD="yourpassword"
```

**For Windows PowerShell:**

```powershell
$env:SUITABILITY_DB_URL="postgresql://postgres:yourpassword@localhost:5432/rtgs_suitability_data"
```

**For persistent configuration (Windows):**

1. Open Environment Variables settings
2. Add `SUITABILITY_DB_URL` as a user or system variable
3. Restart terminal/IDE

#### Command Line Option

You can also pass the database URL directly when running commands:

```bash
rtgs suitability design \
  --input requirements.txt \
  --db-url "postgresql://postgres:password@localhost:5432/rtgs_suitability_data"
```

### Available Datasets

Once configured, you can list available datasets from both sources:

#### PostGIS Datasets (16 datasets, ~110,000 features)

- `mn_bee_habitat_analysis` - Bee Habitat Analysis (Hennepin County)
- `mn_floodplains_analysis` - Floodplains Analysis
- `mn_habitatdiversity_lvl3_analysis` - Habitat Diversity Level 3
- `mn_hcwi_analysis` - Hennepin County Watershed Index (56,018 features)
- `mn_headwaters_analysis` - Headwaters Analysis (1,447 features)
- `mn_important_bird_areas_analysis` - Important Bird Areas
- `mn_mbs_analysis` - MBS Analysis (318 features)
- `mn_mean_gw_recharge_1996_2010_analysis` - Mean Groundwater Recharge (2,884 features)
- `mn_mlccs_analysis` - MLCCS Land Cover (46,745 features)
- `mn_natural_spaces_analysis` - Natural Spaces
- `mn_protected_areas_analysis` - Protected Areas
- `mn_quality_community_analysis` - Quality Community
- `mn_risk_of_development_analysis` - Risk of Development
- `mn_shoreland_bufferareas_analysis` - Shoreland Buffer Areas
- `mn_susceptibility_contamination_groundwater_analysis` - Groundwater Contamination Susceptibility (976 features)
- `mn_wildlife_action_network_analysis` - Wildlife Action Network (1,564 features)

#### spatial_data Datasets

- `wildlife_areas` - DNR Wildlife Management Areas (public data)
- `land_use` - Generalized Land Use (public data)
- `watersheds` - DNR Watersheds (public data)
- ... and more

### Using Mixed Data Sources

You can design models that use datasets from **both** sources:

**Example requirements.txt:**

```
Objective:
Identify suitable conservation easement locations in Hennepin County.

Criteria:
1. Proximity to protected areas (mn_protected_areas_analysis from PostGIS)
2. Habitat diversity (mn_habitatdiversity_lvl3_analysis from PostGIS)
3. Groundwater recharge importance (mn_mean_gw_recharge_1996_2010_analysis from PostGIS)
4. Avoid high development risk (mn_risk_of_development_analysis from PostGIS)
5. Connection to wildlife corridors (wildlife_areas from spatial_data module)

Weights:
- Protected area proximity: 25%
- Habitat diversity: 25%
- Groundwater recharge: 20%
- Development risk: 15%
- Wildlife corridor connection: 15%
```

The system will automatically:
1. Query PostGIS for Hennepin County datasets
2. Query spatial_data for public Minnesota datasets
3. Load each dataset from the appropriate source during execution

## Claude AI Configuration

### API Key Setup

The model designer uses Claude AI to interpret requirements. Configure your API key:

```bash
# Environment variable
export ANTHROPIC_API_KEY="sk-ant-..."

# Or pass via command line
rtgs suitability design --input requirements.txt --api-key "sk-ant-..."
```

**Get an API key:** https://console.anthropic.com/

## Troubleshooting

### Database Connection Issues

**Error:** `Database URL not configured`

**Solution:** Set the `SUITABILITY_DB_URL` environment variable or pass `--db-url` option.

---

**Error:** `Failed to connect to PostGIS database`

**Solution:**
1. Check that PostgreSQL is running: `pg_isready -h localhost -p 5432`
2. Verify database exists: `psql -U postgres -l | grep rtgs_suitability_data`
3. Test connection: `psql -U postgres -d rtgs_suitability_data -c "SELECT PostGIS_Version()"`

---

**Error:** `Dataset not found in PostGIS or spatial_data`

**Solution:** The dataset name in your requirements doesn't match any available dataset. Check available datasets:

```python
from rtgs_lab_tools.suitability_modeling.core.dataset_registry import get_all_available_datasets

datasets = get_all_available_datasets()
for name in sorted(datasets.keys()):
    print(f"- {name}: {datasets[name]['description']}")
```

### Performance Optimization

For large areas or many datasets:

1. **Use PostGIS for large datasets** - Database queries are faster than file loading
2. **Filter by bounding box** - The execution engine can filter PostGIS data spatially
3. **Limit grid resolution** - Reduce cell size or use sampling for initial testing

## Security Notes

**Never commit database passwords to git!**

Use environment variables or secure credential management:

```bash
# Good - environment variable
export SUITABILITY_DB_PASSWORD="secret"

# Good - credential manager
# (Windows Credential Manager, macOS Keychain, etc.)

# Bad - hardcoded in scripts
db_url = "postgresql://postgres:mysecretpassword@..."  # DON'T DO THIS
```

For production deployments, consider:
- Using PostgreSQL `.pgpass` file for passwordless authentication
- Setting up role-based access control (RBAC)
- Using connection pooling for better performance
