"""CLI commands for spatial data extraction."""

import click
import logging
from typing import Optional

# Reuse existing CLI utilities
from ..core.cli_utils import CLIContext

logger = logging.getLogger(__name__)


@click.group()
def spatial_data_cli():
    """Spatial data extraction and processing commands."""
    pass


@spatial_data_cli.command()
def list_datasets():
    """List all available spatial datasets."""
    from .registry.dataset_registry import list_available_datasets
    
    datasets = list_available_datasets()
    
    if not datasets:
        click.echo("No datasets available.")
        return
    
    click.echo("Available spatial datasets:")
    click.echo()
    
    for dataset_name, info in datasets.items():
        description = info.get('description', 'No description')
        source_type = info.get('source_type', 'unknown')
        spatial_type = info.get('spatial_type', 'unknown')
        
        click.echo(f"  {dataset_name}")
        click.echo(f"    Description: {description}")
        click.echo(f"    Source: {source_type}")
        click.echo(f"    Type: {spatial_type}")
        click.echo()


@spatial_data_cli.command()
@click.option('--dataset', required=True, help='Dataset name to extract')
@click.option('--output-dir', help='Output directory (default: ./data)')
@click.option('--output-format', default='geoparquet', 
              type=click.Choice(['geoparquet', 'shapefile', 'csv']), 
              help='Output format')
@click.option('--create-zip', is_flag=True, help='Create zip archive')
@click.option('--note', help='Note for logging')
@CLIContext()
def extract(dataset: str, output_dir: Optional[str], output_format: str, 
           create_zip: bool, note: Optional[str], ctx):
    """Extract spatial dataset."""
    from .core.extractor import extract_spatial_data
    
    try:
        click.echo(f"🌍 Starting extraction of dataset: {dataset}")
        
        result = extract_spatial_data(
            dataset_name=dataset,
            output_dir=output_dir,
            output_format=output_format,
            create_zip=create_zip,
            note=note
        )
        
        if result["success"]:
            click.echo(f"✅ Successfully extracted {result['records_extracted']} features")
            click.echo(f"📊 CRS: {result.get('crs', 'Unknown')}")
            click.echo(f"🔷 Geometry: {result.get('geometry_type', 'Unknown')}")
            click.echo(f"⏱️  Duration: {result['duration_seconds']:.1f} seconds")
            
            if result.get('bounds'):
                bounds = result['bounds']
                click.echo(f"🗺️  Bounds: [{bounds[0]:.2f}, {bounds[1]:.2f}, {bounds[2]:.2f}, {bounds[3]:.2f}]")
            
            click.echo(f"📋 Columns: {', '.join(result['columns'])}")
        
    except Exception as e:
        click.echo(f"❌ Extraction failed: {e}", err=True)
        ctx.exit(1)


@spatial_data_cli.command()  
@click.option('--dataset', required=True, help='Dataset name to test')
def test(dataset: str):
    """Test dataset extraction without saving files."""
    from .core.extractor import extract_spatial_data
    
    click.echo(f"🧪 Testing dataset: {dataset}")
    
    try:
        result = extract_spatial_data(dataset_name=dataset, note="CLI test")
        
        if result["success"]:
            click.echo(f"✅ Test successful!")
            click.echo(f"   Features: {result['records_extracted']}")
            click.echo(f"   Duration: {result['duration_seconds']:.1f}s")
        else:
            click.echo(f"❌ Test failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        click.echo(f"❌ Test failed: {e}", err=True)