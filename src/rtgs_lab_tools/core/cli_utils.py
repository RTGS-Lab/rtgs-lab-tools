"""Shared CLI utilities for RTGS Lab Tools."""

import logging
import sys
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

import click

from .exceptions import (
    APIError,
    ConfigError,
    DatabaseError,
    RTGSLabToolsError,
    ValidationError,
)
from .postgres_logger import PostgresLogger
from .logging import setup_logging


def setup_logging_for_tool(
    tool_name: str, verbose: bool = False, log_file: Optional[str] = None
) -> logging.Logger:
    """Set up logging for a specific tool.

    Args:
        tool_name: Name of the tool for logger naming
        verbose: Enable verbose (DEBUG) logging
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    log_level = "DEBUG" if verbose else "INFO"
    logger = setup_logging(log_level, log_file=log_file)
    return logger


def setup_postgres_logger(tool_name: str, disable: bool = False) -> Optional[PostgresLogger]:
    """Set up postgres logger for a specific tool.

    Args:
        tool_name: Name of the tool for postgres logging
        disable: Whether to disable postgres logging

    Returns:
        PostgresLogger instance or None if disabled/failed
    """
    if disable:
        return None

    try:
        return PostgresLogger(tool_name=tool_name)
    except Exception as e:
        # Log warning but don't fail the tool
        logging.getLogger().warning(
            f"Failed to initialize postgres logging for {tool_name}: {e}"
        )
        return None


def log_error_to_postgres(
    postgres_logger: Optional[PostgresLogger],
    error_type: str,
    error: Exception,
    start_time: datetime,
    parameters: Dict[str, Any],
    script_path: str,
):
    """Helper function to log errors to postgres.

    Args:
        postgres_logger: PostgresLogger instance (can be None)
        error_type: Type/category of error
        error: The exception that occurred
        start_time: When the operation started
        parameters: Parameters passed to the operation
        script_path: Path to the script being executed
    """
    if not postgres_logger:
        return

    try:
        operation = f"Operation failed - {error_type}"

        results = {
            "success": False,
            "error": str(error),
            "error_type": error_type,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
        }

        postgres_logger.log_execution(
            operation=operation,
            parameters=parameters,
            results=results,
            script_path=script_path,
        )
    except Exception:
        # Don't let postgres logging errors crash the application
        pass


def handle_common_errors(tool_name: str):
    """Decorator to handle common errors across all CLI tools.

    Args:
        tool_name: Name of the tool for error context
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ConfigError as e:
                click.echo(f"Configuration error: {e}", err=True)
                click.echo(
                    "Run with --setup-credentials to create a template .env file",
                    err=True,
                )
                sys.exit(1)
            except DatabaseError as e:
                click.echo(f"Database error: {e}", err=True)
                click.echo(
                    "Ensure you are connected to the UMN VPN and have valid credentials",
                    err=True,
                )
                sys.exit(1)
            except APIError as e:
                click.echo(f"API error: {e}", err=True)
                sys.exit(1)
            except ValidationError as e:
                click.echo(f"Validation error: {e}", err=True)
                sys.exit(1)
            except RTGSLabToolsError as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)
            except Exception as e:
                click.echo(f"Unexpected error in {tool_name}: {e}", err=True)
                sys.exit(1)

        return wrapper

    return decorator


def add_common_options(func: Callable) -> Callable:
    """Add common CLI options to a command.

    Args:
        func: Click command function to decorate

    Returns:
        Decorated function with common options
    """
    # Add options in reverse order due to how decorators work
    func = click.option(
        "--no-postgres-log", is_flag=True, help="Disable automatic postgres logging"
    )(func)
    func = click.option("--note", help="Note describing the purpose of this operation")(
        func
    )
    func = click.option("--log-file", help="Log to file")(func)
    func = click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")(
        func
    )
    return func


