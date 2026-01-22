"""
Validate migrated spatial data in PostGIS.

This script performs comprehensive validation of migrated datasets:
- Verifies all datasets registered in metadata
- Checks geometry validity
- Verifies CRS (should be EPSG:26915)
- Checks for null geometries
- Validates spatial indexes exist
- Compares feature counts

Usage:
    python 005_validate_data.py --db-url postgresql://user:pass@host:port/rtgs_spatial_data

Requirements:
    - sqlalchemy
    - psycopg2
    - geopandas
"""

import argparse
import logging
import sys
from typing import Dict, List

from sqlalchemy import create_engine, text
import geopandas as gpd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataValidator:
    """Validate migrated spatial datasets."""

    def __init__(self, db_url: str):
        """
        Initialize validator.

        Args:
            db_url: SQLAlchemy database URL
        """
        self.db_url = db_url
        self.engine = None
        self.issues = []
        self.warnings = []

    def connect_db(self):
        """Establish database connection."""
        try:
            self.engine = create_engine(self.db_url)
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT PostGIS_Version()"))
                version = result.fetchone()[0]
                logger.info(f"Connected to PostGIS: {version}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def get_datasets(self) -> List[Dict]:
        """Get all active datasets from registry."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    dataset_id,
                    dataset_name,
                    table_name,
                    display_name,
                    geometry_type,
                    srid,
                    feature_count
                FROM metadata.dataset_registry
                WHERE is_active = TRUE
                ORDER BY dataset_name
            """))
            return [dict(row._mapping) for row in result]

    def validate_table_exists(self, table_name: str) -> bool:
        """Check if table exists in database."""
        schema, table = table_name.split('.')
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = :schema
                    AND table_name = :table
                )
            """), {'schema': schema, 'table': table})
            return result.fetchone()[0]

    def validate_geometry_column(self, table_name: str) -> bool:
        """Check if geometry column exists."""
        schema, table = table_name.split('.')
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_schema = :schema
                    AND table_name = :table
                    AND column_name = 'geom'
                )
            """), {'schema': schema, 'table': table})
            return result.fetchone()[0]

    def validate_spatial_index(self, table_name: str) -> bool:
        """Check if spatial index exists on geometry column."""
        schema, table = table_name.split('.')
        index_name = f"idx_{table}_geom"

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes
                    WHERE schemaname = :schema
                    AND tablename = :table
                    AND indexname = :index_name
                )
            """), {'schema': schema, 'table': table, 'index_name': index_name})
            return result.fetchone()[0]

    def validate_crs(self, table_name: str, expected_srid: int = 26915) -> tuple:
        """
        Validate that geometry column has correct CRS.

        Returns:
            (is_valid, actual_srid)
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT DISTINCT ST_SRID(geom) as srid
                FROM {table_name}
                WHERE geom IS NOT NULL
                LIMIT 1
            """))
            row = result.fetchone()
            if row:
                actual_srid = row[0]
                return actual_srid == expected_srid, actual_srid
            else:
                return False, None

    def count_invalid_geometries(self, table_name: str) -> int:
        """Count invalid geometries in dataset."""
        with self.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE geom IS NOT NULL
                AND NOT ST_IsValid(geom)
            """))
            return result.fetchone()[0]

    def count_null_geometries(self, table_name: str) -> int:
        """Count null geometries in dataset."""
        with self.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE geom IS NULL
            """))
            return result.fetchone()[0]

    def get_actual_feature_count(self, table_name: str) -> int:
        """Get actual row count from table."""
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.fetchone()[0]

    def validate_dataset(self, dataset: Dict) -> bool:
        """
        Validate a single dataset.

        Args:
            dataset: Dataset dictionary from registry

        Returns:
            True if all validations pass
        """
        dataset_name = dataset['dataset_name']
        table_name = dataset['table_name']
        logger.info(f"\nValidating: {dataset_name}")
        logger.info("-" * 60)

        all_valid = True

        # 1. Check table exists
        if not self.validate_table_exists(table_name):
            self.issues.append(f"{dataset_name}: Table {table_name} does not exist")
            logger.error(f"  ✗ Table does not exist")
            return False

        logger.info(f"  ✓ Table exists")

        # 2. Check geometry column exists
        if not self.validate_geometry_column(table_name):
            self.issues.append(f"{dataset_name}: Geometry column 'geom' not found")
            logger.error(f"  ✗ Geometry column missing")
            return False

        logger.info(f"  ✓ Geometry column exists")

        # 3. Check spatial index
        if not self.validate_spatial_index(table_name):
            self.warnings.append(f"{dataset_name}: Spatial index missing")
            logger.warning(f"  ⚠ Spatial index missing (can be created)")
            all_valid = False
        else:
            logger.info(f"  ✓ Spatial index exists")

        # 4. Validate CRS
        crs_valid, actual_srid = self.validate_crs(table_name, dataset['srid'])
        if not crs_valid:
            self.issues.append(
                f"{dataset_name}: CRS mismatch - expected {dataset['srid']}, got {actual_srid}"
            )
            logger.error(f"  ✗ CRS mismatch: expected {dataset['srid']}, got {actual_srid}")
            all_valid = False
        else:
            logger.info(f"  ✓ CRS correct (EPSG:{dataset['srid']})")

        # 5. Check for invalid geometries
        invalid_count = self.count_invalid_geometries(table_name)
        if invalid_count > 0:
            self.warnings.append(f"{dataset_name}: {invalid_count} invalid geometries")
            logger.warning(f"  ⚠ {invalid_count} invalid geometries (may need repair)")
        else:
            logger.info(f"  ✓ All geometries valid")

        # 6. Check for null geometries
        null_count = self.count_null_geometries(table_name)
        if null_count > 0:
            self.warnings.append(f"{dataset_name}: {null_count} null geometries")
            logger.warning(f"  ⚠ {null_count} null geometries")
        else:
            logger.info(f"  ✓ No null geometries")

        # 7. Verify feature count
        actual_count = self.get_actual_feature_count(table_name)
        expected_count = dataset['feature_count']

        if expected_count is None:
            logger.info(f"  - Feature count: {actual_count} (not verified, no expected count)")
        elif actual_count != expected_count:
            self.warnings.append(
                f"{dataset_name}: Feature count mismatch - expected {expected_count}, got {actual_count}"
            )
            logger.warning(f"  ⚠ Feature count: {actual_count} (expected {expected_count})")
        else:
            logger.info(f"  ✓ Feature count: {actual_count}")

        return all_valid

    def validate_all(self):
        """Validate all registered datasets."""
        datasets = self.get_datasets()

        logger.info("\n" + "="*70)
        logger.info(f"VALIDATING {len(datasets)} DATASETS")
        logger.info("="*70)

        passed = 0
        failed = 0

        for dataset in datasets:
            try:
                if self.validate_dataset(dataset):
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Validation error for {dataset['dataset_name']}: {e}")
                self.issues.append(f"{dataset['dataset_name']}: Unexpected error - {e}")
                failed += 1

        # Print summary
        self.print_summary(passed, failed, len(datasets))

    def print_summary(self, passed: int, failed: int, total: int):
        """Print validation summary."""
        logger.info("\n" + "="*70)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*70)
        logger.info(f"Total datasets:  {total}")
        logger.info(f"Passed:          {passed}")
        logger.info(f"Failed:          {failed}")
        logger.info(f"Critical issues: {len(self.issues)}")
        logger.info(f"Warnings:        {len(self.warnings)}")
        logger.info("="*70)

        if self.issues:
            logger.error("\nCRITICAL ISSUES:")
            for issue in self.issues:
                logger.error(f"  - {issue}")

        if self.warnings:
            logger.warning("\nWARNINGS:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")

        if passed == total and not self.issues:
            logger.info("\n✓ All datasets passed validation!")
        else:
            logger.warning("\n⚠ Some datasets have issues. Review logs above.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate migrated spatial datasets in PostGIS'
    )

    parser.add_argument(
        '--db-url',
        required=True,
        help='PostgreSQL database URL (postgresql://user:pass@host:port/database)'
    )

    args = parser.parse_args()

    try:
        validator = DataValidator(args.db_url)
        validator.connect_db()
        validator.validate_all()

        # Exit with error code if there are critical issues
        if validator.issues:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
