"""PostGIS data source manager for suitability modeling.

This module provides access to spatial datasets stored in the rtgs_suitability_data
PostgreSQL/PostGIS database.
"""

import logging
from typing import Dict, List, Optional
import geopandas as gpd
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


class PostGISDataManager:
    """Manage access to spatial datasets in PostGIS database."""

    def __init__(self, db_url: Optional[str] = None):
        """Initialize PostGIS data manager.

        Args:
            db_url: PostgreSQL connection URL. If None, tries to load from environment.
                   Format: postgresql://user:password@host:port/database
        """
        self.db_url = db_url or self._get_db_url_from_env()
        self.engine = None
        self._datasets_cache = None

    def _get_db_url_from_env(self) -> Optional[str]:
        """Get database URL from environment variables or config.

        Returns:
            Database URL string or None if not configured
        """
        import os

        # Try environment variable first
        db_url = os.getenv('SUITABILITY_DB_URL')
        if db_url:
            return db_url

        # Try building from individual components
        host = os.getenv('SUITABILITY_DB_HOST', 'localhost')
        port = os.getenv('SUITABILITY_DB_PORT', '5432')
        database = os.getenv('SUITABILITY_DB_NAME', 'rtgs_suitability_data')
        user = os.getenv('SUITABILITY_DB_USER', 'postgres')
        password = os.getenv('SUITABILITY_DB_PASSWORD')

        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"

        # Try without password (for trusted authentication)
        try:
            test_url = f"postgresql://{user}@{host}:{port}/{database}"
            test_engine = create_engine(test_url)
            with test_engine.connect():
                return test_url
        except Exception:
            pass

        return None

    def connect(self):
        """Establish database connection."""
        if not self.db_url:
            raise ValueError(
                "Database URL not configured. Set SUITABILITY_DB_URL environment variable "
                "or pass db_url to constructor."
            )

        try:
            self.engine = create_engine(self.db_url)
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT PostGIS_Version()"))
                version = result.fetchone()[0]
                logger.info(f"Connected to PostGIS: {version}")
        except Exception as e:
            logger.error(f"Failed to connect to PostGIS database: {e}")
            raise

    def is_available(self) -> bool:
        """Check if PostGIS database is available.

        Returns:
            True if database connection can be established
        """
        if not self.db_url:
            return False

        try:
            if not self.engine:
                self.connect()
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def list_available_datasets(self, use_cache: bool = True) -> Dict[str, Dict]:
        """Get list of all available datasets from PostGIS database.

        Args:
            use_cache: Use cached dataset list if available

        Returns:
            Dict of dataset_name: {description, geometry_type, feature_count, etc.}
        """
        if use_cache and self._datasets_cache:
            return self._datasets_cache

        if not self.engine:
            self.connect()

        datasets = {}

        with self.engine.connect() as conn:
            # Query metadata registry
            result = conn.execute(text("""
                SELECT
                    dr.dataset_name,
                    dr.display_name,
                    dr.description,
                    dr.geometry_type,
                    dr.feature_count,
                    dr.table_name,
                    dr.data_source,
                    dr.tags,
                    array_agg(DISTINCT cd.column_name) FILTER (WHERE cd.column_name IS NOT NULL) as columns
                FROM metadata.dataset_registry dr
                LEFT JOIN metadata.column_definitions cd ON dr.dataset_id = cd.dataset_id
                WHERE dr.is_active = TRUE
                GROUP BY dr.dataset_id, dr.dataset_name, dr.display_name,
                         dr.description, dr.geometry_type, dr.feature_count,
                         dr.table_name, dr.data_source, dr.tags
                ORDER BY dr.dataset_name
            """))

            for row in result:
                datasets[row.dataset_name] = {
                    'display_name': row.display_name,
                    'description': row.description or f'{row.display_name} ({row.data_source})',
                    'geometry_type': row.geometry_type,
                    'feature_count': row.feature_count,
                    'table_name': row.table_name,
                    'data_source': row.data_source,
                    'tags': row.tags or [],
                    'columns': row.columns or [],
                    'source': 'postgis'  # Mark source for execution engine
                }

        self._datasets_cache = datasets
        return datasets

    def get_dataset_columns(self, dataset_name: str) -> List[Dict]:
        """Get column definitions for a dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            List of column dictionaries with name, type, description, etc.
        """
        if not self.engine:
            self.connect()

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    cd.column_name,
                    cd.data_type,
                    cd.description,
                    cd.is_categorical,
                    cd.category_mapping,
                    cd.units,
                    cd.example_values
                FROM metadata.column_definitions cd
                JOIN metadata.dataset_registry dr ON cd.dataset_id = dr.dataset_id
                WHERE dr.dataset_name = :dataset_name
                ORDER BY cd.column_name
            """), {'dataset_name': dataset_name})

            columns = []
            for row in result:
                columns.append({
                    'name': row.column_name,
                    'type': row.data_type,
                    'description': row.description,
                    'is_categorical': row.is_categorical,
                    'category_mapping': row.category_mapping,
                    'units': row.units,
                    'example_values': row.example_values
                })

            return columns

    def load_dataset(
        self,
        dataset_name: str,
        columns: Optional[List[str]] = None,
        where: Optional[str] = None,
        bbox: Optional[tuple] = None
    ) -> gpd.GeoDataFrame:
        """Load a dataset from PostGIS.

        Args:
            dataset_name: Name of the dataset to load
            columns: Optional list of columns to load (default: all)
            where: Optional SQL WHERE clause for filtering
            bbox: Optional bounding box (minx, miny, maxx, maxy) in EPSG:26915

        Returns:
            GeoDataFrame with the dataset

        Example:
            >>> manager = PostGISDataManager(db_url)
            >>> gdf = manager.load_dataset('mn_wildlife_areas')
            >>> gdf = manager.load_dataset(
            ...     'mn_wildlife_areas',
            ...     columns=['name', 'area_acres'],
            ...     bbox=(450000, 5000000, 460000, 5010000)
            ... )
        """
        if not self.engine:
            self.connect()

        # Get table name from registry
        datasets = self.list_available_datasets()
        if dataset_name not in datasets:
            raise ValueError(f"Dataset '{dataset_name}' not found in PostGIS database")

        table_name = datasets[dataset_name]['table_name']

        # Build SQL query
        select_cols = ', '.join(columns) if columns else '*'
        query = f"SELECT {select_cols} FROM {table_name}"

        # Add filters
        conditions = []
        if bbox:
            minx, miny, maxx, maxy = bbox
            conditions.append(
                f"geom && ST_MakeEnvelope({minx}, {miny}, {maxx}, {maxy}, 26915)"
            )
        if where:
            conditions.append(where)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        logger.info(f"Loading dataset '{dataset_name}' from PostGIS")

        # Load with geopandas
        gdf = gpd.read_postgis(
            query,
            self.engine,
            geom_col='geom',
            crs='EPSG:26915'
        )

        logger.info(f"  Loaded {len(gdf)} features from '{dataset_name}'")

        return gdf

    def get_dataset_info(self, dataset_name: str) -> Dict:
        """Get detailed information about a dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Dictionary with dataset metadata including columns
        """
        datasets = self.list_available_datasets()
        if dataset_name not in datasets:
            raise ValueError(f"Dataset '{dataset_name}' not found")

        info = datasets[dataset_name].copy()
        info['columns_detail'] = self.get_dataset_columns(dataset_name)

        return info
