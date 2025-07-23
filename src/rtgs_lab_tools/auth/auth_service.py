"""Authentication service for Google Cloud integration."""

import os
import subprocess
import sys
from typing import Optional, Dict, Any

from ..core.secret_manager import get_secret_manager_client


class AuthService:
    """Service for managing Google Cloud authentication."""
    
    def __init__(self):
        """Initialize the authentication service."""
        self._secret_client = get_secret_manager_client()
    
    def check_gcloud_installed(self) -> bool:
        """Check if gcloud CLI is installed."""
        try:
            result = subprocess.run(
                ["gcloud", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def install_gcloud_instructions(self) -> str:
        """Get platform-specific gcloud installation instructions."""
        platform = sys.platform.lower()
        
        if platform == "win32":
            return """
To install Google Cloud CLI on Windows:
1. Download the installer: https://cloud.google.com/sdk/docs/install-sdk#windows
2. Or use the Windows installer: https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe
3. Restart Git Bash after installation
"""
        elif platform == "darwin":
            return """
To install Google Cloud CLI on macOS:
1. Using Homebrew (recommended): brew install google-cloud-sdk
2. Or download from: https://cloud.google.com/sdk/docs/install-sdk#mac
3. Restart your terminal after installation
"""
        else:  # Linux
            return """
To install Google Cloud CLI on Linux:
1. Using snap: sudo snap install google-cloud-cli --classic
2. Using apt (Debian/Ubuntu): 
   curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
   echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
   sudo apt update && sudo apt install google-cloud-cli
3. Or download from: https://cloud.google.com/sdk/docs/install-sdk#linux
4. Restart your terminal after installation
"""
    
    def login(self, headless: bool = False) -> Dict[str, Any]:
        """Perform Google Cloud authentication login.
        
        Args:
            headless: If True, use --no-browser for terminal-only environments
        
        Returns:
            Dict with success status and messages
        """
        # Check if gcloud is installed
        if not self.check_gcloud_installed():
            return {
                "success": False,
                "error": "gcloud CLI not found",
                "instructions": self.install_gcloud_instructions()
            }
        
        try:
            # Prepare command based on environment
            cmd = ["gcloud", "auth", "application-default", "login"]
            if headless:
                cmd.append("--no-browser")
                print("🔐 Starting headless Google Cloud authentication...")
                print("📋 Follow the instructions below to complete authentication.")
            else:
                print("🔐 Opening browser for Google Cloud authentication...")
            
            result = subprocess.run(cmd, timeout=300)  # 5 minute timeout
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": "Authentication failed or was cancelled"
                }
            
            # Test authentication by checking Secret Manager access
            auth_status = self.get_auth_status()
            if auth_status["authenticated"]:
                return {
                    "success": True,
                    "message": "Successfully authenticated with Google Cloud",
                    "user": auth_status.get("user"),
                    "project": auth_status.get("project"),
                    "secret_manager_access": auth_status.get("secret_manager_access", False),
                    "headless": headless
                }
            else:
                return {
                    "success": False,
                    "error": "Authentication completed but Secret Manager access failed",
                    "details": "You may need additional IAM permissions for Secret Manager access"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Authentication timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Authentication error: {str(e)}"
            }
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get current authentication status.
        
        Returns:
            Dict with authentication status information
        """
        status = {
            "authenticated": False,
            "user": None,
            "project": None,
            "secret_manager_access": False,
            "gcloud_installed": self.check_gcloud_installed()
        }
        
        if not status["gcloud_installed"]:
            return status
        
        try:
            # Check if authenticated
            result = subprocess.run(
                ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                status["authenticated"] = True
                status["user"] = result.stdout.strip()
            
            # Get current project
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                status["project"] = result.stdout.strip()
            
            # Test Secret Manager access
            if status["authenticated"]:
                status["secret_manager_access"] = self._secret_client.test_access()
            
        except Exception:
            pass
        
        return status
    
    def logout(self) -> Dict[str, Any]:
        """Logout from Google Cloud.
        
        Returns:
            Dict with success status and messages
        """
        if not self.check_gcloud_installed():
            return {
                "success": False,
                "error": "gcloud CLI not found"
            }
        
        try:
            # Try gcloud revoke with shorter timeout first
            result = subprocess.run(
                ["gcloud", "auth", "application-default", "revoke"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Successfully logged out from Google Cloud"
                }
                
        except subprocess.TimeoutExpired:
            # If gcloud command times out, try manual cleanup
            pass
        except Exception:
            # If other errors, try manual cleanup
            pass
        
        # Fallback: manually delete credentials file
        try:
            credentials_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
            if os.path.exists(credentials_path):
                os.remove(credentials_path)
                return {
                    "success": True,
                    "message": "Successfully logged out (manual cleanup)"
                }
            else:
                return {
                    "success": True,
                    "message": "Already logged out (no credentials found)"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Could not remove credentials: {str(e)}"
            }