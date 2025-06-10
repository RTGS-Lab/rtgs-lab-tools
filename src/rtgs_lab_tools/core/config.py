"""Configuration management for RTGS Lab Tools."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .exceptions import ConfigError


class Config:
    """Configuration manager for RTGS Lab Tools."""

    def __init__(self, env_file: Optional[str] = None):
        """Initialize configuration.

        Args:
            env_file: Path to .env file. If None, looks for .env in current directory.
        """
        if env_file:
            env_path = Path(env_file)
        else:
            env_path = Path.cwd() / ".env"

        if env_path.exists():
            load_dotenv(env_path)

    @property
    def db_host(self) -> str:
        """Database host."""
        host = os.getenv("DB_HOST")
        if not host:
            raise ConfigError("DB_HOST not found in environment variables")
        return host

    @property
    def db_port(self) -> int:
        """Database port."""
        port = os.getenv("DB_PORT", "5432")
        try:
            return int(port)
        except ValueError:
            raise ConfigError(f"Invalid DB_PORT value: {port}")

    @property
    def db_name(self) -> str:
        """Database name."""
        name = os.getenv("DB_NAME")
        if not name:
            raise ConfigError("DB_NAME not found in environment variables")
        return name

    @property
    def db_user(self) -> str:
        """Database user."""
        user = os.getenv("DB_USER")
        if not user:
            raise ConfigError("DB_USER not found in environment variables")
        return user

    @property
    def db_password(self) -> str:
        """Database password."""
        password = os.getenv("DB_PASSWORD")
        if not password:
            raise ConfigError("DB_PASSWORD not found in environment variables")
        return password

    @property
    def db_url(self) -> str:
        """Complete database URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def particle_access_token(self) -> Optional[str]:
        """Particle API access token."""
        return os.getenv("PARTICLE_ACCESS_TOKEN")

    @property
    def cds_api_key(self) -> Optional[str]:
        """Copernicus CDS API key."""
        return os.getenv("CDS_API_KEY")
