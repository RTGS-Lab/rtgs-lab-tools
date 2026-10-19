"""
Overview:
    - CLI module for device monitoring
arguments:
    start_date: datetime
    end_date: datetime
    node_ids: list of node ids
    project: str
"""
import sys

# line_buffering=True matters as much as the encoding here. When stdout is
# redirected to a file (as it is under cron) Python block-buffers it, so if the
# process is killed or hangs, every progress message still sitting in the buffer
# is lost -- which is why a stalled run produced a log that looked like the
# pipeline never started. Line buffering flushes each print as it happens, so
# the log always shows how far the run actually got.
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

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
from .timezones import now_utc


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
        # UTC: these bound a query against GEMS publish_time, which is UTC.
        else (now_utc() - timedelta(days=DATA_COLLECTION_WINDOW_DAYS)).strftime(
            "%Y-%m-%d"
        )
    )
    end_date_str = (
        end_date.strftime("%Y-%m-%d")
        if end_date
        else now_utc().strftime("%Y-%m-%d")
    )


    monitor(
        start_date=start_date_str,
        end_date=end_date_str,
        # node_ids=node_ids,
        node_ids=None,
        project=project or "ALL",
        no_email=no_email or False,
    )


@device_monitoring_cli.command("publish")
@click.argument("batch_file", type=click.Path(exists=True, dir_okay=False))
def publish_cmd(batch_file):
    """Re-send a saved batch file to the ingest service (a stored batch is a no-op)."""
    from .publisher import publish_file

    publish_file(batch_file)


@device_monitoring_cli.command("check-ingest")
def check_ingest_cmd():
    """Fetch the ingest token from Secret Manager and call /health and /v1/status.

    Prints the secret version used and the HTTP statuses, never the token. Exit 0 ok,
    2 setup is wrong (key file, IAM, URL), 3 transient (network, 5xx): worth a retry.
    """
    import os

    import requests

    from . import ingest_token
    from .publisher import ingest_urls

    # Several services may be listed (primary first, then mirrors): the exit code is the
    # primary's; a mirror that fails is reported as a warning, as publish_all treats it.
    urls = ingest_urls() or [""]
    code = _check_one(urls[0], ingest_token, requests)
    for url in urls[1:]:
        if _check_one(url, ingest_token, requests):
            click.echo(f"check-ingest: WARNING: mirror {url} failed (the run still publishes to "
                       f"the primary)", err=True)
    if code:
        sys.exit(code)


def _check_one(url, ingest_token, requests):
    """check-ingest for one service; returns 0 ok, 2 setup, 3 transient."""
    try:
        base, _ = ingest_token.check_ingest_url(url)
        secret = ingest_token.secret_for(base)
        token, version = ingest_token.fetch_from_secret_manager(secret)
    except ingest_token.TokenError as e:
        click.echo(f"check-ingest: FAILED: {e}", err=True)
        return 3 if e.transient else 2
    click.echo(f"check-ingest: token from {version}")
    try:
        h = requests.get(f"{base}/health", timeout=(10, 30))
        s = requests.get(f"{base}/v1/status", timeout=(10, 30),
                         headers={"Authorization": f"Bearer {token}"})
    except requests.RequestException as e:
        click.echo(f"check-ingest: FAILED: {base} unreachable: {type(e).__name__}", err=True)
        return 3
    finally:
        del token
    click.echo(f"check-ingest: {base}/health HTTP {h.status_code}; /v1/status HTTP "
               f"{s.status_code} {s.text[:200] if s.status_code == 200 else ''}".rstrip())
    if s.status_code == 401:
        click.echo("check-ingest: FAILED: the service rejects this token (it pins secret "
                   "versions; redeploy it after adding a version)", err=True)
        return 2
    if h.status_code != 200 or s.status_code != 200:
        return 3 if max(h.status_code, s.status_code) >= 500 else 2
    return 0


if __name__ == "__main__":
    device_monitoring_cli()
