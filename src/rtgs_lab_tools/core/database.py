"""Database management for RTGS Lab Tools."""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from .config import Config
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations for GEMS database."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize database manager.

        Args:
            config: Configuration instance. If None, creates a new one.
        """
        self.config = config or Config()
        self._engine: Optional[Engine] = None

    @property
    def engine(self) -> Engine:
        """Get or create database engine."""
        if self._engine is None:
            try:
                self._engine = create_engine(
                    self.config.db_url,
                    echo=False,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                )
                logger.info("Database connection established")
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
            logger.info("Database connection closed")
