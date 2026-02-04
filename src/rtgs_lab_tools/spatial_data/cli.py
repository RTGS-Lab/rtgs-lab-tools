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
@click.option(
    "--config-file",
    type=click.Path(exists=True),
    help="Path to configuration file (optional)",
)
def list_datasets(config_file: Optional[str]):
    """List all available spatial datasets based on configuration mode."""
    from .config import load_config
    from .registry.dataset_registry import format_dataset_list_by_mode

    # Load configuration
    config = load_config(config_file if config_file else None)

    # Get formatted dataset list
    output = format_dataset_list_by_mode(
        mode=config.mode,
        local_directory=config.data.get_local_directory(),
        local_prefix=config.data.local_prefix
    )

    click.echo(output)


@spatial_data_cli.command()
@click.option("--dataset", required=True, help="Dataset name to extract")
@click.option(
    "--output-dir",
    default=None,
    help="Output directory (optional - if not specified, only logs to database)"
)
@click.option(
    "--output-format",
    default="geoparquet",
    type=click.Choice(["geoparquet", "shapefile", "csv"]),
    help="Output format (default: geoparquet)",
)
@click.option("--create-zip", is_flag=True, help="Create zip archive")
@click.option("--note", help="Note for logging")
@click.option(
    "--config-file",
    type=click.Path(exists=True),
    help="Path to configuration file (optional)",
)
@click.pass_context
def extract(
    ctx,
    dataset: str,
    output_dir: Optional[str],
    output_format: str,
    create_zip: bool,
    note: Optional[str],
    config_file: Optional[str],
):
    """Extract spatial dataset - optionally save to file and/or log to database."""
    from .core.extractor import extract_spatial_data
    from .config import load_config

    try:
        # Load configuration
        config = load_config(config_file if config_file else None)

        click.echo(f"Starting extraction of dataset: {dataset}")
        click.echo(f"Mode: {config.mode}")
        if output_dir:
            click.echo(f"Output directory: {output_dir}")
            click.echo(f"Output format: {output_format}")
        else:
            click.echo("Mode: Database logging only (no file output)")
        click.echo()

        result = extract_spatial_data(
            dataset_name=dataset,
            output_dir=output_dir,
            output_format=output_format,
            create_zip=create_zip,
            note=note,
            config=config,
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


@spatial_data_cli.command()
@click.option(
    "--output-dir",
    default=None,
    help="Output directory (optional - if not specified, only logs to database)"
)
@click.option(
    "--output-format",
    default="geoparquet",
    type=click.Choice(["geoparquet", "shapefile", "csv"]),
    help="Output format (default: geoparquet)",
)
@click.option("--create-zip", is_flag=True, help="Create zip archive")
@click.option("--note", help="Note for logging")
@click.option(
    "--continue-on-error",
    is_flag=True,
    help="Continue extracting other datasets if one fails"
)
@click.pass_context
def extract_all(
    ctx,
    output_dir: Optional[str],
    output_format: str,
    create_zip: bool,
    note: Optional[str],
    continue_on_error: bool,
):
    """Extract all available datasets."""
    from .core.extractor import extract_spatial_data
    from .registry.dataset_registry import list_available_datasets

    datasets = list_available_datasets()
    total_datasets = len(datasets)

    click.echo(f"Extracting all {total_datasets} available datasets")
    if output_dir:
        click.echo(f"Output directory: {output_dir}")
        click.echo(f"Output format: {output_format}")
    else:
        click.echo("Mode: Database logging only (no file output)")
    click.echo()

    results = []
    succeeded = 0
    failed = 0

    for idx, dataset_name in enumerate(datasets.keys(), 1):
        click.echo(f"[{idx}/{total_datasets}] Extracting: {dataset_name}")

        try:
            result = extract_spatial_data(
                dataset_name=dataset_name,
                output_dir=output_dir,
                output_format=output_format,
                create_zip=create_zip,
                note=note or f"Batch extraction of all datasets",
            )

            if result["success"]:
                succeeded += 1
                click.echo(f"  [SUCCESS] {result['records_extracted']} features in {result['duration_seconds']:.1f}s")
                if result.get("output_file"):
                    click.echo(f"    File: {result['output_file']} ({result['file_size_mb']:.2f} MB)")
                results.append((dataset_name, result, None))
            else:
                failed += 1
                error_msg = result.get('error', 'Unknown error')
                click.echo(f"  [FAILED] {error_msg}", err=True)
                results.append((dataset_name, result, error_msg))

                if not continue_on_error:
                    click.echo(f"\nStopping extraction due to failure. Use --continue-on-error to continue despite failures.")
                    ctx.exit(1)

        except Exception as e:
            failed += 1
            click.echo(f"  [ERROR] {e}", err=True)
            results.append((dataset_name, None, str(e)))

            if not continue_on_error:
                click.echo(f"\nStopping extraction due to error. Use --continue-on-error to continue despite errors.")
                ctx.exit(1)

        click.echo()

    # Summary
    click.echo("=" * 60)
    click.echo("EXTRACTION SUMMARY")
    click.echo("=" * 60)
    click.echo(f"Total datasets: {total_datasets}")
    click.echo(f"Succeeded: {succeeded}")
    click.echo(f"Failed: {failed}")
    click.echo()

    if succeeded > 0:
        click.echo("Successful extractions:")
        for dataset_name, result, error in results:
            if result and result.get("success"):
                click.echo(f"  [OK] {dataset_name}: {result['records_extracted']} features")

    if failed > 0:
        click.echo("\nFailed extractions:")
        for dataset_name, result, error in results:
            if error or (result and not result.get("success")):
                click.echo(f"  [FAIL] {dataset_name}: {error or result.get('error', 'Unknown')}")
        ctx.exit(1)


@spatial_data_cli.command()
@click.option(
    "--mode",
    type=click.Choice(["built-in", "local", "hybrid"]),
    required=True,
    help="Operational mode",
)
@click.option(
    "--local-data-dir",
    type=click.Path(),
    help="Path to local data directory (required for local/hybrid modes)",
)
@click.option(
    "--output",
    default=".rtgs-config.yaml",
    help="Output configuration file path (default: .rtgs-config.yaml)",
)
@click.option(
    "--database-logging/--no-database-logging",
    default=True,
    help="Enable or disable database logging (default: enabled)",
)
def create_config(
    mode: str,
    local_data_dir: Optional[str],
    output: str,
    database_logging: bool,
):
    """Create a configuration file for spatial_data module."""
    from pathlib import Path
    from .config import SpatialDataConfig, DataConfig, DatabaseConfig, OutputConfig

    # Validate inputs
    if mode in ["local", "hybrid"] and not local_data_dir:
        click.echo(f"ERROR: Mode '{mode}' requires --local-data-dir", err=True)
        raise click.Abort()

    if local_data_dir and not Path(local_data_dir).exists():
        click.echo(
            f"WARNING: Local data directory does not exist: {local_data_dir}",
            err=True
        )
        if not click.confirm("Continue anyway?"):
            raise click.Abort()

    # Create configuration
    config = SpatialDataConfig(
        mode=mode,
        data=DataConfig(
            local_directory=local_data_dir,
            cache_directory=".rtgs_cache",
            sources=["mn_geospatial", "fgdb"],
            local_prefix="local",
        ),
        database=DatabaseConfig(
            logging_enabled=database_logging,
        ),
        output=OutputConfig(
            default_format="geoparquet",
            default_directory="./data",
        )
    )

    # Save to file
    output_path = Path(output)
    config.to_yaml(output_path)

    click.echo(f"Configuration file created: {output_path}")
    click.echo()
    click.echo("Configuration summary:")
    click.echo(f"  Mode: {mode}")
    if local_data_dir:
        click.echo(f"  Local data directory: {local_data_dir}")
    click.echo(f"  Database logging: {'enabled' if database_logging else 'disabled'}")
    click.echo()
    click.echo("You can now use this configuration by placing it in:")
    click.echo("  - Current directory: .rtgs-config.yaml")
    click.echo("  - Home directory: ~/.rtgs-config.yaml")
    click.echo("  - Or specify with --config-file option")
