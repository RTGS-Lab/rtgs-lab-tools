"""CLI for audit functionality."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import click
from sqlalchemy import and_

from ..core.config import Config
from ..core.postgres_logger import PostgresLogger, ToolCallLog
from ..core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class AuditReporter:
    """Generate audit reports from database logs."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize audit reporter."""
        self.config = config or Config()
        self.logger = PostgresLogger("audit", self.config)
    
    def get_logs_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        tool_name: Optional[str] = None
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
                        ToolCallLog.timestamp <= end_date
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
                        "parameters": json.loads(log.parameters) if log.parameters else {},
                        "results": json.loads(log.results) if log.results else {},
                        "environment_variables": json.loads(log.environment_variables) if log.environment_variables else {},
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
    
    def format_log_as_markdown(self, log: Dict[str, Any]) -> str:
        """Format a single log entry as markdown.
        
        Args:
            log: Log dictionary
            
        Returns:
            Formatted markdown string
        """
        # Calculate duration display
        duration = "Unknown"
        if log.get("duration_seconds"):
            seconds = log["duration_seconds"]
            if seconds < 60:
                duration = f"{seconds}s"
            elif seconds < 3600:
                duration = f"{seconds/60:.1f}m"
            else:
                duration = f"{seconds/3600:.1f}h"
        
        # Git information
        git_info = ""
        if log.get("git_commit"):
            git_status = "✅ Clean" if not log.get("git_dirty") else "⚠️ Dirty"
            git_info = f"""
## Git Information
- **Branch**: {log.get('git_branch', 'Unknown')}
- **Commit**: {log.get('git_commit', 'Unknown')[:8]}{'...' if log.get('git_commit') else ''}
- **Status**: {git_status}
"""
        
        # Parameters section
        parameters_section = ""
        if log.get("parameters"):
            parameters_section = "\n## Parameters\n"
            for key, value in log["parameters"].items():
                if isinstance(value, (dict, list)):
                    parameters_section += f"- **{key}**: `{json.dumps(value)}`\n"
                else:
                    parameters_section += f"- **{key}**: {value}\n"
        
        # Results section
        results_section = ""
        if log.get("results"):
            results_section = f"""
## Results Summary
- **Status**: {'✅ Success' if log.get('success', True) else '❌ Failed'}
- **Duration**: {duration}
"""
            for key, value in log["results"].items():
                if key not in ["success", "start_time", "end_time", "duration"]:
                    if isinstance(value, (dict, list)):
                        results_section += f"- **{key.replace('_', ' ').title()}**: `{json.dumps(value)}`\n"
                    else:
                        results_section += f"- **{key.replace('_', ' ').title()}**: {value}\n"
        
        # Environment details
        env_details = {
            "timestamp": log.get("timestamp"),
            "tool_name": log.get("tool_name"),
            "execution_source": log.get("execution_source"),
            "triggered_by": log.get("triggered_by"),
            "hostname": log.get("hostname"),
            "platform": log.get("platform"),
            "python_version": log.get("python_version"),
            "working_directory": log.get("working_directory"),
            "script_path": log.get("script_path"),
            "environment_variables": log.get("environment_variables", {}),
            "git_commit": log.get("git_commit"),
            "git_branch": log.get("git_branch"),
            "git_dirty": log.get("git_dirty"),
        }
        
        # Command section
        command_section = ""
        if log.get('command'):
            command_section = f"""
## Command
```bash
{log.get('command')}
```
"""

        markdown = f"""# {log.get('tool_name', 'Unknown').title()} Execution Log

## Execution Context
- **Timestamp**: {log.get('timestamp')}
- **Operation**: {log.get('operation')}
- **Execution Source**: {log.get('execution_source')}
- **Triggered By**: {log.get('triggered_by')}
- **Hostname**: {log.get('hostname')}
- **Platform**: {log.get('platform')}
- **Working Directory**: {log.get('working_directory')}
{git_info}
{command_section}
{parameters_section}
{results_section}

## Detailed Results
<details>
<summary>Full Results JSON</summary>

```json
{json.dumps(log.get('results', {}), indent=2)}
```
</details>

## Execution Environment
<details>
<summary>Environment Details</summary>

```json
{json.dumps(env_details, indent=2)}
```
</details>

---
*Log generated automatically by RTGS Lab Tools - {log.get('tool_name', 'Unknown')}*
"""
        return markdown
    
    def generate_audit_report(
        self,
        start_date: datetime,
        end_date: datetime,
        output_dir: Path,
        tool_name: Optional[str] = None
    ) -> List[str]:
        """Generate audit report with individual markdown files.
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range
            output_dir: Directory to write markdown files
            tool_name: Optional tool name filter
            
        Returns:
            List of created file paths
        """
        logs = self.get_logs_by_date_range(start_date, end_date, tool_name)
        
        if not logs:
            click.echo("No logs found for the specified date range.")
            return []
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        created_files = []
        
        for log in logs:
            # Create filename
            timestamp = datetime.fromisoformat(log["timestamp"]).strftime("%Y-%m-%d_%H-%M-%S")
            tool = log.get("tool_name", "unknown")
            operation = log.get("operation", "unknown").lower().replace(" ", "_").replace("/", "_")
            
            # Limit filename length
            if len(operation) > 50:
                operation = operation[:47] + "..."
            
            filename = f"{timestamp}_{tool}_{operation}.md"
            filepath = output_dir / filename
            
            # Generate markdown content
            markdown_content = self.format_log_as_markdown(log)
            
            # Write file
            with open(filepath, "w") as f:
                f.write(markdown_content)
            
            created_files.append(str(filepath))
        
        return created_files

    def create_log_file(
        self,
        log: Dict[str, Any],
        output_dir: Path,
        operation: str,
        parameters: Dict[str, Any],
        results: Dict[str, Any],
        additional_sections: Optional[Dict[str, str]] = None,
    ) -> str:
        """Create a log file for audit operations.
        
        Args:
            log: Log dictionary (unused, kept for compatibility)
            output_dir: Directory to write the log file
            operation: Description of the operation
            parameters: Parameters used
            results: Results of the operation
            additional_sections: Additional markdown sections
            
        Returns:
            Path to created log file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Create safe filename from operation
        safe_operation = operation.lower().replace(" ", "_").replace("/", "_")
        if len(safe_operation) > 50:
            safe_operation = safe_operation[:47] + "..."
        
        log_filename = f"{timestamp}_audit_{safe_operation}.md"
        log_path = output_dir / log_filename
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate duration
        duration = "Unknown"
        if results.get("duration"):
            seconds = results["duration"]
            if seconds < 60:
                duration = f"{seconds:.1f}s"
            elif seconds < 3600:
                duration = f"{seconds/60:.1f}m"
            else:
                duration = f"{seconds/3600:.1f}h"
        
        # Parameters section
        parameters_section = ""
        if parameters:
            parameters_section = "\n## Parameters\n"
            for key, value in parameters.items():
                if isinstance(value, (dict, list)):
                    parameters_section += f"- **{key}**: `{json.dumps(value)}`\n"
                else:
                    parameters_section += f"- **{key}**: {value}\n"
        
        # Results section
        results_section = f"""
