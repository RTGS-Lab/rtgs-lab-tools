"""CLI for audit functionality."""

import logging
import time
from datetime import datetime
from pathlib import Path

import click

from .audit_service import AuditService
from .report_service import ReportService
from ..core.postgres_control import (
    enable_postgres_logging,
    disable_postgres_logging,
    get_postgres_logging_status,
)

logger = logging.getLogger(__name__)


@click.group()
def audit_cli():
    """Audit and reporting tools for RTGS Lab Tools."""
    pass


@audit_cli.command()
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]),
    required=True,
    help="Start date for the audit range (YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS')",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]),
    required=True,
    help="End date for the audit range (YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS')",
)
@click.option(
    "--tool-name",
    type=str,
    help="Filter by specific tool name",
)
@click.option(
    "--output-dir",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default="logs",
    help="Output directory for audit reports",
)
def report(start_date, end_date, tool_name, output_dir):
    """Generate audit report with markdown files for the specified date range."""
    operation_start = time.time()

    try:
        click.echo(f"Generating audit report from {start_date} to {end_date}")
        if tool_name:
            click.echo(f"Filtering by tool: {tool_name}")

        # Use services for business logic
        audit_service = AuditService()
        report_service = ReportService()

        # Get logs using audit service
        logs = audit_service.get_logs_by_date_range(start_date, end_date, tool_name)

        if not logs:
            click.echo("No logs found for the specified date range.")
            operation_end = time.time()
            duration = operation_end - operation_start

            # Log operation
            parameters = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "tool_name": tool_name,
                "output_dir": str(output_dir),
            }
            results = {
                "success": True,
                "files_generated": 0,
                "duration": duration,
            }
            audit_service.log_audit_operation(
                "Generate audit report", parameters, results
            )

            # Create log file
            log_path = report_service.create_log_file(
                output_dir=output_dir,
                operation="Generate audit report",
                parameters=parameters,
                results=results,
            )
            click.echo(f"Audit operation logged: {log_path}")
            return

        # Generate report using report service
        created_files = report_service.generate_audit_report(logs, output_dir)

        operation_end = time.time()
        duration = operation_end - operation_start

        # Log this audit operation
        parameters = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "tool_name": tool_name,
            "output_dir": str(output_dir),
        }

        results = {
            "success": True,
            "files_generated": len(created_files),
            "output_directory": str(output_dir),
            "duration": duration,
            "created_files": created_files,
        }

        # Save to database
        audit_service.log_audit_operation("Generate audit report", parameters, results)

        # Create log file
        log_path = report_service.create_log_file(
            output_dir=output_dir,
            operation="Generate audit report",
            parameters=parameters,
            results=results,
            additional_sections={
                "Generated Files": (
                    "\n".join(f"- {f}" for f in created_files)
                    if created_files
                    else "No files generated"
                )
            },
        )

        click.echo(
            f"✅ Generated {len(created_files)} audit report files in {output_dir}"
        )
        for file_path in created_files:
            click.echo(f"   - {file_path}")
        click.echo(f"Audit operation logged: {log_path}")

    except Exception as e:
        operation_end = time.time()
        duration = operation_end - operation_start

        # Log the failed operation
        parameters = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "tool_name": tool_name,
            "output_dir": str(output_dir),
        }

        results = {
            "success": False,
            "error": str(e),
            "duration": duration,
        }

        try:
            audit_service = AuditService()
            report_service = ReportService()
            audit_service.log_audit_operation(
                "Generate audit report", parameters, results
            )

            log_path = report_service.create_log_file(
                output_dir=output_dir,
                operation="Generate audit report",
                parameters=parameters,
                results=results,
            )
            click.echo(f"Failed audit operation logged: {log_path}")
        except Exception:
            pass  # Don't fail if logging fails

        click.echo(f"❌ Error generating audit report: {e}", err=True)
        raise click.ClickException(str(e))


