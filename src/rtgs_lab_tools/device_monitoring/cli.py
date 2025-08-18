"""
Overview:
    - CLI module for device monitoring
arguments:
    start_date: datetime
    end_date: datetime
    node_ids: list of node ids
    project: str
"""

from datetime import datetime, timedelta
from pathlib import Path

import click

from ..core.cli_utils import (
    CLIContext,
    add_common_options,
    handle_common_errors,
)
from .config import DATA_COLLECTION_WINDOW_DAYS
from .core import monitor


@click.group()
@click.pass_context
def device_monitoring_cli(ctx):
    """Device monitoring tools."""
    ctx.ensure_object(CLIContext)


@device_monitoring_cli.command()
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date for data retrieval in 'YYYY-MM-DD' format.",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date for data retrieval in 'YYYY-MM-DD' format.",
)
@click.option(
    "--node-ids",
    type=str,
    help="Comma-separated list of node IDs to filter the data.",
)
@click.option(
    "--project",
    type=str,
    help="Comma-separated list of project names to filter the data.",
)
@click.option(
    "--no-email",
    is_flag=True,
    help="Skip sending email notifications.",
)
@click.pass_context
@handle_common_errors("device-monitoring")
def monitor_cmd(ctx, start_date, end_date, node_ids, project, no_email):
    """Monitor device data."""

    # Convert datetime objects to strings, or use defaults
    start_date_str = (
        start_date.strftime("%Y-%m-%d")
        if start_date
        else (datetime.now() - timedelta(days=DATA_COLLECTION_WINDOW_DAYS)).strftime(
            "%Y-%m-%d"
        )
    )
    end_date_str = (
        end_date.strftime("%Y-%m-%d")
        if end_date
        else datetime.now().strftime("%Y-%m-%d")
    )

    monitor(
        start_date=start_date_str,
        end_date=end_date_str,
        # node_ids=node_ids,
        node_ids=None,
        project=project or "ALL",
        no_email=no_email or False,
    )


if __name__ == "__main__":
    device_monitoring_cli()
