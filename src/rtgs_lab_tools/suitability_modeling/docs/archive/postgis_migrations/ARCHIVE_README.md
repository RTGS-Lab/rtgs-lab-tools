# Archived PostGIS Migration Scripts

These migration scripts were used to load Hennepin County FGDB data into a PostGIS database.

**These scripts are no longer needed for normal use.** The suitability_modeling module now reads directly from the FGDB file via the `spatial_data` module.

## Current Architecture

Users should:
1. Set the `RTGS_FGDB_PATH` environment variable to point to their FGDB file
2. Use `rtgs suitability list-datasets` to see available datasets
3. The `spatial_data` module handles all data extraction

## When to Use These Scripts

These scripts may still be useful for:
- Lab-internal PostGIS database setup
- Data validation and quality checks
- Understanding the original data structure

## Scripts

- `001_create_schema.sql` - Creates PostGIS schema and metadata tables
- `002_load_fgdb_data.py` - Loads feature classes from ESRI FGDB
- `003_populate_metadata.py` - Generates column definitions
- `004_verify_indexes.sql` - Verifies spatial indexes
- `005_validate_data.py` - Comprehensive data validation
- `fix_registration.sql` - Registers datasets in catalog
- `load_shapefile.py` - Loads shapefile data
