#!/usr/bin/env python3
"""
GEMS Sensing Data Access Tool

This script pulls raw data by project, start date, and end date from the GEMS Sensing database.
"""
import os
import sys
import argparse
import tempfile
import shutil
import hashlib
import time
import logging
import zipfile
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
    import sqlalchemy
    from sqlalchemy import create_engine, text
    from dotenv import load_dotenv
except ImportError:
    print("Required libraries not installed.")
    print("Please install them with: pip install pandas sqlalchemy python-dotenv")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def setup_credentials():
    """
    Set up the .env file with credentials template.
    Provides instructions to the user for editing the file
    and obtaining credentials.
    """
    env_path = os.path.join(os.getcwd(), '.env')
    
    # Check if .env already exists
    if os.path.exists(env_path):
        logger.warning(f".env file already exists at {env_path}")
        overwrite = input("Do you want to overwrite it? (y/N): ")
        if overwrite.lower() != 'y':
            logger.info("Keeping existing .env file.")
            return
    
    # Create template .env file
    template = """# GEMS Sensing Database Credentials
# Contact Bryan Runck (runck014@umn.edu) for access credentials

# Database connection settings
DB_HOST=sensing-0.msi.umn.edu
DB_PORT=5433
DB_NAME=gems
DB_USER=your_username
DB_PASSWORD=your_password
"""
    
    # Write the template to .env file
    with open(env_path, 'w') as f:
        f.write(template)
    
    # Make sure permissions are secure for credentials file
    try:
        os.chmod(env_path, 0o600)  # User read/write only
    except Exception as e:
        logger.warning(f"Could not set secure permissions on .env file: {e}")
    
    logger.info(f"Created .env template at {env_path}")
    logger.info("\nINSTRUCTIONS:")
    logger.info("1. Edit the .env file with your database credentials using a text editor:")
    logger.info(f"   - nano {env_path}")
    logger.info(f"   - vim {env_path}")
    logger.info(f"   - vi {env_path}")
    logger.info("2. Replace 'your_username' and 'your_password' with your actual credentials")
    logger.info("3. Save the file and exit the editor")
    logger.info("\nNOTE: If you don't have credentials, contact Bryan Runck (runck014@umn.edu) for access.")
    logger.info("The .env file is in the .gitignore list, so it won't be committed to the repository.")

def load_credentials_from_env():
    """Load GEMS Sensing database credentials from .env file."""
    env_path = os.path.join(os.getcwd(), '.env')
    
    # Check if .env file exists
    if not os.path.exists(env_path):
        logger.error(f".env file not found at {env_path}")
        logger.info("Run 'python get_sensing_data.py --setup-credentials' to create a template .env file")
        raise FileNotFoundError(f".env file not found. Please run --setup-credentials first.")
    
    load_dotenv()
    
    required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Check for default values that should be changed
    if os.getenv('DB_USER') == 'your_username' or os.getenv('DB_PASSWORD') == 'your_password':
        raise ValueError("Default credentials detected in .env file. Please update with real credentials.")
    
    return {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT'),
        'db': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'pass': os.getenv('DB_PASSWORD')
    }

def create_engine_from_credentials(creds):
    """Create SQLAlchemy engine from credentials."""
    db_url = f"postgresql://{creds['user']}:{creds['pass']}@{creds['host']}:{creds['port']}/{creds['db']}"
    try:
        engine = create_engine(db_url)
        
        # Test the connection to catch configuration issues early
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            
        return engine
    except Exception as e:
        # Provide helpful error messages based on the exception
        error_msg = str(e).lower()
        
        if "could not connect to server" in error_msg or "connection refused" in error_msg:
            logger.error("\n========== CONNECTION ERROR ==========")
            logger.error("Failed to connect to the database at %s:%s", creds['host'], creds['port'])
            logger.error("This is likely because you are not connected to the UMN VPN.")
            logger.error("\nTo resolve this issue:")
            logger.error("1. Install the UMN VPN client from: https://it.umn.edu/services-technologies/virtual-private-network-vpn")
            logger.error("2. Connect to the UMN VPN using your UMN credentials")
            logger.error("3. Try running this tool again")
            logger.error("\nFor VPN help, contact UMN Technology Help at 612-301-4357 or visit:")
            logger.error("https://it.umn.edu/services-technologies/virtual-private-network-vpn")
            logger.error("======================================\n")
        elif "password authentication failed" in error_msg:
            logger.error("\n========== AUTHENTICATION ERROR ==========")
            logger.error("The username or password in your .env file is incorrect.")
            logger.error("Please check your credentials and try again.")
            logger.error("To update your credentials, run: python get_sensing_data.py --setup-credentials")
            logger.error("For credential access, contact Bryan Runck at runck014@umn.edu")
            logger.error("===========================================\n")
        elif "database" in error_msg and "does not exist" in error_msg:
            logger.error("\n========== DATABASE ERROR ==========")
            logger.error("The specified database '%s' does not exist.", creds['db'])
            logger.error("Please check your database name in the .env file.")
            logger.error("For help, contact Bryan Runck at runck014@umn.edu")
            logger.error("====================================\n")
        else:
            logger.error("\n========== DATABASE ERROR ==========")
            logger.error("An error occurred while connecting to the database:")
            logger.error(str(e))
            logger.error("\nPossible solutions:")
            logger.error("1. Make sure you are connected to the UMN VPN")
            logger.error("2. Check your credentials in the .env file")
            logger.error("3. Contact Bryan Runck at runck014@umn.edu for assistance")
            logger.error("====================================\n")
        
        # Re-raise the exception with a more informative message
        raise ConnectionError(f"Database connection failed. See log for details. Original error: {e}") from e