@audit_cli.command()
@click.option(
    "--limit",
    type=int,
    default=10,
    help="Number of recent logs to show",
)
@click.option(
    "--tool-name",
    type=str,
    help="Filter by specific tool name",
)
@click.option(
    "--minutes",
    type=int,
    help="Only show logs from the last N minutes",
)
def recent(limit, tool_name, minutes):
    """Show recent log entries."""
    operation_start = time.time()

    try:
        # Use audit service for business logic
        audit_service = AuditService()

        # Get recent logs using audit service
        logs = audit_service.get_recent_logs(limit, tool_name, minutes)

        operation_end = time.time()
        duration = operation_end - operation_start

        # Log this audit operation
        parameters = {
            "limit": limit,
            "tool_name": tool_name,
            "minutes": minutes,
        }

        results = {
            "success": True,
            "logs_found": len(logs),
            "logs_displayed": len(logs),
            "duration": duration,
        }

        # Save to database
        audit_service.log_audit_operation("Show recent logs", parameters, results)

        if not logs:
            click.echo("No logs found.")
            return

        click.echo(f"Recent {len(logs)} log entries:")
        click.echo("=" * 60)

        for log in logs:
            status = "✅" if log.get("success", True) else "❌"
            duration_display = (
                f"{log.get('duration_seconds', 0)}s"
                if log.get("duration_seconds")
                else "Unknown"
            )
            git_info = (
                f" [{log.get('git_branch', 'Unknown')}:{log.get('git_commit', 'Unknown')[:8]}]"
                if log.get("git_commit")
                else ""
            )
            triggered_by = log.get("triggered_by", "Unknown")

            click.echo(
                f"{status} {log.get('timestamp')} - {log.get('tool_name')} - {log.get('operation')}"
            )
            click.echo(
                f"   By: {triggered_by} | Source: {log.get('execution_source')} | Duration: {duration_display}{git_info}"
            )
            click.echo()

    except Exception as e:
        operation_end = time.time()
        duration = operation_end - operation_start

        # Log the failed operation
        parameters = {
            "limit": limit,
            "tool_name": tool_name,
            "minutes": minutes,
        }

        results = {
            "success": False,
            "error": str(e),
            "duration": duration,
        }

        try:
            audit_service = AuditService()
            audit_service.log_audit_operation("Show recent logs", parameters, results)
        except Exception:
            pass  # Don't fail if logging fails

        click.echo(f"❌ Error retrieving recent logs: {e}", err=True)
        raise click.ClickException(str(e))


@audit_cli.command()
@click.option(
    "--logs-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default="logs",
    help="Directory containing log files to include in reproduction script",
)
@click.option(
    "--output-file",
    type=str,
    default="reproduce_commands.sh",
    help="Output filename for the reproduction script (will be created in logs directory)",
)
def reproduce(logs_dir, output_file):
    """Generate a bash script to reproduce commands from log files.

    This command reads markdown log files from the specified directory and creates
    a reproduction script. Users curate which commands to include by:

    1. First generating audit reports to create log files:
       rtgs audit report --start-date YYYY-MM-DD --end-date YYYY-MM-DD

    2. Reviewing the log files in the logs directory

    3. Removing any log files they don't want to reproduce

    4. Running this command to generate the reproduction script

    The script will include git checkout commands to ensure the exact same
    code version is used for each command, and shows who triggered each command.
    The output script will be written to the logs directory to avoid making
    the git repository dirty.
    """
    operation_start = time.time()

    try:
        # Ensure output file is placed in logs directory
        output_file_path = logs_dir / output_file

        click.echo(f"Reading log files from: {logs_dir}")
        click.echo(f"Output script will be written to: {output_file_path}")

        # Find all markdown log files in the directory
        log_files = list(logs_dir.glob("*.md"))

        if not log_files:
            click.echo(f"No log files found in {logs_dir}")
            return

        click.echo(f"Found {len(log_files)} log files")

        # Use report service for business logic
        audit_service = AuditService()
        report_service = ReportService()

        # Generate reproduction script using report service
        script_result = report_service.generate_reproduction_script(
            log_files, output_file_path
        )

        operation_end = time.time()
        duration = operation_end - operation_start

        # Initialize parameters for logging
        parameters = {
            "logs_dir": str(logs_dir),
            "output_file": str(output_file_path),
            "log_files_found": len(log_files),
        }

        # Handle dirty commands error
        if not script_result["success"] and "dirty_commands" in script_result:
            dirty_commands = script_result["dirty_commands"]
            click.echo(
                f"❌ Cannot create reproduction script: {len(dirty_commands)} command(s) were executed with uncommitted changes"
            )
            click.echo("")
            click.echo(
                "The following commands cannot be reproduced because the git repository"
            )
            click.echo("contained uncommitted changes when they were executed:")
            click.echo("")

            for dirty in dirty_commands:
                click.echo(f"❌ {dirty['timestamp']} - {dirty['operation']}")
                click.echo(f"   Command: {dirty['command']}")
                click.echo(f"   By: {dirty['triggered_by']}")
                click.echo(f"   Commit: {dirty['git_commit'][:8]}... (DIRTY)")
                click.echo(f"   File: {dirty['filename']}")
                click.echo("")

            click.echo(
                "To create a reproduction script, ensure all commands are executed"
            )
            click.echo(
                "with a clean git repository (no uncommitted changes), or remove"
            )
            click.echo("the problematic log files from the logs directory.")

            # Log this failed attempt
            results = {
                "success": False,
                "error": script_result["error"],
                "dirty_commands_count": len(dirty_commands),
                "clean_commands_count": script_result["clean_commands_count"],
                "duration": duration,
            }
            audit_service.log_audit_operation(
                "Generate reproduction script from files", parameters, results
            )
            return

        if not script_result["success"]:
            click.echo(f"❌ {script_result['error']}")
            results = {
                "success": False,
                "error": script_result["error"],
                "duration": duration,
            }
            audit_service.log_audit_operation(
                "Generate reproduction script from files", parameters, results
            )
            return

        # Update results with script information
        results = script_result.copy()
        results["duration"] = duration

        # Save to database
        audit_service.log_audit_operation(
            "Generate reproduction script from files", parameters, results
        )

        # Create log file in logs directory
        commands = results.get("commands", [])
        log_path = report_service.create_log_file(
            output_dir=logs_dir,
            operation="Generate reproduction script from files",
            parameters=parameters,
            results=results,
            additional_sections={
                "Log Files Processed": "\n".join(
                    f"- {cmd.get('timestamp')}: {cmd.get('command', 'unknown')} (by {cmd.get('triggered_by', 'unknown')})"
                    for cmd in commands[:10]
                )
                + ("\n- ..." if len(commands) > 10 else "")
            },
        )

        click.echo(f"✅ Generated reproduction script: {output_file_path}")
        click.echo(f"   Log files processed: {results['log_files_processed']}")
        click.echo(f"   Unique commits: {results['unique_commits']}")
        click.echo(f"   Script is executable and ready to run")
        click.echo(f"   Audit operation logged: {log_path}")

    except Exception as e:
        operation_end = time.time()
        duration = operation_end - operation_start

        # Log the failed operation
        parameters = {
            "logs_dir": str(logs_dir),
            "output_file": str(logs_dir / output_file),
        }

        results = {
            "success": False,
            "error": str(e),
            "duration": duration,
        }

        try:
            audit_service = AuditService()
            report_service = ReportService()
            audit_service.log_audit_operation(
                "Generate reproduction script from files", parameters, results
            )

            log_path = report_service.create_log_file(
                output_dir=Path("logs"),
                operation="Generate reproduction script from files",
                parameters=parameters,
                results=results,
            )
            click.echo(f"Failed audit operation logged: {log_path}")
        except Exception:
            pass  # Don't fail if logging fails

        click.echo(f"❌ Error generating reproduction script: {e}", err=True)
        raise click.ClickException(str(e))


