"""Data extraction functions for GEMS sensing database."""

import logging
import time
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd
from sqlalchemy import text

from ..core import DatabaseManager
from ..core.exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)


def list_projects(
    database_manager: DatabaseManager, max_retries: int = 3
) -> List[Tuple[str, int]]:
    """List all available projects with node counts.

    Args:
        database_manager: Database manager instance
        max_retries: Maximum number of retry attempts

    Returns:
        List of tuples containing (project_name, node_count)
    """
    query = """
    SELECT project, COUNT(*) as node_count 
    FROM node 
    WHERE project IS NOT NULL 
    GROUP BY project 
    ORDER BY project
    """

    for attempt in range(max_retries):
        try:
            df = database_manager.execute_query(query)
            return [(row["project"], row["node_count"]) for _, row in df.iterrows()]
        except Exception as e:
            if attempt < max_retries - 1:
                logger.error(
                    f"Project listing error (attempt {attempt+1}/{max_retries}): {e}"
                )
                logger.info(f"Retrying in {2**attempt} seconds...")
                time.sleep(2**attempt)
            else:
                logger.error(f"Failed to list projects after {max_retries} attempts")
                raise DatabaseError(f"Failed to list projects: {e}")

    return []


def get_nodes_for_project(
    database_manager: DatabaseManager, project: str
) -> pd.DataFrame:
    """Get nodes for a specific project.

    Args:
        database_manager: Database manager instance
        project: Project name

    Returns:
        DataFrame with node information
    """
    return database_manager.get_nodes_for_project(project)


def check_project_exists(
    database_manager: DatabaseManager, project: str, max_retries: int = 3
) -> Tuple[bool, List[Tuple[str, int]]]:
    """Check if a project exists and return matching projects.

    Args:
        database_manager: Database manager instance
        project: Project name to check
        max_retries: Maximum number of retry attempts

    Returns:
        Tuple of (exists, list_of_matching_projects_with_counts)
    """
    query = """
    SELECT project, COUNT(*) as node_count 
    FROM node 
    WHERE project LIKE :project
    GROUP BY project 
    ORDER BY project
    """

    for attempt in range(max_retries):
        try:
            df = database_manager.execute_query(query, {"project": f"%{project}%"})
            if df.empty:
                return False, []

            matching_projects = [
                (row["project"], row["node_count"]) for _, row in df.iterrows()
            ]
            return True, matching_projects

        except Exception as e:
            if attempt < max_retries - 1:
                logger.error(
                    f"Project check error (attempt {attempt+1}/{max_retries}): {e}"
                )
                logger.info(f"Retrying in {2**attempt} seconds...")
                time.sleep(2**attempt)
            else:
                logger.error(f"Failed to check project after {max_retries} attempts")
                raise DatabaseError(f"Failed to check project: {e}")

    return False, []


def extract_data(
    project: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    node_ids: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
    output_format: str = "csv",
    create_zip: bool = False,
    retry_count: int = 3,
    note: Optional[str] = None,
) -> dict:
    """High-level data extraction function that orchestrates the entire workflow.

    Args:
        project: Project name to query
        start_date: Start date string (YYYY-MM-DD). Defaults to 2018-01-01
        end_date: End date string (YYYY-MM-DD). Defaults to today
        node_ids: Optional list of specific node IDs to query
        output_dir: Output directory for data files (default: ./data)
        output_format: Output format ('csv' or 'parquet')
        create_zip: Create zip archive with metadata
        retry_count: Maximum retry attempts
        note: Optional note for git logging

    Returns:
        Dictionary with extraction results including file paths and metadata

    Raises:
        ValidationError: If parameters are invalid
        DatabaseError: If database operations fail
    """
    from datetime import datetime

    from ..core import Config, DatabaseManager
    from ..core.cli_utils import parse_node_ids, validate_date_format
    from ..core.exceptions import DatabaseError, ValidationError
    from .file_operations import create_zip_archive, ensure_data_directory, save_data

    # Validate and normalize dates
    if start_date is None:
        start_date = "2018-01-01"
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    validate_date_format(start_date, "start-date")
    validate_date_format(end_date, "end-date")

    # Parse node IDs if provided as string
    if isinstance(node_ids, str):
        node_ids = parse_node_ids(node_ids)

    # Initialize database connection
    config = Config()
    db_manager = DatabaseManager(config)

    if not db_manager.test_connection():
        raise DatabaseError(
            "Failed to connect to database. Please check your configuration and VPN connection."
        )

    try:
        # Extract raw data
        logger.info(f"Extracting data for project: {project}")
        df = get_raw_data(
            database_manager=db_manager,
            project=project,
            start_date=start_date,
            end_date=end_date,
            node_ids=node_ids,
            max_retries=retry_count,
        )

        if df.empty:
            logger.info("No data found for the specified parameters")
            return {
                "success": True,
                "records_extracted": 0,
                "output_file": None,
                "zip_file": None,
                "message": "No data found for the specified parameters",
            }

        # Ensure output directory
        output_directory = ensure_data_directory(output_dir)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{project.replace(' ', '_')}_{start_date}_to_{end_date}_{timestamp}"

        # Save data
        file_path = save_data(df, output_directory, filename, output_format)

        # Create zip archive if requested
        zip_path = None
        if create_zip:
            zip_path = create_zip_archive(file_path, df, output_format)

        results = {
            "success": True,
            "records_extracted": len(df),
            "output_file": str(file_path),
            "zip_file": str(zip_path) if zip_path else None,
            "project": project,
            "start_date": start_date,
            "end_date": end_date,
            "node_ids": node_ids,
            "output_format": output_format,
            "output_directory": str(output_directory),
            "create_zip": create_zip,
            "retry_count": retry_count,
            "note": note,
        }

        logger.info(f"Successfully extracted {len(df)} records to {file_path}")
        return results

    finally:
        db_manager.close()


