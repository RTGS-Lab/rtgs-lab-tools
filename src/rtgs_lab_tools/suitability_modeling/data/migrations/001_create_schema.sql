-- ============================================================================
-- PostGIS Spatial Data Schema - Initial Setup
-- ============================================================================
-- Purpose: Create database, schemas, and metadata tables for spatial datasets
-- Database: rtgs_spatial_data
-- Author: RTGS Lab
-- Date: 2025-01-09
-- ============================================================================

-- ============================================================================
-- SETUP INSTRUCTIONS
-- ============================================================================
-- 1. Create the database (run as postgres superuser):
--    CREATE DATABASE rtgs_spatial_data;
--
-- 2. Connect to the database:
--    \c rtgs_spatial_data
--
-- 3. Run this script:
--    \i 001_create_schema.sql
--
-- OR run via psql:
--    psql -U postgres -d rtgs_spatial_data -f 001_create_schema.sql
-- ============================================================================

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Fuzzy text search

-- ============================================================================
-- SCHEMAS
-- ============================================================================

-- Metadata schema for data catalog and documentation
CREATE SCHEMA IF NOT EXISTS metadata;

COMMENT ON SCHEMA metadata IS 'Metadata, data catalog, and documentation for spatial datasets';
COMMENT ON SCHEMA public IS 'Spatial datasets for suitability modeling and analysis';

-- ============================================================================
-- METADATA TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Dataset Registry - Central catalog of all available datasets
-- ----------------------------------------------------------------------------
CREATE TABLE metadata.dataset_registry (
    dataset_id SERIAL PRIMARY KEY,
    dataset_name TEXT UNIQUE NOT NULL,           -- e.g., 'mn_wildlife_areas'
    table_name TEXT NOT NULL,                    -- e.g., 'public.mn_wildlife_areas'
    display_name TEXT NOT NULL,                  -- e.g., 'Minnesota Wildlife Management Areas'
    description TEXT,
    geometry_type TEXT,                          -- Point, LineString, Polygon, MultiPolygon, etc.
    srid INTEGER DEFAULT 26915,                  -- EPSG:26915 (NAD83 / UTM 15N)
    extent_geom GEOMETRY(Polygon, 26915),        -- Bounding box of dataset
    feature_count INTEGER,
    data_source TEXT,                            -- 'MN Geospatial Commons', 'County GIS', etc.
    is_public BOOLEAN DEFAULT TRUE,              -- Public or private dataset
    is_active BOOLEAN DEFAULT TRUE,              -- Available for use in suitability modeling
    tags TEXT[],                                 -- ['wildlife', 'protected_areas', 'conservation']
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_geometry_type CHECK (
        geometry_type IN ('Point', 'LineString', 'Polygon', 'MultiPoint', 'MultiLineString', 'MultiPolygon', 'GeometryCollection')
    )
);

COMMENT ON TABLE metadata.dataset_registry IS 'Central catalog of all spatial datasets available for suitability modeling';
COMMENT ON COLUMN metadata.dataset_registry.dataset_name IS 'Internal identifier used in code (lowercase, underscores)';
COMMENT ON COLUMN metadata.dataset_registry.table_name IS 'Fully qualified table name (schema.table)';
COMMENT ON COLUMN metadata.dataset_registry.display_name IS 'Human-readable name for UI/reports';
COMMENT ON COLUMN metadata.dataset_registry.srid IS 'Spatial Reference System Identifier (default: EPSG:26915 for Minnesota)';
COMMENT ON COLUMN metadata.dataset_registry.extent_geom IS 'Bounding box of dataset for quick spatial queries';
COMMENT ON COLUMN metadata.dataset_registry.is_active IS 'Whether dataset is available for use (allows disabling without deletion)';
COMMENT ON COLUMN metadata.dataset_registry.tags IS 'Searchable tags for dataset discovery';

