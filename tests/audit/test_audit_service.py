"""Tests for audit service."""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from rtgs_lab_tools.audit.audit_service import AuditService
from rtgs_lab_tools.core.exceptions import DatabaseError


class TestAuditService:
    """Test the audit service class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock()
        config.db_host = "test-host"
        config.db_port = 5432
        config.db_name = "test_db"
        config.db_user = "test_user"
        config.db_password = "test_password"
        return config

    @pytest.fixture
    def mock_postgres_logger(self):
        """Mock PostgresLogger for testing."""
        with patch("rtgs_lab_tools.audit.audit_service.PostgresLogger") as mock_logger:
            yield mock_logger

    @pytest.fixture
    def audit_service(self, mock_config, mock_postgres_logger):
        """Create audit service instance for testing."""
        return AuditService(mock_config)

    def test_init_with_config(self, mock_config, mock_postgres_logger):
        """Test audit service initialization with config."""
        service = AuditService(mock_config)
        assert service.config == mock_config
        mock_postgres_logger.assert_called_once_with("audit", mock_config)

    def test_init_without_config(self, mock_postgres_logger):
        """Test audit service initialization without config."""
        with patch("rtgs_lab_tools.audit.audit_service.Config") as mock_config_class:
            mock_config_instance = Mock()
            mock_config_class.return_value = mock_config_instance

            service = AuditService()
            assert service.config == mock_config_instance
            mock_postgres_logger.assert_called_once_with("audit", mock_config_instance)

    def test_get_logs_by_date_range(self, audit_service):
        """Test getting logs by date range."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)

        # Mock database session and query
        mock_session = Mock()
        mock_query = Mock()
        mock_log = Mock()
        mock_log.id = 1
        mock_log.timestamp = datetime(2023, 1, 15, 10, 0, 0)
        mock_log.tool_name = "test_tool"
        mock_log.operation = "test_operation"
        mock_log.execution_source = "test"
        mock_log.triggered_by = "user"
        mock_log.hostname = "test-host"
        mock_log.platform = "linux"
        mock_log.python_version = "3.9"
        mock_log.working_directory = "/test"
        mock_log.script_path = "/test/script.py"
        mock_log.success = True
        mock_log.duration_seconds = 1.5
        mock_log.parameters = '{"param1": "value1"}'
        mock_log.results = '{"result": "success"}'
        mock_log.environment_variables = '{"ENV_VAR": "value"}'
        mock_log.note = "test note"
        mock_log.log_file_path = "/test/log.log"
        mock_log.git_commit = "abc123"
        mock_log.git_branch = "main"
        mock_log.git_dirty = False
        mock_log.command = "test command"
        mock_log.created_at = datetime(2023, 1, 15, 10, 0, 0)

        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_log]
        mock_session.query.return_value = mock_query

        audit_service.logger.Session.return_value = mock_session

        logs = audit_service.get_logs_by_date_range(start_date, end_date)

        assert len(logs) == 1
        assert logs[0]["id"] == 1
        assert logs[0]["tool_name"] == "test_tool"
        assert logs[0]["operation"] == "test_operation"
        assert logs[0]["success"] is True
        assert logs[0]["parameters"] == {"param1": "value1"}
        assert logs[0]["results"] == {"result": "success"}

    def test_get_logs_by_date_range_with_tool_filter(self, audit_service):
        """Test getting logs by date range with tool name filter."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        tool_name = "specific_tool"

        mock_session = Mock()
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query

        audit_service.logger.Session.return_value = mock_session

        logs = audit_service.get_logs_by_date_range(start_date, end_date, tool_name)

        # Verify the filter was called twice (date range + tool name)
        assert mock_query.filter.call_count == 2
        assert logs == []

    def test_get_logs_by_date_range_database_error(self, audit_service):
        """Test database error handling in get_logs_by_date_range."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)

        audit_service.logger.Session.side_effect = Exception(
            "Database connection failed"
        )

        with pytest.raises(DatabaseError) as excinfo:
            audit_service.get_logs_by_date_range(start_date, end_date)

        assert "Failed to get logs" in str(excinfo.value)

    def test_get_recent_logs_with_limit(self, audit_service):
        """Test getting recent logs with limit."""
        with patch.object(audit_service, "get_logs_by_date_range") as mock_get_logs:
            mock_get_logs.return_value = [{"id": 1}, {"id": 2}, {"id": 3}]

            logs = audit_service.get_recent_logs(limit=2)

            assert len(logs) == 2
            assert logs == [{"id": 1}, {"id": 2}]

    def test_get_recent_logs_with_minutes_filter(self, audit_service):
        """Test getting recent logs with minutes filter."""
        with patch.object(audit_service, "get_logs_by_date_range") as mock_get_logs:
            mock_get_logs.return_value = [{"id": 1}, {"id": 2}]

            logs = audit_service.get_recent_logs(limit=10, minutes=30)

            assert len(logs) == 2
            mock_get_logs.assert_called_once()

    def test_get_recent_logs_with_tool_filter(self, audit_service):
        """Test getting recent logs with tool name filter."""
        with patch.object(audit_service, "get_logs_by_date_range") as mock_get_logs:
            mock_get_logs.return_value = [{"id": 1}]

            logs = audit_service.get_recent_logs(limit=10, tool_name="specific_tool")

            assert len(logs) == 1
            mock_get_logs.assert_called_once()

    def test_log_audit_operation(self, audit_service):
        """Test logging an audit operation."""
        operation = "test_operation"
        parameters = {"param1": "value1"}
        results = {"result": "success"}

        audit_service.logger.log_execution.return_value = True

        success = audit_service.log_audit_operation(operation, parameters, results)

        assert success is True
        audit_service.logger.log_execution.assert_called_once_with(
            operation=operation,
            parameters=parameters,
            results=results,
            script_path=audit_service.log_audit_operation.__code__.co_filename,
        )

    def test_log_audit_operation_failure(self, audit_service):
        """Test logging an audit operation failure."""
        operation = "test_operation"
        parameters = {"param1": "value1"}
        results = {"result": "failure"}

        audit_service.logger.log_execution.return_value = False

        success = audit_service.log_audit_operation(operation, parameters, results)

        assert success is False

    def test_close(self, audit_service):
        """Test closing the audit service."""
        mock_db_manager = Mock()
        audit_service.logger.db_manager = mock_db_manager

        audit_service.close()

        mock_db_manager.close.assert_called_once()

    def test_close_no_db_manager(self, audit_service):
        """Test closing the audit service when no db_manager exists."""
        audit_service.logger.db_manager = None

        # Should not raise an exception
        audit_service.close()

    def test_close_no_db_manager_attribute(self, audit_service):
        """Test closing the audit service when db_manager attribute doesn't exist."""
        delattr(audit_service.logger, "db_manager")

        # Should not raise an exception
        audit_service.close()

    def test_logs_with_null_json_fields(self, audit_service):
        """Test handling logs with null JSON fields."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)

        mock_session = Mock()
        mock_query = Mock()
        mock_log = Mock()
        mock_log.id = 1
        mock_log.timestamp = datetime(2023, 1, 15, 10, 0, 0)
        mock_log.tool_name = "test_tool"
        mock_log.operation = "test_operation"
        mock_log.execution_source = "test"
        mock_log.triggered_by = "user"
        mock_log.hostname = "test-host"
        mock_log.platform = "linux"
        mock_log.python_version = "3.9"
        mock_log.working_directory = "/test"
        mock_log.script_path = "/test/script.py"
        mock_log.success = True
        mock_log.duration_seconds = 1.5
        mock_log.parameters = None  # Null JSON field
        mock_log.results = None  # Null JSON field
        mock_log.environment_variables = None  # Null JSON field
        mock_log.note = "test note"
        mock_log.log_file_path = "/test/log.log"
        mock_log.git_commit = "abc123"
        mock_log.git_branch = "main"
        mock_log.git_dirty = False
        mock_log.command = "test command"
        mock_log.created_at = datetime(2023, 1, 15, 10, 0, 0)

        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_log]
        mock_session.query.return_value = mock_query

        audit_service.logger.Session.return_value = mock_session

        logs = audit_service.get_logs_by_date_range(start_date, end_date)

        assert len(logs) == 1
        assert logs[0]["parameters"] == {}
        assert logs[0]["results"] == {}
        assert logs[0]["environment_variables"] == {}
