-- ============================================================================
-- Verify and Create Spatial Indexes
-- ============================================================================
-- Purpose: Ensure all spatial tables have proper GiST indexes on geometry columns
-- Usage: psql -U postgres -d rtgs_spatial_data -f 004_verify_indexes.sql
-- ============================================================================

-- Function to create spatial index if it doesn't exist
CREATE OR REPLACE FUNCTION create_spatial_index_if_missing(
    p_table_name TEXT,
    p_schema_name TEXT DEFAULT 'public'
)
RETURNS VOID AS $$
DECLARE
    v_index_name TEXT;
    v_full_table_name TEXT;
    v_index_exists BOOLEAN;
BEGIN
    -- Construct index name and full table name
    v_index_name := 'idx_' || p_table_name || '_geom';
    v_full_table_name := p_schema_name || '.' || p_table_name;

    -- Check if index exists
    SELECT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = p_schema_name
        AND tablename = p_table_name
        AND indexname = v_index_name
    ) INTO v_index_exists;

    IF v_index_exists THEN
        RAISE NOTICE 'Index % already exists on %', v_index_name, v_full_table_name;
    ELSE
        -- Create the index
        EXECUTE format('CREATE INDEX %I ON %I.%I USING GIST(geom)',
                      v_index_name, p_schema_name, p_table_name);
        RAISE NOTICE 'Created index % on %', v_index_name, v_full_table_name;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create indexes for all tables with geometry columns
DO $$
DECLARE
    r RECORD;
BEGIN
    RAISE NOTICE '=======================================================';
    RAISE NOTICE 'Creating spatial indexes for all geometry columns';
    RAISE NOTICE '=======================================================';

    FOR r IN
        SELECT
            f_table_schema,
            f_table_name,
            f_geometry_column
        FROM geometry_columns
        WHERE f_table_schema = 'public'
        ORDER BY f_table_name
    LOOP
        PERFORM create_spatial_index_if_missing(r.f_table_name, r.f_table_schema);
    END LOOP;

    RAISE NOTICE '=======================================================';
    RAISE NOTICE 'Spatial index verification complete';
    RAISE NOTICE '=======================================================';
END;
$$;

-- ============================================================================
-- Index Statistics
-- ============================================================================

-- Show all spatial indexes
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE 'idx_%_geom'
ORDER BY tablename;

-- ============================================================================
-- Analyze Tables
-- ============================================================================
-- Update table statistics for query optimization

DO $$
DECLARE
    r RECORD;
BEGIN
    RAISE NOTICE '=======================================================';
    RAISE NOTICE 'Analyzing tables for query optimization';
    RAISE NOTICE '=======================================================';

    FOR r IN
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    LOOP
        EXECUTE 'ANALYZE public.' || r.table_name;
        RAISE NOTICE 'Analyzed table: %', r.table_name;
    END LOOP;
END;
$$;

-- ============================================================================
-- Summary Report
-- ============================================================================

SELECT
    'Total Spatial Tables' as metric,
    COUNT(*)::TEXT as value
FROM geometry_columns
WHERE f_table_schema = 'public'

UNION ALL

SELECT
    'Total Spatial Indexes',
    COUNT(*)::TEXT
FROM pg_indexes
WHERE indexname LIKE 'idx_%_geom'
AND schemaname = 'public'

UNION ALL

SELECT
    'Total Features',
    SUM(feature_count)::TEXT
FROM metadata.dataset_registry
WHERE is_active = TRUE;
