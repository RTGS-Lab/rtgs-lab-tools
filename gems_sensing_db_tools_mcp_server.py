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
VISUALIZER_PATH = os.path.join(SCRIPT_DIR, "gems_sensing_data_visualizer.py")

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
    Extract raw data from the GEMS Sensing database. Before using this command be sure the node_id from Particle is known. Use a particle list_devices tool to get the Node IDs.
    
    Args:
        project: Project name to query (required)
        start_date: Start date in YYYY-MM-DD format (default: 2018-01-01)
        end_date: End date in YYYY-MM-DD format (default: today)
        node_id: Comma-separated list of node IDs to query. These should be node IDs from Partile directly. As an example, the ID should ALWAYS look something like this e00fcx6xf3x4e4x5e2x6b8x1 (optional)
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

# -----------------
# DATA VISUALIZATION ENDPOINTS
# -----------------

@mcp.tool("visualize_data")
async def visualize_data(
    file_path: str,
    node_parameter: Optional[str] = None,
    output: Optional[str] = None,
    type: Optional[str] = None,
    multi_node_param: Optional[List[str]] = None,
    format: str = "png",
    no_markers: bool = False,
    time_range: Optional[List[str]] = None,
    search: Optional[str] = None,
    explore: bool = False,
    list_params: bool = False
) -> Dict[str, Any]:
    """
    Visualize GEMS sensing data using the data visualizer tool.
    
    Args:
        file_path: Path to the CSV file containing GEMS data
        node_parameter: Node ID and parameter path (e.g. "e00fce68616772391f284037, Data.Devices.0.Acclima Soil.VWC"). To plot for all devices in the data file, use node_id = "all"
        output: Output filename for the graph
        type: Filter by message type (data, diagnostic, error, metadata)
        multi_node_param: List of node-parameters to plot on the same graph (format: "e00fce68616772391f284037, Data.Devices.0.Acclima Soil.VWC","e00fce68616772391f284037, Data.Devices.0.Acclima Soil.VWC")
        format: Output file format (png, pdf, svg, jpg)
        no_markers: Disable markers on the plot
        time_range: Filter data by time range [start, end] (format: YYYY-MM-DD HH:MM:SS)
        search: Search for parameters containing the given string
        explore: Explore data structure and show available parameters
        list_params: List available parameters instead of plotting
    """
    # Ensure the figures directory exists
    figures_dir = os.path.join(SCRIPT_DIR, "figures")
    os.makedirs(figures_dir, exist_ok=True)
    
    # Build the command with all the options
    cmd = [PYTHON_EXECUTABLE, VISUALIZER_PATH, "--file", file_path]
    
    # Handle node_parameter if provided
    if node_parameter:
        cmd.extend(["--node-parameter", node_parameter])
    
    if output:
        cmd.extend(["--output", output])
    
    if type:
        cmd.extend(["--type", type])
    
    if multi_node_param:
        cmd.extend(["--multi-node-param"])
        cmd.extend(multi_node_param)
    
    if format:
        cmd.extend(["--format", format])
    
    if no_markers:
        cmd.append("--no-markers")
    
    if time_range and len(time_range) == 2:
        cmd.extend(["--time-range", time_range[0], time_range[1]])
    
    if search:
        cmd.extend(["--search", search])
    
    if explore:
        cmd.append("--explore")
    
    if list_params:
        cmd.append("--list")
    
    try:
        stdout, stderr = await run_command(cmd)
        
        # Determine the output file path from stdout
        output_file = None
        for line in stdout.splitlines():
            if "Plot saved to" in line:
                output_file = line.split("Plot saved to")[1].strip()
                break
        
        result = {
            "success": True,
            "output": stdout,
            "command": " ".join(cmd)
        }
        
        if output_file:
            # Get the full path to the output file
            if output_file.startswith("figures/"):
                # Extract just the filename part
                output_file = output_file.replace("figures/", "")
            
            full_path = os.path.join(figures_dir, output_file)
            if os.path.exists(full_path):
                result["output_file"] = full_path
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error running visualizer: {str(e)}",
            "command": " ".join(cmd)
        }

@mcp.tool("list_parameters") 
async def list_parameters(file_path: str) -> Dict[str, Any]:
    """
    List available parameters in the GEMS sensing data file.
    
    Args:
        file_path: Path to the CSV file containing GEMS data
    """
    return await visualize_data(file_path, list_params=True)

@mcp.tool("explore_data_structure")
async def explore_data_structure(file_path: str) -> Dict[str, Any]:
    """
    Explore the data structure of a GEMS sensing data file.
    
    Args:
        file_path: Path to the CSV file containing GEMS data
    """
    return await visualize_data(file_path, explore=True)

@mcp.tool("search_parameters")
async def search_parameters(file_path: str, search_term: str) -> Dict[str, Any]:
    """
    Search for parameters in the GEMS sensing data file.
    
    Args:
        file_path: Path to the CSV file containing GEMS data
        search_term: String to search for in parameter names
    """
    return await visualize_data(file_path, search=search_term)

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
    cwd = os.path.dirname(os.path.abspath(__file__))
    
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
    print(f"Visualizer tool path: {VISUALIZER_PATH}")
    print(f"Current working directory: {os.getcwd()}")
    
    mcp.run(transport='stdio')