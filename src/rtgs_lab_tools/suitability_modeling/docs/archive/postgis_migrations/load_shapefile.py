"""
Load shapefiles into PostGIS database.

This script loads boundary and analysis unit shapefiles into the
rtgs_suitability_data database.

Usage:
    python load_shapefile.py --shapefile /path/to/file.shp --table-name my_table --db-url postgresql://...
"""

import argparse
import logging
import sys
from pathlib import Path

import geopandas as gpd
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Target CRS for all datasets (Minnesota UTM Zone 15N)
TARGET_CRS = 'EPSG:26915'


def load_shapefile(
    shapefile_path: str,
    table_name: str,
    db_url: str,
    dataset_type: str = 'boundary'
):
    """Load a shapefile into PostGIS.

    Args:
        shapefile_path: Path to shapefile
        table_name: Name for the database table
        db_url: PostgreSQL connection URL
        dataset_type: Type of dataset ('boundary', 'analysis_unit', or 'criteria')
    """
    shapefile_path = Path(shapefile_path)

    if not shapefile_path.exists():
        raise FileNotFoundError(f"Shapefile not found: {shapefile_path}")

    logger.info(f"Loading shapefile: {shapefile_path}")
    logger.info(f"Target table: {table_name}")

    # Read shapefile
    logger.info("Reading shapefile...")
    gdf = gpd.read_file(shapefile_path)
    logger.info(f"  Read {len(gdf)} features")
    logger.info(f"  Original CRS: {gdf.crs}")
    logger.info(f"  Columns: {', '.join(gdf.columns)}")

    # Transform to target CRS if needed
    if gdf.crs is None:
        logger.warning(f"No CRS defined, assuming {TARGET_CRS}")
        gdf.set_crs(TARGET_CRS, inplace=True)
    elif gdf.crs.to_string() != TARGET_CRS:
        logger.info(f"Transforming from {gdf.crs.to_string()} to {TARGET_CRS}")
        gdf = gdf.to_crs(TARGET_CRS)

    # Rename geometry column to 'geom' (PostGIS convention)
    if gdf.geometry.name != 'geom':
        gdf = gdf.rename_geometry('geom')

    # Add id column if not present
    if 'id' in gdf.columns:
        gdf = gdf.rename(columns={'id': 'original_id'})
        logger.info("  Renamed existing 'id' column to 'original_id'")

    gdf.insert(0, 'id', range(1, len(gdf) + 1))

    # Add timestamp
    gdf['created_at'] = gpd.pd.Timestamp.now()

    # Connect to database
    logger.info("Connecting to database...")
    engine = create_engine(db_url)

    # Load to PostGIS
    logger.info(f"Loading {len(gdf)} features to PostGIS table '{table_name}'...")
    gdf.to_postgis(
        table_name,
        engine,
        schema='public',
        if_exists='replace',
        index=False
    )

    # Create spatial index
    logger.info("Creating spatial index...")
    with engine.connect() as conn:
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_geom
            ON public.{table_name} USING GIST(geom)
        """))
        conn.commit()

    # Determine display name and tags based on dataset type
    if 'county' in table_name.lower() and 'boundary' in table_name.lower():
        display_name = "Hennepin County Boundary"
        tags = ['boundary', 'hennepin_county', 'study_area']
        description = "Hennepin County administrative boundary"
    elif 'cities' in table_name.lower() or 'ctu' in table_name.lower():
        display_name = "Hennepin County Cities and Towns"
        tags = ['analysis_unit', 'boundary', 'hennepin_county', 'municipalities']
        description = "Cities and towns (CTUs) within Hennepin County"
    elif 'parcel' in table_name.lower():
        display_name = "Hennepin County Parcels"
        tags = ['analysis_unit', 'hennepin_county', 'parcels']
        description = "Land parcels within Hennepin County"
    else:
        display_name = table_name.replace('_', ' ').title()
        tags = [dataset_type, 'hennepin_county']
        description = f"Loaded from {shapefile_path.name}"

    # Get geometry type
    geom_type = str(gdf.geom_type.mode()[0]) if not gdf.empty else 'Unknown'

    # Register in metadata
    logger.info("Registering in metadata catalog...")
    with engine.connect() as conn:
        # Insert into registry (let PostgreSQL calculate extent directly)
        conn.execute(text(f"""
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
            )
            SELECT
                :dataset_name,
                :table_name,
                :display_name,
                :description,
                :geometry_type,
                26915,
                ST_SetSRID(ST_Extent(geom)::geometry, 26915),
                :feature_count,
                'Shapefile',
                FALSE,
                :tags
            FROM public.{table_name}
            ON CONFLICT (dataset_name) DO UPDATE
            SET
                feature_count = EXCLUDED.feature_count,
                extent_geom = EXCLUDED.extent_geom,
                updated_at = NOW()
        """), {
            'dataset_name': table_name,
            'table_name': f'public.{table_name}',
            'display_name': display_name,
            'description': description,
            'geometry_type': geom_type,
            'feature_count': len(gdf),
            'tags': tags
        })
        conn.commit()

    logger.info(f"✓ Successfully loaded {table_name}")
    logger.info(f"  Features: {len(gdf)}")
    logger.info(f"  Geometry type: {geom_type}")
    logger.info(f"  Dataset type: {dataset_type}")
    logger.info(f"  Tags: {', '.join(tags)}")


def main():
    parser = argparse.ArgumentParser(
        description='Load shapefile into PostGIS database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load county boundary
  python load_shapefile.py --shapefile county.shp --table-name hennepin_county_boundary --db-url postgresql://user:pass@localhost/rtgs_suitability_data

  # Load cities with custom type
  python load_shapefile.py --shapefile cities.shp --table-name hennepin_county_cities --type analysis_unit --db-url postgresql://user:pass@localhost/rtgs_suitability_data
        """
    )

    parser.add_argument(
        '--shapefile',
        required=True,
        help='Path to shapefile (.shp)'
    )

    parser.add_argument(
        '--table-name',
        required=True,
        help='Name for the database table'
    )

    parser.add_argument(
        '--db-url',
        required=True,
        help='PostgreSQL database URL (postgresql://user:pass@host:port/database)'
    )

    parser.add_argument(
        '--type',
        default='boundary',
        choices=['boundary', 'analysis_unit', 'criteria'],
        help='Type of dataset (default: boundary)'
    )

    args = parser.parse_args()

    try:
        load_shapefile(
            shapefile_path=args.shapefile,
            table_name=args.table_name,
            db_url=args.db_url,
            dataset_type=args.type
        )

    except Exception as e:
        logger.error(f"Failed to load shapefile: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