## Results Summary
- **Status**: {'✅ Success' if results.get('success', True) else '❌ Failed'}
- **Duration**: {duration}
"""
        for key, value in results.items():
            if key not in ["success", "start_time", "end_time", "duration"]:
                if isinstance(value, (dict, list)):
                    results_section += f"- **{key.replace('_', ' ').title()}**: `{json.dumps(value)}`\n"
                else:
                    results_section += f"- **{key.replace('_', ' ').title()}**: {value}\n"
        
        # Additional sections
        additional_content = ""
        if additional_sections:
            for section_title, section_content in additional_sections.items():
                additional_content += f"\n## {section_title}\n{section_content}\n"
        
        # Get system and git information
        import platform
        import socket
        import os
        import subprocess
        import sys
        
        hostname = socket.gethostname()
        platform_info = platform.platform()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.patch}"
        working_directory = os.getcwd()
        
        # Get git information
        git_branch = "Unknown"
        git_commit = "Unknown"
        git_dirty = False
        git_info_section = ""
        
        try:
            git_branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                stderr=subprocess.DEVNULL
            ).decode().strip()
            
            git_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], 
                stderr=subprocess.DEVNULL
            ).decode().strip()
            
            # Check if git is dirty
            git_status = subprocess.check_output(
                ["git", "status", "--porcelain"], 
                stderr=subprocess.DEVNULL
            ).decode().strip()
            git_dirty = bool(git_status)
            
            git_status_display = "✅ Clean" if not git_dirty else "⚠️ Dirty"
            git_info_section = f"""