def list_available_projects(max_retries: int = 3) -> List[Tuple[str, int]]:
    """List all available projects in the database.

    Args:
        max_retries: Maximum number of retry attempts

    Returns:
        List of tuples containing (project_name, node_count)

    Raises:
        DatabaseError: If database operations fail
    """
    from ..core import Config, DatabaseManager
    from ..core.exceptions import DatabaseError

    config = Config()
    db_manager = DatabaseManager(config)

    if not db_manager.test_connection():
        raise DatabaseError(
            "Failed to connect to database. Please check your configuration and VPN connection."
        )

    try:
        return list_projects(db_manager, max_retries)
    finally:
        db_manager.close()


def get_raw_data(
    database_manager: DatabaseManager,
    project: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    node_ids: Optional[List[str]] = None,
    max_retries: int = 3,
) -> pd.DataFrame:
    """Get raw sensor data from GEMS database.

    Args:
        database_manager: Database manager instance
        project: Project name to query
        start_date: Start date string (YYYY-MM-DD). Defaults to 2018-01-01
        end_date: End date string (YYYY-MM-DD). Defaults to today
        node_ids: Optional list of specific node IDs to query
        max_retries: Maximum number of retry attempts

    Returns:
        DataFrame with raw sensor data

    Raises:
        ValidationError: If project doesn't exist
        DatabaseError: If query fails
    """
    # Set default dates
    if start_date is None:
        start_date = "2018-01-01"
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # Validate date format
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        raise ValidationError(f"Invalid date format: {e}")

    # Check if project exists
    project_exists, matching_projects = check_project_exists(database_manager, project)

    if not project_exists:
        available_projects = list_projects(database_manager)
        if available_projects:
            # Format first 10 projects with node counts
            projects_list = [f"{p} ({c} nodes)" for p, c in available_projects[:10]]
            projects_str = ", ".join(projects_list)

            if len(available_projects) > 10:
                total_remaining_nodes = sum(
                    count for _, count in available_projects[10:]
                )
                projects_str += f", ... and {len(available_projects) - 10} more projects with {total_remaining_nodes} nodes"

            error_msg = f"Project '{project}' not found. Available projects include: {projects_str}"
        else:
            error_msg = f"Project '{project}' not found and no projects are available. Please check database connection and permissions."

        logger.error(error_msg)
        raise ValidationError(error_msg)

    # Log matching projects if multiple
    if len(matching_projects) > 1:
        logger.info(f"Multiple projects match '{project}':")
        for proj, count in matching_projects:
            logger.info(f"  - {proj} ({count} nodes)")
        logger.info(f"Using pattern '%{project}%' to match all of them")

    # Build query for raw data
    query = """
    SELECT r.id, r.node_id, r.publish_time, r.ingest_time, r.event, r.message, r.message_id
    FROM raw r
    JOIN node n ON r.node_id = n.node_id
    WHERE n.project LIKE :project
    AND r.publish_time BETWEEN :start_date AND :end_date
    """

    # Add node_id filter if specified
    params = {"project": f"%{project}%", "start_date": start_date, "end_date": end_date}

    if node_ids:
        if len(node_ids) == 1:
            query += " AND r.node_id = :node_id"
            params["node_id"] = node_ids[0]
        else:
            # Use parameterized query for multiple node IDs
            placeholders = ",".join([f":node_id_{i}" for i in range(len(node_ids))])
            query += f" AND r.node_id IN ({placeholders})"
            for i, node_id in enumerate(node_ids):
                params[f"node_id_{i}"] = node_id

    query += " ORDER BY r.publish_time"

    logger.info(
        f"Fetching raw data for project '{project}' from {start_date} to {end_date}"
    )
    if node_ids:
        logger.info(f"Filtering for nodes: {', '.join(node_ids)}")

    # Execute query with retries
    for attempt in range(max_retries):
        try:
            logger.info("Executing query...")
            df = database_manager.execute_query(query, params)

            if df.empty:
                logger.info("No data found for the specified parameters")
                return df

            logger.info(f"Successfully retrieved {len(df)} raw data records")
            return df

        except Exception as e:
            if attempt < max_retries - 1:
                logger.error(f"Query error (attempt {attempt+1}/{max_retries}): {e}")
                logger.info(f"Retrying in {2**attempt} seconds...")
                time.sleep(2**attempt)
            else:
                logger.error(f"Failed to execute query after {max_retries} attempts")
                raise DatabaseError(f"Query execution failed: {e}")

    return pd.DataFrame()
