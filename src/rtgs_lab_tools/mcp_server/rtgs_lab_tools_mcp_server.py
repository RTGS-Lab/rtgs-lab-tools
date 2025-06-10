"""FastMCP server for RTGS Lab Tools - Fixed environment variable handling."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("rtgs-lab-tools")

# Get the absolute path to the Python executable
PYTHON_EXECUTABLE = sys.executable

# Get the root directory of the project - this should be where your .env file is
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
print(f"Project root: {PROJECT_ROOT}")


# Load environment variables from .env file if it exists
def load_env_file():
    """Load environment variables from .env file."""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        from dotenv import load_dotenv

        load_dotenv(env_file)
        print(f"Loaded .env file from: {env_file}")
        return True
    else:
        print(f"No .env file found at: {env_file}")
        return False


# Load environment on startup
env_loaded = load_env_file()

# -----------------
# DATA EXTRACTION TOOLS
# -----------------


@mcp.tool("sensing_data_extract")
async def sensing_data_extract(
    project: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    node_ids: Optional[str] = None,
    output_format: str = "csv",
    create_zip: bool = False,
    output_dir: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract raw sensor data from the GEMS Sensing database with automatic git logging.

    This tool extracts environmental sensor data from the GEMS database, processes it,
    and saves it to CSV or Parquet format. All operations are automatically logged
    to git for tracking and reproducibility. Perfect for research data analysis,
    environmental monitoring studies, and scientific investigations.
    The node_id for this function is the node_id in the Particle ecosystem,
    which can be matched to a name by listing devices in the Particle ecosystem.

    Args:
        project: Project name to query (required) - use list_available_projects to see options
        start_date: Start date in YYYY-MM-DD format (default: 2018-01-01)
        end_date: End date in YYYY-MM-DD format (default: today)
        node_ids: Comma-separated list of node IDs to query specific sensors (optional)
        output_format: Output format - "csv" or "parquet" (default: csv)
        create_zip: Create a zip archive with metadata for sharing (default: False)
        output_dir: Custom output directory (default: ./data)
        note: Description for this data extraction for git logging (optional)

    Returns:
        Dict with success status, output file path, and extraction metadata
    """
    try:
        # Ensure we're in the correct directory
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables for proper git logging
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        # Build command to call the new grouped CLI
        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "sensing-data",
            "extract",
            "--project",
            project,
            "--output",
            output_format,
        ]

        if start_date:
            cmd.extend(["--start-date", start_date])

        if end_date:
            cmd.extend(["--end-date", end_date])

        if node_ids:
            cmd.extend(["--node-id", node_ids])

        if create_zip:
            cmd.append("--create-zip")

        if output_dir:
            cmd.extend(["--output-dir", output_dir])

        if note:
            cmd.extend(["--note", note])

        # Run with MCP environment for proper git logging
        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        # Restore original working directory
        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "stderr": stderr if stderr else None,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
            "working_directory": str(PROJECT_ROOT),
        }

    except Exception as e:
        # Restore original working directory
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"Data extraction failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
            "mcp_execution": True,
            "env_loaded": env_loaded,
            "project_root": str(PROJECT_ROOT),
        }


@mcp.tool("sensing_data_list_projects")
async def sensing_data_list_projects() -> Dict[str, Any]:
    """
    List all available projects in the GEMS Sensing database.

    Retrieves a comprehensive list of all environmental monitoring projects
    available in the GEMS database, including project names and node counts.
    Use this to discover what data is available before extracting sensor data.
    Nodes in the Particle ecosystem have a name and a node_id.
    Projects in the database only contain the node_id but not the name,
    so this tool requires that the name of the device is searched by listing devices
    in the Particle ecosystem to match the node_id to a name.

    Returns:
        Dict with success status and formatted list of projects with node counts
    """
    try:
        # Ensure we're in the correct directory
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "sensing-data",
            "list-projects",
        ]

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        # Restore original working directory
        os.chdir(original_cwd)

        return {"success": True, "output": stdout, "command": " ".join(cmd)}

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"Failed to list projects: {str(e)}",
            "env_loaded": env_loaded,
        }


# -----------------
# VISUALIZATION TOOLS
# -----------------