## Git Information
- **Branch**: {git_branch}
- **Commit**: {git_commit[:8]}...
- **Status**: {git_status_display}
"""
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Get execution source and triggered by info
        execution_source = "CLI"
        triggered_by = "Unknown"
        
        # Check for MCP environment variables
        if os.getenv("MCP_SESSION") == "true":
            execution_source = "LLM/MCP"
            mcp_user = os.getenv("MCP_USER", "unknown")
            triggered_by = f"{mcp_user} via {os.getenv('USER', 'unknown')}@{hostname}"
        else:
            triggered_by = f"{os.getenv('USER', 'unknown')}@{hostname}"

        # Create log content
        log_content = f"""# Audit Tool Execution Log

## Execution Context
- **Timestamp**: {datetime.now().isoformat()}
- **Operation**: {operation}
- **Execution Source**: {execution_source}
- **Triggered By**: {triggered_by}
- **Hostname**: {hostname}
- **Platform**: {platform_info}
- **Working Directory**: {working_directory}
{git_info_section}
{parameters_section}
{results_section}
{additional_content}
## Detailed Results
<details>
<summary>Full Results JSON</summary>

```json
{json.dumps(results, indent=2)}
```
</details>

## Execution Environment
<details>
<summary>Environment Details</summary>

```json
{json.dumps({
    "timestamp": datetime.now().isoformat(),
    "tool_name": "audit",
    "execution_source": execution_source,
    "triggered_by": triggered_by,
    "hostname": hostname,
    "platform": platform_info,
    "python_version": python_version,
    "working_directory": working_directory,
    "script_path": __file__,
    "environment_variables": {
        "CI": os.getenv("CI", "false"),
        "GITHUB_ACTIONS": os.getenv("GITHUB_ACTIONS", "false"),
        "GITHUB_ACTOR": os.getenv("GITHUB_ACTOR"),
        "GITHUB_WORKFLOW": os.getenv("GITHUB_WORKFLOW"),
        "GITHUB_RUN_ID": os.getenv("GITHUB_RUN_ID"),
        "MCP_SESSION": os.getenv("MCP_SESSION", "false"),
        "MCP_USER": os.getenv("MCP_USER")
    },
    "git_commit": git_commit,
    "git_branch": git_branch,
    "git_dirty": git_dirty
}, indent=2)}
```
</details>

