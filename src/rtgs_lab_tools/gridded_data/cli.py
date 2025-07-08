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
    "--source",  multiple=False, required=True, help="A source of gridded data to download (short name)."
)
@click.option(
    "--variables", multiple=True, required=True, help="Dataset variables to extract"
)
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
@click.option("--roi-type", required=True, help='Region of interest type: p (pixel/point) or bbox (bounding box)')
@click.option("--roi", required=True, help='Region of interest coordinates file path: path/to/file.json')
@click.option("--clouds", help='Cloud percentage threshold')
@click.option("--out-dest", "-o", required=True, help="Output destination: drive (google-drive) or bucket (google-bucket)")
@click.option("--folder", "-o", help="Output destination folder")
@click.option("--scale", "-o", help="Image resolution. When not set, the image is downloaded in native resolution")
@add_common_options
@click.pass_context
@handle_common_errors("gee-data")
def get_gee_data(ctx, source, variables, start_date, end_date, roi_type, roi, clouds, out_dest, folder, scale,
    verbose, log_file, no_postgres_log, note,
):
    """Download GEE raster data to the google drive or google bucket."""
    cli_ctx = ctx.obj
    cli_ctx.setup("gee-data", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import  download_GEE_raster, load_roi, sources

        # Load ROI from file
        if roi:
            roi_bounds = load_roi(roi)

        # Parse variables
        if variables:
            variable_list = list(variables)[0].replace(" ", "").split(',')
        #TODO: roi_type logic, i.e. pixel vs region download: for a pixel download csv locally, for a bbox export a tiff to the cloud
        #TODO: a func to create a csv of image meta info (clouds)
        #TODO: a func to upload images from the csv
        # Download data 
        if roi_type=='bbox':
            cli_ctx.logger.info(f"Downloading from {source}: {variables}")
            output_path = download_GEE_raster(
                name=source,
                source=sources[source],
                bands=variable_list,
                roi=roi_bounds,
                scale=scale,
                start_date=start_date,
                end_date=end_date,
                out_dest=out_dest,
                folder=folder,
                clouds=clouds
            )

        click.echo(f"GEE data downloaded to: {out_dest}/{folder}")

        # Log success to git
        operation = f"Download GEE data for variables: {', '.join(variables)}"

        parameters = {
            "variables": list(variables),
            "start_date": start_date,
            "end_date": end_date,
            "roi_type": roi_type,
            "roi": roi,
            "out_dest": out_dest,
            "clouds": clouds,
            "folder": folder,
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
            "out_dest": out_dest,
            "clouds": clouds,
            "folder": folder,
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
        
        band_names = list_GEE_vars(sources[source])
        click.echo(f"Available GEE variables for {source}:")
        for band in band_names:
            click.echo(f"  {band}")

    except Exception as e:
        cli_ctx.log_error("GEE variables listing error", e, {"note": note}, __file__)
        raise



if __name__ == "__main__":
    gridded_data_cli()
