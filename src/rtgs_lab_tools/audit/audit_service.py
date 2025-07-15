"""Core audit service for business logic operations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import and_

from ..core.config import Config
from ..core.exceptions import DatabaseError
from ..core.postgres_logger import PostgresLogger, ToolCallLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service class for audit operations business logic."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize audit service."""
        self.config = config or Config()
        self.logger = PostgresLogger("audit", self.config)

    def get_logs_by_date_range(
        self, start_date: datetime, end_date: datetime, tool_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get logs within a date range.

        Args:
            start_date: Start date for the range
            end_date: End date for the range
            tool_name: Optional tool name filter

        Returns:
            List of log dictionaries
        """
        try:
            session = self.logger.Session()
            try:
                query = session.query(ToolCallLog).filter(
                    and_(
                        ToolCallLog.timestamp >= start_date,
                        ToolCallLog.timestamp <= end_date,
                    )
                )

                if tool_name:
                    query = query.filter(ToolCallLog.tool_name == tool_name)

                logs = query.order_by(ToolCallLog.timestamp.desc()).all()

                return [
                    {
                        "id": log.id,
                        "timestamp": log.timestamp.isoformat(),
                        "tool_name": log.tool_name,
                        "operation": log.operation,
                        "execution_source": log.execution_source,
                        "triggered_by": log.triggered_by,
                        "hostname": log.hostname,
                        "platform": log.platform,
                        "python_version": log.python_version,
                        "working_directory": log.working_directory,
                        "script_path": log.script_path,
                        "success": log.success,
                        "duration_seconds": log.duration_seconds,
                        "parameters": (
                            json.loads(log.parameters) if log.parameters else {}
                        ),
                        "results": json.loads(log.results) if log.results else {},
                        "environment_variables": (
                            json.loads(log.environment_variables)
                            if log.environment_variables
                            else {}
                        ),
                        "note": log.note,
                        "log_file_path": log.log_file_path,
                        "git_commit": log.git_commit,
                        "git_branch": log.git_branch,
                        "git_dirty": log.git_dirty,
                        "command": log.command,
                        "created_at": log.created_at.isoformat(),
                    }
                    for log in logs
                ]
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Failed to get logs by date range: {e}")
            raise DatabaseError(f"Failed to get logs: {e}")

    def get_recent_logs(
        self,
        limit: int = 10,
        tool_name: Optional[str] = None,
        minutes: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent logs.

        Args:
            limit: Maximum number of logs to return
            tool_name: Optional tool name filter
            minutes: Only show logs from the last N minutes

        Returns:
            List of log dictionaries
        """
        if minutes:
            end_date = datetime.now()
            start_date = datetime.now().replace(
                minute=max(0, end_date.minute - minutes)
            )
            return self.get_logs_by_date_range(start_date, end_date, tool_name)[:limit]
        else:
            # Get all logs and filter by tool if specified
            # For simplicity, we'll use a large date range
            end_date = datetime.now()
            start_date = datetime(2020, 1, 1)  # Far back start date
            return self.get_logs_by_date_range(start_date, end_date, tool_name)[:limit]

    def log_audit_operation(
        self, operation: str, parameters: Dict[str, Any], results: Dict[str, Any]
    ) -> bool:
        """Log an audit operation to the database.

        Args:
            operation: Description of the operation
            parameters: Parameters used
            results: Results of the operation

        Returns:
            True if successful, False otherwise
        """
        return self.logger.log_execution(
            operation=operation,
            parameters=parameters,
            results=results,
            script_path=__file__,
        )

    def close(self):
        """Close database connections and cleanup resources."""
        if hasattr(self.logger, "db_manager") and self.logger.db_manager:
            self.logger.db_manager.close()
