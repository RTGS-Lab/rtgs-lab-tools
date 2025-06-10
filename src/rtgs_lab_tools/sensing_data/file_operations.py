"""File operations for sensing data export."""

import hashlib
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from ..core.exceptions import RTGSLabToolsError

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        SHA-256 hash as hexadecimal string
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def ensure_data_directory(output_dir: Optional[str] = None) -> str:
    """Ensure output directory exists.

    Args:
        output_dir: Optional output directory path. If None, uses 'data' directory.

    Returns:
        Absolute path to the output directory
    """
    if output_dir is None:
        output_dir = "data"

    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Output directory: {output_path}")
    return str(output_path)


def save_data(
    df: pd.DataFrame, directory: str, filename: str, format: str = "csv"
) -> str:
    """Save DataFrame to file with integrity verification.

    Args:
        df: DataFrame to save
        directory: Output directory
        filename: Base filename (without extension)
        format: File format ('csv' or 'parquet')

    Returns:
        Path to the saved file

    Raises:
        RTGSLabToolsError: If saving fails
    """
    if format not in ["csv", "parquet"]:
        raise RTGSLabToolsError(f"Unsupported format: {format}")

    # Determine file extension and full path
    extension = ".csv" if format == "csv" else ".parquet"
    file_path = os.path.join(directory, f"{filename}{extension}")

    try:
        logger.info(f"Saving data to {format.upper()} format...")

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=extension, dir=directory
        ) as temp:
            temp_file = temp.name

            # Write the data
            if format == "csv":
                df.to_csv(temp_file, index=False)
            else:
                df.to_parquet(temp_file, index=False)

        # Calculate hash for verification
        file_hash = calculate_file_hash(temp_file)

        # Move the temp file to the destination
        shutil.move(temp_file, file_path)
        logger.info(f"Saved data to {file_path}")
        logger.info(f"File hash (SHA-256): {file_hash}")

        return file_path

    except Exception as e:
        # Clean up temp file if it exists
        if "temp_file" in locals() and os.path.exists(temp_file):
            os.remove(temp_file)
        logger.error(f"Error saving data: {e}")
        raise RTGSLabToolsError(f"Failed to save data: {e}")


def create_zip_archive(file_path: str, df: pd.DataFrame, format: str = "csv") -> str:
    """Create zip archive with data file and metadata.

    Args:
        file_path: Path to the data file to archive
        df: DataFrame that was saved (for metadata)
        format: File format that was used

    Returns:
        Path to the created zip file

    Raises:
        RTGSLabToolsError: If zip creation fails
    """
    try:
        zip_path = f"{file_path}.zip"
        logger.info(f"Creating zip archive: {zip_path}")

        # Calculate file hash
        file_hash = calculate_file_hash(file_path)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add the data file
            zipf.write(file_path, os.path.basename(file_path))

            # Create and add metadata file
            metadata_content = f"""# GEMS Sensing Data Export Metadata
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
File: {os.path.basename(file_path)}
Format: {format.upper()}
Rows: {len(df)}
Date Range: {df['publish_time'].min() if 'publish_time' in df.columns and not df.empty else 'N/A'} to {df['publish_time'].max() if 'publish_time' in df.columns and not df.empty else 'N/A'}
SHA-256 Hash: {file_hash}
"""
            metadata_file = f"{file_path}.metadata.txt"
            with open(metadata_file, "w") as f:
                f.write(metadata_content)

            zipf.write(metadata_file, os.path.basename(metadata_file))

        # Clean up temporary metadata file
        if os.path.exists(metadata_file):
            os.remove(metadata_file)

        logger.info(f"Created zip archive: {zip_path}")
        return zip_path

    except Exception as e:
        logger.error(f"Error creating zip archive: {e}")
        raise RTGSLabToolsError(f"Failed to create zip archive: {e}")
