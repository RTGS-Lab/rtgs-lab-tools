"""Core utilities for RTGS Lab Tools."""

from .cli_utils import CLIContext, setup_logging_for_tool, setup_postgres_logger
from .config import Config
from .database import DatabaseManager
from .exceptions import (
    APIError,
    ConfigError,
    DatabaseError,
    RTGSLabToolsError,
    ValidationError,
)
from .logging import setup_logging
from .postgres_control import (
    disable_postgres_logging,
    enable_postgres_logging,
    get_postgres_logging_status,
    is_postgres_logging_enabled,
)
from .postgres_logger import PostgresLogger
from .update import (
    check_for_updates,
    get_current_version,
    get_latest_release_tag,
    get_version_info,
    run_install_script,
)

__all__ = [
    "DatabaseManager",
    "Config",
    "RTGSLabToolsError",
    "DatabaseError",
    "ConfigError",
    "APIError",
    "ValidationError",
    "setup_logging",
    "PostgresLogger",
    "CLIContext",
    "setup_logging_for_tool",
    "setup_postgres_logger",
    "enable_postgres_logging",
    "disable_postgres_logging",
    "is_postgres_logging_enabled",
    "get_postgres_logging_status",
    "check_for_updates",
    "get_current_version",
    "get_latest_release_tag",
    "get_version_info",
    "run_install_script",
]
