from typing import Any, Dict
from helpers.api_helpers import make_api_request

async def get_device_vitals(device_id: str) -> Dict[str, Any]:
    """
    Get the last known vitals for a device.
    
    Args:
        device_id: The ID of the device
    """
    return await make_api_request("get", f"/v1/diagnostics/{device_id}/last")