-- Indexes
CREATE INDEX idx_dataset_registry_tags ON metadata.dataset_registry USING GIN(tags);
CREATE INDEX idx_dataset_registry_geometry_type ON metadata.dataset_registry(geometry_type);
CREATE INDEX idx_dataset_registry_is_active ON metadata.dataset_registry(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_dataset_registry_name_trgm ON metadata.dataset_registry USING GIN(dataset_name gin_trgm_ops);

-- ----------------------------------------------------------------------------
-- Dataset Sources - Provenance and update tracking
-- ----------------------------------------------------------------------------
CREATE TABLE metadata.dataset_sources (
    source_id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES metadata.dataset_registry(dataset_id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,                   -- 'esri_fgdb', 'shapefile', 'api', 'manual', 'postgis'
    source_path TEXT,                            -- Original file path or URL
    source_date DATE,                            -- When source data was published
    import_date TIMESTAMP DEFAULT NOW(),         -- When loaded into PostGIS
    import_method TEXT,                          -- 'migration_script', 'manual', 'automated'
    imported_by TEXT,                            -- User who imported the data
    notes TEXT,
    md5_hash TEXT,                               -- Verify data integrity
    original_crs TEXT,                           -- Original coordinate reference system
    transformed_crs TEXT DEFAULT 'EPSG:26915',   -- CRS after transformation
    CONSTRAINT valid_source_type CHECK (
        source_type IN ('esri_fgdb', 'shapefile', 'geojson', 'geopackage', 'api', 'wfs', 'manual', 'postgis')
    )
);

COMMENT ON TABLE metadata.dataset_sources IS 'Tracks data provenance and import history';
COMMENT ON COLUMN metadata.dataset_sources.source_type IS 'Type of original data source';
COMMENT ON COLUMN metadata.dataset_sources.source_path IS 'File path or URL of original data';
COMMENT ON COLUMN metadata.dataset_sources.import_date IS 'Timestamp when data was loaded into PostGIS';
COMMENT ON COLUMN metadata.dataset_sources.md5_hash IS 'Hash of source file for change detection';

-- Indexes
CREATE INDEX idx_dataset_sources_dataset_id ON metadata.dataset_sources(dataset_id);

-- ----------------------------------------------------------------------------
-- Column Definitions - Data dictionary for dataset attributes
-- ----------------------------------------------------------------------------
CREATE TABLE metadata.column_definitions (
    column_id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES metadata.dataset_registry(dataset_id) ON DELETE CASCADE,
    column_name TEXT NOT NULL,
    data_type TEXT,                              -- 'TEXT', 'INTEGER', 'NUMERIC', 'DATE', etc.
    description TEXT,
    example_values TEXT[],                       -- Sample values for reference
    is_categorical BOOLEAN DEFAULT FALSE,        -- Whether column contains categorical data
    category_mapping JSONB,                      -- For categorical: {'code': 'label'} mapping
    units TEXT,                                  -- 'meters', 'acres', 'degrees', 'count', etc.
    is_nullable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_dataset_column UNIQUE(dataset_id, column_name)
);

COMMENT ON TABLE metadata.column_definitions IS 'Data dictionary explaining dataset columns (helps LLM understand schemas)';
COMMENT ON COLUMN metadata.column_definitions.column_name IS 'Name of column in dataset table';
COMMENT ON COLUMN metadata.column_definitions.is_categorical IS 'Whether column should be treated as categorical for analysis';
COMMENT ON COLUMN metadata.column_definitions.category_mapping IS 'JSON mapping of codes to human-readable labels';
COMMENT ON COLUMN metadata.column_definitions.example_values IS 'Sample values to help understand column content';

-- Indexes
CREATE INDEX idx_column_definitions_dataset_id ON metadata.column_definitions(dataset_id);
CREATE INDEX idx_column_definitions_categorical ON metadata.column_definitions(is_categorical) WHERE is_categorical = TRUE;

-- ----------------------------------------------------------------------------
-- Dataset Versions (Optional) - Track dataset history
-- ----------------------------------------------------------------------------
CREATE TABLE metadata.dataset_versions (
    version_id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES metadata.dataset_registry(dataset_id) ON DELETE CASCADE,
    version_number TEXT NOT NULL,                -- 'v1.0', '2024-01', etc.
    effective_date DATE NOT NULL,
    archived_table_name TEXT,                    -- e.g., 'public.mn_wildlife_areas_v2024'
    is_current BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_dataset_version UNIQUE(dataset_id, version_number)
);

COMMENT ON TABLE metadata.dataset_versions IS 'Version history for datasets (for reproducibility)';
COMMENT ON COLUMN metadata.dataset_versions.archived_table_name IS 'Table name where old version is archived';
COMMENT ON COLUMN metadata.dataset_versions.is_current IS 'Whether this is the active version';

-- Indexes
CREATE INDEX idx_dataset_versions_dataset_id ON metadata.dataset_versions(dataset_id);
CREATE INDEX idx_dataset_versions_current ON metadata.dataset_versions(dataset_id, is_current) WHERE is_current = TRUE;

-- ----------------------------------------------------------------------------
-- Access Log (Optional) - Audit trail for sensitive datasets
-- ----------------------------------------------------------------------------
CREATE TABLE metadata.access_log (
    access_id SERIAL PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    user_name TEXT,
    access_timestamp TIMESTAMP DEFAULT NOW(),
    query_type TEXT,                             -- 'list', 'query', 'export', 'download'
    query_bounds GEOMETRY(Polygon, 26915),       -- Spatial extent of query
    feature_count INTEGER,                       -- Number of features returned
    ip_address INET,
    notes TEXT
);

COMMENT ON TABLE metadata.access_log IS 'Audit trail for dataset access (useful for sensitive/private data)';

-- Indexes
CREATE INDEX idx_access_log_dataset_name ON metadata.access_log(dataset_name);
CREATE INDEX idx_access_log_timestamp ON metadata.access_log(access_timestamp DESC);
CREATE INDEX idx_access_log_user ON metadata.access_log(user_name);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Function: Update dataset registry extent and feature count
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION metadata.update_dataset_extent(
    p_dataset_name TEXT
)
RETURNS VOID AS $$
DECLARE
    v_table_name TEXT;
    v_extent GEOMETRY;
    v_count INTEGER;
BEGIN
    -- Get table name
    SELECT table_name INTO v_table_name
    FROM metadata.dataset_registry
    WHERE dataset_name = p_dataset_name;

    IF v_table_name IS NULL THEN
        RAISE EXCEPTION 'Dataset % not found in registry', p_dataset_name;
    END IF;

    -- Calculate extent and count (dynamic SQL)
    EXECUTE format('SELECT ST_SetSRID(ST_Extent(geom)::geometry, 26915), COUNT(*) FROM %I', v_table_name)
    INTO v_extent, v_count;

    -- Update registry
    UPDATE metadata.dataset_registry
    SET extent_geom = v_extent,
        feature_count = v_count,
        updated_at = NOW()
    WHERE dataset_name = p_dataset_name;

    RAISE NOTICE 'Updated extent and count for %: % features', p_dataset_name, v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION metadata.update_dataset_extent IS 'Calculate and update bounding box and feature count for a dataset';

-- ----------------------------------------------------------------------------
-- Function: Register new dataset in catalog
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION metadata.register_dataset(
    p_dataset_name TEXT,
    p_table_name TEXT,
    p_display_name TEXT,
    p_description TEXT DEFAULT NULL,
    p_geometry_type TEXT DEFAULT NULL,
    p_data_source TEXT DEFAULT NULL,
    p_is_public BOOLEAN DEFAULT TRUE,
    p_tags TEXT[] DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_dataset_id INTEGER;
BEGIN
    -- Insert into registry
    INSERT INTO metadata.dataset_registry (
        dataset_name, table_name, display_name, description,
        geometry_type, data_source, is_public, tags
    ) VALUES (
        p_dataset_name, p_table_name, p_display_name, p_description,
        p_geometry_type, p_data_source, p_is_public, p_tags
    )
    RETURNING dataset_id INTO v_dataset_id;

    -- Update extent
    PERFORM metadata.update_dataset_extent(p_dataset_name);

    RAISE NOTICE 'Registered dataset %: %', p_dataset_name, p_display_name;
    RETURN v_dataset_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION metadata.register_dataset IS 'Register a new dataset in the catalog with automatic extent calculation';

-- ============================================================================
-- VIEWS - Convenient queries
-- ============================================================================

-- ----------------------------------------------------------------------------
-- View: Active datasets with full metadata
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW metadata.v_active_datasets AS
SELECT
    dr.dataset_id,
    dr.dataset_name,
    dr.table_name,
    dr.display_name,
    dr.description,
    dr.geometry_type,
    dr.feature_count,
    dr.data_source,
    dr.is_public,
    dr.tags,
    ds.source_type,
    ds.source_date,
    ds.import_date,
    ST_AsText(ST_Envelope(dr.extent_geom)) as extent_wkt
FROM metadata.dataset_registry dr
LEFT JOIN metadata.dataset_sources ds ON dr.dataset_id = ds.dataset_id
WHERE dr.is_active = TRUE
ORDER BY dr.display_name;

COMMENT ON VIEW metadata.v_active_datasets IS 'All active datasets with source information';

-- ----------------------------------------------------------------------------
-- View: Dataset statistics
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW metadata.v_dataset_stats AS
SELECT
    geometry_type,
    COUNT(*) as dataset_count,
    SUM(feature_count) as total_features,
    COUNT(*) FILTER (WHERE is_public = TRUE) as public_count,
    COUNT(*) FILTER (WHERE is_public = FALSE) as private_count
FROM metadata.dataset_registry
WHERE is_active = TRUE
GROUP BY geometry_type;

COMMENT ON VIEW metadata.v_dataset_stats IS 'Summary statistics of datasets by geometry type';

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

-- Create read-only role for general users
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rtgs_readonly') THEN
        CREATE ROLE rtgs_readonly;
    END IF;
END
$$;

-- Grant permissions
GRANT USAGE ON SCHEMA public, metadata TO rtgs_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public, metadata TO rtgs_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA metadata TO rtgs_readonly;

-- Future tables inherit permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public, metadata
    GRANT SELECT ON TABLES TO rtgs_readonly;

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '=======================================================';
    RAISE NOTICE 'PostGIS Spatial Data Schema Created Successfully';
    RAISE NOTICE '=======================================================';
    RAISE NOTICE 'Next Steps:';
    RAISE NOTICE '1. Run 002_load_fgdb_data.py to import datasets';
    RAISE NOTICE '2. Run 003_populate_metadata.py to add column definitions';
    RAISE NOTICE '3. Run 004_create_indexes.sql to optimize queries';
    RAISE NOTICE '=======================================================';
END
$$;
