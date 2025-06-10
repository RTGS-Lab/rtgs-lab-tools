"""Tests for data extraction functions."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from rtgs_lab_tools.core.exceptions import DatabaseError, ValidationError
from rtgs_lab_tools.sensing_data.data_extractor import (
    check_project_exists,
    get_nodes_for_project,
    get_raw_data,
    list_projects,
)


def test_list_projects(mock_database_manager, sample_projects):
    """Test listing projects."""
    mock_database_manager.execute_query.return_value = pd.DataFrame(
        {
            "project": [p[0] for p in sample_projects],
            "node_count": [p[1] for p in sample_projects],
        }
    )

    result = list_projects(mock_database_manager)

    assert len(result) == 4
    assert result[0] == ("Winter Turf", 5)
    assert result[1] == ("Summer Crops", 8)


def test_check_project_exists(mock_database_manager):
    """Test checking if project exists."""
    # Test existing project
    mock_database_manager.execute_query.return_value = pd.DataFrame(
        {"project": ["Winter Turf"], "node_count": [5]}
    )

    exists, matches = check_project_exists(mock_database_manager, "Winter")

    assert exists is True
    assert len(matches) == 1
    assert matches[0] == ("Winter Turf", 5)

    # Test non-existing project
    mock_database_manager.execute_query.return_value = pd.DataFrame()

    exists, matches = check_project_exists(mock_database_manager, "NonExistent")

    assert exists is False
    assert len(matches) == 0


def test_get_raw_data_success(mock_database_manager, sample_raw_data):
    """Test successful data extraction."""
    # Mock project check
    with patch(
        "rtgs_lab_tools.sensing_data.data_extractor.check_project_exists"
    ) as mock_check:
        mock_check.return_value = (True, [("Test Project", 5)])

        result = get_raw_data(
            database_manager=mock_database_manager,
            project="Test Project",
            start_date="2023-01-01",
            end_date="2023-01-02",
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        assert "node_id" in result.columns
        assert "publish_time" in result.columns


def test_get_raw_data_invalid_dates(mock_database_manager):
    """Test data extraction with invalid dates."""
    with pytest.raises(ValidationError, match="Invalid date format"):
        get_raw_data(
            database_manager=mock_database_manager,
            project="Test Project",
            start_date="invalid-date",
            end_date="2023-01-02",
        )


def test_get_raw_data_project_not_found(mock_database_manager):
    """Test data extraction with non-existent project."""
    with patch(
        "rtgs_lab_tools.sensing_data.data_extractor.check_project_exists"
    ) as mock_check:
        mock_check.return_value = (False, [])

        with patch(
            "rtgs_lab_tools.sensing_data.data_extractor.list_projects"
        ) as mock_list:
            mock_list.return_value = [("Other Project", 3)]

            with pytest.raises(
                ValidationError, match="Project 'NonExistent' not found"
            ):
                get_raw_data(
                    database_manager=mock_database_manager, project="NonExistent"
                )


def test_get_raw_data_with_node_filter(mock_database_manager, sample_raw_data):
    """Test data extraction with node ID filter."""
    with patch(
        "rtgs_lab_tools.sensing_data.data_extractor.check_project_exists"
    ) as mock_check:
        mock_check.return_value = (True, [("Test Project", 5)])

        # Filter to specific nodes
        filtered_data = sample_raw_data[
            sample_raw_data["node_id"].isin(["node_001", "node_002"])
        ]
        mock_database_manager.execute_query.return_value = filtered_data

        result = get_raw_data(
            database_manager=mock_database_manager,
            project="Test Project",
            node_ids=["node_001", "node_002"],
        )

        assert len(result) == 4  # Only records from node_001 and node_002
        unique_nodes = result["node_id"].unique()
        assert "node_001" in unique_nodes
        assert "node_002" in unique_nodes
        assert "node_003" not in unique_nodes


def test_get_raw_data_empty_result(mock_database_manager):
    """Test data extraction with no results."""
    with patch(
        "rtgs_lab_tools.sensing_data.data_extractor.check_project_exists"
    ) as mock_check:
        mock_check.return_value = (True, [("Test Project", 5)])

        mock_database_manager.execute_query.return_value = pd.DataFrame()

        result = get_raw_data(
            database_manager=mock_database_manager, project="Test Project"
        )

        assert result.empty


def test_get_nodes_for_project(mock_database_manager):
    """Test getting nodes for a project."""
    result = get_nodes_for_project(mock_database_manager, "Test Project")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert "node_id" in result.columns
    assert "project" in result.columns
