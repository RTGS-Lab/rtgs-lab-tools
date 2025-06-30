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


@gridded_data_cli.command()
@click.option(
    "--variables", "-v", multiple=True, required=True, help="ERA5 variables to download"
)
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
@click.option("--area", help='Bounding box as "north,west,south,east"')
@click.option("--output-file", "-o", help="Output NetCDF file path")
@click.option("--pressure-levels", help="Pressure levels (comma-separated)")
@click.option(
    "--time-hours", help='Specific hours (comma-separated, e.g., "00:00,12:00")'
)
@click.option(
    "--list-variables", is_flag=True, help="List available variables and exit"
)
@click.option(
    "--process", is_flag=True, help="Process downloaded data (basic statistics)"
)
@add_common_options
@click.pass_context
@handle_common_errors("era5-data")
def era5(
    ctx,
    variables,
    start_date,
    end_date,
    area,
    output_file,
    pressure_levels,
    time_hours,
    list_variables,
    process,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Download and process ERA5 climate data."""
    cli_ctx = ctx.obj
    cli_ctx.setup("era5-data", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import ERA5Client, download_era5_data, process_era5_data

        if list_variables:
            client = ERA5Client()

            click.echo("Available ERA5 single-level variables:")
            single_vars = client.get_available_variables("single-levels")
            for code, desc in single_vars.items():
                click.echo(f"  {code}: {desc}")

            click.echo("\nAvailable ERA5 pressure-level variables:")
            pressure_vars = client.get_available_variables("pressure-levels")
            for code, desc in pressure_vars.items():
                click.echo(f"  {code}: {desc}")
            return

        # Parse area if provided
        area_bounds = None
        if area:
            area_bounds = parse_area_bounds(area)

        # Parse pressure levels if provided
        pressure_list = None
        if pressure_levels:
            pressure_list = parse_comma_separated_list(
                pressure_levels, int, "pressure levels"
            )

        # Parse time hours if provided
        time_list = None
        if time_hours:
            time_list = parse_comma_separated_list(time_hours, str, "time hours")

        # Download data
        cli_ctx.logger.info(f"Downloading ERA5 data: {variables}")
        output_path = download_era5_data(
            variables=list(variables),
            start_date=start_date,
            end_date=end_date,
            area=area_bounds,
            output_file=output_file,
            pressure_levels=pressure_list,
            time_hours=time_list,
        )

        click.echo(f"ERA5 data downloaded to: {output_path}")

        # Basic processing if requested
        if process:
            cli_ctx.logger.info("Processing downloaded ERA5 data")
            ds = process_era5_data(output_path)

            click.echo(f"\nDataset summary:")
            click.echo(f"  Variables: {list(ds.data_vars)}")
            click.echo(
                f"  Time range: {ds.time.min().values} to {ds.time.max().values}"
            )
            click.echo(
                f"  Spatial extent: {ds.latitude.min().values:.2f}°N to {ds.latitude.max().values:.2f}°N, "
                f"{ds.longitude.min().values:.2f}°E to {ds.longitude.max().values:.2f}°E"
            )
            click.echo(f"  Shape: {ds.dims}")

        # Log success to git
        operation = f"Download ERA5 data for variables: {', '.join(variables)}"

        parameters = {
            "variables": list(variables),
            "start_date": start_date,
            "end_date": end_date,
            "area": area,
            "output_file": output_file,
            "pressure_levels": pressure_levels,
            "time_hours": time_hours,
            "process": process,
            "note": note,
        }

        results = {
            "success": True,
            "output_file": output_path,
            "processed": process,
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "note": note,
        }

        additional_sections = {
            "Download Summary": f"- **Variables**: {', '.join(variables)}\n- **Output**: {output_path}\n- **Date Range**: {start_date} to {end_date}"
        }

        cli_ctx.log_success(
            operation=operation,
            parameters=parameters,
            results=results,
            script_path=__file__,
            additional_sections=additional_sections,
        )

    except Exception as e:
        # Log error
        parameters = {
            "variables": list(variables) if variables else [],
            "start_date": start_date,
            "end_date": end_date,
            "area": area,
            "output_file": output_file,
            "pressure_levels": pressure_levels,
            "time_hours": time_hours,
            "note": note,
        }
        cli_ctx.log_error("ERA5 error", e, parameters, __file__)
        raise


@gridded_data_cli.command()
@click.argument("file_path")
@click.option("--variables", multiple=True, help="Specific variables to process")
@click.option(
    "--temporal-aggregation",
    type=click.Choice(["daily", "monthly"]),
    help="Temporal aggregation",
)
@click.option(
    "--spatial-subset", help='Spatial subset as "lat_min,lat_max,lon_min,lon_max"'
)
@add_common_options
@click.pass_context
@handle_common_errors("era5-processing")
def process_era5(
    ctx,
    file_path,
    variables,
    temporal_aggregation,
    spatial_subset,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Process ERA5 NetCDF data with aggregation and subsetting."""
    cli_ctx = ctx.obj
    cli_ctx.setup("era5-processing", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import process_era5_data

        # Parse spatial subset if provided
        spatial_dict = None
        if spatial_subset:
            try:
                lat_min, lat_max, lon_min, lon_max = [
                    float(x.strip()) for x in spatial_subset.split(",")
                ]
                spatial_dict = {
                    "lat_min": lat_min,
                    "lat_max": lat_max,
                    "lon_min": lon_min,
                    "lon_max": lon_max,
                }
            except ValueError:
                click.echo(
                    "Error: Spatial subset must be 'lat_min,lat_max,lon_min,lon_max'"
                )
                sys.exit(1)

        # Process data
        cli_ctx.logger.info(f"Processing ERA5 data from {file_path}")
        ds = process_era5_data(
            file_path=file_path,
            variables=list(variables) if variables else None,
            temporal_aggregation=temporal_aggregation,
            spatial_subset=spatial_dict,
        )

        # Generate output filename
        output_path = Path(file_path).with_suffix(".processed.nc")
        ds.to_netcdf(output_path)

        click.echo(f"Processed data saved to: {output_path}")
        click.echo(f"Variables: {list(ds.data_vars)}")
        click.echo(f"Dimensions: {ds.dims}")

        # Log success to git
        operation = f"Process ERA5 data from {Path(file_path).name}"
        if note:
            operation += f" - {note}"

        parameters = {
            "input_file": file_path,
            "variables": list(variables) if variables else None,
            "temporal_aggregation": temporal_aggregation,
            "spatial_subset": spatial_subset,
            "note": note,
        }

        results = {
            "success": True,
            "input_file": file_path,
            "output_file": str(output_path),
            "variables_processed": list(ds.data_vars),
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
        }

        cli_ctx.log_success(
            operation=operation,
            parameters=parameters,
            results=results,
            script_path=__file__,
        )

    except Exception as e:
        # Log error
        parameters = {
            "input_file": file_path,
            "variables": list(variables) if variables else None,
            "temporal_aggregation": temporal_aggregation,
            "spatial_subset": spatial_subset,
            "note": note,
        }
        cli_ctx.log_error("ERA5 processing error", e, parameters, __file__)
        raise


@gridded_data_cli.command()
@add_common_options
@click.pass_context
@handle_common_errors("era5-variables")
def list_variables(ctx, verbose, log_file, no_postgres_log, note):
    """List available ERA5 variables."""
    cli_ctx = ctx.obj
    cli_ctx.setup("era5-variables", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import ERA5Client

        client = ERA5Client()

        click.echo("Available ERA5 single-level variables:")
        single_vars = client.get_available_variables("single-levels")
        for code, desc in single_vars.items():
            click.echo(f"  {code}: {desc}")

        click.echo("\nAvailable ERA5 pressure-level variables:")
        pressure_vars = client.get_available_variables("pressure-levels")
        for code, desc in pressure_vars.items():
            click.echo(f"  {code}: {desc}")

    except Exception as e:
        cli_ctx.log_error("ERA5 variables listing error", e, {"note": note}, __file__)
        raise


if __name__ == "__main__":
    gridded_data_cli()
