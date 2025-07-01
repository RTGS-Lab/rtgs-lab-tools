"""CLI module for gridded climate data tools."""

import sys
from datetime import datetime
from pathlib import Path

import click

from ..core.cli_utils import (
    CLIContext,
    add_common_options,
    handle_common_errors,
    parse_area_bounds,
    parse_comma_separated_list,
)


@click.group()
@click.pass_context
def gridded_data_cli(ctx):
    """Gridded climate data tools."""
    ctx.ensure_object(CLIContext)

########################################################
# GET DATA
########################################################
@gridded_data_cli.command()
@click.option(
    "--source", "-s", multiple=False, required=True, help="A source of gridded data to download"
)
@click.option(
    "--variables", "-v", multiple=True, required=True, help="Dataset variables to extract"
)
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
@click.option("--roi-type", required=True, help='Region of interest type: p (pixel/point) or bbox (bounding box)')
@click.option("--roi", required=True, help='Region of interest coordinates file path: path/to/file.json')
@click.option("--clouds", help='Cloud percentage threshold')
@click.option("--output-dir", "-o", help="Output directory")
@add_common_options
@click.pass_context
@handle_common_errors("gee-data")
def get_gee_data(ctx, source, variables, start_date, end_date, roi_type, roi, clouds, output_dir,
    verbose, log_file, no_postgres_log, note,
):
    """Download and process GEE data."""
    cli_ctx = ctx.obj
    cli_ctx.setup("gee-data", verbose, log_file, no_postgres_log)

    try:
        #from ..gridded_data import ERA5Client, download_era5_data, process_era5_data
        from ..gridded_data import  download_GEE_data, load_roi#, process_GEE_data

        # Load ROI from file
        if roi:
            roi_bounds = load_roi(roi)

        # Parse variables
        if variables:
            variable_list = list(variables)
            
        # Download data 
        cli_ctx.logger.info(f"Downloading from {source}: {variables}")
        output_path = download_GEE_data(
            variables=variable_list,
            start_date=start_date,
            end_date=end_date,
            roi_type=roi_type,
            roi=roi_bounds,
            output_dir=output_dir,
            clouds=clouds
        )

        click.echo(f"GEE data downloaded to: {output_path}")

        # Basic processing if requested
        # if process:
        #     cli_ctx.logger.info("Processing downloaded ERA5 data")
        #     ds = process_GEE_data(output_path)

        #     click.echo(f"\nDataset summary:")
        #     click.echo(f"  Variables: {list(ds.data_vars)}")
        #     click.echo(
        #         f"  Time range: {ds.time.min().values} to {ds.time.max().values}"
        #     )
        #     click.echo(
        #         f"  Spatial extent: {ds.latitude.min().values:.2f}°N to {ds.latitude.max().values:.2f}°N, "
        #         f"{ds.longitude.min().values:.2f}°E to {ds.longitude.max().values:.2f}°E"
        #     )
        #     click.echo(f"  Shape: {ds.dims}")

        # Log success to git
        operation = f"Download GEE data for variables: {', '.join(variables)}"

        parameters = {
            "variables": list(variables),
            "start_date": start_date,
            "end_date": end_date,
            "roi_type": roi_type,
            "roi": roi,
            "output_dir": output_dir,
            "clouds": clouds,
            "note": note,
        }

        results = {
            "success": True,
            "output_file": output_path,
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "note": note,
        }

        additional_sections = {
            "Download Summary": f"- **Variables**: {', '.join(variables)}\n- **Output**: {output_path}\n- **Date Range**: {start_date} to {end_date}"
        }

        # cli_ctx.log_success(
        #     operation=operation,
        #     parameters=parameters,
        #     results=results,
        #     script_path=__file__,
        #     additional_sections=additional_sections,
        # )

    except Exception as e:
        # Log error
        parameters = {
            "variables": list(variables),
            "start_date": start_date,
            "end_date": end_date,
            "roi_type": roi_type,
            "roi": roi,
            "output_dir": output_dir,
            "clouds": clouds,
            "note": note,
        }
        #cli_ctx.log_error("ERA5 error", e, parameters, __file__)
        raise

########################################################
# LIST AVAILABLE DATASETS
########################################################
@gridded_data_cli.command()
@add_common_options
@click.pass_context
@handle_common_errors("gee-datasets")
def list_gee_datasets(ctx, verbose, log_file, no_postgres_log, note):
    """List available GEE datasets."""
    cli_ctx = ctx.obj
    cli_ctx.setup("gee-datasets", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import sources

        click.echo("Available GEE datasets:")
        for key in list(sources.keys()):
            click.echo(f"  {key}: {sources[key]}")

    except Exception as e:
        cli_ctx.log_error("GEE datasets listing error", e, {"note": note}, __file__)
        raise

########################################################
# LIST AVAILABLE VARIABLES
########################################################
@gridded_data_cli.command()
@click.option(
    "--source", "-s", multiple=False, required=True, help="Dataset to list from"
)
@add_common_options
@click.pass_context
@handle_common_errors("gee-dataset-varaibles")
def list_gee_variables(ctx, source, verbose, log_file, no_postgres_log, note):
    """List available variables for the given GEE dataset."""
    cli_ctx = ctx.obj
    cli_ctx.setup("gee-dataset-varaibles", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import sources, list_GEE_vars
        
        band_names = list_GEE_vars(source)
        click.echo(f"Available GEE variables for {source}:")
        for band in band_names:
            click.echo(f"  {band}")

    except Exception as e:
        cli_ctx.log_error("GEE variables listing error", e, {"note": note}, __file__)
        raise



if __name__ == "__main__":
    gridded_data_cli()
