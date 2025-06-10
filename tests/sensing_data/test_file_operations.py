"""Tests for file operations."""

import os
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from rtgs_lab_tools.core.exceptions import RTGSLabToolsError
from rtgs_lab_tools.sensing_data.file_operations import (
    calculate_file_hash,
    create_zip_archive,
    ensure_data_directory,
    save_data,
)


def test_save_data_csv(sample_raw_data, temp_output_dir):
    """Test saving data as CSV."""
    file_path = save_data(
        df=sample_raw_data,
        directory=temp_output_dir,
        filename="test_data",
        format="csv",
    )

    assert os.path.exists(file_path)
    assert file_path.endswith(".csv")

    # Verify data integrity
    loaded_df = pd.read_csv(file_path)
    assert len(loaded_df) == len(sample_raw_data)
    assert list(loaded_df.columns) == list(sample_raw_data.columns)


def test_save_data_parquet(sample_raw_data, temp_output_dir):
    """Test saving data as Parquet."""
    file_path = save_data(
        df=sample_raw_data,
        directory=temp_output_dir,
        filename="test_data",
        format="parquet",
    )

    assert os.path.exists(file_path)
    assert file_path.endswith(".parquet")

    # Verify data integrity
    loaded_df = pd.read_parquet(file_path)
    assert len(loaded_df) == len(sample_raw_data)
    assert list(loaded_df.columns) == list(sample_raw_data.columns)


def test_save_data_invalid_format(sample_raw_data, temp_output_dir):
    """Test saving data with invalid format."""
    with pytest.raises(RTGSLabToolsError, match="Unsupported format"):
        save_data(
            df=sample_raw_data,
            directory=temp_output_dir,
            filename="test_data",
            format="invalid",
        )


def test_calculate_file_hash(temp_output_dir):
    """Test file hash calculation."""
    # Create a test file
    test_file = os.path.join(temp_output_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    hash1 = calculate_file_hash(test_file)
    hash2 = calculate_file_hash(test_file)

    # Same file should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 produces 64-character hex string

    # Different content should produce different hash
    with open(test_file, "w") as f:
        f.write("different content")

    hash3 = calculate_file_hash(test_file)
    assert hash1 != hash3


def test_ensure_data_directory():
    """Test directory creation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test creating subdirectory
        new_dir = os.path.join(temp_dir, "new_subdir")
        result_dir = ensure_data_directory(new_dir)

        assert os.path.exists(result_dir)
        assert os.path.isdir(result_dir)
        assert result_dir == str(Path(new_dir).resolve())


def test_create_zip_archive(sample_raw_data, temp_output_dir):
    """Test creating zip archive."""
    # First save data
    file_path = save_data(
        df=sample_raw_data,
        directory=temp_output_dir,
        filename="test_data",
        format="csv",
    )

    # Create zip archive
    zip_path = create_zip_archive(file_path, sample_raw_data, "csv")

    assert os.path.exists(zip_path)
    assert zip_path.endswith(".zip")

    # Verify zip contents
    with zipfile.ZipFile(zip_path, "r") as zipf:
        file_list = zipf.namelist()

        # Should contain data file and metadata
        assert "test_data.csv" in file_list
        assert "test_data.csv.metadata.txt" in file_list

        # Check metadata content
        metadata_content = zipf.read("test_data.csv.metadata.txt").decode("utf-8")
        assert "GEMS Sensing Data Export Metadata" in metadata_content
        assert "CSV" in metadata_content
        assert f"Rows: {len(sample_raw_data)}" in metadata_content
        assert "SHA-256 Hash:" in metadata_content


def test_create_zip_archive_empty_dataframe(temp_output_dir):
    """Test creating zip archive with empty DataFrame."""
    empty_df = pd.DataFrame()

    # Save empty data
    file_path = save_data(
        df=empty_df, directory=temp_output_dir, filename="empty_data", format="csv"
    )

    # Create zip archive
    zip_path = create_zip_archive(file_path, empty_df, "csv")

    assert os.path.exists(zip_path)

    # Verify metadata handles empty data gracefully
    with zipfile.ZipFile(zip_path, "r") as zipf:
        metadata_content = zipf.read("empty_data.csv.metadata.txt").decode("utf-8")
        assert "Rows: 0" in metadata_content
        assert "Date Range: N/A to N/A" in metadata_content
