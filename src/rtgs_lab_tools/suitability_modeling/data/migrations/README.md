# PostGIS Migration Scripts

This directory contains scripts for migrating spatial datasets from an ESRI File Geodatabase to PostgreSQL/PostGIS.

## Overview

The migration process consists of five steps:

1. **Create Database Schema** - Set up database, schemas, and metadata tables
2. **Load FGDB Data** - Import feature classes from FGDB into PostGIS
3. **Populate Metadata** - Generate column definitions and data dictionary
4. **Verify Indexes** - Ensure spatial indexes exist for optimal performance
5. **Validate Data** - Comprehensive validation of migrated datasets

## Prerequisites

### Software Requirements

- **PostgreSQL** 12+ with **PostGIS** 3.0+
- **Python** 3.8+
- **GDAL** (for FGDB support)

### Python Dependencies

Install required packages:

```bash
pip install geopandas sqlalchemy psycopg2-binary fiona
```

### Database Setup

Create the database and enable PostGIS:

```sql
-- As postgres superuser
CREATE DATABASE rtgs_spatial_data;
\c rtgs_spatial_data
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
CREATE EXTENSION pg_trgm;
```

### Environment Variables

Set database connection parameters:

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=rtgs_spatial_data
export POSTGRES_USER=your_username
export POSTGRES_PASSWORD=your_password

# Or as connection string
export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
```

## Migration Steps

### Step 1: Create Database Schema

Create all necessary schemas and metadata tables.

**Run:**

```bash
psql -U postgres -d rtgs_spatial_data -f 001_create_schema.sql
```

**What it does:**
- Creates `public` schema for spatial datasets
- Creates `metadata` schema for data catalog
- Creates tables: `dataset_registry`, `dataset_sources`, `column_definitions`
- Creates helper functions for dataset management
- Sets up read-only role for general users

**Verify:**

```sql
-- Check schemas exist
\dn

-- Check metadata tables exist
\dt metadata.*

-- Expected output: dataset_registry, dataset_sources, column_definitions, etc.
```

### Step 2: Load FGDB Data

Import all feature classes from ESRI File Geodatabase into PostGIS.

**Dry run (recommended first):**

```bash
python 002_load_fgdb_data.py \
  --fgdb /path/to/your/data.gdb \
  --db-url postgresql://user:pass@localhost:5432/rtgs_spatial_data \
  --dry-run
```

**Actual migration:**

```bash
python 002_load_fgdb_data.py \
  --fgdb /path/to/your/data.gdb \
  --db-url postgresql://user:pass@localhost:5432/rtgs_spatial_data
```

**Load specific layers only:**

```bash
python 002_load_fgdb_data.py \
  --fgdb /path/to/your/data.gdb \
  --db-url postgresql://user:pass@localhost:5432/rtgs_spatial_data \
  --layers "Wildlife Areas" "Land Use" "County Boundaries"
```

**What it does:**
- Reads feature classes from FGDB
- Transforms geometries to **EPSG:26915** (NAD83 / UTM Zone 15N)
- Renames geometry column to `geom` (standard)
- Adds `id` primary key and `created_at` timestamp
- Loads data into PostGIS tables (schema: `public`, prefix: `mn_`)
- Creates spatial indexes (GiST on `geom`)
- Registers datasets in `metadata.dataset_registry`
- Records source information in `metadata.dataset_sources`

**Output:**
- Log file: `fgdb_migration.log`
- Database tables: `public.mn_{dataset_name}`
- Metadata entries in `metadata.dataset_registry`

**Verify:**

```sql
-- Check loaded tables
SELECT dataset_name, table_name, feature_count, data_source
FROM metadata.dataset_registry
ORDER BY dataset_name;

-- Check a specific dataset
SELECT COUNT(*), ST_SRID(geom) as srid
FROM public.mn_wildlife_areas
GROUP BY ST_SRID(geom);
```

### Step 3: Populate Metadata

Generate data dictionary with column definitions for all datasets.

**Run:**

```bash
python 003_populate_metadata.py \
  --db-url postgresql://user:pass@localhost:5432/rtgs_spatial_data
