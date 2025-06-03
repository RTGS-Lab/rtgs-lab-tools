from typing import Any, Dict, Optional
from helpers.api_helpers import make_api_request

async def list_product_firmware(product_id: str, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
    """
    List all firmware versions for a specific product.
    
    Args:
        product_id: The ID of the product
        page: Page number for paginated results (default: 1)
        per_page: Number of firmware versions per page (default: 25)
    """
    params = {
        "page": page,
        "per_page": per_page
    }
    return await make_api_request("get", f"/v1/products/{product_id}/firmware", params=params)
