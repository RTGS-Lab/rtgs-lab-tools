"""Report generation service for audit functionality."""

import json
import logging
import os
import platform
import re
import shlex
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.config import Config

logger = logging.getLogger(__name__)


class ReportService:
    """Service class for generating audit reports and reproduction scripts."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize report service."""
        self.config = config or Config()

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
                        results_section += (
                            f"- **{key.replace('_', ' ').title()}**: {value}\n"
                        )

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
        if log.get("command"):
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
        self, logs: List[Dict[str, Any]], output_dir: Path
    ) -> List[str]:
        """Generate audit report with individual markdown files.

        Args:
            logs: List of log dictionaries
            output_dir: Directory to write markdown files

        Returns:
            List of created file paths
        """
        if not logs:
            return []

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        created_files = []

        for log in logs:
            # Create filename
            timestamp = datetime.fromisoformat(log["timestamp"]).strftime(
                "%Y-%m-%d_%H-%M-%S"
            )
            tool = log.get("tool_name", "unknown")
            operation = (
                log.get("operation", "unknown")
                .lower()
                .replace(" ", "_")
                .replace("/", "_")
            )

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
        output_dir: Path,
        operation: str,
        parameters: Dict[str, Any],
        results: Dict[str, Any],
        additional_sections: Optional[Dict[str, str]] = None,
    ) -> str:
        """Create a log file for audit operations.

        Args:
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
                    results_section += (
                        f"- **{key.replace('_', ' ').title()}**: {value}\n"
                    )

        # Additional sections
        additional_content = ""
        if additional_sections:
            for section_title, section_content in additional_sections.items():
                additional_content += f"\n## {section_title}\n{section_content}\n"

        # Get system and git information
        hostname = socket.gethostname()
        platform_info = platform.platform()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        working_directory = os.getcwd()

        # Get git information
        git_branch = "Unknown"
        git_commit = "Unknown"
        git_dirty = False
        git_info_section = ""

        try:
            git_branch = (
                subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )

            git_commit = (
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
                )
                .decode()
                .strip()
            )

            # Check if git is dirty
            git_status = (
                subprocess.check_output(
                    ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL
                )
                .decode()
                .strip()
            )
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

    def parse_log_file(self, content: str, filename: str) -> Optional[Dict[str, Any]]:
        """Parse a markdown log file to extract command information.

        Args:
            content: The markdown content of the log file
            filename: The filename (for debugging)

        Returns:
            Dictionary with command information or None if parsing fails
        """
        try:
            # Extract timestamp from execution context
            timestamp_match = re.search(r"- \*\*Timestamp\*\*: (.+)", content)
            timestamp = timestamp_match.group(1).strip() if timestamp_match else None

            # Extract operation
            operation_match = re.search(r"- \*\*Operation\*\*: (.+)", content)
            operation = operation_match.group(1).strip() if operation_match else None

            # Extract triggered by
            triggered_by_match = re.search(r"- \*\*Triggered By\*\*: (.+)", content)
            triggered_by = (
                triggered_by_match.group(1).strip() if triggered_by_match else None
            )

            # Extract command from the command section
            command_match = re.search(
                r"## Command\s*```bash\s*(.+?)\s*```", content, re.DOTALL
            )
            command = command_match.group(1).strip() if command_match else None

            # Extract git information
            git_branch_match = re.search(r"- \*\*Branch\*\*: (.+)", content)
            git_branch = git_branch_match.group(1).strip() if git_branch_match else None

            git_commit_match = re.search(r"- \*\*Commit\*\*: (.+?)\.\.\.", content)
            git_commit = git_commit_match.group(1).strip() if git_commit_match else None

            # Try to get full commit from environment details
            if not git_commit:
                full_commit_match = re.search(
                    r'"git_commit": "([a-f0-9]{40})"', content
                )
                git_commit = full_commit_match.group(1) if full_commit_match else None

            # Extract git dirty status
            git_dirty = None
            git_dirty_match = re.search(r"- \*\*Status\*\*: (.+)", content)
            if git_dirty_match:
                status_text = git_dirty_match.group(1).strip()
                git_dirty = "Dirty" in status_text or "⚠️" in status_text

            # Try to get git dirty from environment details if not found in git section
            if git_dirty is None:
                dirty_env_match = re.search(r'"git_dirty": (true|false)', content)
                if dirty_env_match:
                    git_dirty = dirty_env_match.group(1) == "true"

            # Only return if we have the essential information
            if command and timestamp:
                return {
                    "timestamp": timestamp,
                    "operation": operation or "Unknown operation",
                    "triggered_by": triggered_by or "Unknown",
                    "command": command,
                    "git_commit": git_commit,
                    "git_branch": git_branch,
                    "git_dirty": git_dirty,
                    "filename": filename,
                }
            else:
                return None

        except Exception as e:
            # Return None if parsing fails
            return None

    def quote_command_for_bash(self, command: str) -> str:
        """Quote a command properly for bash execution.

        Args:
            command: The command string to quote

        Returns:
            Properly quoted command string
        """
        try:
            # Parse the command using shlex to handle existing quotes
            parts = shlex.split(command)

            # Quote each part that needs quoting
            quoted_parts = []
            for part in parts:
                # If the part contains spaces, special characters, or is already quoted, quote it
                if (
                    " " in part
                    or '"' in part
                    or "'" in part
                    or any(
                        c in part
                        for c in ["&", "|", ";", "(", ")", "<", ">", "$", "`", "\\"]
                    )
                ):
                    # Use shlex.quote to properly escape the part
                    quoted_parts.append(shlex.quote(part))
                else:
                    quoted_parts.append(part)

            return " ".join(quoted_parts)
        except ValueError:
            # If shlex.split fails (malformed quotes), fall back to simple quoting
            # Split on spaces but be careful about existing quotes

            # Pattern to match arguments with values that might contain spaces
            # This handles cases like --project "Gems Demo" or --note "Some note with spaces"
            pattern = r"(--[\w-]+)\s+([^-][^\s]*(?:\s+[^-][^\s]*)*)"

            def quote_match(match):
                flag = match.group(1)
                value = match.group(2).strip()

                # If value contains spaces and isn't already quoted, quote it
                if (
                    " " in value
                    and not (value.startswith('"') and value.endswith('"'))
                    and not (value.startswith("'") and value.endswith("'"))
                ):
                    return f'{flag} "{value}"'
                else:
                    return f"{flag} {value}"

            # Apply the quoting pattern
            quoted_command = re.sub(pattern, quote_match, command)
            return quoted_command

    def generate_reproduction_script(
        self, log_files: List[Path], output_file_path: Path
    ) -> Dict[str, Any]:
        """Generate a bash script to reproduce commands from log files.

        Args:
            log_files: List of log file paths to process
            output_file_path: Path for the output script

        Returns:
            Dictionary with operation results
        """
        # Parse each log file to extract command information
        commands = []
        dirty_commands = []

        for log_file in log_files:
            try:
                with open(log_file, "r") as f:
                    content = f.read()

                # Extract command information using simple parsing
                command_info = self.parse_log_file(content, log_file.name)
                if command_info:
                    # Check if git was dirty during this command execution
                    if command_info.get("git_dirty") is True:
                        dirty_commands.append(
                            {
                                "filename": log_file.name,
                                "timestamp": command_info.get("timestamp", "Unknown"),
                                "operation": command_info.get("operation", "Unknown"),
                                "command": command_info.get("command", "Unknown"),
                                "git_commit": command_info.get("git_commit", "Unknown"),
                                "triggered_by": command_info.get(
                                    "triggered_by", "Unknown"
                                ),
                            }
                        )
                    else:
                        commands.append(command_info)

            except Exception as e:
                logger.warning(f"Failed to parse {log_file}: {e}")
                continue

        # If any commands were executed with dirty git state, return error
        if dirty_commands:
            return {
                "success": False,
                "error": f"Cannot reproduce {len(dirty_commands)} commands executed with dirty git state",
                "dirty_commands": dirty_commands,
                "clean_commands_count": len(commands),
            }

        if not commands:
            return {
                "success": False,
                "error": "No valid commands found in log files",
                "commands_processed": 0,
            }

        # Sort commands by timestamp
        commands.sort(key=lambda x: x.get("timestamp", ""))

        # Group commands by git commit to create checkout sections
        commits = {}
        for cmd in commands:
            commit = cmd.get("git_commit")
            if commit:
                if commit not in commits:
                    commits[commit] = {
                        "branch": cmd.get("git_branch"),
                        "commands": [],
                        "timestamp": cmd.get("timestamp"),
                    }
                commits[commit]["commands"].append(cmd)

        # Generate script content
        script_content = f"""#!/bin/bash
