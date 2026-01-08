"""CLI commands for spatial data extraction."""

import logging
from typing import Optional

import click

# Reuse existing CLI utilities
from ..core.cli_utils import CLIContext

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def spatial_data_cli(ctx):
    """Spatial data extraction and processing commands."""
    ctx.ensure_object(CLIContext)


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
        description = info.get("description", "No description")
        source_type = info.get("source_type", "unknown")
        spatial_type = info.get("spatial_type", "unknown")

        click.echo(f"  {dataset_name}")
        click.echo(f"    Description: {description}")
        click.echo(f"    Source: {source_type}")
        click.echo(f"    Type: {spatial_type}")
        click.echo()


@spatial_data_cli.command()
@click.option("--dataset", required=True, help="Dataset name to extract")
@click.option(
    "--output-dir", default="./data", help="Output directory (default: ./data)"
)
@click.option(
    "--output-format",
    default="geoparquet",
    type=click.Choice(["geoparquet", "shapefile", "csv"]),
    help="Output format (default: geoparquet)",
)
@click.option("--create-zip", is_flag=True, help="Create zip archive")
@click.option("--note", help="Note for logging")
@click.pass_context
def extract(
    ctx,
    dataset: str,
    output_dir: str,
    output_format: str,
    create_zip: bool,
    note: Optional[str],
):
    """Extract spatial dataset and save to file."""
    from .core.extractor import extract_spatial_data

    try:
        click.echo(f"Starting extraction of dataset: {dataset}")
        click.echo(f"Output directory: {output_dir}")
        click.echo(f"Output format: {output_format}")
        click.echo()

        result = extract_spatial_data(
            dataset_name=dataset,
            output_dir=output_dir,
            output_format=output_format,
            create_zip=create_zip,
            note=note,
        )

        if result["success"]:
            click.echo(
                f"SUCCESS: Successfully extracted {result['records_extracted']} features"
            )
            click.echo(f"CRS: {result.get('crs', 'Unknown')}")
            click.echo(f"Geometry: {result.get('geometry_type', 'Unknown')}")
            click.echo(f"Duration: {result['duration_seconds']:.1f} seconds")

            # Show file output information
            if result.get("output_file"):
                click.echo(f"Output file: {result['output_file']}")
                if result.get("file_size_mb"):
                    click.echo(f"File size: {result['file_size_mb']:.2f} MB")

            if result.get("bounds"):
                bounds = result["bounds"]
                click.echo(
                    f"Bounds: [{bounds[0]:.2f}, {bounds[1]:.2f}, {bounds[2]:.2f}, {bounds[3]:.2f}]"
                )

            click.echo(f"Columns: {', '.join(result['columns'])}")
            click.echo()
            click.echo("Extraction completed successfully and logged to database!")

    except Exception as e:
        click.echo(f"ERROR: Extraction failed: {e}", err=True)
        ctx.exit(1)


@spatial_data_cli.command()
@click.option("--dataset", required=True, help="Dataset name to test")
def test(dataset: str):
    """Test dataset extraction without saving files."""
    from .core.extractor import extract_spatial_data

    click.echo(f"Testing dataset: {dataset}")

    try:
        result = extract_spatial_data(dataset_name=dataset, note="CLI test")

        if result["success"]:
            click.echo(f"SUCCESS: Test successful!")
            click.echo(f"   Features: {result['records_extracted']}")
            click.echo(f"   Duration: {result['duration_seconds']:.1f}s")
        else:
            click.echo(f"FAILED: Test failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        click.echo(f"ERROR: Test failed: {e}", err=True)
