"""Package update functionality for RTGS Lab Tools."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

import requests


def get_latest_release_tag() -> Optional[str]:
    """Get the latest release tag from GitHub API."""
    try:
        # Get the repository info from git remote
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        
        # Extract owner/repo from various URL formats
        if "github.com" in remote_url:
            if remote_url.startswith("https://github.com/"):
                repo_path = remote_url.replace("https://github.com/", "").replace(".git", "")
            elif remote_url.startswith("git@github.com:"):
                repo_path = remote_url.replace("git@github.com:", "").replace(".git", "")
            else:
                return None
            
            # Query GitHub API for latest release
            api_url = f"https://api.github.com/repos/{repo_path}/releases/latest"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("tag_name")
            
    except (subprocess.CalledProcessError, requests.RequestException, KeyError):
        pass
    
    return None


def get_current_version() -> str:
    """Get current version information."""
    try:
        # Try to get git tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        try:
            # Get latest commit hash
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            return f"dev-{result.stdout.strip()}"
        except subprocess.CalledProcessError:
            return "unknown"


def check_for_updates() -> Tuple[Optional[bool], str, str]:
    """
    Check if updates are available.
    
    Returns:
        Tuple of (has_update, current_version, message)
        has_update: True if update available, False if up-to-date, None if error
    """
    current = get_current_version()
    latest = get_latest_release_tag()
    
    if not latest:
        return None, current, "Could not fetch latest release information"
    
    if current == latest:
        return False, current, f"Already on latest release: {latest}"
    elif current.startswith("dev-"):
        return True, current, f"Development version detected. Latest release: {latest}"
    else:
        return True, current, f"Update available: {current} → {latest}"


def run_install_script() -> bool:
    """
    Run the install.sh script to update the package.
    
    Returns:
        True if successful, False otherwise
    """
    # Find the install.sh script (should be in project root)
    project_root = Path(__file__).parent.parent.parent.parent
    install_script = project_root / "install.sh"
    
    if not install_script.exists():
        print("Error: install.sh script not found")
        return False
    
    print("Running install.sh to update package...")
    
    try:
        # Make sure the script is executable
        os.chmod(install_script, 0o755)
        
        # Run the install script using bash explicitly, inheriting terminal I/O
        # This allows the script to run exactly as if called from the command line
        result = subprocess.run(
            ["bash", str(install_script)], 
            cwd=project_root, 
            check=True
        )
        
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Update failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"Update failed: {e}")
        return False


def get_version_info() -> dict:
    """Get comprehensive version information."""
    current = get_current_version()
    latest = get_latest_release_tag()
    
    return {
        "current": current,
        "latest": latest,
        "is_dev": current.startswith("dev-"),
        "is_latest": current == latest if latest else None,
        "update_available": current != latest if latest else None
    }