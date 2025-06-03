from typing import Any, Dict
from helpers.api_helpers import make_api_request

async def list_organizations() -> Dict[str, Any]:
    """List all organizations the user has access to."""
    return await make_api_request("get", "/v1/orgs")

async def list_organization_products(org_id: str) -> Dict[str, Any]:
    """
    List products within an organization.
    
    Args:
        org_id: The ID of the organization
    """
    return await make_api_request("get", f"/v1/orgs/{org_id}/products")