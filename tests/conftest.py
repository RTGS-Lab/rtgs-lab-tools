"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from rtgs_lab_tools.core import Config, DatabaseManager


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = Mock(spec=Config)
    config.db_host = "test-host"
    config.db_port = 5432
    config.db_name = "test_db"
    config.db_user = "test_user"
    config.db_password = "test_password"
    config.db_url = "postgresql://test_user:test_password@test-host:5432/test_db"
    config.particle_access_token = "test_token"
    config.cds_api_key = "test_cds_key"
    return config


@pytest.fixture
def temp_env_file():
    """Create temporary .env file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write(
            """DB_HOST=test-host
DB_PORT=5432
DB_NAME=test_db
DB_USER=test_user
DB_PASSWORD=test_password
PARTICLE_ACCESS_TOKEN=test_token
CDS_API_KEY=test_cds_key
"""
        )
        temp_path = f.name

    yield temp_path

    # Clean up
    os.unlink(temp_path)


@pytest.fixture
def sample_raw_data():
    """Sample raw sensor data for testing."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "node_id": ["node_001", "node_001", "node_002", "node_002", "node_003"],
            "publish_time": pd.to_datetime(
                [
                    "2023-01-01 10:00:00",
                    "2023-01-01 11:00:00",
                    "2023-01-01 10:30:00",
                    "2023-01-01 11:30:00",
                    "2023-01-01 12:00:00",
                ]
            ),
            "ingest_time": pd.to_datetime(
                [
                    "2023-01-01 10:01:00",
                    "2023-01-01 11:01:00",
                    "2023-01-01 10:31:00",
                    "2023-01-01 11:31:00",
                    "2023-01-01 12:01:00",
                ]
            ),
            "event": [
                "temperature",
                "humidity",
                "temperature",
                "humidity",
                "temperature",
            ],
            "message": [
                '{"temp": 22.5}',
                '{"humidity": 65}',
                '{"temp": 23.1}',
                '{"humidity": 62}',
                '{"temp": 21.8}',
            ],
            "message_id": ["msg_001", "msg_002", "msg_003", "msg_004", "msg_005"],
        }
    )


@pytest.fixture
def sample_projects():
    """Sample project data for testing."""
    return [
        ("Winter Turf", 5),
        ("Summer Crops", 8),
        ("Forest Monitoring", 12),
        ("Urban Heat", 3),
    ]


@pytest.fixture
def mock_database_manager(mock_config, sample_raw_data, sample_projects):
    """Mock database manager for testing."""
    db_manager = Mock(spec=DatabaseManager)
    db_manager.config = mock_config
    db_manager.test_connection.return_value = True
    db_manager.execute_query.return_value = sample_raw_data
    db_manager.get_projects.return_value = [p[0] for p in sample_projects]
    db_manager.get_nodes_for_project.return_value = pd.DataFrame(
        {
            "node_id": ["node_001", "node_002", "node_003"],
            "project": ["Test Project", "Test Project", "Test Project"],
            "location": ["Site A", "Site B", "Site C"],
            "latitude": [44.9778, 44.9779, 44.9780],
            "longitude": [-93.2650, -93.2651, -93.2652],
            "deployment_date": pd.to_datetime(
                ["2023-01-01", "2023-01-02", "2023-01-03"]
            ),
        }
    )
    return db_manager


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir
