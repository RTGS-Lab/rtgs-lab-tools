"""Tests for configuration management."""

import os
from unittest.mock import Mock, patch

import pytest

from rtgs_lab_tools.core import Config
from rtgs_lab_tools.core.exceptions import ConfigError


def test_config_from_env_file(temp_env_file):
    """Test configuration loading from .env file."""
    # Mock Secret Manager to return None so it falls back to env vars
    mock_client = Mock()
    mock_client.get_secret.return_value = None
    with patch(
        "rtgs_lab_tools.core.config.get_secret_manager_client", return_value=mock_client
    ):
        config = Config(temp_env_file)

        assert config.db_host == "test-host"
        assert config.db_port == 5432
        assert config.db_name == "test_db"
        assert config.db_user == "test_user"
        assert config.db_password == "test_password"
        assert config.particle_access_token == "test_token"


def test_config_missing_required_vars():
    """Test configuration with missing required variables."""
    with patch.dict(os.environ, {}, clear=True):
        mock_client = Mock()
        mock_client.get_secret.return_value = None
        with patch(
            "rtgs_lab_tools.core.config.get_secret_manager_client",
            return_value=mock_client,
        ):
            # Pass a non-existent env file to prevent loading from existing .env
            config = Config(env_file="/nonexistent/.env")

            with pytest.raises(ConfigError, match="DB_HOST not found"):
                _ = config.db_host


def test_config_invalid_port():
    """Test configuration with invalid port."""
    with patch.dict(os.environ, {"DB_PORT": "invalid_port"}):
        mock_client = Mock()
        mock_client.get_secret.return_value = None
        with patch(
            "rtgs_lab_tools.core.config.get_secret_manager_client",
            return_value=mock_client,
        ):
            config = Config()

            with pytest.raises(ConfigError, match="Invalid DB_PORT value"):
                _ = config.db_port


def test_config_db_url(temp_env_file):
    """Test database URL generation."""
    mock_client = Mock()
    mock_client.get_secret.return_value = None
    with patch(
        "rtgs_lab_tools.core.config.get_secret_manager_client", return_value=mock_client
    ):
        config = Config(temp_env_file)

        expected_url = "postgresql://test_user:test_password@test-host:5432/test_db"
        assert config.db_url == expected_url


def test_config_optional_values():
    """Test optional configuration values."""
    with patch.dict(os.environ, {}, clear=True):
        mock_client = Mock()
        mock_client.get_secret.return_value = None
        with patch(
            "rtgs_lab_tools.core.config.get_secret_manager_client",
            return_value=mock_client,
        ):
            # Pass a non-existent env file to prevent loading from existing .env
            config = Config(env_file="/nonexistent/.env")

            assert config.particle_access_token is None