# Reproduction script generated by RTGS Lab Tools audit
# Generated on: {datetime.now().isoformat()}
# Source: Log files
# Total commands: {len(commands)}

set -e  # Exit on any error

echo "🚀 Starting reproduction of RTGS Lab Tools commands"
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
                for cmd in commit_info["commands"]:
                    command = cmd.get("command", "unknown")
                    quoted_command = self.quote_command_for_bash(command)
                    timestamp = cmd.get("timestamp", "unknown")
                    operation = cmd.get("operation", "unknown")
                    triggered_by = cmd.get("triggered_by", "unknown")

                    script_content += f"""# {timestamp} - {operation} (by {triggered_by})
echo "⚡ Running: {command}"
{quoted_command}
echo ""

"""
        else:
            # Fallback for commands without git info
            script_content += "# Commands without git information\n"
            for cmd in commands:
                command = cmd.get("command", "unknown")
                quoted_command = self.quote_command_for_bash(command)
                timestamp = cmd.get("timestamp", "unknown")
                operation = cmd.get("operation", "unknown")
                triggered_by = cmd.get("triggered_by", "unknown")

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

        return {
            "success": True,
            "log_files_processed": len(commands),
            "log_files_found": len(log_files),
            "output_file": str(output_file_path),
            "script_content_lines": len(script_content.split("\n")),
            "unique_commits": len(commits),
            "commands": commands,
        }