def create_setup_credentials_command():
    """Create the setup-credentials command that can be reused."""

    @click.command()
    def setup_credentials():
        """Create template .env file with credentials."""
        from pathlib import Path

        env_path = Path.cwd() / ".env"

        # Check if .env already exists
        if env_path.exists():
            click.echo(f".env file already exists at {env_path}")
            if not click.confirm("Do you want to overwrite it?"):
                click.echo("Operation cancelled.")
                return

        # Create template content
        template_content = """# GEMS Database Configuration
# Update these values with your actual credentials

DB_HOST=sensing-0.msi.umn.edu
DB_PORT=5433
DB_NAME=gems
DB_USER=your_username
DB_PASSWORD=your_password

# Optional API Keys
PARTICLE_ACCESS_TOKEN=your_particle_token
CDS_API_KEY=your_cds_api_key
"""

        # Write template file
        with open(env_path, "w") as f:
            f.write(template_content)

        click.echo(f"Created template .env file at {env_path}")
        click.echo("\nPlease edit this file and update the credentials:")
        click.echo("1. Replace 'your_username' with your database username")
        click.echo("2. Replace 'your_password' with your database password")
        click.echo("3. Ensure you are connected to the UMN VPN")
        click.echo("\nFor database access, contact the RTGS Lab.")

    return setup_credentials


def validate_date_format(date_str: str, param_name: str) -> str:
    """Validate date format and return normalized date string.

    Args:
        date_str: Date string to validate
        param_name: Parameter name for error messages

    Returns:
        Validated date string

    Raises:
        ValidationError: If date format is invalid
    """
    try:
        # Try parsing the date
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise ValidationError(
            f"Invalid {param_name} format. Use YYYY-MM-DD (e.g., 2023-01-01)"
        )


def parse_node_ids(node_id_str: Optional[str]) -> Optional[list]:
    """Parse comma-separated node IDs.

    Args:
        node_id_str: Comma-separated node ID string

    Returns:
        List of node IDs or None
    """
    if not node_id_str:
        return None

    return [n.strip() for n in node_id_str.split(",") if n.strip()]


def parse_area_bounds(area_str: str) -> list:
    """Parse area bounds string into list of floats.

    Args:
        area_str: Area bounds as "north,west,south,east"

    Returns:
        List of [north, west, south, east] floats

    Raises:
        ValidationError: If area format is invalid
    """
    try:
        bounds = [float(x.strip()) for x in area_str.split(",")]
        if len(bounds) != 4:
            raise ValueError()
        return bounds
    except ValueError:
        raise ValidationError(
            "Area must be 'north,west,south,east' (4 comma-separated numbers)"
        )


def parse_comma_separated_list(
    list_str: str, item_type: type = str, item_name: str = "items"
) -> list:
    """Parse comma-separated list with type conversion.

    Args:
        list_str: Comma-separated string
        item_type: Type to convert items to
        item_name: Name for error messages

    Returns:
        List of converted items

    Raises:
        ValidationError: If conversion fails
    """
    try:
        return [item_type(x.strip()) for x in list_str.split(",") if x.strip()]
    except ValueError as e:
        raise ValidationError(f"Invalid {item_name} format: {e}")


# Parameter decorator factories for eliminating CLI parameter duplication
def device_config_parameters(func: Callable) -> Callable:
    """Add device configuration parameters to a command."""
    # Add options in reverse order due to how decorators work
    func = click.option(
        "--no-particle-postgres-log",
        is_flag=True,
        help="Disable Particle-specific postgres logging (CLI logging still active)",
    )(func)
    func = click.option(
        "--dry-run", is_flag=True, help="Validate inputs without making changes"
    )(func)
    func = click.option(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum concurrent devices to process",
    )(func)
    func = click.option(
        "--online-timeout",
        type=int,
        default=120,
        help="Seconds to wait for device to come online",
    )(func)
    func = click.option(
        "--restart-wait",
        type=int,
        default=30,
        help="Seconds to wait for device restart",
    )(func)
    func = click.option(
        "--max-retries", type=int, default=3, help="Maximum retry attempts per device"
    )(func)
    func = click.option(
        "--output", default="update_results.json", help="Output file for results"
    )(func)
    func = click.option(
        "--devices",
        required=True,
        help="Path to device list file OR comma/space separated device IDs",
    )(func)
    func = click.option(
        "--config", required=True, help="Path to configuration JSON file OR JSON string"
    )(func)
    return func


def error_analysis_parameters(func: Callable) -> Callable:
    """Add error analysis parameters to a command."""
    # Add options in reverse order due to how decorators work
    func = click.option("--output-analysis", help="Save analysis results to JSON file")(
        func
    )
    func = click.option(
        "--output-dir", default="figures", help="Output directory for plots"
    )(func)
    func = click.option("--nodes", help="Comma-separated list of node IDs to analyze")(
        func
    )
    func = click.option(
        "--generate-graph", is_flag=True, help="Generate error frequency graphs"
    )(func)
    func = click.option(
        "--error-column", default="message", help="Column containing error data"
    )(func)
    func = click.option(
        "--file", "-f", required=True, help="CSV or JSON file with error data"
    )(func)
    return func


