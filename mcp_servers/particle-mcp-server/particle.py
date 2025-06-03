from typing import Any, Dict, Optional
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Import all endpoint modules
from endpoints import devices, diagnostics, organizations, product_firmware

# Initialize FastMCP server
mcp = FastMCP("particle")

# -----------------
# DEVICE ENDPOINTS
# -----------------
@mcp.tool("list_devices")
async def list_devices() -> Dict[str, Any]:
    """List all Particle devices in your account."""
    return await devices.list_devices()

@mcp.tool("list_product_devices")
async def list_product_devices(product_id: str, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
    """
    List devices in a specific product.
    
    Args:
        product_id: The ID of the product
        page: Page number for paginated results (default: 1)
        per_page: Number of devices per page (default: 25)
    """
    return await devices.list_product_devices(product_id, page, per_page)

@mcp.tool("rename_device")
async def rename_device(device_id: str, name: str) -> Dict[str, Any]:
    """Rename a device."""
    return await devices.rename_device(device_id, name)

@mcp.tool("add_device_notes")
async def add_device_notes(device_id: str, notes: str) -> Dict[str, Any]:
    """Add notes to a device."""
    return await devices.add_device_notes(device_id, notes)

@mcp.tool("ping_device")
async def ping_device(device_id: str) -> Dict[str, Any]:
    """Ping a device to check if it's online. This sould only ever be called if specifically asked for."""
    return await diagnostics.ping_device(device_id)

@mcp.tool("call_function")
async def call_function(device_id: str, function_name: str, argument: str = "") -> Dict[str, Any]:
    """
    Call a function on a device. This should only be used when a specific function needs to be called and explicitly asked for.
    
    Args:
        device_id: The ID of the device
        function_name: The name of the function to call
        argument: Argument to pass to the function (optional)
    """
    return await devices.call_function(device_id, function_name, argument)

# -----------------
# DIAGNOSTIC ENDPOINTS
# -----------------

@mcp.tool("get_device_vitals")
async def get_device_vitals(device_id: str) -> Dict[str, Any]:
    """Get the last known vitals for a device."""
    return await diagnostics.get_device_vitals(device_id)

# -----------------
# ORGANIZATION ENDPOINTS
# -----------------
@mcp.tool("list_organizations")
async def list_organizations() -> Dict[str, Any]:
    """List all organizations the user has access to."""
    return await organizations.list_organizations()

@mcp.tool("list_organization_products")
async def list_organization_products(org_id: str) -> Dict[str, Any]:
    """List products within an organization."""
    return await organizations.list_organization_products(org_id)

# -----------------
# PRODUCT FIRMWARE ENDPOINTS
# -----------------
@mcp.tool("list_product_firmware")
async def list_product_firmware(product_id: str, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
    """
    List all firmware versions for a specific product.
    
    Args:
        product_id: The ID of the product
        page: Page number for paginated results (default: 1)
        per_page: Number of firmware versions per page (default: 25)
    """
    return await product_firmware.list_product_firmware(product_id, page, per_page)


# Start the server when the script is run directly
if __name__ == "__main__":
    mcp.run(transport='stdio')