from typing import Any, Dict, Optional
import os
import httpx

# Constants
PARTICLE_API_BASE = "https://api.particle.io"

# Get access token from environment variables
ACCESS_TOKEN = os.getenv("PARTICLE_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    raise EnvironmentError("PARTICLE_ACCESS_TOKEN environment variable is not set. Please add it to your .env file.")

async def make_api_request(method: str, endpoint: str, headers: Optional[Dict] = None, 
                          json_data: Optional[Dict] = None, params: Optional[Dict] = None):
    """Make an API request to the Particle API with proper error handling."""
    if headers is None:
        headers = {}
    
    # Add authorization header if not present
    if "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    
    async with httpx.AsyncClient() as client:
        try:
            if method.lower() == "get":
                response = await client.get(f"{PARTICLE_API_BASE}{endpoint}", headers=headers, params=params)
            elif method.lower() == "post":
                response = await client.post(f"{PARTICLE_API_BASE}{endpoint}", headers=headers, json=json_data)
            elif method.lower() == "put":
                response = await client.put(f"{PARTICLE_API_BASE}{endpoint}", headers=headers, json=json_data)
            elif method.lower() == "delete":
                response = await client.delete(f"{PARTICLE_API_BASE}{endpoint}", headers=headers)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}
            
            # Check if the response was successful
            if response.status_code >= 200 and response.status_code < 300:
                return response.json() if response.content else {"status": "success"}
            else:
                return {
                    "error": f"API request failed with status code: {response.status_code}",
                    "message": response.text
                }
        except Exception as e:
            return {"error": f"Error making API request: {str(e)}"}