def sensing_data_parameters(func: Callable) -> Callable:
    """Add sensing data extraction parameters to a command."""
    # Add options in reverse order due to how decorators work
    func = click.option(
        "--retry-count", type=int, default=3, help="Maximum retry attempts"
    )(func)
    func = click.option(
        "--create-zip", is_flag=True, help="Create zip archive with metadata"
    )(func)
    func = click.option(
        "--output",
        type=click.Choice(["csv", "parquet"]),
        default="csv",
        help="Output format",
    )(func)
    func = click.option(
        "--output-dir", help="Output directory for data files (default: ./data)"
    )(func)
    func = click.option("--node-id", help="Comma-separated list of node IDs to query")(
        func
    )
    func = click.option("--end-date", help="End date (YYYY-MM-DD), defaults to today")(
        func
    )
    func = click.option(
        "--start-date", default="2018-01-01", help="Start date (YYYY-MM-DD)"
    )(func)
    func = click.option(
        "--setup-credentials", is_flag=True, help="Create template .env file"
    )(func)
    func = click.option(
        "--list-projects", is_flag=True, help="List all available projects and exit"
    )(func)
    func = click.option("--project", "-p", help="Project name to query")(func)
    return func


def visualization_parameters(func: Callable) -> Callable:
    """Add visualization parameters to a command."""
    # Add options in reverse order due to how decorators work
    func = click.option(
        "--no-markers", is_flag=True, help="Disable data point markers"
    )(func)
    func = click.option("--title", help="Plot title")(func)
    func = click.option(
        "--list-params", is_flag=True, help="List available parameters and exit"
    )(func)
    func = click.option(
        "--format",
        "output_format",
        type=click.Choice(["png", "pdf", "svg"]),
        default="png",
        help="Output format",
    )(func)
    func = click.option("--output-file", help="Output filename (without extension)")(
        func
    )
    func = click.option(
        "--output-dir", default="figures", help="Output directory for plots"
    )(func)
    func = click.option(
        "--multi-param",
        multiple=True,
        help='Multiple parameters as "node_id,parameter_path"',
    )(func)
    func = click.option("--node-id", help="Specific node ID to plot")(func)
    func = click.option(
        "--parameter",
        "-p",
        help='Parameter path to plot (e.g., "Data.Devices.0.Temperature")',
    )(func)
    func = click.option(
        "--file", "-f", required=True, help="CSV file with sensor data"
    )(func)
    return func


# Context class for passing data between CLI commands
class CLIContext:
    """Context object for sharing data between CLI commands."""

    def __init__(self):
        self.logger: Optional[logging.Logger] = None
        self.postgres_logger: Optional[PostgresLogger] = None
        self.start_time: Optional[datetime] = None
        self.tool_name: Optional[str] = None

    def setup(
        self,
        tool_name: str,
        verbose: bool = False,
        log_file: Optional[str] = None,
        no_postgres_log: bool = False,
    ):
        """Set up context for a tool.

        Args:
            tool_name: Name of the tool
            verbose: Enable verbose logging
            log_file: Optional log file
            no_postgres_log: Disable postgres logging
        """
        self.tool_name = tool_name
        self.logger = setup_logging_for_tool(tool_name, verbose, log_file)
        self.postgres_logger = setup_postgres_logger(tool_name, no_postgres_log)
        self.start_time = datetime.now()

    def log_error(
        self,
        error_type: str,
        error: Exception,
        parameters: Dict[str, Any],
        script_path: str,
    ):
        """Log error to postgres if postgres logger is available."""
        if self.postgres_logger and self.start_time:
            log_error_to_postgres(
                self.postgres_logger,
                error_type,
                error,
                self.start_time,
                parameters,
                script_path,
            )

    def log_success(
        self,
        operation: str,
        parameters: Dict[str, Any],
        results: Dict[str, Any],
        script_path: str,
        additional_sections: Optional[Dict[str, str]] = None,
    ):
        """Log successful operation to postgres if postgres logger is available."""
        if self.postgres_logger:
            try:
                self.postgres_logger.log_execution(
                    operation=operation,
                    parameters=parameters,
                    results=results,
                    script_path=script_path,
                    additional_sections=additional_sections,
                )
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to create postgres log: {e}")
