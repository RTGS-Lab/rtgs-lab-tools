"""Google Cloud Secret Manager integration for RTGS Lab Tools."""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SecretManagerClient:
    """Client for Google Cloud Secret Manager with graceful fallback."""
    
    def __init__(self, project_id: Optional[str] = None):
        """Initialize Secret Manager client.
        
        Args:
            project_id: Google Cloud Project ID. If None, will try to detect from environment.
        """
        self._client = None
        self._project_id = project_id or self._get_project_id()
        self._authenticated = False
        
        # Try to initialize client
        if self._project_id:
            self._init_client()
    
    def _get_project_id(self) -> Optional[str]:
        """Get project ID from various sources."""
        # Try environment variables first
        project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        if project_id:
            return project_id
            
        # Try to get from gcloud config
        try:
            import subprocess
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
            
        return None
    
    def _init_client(self):
        """Initialize the Secret Manager client."""
        try:
            from google.cloud import secretmanager
            from google.auth.exceptions import DefaultCredentialsError
            
            self._client = secretmanager.SecretManagerServiceClient()
            # Test authentication by listing (but not executing) a secret access
            self._authenticated = True
            logger.debug("Secret Manager client initialized successfully")
            
        except DefaultCredentialsError:
            logger.debug("No valid Google Cloud credentials found")
            self._authenticated = False
        except ImportError:
            logger.debug("Google Cloud Secret Manager library not available")
            self._authenticated = False
        except Exception as e:
            logger.debug(f"Failed to initialize Secret Manager client: {e}")
            self._authenticated = False
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a secret value from Secret Manager.
        
        Args:
            secret_name: Name of the secret (without project path)
            
        Returns:
            Secret value if found and accessible, None otherwise
        """
        if not self._authenticated or not self._client or not self._project_id:
            return None
            
        try:
            # Build the resource name
            name = f"projects/{self._project_id}/secrets/{secret_name}/versions/latest"
            
            # Access the secret version
            response = self._client.access_secret_version(request={"name": name})
            
            # Return the decoded payload
            secret_value = response.payload.data.decode("UTF-8")
            logger.debug(f"Successfully retrieved secret: {secret_name}")
            return secret_value
            
        except Exception as e:
            logger.debug(f"Failed to retrieve secret {secret_name}: {e}")
            return None
    
    def test_access(self) -> bool:
        """Test if Secret Manager is accessible.
        
        Returns:
            True if Secret Manager is accessible, False otherwise
        """
        if not self._authenticated or not self._client or not self._project_id:
            return False
            
        try:
            # Try to list secrets (just to test access, we don't use the result)
            parent = f"projects/{self._project_id}"
            list(self._client.list_secrets(request={"parent": parent}, timeout=5))
            return True
        except Exception:
            return False
    
    def is_authenticated(self) -> bool:
        """Check if Secret Manager client is authenticated."""
        return self._authenticated
    
    def get_project_id(self) -> Optional[str]:
        """Get the current project ID."""
        return self._project_id


# Global instance
_secret_manager_client: Optional[SecretManagerClient] = None


def get_secret_manager_client() -> SecretManagerClient:
    """Get the global Secret Manager client instance."""
    global _secret_manager_client
    if _secret_manager_client is None:
        _secret_manager_client = SecretManagerClient()
    return _secret_manager_client