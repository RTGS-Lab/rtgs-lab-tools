"""PostGIS integration for spatial data ETL pipeline."""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Reuse existing infrastructure
from ..core.config import Config
from ..core.database import DatabaseManager
from ..core.exceptions import DatabaseError
from ..core.postgres_logger import PostgresLogger

logger = logging.getLogger(__name__)

Base = declarative_base()


class SpatialDataset(Base):
    """SQLAlchemy model for spatial datasets catalog."""

    __tablename__ = "spatial_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    source_type = Column(String(50), nullable=False)
    source_url = Column(Text)
    download_url = Column(Text)
    spatial_type = Column(String(50))
    coordinate_system = Column(String(20))
    update_frequency = Column(String(50))
    model_critical = Column(Boolean, default=False)
    expected_features = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SpatialExtraction(Base):
    """SQLAlchemy model for spatial extraction logs."""

    __tablename__ = "spatial_extractions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_name = Column(String(100), nullable=False)
    extraction_start = Column(DateTime, nullable=False)
    extraction_end = Column(DateTime, nullable=False)
    duration_seconds = Column(Numeric(10, 3))
    success = Column(Boolean, nullable=False)
    records_extracted = Column(Integer, default=0)
    output_file = Column(Text)
    file_size_mb = Column(Numeric(10, 3))
    output_format = Column(String(20))
    crs = Column(String(20))
    geometry_type = Column(String(50))
    bounds_minx = Column(Numeric)
    bounds_miny = Column(Numeric)
    bounds_maxx = Column(Numeric)
    bounds_maxy = Column(Numeric)
    columns_extracted = Column(ARRAY(String))
    error_message = Column(Text)
    note = Column(Text)
    git_commit_hash = Column(String(40))
    created_at = Column(DateTime, default=datetime.utcnow)


