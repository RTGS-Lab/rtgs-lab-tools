# PostGIS Data Source Architecture

**Status:** Implementation Phase
**Purpose:** PostGIS database as centralized spatial data source for suitability modeling
**Branch:** ben/etl-pipeline-v0

---

## Executive Summary

This document describes the PostGIS-based data architecture that replaces the incomplete `spatial_data` module as the primary data source for suitability modeling. All spatial datasets (public and private) are stored in a PostgreSQL/PostGIS database, providing reliable, performant access to vetted datasets with proper spatial indexing and metadata tracking.

### Why PostGIS Instead of spatial_data Module?

**Problem**: The `spatial_data` module's public API extraction approach hit roadblocks:
- Not all required datasets available via public APIs
- Mix of public and private datasets needed
- API reliability and rate limiting issues

**Solution**: Centralized PostGIS database provides:
- ✅ Single source for all datasets (public + private)
- ✅ Complete control over data availability
- ✅ Production-ready infrastructure
- ✅ Better performance with spatial indexing
- ✅ Proper CRS management (fixes suitability_modeling Critical Issue #2)
- ✅ Efficient spatial queries (study area filtering)
- ✅ Multi-user access for lab researchers
- ✅ Metadata tracking and data governance

---

## Database Architecture

### Database: `rtgs_spatial_data`

PostgreSQL database with PostGIS extension for spatial data management.

### Schema Design

```
rtgs_spatial_data (database)
│
├── public (schema) - Main spatial datasets
│   ├── mn_wildlife_areas
│   ├── mn_scientific_natural_areas
│   ├── mn_land_use
│   ├── mn_watersheds
│   ├── mn_county_boundaries
│   ├── mn_parks
│   ├── mn_water_bodies
│   ├── mn_wetlands
│   ├── mn_roads
│   ├── hennepin_parcel_data (private)
│   └── ... (additional datasets)
│
└── metadata (schema) - Data catalog and documentation
    ├── dataset_registry
    ├── dataset_sources
    └── column_definitions
```

---

## Core Tables

### 1. Spatial Dataset Tables (public schema)

Each spatial dataset is stored as a separate table with:
- **Geometry column**: Always named `geom` (standardized)
- **Original attributes**: Preserved from source
- **Primary key**: `id` (auto-generated if not present)
- **Spatial index**: GiST index on `geom` column
- **Consistent CRS**: All data in **EPSG:26915** (NAD83 / UTM Zone 15N)

**Naming Convention**: `{state}_{dataset_name}` (lowercase, underscores)

**Example Table Structure**:
```sql
CREATE TABLE public.mn_wildlife_areas (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(MultiPolygon, 26915) NOT NULL,
    site_name TEXT,
    mgmt_unit TEXT,
    acres NUMERIC,
    county TEXT,
    -- ... other attributes from source
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mn_wildlife_areas_geom ON public.mn_wildlife_areas USING GIST(geom);
```

### 2. Dataset Registry (metadata.dataset_registry)

Central catalog of all available datasets for suitability modeling.

```sql
CREATE TABLE metadata.dataset_registry (
    dataset_id SERIAL PRIMARY KEY,
    dataset_name TEXT UNIQUE NOT NULL,           -- e.g., 'mn_wildlife_areas'
    table_name TEXT NOT NULL,                    -- e.g., 'public.mn_wildlife_areas'
    display_name TEXT NOT NULL,                  -- e.g., 'Minnesota Wildlife Management Areas'
    description TEXT,
    geometry_type TEXT,                          -- Point, LineString, Polygon, etc.
    srid INTEGER DEFAULT 26915,
    extent_geom GEOMETRY(Polygon, 26915),        -- Bounding box of dataset
    feature_count INTEGER,
    data_source TEXT,                            -- 'MN Geospatial Commons', 'County GIS', etc.
    is_public BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,              -- Available for use?
    tags TEXT[],                                 -- ['wildlife', 'protected_areas', 'conservation']
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Example row
INSERT INTO metadata.dataset_registry (
    dataset_name, table_name, display_name, description,
    geometry_type, data_source, tags
) VALUES (
    'mn_wildlife_areas',
    'public.mn_wildlife_areas',
    'Minnesota Wildlife Management Areas',
    'Wildlife Management Areas (WMAs) managed by MN DNR for wildlife habitat',
    'MultiPolygon',
    'MN Geospatial Commons',
    ARRAY['wildlife', 'protected_areas', 'conservation', 'dnr']
);
```

### 3. Dataset Sources (metadata.dataset_sources)

Tracks provenance and update information.

```sql
CREATE TABLE metadata.dataset_sources (
    source_id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES metadata.dataset_registry(dataset_id),
    source_type TEXT,                            -- 'esri_fgdb', 'shapefile', 'api', 'manual'
    source_path TEXT,                            -- Original file path or URL
    source_date DATE,                            -- When source data was published
    import_date TIMESTAMP,                       -- When loaded into PostGIS
    import_method TEXT,                          -- 'migration_script', 'manual', 'automated'
    notes TEXT,
    md5_hash TEXT                                -- Verify data hasn't changed
);
```

### 4. Column Definitions (metadata.column_definitions)

Data dictionary for understanding dataset attributes (helps Claude AI understand schemas).

```sql
CREATE TABLE metadata.column_definitions (
    column_id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES metadata.dataset_registry(dataset_id),
    column_name TEXT NOT NULL,
    data_type TEXT,
    description TEXT,
    example_values TEXT[],                       -- Sample values for reference
    is_categorical BOOLEAN,
    category_mapping JSONB,                      -- For categorical columns: {'forest': 'Forest', 'urban': 'Urban'}
    units TEXT,                                  -- 'meters', 'acres', 'degrees', etc.
    UNIQUE(dataset_id, column_name)
);

-- Example rows for land_use dataset
INSERT INTO metadata.column_definitions (dataset_id, column_name, data_type, description, is_categorical, category_mapping) VALUES
((SELECT dataset_id FROM metadata.dataset_registry WHERE dataset_name = 'mn_land_use'),
 'landuse_code', 'INTEGER', 'NLCD land use classification code', TRUE,
 '{"11": "Open Water", "21": "Developed, Open Space", "41": "Deciduous Forest", "81": "Pasture/Hay"}'::jsonb);
```

---

## Key Design Decisions

### 1. Unified CRS: EPSG:26915 (NAD83 / UTM Zone 15N)

**Why?**
- Minnesota-appropriate projected coordinate system
- **Fixes Critical Issue #2**: Distance calculations in meters, not degrees
- Enables accurate distance-based scoring functions
- All datasets transformed on import

**Trade-offs**:
- Small distortion at state boundaries (acceptable for county-level analysis)
- Must reproject if working outside Minnesota (future consideration)

### 2. Standardized Geometry Column Name: `geom`

**Why?**
- Consistent querying across all datasets
- Simplifies suitability_modeling integration
- PostGIS convention

### 3. Separate Schema for Metadata

**Why?**
- Clean separation: data vs. data-about-data
- Easier permissions management
- Clear organization

### 4. Dataset Registry as Single Source of Truth

**Why?**
- Replaces `spatial_data.registry.list_available_datasets()`
- Dynamic dataset discovery
- Supports filtering (tags, geometry_type, is_public)
- Extensible metadata

---

## Integration with Suitability Modeling

### Current Integration (spatial_data module)

```python
# Old approach - uses spatial_data module
from rtgs_lab_tools.spatial_data import extract_spatial_data

gdf = extract_spatial_data('wildlife_areas')
```

### New Integration (PostGIS)

```python
# New approach - queries PostGIS database
from rtgs_lab_tools.suitability_modeling.data import SpatialDataManager

data_manager = SpatialDataManager(db_config)
gdf = data_manager.get_dataset('mn_wildlife_areas', study_area_bounds=hennepin_bounds)
```

### Proposed `SpatialDataManager` Class

New module: `src/rtgs_lab_tools/suitability_modeling/data/spatial_data_manager.py`

**Key Methods**:
```python
class SpatialDataManager:
    def __init__(self, db_config):
        """Initialize with database configuration."""
        pass

    def list_available_datasets(self, tags=None, geometry_type=None):
        """Query metadata.dataset_registry for available datasets."""
        pass

    def get_dataset(self, dataset_name, study_area_bounds=None, buffer_meters=None):
        """Load dataset as GeoDataFrame, optionally clipped to study area."""
        pass

    def get_dataset_metadata(self, dataset_name):
        """Get full metadata for a dataset including column definitions."""
        pass

    def get_column_definitions(self, dataset_name):
        """Get data dictionary for dataset columns (helps Claude understand schema)."""
        pass
```

### Benefits for Suitability Modeling

1. **Study Area Filtering**: Can clip/filter at query time
   ```python
   gdf = manager.get_dataset('mn_wildlife_areas', study_area_bounds=hennepin_county_geom)
   # Returns only features intersecting Hennepin County
   ```

2. **Proper Distance Calculations**: Data in projected CRS
   ```python
   # Distance calculations now accurate in meters
   distances = gdf.geometry.distance(point)  # Results in meters, not degrees
   ```

3. **Column Schema Awareness**: Claude can see column definitions
   ```python
   columns = manager.get_column_definitions('mn_land_use')
   # Claude knows actual column names, not just guessing
   ```

4. **Performance**: Spatial indexes make queries fast
   ```sql
   -- PostGIS uses spatial index for efficient filtering
   SELECT * FROM mn_wildlife_areas WHERE ST_Intersects(geom, study_area_geom);
   ```

---

## Migration Process

### Source: ESRI File Geodatabase (FGDB)

All datasets currently in `.gdb` format (ESRI proprietary).

### Migration Steps

1. **Create Database and Schema** (SQL script)
2. **Load Spatial Datasets** (Python script using GeoPandas)
3. **Populate Metadata Tables** (Python/SQL)
4. **Create Spatial Indexes** (SQL)
5. **Validate Data** (Python script)

### Migration Scripts

Located in: `src/rtgs_lab_tools/suitability_modeling/data/migrations/`

```
migrations/
├── 001_create_schema.sql           # Create database, schemas, metadata tables
├── 002_load_fgdb_data.py           # Load all feature classes from FGDB
├── 003_populate_metadata.py        # Populate dataset_registry and column_definitions
├── 004_create_indexes.sql          # Create spatial indexes
└── 005_validate_data.py            # Verify data integrity
```

---

## Database Configuration

### Environment Variables

```bash
# PostgreSQL connection
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=rtgs_spatial_data
export POSTGRES_USER=rtgs_admin
export POSTGRES_PASSWORD=<secure_password>
```

### Connection String Format

```python
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"
```

### Recommended PostgreSQL Setup

**Extensions Required**:
- `postgis` - Spatial data support
- `postgis_topology` - Topology support (optional)
- `pg_trgm` - Fuzzy text search for dataset names

```sql
CREATE DATABASE rtgs_spatial_data;
\c rtgs_spatial_data
CREATE EXTENSION postgis;
CREATE EXTENSION pg_trgm;
```

---

## Performance Considerations

### Spatial Indexes

All geometry columns have GiST indexes:
```sql
CREATE INDEX idx_{table_name}_geom ON {table_name} USING GIST(geom);
```

**Impact**: 10-100x faster spatial queries

### Study Area Queries

Efficient bounding box filtering:
```sql
-- Fast: Uses spatial index
SELECT * FROM mn_wildlife_areas
WHERE geom && ST_MakeEnvelope(xmin, ymin, xmax, ymax, 26915);

-- Even better: Actual intersection
SELECT * FROM mn_wildlife_areas
WHERE ST_Intersects(geom, study_area_boundary);
```

### Connection Pooling

Use `psycopg2.pool` or SQLAlchemy connection pooling for multiple queries:
```python
from sqlalchemy import create_engine
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
```

---

## Data Governance

### Access Control

**Public Datasets**: Readable by all lab members
**Private Datasets**: Restricted access (e.g., parcel data, proprietary datasets)

```sql
-- Create read-only role for general users
CREATE ROLE rtgs_readonly;
GRANT USAGE ON SCHEMA public, metadata TO rtgs_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public, metadata TO rtgs_readonly;
```

### Audit Trail

Track when datasets are accessed (optional, for sensitive data):
```sql
CREATE TABLE metadata.access_log (
    access_id SERIAL PRIMARY KEY,
    dataset_name TEXT,
    user_name TEXT,
    access_timestamp TIMESTAMP DEFAULT NOW(),
    query_type TEXT  -- 'list', 'query', 'export'
);
```

---

## Future Enhancements

### 1. Automated Data Updates

Python script to refresh public datasets from sources:
```python
# updates/refresh_public_datasets.py
def refresh_dataset(dataset_name):
    """Re-download and update a public dataset."""
    pass
```

### 2. Data Versioning

Track dataset versions for reproducibility:
```sql
CREATE TABLE metadata.dataset_versions (
    version_id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES metadata.dataset_registry(dataset_id),
    version_number TEXT,
    effective_date DATE,
    archived_table_name TEXT  -- e.g., 'public.mn_wildlife_areas_v2024'
);
```

### 3. Spatial Data Catalog UI

Web interface to browse available datasets, preview geometries, view metadata.

### 4. Quality Checks

Automated validation on import:
- Geometry validity (ST_IsValid)
- CRS verification
- Null geometry detection
- Topology checks

---

## Comparison: spatial_data vs PostGIS

| Feature | spatial_data Module | PostGIS Database |
|---------|-------------------|------------------|
| **Data Source** | Public APIs only | Public + Private |
| **Reliability** | API-dependent | Fully controlled |
| **Performance** | Download on demand | Pre-loaded, indexed |
| **CRS Management** | Variable | Standardized (EPSG:26915) |
| **Spatial Queries** | GeoPandas in-memory | PostGIS optimized |
| **Multi-user** | No | Yes |
| **Metadata** | Limited | Comprehensive |
| **Study Area Filtering** | Manual post-load | Efficient at query time |
| **Setup Complexity** | Low | Medium |
| **Production Ready** | No | Yes |

---

## Migration Timeline

1. **Phase 1**: Create schema and load datasets (Week 1)
   - Run migration scripts
   - Load all FGDB feature classes
   - Populate metadata

2. **Phase 2**: Build SpatialDataManager class (Week 1)
   - Implement data access methods
   - Integration with suitability_modeling

3. **Phase 3**: Update suitability_modeling module (Week 2)
   - Replace spatial_data calls
   - Fix Critical Issue #2 (CRS)
   - Implement study area filtering

4. **Phase 4**: Testing and validation (Week 2)
   - Verify all datasets accessible
   - Test suitability model execution
   - Performance benchmarking

---

## References

- **PostGIS Documentation**: https://postgis.net/docs/
- **GeoPandas I/O**: https://geopandas.org/en/stable/docs/user_guide/io.html
- **EPSG:26915 (UTM 15N)**: https://epsg.io/26915
- **Existing DatabaseManager**: `src/rtgs_lab_tools/shared/database.py`

---

## Contact

For questions about this architecture:
- Ben Langenberg (implementation)
- RTGS Lab team (requirements)