```

**What it does:**
- Analyzes columns in all registered datasets
- Detects categorical vs. continuous columns
- Extracts sample values
- Auto-generates column descriptions
- Detects units from column names
- Populates `metadata.column_definitions` table

**Verify:**

```sql
-- View column definitions
SELECT
    dr.dataset_name,
    cd.column_name,
    cd.data_type,
    cd.is_categorical,
    cd.units,
    cd.example_values
FROM metadata.column_definitions cd
JOIN metadata.dataset_registry dr ON cd.dataset_id = dr.dataset_id
WHERE dr.dataset_name = 'mn_land_use'
ORDER BY cd.column_name;
```

### Step 4: Verify Indexes

Ensure all geometry columns have spatial indexes.

**Run:**

```bash
psql -U postgres -d rtgs_spatial_data -f 004_verify_indexes.sql
```

**What it does:**
- Checks for missing spatial indexes
- Creates indexes on any geometry columns without them
- Runs `ANALYZE` on all tables (updates query planner statistics)
- Displays summary of spatial tables and indexes

**Verify:**

```sql
-- List all spatial indexes
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_indexes
WHERE indexname LIKE 'idx_%_geom'
ORDER BY tablename;
```

### Step 5: Validate Data

Comprehensive validation of migrated datasets.

**Run:**

```bash
python 005_validate_data.py \
  --db-url postgresql://user:pass@localhost:5432/rtgs_spatial_data
```

**What it does:**
- Verifies all tables exist
- Checks geometry columns exist
- Validates spatial indexes present
- Verifies CRS is EPSG:26915
- Checks for invalid geometries
- Checks for null geometries
- Compares feature counts with registry

**Output:**
- Validation report with pass/fail status
- List of critical issues (must fix)
- List of warnings (should review)
- Exit code 0 if all passed, 1 if issues found

**Example output:**

```
Validating: mn_wildlife_areas
------------------------------------------------------------
  ✓ Table exists
  ✓ Geometry column exists
  ✓ Spatial index exists
  ✓ CRS correct (EPSG:26915)
  ✓ All geometries valid
  ✓ No null geometries
  ✓ Feature count: 1234
```

## Post-Migration Tasks

### 1. Update Dataset Metadata

Some metadata fields should be manually updated for accuracy:

```sql
-- Add better descriptions
UPDATE metadata.dataset_registry
SET description = 'Wildlife Management Areas (WMAs) managed by Minnesota DNR for wildlife habitat conservation'
WHERE dataset_name = 'mn_wildlife_areas';

-- Add/update tags
UPDATE metadata.dataset_registry
SET tags = ARRAY['wildlife', 'protected_areas', 'conservation', 'dnr', 'habitat']
WHERE dataset_name = 'mn_wildlife_areas';

-- Mark private datasets
UPDATE metadata.dataset_registry
SET is_public = FALSE
WHERE dataset_name IN ('hennepin_parcel_data', 'private_landowner_data');
```

### 2. Update Column Descriptions

Auto-generated descriptions can be improved:

```sql
-- Update column descriptions
UPDATE metadata.column_definitions
SET description = 'NLCD Land Use Classification Code (National Land Cover Database)',
    category_mapping = '{
        "11": "Open Water",
        "21": "Developed, Open Space",
        "22": "Developed, Low Intensity",
        "23": "Developed, Medium Intensity",
        "24": "Developed, High Intensity",
        "41": "Deciduous Forest",
        "42": "Evergreen Forest",
        "43": "Mixed Forest",
        "52": "Shrub/Scrub",
        "71": "Grassland/Herbaceous",
        "81": "Pasture/Hay",
        "82": "Cultivated Crops",
        "90": "Woody Wetlands",
        "95": "Emergent Herbaceous Wetlands"
    }'::jsonb
WHERE column_name = 'landuse_code'
AND dataset_id = (SELECT dataset_id FROM metadata.dataset_registry WHERE dataset_name = 'mn_land_use');
```

### 3. Create Database Users

Set up appropriate access control:

```sql
-- Create read-only user for suitability modeling
CREATE USER rtgs_suitability WITH PASSWORD 'secure_password';
GRANT rtgs_readonly TO rtgs_suitability;
GRANT CONNECT ON DATABASE rtgs_spatial_data TO rtgs_suitability;