class SpatialDataLogger:
    """Handle PostgreSQL logging for spatial data extractions."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize spatial data logger.

        Args:
            config: Optional configuration instance
        """
        self.config = config or Config()
        # Use GCP authentication if LOGGING_INSTANCE_CONNECTION_NAME is set
        use_gcp = bool(self.config.logging_instance_connection_name)
        self.db_manager = DatabaseManager(config=self.config, use_gcp=use_gcp)
        self._Session = None

        # Also initialize the general postgres logger for compatibility
        self.postgres_logger = PostgresLogger("spatial-data", config)

    @property
    def engine(self):
        """Get or create database engine."""
        return self.db_manager.engine

    @property
    def Session(self):
        """Get or create database session factory."""
        if self._Session is None:
            self._Session = sessionmaker(bind=self.engine)
        return self._Session

    def get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent.parent,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.debug(f"Failed to get git commit: {e}")
        return None

    def ensure_spatial_tables_exist(self):
        """Ensure spatial data tables exist with PostGIS enabled."""
        try:
            # Check if PostGIS extension exists
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'postgis')"
                    )
                )
                postgis_exists = result.scalar()

                if not postgis_exists:
                    logger.warning(
                        "PostGIS extension not found. Tables will be created without spatial features."
                    )

            # Create tables
            Base.metadata.create_all(self.engine)
            logger.info("Spatial data tables ensured to exist")

        except SQLAlchemyError as e:
            logger.error(f"Failed to create spatial data tables: {e}")
            raise DatabaseError(f"Failed to create spatial tables: {e}")

    def log_extraction(self, results: Dict[str, Any]) -> bool:
        """Log spatial data extraction to database.

        Args:
            results: Results dictionary from extract_spatial_data

        Returns:
            True if successful, False otherwise
        """
        try:
            self.ensure_spatial_tables_exist()

            # Parse extraction times
            start_time = datetime.fromisoformat(results["start_time"])
            end_time = datetime.fromisoformat(results["end_time"])

            # Parse bounds if available
            bounds = results.get("bounds", [])
            bounds_values = {}
            if bounds and len(bounds) >= 4:
                bounds_values = {
                    "bounds_minx": bounds[0],
                    "bounds_miny": bounds[1],
                    "bounds_maxx": bounds[2],
                    "bounds_maxy": bounds[3],
                }

            # Create extraction log entry
            extraction_log = SpatialExtraction(
                dataset_name=results["dataset_name"],
                extraction_start=start_time,
                extraction_end=end_time,
                duration_seconds=results["duration_seconds"],
                success=results["success"],
                records_extracted=results.get("records_extracted", 0),
                output_file=results.get("output_file"),
                file_size_mb=results.get("file_size_mb"),
                output_format=results.get("output_format", "geoparquet"),
                crs=results.get("crs"),
                geometry_type=results.get("geometry_type"),
                columns_extracted=results.get("columns", []),
                error_message=results.get("error"),
                note=results.get("note"),
                git_commit_hash=self.get_git_commit(),
                **bounds_values,
            )

            session = self.Session()
            try:
                session.add(extraction_log)
                session.commit()
                logger.info(f"Logged spatial extraction: {results['dataset_name']}")

                # Also log to general postgres logger for audit trail
                self.postgres_logger.log_execution(
                    operation=f"spatial-data extract {results['dataset_name']}",
                    parameters={
                        "dataset_name": results["dataset_name"],
                        "output_format": results.get("output_format", "geoparquet"),
                        "note": results.get("note"),
                    },
                    results=results,
                )

                return True

            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Failed to log spatial extraction: {e}")
                return False
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Failed to log spatial extraction: {e}")
            return False

    def get_dataset_info(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """Get dataset information from catalog.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Dataset information dictionary or None if not found
        """
        try:
            session = self.Session()
            try:
                dataset = (
                    session.query(SpatialDataset)
                    .filter_by(dataset_name=dataset_name)
                    .first()
                )

                if dataset:
                    return {
                        "id": dataset.id,
                        "dataset_name": dataset.dataset_name,
                        "description": dataset.description,
                        "source_type": dataset.source_type,
                        "source_url": dataset.source_url,
                        "spatial_type": dataset.spatial_type,
                        "coordinate_system": dataset.coordinate_system,
                        "expected_features": dataset.expected_features,
                        "created_at": (
                            dataset.created_at.isoformat()
                            if dataset.created_at
                            else None
                        ),
                    }
                return None

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Failed to get dataset info: {e}")
            return None

    def get_extraction_history(
        self, dataset_name: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get extraction history for a dataset.

        Args:
            dataset_name: Name of the dataset
            limit: Maximum number of records to return

        Returns:
            List of extraction records
        """
        try:
            session = self.Session()
            try:
                extractions = (
                    session.query(SpatialExtraction)
                    .filter_by(dataset_name=dataset_name)
                    .order_by(SpatialExtraction.extraction_start.desc())
                    .limit(limit)
                    .all()
                )

                return [
                    {
                        "id": ext.id,
                        "extraction_start": ext.extraction_start.isoformat(),
                        "success": ext.success,
                        "records_extracted": ext.records_extracted,
                        "duration_seconds": (
                            float(ext.duration_seconds)
                            if ext.duration_seconds
                            else None
                        ),
                        "output_file": ext.output_file,
                        "file_size_mb": (
                            float(ext.file_size_mb) if ext.file_size_mb else None
                        ),
                        "crs": ext.crs,
                        "geometry_type": ext.geometry_type,
                    }
                    for ext in extractions
                ]

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Failed to get extraction history: {e}")
            return []

    def register_dataset(self, dataset_config: Dict[str, Any]) -> bool:
        """Register a dataset in the catalog.

        Args:
            dataset_config: Dataset configuration dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            self.ensure_spatial_tables_exist()

            dataset = SpatialDataset(
                dataset_name=dataset_config["dataset_name"],
                description=dataset_config.get("description"),
                source_type=dataset_config.get("source_type"),
                source_url=dataset_config.get("url"),
                download_url=dataset_config.get("download_url"),
                spatial_type=dataset_config.get("spatial_type"),
                coordinate_system=dataset_config.get("coordinate_system"),
                update_frequency=dataset_config.get("update_frequency"),
                model_critical=dataset_config.get("model_critical", False),
                expected_features=dataset_config.get("expected_features"),
            )

            session = self.Session()
            try:
                # Use merge to handle duplicates
                session.merge(dataset)
                session.commit()
                logger.info(f"Registered dataset: {dataset_config['dataset_name']}")
                return True

            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Failed to register dataset: {e}")
                return False
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Failed to register dataset: {e}")
            return False

    def get_dataset_stats(self) -> Dict[str, Any]:
        """Get overall statistics about spatial datasets.

        Returns:
            Statistics dictionary
        """
        try:
            session = self.Session()
            try:
                # Count datasets
                dataset_count = session.query(SpatialDataset).count()

                # Count successful extractions
                successful_extractions = (
                    session.query(SpatialExtraction).filter_by(success=True).count()
                )

                # Count total extractions
                total_extractions = session.query(SpatialExtraction).count()

                # Get recent activity
                recent_extractions = (
                    session.query(SpatialExtraction)
                    .order_by(SpatialExtraction.extraction_start.desc())
                    .limit(5)
                    .all()
                )

                success_rate = (
                    (successful_extractions / total_extractions * 100)
                    if total_extractions > 0
                    else 0
                )

                return {
                    "total_datasets": dataset_count,
                    "total_extractions": total_extractions,
                    "successful_extractions": successful_extractions,
                    "success_rate_percent": round(success_rate, 1),
                    "recent_activity": [
                        {
                            "dataset_name": ext.dataset_name,
                            "extraction_start": ext.extraction_start.isoformat(),
                            "success": ext.success,
                            "records_extracted": ext.records_extracted,
                        }
                        for ext in recent_extractions
                    ],
                }

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Failed to get dataset stats: {e}")
            return {}

    def close(self):
        """Close database connections."""
        try:
            if self.db_manager:
                self.db_manager.close()
            if self.postgres_logger:
                self.postgres_logger.close()
            logger.debug("Closed spatial data logger connections")
        except Exception as e:
            logger.error(f"Error closing spatial data logger: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