@mcp.tool("visualization_create")
async def visualization_create(
    file_path: str,
    parameter: Optional[str] = None,
    node_id: Optional[str] = None,
    multi_param: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    format: str = "png",
    title: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create professional visualizations from sensor data with automatic git logging.

    Generates time-series plots, multi-parameter comparisons, and custom visualizations
    from GEMS sensor data. Automatically parses sensor messages and creates publication-ready
    plots. All visualization operations are logged to git for reproducibility.

    Args:
        file_path: Path to the CSV file containing sensor data (required)
        parameter: Parameter path to plot (e.g., "Data.Devices.0.Temperature") - single parameter mode
        node_id: Specific node ID to plot when using single parameter mode
        multi_param: List of parameters as "node_id,parameter_path" for multi-parameter plots
        output_file: Custom output filename without extension (optional)
        format: Output format - "png", "pdf", or "svg" (default: png)
        title: Custom plot title (optional)
        note: Description for this visualization for git logging (optional)

    Returns:
        Dict with success status, output file path, and visualization metadata
    """
    try:
        # Ensure we're in the correct directory
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "visualization",
            "create",
            "--file",
            file_path,
            "--format",
            format,
        ]

        if parameter:
            cmd.extend(["--parameter", parameter])

        if node_id:
            cmd.extend(["--node-id", node_id])

        if multi_param:
            for param in multi_param:
                cmd.extend(["--multi-param", param])

        if output_file:
            cmd.extend(["--output-file", output_file])

        if title:
            cmd.extend(["--title", title])

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        # Restore original working directory
        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"Visualization failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


@mcp.tool("visualization_list_parameters")
async def visualization_list_parameters(file_path: str) -> Dict[str, Any]:
    """
    List available parameters in a sensor data file for visualization.

    Analyzes a sensor data CSV file and extracts all available parameters
    that can be visualized, organized by node ID. Essential for discovering
    what data is available for plotting before creating visualizations.

    Args:
        file_path: Path to the CSV file containing sensor data (required)

    Returns:
        Dict with success status and formatted list of parameters by node
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "visualization",
            "list-parameters",
            file_path,
        ]

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {"success": True, "output": stdout, "command": " ".join(cmd)}

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {"success": False, "error": f"Failed to list parameters: {str(e)}"}


# -----------------
# ERROR ANALYSIS TOOLS
# -----------------


@mcp.tool("error_analysis_analyze")
async def error_analysis_analyze(
    file_path: str,
    generate_graph: bool = False,
    node_filter: Optional[str] = None,
    error_column: str = "message",
    output_analysis: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse and analyze error codes from GEMS sensor data files with automatic git logging.

    Args:
        file_path: Path to the CSV or JSON file containing error data
        generate_graph: Whether to generate error frequency graphs (default: False)
        node_filter: Comma-separated list of node IDs to filter errors by (use "all" to separate by node)
        error_column: Column containing error data (default: "message")
        output_analysis: Save analysis results to JSON file (optional)
        note: Description for this error analysis (optional)
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "error-analysis",
            "analyze",
            "--file",
            file_path,
            "--error-column",
            error_column,
        ]

        if generate_graph:
            cmd.append("--generate-graph")

        if node_filter:
            cmd.extend(["--nodes", node_filter])

        if output_analysis:
            cmd.extend(["--output-analysis", output_analysis])

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"Error analysis failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