def ensure_data_directory(output_dir=None):
    """Ensure that data directory exists, create if needed."""
    if output_dir:
        data_dir = output_dir
    else:
        # Use ./data as default directory
        data_dir = os.path.join(os.getcwd(), "data")
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.info(f"Created data directory: {data_dir}")
    
    return data_dir

def check_project_exists(engine, project, max_retries=3):
    """
    Check if a project exists in the database.
    
    Args:
        engine: SQLAlchemy engine
        project: Project name to check
        max_retries: Maximum number of retry attempts
        
    Returns:
        tuple: (exists, matching_projects) - Boolean indicating if project exists and list of tuples (project_name, node_count)
    """
    query = """
    SELECT project, COUNT(DISTINCT node_id) as node_count
    FROM node 
    WHERE project LIKE :project
    GROUP BY project
    ORDER BY project
    """
    
    with engine.connect() as conn:
        with conn.begin():
            for attempt in range(max_retries):
                try:
                    result = conn.execute(
                        text(query),
                        {"project": f"%{project}%"}
                    )
                    matching_projects = [(row[0], row[1]) for row in result.fetchall()]
                    return len(matching_projects) > 0, matching_projects
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.error(f"Project check error (attempt {attempt+1}/{max_retries}): {e}")
                        logger.info(f"Retrying in {2**attempt} seconds...")
                        time.sleep(2**attempt)
                    else:
                        logger.error(f"Failed to check project existence after {max_retries} attempts")
                        raise
    
    return False, []

def list_available_projects(engine, max_retries=3):
    """
    List all available projects in the database along with node counts.
    
    Args:
        engine: SQLAlchemy engine
        max_retries: Maximum number of retry attempts
        
    Returns:
        list of tuples: (project_name, node_count)
    """
    query = """
    SELECT project, COUNT(DISTINCT node_id) as node_count
    FROM node
    GROUP BY project
    ORDER BY project
    """
    
    with engine.connect() as conn:
        with conn.begin():
            for attempt in range(max_retries):
                try:
                    result = conn.execute(text(query))
                    return [(row[0], row[1]) for row in result.fetchall()]
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.error(f"Project listing error (attempt {attempt+1}/{max_retries}): {e}")
                        logger.info(f"Retrying in {2**attempt} seconds...")
                        time.sleep(2**attempt)
                    else:
                        logger.error(f"Failed to list projects after {max_retries} attempts")
                        raise
    
    return []

