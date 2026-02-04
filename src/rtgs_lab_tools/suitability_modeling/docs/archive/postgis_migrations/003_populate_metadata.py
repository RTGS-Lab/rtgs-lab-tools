"""
Populate metadata.column_definitions table with data dictionary information.

This script analyzes loaded datasets and populates the column_definitions table
to help the LLM (Claude) understand dataset schemas when designing suitability models.

Usage:
    python 003_populate_metadata.py --db-url postgresql://user:pass@host:port/rtgs_spatial_data

Requirements:
    - sqlalchemy
    - psycopg2
"""

import argparse
import logging
import sys
from typing import Dict, List, Optional

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetadataPopulator:
    """Populate column definitions for datasets."""

    def __init__(self, db_url: str):
        """
        Initialize metadata populator.

        Args:
            db_url: SQLAlchemy database URL
        """
        self.db_url = db_url
        self.engine = None

    def connect_db(self):
        """Establish database connection."""
        try:
            self.engine = create_engine(self.db_url)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def get_datasets(self) -> List[Dict]:
        """
        Get list of all registered datasets.

        Returns:
            List of dataset dictionaries
        """
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT dataset_id, dataset_name, table_name
                FROM metadata.dataset_registry
                WHERE is_active = TRUE
                ORDER BY dataset_name
            """))
            return [dict(row._mapping) for row in result]

    def get_table_columns(self, table_name: str) -> List[Dict]:
        """
        Get column information for a table.

        Args:
            table_name: Full table name (schema.table)

        Returns:
            List of column dictionaries with name, type, nullable
        """
        schema, table = table_name.split('.')

        inspector = inspect(self.engine)
        columns = inspector.get_columns(table, schema=schema)

        # Filter out system columns
        return [
            {
                'name': col['name'],
                'type': str(col['type']),
                'nullable': col['nullable']
            }
            for col in columns
            if col['name'] not in ['id', 'geom', 'created_at']  # Skip standard columns
        ]

    def get_sample_values(self, table_name: str, column_name: str, limit: int = 5) -> List[str]:
        """
        Get sample values from a column.

        Args:
            table_name: Full table name
            column_name: Column name
            limit: Number of sample values to retrieve

        Returns:
            List of sample values as strings
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT DISTINCT "{column_name}"
                    FROM {table_name}
                    WHERE "{column_name}" IS NOT NULL
                    LIMIT :limit
                """), {'limit': limit})

                return [str(row[0]) for row in result]
        except Exception as e:
            logger.warning(f"Failed to get sample values for {table_name}.{column_name}: {e}")
            return []

    def is_categorical(self, table_name: str, column_name: str, threshold: int = 100) -> bool:
        """
        Determine if a column is categorical based on distinct value count.

        Args:
            table_name: Full table name
            column_name: Column name
            threshold: Maximum distinct values to consider categorical

        Returns:
            True if column appears to be categorical
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT COUNT(DISTINCT "{column_name}") as distinct_count
                    FROM {table_name}
                    WHERE "{column_name}" IS NOT NULL
                """))
                distinct_count = result.fetchone()[0]
                return distinct_count <= threshold
        except Exception as e:
            logger.warning(f"Failed to check if categorical: {table_name}.{column_name}: {e}")
            return False

    def populate_column_definitions(self, dataset_id: int, table_name: str, dataset_name: str):
        """
        Populate column definitions for a dataset.

        Args:
            dataset_id: Dataset ID from registry
            table_name: Full table name
            dataset_name: Dataset name
        """
        logger.info(f"Processing columns for {dataset_name}...")

        columns = self.get_table_columns(table_name)

        for col in columns:
            col_name = col['name']
            col_type = col['type']
            nullable = col['nullable']

            # Get sample values
            sample_values = self.get_sample_values(table_name, col_name)

            # Check if categorical
            is_cat = self.is_categorical(table_name, col_name)

            # Auto-generate description based on column name
            description = self.generate_description(col_name, col_type)

            # Detect units
            units = self.detect_units(col_name)

            try:
                with self.engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO metadata.column_definitions (
                            dataset_id, column_name, data_type, description,
                            example_values, is_categorical, units, is_nullable
                        ) VALUES (
                            :dataset_id, :column_name, :data_type, :description,
                            :example_values, :is_categorical, :units, :is_nullable
                        )
                        ON CONFLICT (dataset_id, column_name) DO UPDATE
                        SET data_type = EXCLUDED.data_type,
                            example_values = EXCLUDED.example_values,
                            is_categorical = EXCLUDED.is_categorical,
                            is_nullable = EXCLUDED.is_nullable
                    """), {
                        'dataset_id': dataset_id,
                        'column_name': col_name,
                        'data_type': col_type,
                        'description': description,
                        'example_values': sample_values,
                        'is_categorical': is_cat,
                        'units': units,
                        'is_nullable': nullable
                    })
                    conn.commit()

                logger.info(f"  ✓ {col_name} ({col_type}) - Categorical: {is_cat}")

            except Exception as e:
                logger.error(f"  ✗ Failed to insert column definition for {col_name}: {e}")

    def generate_description(self, column_name: str, column_type: str) -> str:
        """
        Auto-generate column description based on name and type.

        Args:
            column_name: Column name
            column_type: Column data type

        Returns:
            Generated description
        """
        # Common patterns
        name_lower = column_name.lower()

        if 'name' in name_lower:
            return f"Name or identifier"
        elif 'code' in name_lower:
            return f"Code or classification identifier"
        elif 'type' in name_lower or 'class' in name_lower:
            return f"Classification or type category"
        elif 'area' in name_lower or 'acres' in name_lower:
            return f"Area measurement"
        elif 'length' in name_lower:
            return f"Length measurement"
        elif 'date' in name_lower:
            return f"Date or timestamp"
        elif 'count' in name_lower or 'num' in name_lower:
            return f"Count or numeric value"
        elif 'description' in name_lower or 'desc' in name_lower:
            return f"Descriptive text"
        else:
            return f"Attribute: {column_name}"

    def detect_units(self, column_name: str) -> Optional[str]:
        """
        Detect units from column name.

        Args:
            column_name: Column name

        Returns:
            Units string or None
        """
        name_lower = column_name.lower()

        if 'acres' in name_lower:
            return 'acres'
        elif 'sqft' in name_lower or 'sq_ft' in name_lower:
            return 'square feet'
        elif 'meters' in name_lower or '_m' in name_lower:
            return 'meters'
        elif 'feet' in name_lower or '_ft' in name_lower:
            return 'feet'
        elif 'miles' in name_lower or '_mi' in name_lower:
            return 'miles'
        elif 'percent' in name_lower or 'pct' in name_lower:
            return 'percent'
        elif 'degrees' in name_lower or '_deg' in name_lower:
            return 'degrees'
        else:
            return None

    def process_all_datasets(self):
        """Process all registered datasets."""
        datasets = self.get_datasets()
        logger.info(f"Found {len(datasets)} datasets to process\n")

        for i, dataset in enumerate(datasets, 1):
            logger.info(f"\n[{i}/{len(datasets)}] {dataset['dataset_name']}")
            logger.info("-" * 50)

            try:
                self.populate_column_definitions(
                    dataset['dataset_id'],
                    dataset['table_name'],
                    dataset['dataset_name']
                )
            except Exception as e:
                logger.error(f"Failed to process {dataset['dataset_name']}: {e}")

        logger.info("\n" + "="*70)
        logger.info("Metadata population complete!")
        logger.info("="*70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Populate column definitions for spatial datasets'
    )

    parser.add_argument(
        '--db-url',
        required=True,
        help='PostgreSQL database URL (postgresql://user:pass@host:port/database)'
    )

    args = parser.parse_args()

    try:
        populator = MetadataPopulator(args.db_url)
        populator.connect_db()
        populator.process_all_datasets()

    except Exception as e:
        logger.error(f"Failed to populate metadata: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