---
*Log generated automatically by RTGS Lab Tools - audit*
"""
        
        # Write log file
        with open(log_path, "w") as f:
            f.write(log_content)
        
        logger.info(f"Created audit log: {log_path}")
        return str(log_path)


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
        
        reporter = AuditReporter()
        created_files = reporter.generate_audit_report(
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            tool_name=tool_name
        )
        
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
        audit_logger = PostgresLogger("audit", reporter.config)
        audit_logger.log_execution(
            operation="Generate audit report",
            parameters=parameters,
            results=results,
            script_path=__file__,
        )
        
        # Create log file
        log_path = reporter.create_log_file(
            log={},  # Not used
            output_dir=output_dir,
            operation="Generate audit report",
            parameters=parameters,
            results=results,
            additional_sections={
                "Generated Files": "\n".join(f"- {f}" for f in created_files) if created_files else "No files generated"
            }
        )
        
        if created_files:
            click.echo(f"✅ Generated {len(created_files)} audit report files in {output_dir}")
            for file_path in created_files:
                click.echo(f"   - {file_path}")
            click.echo(f"📋 Audit operation logged: {log_path}")
        else:
            click.echo("No logs found for the specified criteria.")
            click.echo(f"📋 Audit operation logged: {log_path}")
            
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
            reporter = AuditReporter()
            audit_logger = PostgresLogger("audit", reporter.config)
            audit_logger.log_execution(
                operation="Generate audit report",
                parameters=parameters,
                results=results,
                script_path=__file__,
            )
            
            log_path = reporter.create_log_file(
                log={},
                output_dir=output_dir,
                operation="Generate audit report", 
                parameters=parameters,
                results=results,
            )
            click.echo(f"📋 Failed audit operation logged: {log_path}")
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
def recent(limit, tool_name):
    """Show recent log entries."""
    operation_start = time.time()
    
    try:
        reporter = AuditReporter()
        
        # Get all logs and filter by tool if specified
        # For simplicity, we'll use a large date range
        end_date = datetime.now()
        start_date = datetime(2020, 1, 1)  # Far back start date
        
        logs = reporter.get_logs_by_date_range(start_date, end_date, tool_name)
        
        operation_end = time.time()
        duration = operation_end - operation_start
        
        # Log this audit operation
        parameters = {
            "limit": limit,
            "tool_name": tool_name,
        }
        
        results = {
            "success": True,
            "logs_found": len(logs),
            "logs_displayed": min(len(logs), limit),
            "duration": duration,
        }
        
        # Save to database
        audit_logger = PostgresLogger("audit", reporter.config)
        audit_logger.log_execution(
            operation="Show recent logs",
            parameters=parameters,
            results=results,
            script_path=__file__,
        )
        
        if not logs:
            click.echo("No logs found.")
            return
        
        # Take only the requested number
        recent_logs = logs[:limit]
        
        click.echo(f"Recent {len(recent_logs)} log entries:")
        click.echo("=" * 60)
        
        for log in recent_logs:
            status = "✅" if log.get("success", True) else "❌"
            duration_display = f"{log.get('duration_seconds', 0)}s" if log.get("duration_seconds") else "Unknown"
            git_info = f" [{log.get('git_branch', 'Unknown')}:{log.get('git_commit', 'Unknown')[:8]}]" if log.get('git_commit') else ""
            triggered_by = log.get('triggered_by', 'Unknown')
            
            click.echo(f"{status} {log.get('timestamp')} - {log.get('tool_name')} - {log.get('operation')}")
            click.echo(f"   By: {triggered_by} | Source: {log.get('execution_source')} | Duration: {duration_display}{git_info}")
            click.echo()
            
    except Exception as e:
        operation_end = time.time()
        duration = operation_end - operation_start
        
        # Log the failed operation
        parameters = {
            "limit": limit,
            "tool_name": tool_name,
        }
        
        results = {
            "success": False,
            "error": str(e),
            "duration": duration,
        }
        
        try:
            reporter = AuditReporter()
            audit_logger = PostgresLogger("audit", reporter.config)
            audit_logger.log_execution(
                operation="Show recent logs",
                parameters=parameters,
                results=results,
                script_path=__file__,
            )
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
        
        # Initialize parameters for logging
        parameters = {
            "logs_dir": str(logs_dir),
            "output_file": str(output_file_path),
            "log_files_found": len(log_files),
        }
        
        operation_end = time.time()
        duration = operation_end - operation_start
        
        # Parse each log file to extract command information
        commands = []
        dirty_commands = []
        
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                
                # Extract command information using simple parsing
                command_info = parse_log_file(content, log_file.name)
                if command_info:
                    # Check if git was dirty during this command execution
                    if command_info.get('git_dirty') is True:
                        dirty_commands.append({
                            'filename': log_file.name,
                            'timestamp': command_info.get('timestamp', 'Unknown'),
                            'operation': command_info.get('operation', 'Unknown'),
                            'command': command_info.get('command', 'Unknown'),
                            'git_commit': command_info.get('git_commit', 'Unknown'),
                            'triggered_by': command_info.get('triggered_by', 'Unknown')
                        })
                    else:
                        commands.append(command_info)
                    
            except Exception as e:
                click.echo(f"Warning: Failed to parse {log_file}: {e}")
                continue
        
        # If any commands were executed with dirty git state, fail with detailed error
        if dirty_commands:
            click.echo(f"❌ Cannot create reproduction script: {len(dirty_commands)} command(s) were executed with uncommitted changes")
            click.echo("")
            click.echo("The following commands cannot be reproduced because the git repository")
            click.echo("contained uncommitted changes when they were executed:")
            click.echo("")
            
            for dirty in dirty_commands:
                click.echo(f"🔴 {dirty['timestamp']} - {dirty['operation']}")
                click.echo(f"   Command: {dirty['command']}")
                click.echo(f"   By: {dirty['triggered_by']}")
                click.echo(f"   Commit: {dirty['git_commit'][:8]}... (DIRTY)")
                click.echo(f"   File: {dirty['filename']}")
                click.echo("")
            
            click.echo("To create a reproduction script, ensure all commands are executed")
            click.echo("with a clean git repository (no uncommitted changes), or remove")
            click.echo("the problematic log files from the logs directory.")
            
            # Still log this failed attempt
            reporter = AuditReporter()
            audit_logger = PostgresLogger("audit", reporter.config)
            audit_logger.log_execution(
                operation="Generate reproduction script from files",
                parameters=parameters,
                results={
                    "success": False,
                    "error": f"Cannot reproduce {len(dirty_commands)} commands executed with dirty git state",
                    "dirty_commands_count": len(dirty_commands),
                    "clean_commands_count": len(commands),
                    "duration": duration,
                },
                script_path=__file__,
            )
            
            return
        
        operation_end = time.time()
        duration = operation_end - operation_start
        
        results = {
            "success": True,
            "log_files_processed": len(commands),
            "log_files_found": len(log_files),
            "output_file": str(output_file_path),
            "duration": duration,
        }
        
        if not commands:
            click.echo("No valid commands found in log files.")
            # Still log the operation
            reporter = AuditReporter()
            audit_logger = PostgresLogger("audit", reporter.config)
            audit_logger.log_execution(
                operation="Generate reproduction script from files",
                parameters=parameters,
                results=results,
                script_path=__file__,
            )
            return
        
        # Sort commands by timestamp
        commands.sort(key=lambda x: x.get('timestamp', ''))
        
        # Group commands by git commit to create checkout sections
        commits = {}
        for cmd in commands:
            commit = cmd.get('git_commit')
            if commit:
                if commit not in commits:
                    commits[commit] = {
                        'branch': cmd.get('git_branch'),
                        'commands': [],
                        'timestamp': cmd.get('timestamp')
                    }
                commits[commit]['commands'].append(cmd)
        
        # Generate script content
        script_content = f"""#!/bin/bash
