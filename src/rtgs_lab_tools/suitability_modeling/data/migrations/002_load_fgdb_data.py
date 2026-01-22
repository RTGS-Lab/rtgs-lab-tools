"""
Load spatial datasets from ESRI File Geodatabase into PostGIS.

This script:
1. Reads feature classes from an ESRI File Geodatabase (.gdb)
2. Transforms geometries to EPSG:26915 (NAD83 / UTM Zone 15N)
3. Loads data into PostGIS tables in the 'public' schema
4. Registers datasets in metadata.dataset_registry
5. Creates spatial indexes on geometry columns

Usage:
    python 002_load_fgdb_data.py --fgdb /path/to/data.gdb --db-url postgresql://user:pass@host:port/rtgs_spatial_data

Requirements:
    - geopandas
    - sqlalchemy
    - psycopg2
    - fiona (for FGDB reading)
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import hashlib
import json

import geopandas as gpd
import fiona
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import warnings

# Suppress specific warnings
warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy connectable')
warnings.filterwarnings('ignore', category=UserWarning, module='geopandas')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fgdb_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Target CRS for all datasets (Minnesota UTM Zone 15N)
TARGET_CRS = 'EPSG:26915'

# Naming conventions
SCHEMA = 'public'
PREFIX = 'mn_'  # State prefix for Minnesota datasets


class FGDBLoader:
    """Load datasets from ESRI File Geodatabase into PostGIS."""

    def __init__(self, fgdb_path: str, db_url: str, dry_run: bool = False):
        """
        Initialize FGDB loader.

        Args:
            fgdb_path: Path to ESRI File Geodatabase (.gdb directory)
            db_url: SQLAlchemy database URL (postgresql://user:pass@host:port/database)
            dry_run: If True, only print what would be done without making changes
        """
        self.fgdb_path = Path(fgdb_path)
        self.db_url = db_url
        self.dry_run = dry_run
        self.engine = None
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        if not self.fgdb_path.exists():
            raise FileNotFoundError(f"FGDB not found: {self.fgdb_path}")

    def connect_db(self):
        """Establish database connection."""
        try:
            self.engine = create_engine(self.db_url)
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT PostGIS_Version()"))
                version = result.fetchone()[0]
                logger.info(f"Connected to PostGIS: {version}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def list_feature_classes(self) -> List[str]:
        """
        List all feature classes in the FGDB.

        Returns:
            List of feature class names
        """
        try:
            layers = fiona.listlayers(str(self.fgdb_path))
            logger.info(f"Found {len(layers)} feature classes in FGDB")
            return layers
        except Exception as e:
            logger.error(f"Failed to list FGDB layers: {e}")
            raise

    def normalize_table_name(self, fc_name: str) -> str:
        """
        Convert feature class name to PostgreSQL table name.

        Args:
            fc_name: Original feature class name

        Returns:
            Normalized table name (lowercase, underscores, state prefix)
        """
        # Remove special characters, convert to lowercase, replace spaces with underscores
        table_name = fc_name.lower().replace(' ', '_').replace('-', '_')

        # Remove any non-alphanumeric characters except underscores
        table_name = ''.join(c for c in table_name if c.isalnum() or c == '_')

        # Ensure it starts with state prefix
        if not table_name.startswith(PREFIX):
            table_name = PREFIX + table_name

        return table_name

    def get_fgdb_metadata(self, fc_name: str) -> Dict:
        """
        Extract metadata from feature class.

        Args:
            fc_name: Feature class name

        Returns:
            Dictionary with metadata
        """
        try:
            with fiona.open(str(self.fgdb_path), layer=fc_name) as src:
                return {
                    'feature_count': len(src),
                    'geometry_type': src.schema['geometry'],
                    'crs': src.crs.to_string() if src.crs else None,
                    'bounds': src.bounds,
                    'columns': list(src.schema['properties'].keys())
                }
        except Exception as e:
            logger.warning(f"Failed to extract metadata for {fc_name}: {e}")
            return {}

    def calculate_md5(self, fc_name: str) -> str:
        """
        Calculate MD5 hash of feature class (for change detection).

        Args:
            fc_name: Feature class name

        Returns:
            MD5 hash string
        """
        try:
            with fiona.open(str(self.fgdb_path), layer=fc_name) as src:
                # Hash the schema and first 100 features (reasonable proxy)
                content = json.dumps(src.schema, sort_keys=True)
                for i, feature in enumerate(src):
                    if i >= 100:
                        break
                    content += json.dumps(feature, sort_keys=True)

                return hashlib.md5(content.encode()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate MD5 for {fc_name}: {e}")
            return None

    def load_feature_class(self, fc_name: str) -> bool:
        """
        Load a single feature class into PostGIS.

        Args:
            fc_name: Feature class name in FGDB

        Returns:
            True if successful, False otherwise
        """
        table_name = self.normalize_table_name(fc_name)
        full_table_name = f"{SCHEMA}.{table_name}"

        logger.info(f"\n{'='*70}")
        logger.info(f"Processing: {fc_name} -> {full_table_name}")
        logger.info(f"{'='*70}")

        try:
            # Get metadata
            metadata = self.get_fgdb_metadata(fc_name)
            if not metadata:
                logger.error(f"Skipping {fc_name}: Could not extract metadata")
                self.stats['skipped'] += 1
                return False

            logger.info(f"Features: {metadata['feature_count']}")
            logger.info(f"Geometry: {metadata['geometry_type']}")
            logger.info(f"Original CRS: {metadata['crs']}")

            # Check if empty
            if metadata['feature_count'] == 0:
                logger.warning(f"Skipping {fc_name}: No features")
                self.stats['skipped'] += 1
                return False

            if self.dry_run:
                logger.info(f"[DRY RUN] Would load {metadata['feature_count']} features to {full_table_name}")
                return True

            # Read feature class
            logger.info("Reading feature class from FGDB...")
            gdf = gpd.read_file(str(self.fgdb_path), layer=fc_name)

            # Transform to target CRS
            if gdf.crs is None:
                logger.warning(f"No CRS defined, assuming {TARGET_CRS}")
                gdf.set_crs(TARGET_CRS, inplace=True)
            elif gdf.crs.to_string() != TARGET_CRS:
                logger.info(f"Transforming from {gdf.crs.to_string()} to {TARGET_CRS}")
                gdf = gdf.to_crs(TARGET_CRS)

            # Rename geometry column to 'geom' (PostGIS convention)
            if gdf.geometry.name != 'geom':
                gdf = gdf.rename_geometry('geom')

            # Handle 'id' column - rename existing one if present, then create new sequential id
            if 'id' in gdf.columns:
                # Rename existing id column to preserve original data
                gdf = gdf.rename(columns={'id': 'original_id'})
                logger.info("  Renamed existing 'id' column to 'original_id'")

            # Add sequential id column for primary key
            gdf.insert(0, 'id', range(1, len(gdf) + 1))

            # Add timestamp
            gdf['created_at'] = gpd.pd.Timestamp.now()

            # Load to PostGIS
            logger.info(f"Loading {len(gdf)} features to PostGIS...")
            gdf.to_postgis(
                table_name,
                self.engine,
                schema=SCHEMA,
                if_exists='replace',  # Replace existing table
                index=False  # Don't write index as we already have 'id' column
            )

            # Create spatial index
            logger.info("Creating spatial index...")
            with self.engine.connect() as conn:
                conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_geom
                    ON {full_table_name} USING GIST(geom)
                """))
                conn.commit()

            # Register in metadata.dataset_registry
            logger.info("Registering in dataset catalog...")
            self.register_dataset(
                dataset_name=table_name,
                table_name=full_table_name,
                display_name=fc_name,
                geometry_type=metadata['geometry_type'],
                original_crs=metadata['crs']
            )

            # Record source information
            logger.info("Recording source information...")
            self.record_source(
                dataset_name=table_name,
                fc_name=fc_name,
                original_crs=metadata['crs'],
                md5_hash=self.calculate_md5(fc_name)
            )

            logger.info(f"✓ Successfully loaded {fc_name}")
            self.stats['success'] += 1
            return True

        except Exception as e:
            logger.error(f"✗ Failed to load {fc_name}: {e}", exc_info=True)
            self.stats['failed'] += 1
            return False

    def register_dataset(
        self,
        dataset_name: str,
        table_name: str,
        display_name: str,
        geometry_type: str,
        original_crs: str
    ):
        """
        Register dataset in metadata.dataset_registry.

        Args:
            dataset_name: Internal dataset identifier
            table_name: Full table name (schema.table)
            display_name: Human-readable name
            geometry_type: Geometry type
            original_crs: Original coordinate reference system
        """
        if self.dry_run:
            return

        try:
            with self.engine.connect() as conn:
                # Use the register_dataset function from schema
                result = conn.execute(text("""
                    SELECT metadata.register_dataset(
                        :dataset_name,
                        :table_name,
                        :display_name,
                        :description,
                        :geometry_type,
                        :data_source,
                        :is_public,
                        :tags
                    )
                """), {
                    'dataset_name': dataset_name,
                    'table_name': table_name,
                    'display_name': display_name,
                    'description': f'Imported from ESRI File Geodatabase ({display_name})',
                    'geometry_type': geometry_type,
                    'data_source': 'ESRI File Geodatabase',
                    'is_public': True,  # Adjust based on your needs
                    'tags': ['minnesota', 'gis']
                })
                conn.commit()
                logger.info(f"Registered dataset: {dataset_name}")
        except Exception as e:
            logger.warning(f"Failed to register dataset {dataset_name}: {e}")

    def record_source(
        self,
        dataset_name: str,
        fc_name: str,
        original_crs: str,
        md5_hash: Optional[str]
    ):
        """
        Record source information in metadata.dataset_sources.

        Args:
            dataset_name: Internal dataset identifier
            fc_name: Original feature class name
            original_crs: Original CRS
            md5_hash: MD5 hash of source data
        """
        if self.dry_run:
            return

        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO metadata.dataset_sources (
                        dataset_id, source_type, source_path, import_method,
                        imported_by, md5_hash, original_crs, transformed_crs
                    )
                    SELECT
                        dataset_id, 'esri_fgdb', :source_path, 'migration_script',
                        :imported_by, :md5_hash, :original_crs, :transformed_crs
                    FROM metadata.dataset_registry
                    WHERE dataset_name = :dataset_name
                """), {
                    'dataset_name': dataset_name,
                    'source_path': f"{self.fgdb_path.name}/{fc_name}",
                    'imported_by': 'migration_script',
                    'md5_hash': md5_hash,
                    'original_crs': original_crs,
                    'transformed_crs': TARGET_CRS
                })
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to record source for {dataset_name}: {e}")

    def load_all(self, feature_classes: Optional[List[str]] = None):
        """
        Load all feature classes (or specified subset) from FGDB to PostGIS.

        Args:
            feature_classes: Optional list of feature class names to load.
                           If None, loads all feature classes.
        """
        # List feature classes
        all_fc = self.list_feature_classes()

        # Filter if specific feature classes requested
        if feature_classes:
            fc_to_load = [fc for fc in all_fc if fc in feature_classes]
            not_found = set(feature_classes) - set(all_fc)
            if not_found:
                logger.warning(f"Feature classes not found: {', '.join(not_found)}")
        else:
            fc_to_load = all_fc

        logger.info(f"\nLoading {len(fc_to_load)} feature classes:")
        for fc in fc_to_load:
            logger.info(f"  - {fc}")

        if self.dry_run:
            logger.info("\n[DRY RUN MODE] No changes will be made\n")

        # Load each feature class
        self.stats['total'] = len(fc_to_load)
        for i, fc_name in enumerate(fc_to_load, 1):
            logger.info(f"\nProgress: {i}/{len(fc_to_load)}")
            self.load_feature_class(fc_name)

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print migration summary statistics."""
        logger.info("\n" + "="*70)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*70)
        logger.info(f"Total feature classes: {self.stats['total']}")
        logger.info(f"Successfully loaded:   {self.stats['success']}")
        logger.info(f"Failed:               {self.stats['failed']}")
        logger.info(f"Skipped:              {self.stats['skipped']}")
        logger.info("="*70)

        if self.stats['failed'] > 0:
            logger.warning("\nSome feature classes failed to load. Check logs for details.")
        else:
            logger.info("\n✓ All feature classes loaded successfully!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Load spatial datasets from ESRI File Geodatabase into PostGIS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load all feature classes
  python 002_load_fgdb_data.py --fgdb /path/to/data.gdb --db-url postgresql://user:pass@localhost:5432/rtgs_spatial_data

  # Dry run (no changes)
  python 002_load_fgdb_data.py --fgdb /path/to/data.gdb --db-url postgresql://user:pass@localhost:5432/rtgs_spatial_data --dry-run

  # Load specific feature classes only
  python 002_load_fgdb_data.py --fgdb /path/to/data.gdb --db-url postgresql://user:pass@localhost:5432/rtgs_spatial_data --layers "Wildlife Areas" "Land Use"
        """
    )

    parser.add_argument(
        '--fgdb',
        required=True,
        help='Path to ESRI File Geodatabase (.gdb directory)'
    )

    parser.add_argument(
        '--db-url',
        required=True,
        help='PostgreSQL database URL (postgresql://user:pass@host:port/database)'
    )

    parser.add_argument(
        '--layers',
        nargs='+',
        help='Specific feature class names to load (default: all)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be done without making changes'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Initialize loader
    try:
        loader = FGDBLoader(args.fgdb, args.db_url, dry_run=args.dry_run)

        if not args.dry_run:
            loader.connect_db()

        # Load datasets
        loader.load_all(feature_classes=args.layers)

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
