"""Custom exceptions for RTGS Lab Tools."""


class RTGSLabToolsError(Exception):
    """Base exception for RTGS Lab Tools."""

    pass


class DatabaseError(RTGSLabToolsError):
    """Exception raised for database-related errors."""

    pass


class ConfigError(RTGSLabToolsError):
    """Exception raised for configuration-related errors."""

    pass


class APIError(RTGSLabToolsError):
    """Exception raised for API-related errors."""

    pass


class ValidationError(RTGSLabToolsError):
    """Exception raised for data validation errors."""

    pass
