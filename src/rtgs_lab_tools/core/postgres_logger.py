"""PostgreSQL logging and audit trail functionality for RTGS Lab Tools."""

import getpass
import json
import logging
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import Config
from .database import DatabaseManager
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)

Base = declarative_base()


class ToolCallLog(Base):
    """SQLAlchemy model for tool call logs."""

    __tablename__ = "tool_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    tool_name = Column(String(100), nullable=False)
    operation = Column(String(255), nullable=False)
    execution_source = Column(String(50), nullable=False)
    triggered_by = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=False)
    platform = Column(String(255), nullable=False)
    python_version = Column(String(50), nullable=False)
    working_directory = Column(Text, nullable=False)
    script_path = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    duration_seconds = Column(Integer, nullable=True)
    parameters = Column(Text, nullable=True)  # JSON string
    results = Column(Text, nullable=True)  # JSON string
    environment_variables = Column(Text, nullable=True)  # JSON string
    note = Column(Text, nullable=True)
    log_file_path = Column(Text, nullable=True)
    git_commit = Column(String(40), nullable=True)
    git_branch = Column(String(255), nullable=True)
    git_dirty = Column(Boolean, nullable=True)
    command = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PostgresLogger:
    """Handle PostgreSQL logging for tool executions with audit trails."""

    def __init__(self, tool_name: str, config: Optional[Config] = None):
        """Initialize PostgresLogger for a specific tool.

        Args:
            tool_name: Name of the tool (e.g., 'data-extraction', 'visualization', 'device-config')
            config: Optional configuration instance
        """
        self.tool_name = tool_name
        self.config = config or Config()
        # Use GCP authentication if LOGGING_INSTANCE_CONNECTION_NAME is set
        use_gcp = bool(self.config.logging_instance_connection_name)
        self.db_manager = DatabaseManager(config=self.config, use_gcp=use_gcp)
        self._Session = None
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

    @property
    def engine(self):
        """Get or create database engine."""
        return self.db_manager.engine

    @property
    def Session(self):
        """Get or create database session factory."""
        if self._Session is None:
            self._Session = sessionmaker(bind=self.engine)
        return self._Session

    def get_git_info(self) -> Dict[str, Any]:
        """Get git repository information.

        Returns:
            Dictionary with git commit, branch, and dirty status
        """
        git_info = {"commit": None, "branch": None, "dirty": None}

        try:
            # Get current commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent.parent,
                timeout=5,
            )
            if result.returncode == 0:
                git_info["commit"] = result.stdout.strip()

            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent.parent,
                timeout=5,
            )
            if result.returncode == 0:
                git_info["branch"] = result.stdout.strip()

            # Check if repository is dirty
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent.parent,
                timeout=5,
            )
            if result.returncode == 0:
                git_info["dirty"] = bool(result.stdout.strip())

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            logger.debug(f"Failed to get git information: {e}")

        return git_info

    def get_command_info(self) -> str:
        """Get the current command that was executed.

        Returns:
            The command string that was used to run this tool
        """
        try:
            # Get the command line arguments
            args = sys.argv.copy()

            # If the first argument is a full path to python script, just use the script name
            if args and args[0].endswith(".py"):
                args[0] = Path(args[0]).stem

            # For rtgs commands, reconstruct the proper format
            if len(args) >= 2 and args[0] in ["rtgs", "python", "python3"]:
                if args[0] in ["python", "python3"] and len(args) >= 3:
                    # python -m rtgs_lab_tools.cli -> rtgs
                    if "-m" in args and "rtgs_lab_tools" in " ".join(args):
                        # Find the index after -m rtgs_lab_tools.cli
                        try:
                            m_index = args.index("-m")
                            if (
                                m_index + 1 < len(args)
                                and "rtgs_lab_tools" in args[m_index + 1]
                            ):
                                return "rtgs " + " ".join(args[m_index + 2 :])
                        except ValueError:
                            pass

                # Direct rtgs command
                if args[0] == "rtgs":
                    return " ".join(args)

            # For MCP or other contexts, try to reconstruct rtgs command
            # Look for tool patterns in the arguments
            for i, arg in enumerate(args):
                if arg in [
                    "sensing-data",
                    "data-parser",
                    "visualization",
                    "gridded-data",
                    "device-configuration",
                    "error-analysis",
                    "agricultural-modeling",
                    "audit",
                ]:
                    return "rtgs " + " ".join(args[i:])

            # Fallback - return the raw command
            return " ".join(args)

        except Exception as e:
            logger.debug(f"Failed to get command info: {e}")
            return "unknown"

    def ensure_table_exists(self):
        """Ensure the tool_call_logs table exists."""
        try:
            Base.metadata.create_all(self.engine)
            logger.debug("Tool call logs table ensured to exist")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create tool call logs table: {e}")
            raise DatabaseError(f"Failed to create logs table: {e}")

    def get_execution_context(
        self, script_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get context information about the current execution.

        Args:
            script_path: Path to the script being executed

        Returns:
            Dictionary with execution context information
        """
        git_info = self.get_git_info()
        command = self.get_command_info()

        context = {
            "timestamp": datetime.now().isoformat(),
            "user": getpass.getuser(),
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "working_directory": os.getcwd(),
            "script_path": script_path or "unknown",
            "tool_name": self.tool_name,
            "command": command,
            "git_commit": git_info["commit"],
            "git_branch": git_info["branch"],
            "git_dirty": git_info["dirty"],
            "environment_variables": {
                "CI": os.environ.get("CI", "false"),
                "GITHUB_ACTIONS": os.environ.get("GITHUB_ACTIONS", "false"),
                "GITHUB_ACTOR": os.environ.get("GITHUB_ACTOR"),
                "GITHUB_WORKFLOW": os.environ.get("GITHUB_WORKFLOW"),
                "GITHUB_RUN_ID": os.environ.get("GITHUB_RUN_ID"),
                "MCP_SESSION": os.environ.get("MCP_SESSION", "false"),
                "MCP_USER": os.environ.get("MCP_USER"),
            },
        }

        # Determine execution source
        if context["environment_variables"]["GITHUB_ACTIONS"] == "true":
            context["execution_source"] = "GitHub Actions"
            context["triggered_by"] = context["environment_variables"]["GITHUB_ACTOR"]
        elif context["environment_variables"]["MCP_SESSION"] == "true":
            mcp_user = context["environment_variables"]["MCP_USER"] or "claude"
            context["execution_source"] = "LLM/MCP"
            context["triggered_by"] = (
                f"{mcp_user} via {context['user']}@{context['hostname']}"
            )
        else:
            context["execution_source"] = "Manual/Local"
            context["triggered_by"] = f"{context['user']}@{context['hostname']}"

        return context

    def create_execution_log(
        self,
        operation: str,
        parameters: Dict[str, Any],
        results: Dict[str, Any],
        script_path: Optional[str] = None,
        additional_sections: Optional[Dict[str, str]] = None,
    ) -> str:
        """Create a detailed execution log file.

        Args:
            operation: Description of the operation performed
            parameters: Parameters used for the operation
            results: Results of the operation
            script_path: Path to the script that was executed
            additional_sections: Additional markdown sections to include

        Returns:
            Path to the created log file
        """
        context = self.get_execution_context(script_path)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Create safe filename from operation with length limits
        safe_operation = operation.lower().replace(" ", "_").replace("/", "_")

        # Limit operation length to prevent filesystem issues (max 100 chars for operation part)
        if len(safe_operation) > 100:
            safe_operation = safe_operation[:97] + "..."

        log_filename = f"{timestamp}_{context['execution_source'].lower().replace('/', '_')}_{safe_operation}.md"

        # Final safety check - most filesystems have 255 char limit
        if len(log_filename) > 250:
            # Truncate the operation part further if needed
            max_operation_len = 250 - len(
                f"{timestamp}_{context['execution_source'].lower().replace('/', '_')}_.md"
            )
            if max_operation_len > 0:
                safe_operation = safe_operation[: max_operation_len - 3] + "..."
                log_filename = f"{timestamp}_{context['execution_source'].lower().replace('/', '_')}_{safe_operation}.md"
            else:
                # Fallback to just timestamp if other parts are too long
                log_filename = f"{timestamp}_log.md"
        log_path = self.logs_dir / log_filename

        # Calculate duration if available
        duration = self._calculate_duration(results)

        # Create log content
        git_status = "✅ Clean" if not context.get("git_dirty") else "⚠️ Dirty"
        git_section = (
            f"""
## Git Information
- **Branch**: {context.get('git_branch', 'Unknown')}
- **Commit**: {context.get('git_commit', 'Unknown')[:8]}{'...' if context.get('git_commit') else ''}
- **Status**: {git_status}
"""
            if context.get("git_commit")
            else ""
        )

        log_content = f"""# {self.tool_name.title()} Execution Log

## Execution Context
- **Timestamp**: {context['timestamp']}
- **Operation**: {operation}
- **Execution Source**: {context['execution_source']}
- **Triggered By**: {context['triggered_by']}
- **Hostname**: {context['hostname']}
- **Platform**: {context['platform']}
- **Working Directory**: {context['working_directory']}
{git_section}
## Parameters
"""

        # Add parameters
        for key, value in parameters.items():
            if isinstance(value, (dict, list)):
                log_content += f"- **{key}**: `{json.dumps(value)}`\n"
            else:
                log_content += f"- **{key}**: {value}\n"

        # Add results summary
        log_content += f"""
## Results Summary
- **Status**: {'✅ Success' if results.get('success', True) else '❌ Failed'}
- **Duration**: {duration}
"""

        # Add specific result fields
        for key, value in results.items():
            if key not in ["success", "start_time", "end_time", "duration"]:
                if isinstance(value, (dict, list)):
                    log_content += f"- **{key.replace('_', ' ').title()}**: `{json.dumps(value)}`\n"
                else:
                    log_content += f"- **{key.replace('_', ' ').title()}**: {value}\n"

        # Add additional sections if provided
        if additional_sections:
            for section_title, section_content in additional_sections.items():
                log_content += f"\n## {section_title}\n{section_content}\n"

        # Add detailed results
        log_content += f"""
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
{json.dumps(context, indent=2)}
```
</details>

---
*Log generated automatically by RTGS Lab Tools - {self.tool_name}*
"""

        # Write log file
        with open(log_path, "w") as f:
            f.write(log_content)

        logger.info(f"Created execution log: {log_path}")
        return str(log_path)

    def _calculate_duration(self, results: Dict[str, Any]) -> str:
        """Calculate and format execution duration from results."""
        try:
            if "start_time" in results and "end_time" in results:
                start_time = datetime.fromisoformat(results["start_time"])
                end_time = datetime.fromisoformat(results["end_time"])
                duration = (end_time - start_time).total_seconds()
            elif "duration" in results:
                duration = float(results["duration"])
            else:
                return "Unknown"

            if duration < 60:
                return f"{duration:.1f}s"
            elif duration < 3600:
                return f"{duration/60:.1f}m"
            else:
                return f"{duration/3600:.1f}h"
        except Exception:
            return "Unknown"

    def _get_duration_seconds(self, results: Dict[str, Any]) -> Optional[int]:
        """Get duration in seconds from results."""
        try:
            if "start_time" in results and "end_time" in results:
                start_time = datetime.fromisoformat(results["start_time"])
                end_time = datetime.fromisoformat(results["end_time"])
                return int((end_time - start_time).total_seconds())
            elif "duration" in results:
                return int(float(results["duration"]))
            else:
                return None
        except Exception:
            return None

    def save_to_postgres(
        self,
        operation: str,
        parameters: Dict[str, Any],
        results: Dict[str, Any],
        script_path: Optional[str] = None,
        log_file_path: Optional[str] = None,
    ) -> bool:
        """Save execution log to PostgreSQL database.

        Args:
            operation: Description of the operation performed
            parameters: Parameters used for the operation
            results: Results of the operation
            script_path: Path to the script that was executed
            log_file_path: Path to the markdown log file

        Returns:
            True if successful, False otherwise
        """
        try:
            self.ensure_table_exists()
            context = self.get_execution_context(script_path)

            log_entry = ToolCallLog(
                timestamp=datetime.fromisoformat(context["timestamp"]),
                tool_name=self.tool_name,
                operation=operation,
                execution_source=context["execution_source"],
                triggered_by=context["triggered_by"],
                hostname=context["hostname"],
                platform=context["platform"],
                python_version=context["python_version"],
                working_directory=context["working_directory"],
                script_path=script_path,
                success=results.get("success", True),
                duration_seconds=self._get_duration_seconds(results),
                parameters=json.dumps(parameters),
                results=json.dumps(results),
                environment_variables=json.dumps(context["environment_variables"]),
                note=results.get("note"),
                log_file_path=log_file_path,
                git_commit=context.get("git_commit"),
                git_branch=context.get("git_branch"),
                git_dirty=context.get("git_dirty"),
                command=context.get("command"),
            )

            session = self.Session()
            try:
                session.add(log_entry)
                session.commit()
                logger.info(
                    f"Successfully saved tool call log to database: {operation}"
                )
                return True
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Failed to save tool call log to database: {e}")
                return False
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Failed to save tool call log to database: {e}")
            return False

    def log_execution(
        self,
        operation: str,
        parameters: Dict[str, Any],
        results: Dict[str, Any],
        script_path: Optional[str] = None,
        additional_sections: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Log execution to database only.

        Args:
            operation: Description of the operation performed
            parameters: Parameters used for the operation
            results: Results of the operation
            script_path: Path to the script that was executed
            additional_sections: Additional markdown sections to include (ignored, for compatibility)

        Returns:
            True if successfully saved to database, False otherwise
        """
        return self.save_to_postgres(
            operation=operation,
            parameters=parameters,
            results=results,
            script_path=script_path,
            log_file_path=None,
        )

    def get_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent tool call logs from database.

        Args:
            limit: Maximum number of logs to return

        Returns:
            List of log dictionaries
        """
        try:
            session = self.Session()
            try:
                logs = (
                    session.query(ToolCallLog)
                    .order_by(ToolCallLog.timestamp.desc())
                    .limit(limit)
                    .all()
                )

                return [
                    {
                        "id": log.id,
                        "timestamp": log.timestamp.isoformat(),
                        "tool_name": log.tool_name,
                        "operation": log.operation,
                        "execution_source": log.execution_source,
                        "triggered_by": log.triggered_by,
                        "success": log.success,
                        "duration_seconds": log.duration_seconds,
                        "note": log.note,
                        "git_commit": log.git_commit,
                        "git_branch": log.git_branch,
                        "git_dirty": log.git_dirty,
                        "command": log.command,
                    }
                    for log in logs
                ]
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Failed to get recent logs: {e}")
            return []