def get_raw_data(engine, project, node_ids=None, start_date=None, end_date=None, max_retries=3):
    """
    Get raw data for a specific project.
    
    Args:
        engine: SQLAlchemy engine
        project: Project name to query
        node_ids: Optional list of specific node IDs to query
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        max_retries: Maximum number of retry attempts for failed queries
        
    Returns:
        DataFrame with raw data
    """
    if start_date is None:
        start_date = "2018-01-01"
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    # First check if the project exists
    project_exists, matching_projects = check_project_exists(engine, project)
    
    if not project_exists:
        available_projects = list_available_projects(engine)
        if available_projects:
            # Format first 10 projects with node counts
            projects_list = [f"{p} ({c} nodes)" for p, c in available_projects[:10]]
            projects_str = ", ".join(projects_list)
            
            if len(available_projects) > 10:
                total_remaining_nodes = sum(count for _, count in available_projects[10:])
                projects_str += f", ... and {len(available_projects) - 10} more projects with {total_remaining_nodes} nodes"
            
            error_msg = f"Project '{project}' not found. Available projects include: {projects_str}"
        else:
            error_msg = f"Project '{project}' not found and no projects are available. Please check database connection and permissions."
        
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # If there are multiple matching projects, log them with node counts
    if len(matching_projects) > 1:
        projects_with_counts = [f"{p} ({c} nodes)" for p, c in matching_projects]
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
    if node_ids:
        if len(node_ids) == 1:
            query += f" AND r.node_id = '{node_ids[0]}'"
        else:
            node_id_list = "','".join(node_ids)
            query += f" AND r.node_id IN ('{node_id_list}')"
    
    query += " ORDER BY r.publish_time"
    
    logger.info(f"Fetching raw data for project '{project}' from {start_date} to {end_date}")
    if node_ids:
        logger.info(f"Filtering for nodes: {', '.join(node_ids)}")
    
    with engine.connect() as conn:
        with conn.begin():
            for attempt in range(max_retries):
                try:
                    logger.info("Executing query...")
                    result = conn.execute(
                        text(query),
                        {"project": f"%{project}%", "start_date": start_date, "end_date": end_date}
                    )
                    
                    # Fetch results and convert to DataFrame
                    data = result.fetchall()
                    if not data:
                        logger.info("No data found for the specified parameters")
                        return pd.DataFrame()
                    
                    df = pd.DataFrame(data, columns=result.keys())
                    logger.info(f"Successfully retrieved {len(df)} raw data records")
                    return df
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.error(f"Query error (attempt {attempt+1}/{max_retries}): {e}")
                        logger.info(f"Retrying in {2**attempt} seconds...")
                        time.sleep(2**attempt)  # Exponential backoff
                    else:
                        logger.error(f"Failed to execute query after {max_retries} attempts")
                        raise

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def save_data(df, directory, filename, format='csv', create_zip=False):
    """Save DataFrame to file with integrity verification."""
    # Determine file extension and full path
    extension = '.csv' if format == 'csv' else '.parquet'
    file_path = os.path.join(directory, f"{filename}{extension}")
    
    try:
        logger.info(f"Saving data to {format.upper()} format...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension, dir=directory) as temp:
            temp_file = temp.name
            
            # Write the data
            if format == 'csv':
                df.to_csv(temp_file, index=False)
            else:
                df.to_parquet(temp_file, index=False)
        
        # Calculate hash for verification
        file_hash = calculate_file_hash(temp_file)
        
        # Move the temp file to the destination
        shutil.move(temp_file, file_path)
        logger.info(f"Saved data to {file_path}")
        
        # Create zip archive if requested
        if create_zip:
            zip_path = f"{file_path}.zip"
            logger.info(f"Creating zip archive: {zip_path}")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add the data file
                zipf.write(file_path, os.path.basename(file_path))
                
                # Create and add metadata file
                metadata_content = f"""# GEMS Sensing Data Export Metadata
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
File: {os.path.basename(file_path)}
Format: {format.upper()}
Rows: {len(df)}
Date Range: {df['publish_time'].min()} to {df['publish_time'].max() if 'publish_time' in df.columns else 'N/A'}
SHA-256 Hash: {file_hash}
"""
                metadata_file = f"{file_path}.metadata.txt"
                with open(metadata_file, 'w') as f:
                    f.write(metadata_content)
                
                zipf.write(metadata_file, os.path.basename(metadata_file))
            
            # Clean up temporary files
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
                
            logger.info(f"Created zip archive: {zip_path}")
            return zip_path
            
        return file_path
        
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        raise

def main():
    """Main function to pull GEMS Sensing data."""
    parser = argparse.ArgumentParser(description="Pull raw data from GEMS Sensing database")
    parser.add_argument("--project", help="Project name to query")
    parser.add_argument("--list-projects", action="store_true", help="List all available projects and exit")
    parser.add_argument("--setup-credentials", action="store_true", help="Create a template .env file for database credentials")
    parser.add_argument("--start-date", default="2018-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=None, help="End date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--node-id", help="Comma-separated list of node IDs to query")
    parser.add_argument("--output-dir", default=None, help="Output directory for data files")
    parser.add_argument("--output", choices=["csv", "parquet"], default="csv", help="Output file format")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--retry-count", type=int, default=3, help="Maximum number of retry attempts")
    parser.add_argument("--zip", action="store_true", help="Create a zip archive of the output files")
    
    args = parser.parse_args()
    
    # Set verbose logging if needed
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=== GEMS Sensing Data Extraction ===")
    
    # Handle setup-credentials command
    if args.setup_credentials:
        logger.info("Setting up credentials template...")
        setup_credentials()
        return 0
    
    try:
        # Load credentials
        logger.info("Step 1: Loading credentials...")
        try:
            creds = load_credentials_from_env()
            logger.info("✓ Credentials loaded successfully")
        except FileNotFoundError as e:
            logger.error(str(e))
            logger.info("Run with --setup-credentials to create the .env file")
            return 1
        except ValueError as e:
            logger.error(str(e))
            logger.info("Please edit your .env file with valid credentials")
            logger.info("For access credentials, contact Bryan Runck (runck014@umn.edu)")
            return 1
        
        # Create database engine
        logger.info("Step 2: Establishing database connection...")
        try:
            engine = create_engine_from_credentials(creds)
            logger.info("✓ Database connection established")
        except ConnectionError as e:
            # ConnectionError already has detailed messages from create_engine_from_credentials
            return 1
        
        # If list-projects flag is set, show available projects and exit
        if args.list_projects:
            logger.info("Listing all available projects...")
            projects = list_available_projects(engine)
            
            if projects:
                logger.info("\nAvailable projects:")
                # Find the length of the longest project name for alignment
                max_name_length = max(len(project[0]) for project in projects)
                
                for i, (project, node_count) in enumerate(projects, 1):
                    # Format with padding for alignment
                    logger.info(f"{i:3}. {project:{max_name_length}} - {node_count} nodes")
                
                # Calculate total nodes
                total_nodes = sum(count for _, count in projects)
                logger.info(f"\nTotal: {len(projects)} projects with {total_nodes} nodes found")
            else:
                logger.warning("No projects found in the database")
            
            return 0
        
        # Verify that project is specified
        if not args.project:
            logger.error("No project specified. Use --project to specify a project or --list-projects to see available projects.")
            return 1
            
        logger.info(f"Project: {args.project}")
        logger.info(f"Start Date: {args.start_date}")
        logger.info(f"End Date: {args.end_date if args.end_date else 'today'}")
        if args.node_id:
            logger.info(f"Node IDs: {args.node_id}")
        
        start_time = time.time()
        
        # Create data directory
        logger.info("Step 3: Setting up data directory...")
        data_dir = ensure_data_directory(args.output_dir)
        logger.info(f"✓ Using data directory: {data_dir}")
        
        # Process node IDs if provided
        node_ids = None
        if args.node_id:
            node_ids = args.node_id.split(',')
            
        # Get project raw data
        logger.info("Step 4: Retrieving raw data...")
        logger.info(f"   - Project: {args.project}")
        logger.info(f"   - Date range: {args.start_date} to {args.end_date if args.end_date else 'today'}")
        
        try:
            data_df = get_raw_data(
                engine, 
                project=args.project,
                node_ids=node_ids,
                start_date=args.start_date, 
                end_date=args.end_date,
                max_retries=args.retry_count
            )
        except ValueError as e:
            logger.error(str(e))
            logger.info("Hint: Use --list-projects to see all available projects")
            return 1
        
        if data_df.empty:
            logger.error("❌ No data found for the specified parameters.")
            return 1
        
        logger.info(f"✓ Retrieved {len(data_df)} raw data records")
        
        if args.verbose:
            logger.info("\nData preview:")
            logger.info(data_df.head())
            logger.info("\nData types:")
            logger.info(data_df.dtypes)
            logger.info("\nUnique nodes:")
            if 'node_id' in data_df.columns:
                logger.info(f"Node count: {data_df['node_id'].nunique()}")
                logger.info(f"Nodes: {', '.join(data_df['node_id'].unique())}")
        
        # Format the start and end dates for the filename
        start_date_str = args.start_date.replace('-', '')
        end_date_str = args.end_date.replace('-', '') if args.end_date else datetime.now().strftime('%Y%m%d')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Create the filename
        filename = f"{start_date_str}_{end_date_str}_{args.project}_{timestamp}"
        
        # Save the data
        logger.info(f"Step 5: Saving data to {args.output.upper()}...")
        output_file = save_data(
            data_df, 
            data_dir, 
            filename,
            format=args.output,
            create_zip=args.zip
        )
        
        if output_file:
            logger.info(f"✓ Data saved to: {output_file}")
            
            # Calculate and display file size
            file_size_bytes = os.path.getsize(output_file)
            file_size_mb = file_size_bytes / (1024 * 1024)
            logger.info(f"File size: {file_size_mb:.2f} MB ({file_size_bytes:,} bytes)")
            
            logger.info("\n=== Data extraction complete! ===")
            logger.info(f"Total records: {len(data_df)}")
            if 'publish_time' in data_df.columns:
                logger.info(f"Date range: {data_df['publish_time'].min()} to {data_df['publish_time'].max()}")
            
            # Calculate and display total runtime
            elapsed_time = time.time() - start_time
            minutes, seconds = divmod(elapsed_time, 60)
            logger.info(f"Total runtime: {int(minutes)} minutes, {seconds:.1f} seconds")
            
            return 0
        else:
            logger.error(f"❌ Failed to save data.")
            return 1
        
    except Exception as e:
        logger.error(f"Error pulling GEMS Sensing data: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())