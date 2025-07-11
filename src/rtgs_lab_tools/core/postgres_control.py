"""Global postgres logging control for RTGS Lab Tools."""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def enable_postgres_logging() -> None:
    """Enable postgres logging globally by updating .env file."""
    logger.info("Postgres logging enabled globally")
    logger.info(
        "Note: Set POSTGRES_LOGGING_STATUS=true in your .env file to persist this setting"
    )


def disable_postgres_logging() -> None:
    """Disable postgres logging globally by updating .env file."""
    logger.info("Postgres logging disabled globally")
    logger.info(
        "Note: Set POSTGRES_LOGGING_STATUS=false in your .env file to persist this setting"
    )


def is_postgres_logging_enabled() -> bool:
    """Check if postgres logging is enabled by reading from .env file.

    Returns:
        True if postgres logging is enabled, False otherwise (default)
    """
    status = os.getenv("POSTGRES_LOGGING_STATUS", "false").lower()
    return status in ("true", "1", "yes", "on")


def get_postgres_logging_status() -> dict:
    """Get the current postgres logging status from .env file.

    Returns:
        Dictionary with status information
    """
    enabled = is_postgres_logging_enabled()
    return {"enabled": enabled, "status": "enabled" if enabled else "disabled"}