# Reproduction script generated by RTGS Lab Tools audit
# Generated on: {datetime.now().isoformat()}
# Source: Log files from {logs_dir}
# Total commands: {len(commands)}

set -e  # Exit on any error

echo "🚀 Starting reproduction of RTGS Lab Tools commands"
echo "Source: Log files from {logs_dir}"
echo "Total commands: {len(commands)}"
echo ""

# Store original branch
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "📍 Current branch: $ORIGINAL_BRANCH"
echo ""

"""
        
        # Add commands grouped by commit
        if commits:
            for commit, commit_info in commits.items():
                script_content += f"""# === Commands from commit {commit[:8]}... ({commit_info['branch']}) ===
echo "🔀 Checking out commit {commit[:8]}... (branch: {commit_info['branch']})"
git checkout {commit}
echo ""

"""
                for cmd in commit_info['commands']:
                    command = cmd.get('command', 'unknown')
                    quoted_command = quote_command_for_bash(command)
                    timestamp = cmd.get('timestamp', 'unknown')
                    operation = cmd.get('operation', 'unknown')
                    triggered_by = cmd.get('triggered_by', 'unknown')
                    
                    script_content += f"""# {timestamp} - {operation} (by {triggered_by})
echo "⚡ Running: {command}"
{quoted_command}
echo ""

