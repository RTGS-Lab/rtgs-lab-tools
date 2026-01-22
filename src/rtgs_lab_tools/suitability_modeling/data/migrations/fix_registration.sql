-- Manual registration of all migrated datasets
-- This fixes the registration that failed during initial migration

DO $$
DECLARE
    v_table_name TEXT;
    v_dataset_name TEXT;
    v_display_name TEXT;
    v_geom_type TEXT;
    v_feature_count BIGINT;
    v_extent GEOMETRY;
BEGIN
    -- Get all spatial tables in public schema
    FOR v_table_name IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename LIKE 'mn_%'
        ORDER BY tablename
    LOOP
        -- Derive names
        v_dataset_name := v_table_name;
        v_display_name := UPPER(REPLACE(REPLACE(v_table_name, 'mn_', ''), '_', ' '));

        -- Get geometry type
        EXECUTE format('SELECT ST_GeometryType(geom) FROM public.%I WHERE geom IS NOT NULL LIMIT 1', v_table_name)
        INTO v_geom_type;

        -- Clean up geometry type (remove "ST_" prefix)
        v_geom_type := REPLACE(v_geom_type, 'ST_', '');

        -- Get full feature count
        EXECUTE format('SELECT COUNT(*) FROM public.%I', v_table_name)
        INTO v_feature_count;

        -- Get extent
        EXECUTE format('SELECT ST_SetSRID(ST_Extent(geom)::geometry, 26915) FROM public.%I', v_table_name)
        INTO v_extent;

        -- Insert into registry (with ON CONFLICT to handle duplicates)
        INSERT INTO metadata.dataset_registry (
            dataset_name,
            table_name,
            display_name,
            description,
            geometry_type,
            srid,
            extent_geom,
            feature_count,
            data_source,
            is_public,
            tags
        ) VALUES (
            v_dataset_name,
            'public.' || v_table_name,
            v_display_name,
            'Imported from Hennepin County ESRI File Geodatabase',
            v_geom_type,
            26915,
            v_extent,
            v_feature_count,
            'Hennepin County FGDB',
            FALSE,  -- Private data
            ARRAY['hennepin_county', 'minnesota', 'conservation', 'easement_analysis']
        )
        ON CONFLICT (dataset_name) DO UPDATE
        SET
            feature_count = EXCLUDED.feature_count,
            extent_geom = EXCLUDED.extent_geom,
            updated_at = NOW();

        RAISE NOTICE 'Registered: % (% features, %)', v_dataset_name, v_feature_count, v_geom_type;

        -- Insert source record
        INSERT INTO metadata.dataset_sources (
            dataset_id,
            source_type,
            source_path,
            import_method,
            imported_by,
            original_crs,
            transformed_crs
        )
        SELECT
            dataset_id,
            'esri_fgdb',
            'HC_EasementAnalysis_Model_Inputs_2020.gdb/' || v_display_name,
            'migration_script',
            'manual_registration',
            'EPSG:26915',
            'EPSG:26915'
        FROM metadata.dataset_registry
        WHERE dataset_name = v_dataset_name
        ON CONFLICT DO NOTHING;

    END LOOP;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Dataset registration complete!';
    RAISE NOTICE '========================================';
END;
$$;

-- Show results
SELECT
    dataset_name,
    display_name,
    geometry_type,
    feature_count
FROM metadata.dataset_registry
ORDER BY dataset_name;
