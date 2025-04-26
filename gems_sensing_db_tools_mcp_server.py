from typing import Any, Dict, List, Optional
import asyncio
import os
import sys
import json
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("gems_sensing")

# Get the absolute path to the Python executable
PYTHON_EXECUTABLE = sys.executable

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEMS_TOOL_PATH = os.path.join(SCRIPT_DIR, "get_sensing_data.py")

@mcp.tool("list_projects")
async def list_projects() -> Dict[str, Any]:
    """List all available projects in the GEMS Sensing database."""
    try:
        stdout, stderr = await run_command([PYTHON_EXECUTABLE, GEMS_TOOL_PATH, "--list-projects"])
        # Combine stdout and stderr to get all logger output
        full_output = stdout
        if stderr:
            full_output += "\n" + stderr
        return {"output": full_output}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool("get_raw_data")
async def get_raw_data(
    project: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    node_id: Optional[str] = None,
    output_format: str = "csv",
    verbose: bool = False,
    create_zip: bool = False,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract raw data from the GEMS Sensing database. Before using this command be sure the node_id from Particle is known.
    
    Args:
        project: Project name to query (required)
        start_date: Start date in YYYY-MM-DD format (default: 2018-01-01)
        end_date: End date in YYYY-MM-DD format (default: today)
        node_id: Comma-separated list of node IDs to query. These should be node IDs from Partile directly. As an example, the ID should look something like this e00fcx6xf3x4e4x5e2x6b8x1 (optional)
        output_format: Output format - "csv" or "parquet" (default: csv)
        verbose: Enable verbose output (default: False)
        create_zip: Create a zip archive of the output (default: False)
        output_dir: Custom output directory (default: ./data)
    """
    cmd = [PYTHON_EXECUTABLE, GEMS_TOOL_PATH, "--project", project]
    
    if start_date:
        cmd.extend(["--start-date", start_date])
    
    if end_date:
        cmd.extend(["--end-date", end_date])
    
    if node_id:
        cmd.extend(["--node-id", node_id])
    
    if output_format:
        cmd.extend(["--output", output_format])
    
    if verbose:
        cmd.append("--verbose")
    
    if create_zip:
        cmd.append("--zip")
    
    if output_dir:
        cmd.extend(["--output-dir", output_dir])
    
    try:
        stdout, stderr = await run_command(cmd)
        # Combine stdout and stderr to get all logger output
        full_output = stdout
        if stderr:
            full_output += "\n" + stderr
        return {"output": full_output}
    except Exception as e:
        return {"error": str(e), "command": " ".join(cmd)}

@mcp.tool("setup_credentials")
async def setup_credentials() -> Dict[str, Any]:
    """Create a template .env file for database credentials."""
    try:
        stdout, stderr = await run_command([PYTHON_EXECUTABLE, GEMS_TOOL_PATH, "--setup-credentials"])
        # Combine stdout and stderr to get all logger output
        full_output = stdout
        if stderr:
            full_output += "\n" + stderr
        return {"output": full_output}
    except Exception as e:
        return {"error": str(e)}

async def run_command(cmd: List[str]) -> tuple:
    """
    Run a command asynchronously and return its stdout and stderr.
    
    Args:
        cmd: Command to run as a list of strings
        
    Returns:
        Tuple of (stdout, stderr) as strings
    """
    # Print the command for debugging
    print(f"Running command: {' '.join(cmd)}")
    
    # Make sure we're running in the correct directory
    cwd = os.path.dirname(GEMS_TOOL_PATH)
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd  # Set the current working directory
    )
    
    stdout, stderr = await process.communicate()
    
    stdout_str = stdout.decode('utf-8')
    stderr_str = stderr.decode('utf-8')
    
    if process.returncode != 0:
        error_message = stderr_str if stderr_str else "Unknown error"
        raise Exception(f"Command failed with exit code {process.returncode}: {error_message}")
    
    return stdout_str, stderr_str

# Start the server when the script is run directly
if __name__ == "__main__":
    # Print some debug info
    print(f"Python executable: {PYTHON_EXECUTABLE}")
    print(f"GEMS tool path: {GEMS_TOOL_PATH}")
    print(f"Current working directory: {os.getcwd()}")
    
    mcp.run(transport='stdio')