@audit_cli.command("enable-postgres-logging")
def enable_postgres_logging_cmd():
    """Enable postgres logging globally for all RTGS tools."""
    try:
        enable_postgres_logging()
        click.echo("To enable postgres logging globally, add this to your .env file:")
        click.echo("POSTGRES_LOGGING_STATUS=true")
        click.echo("")
        click.echo("After adding this setting, all RTGS tools will log to postgres when possible")
    except Exception as e:
        click.echo(f"❌ Error enabling postgres logging: {e}", err=True)
        raise click.ClickException(str(e))


@audit_cli.command("disable-postgres-logging")
def disable_postgres_logging_cmd():
    """Disable postgres logging globally for all RTGS tools."""
    try:
        disable_postgres_logging()
        click.echo("To disable postgres logging globally, add this to your .env file:")
        click.echo("POSTGRES_LOGGING_STATUS=false")
        click.echo("")
        click.echo("After adding this setting, RTGS tools will skip postgres logging")
    except Exception as e:
        click.echo(f"❌ Error disabling postgres logging: {e}", err=True)
        raise click.ClickException(str(e))


@audit_cli.command("postgres-logging-status")
def postgres_logging_status_cmd():
    """Show the current postgres logging status."""
    try:
        import os
        status = get_postgres_logging_status()
        env_value = os.getenv("POSTGRES_LOGGING_STATUS", "not set")
        
        status_icon = "✅" if status["enabled"] else "❌"
        click.echo(f"Postgres logging status: {status_icon} {status['status'].upper()}")
        click.echo(f"POSTGRES_LOGGING_STATUS in .env: {env_value}")
        click.echo("")
        
        if status["enabled"]:
            click.echo("All RTGS tools will log to postgres database when possible")
        else:
            click.echo("RTGS tools will skip postgres logging (default)")
            click.echo("To enable postgres logging, add 'POSTGRES_LOGGING_STATUS=true' to your .env file")
            
    except Exception as e:
        click.echo(f"❌ Error checking postgres logging status: {e}", err=True)
        raise click.ClickException(str(e))
