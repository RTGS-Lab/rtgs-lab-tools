-- PostGIS Schema for Spatial Data ETL Pipeline
-- Database: rtgs_lab_tools
-- Purpose: Metadata catalog and logging for spatial datasets

-- Enable PostGIS extension (run as superuser if needed)
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- =====================================================
-- SPATIAL DATASETS CATALOG
-- =====================================================

-- Table: spatial_datasets
-- Purpose: Registry of available spatial datasets
CREATE TABLE IF NOT EXISTS spatial_datasets (
    id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    source_type VARCHAR(50) NOT NULL,  -- 'mn_geospatial', 'gee', etc.
    source_url TEXT,
    download_url TEXT,
    spatial_type VARCHAR(50),          -- 'polygon', 'point', 'raster', etc.
    coordinate_system VARCHAR(20),     -- 'EPSG:4326', 'EPSG:26915', etc.
    update_frequency VARCHAR(50),      -- 'yearly', 'monthly', 'static'
    model_critical BOOLEAN DEFAULT FALSE,
    expected_features INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_spatial_datasets_name ON spatial_datasets(dataset_name);
CREATE INDEX IF NOT EXISTS idx_spatial_datasets_source ON spatial_datasets(source_type);

-- =====================================================
-- EXTRACTION LOGS
-- =====================================================

-- Table: spatial_extractions
-- Purpose: Log every ETL extraction run with metadata
CREATE TABLE IF NOT EXISTS spatial_extractions (
    id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(100) NOT NULL,
    extraction_start TIMESTAMP NOT NULL,
    extraction_end TIMESTAMP NOT NULL,
    duration_seconds NUMERIC(10,3),
    success BOOLEAN NOT NULL,
    records_extracted INTEGER DEFAULT 0,
    output_file TEXT,
    file_size_mb NUMERIC(10,3),
    output_format VARCHAR(20),          -- 'geoparquet', 'shapefile', 'csv'
    crs VARCHAR(20),
    geometry_type VARCHAR(50),
    bounds_minx NUMERIC,               -- Spatial extent
    bounds_miny NUMERIC,
    bounds_maxx NUMERIC,
    bounds_maxy NUMERIC,
    columns_extracted TEXT[],          -- Array of column names
    error_message TEXT,
    note TEXT,
    git_commit_hash VARCHAR(40),       -- For reproducibility
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key to datasets catalog
    CONSTRAINT fk_dataset FOREIGN KEY (dataset_name) 
        REFERENCES spatial_datasets(dataset_name) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_extractions_dataset ON spatial_extractions(dataset_name);
CREATE INDEX IF NOT EXISTS idx_extractions_timestamp ON spatial_extractions(extraction_start);
CREATE INDEX IF NOT EXISTS idx_extractions_success ON spatial_extractions(success);

-- =====================================================
-- DATA LINEAGE AND QUALITY
-- =====================================================

-- Table: spatial_data_quality
-- Purpose: Track data quality metrics over time
CREATE TABLE IF NOT EXISTS spatial_data_quality (
    id SERIAL PRIMARY KEY,
    extraction_id INTEGER NOT NULL,
    valid_geometries INTEGER DEFAULT 0,
    invalid_geometries INTEGER DEFAULT 0,
    null_geometries INTEGER DEFAULT 0,
    geometry_validation_passed BOOLEAN DEFAULT FALSE,
    crs_validation_passed BOOLEAN DEFAULT FALSE,
    attribute_completeness NUMERIC(5,2), -- Percentage (0-100)
    spatial_index_created BOOLEAN DEFAULT FALSE,
    quality_score NUMERIC(3,1),        -- Overall score 0-10
    quality_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_extraction FOREIGN KEY (extraction_id) 
        REFERENCES spatial_extractions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_quality_extraction ON spatial_data_quality(extraction_id);

-- =====================================================
-- DATASET UPDATE TRACKING
-- =====================================================

-- Table: spatial_dataset_updates
-- Purpose: Track when source datasets were last updated
CREATE TABLE IF NOT EXISTS spatial_dataset_updates (
    id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(100) NOT NULL,
    source_last_modified TIMESTAMP,
    source_etag VARCHAR(255),          -- HTTP ETag for change detection
    source_checksum VARCHAR(64),       -- SHA256 of source data
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_available BOOLEAN DEFAULT FALSE,
    update_notes TEXT,
    
    CONSTRAINT fk_dataset_updates FOREIGN KEY (dataset_name) 
        REFERENCES spatial_datasets(dataset_name) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_updates_dataset ON spatial_dataset_updates(dataset_name);
CREATE INDEX IF NOT EXISTS idx_updates_checked ON spatial_dataset_updates(last_checked);

-- =====================================================
-- SPATIAL DATA STORAGE (OPTIONAL)
-- =====================================================

-- Note: For large datasets, store in files (GeoParquet) and catalog here
-- For small datasets or analysis results, can store geometry directly

-- Example table for storing processed spatial data in PostGIS
-- CREATE TABLE IF NOT EXISTS spatial_data_cache (
--     id SERIAL PRIMARY KEY,
--     dataset_name VARCHAR(100) NOT NULL,
--     feature_id VARCHAR(100),
--     geometry GEOMETRY,
--     attributes JSONB,
--     extraction_id INTEGER,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     
--     CONSTRAINT fk_cache_extraction FOREIGN KEY (extraction_id) 
--         REFERENCES spatial_extractions(id) ON DELETE CASCADE
-- );

-- CREATE INDEX IF NOT EXISTS idx_cache_dataset ON spatial_data_cache(dataset_name);
-- CREATE INDEX IF NOT EXISTS idx_cache_geom ON spatial_data_cache USING GIST(geometry);

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- View: Latest successful extractions per dataset
CREATE OR REPLACE VIEW latest_extractions AS
SELECT DISTINCT ON (dataset_name)
    dataset_name,
    extraction_start,
    records_extracted,
    output_file,
    file_size_mb,
    duration_seconds
FROM spatial_extractions
WHERE success = TRUE
ORDER BY dataset_name, extraction_start DESC;

-- View: Dataset summary with latest extraction info
CREATE OR REPLACE VIEW dataset_summary AS
SELECT 
    d.dataset_name,
    d.description,
    d.source_type,
    d.spatial_type,
    d.expected_features,
    le.extraction_start as last_extracted,
    le.records_extracted,
    le.file_size_mb,
    CASE 
        WHEN le.extraction_start IS NULL THEN 'Never extracted'
        WHEN le.extraction_start < NOW() - INTERVAL '30 days' THEN 'Stale'
        ELSE 'Recent'
    END as status
FROM spatial_datasets d
LEFT JOIN latest_extractions le ON d.dataset_name = le.dataset_name
ORDER BY d.dataset_name;

-- View: Extraction success rate by dataset
CREATE OR REPLACE VIEW extraction_success_rates AS
SELECT 
    dataset_name,
    COUNT(*) as total_attempts,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_attempts,
    ROUND(
        100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 
        2
    ) as success_rate_percent,
    MAX(extraction_start) as last_attempt
FROM spatial_extractions
GROUP BY dataset_name
ORDER BY success_rate_percent DESC;

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Insert existing datasets from registry
INSERT INTO spatial_datasets (
    dataset_name, description, source_type, source_url, download_url,
    spatial_type, coordinate_system, update_frequency, model_critical, expected_features
) VALUES 
(
    'protected_areas',
    'DNR Wildlife Management Areas',
    'mn_geospatial',
    'https://gisdata.mn.gov/dataset/bdry-dnr-wildlife-mgmt-areas-pub',
    'https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dnr/bdry_dnr_wildlife_mgmt_areas_pub/gpkg_bdry_dnr_wildlife_mgmt_areas_pub.zip',
    'multipolygon',
    'EPSG:26915',
    'yearly',
    TRUE,
    1731
),
(
    'groundwater_recharge',
    'Mean annual potential groundwater recharge rates from 1996-2010 for Minnesota',
    'mn_geospatial',
    'https://gisdata.mn.gov/id/dataset/geos-gw-recharge-1996-2010-mean',
    'https://resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_pca/geos_gw_recharge_1996_2010_mean/aaigrid_geos_gw_recharge_1996_2010_mean.zip',
    'raster',
    'unknown',
    'static',
    TRUE,
    201264
) ON CONFLICT (dataset_name) DO NOTHING;

-- =====================================================
-- FUNCTIONS FOR COMMON OPERATIONS
-- =====================================================

-- Function: Get dataset extraction history
CREATE OR REPLACE FUNCTION get_dataset_history(p_dataset_name VARCHAR)
RETURNS TABLE(
    extraction_date TIMESTAMP,
    success BOOLEAN,
    records INTEGER,
    duration NUMERIC,
    file_size NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        extraction_start,
        spatial_extractions.success,
        records_extracted,
        duration_seconds,
        file_size_mb
    FROM spatial_extractions
    WHERE dataset_name = p_dataset_name
    ORDER BY extraction_start DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- Function: Update dataset last modified time
CREATE OR REPLACE FUNCTION update_dataset_check(
    p_dataset_name VARCHAR,
    p_last_modified TIMESTAMP DEFAULT NULL,
    p_etag VARCHAR DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO spatial_dataset_updates (
        dataset_name, source_last_modified, source_etag, last_checked
    ) VALUES (
        p_dataset_name, p_last_modified, p_etag, CURRENT_TIMESTAMP
    )
    ON CONFLICT (dataset_name) 
    DO UPDATE SET
        source_last_modified = EXCLUDED.source_last_modified,
        source_etag = EXCLUDED.source_etag,
        last_checked = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- PERMISSIONS (adjust as needed for your setup)
-- =====================================================

-- Grant permissions to application user
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rtgs_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO rtgs_app_user;

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================

COMMENT ON TABLE spatial_datasets IS 'Registry of available spatial datasets for extraction';
COMMENT ON TABLE spatial_extractions IS 'Log of all spatial data extraction attempts with metadata';
COMMENT ON TABLE spatial_data_quality IS 'Quality metrics for each extraction';
COMMENT ON TABLE spatial_dataset_updates IS 'Tracking of source dataset modifications';

COMMENT ON COLUMN spatial_extractions.bounds_minx IS 'Minimum X coordinate of dataset extent';
COMMENT ON COLUMN spatial_extractions.git_commit_hash IS 'Git commit for reproducibility';
COMMENT ON COLUMN spatial_data_quality.quality_score IS 'Overall quality score 0-10 based on multiple metrics';