"""
        else:
            # Fallback for commands without git info
            script_content += "# Commands without git information\n"
            for cmd in commands:
                command = cmd.get('command', 'unknown')
                quoted_command = quote_command_for_bash(command)
                timestamp = cmd.get('timestamp', 'unknown')
                operation = cmd.get('operation', 'unknown')
                triggered_by = cmd.get('triggered_by', 'unknown')
                
                script_content += f"""# {timestamp} - {operation} (by {triggered_by})
echo "⚡ Running: {command}"
{quoted_command}
echo ""

"""
        
        script_content += f"""# === Restoration ===
echo "🔄 Returning to original branch: $ORIGINAL_BRANCH"
git checkout $ORIGINAL_BRANCH
echo ""
echo "✅ Reproduction script completed successfully!"
"""
        
        # Write script file
        with open(output_file_path, "w") as f:
            f.write(script_content)
        
        # Make script executable
        output_file_path.chmod(0o755)
        
        results["script_content_lines"] = len(script_content.split('\n'))
        results["unique_commits"] = len(commits)
        
        # Save to database
        reporter = AuditReporter()
        audit_logger = PostgresLogger("audit", reporter.config)
        audit_logger.log_execution(
            operation="Generate reproduction script from files",
            parameters=parameters,
            results=results,
            script_path=__file__,
        )
        
        # Create log file in logs directory
        log_path = reporter.create_log_file(
            log={},
            output_dir=logs_dir,
            operation="Generate reproduction script from files",
            parameters=parameters,
            results=results,
            additional_sections={
                "Script Content Preview": f"```bash\n{script_content[:500]}...\n```" if len(script_content) > 500 else f"```bash\n{script_content}\n```",
                "Log Files Processed": "\n".join(f"- {cmd.get('timestamp')}: {cmd.get('command', 'unknown')} (by {cmd.get('triggered_by', 'unknown')})" for cmd in commands[:10]) + ("\n- ..." if len(commands) > 10 else "")
            }
        )
        
        click.echo(f"✅ Generated reproduction script: {output_file_path}")
        click.echo(f"   Log files processed: {len(commands)}")
        click.echo(f"   Unique commits: {len(commits)}")
        click.echo(f"   Script is executable and ready to run")
        click.echo(f"📋 Audit operation logged: {log_path}")
        
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
            reporter = AuditReporter()
            audit_logger = PostgresLogger("audit", reporter.config)
            audit_logger.log_execution(
                operation="Generate reproduction script from files",
                parameters=parameters,
                results=results,
                script_path=__file__,
            )
            
            log_path = reporter.create_log_file(
                log={},
                output_dir=Path("logs"),
                operation="Generate reproduction script from files",
                parameters=parameters,
                results=results,
            )
            click.echo(f"📋 Failed audit operation logged: {log_path}")
        except Exception:
            pass  # Don't fail if logging fails
        
        click.echo(f"❌ Error generating reproduction script: {e}", err=True)
        raise click.ClickException(str(e))


def quote_command_for_bash(command: str) -> str:
    """Quote a command properly for bash execution.
    
    Args:
        command: The command string to quote
        
    Returns:
        Properly quoted command string
    """
    import shlex
    import re
    
    # Split the command into parts while preserving quotes
    try:
        # Parse the command using shlex to handle existing quotes
        parts = shlex.split(command)
        
        # Quote each part that needs quoting
        quoted_parts = []
        for part in parts:
            # If the part contains spaces, special characters, or is already quoted, quote it
            if ' ' in part or '"' in part or "'" in part or any(c in part for c in ['&', '|', ';', '(', ')', '<', '>', '$', '`', '\\']):
                # Use shlex.quote to properly escape the part
                quoted_parts.append(shlex.quote(part))
            else:
                quoted_parts.append(part)
        
        return ' '.join(quoted_parts)
    except ValueError:
        # If shlex.split fails (malformed quotes), fall back to simple quoting
        # Split on spaces but be careful about existing quotes
        import re
        
        # Pattern to match arguments with values that might contain spaces
        # This handles cases like --project "Gems Demo" or --note "Some note with spaces"
        pattern = r'(--[\w-]+)\s+([^-][^\s]*(?:\s+[^-][^\s]*)*)'
        
        def quote_match(match):
            flag = match.group(1)
            value = match.group(2).strip()
            
            # If value contains spaces and isn't already quoted, quote it
            if ' ' in value and not (value.startswith('"') and value.endswith('"')) and not (value.startswith("'") and value.endswith("'")):
                return f'{flag} "{value}"'
            else:
                return f'{flag} {value}'
        
        # Apply the quoting pattern
        quoted_command = re.sub(pattern, quote_match, command)
        return quoted_command


def parse_log_file(content: str, filename: str) -> Optional[Dict[str, Any]]:
    """Parse a markdown log file to extract command information.
    
    Args:
        content: The markdown content of the log file
        filename: The filename (for debugging)
    
    Returns:
        Dictionary with command information or None if parsing fails
    """
    import re
    
    try:
        # Extract timestamp from execution context
        timestamp_match = re.search(r'- \*\*Timestamp\*\*: (.+)', content)
        timestamp = timestamp_match.group(1).strip() if timestamp_match else None
        
        # Extract operation
        operation_match = re.search(r'- \*\*Operation\*\*: (.+)', content)
        operation = operation_match.group(1).strip() if operation_match else None
        
        # Extract triggered by
        triggered_by_match = re.search(r'- \*\*Triggered By\*\*: (.+)', content)
        triggered_by = triggered_by_match.group(1).strip() if triggered_by_match else None
        
        # Extract command from the command section
        command_match = re.search(r'## Command\s*```bash\s*(.+?)\s*```', content, re.DOTALL)
        command = command_match.group(1).strip() if command_match else None
        
        # Extract git information
        git_branch_match = re.search(r'- \*\*Branch\*\*: (.+)', content)
        git_branch = git_branch_match.group(1).strip() if git_branch_match else None
        
        git_commit_match = re.search(r'- \*\*Commit\*\*: (.+?)\.\.\.', content)
        git_commit = git_commit_match.group(1).strip() if git_commit_match else None
        
        # Try to get full commit from environment details
        if not git_commit:
            full_commit_match = re.search(r'"git_commit": "([a-f0-9]{40})"', content)
            git_commit = full_commit_match.group(1) if full_commit_match else None
        
        # Extract git dirty status
        git_dirty = None
        git_dirty_match = re.search(r'- \*\*Status\*\*: (.+)', content)
        if git_dirty_match:
            status_text = git_dirty_match.group(1).strip()
            git_dirty = "Dirty" in status_text or "⚠️" in status_text
        
        # Try to get git dirty from environment details if not found in git section
        if git_dirty is None:
            dirty_env_match = re.search(r'"git_dirty": (true|false)', content)
            if dirty_env_match:
                git_dirty = dirty_env_match.group(1) == 'true'
        
        # Only return if we have the essential information
        if command and timestamp:
            return {
                'timestamp': timestamp,
                'operation': operation or 'Unknown operation',
                'triggered_by': triggered_by or 'Unknown',
                'command': command,
                'git_commit': git_commit,
                'git_branch': git_branch,
                'git_dirty': git_dirty,
                'filename': filename
            }
        else:
            return None
            
    except Exception as e:
        # Return None if parsing fails
        return None