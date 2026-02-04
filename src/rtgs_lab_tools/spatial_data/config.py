"""
Configuration management for spatial_data module.

Supports three operational modes:
- built-in: Use web-sourced datasets with database logging
- local: Use user's flat files without database
- hybrid: Mix built-in and local datasets
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Literal
import yaml


ModeType = Literal["built-in", "local", "hybrid"]


@dataclass
class DataConfig:
    """Configuration for data sources."""

    local_directory: Optional[str] = None
    cache_directory: Optional[str] = ".rtgs_cache"
    sources: List[str] = field(default_factory=lambda: ["mn_geospatial", "fgdb"])
    local_prefix: str = "local"  # Prefix for local datasets in hybrid mode

    def get_local_directory(self) -> Optional[Path]:
        """Get local directory as Path object."""
        if self.local_directory:
            return Path(self.local_directory).expanduser().resolve()
        return None

    def get_cache_directory(self) -> Path:
        """Get cache directory as Path object."""
        return Path(self.cache_directory).expanduser().resolve()


@dataclass
class DatabaseConfig:
    """Configuration for database logging."""

    logging_enabled: bool = True
    connection_string: Optional[str] = None

    def __post_init__(self):
        """Load connection string from environment if not provided."""
        if self.connection_string is None:
            self.connection_string = os.getenv("RTGS_DB_CONNECTION_STRING")


@dataclass
class OutputConfig:
    """Configuration for output preferences."""

    default_format: str = "geoparquet"
    default_directory: str = "./data"

    def get_default_directory(self) -> Path:
        """Get default output directory as Path object."""
        return Path(self.default_directory).expanduser().resolve()


@dataclass
class SpatialDataConfig:
    """Main configuration for spatial_data module."""

    mode: ModeType = "built-in"
    data: DataConfig = field(default_factory=DataConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def from_dict(cls, config_dict: dict) -> "SpatialDataConfig":
        """Create configuration from dictionary."""
        return cls(
            mode=config_dict.get("mode", "built-in"),
            data=DataConfig(**config_dict.get("data", {})),
            database=DatabaseConfig(**config_dict.get("database", {})),
            output=OutputConfig(**config_dict.get("output", {}))
        )

    @classmethod
    def from_yaml(cls, config_path: Path) -> "SpatialDataConfig":
        """Load configuration from YAML file."""
        with open(config_path, "r") as f:
            config_dict = yaml.safe_load(f)
        return cls.from_dict(config_dict)

    def to_yaml(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        config_dict = {
            "mode": self.mode,
            "data": {
                "local_directory": self.data.local_directory,
                "cache_directory": self.data.cache_directory,
                "sources": self.data.sources,
                "local_prefix": self.data.local_prefix,
            },
            "database": {
                "logging_enabled": self.database.logging_enabled,
            },
            "output": {
                "default_format": self.output.default_format,
                "default_directory": self.output.default_directory,
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    def validate(self) -> None:
        """Validate configuration."""
        if self.mode not in ["built-in", "local", "hybrid"]:
            raise ValueError(f"Invalid mode: {self.mode}. Must be 'built-in', 'local', or 'hybrid'")

        if self.mode in ["local", "hybrid"]:
            if not self.data.local_directory:
                raise ValueError(f"Mode '{self.mode}' requires data.local_directory to be set")

            local_dir = self.data.get_local_directory()
            if not local_dir.exists():
                raise ValueError(f"Local directory does not exist: {local_dir}")

        if self.output.default_format not in ["geoparquet", "shapefile", "geojson", "csv"]:
            raise ValueError(f"Invalid output format: {self.output.default_format}")


# Global configuration instance
_config: Optional[SpatialDataConfig] = None


def load_config(config_path: Optional[Path] = None) -> SpatialDataConfig:
    """
    Load configuration from file or create default.

    Search order:
    1. Provided config_path
    2. .rtgs-config.yaml in current directory
    3. .rtgs-config.yaml in user home directory
    4. Default configuration

    Args:
        config_path: Optional path to configuration file

    Returns:
        SpatialDataConfig instance
    """
    global _config

    # Return cached config if already loaded
    if _config is not None:
        return _config

    # Search for config file
    search_paths = []

    if config_path:
        search_paths.append(config_path)

    search_paths.extend([
        Path.cwd() / ".rtgs-config.yaml",
        Path.home() / ".rtgs-config.yaml",
    ])

    for path in search_paths:
        if path.exists():
            _config = SpatialDataConfig.from_yaml(path)
            _config.validate()
            return _config

    # No config file found, use defaults
    _config = SpatialDataConfig()
    return _config


def get_config() -> SpatialDataConfig:
    """Get current configuration, loading if necessary."""
    return load_config()


def set_config(config: SpatialDataConfig) -> None:
    """Set global configuration."""
    global _config
    config.validate()
    _config = config


def reset_config() -> None:
    """Reset configuration to force reload."""
    global _config
    _config = None
