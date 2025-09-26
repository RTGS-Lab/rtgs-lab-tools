"""Configuration management for RTGS Lab Tools."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .exceptions import ConfigError
from .secret_manager import get_secret_manager_client


class Config:
    """Configuration manager for RTGS Lab Tools."""

    def __init__(self, env_file: Optional[str] = None):
        """Initialize configuration.

        Args:
            env_file: Path to .env file. If None, looks for .env in current directory.
        """
        # Load .env file first so environment variables are available
        if env_file:
            env_path = Path(env_file)
            if env_path.exists():
                load_dotenv(env_path, override=True)
        else:
            # Only load default .env if no specific file is provided
            env_path = Path.cwd() / ".env"
            if env_path.exists():
                load_dotenv(env_path)

        # Initialize Secret Manager client after .env is loaded
        self._secret_client = get_secret_manager_client()

    def _get_secret(
        self, secret_name: str, env_var: str, required: bool = True
    ) -> Optional[str]:
        """Get a secret value, trying Secret Manager first, then environment variables.

        Args:
            secret_name: Name of the secret in Secret Manager
            env_var: Environment variable name as fallback
            required: Whether this secret is required

        Returns:
            Secret value if found

        Raises:
            ConfigError: If required secret is not found
        """
        # Try Secret Manager first
        secret_value = self._secret_client.get_secret(secret_name)
        if secret_value:
            return secret_value

        # Fall back to environment variable
        env_value = os.getenv(env_var)
        if env_value:
            return env_value

        # If required and not found, raise error
        if required:
            raise ConfigError(
                f"{env_var} not found in Secret Manager or environment variables"
            )

        return None

    @property
    def db_host(self) -> str:
        """Database host."""
        return self._get_secret("rtgs-db-host", "DB_HOST")

    @property
    def db_port(self) -> int:
        """Database port."""
        port_str = self._get_secret("rtgs-db-port", "DB_PORT", required=False) or "5432"
        try:
            return int(port_str)
        except ValueError:
            raise ConfigError(f"Invalid DB_PORT value: {port_str}")

    @property
    def db_name(self) -> str:
        """Database name."""
        return self._get_secret("rtgs-db-name", "DB_NAME")

    @property
    def db_user(self) -> str:
        """Database user."""
        return self._get_secret("rtgs-db-user", "DB_USER")

    @property
    def db_password(self) -> str:
        """Database password."""
        return self._get_secret("rtgs-db-password", "DB_PASSWORD")

    @property
    def db_url(self) -> str:
        """Complete database URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def logging_db_host(self) -> str:
        """Logging database host."""
        return (
            self._get_secret("rtgs-logging-db-host", "LOGGING_DB_HOST", required=False)
            or self.db_host
        )

    @property
    def logging_db_port(self) -> int:
        """Logging database port."""
        port_str = self._get_secret(
            "rtgs-logging-db-port", "LOGGING_DB_PORT", required=False
        ) or str(self.db_port)
        try:
            return int(port_str)
        except ValueError:
            raise ConfigError(f"Invalid LOGGING_DB_PORT value: {port_str}")

    @property
    def logging_db_name(self) -> str:
        """Logging database name."""
        return (
            self._get_secret("rtgs-logging-db-name", "LOGGING_DB_NAME", required=False)
            or self.db_name
        )

    @property
    def logging_db_user(self) -> str:
        """Logging database user."""
        return (
            self._get_secret("rtgs-logging-db-user", "LOGGING_DB_USER", required=False)
            or self.db_user
        )

    @property
    def logging_db_password(self) -> str:
        """Logging database password."""
        return (
            self._get_secret(
                "rtgs-logging-db-password", "LOGGING_DB_PASSWORD", required=False
            )
            or self.db_password
        )

    @property
    def logging_db_url(self) -> str:
        """Complete logging database URL."""
        return f"postgresql://{self.logging_db_user}:{self.logging_db_password}@{self.logging_db_host}:{self.logging_db_port}/{self.logging_db_name}"

    @property
    def particle_access_token(self) -> Optional[str]:
        """Particle API access token."""
        return self._get_secret(
            "rtgs-particle-access-token", "PARTICLE_ACCESS_TOKEN", required=False
        )

    @property
    def GEE_PROJECT(self) -> Optional[str]:
        """Google Earth Engine Project name."""
        return self._get_secret("rtgs-gee-project", "GEE_PROJECT", required=False)

    @property
    def BUCKET_NAME(self) -> Optional[str]:
        """Google Cloud Bucket name."""
        return self._get_secret("rtgs-bucket-name", "BUCKET_NAME", required=False)

    @property
    def PL_API_KEY(self) -> Optional[str]:
        """PlanetLabs API key."""
        return self._get_secret("rtgs-pl-api-key", "PL_API_KEY", required=False)

    @property
    def logging_instance_connection_name(self) -> Optional[str]:
        """GCP Cloud SQL instance connection name for logging database."""
        return self._get_secret(
            "rtgs-logging-instance-connection-name",
            "LOGGING_INSTANCE_CONNECTION_NAME",
            required=False,
        )