-- Create admin user for data management
CREATE USER rtgs_admin WITH PASSWORD 'admin_password';
GRANT ALL PRIVILEGES ON DATABASE rtgs_spatial_data TO rtgs_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public, metadata TO rtgs_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA metadata TO rtgs_admin;
```

### 4. Backup Database

Create initial backup after successful migration:

```bash
# Full database backup
pg_dump -U postgres -Fc rtgs_spatial_data > rtgs_spatial_data_initial.backup

# Restore if needed
pg_restore -U postgres -d rtgs_spatial_data rtgs_spatial_data_initial.backup
```

## Troubleshooting

### FGDB Reading Issues

If you get errors reading the FGDB:

```bash
# Check GDAL/Fiona can see the FGDB driver
python -c "import fiona; print(fiona.supported_drivers)"

# Should show 'OpenFileGDB' or 'FileGDB' in the list
```

If not, install GDAL with FGDB support:

```bash
# Ubuntu/Debian
sudo apt-get install gdal-bin libgdal-dev

# macOS
brew install gdal

# Windows - use OSGeo4W or conda
conda install -c conda-forge gdal
```

### CRS Transformation Errors

If you get CRS transformation errors:

```python
# Check if PROJ database is accessible
python -c "import pyproj; print(pyproj.datadir.get_data_dir())"

# Install proj-data if needed
conda install -c conda-forge proj-data
```

### Invalid Geometries

If validation reports invalid geometries:

```sql
-- Attempt to fix invalid geometries
UPDATE public.mn_dataset_name
SET geom = ST_MakeValid(geom)
WHERE NOT ST_IsValid(geom);

-- Check if fixed
SELECT COUNT(*) FROM public.mn_dataset_name WHERE NOT ST_IsValid(geom);
```

### Connection Errors

If you can't connect to the database:

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check connection string
psql "postgresql://user:pass@localhost:5432/rtgs_spatial_data" -c "SELECT 1"

# Check pg_hba.conf allows connections
# Edit /etc/postgresql/XX/main/pg_hba.conf if needed
```

## Maintenance

### Updating a Dataset

To update an existing dataset with new data:

1. Run migration script with new FGDB (will replace existing table)
2. Re-run metadata population
3. Re-run validation

```bash
python 002_load_fgdb_data.py \
  --fgdb /path/to/updated_data.gdb \
  --db-url postgresql://user:pass@localhost:5432/rtgs_spatial_data \
  --layers "Wildlife Areas"  # Only update specific dataset

python 003_populate_metadata.py --db-url postgresql://user:pass@localhost:5432/rtgs_spatial_data
python 005_validate_data.py --db-url postgresql://user:pass@localhost:5432/rtgs_spatial_data
```

### Adding New Datasets

To add new datasets after initial migration:

1. Place new feature class in FGDB
2. Run migration for specific layers
3. Update metadata manually if needed

### Query Performance Optimization

If queries are slow:

```sql
-- Analyze tables to update statistics
ANALYZE public.mn_dataset_name;

-- Rebuild spatial index
REINDEX INDEX idx_mn_dataset_name_geom;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

## Integration with Suitability Modeling

After successful migration, update the suitability modeling module to use PostGIS:

See: `../docs/postgis_data_source.md` for integration details.

**Key changes:**
- Create `SpatialDataManager` class to query PostGIS
- Replace `spatial_data.extract_spatial_data()` calls
- Implement study area filtering at query time
- Use column_definitions for Claude's dataset understanding

## References

- **PostGIS Documentation**: https://postgis.net/docs/
- **GeoPandas I/O**: https://geopandas.org/en/stable/docs/user_guide/io.html
- **FGDB with Python**: https://gdal.org/drivers/vector/openfilegdb.html
- **EPSG:26915**: https://epsg.io/26915 (NAD83 / UTM Zone 15N)

## Contact

For questions or issues with migration scripts:
- Ben Langenberg
- RTGS Lab team
