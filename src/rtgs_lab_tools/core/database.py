"""Database management for RTGS Lab Tools."""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from .config import Config
from .exceptions import DatabaseError

try:
    import pg8000
    from google.cloud.sql.connector import Connector, IPTypes

    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations for GEMS database."""

    def __init__(self, config: Optional[Config] = None, use_gcp: bool = False):
        """Initialize database manager.

        Args:
            config: Configuration instance. If None, creates a new one.
            use_gcp: Whether to use GCP Cloud SQL authentication
        """
        self.config = config or Config()
        self.use_gcp = use_gcp
        self._engine: Optional[Engine] = None
        self._connector: Optional[Any] = None

    def _create_gcp_engine(self, instance_connection_name: str) -> Engine:
        """Create database engine using GCP Cloud SQL Connector.

        Args:
            instance_connection_name: GCP Cloud SQL instance connection name

        Returns:
            SQLAlchemy engine
        """
        if not GCP_AVAILABLE:
            raise DatabaseError("GCP Cloud SQL dependencies not installed")

        try:
            self._connector = Connector(
                refresh_strategy="LAZY",
                enable_iam_auth=False,  # Using username/password auth
            )
        except Exception as e:
            if "default credentials were not found" in str(e):
                raise DatabaseError(
                    "GCP authentication failed. Please set up Application Default Credentials. "
                    "Run: gcloud auth application-default login"
                )
            raise DatabaseError(f"Failed to initialize GCP Cloud SQL connector: {e}")

        def getconn():
            conn = self._connector.connect(
                instance_connection_name,
                "pg8000",
                user=self.config.logging_db_user,
                password=self.config.logging_db_password,
                db=self.config.logging_db_name,
                ip_type=IPTypes.PUBLIC,
            )
            return conn

        return create_engine(
            "postgresql+pg8000://",
            creator=getconn,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

    @property
    def engine(self) -> Engine:
        """Get or create database engine."""
        if self._engine is None:
            try:
                if self.use_gcp and self.config.logging_instance_connection_name:
                    try:
                        self._engine = self._create_gcp_engine(
                            self.config.logging_instance_connection_name
                        )
                        logger.info(
                            "GCP Cloud SQL logging database connection established"
                        )
                    except DatabaseError as e:
                        logger.warning(
                            f"GCP connection failed, falling back to traditional connection: {e}"
                        )
                        self._engine = create_engine(
                            self.config.logging_db_url,
                            echo=False,
                            pool_pre_ping=True,
                            pool_recycle=3600,
                        )
                        logger.info(
                            "Traditional logging database connection established (fallback)"
                        )
                elif self.use_gcp:
                    self._engine = create_engine(
                        self.config.logging_db_url,
                        echo=False,
                        pool_pre_ping=True,
                        pool_recycle=3600,
                    )
                    logger.info("Traditional logging database connection established")
                else:
                    self._engine = create_engine(
                        self.config.db_url,
                        echo=False,
                        pool_pre_ping=True,
                        pool_recycle=3600,
                    )
                    logger.info("Traditional main database connection established")
            except SQLAlchemyError as e:
                raise DatabaseError(f"Failed to create database engine: {e}")

        return self._engine

    def test_connection(self) -> bool:
        """Test database connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            logger.info("Database connection test successful")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """Execute a SQL query and return results as DataFrame.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            Query results as pandas DataFrame

        Raises:
            DatabaseError: If query execution fails
        """
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql_query(text(query), conn, params=params or {})
            logger.debug(f"Query executed successfully, returned {len(df)} rows")
            return df
        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            raise DatabaseError(f"Query execution failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during query execution: {e}")
            raise DatabaseError(f"Unexpected error: {e}")

    def get_projects(self) -> List[str]:
        """Get list of available projects.

        Returns:
            List of project names
        """
        query = "SELECT DISTINCT project FROM node WHERE project IS NOT NULL ORDER BY project"
        df = self.execute_query(query)
        return df["project"].tolist()

    def get_nodes_for_project(self, project: str) -> pd.DataFrame:
        """Get nodes for a specific project.

        Args:
            project: Project name

        Returns:
            DataFrame with node information
        """
        query = """
        SELECT node_id, project, location, latitude, longitude, deployment_date
        FROM node 
        WHERE project = :project 
        ORDER BY node_id
        """
        return self.execute_query(query, {"project": project})

    def close(self):
        """Close database connection."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
        if self._connector:
            self._connector.close()
            self._connector = None
        logger.info("Database connection closed")