@mcp.tool("error_analysis_decode")
async def error_analysis_decode(error_code: str) -> Dict[str, Any]:
    """
    Decode a single GEMS device error code.

    Args:
        error_code: Hex error code to decode (e.g., "1E01" or "0x1E01")
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "error-analysis",
            "decode",
            error_code,
        ]

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {"success": True, "output": stdout, "command": " ".join(cmd)}

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {"success": False, "error": f"Error code decoding failed: {str(e)}"}


# -----------------
# DEVICE CONFIGURATION TOOLS
# -----------------


@mcp.tool("device_configuration_update_config")
async def device_configuration_update_config(
    config: str,
    devices: str,
    output: str = "update_results.json",
    max_retries: int = 3,
    restart_wait: int = 30,
    online_timeout: int = 120,
    max_concurrent: int = 5,
    dry_run: bool = False,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update configurations on multiple Particle devices with automatic git logging.

    Args:
        config: Path to configuration JSON file OR JSON string (required)
        devices: Path to device list file OR comma/space separated device IDs (required)
        output: Output file for results (default: update_results.json)
        max_retries: Maximum retry attempts per device (default: 3)
        restart_wait: Seconds to wait for device restart (default: 30)
        online_timeout: Seconds to wait for device to come online (default: 120)
        max_concurrent: Maximum concurrent devices to process (default: 5)
        dry_run: Validate inputs without making changes (default: False)
        note: Description for this configuration update (optional)
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "device-configuration",
            "update-config",
            "--config",
            config,
            "--devices",
            devices,
            "--output",
            output,
            "--max-retries",
            str(max_retries),
            "--restart-wait",
            str(restart_wait),
            "--online-timeout",
            str(online_timeout),
            "--max-concurrent",
            str(max_concurrent),
        ]

        if dry_run:
            cmd.append("--dry-run")

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"Device configuration update failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


@mcp.tool("device_configuration_decode_system_uid")
async def device_configuration_decode_system_uid(
    uid: str,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Decode system configuration UID from ConfigurationManager.

    Args:
        uid: System configuration UID in decimal or hexadecimal format (with 0x prefix)
        note: Description for this operation (optional)

    Returns:
        Dict with success status and decoded system configuration
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "device-configuration",
            "decode-system",
            uid,
        ]

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"System UID decoding failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


@mcp.tool("device_configuration_decode_sensor_uid")
async def device_configuration_decode_sensor_uid(
    uid: str,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Decode sensor configuration UID from ConfigurationManager.

    Args:
        uid: Sensor configuration UID in decimal or hexadecimal format (with 0x prefix)
        note: Description for this operation (optional)

    Returns:
        Dict with success status and decoded sensor configuration
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "device-configuration",
            "decode-sensor",
            uid,
        ]

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"Sensor UID decoding failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


@mcp.tool("device_configuration_decode_both_uids")
async def device_configuration_decode_both_uids(
    system_uid: str,
    sensor_uid: str,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Decode both system and sensor configuration UIDs from ConfigurationManager.

    Args:
        system_uid: System configuration UID in decimal or hexadecimal format (with 0x prefix)
        sensor_uid: Sensor configuration UID in decimal or hexadecimal format (with 0x prefix)
        note: Description for this operation (optional)

    Returns:
        Dict with success status and decoded configurations for both UIDs
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "device-configuration",
            "decode-both",
            system_uid,
            sensor_uid,
        ]

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"UID decoding failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


# -----------------
# GRIDDED DATA TOOLS
# -----------------


@mcp.tool("gridded_data_era5")
async def gridded_data_era5(
    variables: List[str],
    start_date: str,
    end_date: str,
    area: Optional[str] = None,
    output_file: Optional[str] = None,
    pressure_levels: Optional[str] = None,
    time_hours: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Download ERA5 climate data with automatic git logging.

    Args:
        variables: List of ERA5 variables to download (required)
        start_date: Start date in YYYY-MM-DD format (required)
        end_date: End date in YYYY-MM-DD format (required)
        area: Bounding box as "north,west,south,east" (optional)
        output_file: Output NetCDF file path (optional)
        pressure_levels: Pressure levels (comma-separated) (optional)
        time_hours: Specific hours (comma-separated, e.g., "00:00,12:00") (optional)
        note: Description for this data download (optional)
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "gridded-data",
            "era5",
            "--start-date",
            start_date,
            "--end-date",
            end_date,
        ]

        # Add variables
        for var in variables:
            cmd.extend(["--variables", var])

        if area:
            cmd.extend(["--area", area])

        if output_file:
            cmd.extend(["--output-file", output_file])

        if pressure_levels:
            cmd.extend(["--pressure-levels", pressure_levels])

        if time_hours:
            cmd.extend(["--time-hours", time_hours])

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"ERA5 data download failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


@mcp.tool("gridded_data_list_variables")
async def gridded_data_list_variables() -> Dict[str, Any]:
    """List available ERA5 variables for download."""
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "gridded-data",
            "list-variables",
        ]

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {"success": True, "output": stdout, "command": " ".join(cmd)}

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {"success": False, "error": f"Failed to list ERA5 variables: {str(e)}"}


# -----------------
# AGRICULTURAL MODELING TOOLS
# -----------------


@mcp.tool("agricultural_crop_parameters")
async def agricultural_crop_parameters(
    crop: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get crop parameters for growing degree day calculations.

    Args:
        crop: Specific crop to show parameters for (optional - if not provided, lists all crops)
        note: Description for this operation (optional)

    Returns:
        Dict with success status and crop parameters or list of available crops
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "agricultural-modeling",
            "crops",
            "parameters",
        ]

        if crop:
            cmd.extend(["--crop", crop])

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"Crop parameters lookup failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


@mcp.tool("agricultural_calculate_gdd")
async def agricultural_calculate_gdd(
    t_min: float,
    t_max: float,
    crop: str,
    method: str = "modified",
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate Growing Degree Days for a crop.

    Args:
        t_min: Minimum temperature (°C)
        t_max: Maximum temperature (°C)
        crop: Crop to use for base and upper temperatures
        method: GDD calculation method - "original" or "modified" (default: modified)
        note: Description for this calculation (optional)

    Returns:
        Dict with success status and GDD calculation results
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "agricultural-modeling",
            "crops",
            "gdd",
            str(t_min),
            str(t_max),
            "--crop",
            crop,
            "--method",
            method,
        ]

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"GDD calculation failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


@mcp.tool("agricultural_calculate_chu")
async def agricultural_calculate_chu(
    t_min: float,
    t_max: float,
    t_base: float = 10.0,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate Corn Heat Units (CHU).

    Args:
        t_min: Minimum temperature (°C)
        t_max: Maximum temperature (°C)
        t_base: Base temperature (default: 10.0°C)
        note: Description for this calculation (optional)

    Returns:
        Dict with success status and CHU calculation results
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "agricultural-modeling",
            "crops",
            "chu",
            str(t_min),
            str(t_max),
            "--t-base",
            str(t_base),
        ]

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"CHU calculation failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


@mcp.tool("agricultural_calculate_et")
async def agricultural_calculate_et(
    input_file: str,
    output: Optional[str] = None,
    validate_only: bool = False,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate reference evapotranspiration from weather data CSV.

    Args:
        input_file: Path to the CSV file containing weather data (required)
        output: Output CSV file path (optional - auto-generated if not provided)
        validate_only: Only validate input data without calculation (default: False)
        note: Description for this calculation (optional)

    Returns:
        Dict with success status and evapotranspiration calculation results
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "agricultural-modeling",
            "evapotranspiration",
            "calculate",
            input_file,
        ]

        if output:
            cmd.extend(["--output", output])

        if validate_only:
            cmd.append("--validate-only")

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"Evapotranspiration calculation failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


@mcp.tool("agricultural_et_requirements")
async def agricultural_et_requirements(
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Show required columns for evapotranspiration calculation.

    Args:
        note: Description for this operation (optional)

    Returns:
        Dict with success status and list of required columns for ET calculation
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)

        # Set MCP environment variables
        env = os.environ.copy()
        env["MCP_SESSION"] = "true"
        env["MCP_USER"] = "claude"

        cmd = [
            PYTHON_EXECUTABLE,
            "-m",
            "rtgs_lab_tools.cli",
            "agricultural-modeling",
            "evapotranspiration",
            "requirements",
        ]

        if note:
            cmd.extend(["--note", note])

        stdout, stderr = await run_command_with_env(cmd, env, cwd=PROJECT_ROOT)

        os.chdir(original_cwd)

        return {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd),
            "mcp_execution": True,
            "git_logging_enabled": True,
        }

    except Exception as e:
        if "original_cwd" in locals():
            os.chdir(original_cwd)

        return {
            "success": False,
            "error": f"ET requirements lookup failed: {str(e)}",
            "command": " ".join(cmd) if "cmd" in locals() else "N/A",
        }


# -----------------
# UTILITY FUNCTIONS
# -----------------


async def run_command_with_env(
    cmd: List[str], env: Dict[str, str], cwd: Optional[str] = None
) -> tuple:
    """
    Run a command asynchronously with custom environment variables.

    Args:
        cmd: Command to run as a list of strings
        env: Environment variables dictionary
        cwd: Working directory for the command

    Returns:
        Tuple of (stdout, stderr) as strings
    """
    print(f"Running command with MCP env in {cwd}: {' '.join(cmd)}")
    print(f"DB_USER in env: {'DB_USER' in env}")
    print(f"MCP_SESSION in env: {env.get('MCP_SESSION', 'not set')}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=cwd,
    )

    stdout, stderr = await process.communicate()

    stdout_str = stdout.decode("utf-8")
    stderr_str = stderr.decode("utf-8")

    if process.returncode != 0:
        error_message = stderr_str if stderr_str else "Unknown error"
        raise Exception(
            f"Command failed with exit code {process.returncode}: {error_message}"
        )

    return stdout_str, stderr_str


# -----------------
# FILE MANAGEMENT TOOLS
# -----------------


@mcp.tool("list_data_files")
async def list_data_files(directory: Optional[str] = None) -> Dict[str, Any]:
    """
    List all files in a directory, with the default being the data directory.

    Args:
        directory: Path to the directory to list (default: ./data)
    """
    try:
        # Default to data directory in project root if none specified
        if directory is None:
            directory = str(PROJECT_ROOT / "data")

        # Ensure the directory exists
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            return {
                "success": True,
                "directory": directory,
                "files": [],
                "message": f"Directory {directory} was created as it did not exist.",
            }

        # Check if it's a valid directory
        if not os.path.isdir(directory):
            return {"success": False, "error": f"{directory} is not a directory."}

        # Get all files and subdirectories
        all_items = os.listdir(directory)

        # Separate files and directories
        files = []
        subdirs = []

        for item in all_items:
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                subdirs.append({"name": item, "type": "directory", "path": item_path})
            else:
                # Get file size and modification time
                stat_info = os.stat(item_path)
                size_bytes = stat_info.st_size
                mod_time = stat_info.st_mtime

                # Format size for human readability
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                # Format modification time
                from datetime import datetime

                mod_time_str = datetime.fromtimestamp(mod_time).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                files.append(
                    {
                        "name": item,
                        "type": "file",
                        "path": item_path,
                        "size_bytes": size_bytes,
                        "size": size_str,
                        "last_modified": mod_time_str,
                    }
                )

        # Sort both lists by name
        files.sort(key=lambda x: x["name"])
        subdirs.sort(key=lambda x: x["name"])

        return {
            "success": True,
            "directory": directory,
            "directories": subdirs,
            "files": files,
            "total_files": len(files),
            "total_directories": len(subdirs),
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error listing directory: {str(e)}",
            "directory": directory,
        }


@mcp.tool("check_environment")
async def check_environment() -> Dict[str, Any]:
    """Check the current environment and configuration status."""
    try:
        env_file = PROJECT_ROOT / ".env"

        result = {
            "success": True,
            "project_root": str(PROJECT_ROOT),
            "env_file_exists": env_file.exists(),
            "env_file_path": str(env_file),
            "current_working_directory": os.getcwd(),
            "python_executable": PYTHON_EXECUTABLE,
            "environment_variables": {},
        }

        # Check for key environment variables
        key_vars = [
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "PARTICLE_ACCESS_TOKEN",
            "CDS_API_KEY",
        ]
        for var in key_vars:
            result["environment_variables"][var] = {
                "exists": var in os.environ,
                "value": (
                    "***"
                    if var in os.environ
                    and var in ["DB_PASSWORD", "PARTICLE_ACCESS_TOKEN", "CDS_API_KEY"]
                    else os.environ.get(var, "NOT SET")
                ),
            }

        return result

    except Exception as e:
        return {"success": False, "error": f"Environment check failed: {str(e)}"}


# Start the server when the script is run directly
if __name__ == "__main__":
    # Print some debug info
    print(f"Python executable: {PYTHON_EXECUTABLE}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Environment loaded: {env_loaded}")

    # Check if .env file exists
    env_file = PROJECT_ROOT / ".env"
    print(f".env file exists: {env_file.exists()}")
    if env_file.exists():
        print(f".env file path: {env_file}")

    mcp.run(transport="stdio")
