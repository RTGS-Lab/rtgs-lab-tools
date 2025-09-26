"""Authentication service for Google Cloud integration."""

import os
import subprocess
import sys
from typing import Any, Dict, Optional

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
                ["gcloud", "--version"], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # On Windows, try common installation paths
            if sys.platform.lower() == "win32":
                return self._check_windows_gcloud_paths()
            return False

    def _check_windows_gcloud_paths(self) -> bool:
        """Check common Windows paths for gcloud installation."""
        import shutil

        # Try using shutil.which which checks PATH and PATHEXT on Windows
        if shutil.which("gcloud"):
            return True

        # Common Windows installation paths
        common_paths = [
            os.path.expanduser(
                "~\\AppData\\Local\\Google\\Cloud SDK\\google-cloud-sdk\\bin\\gcloud.cmd"
            ),
            "C:\\Program Files (x86)\\Google\\Cloud SDK\\google-cloud-sdk\\bin\\gcloud.cmd",
            "C:\\Program Files\\Google\\Cloud SDK\\google-cloud-sdk\\bin\\gcloud.cmd",
            os.path.expanduser("~\\google-cloud-sdk\\bin\\gcloud.cmd"),
        ]

        for path in common_paths:
            if os.path.exists(path):
                try:
                    result = subprocess.run(
                        [path, "--version"], capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        return True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue

        return False

    def _update_env_file_with_project(self, project_id: str) -> None:
        """Update .env file with Google Cloud project ID.

        Args:
            project_id: The Google Cloud project ID to add
        """
        env_file_path = ".env"

        # Check if .env file exists in current directory or parent directories
        current_dir = os.getcwd()
        while current_dir != os.path.dirname(current_dir):  # Stop at root
            env_path = os.path.join(current_dir, ".env")
            if os.path.exists(env_path):
                env_file_path = env_path
                break
            current_dir = os.path.dirname(current_dir)

        try:
            # Read existing .env file if it exists
            lines = []
            env_var_exists = False

            if os.path.exists(env_file_path):
                with open(env_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Check if GOOGLE_CLOUD_PROJECT already exists and update it
                for i, line in enumerate(lines):
                    if line.strip().startswith("GOOGLE_CLOUD_PROJECT"):
                        lines[i] = f"GOOGLE_CLOUD_PROJECT={project_id}\n"
                        env_var_exists = True
                        break

            # Add the environment variable if it doesn't exist
            if not env_var_exists:
                # Add a newline if file doesn't end with one
                if lines and not lines[-1].endswith("\n"):
                    lines.append("\n")
                lines.append(f"GOOGLE_CLOUD_PROJECT={project_id}\n")

            # Write back to file
            with open(env_file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

        except Exception as e:
            # Don't fail the login if we can't update .env file
            import logging

            logging.warning(f"Could not update .env file with project ID: {e}")

    def _get_gcloud_command(self) -> str:
        """Get the correct gcloud command for the current platform."""
        # On Windows, use shutil.which first as it handles PATH and PATHEXT properly
        if sys.platform.lower() == "win32":
            import shutil

            # Try shutil.which which handles Windows PATH and file extensions correctly
            gcloud_path = shutil.which("gcloud")
            if gcloud_path:
                try:
                    result = subprocess.run(
                        [gcloud_path, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        return gcloud_path
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

            # Try common Windows installation paths with proper path handling
            common_paths = [
                os.path.expanduser(
                    r"~\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
                ),
                r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
                r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
                os.path.expanduser(r"~\google-cloud-sdk\bin\gcloud.cmd"),
            ]

            for path in common_paths:
                if os.path.exists(path):
                    try:
                        result = subprocess.run(
                            [path, "--version"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if result.returncode == 0:
                            return path
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        continue

        # For non-Windows or as fallback, try the standard command
        try:
            result = subprocess.run(
                ["gcloud", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return "gcloud"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return "gcloud"  # Final fallback

    def install_gcloud_instructions(self) -> str:
        """Get platform-specific gcloud installation instructions."""
        platform = sys.platform.lower()

        if platform == "win32":
            return """
To install Google Cloud CLI on Windows:
1. Download the installer: https://cloud.google.com/sdk/docs/install-sdk#windows
2. Or use the Windows installer: https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe
3. Make sure to check "Add gcloud to PATH" during installation
4. Restart your terminal/command prompt after installation

If gcloud is installed but not found, you may need to add it to your PATH manually or restart your terminal.
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
                "instructions": self.install_gcloud_instructions(),
            }

        try:
            # Get the correct gcloud command
            gcloud_cmd = self._get_gcloud_command()

            # Prepare command based on environment
            cmd = [gcloud_cmd, "auth", "application-default", "login"]
            if headless:
                cmd.append("--no-browser")
                print("Starting headless Google Cloud authentication...")
                print("Follow the instructions below to complete authentication.")
            else:
                print("Opening browser for Google Cloud authentication...")

            result = subprocess.run(cmd, timeout=300)  # 5 minute timeout

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": "Authentication failed or was cancelled",
                }

            # Test authentication by checking Secret Manager access
            auth_status = self.get_auth_status()
            if auth_status["authenticated"]:
                # Auto-add project ID to .env file if available
                project_id = auth_status.get("project")
                if project_id:
                    self._update_env_file_with_project(project_id)

                return {
                    "success": True,
                    "message": "Successfully authenticated with Google Cloud",
                    "user": auth_status.get("user"),
                    "project": project_id,
                    "secret_manager_access": auth_status.get(
                        "secret_manager_access", False
                    ),
                    "headless": headless,
                }
            else:
                return {
                    "success": False,
                    "error": "Authentication completed but Secret Manager access failed",
                    "details": "You may need additional IAM permissions for Secret Manager access",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Authentication timed out"}
        except Exception as e:
            return {"success": False, "error": f"Authentication error: {str(e)}"}

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
            "gcloud_installed": self.check_gcloud_installed(),
        }

        if not status["gcloud_installed"]:
            return status

        try:
            # Get the correct gcloud command
            gcloud_cmd = self._get_gcloud_command()

            # Check if authenticated
            result = subprocess.run(
                [
                    gcloud_cmd,
                    "auth",
                    "list",
                    "--filter=status:ACTIVE",
                    "--format=value(account)",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout.strip():
                status["authenticated"] = True
                status["user"] = result.stdout.strip()

            # Get current project
            result = subprocess.run(
                [gcloud_cmd, "config", "get-value", "project"],
                capture_output=True,
                text=True,
                timeout=10,
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
            return {"success": False, "error": "gcloud CLI not found"}

        try:
            # Get the correct gcloud command
            gcloud_cmd = self._get_gcloud_command()

            # Try gcloud revoke with shorter timeout first
            result = subprocess.run(
                [gcloud_cmd, "auth", "application-default", "revoke"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Successfully logged out from Google Cloud",
                }

        except subprocess.TimeoutExpired:
            # If gcloud command times out, try manual cleanup
            pass
        except Exception:
            # If other errors, try manual cleanup
            pass

        # Fallback: manually delete credentials file
        try:
            credentials_path = os.path.expanduser(
                "~/.config/gcloud/application_default_credentials.json"
            )
            if os.path.exists(credentials_path):
                os.remove(credentials_path)
                return {
                    "success": True,
                    "message": "Successfully logged out (manual cleanup)",
                }
            else:
                return {
                    "success": True,
                    "message": "Already logged out (no credentials found)",
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Could not remove credentials: {str(e)}",
            }
