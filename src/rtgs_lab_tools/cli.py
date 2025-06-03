"""Command-line interface for RTGS Lab Tools."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import click
import pandas as pd

from .core import Config, DatabaseManager, setup_logging
from .core.exceptions import RTGSLabToolsError, DatabaseError, ConfigError
from .sensing_data import get_raw_data, list_projects, save_data, create_zip_archive
from .sensing_data.file_operations import ensure_data_directory


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--log-file', help='Log to file')
@click.pass_context
def cli(ctx, verbose, log_file):
    """RTGS Lab Tools - Environmental sensing and climate data toolkit."""
    ctx.ensure_object(dict)
    
    # Set up logging
    log_level = "DEBUG" if verbose else "INFO"
    ctx.obj['logger'] = setup_logging(log_level, log_file=log_file)


@cli.command()
@click.option('--project', '-p', help='Project name to query')
@click.option('--list-projects', is_flag=True, help='List all available projects and exit')
@click.option('--setup-credentials', is_flag=True, help='Create template .env file')
@click.option('--start-date', default="2018-01-01", help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD), defaults to today')
@click.option('--node-id', help='Comma-separated list of node IDs to query')
@click.option('--output-dir', help='Output directory for data files')
@click.option('--output', type=click.Choice(['csv', 'parquet']), default='csv', help='Output format')
@click.option('--create-zip', is_flag=True, help='Create zip archive with metadata')
@click.option('--retry-count', type=int, default=3, help='Maximum retry attempts')
@click.pass_context
def data(ctx, project, list_projects, setup_credentials, start_date, end_date, 
         node_id, output_dir, output, create_zip, retry_count):
    """Extract sensing data from GEMS database."""
    logger = ctx.obj['logger']
    
    # Handle setup credentials
    if setup_credentials:
        setup_credentials_file()
        return
    
    try:
        # Initialize configuration and database
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Test database connection
        if not db_manager.test_connection():
            logger.error("Failed to connect to database. Please check your configuration and VPN connection.")
            sys.exit(1)
        
        # Handle list projects
        if list_projects:
            projects = list_projects_command(db_manager)
            if projects:
                click.echo("Available projects:")
                for project_name, node_count in projects:
                    click.echo(f"  {project_name} ({node_count} nodes)")
            else:
                click.echo("No projects found.")
            return
        
        # Validate required arguments
        if not project:
            click.echo("Error: --project is required when not listing projects")
            sys.exit(1)
        
        # Set end date default
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Parse node IDs
        node_ids = None
        if node_id:
            node_ids = [n.strip() for n in node_id.split(',')]
        
        # Ensure output directory
        output_directory = ensure_data_directory(output_dir)
        
        # Extract data
        logger.info(f"Extracting data for project: {project}")
        df = get_raw_data(
            database_manager=db_manager,
            project=project,
            start_date=start_date,
            end_date=end_date,
            node_ids=node_ids,
            max_retries=retry_count
        )
        
        if df.empty:
            logger.info("No data found for the specified parameters")
            return
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{project.replace(' ', '_')}_{start_date}_to_{end_date}_{timestamp}"
        
        # Save data
        file_path = save_data(df, output_directory, filename, output)
        
        # Create zip archive if requested
        if create_zip:
            zip_path = create_zip_archive(file_path, df, output)
            click.echo(f"Created zip archive: {zip_path}")
        else:
            click.echo(f"Data saved to: {file_path}")
        
        # Print summary
        click.echo(f"Successfully extracted {len(df)} records")
        
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        click.echo("Run with --setup-credentials to create a template .env file")
        sys.exit(1)
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)
    except RTGSLabToolsError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        if 'db_manager' in locals():
            db_manager.close()


@cli.command()
@click.pass_context
def era5(ctx):
    """Download ERA5 climate data (placeholder)."""
    logger = ctx.obj['logger']
    logger.info("ERA5 functionality not yet implemented")
    click.echo("ERA5 data access will be available in a future version")


@cli.command()
@click.pass_context
def visualize(ctx):
    """Create visualizations (placeholder)."""
    logger = ctx.obj['logger']
    logger.info("Visualization functionality not yet implemented")
    click.echo("Visualization tools will be available in a future version")


def setup_credentials_file():
    """Create template .env file with credentials."""
    env_path = Path.cwd() / '.env'
    
    # Check if .env already exists
    if env_path.exists():
        click.echo(f".env file already exists at {env_path}")
        if not click.confirm("Do you want to overwrite it?"):
            click.echo("Operation cancelled.")
            return
    
    # Create template content
    template_content = """# GEMS Database Configuration
# Update these values with your actual credentials

DB_HOST=sensing-0.msi.umn.edu
DB_PORT=5433
DB_NAME=gems
DB_USER=your_username
DB_PASSWORD=your_password

# Optional API Keys
PARTICLE_ACCESS_TOKEN=your_particle_token
CDS_API_KEY=your_cds_api_key
"""
    
    # Write template file
    with open(env_path, 'w') as f:
        f.write(template_content)
    
    click.echo(f"Created template .env file at {env_path}")
    click.echo("\nPlease edit this file and update the credentials:")
    click.echo("1. Replace 'your_username' with your database username")
    click.echo("2. Replace 'your_password' with your database password")
    click.echo("3. Ensure you are connected to the UMN VPN")
    click.echo("\nFor database access, contact the RTGS Lab.")


def list_projects_command(db_manager: DatabaseManager):
    """List available projects."""
    try:
        return list_projects(db_manager)
    except Exception as e:
        raise DatabaseError(f"Failed to list projects: {e}")


if __name__ == '__main__':
    cli()