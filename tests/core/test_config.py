"""Tests for configuration management."""

import os
import pytest

from rtgs_lab_tools.core import Config
from rtgs_lab_tools.core.exceptions import ConfigError


def test_config_from_env_file(temp_env_file):
    """Test configuration loading from .env file."""
    config = Config(temp_env_file)
    
    assert config.db_host == "test-host"
    assert config.db_port == 5432
    assert config.db_name == "test_db"
    assert config.db_user == "test_user"
    assert config.db_password == "test_password"
    assert config.particle_access_token == "test_token"
    assert config.cds_api_key == "test_cds_key"


def test_config_missing_required_vars():
    """Test configuration with missing required variables."""
    # Clear environment
    for var in ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']:
        if var in os.environ:
            del os.environ[var]
    
    config = Config()
    
    with pytest.raises(ConfigError, match="DB_HOST not found"):
        _ = config.db_host


def test_config_invalid_port():
    """Test configuration with invalid port."""
    os.environ['DB_PORT'] = 'invalid_port'
    
    config = Config()
    
    with pytest.raises(ConfigError, match="Invalid DB_PORT value"):
        _ = config.db_port
    
    # Clean up
    del os.environ['DB_PORT']


def test_config_db_url(temp_env_file):
    """Test database URL generation."""
    config = Config(temp_env_file)
    
    expected_url = "postgresql://test_user:test_password@test-host:5432/test_db"
    assert config.db_url == expected_url


def test_config_optional_values():
    """Test optional configuration values."""
    # Clear optional environment variables
    for var in ['PARTICLE_ACCESS_TOKEN', 'CDS_API_KEY']:
        if var in os.environ:
            del os.environ[var]
    
    config = Config()
    
    assert config.particle_access_token is None
    assert config.cds_api_key is None