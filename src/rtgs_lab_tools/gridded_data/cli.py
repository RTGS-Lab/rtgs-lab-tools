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
# DOWNLOAD CLIPPED PLANET IMAGES
########################################################
@gridded_data_cli.command()
@click.option(
    "--source",
    multiple=False,
    required=True,
    help="One source of Planet data: PSScene (PlanetScope) or SkySatScene (SkySat)",
)
@click.option(
    "--meta-file",
    help="Path to the CSV file containing id column with scene ids to download",
)
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option(
    "--roi",
    required=True,
    help="Region of interest coordinates file path: path/to/file.json",
)
@click.option("--clouds", help="Cloud percentage threshold")
@click.option("--out-dir", "-o", required=True, help="Local output directory")
@add_common_options
@click.pass_context
@handle_common_errors("download-clipped-scenes")
def download_clipped_scenes(
    ctx,
    source,
    meta_file,
    start_date,
    end_date,
    roi,
    clouds,
    out_dir,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Downloading clipped PlanetLabs scenes. Provide eaither a csv file with scene id's or dates and region of interest(roi)."""
    cli_ctx = ctx.obj
    cli_ctx.setup("download-scenes", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import download_clipped_scenes, load_roi

        # Load ROI from file
        if roi:
            roi = load_roi(roi).getInfo()

        download_clipped_scenes(
            source=source,
            meta_file=meta_file,
            roi=roi,
            start_date=start_date,
            end_date=end_date,
            clouds=clouds,
            out_dir=out_dir,
        )

        click.echo(f"Planet imagery is saved to: {out_dir}")

    except Exception as e:
        # Log error
        parameters = {
            "start_date": start_date,
            "end_date": end_date,
            "roi": roi,
            "out_dir": out_dir,
            "note": note,
        }
        raise


########################################################
# DOWNLOAD RAW PLANET IMAGES
########################################################
@gridded_data_cli.command()
@click.option(
    "--source",
    multiple=False,
    required=True,
    help="A source of Planet data: PSScene (PlanetScope), SkySatScene (SkySat)",
)
@click.option(
    "--meta-file",
    help="Path to the CSV file containing id column with scene ids to download",
)
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option(
    "--roi",
    help="Region of interest coordinates file path: path/to/file.json",
)
@click.option("--clouds", help="Cloud percentage threshold")
@click.option("--out-dir", "-o", required=True, help="Local output directory")
@add_common_options
@click.pass_context
@handle_common_errors("download-scenes")
def download_scenes(
    ctx,
    source,
    meta_file,
    start_date,
    end_date,
    roi,
    clouds,
    out_dir,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Downloading PlanetLabs scenes. To use provide eaither a csv file with scene id's or dates and region of interest(roi)."""
    cli_ctx = ctx.obj
    cli_ctx.setup("download-scenes", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import download_scenes, load_roi

        # Load ROI from file
        if roi:
            roi = load_roi(roi).getInfo()

        download_scenes(
            source=source,
            meta_file=meta_file,
            roi=roi,
            start_date=start_date,
            end_date=end_date,
            clouds=clouds,
            out_dir=out_dir,
        )

        click.echo(f"Planet imagery is saved to: {out_dir}")

    except Exception as e:
        # Log error
        parameters = {
            "start_date": start_date,
            "end_date": end_date,
            "roi": roi,
            "out_dir": out_dir,
            "note": note,
        }
        raise


########################################################
# SEARCH FOR PLANET IMAGES
########################################################
@gridded_data_cli.command()
@click.option(
    "--source",
    multiple=False,
    required=True,
    help="A source of Planet data: PSScene (PlanetScope), SkySatScene (SkySat)",
)
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
@click.option(
    "--roi",
    required=True,
    help="Region of interest coordinates file path: path/to/file.json",
)
@click.option("--clouds", help="Cloud percentage threshold")
@click.option("--out-dir", "-o", required=True, help="Local output directory")
@add_common_options
@click.pass_context
@handle_common_errors("planet-search")
def planet_search(
    ctx,
    source,
    start_date,
    end_date,
    roi,
    clouds,
    out_dir,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Searchg for PlanetLabs imagery between dates."""
    cli_ctx = ctx.obj
    cli_ctx.setup("planet-search", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import load_roi, quick_search

        # Load ROI from file
        if roi:
            roi = load_roi(roi).getInfo()
        # print(roi_bounds)

        quick_search(
            source=source,
            roi=roi,
            start_date=start_date,
            end_date=end_date,
            clouds=clouds,
            out_dir=out_dir,
        )

        click.echo(f"Planet Search results are saved to: {out_dir}")

    except Exception as e:
        # Log error
        parameters = {
            "start_date": start_date,
            "end_date": end_date,
            "roi": roi,
            "out_dir": out_dir,
            "note": note,
        }
        raise


########################################################
# SEARCH FOR GEE IMAGES
# SEARCH FOR GEE IMAGES
########################################################
@gridded_data_cli.command()
@click.option(
    "--source",
    multiple=False,
    required=True,
    help="A source of gridded data to download (short name).",
)
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
@click.option(
    "--roi",
    required=True,
    help="Region of interest coordinates file path: path/to/file.json",
)
@click.option("--out-dir", "-o", required=True, help="Local output directory")
@add_common_options
@click.pass_context
@handle_common_errors("gee-search")
def gee_search(
    ctx,
    source,
    start_date,
    end_date,
    roi,
    out_dir,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Searchg for GEE between dates."""
    cli_ctx = ctx.obj
    cli_ctx.setup("gee-search", verbose, log_file, no_postgres_log)
    cli_ctx.setup("gee-search", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import init_ee, load_roi, search_images, sources

        init_ee()

        # Load ROI from file
        if roi:
            roi_bounds = load_roi(roi)

        # Download data
        search_images(
            name=source,
            source=sources[source],
            roi=roi_bounds,
            start_date=start_date,
            end_date=end_date,
            out_dir=out_dir,
        )

        click.echo(f"GEE data saved to: {out_dir}")

    except Exception as e:
        # Log error
        parameters = {
            "start_date": start_date,
            "end_date": end_date,
            "roi": roi,
            "out_dir": out_dir,
            "note": note,
        }
        raise


########################################################
# GET GEE POINT DATA
# GET GEE POINT DATA
########################################################
@gridded_data_cli.command()
@click.option(
    "--source",
    multiple=False,
    required=True,
    help="A source of gridded data to download (short name).",
)
@click.option(
    "--variables", multiple=True, required=True, help="Dataset variables to extract"
)
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
@click.option(
    "--roi",
    required=True,
    help="Region of interest coordinates file path: path/to/file.json",
)
@click.option("--clouds", help="Cloud percentage threshold")
@click.option("--out-dir", "-o", required=True, help="Local output directory")
@add_common_options
@click.pass_context
@handle_common_errors("gee-point")
def get_gee_point(
    ctx,
    source,
    variables,
    start_date,
    end_date,
    roi,
    clouds,
    out_dir,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Download GEE point data to the local path."""
    cli_ctx = ctx.obj
    cli_ctx.setup("gee-point", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import download_GEE_point, init_ee, load_roi, sources

        init_ee()

        # Load ROI from file
        if roi:
            roi_bounds = load_roi(roi)

        # Parse variables
        if variables:
            variable_list = list(variables)[0].replace(" ", "").split(",")
        else:
            variables = []

        # Download data
        cli_ctx.logger.info(f"Downloading from {source}: {variables}")
        download_GEE_point(
            name=source,
            source=sources[source],
            bands=variable_list,
            roi=roi_bounds,
            start_date=start_date,
            end_date=end_date,
            out_dir=out_dir,
        )

        click.echo(f"GEE data downloaded to: {out_dir}")

        # Log success to git
        operation = f"Download GEE data for variables: {', '.join(variables)}"

        parameters = {
            "variables": list(variables),
            "start_date": start_date,
            "end_date": end_date,
            "roi": roi,
            "out_dir": out_dir,
            "note": note,
        }

        results = {
            "success": True,
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "note": note,
        }

        additional_sections = {
            "Download Summary": f"- **Variables**: {', '.join(variables)}\n- **Date Range**: {start_date} to {end_date}"
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
            "roi": roi,
            "out_dir": out_dir,
            "clouds": clouds,
            "note": note,
        }
        # cli_ctx.log_error("ERA5 error", e, parameters, __file__)
        raise


########################################################
# GET GEE RASTER DATA
# GET GEE RASTER DATA
########################################################
@gridded_data_cli.command()
@click.option(
    "--source",
    multiple=False,
    required=True,
    help="A source of gridded data to download (short name).",
)
@click.option("--variables", multiple=True, help="Dataset variables to extract")
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
@click.option(
    "--roi",
    required=True,
    help="Region of interest coordinates file path: path/to/file.json",
)
@click.option("--clouds", help="Cloud percentage threshold")
@click.option(
    "--out-dest",
    "-o",
    required=True,
    help="Output destination: drive (google-drive) or bucket (google-bucket)",
)
@click.option("--folder", "-o", help="Output destination folder")
@add_common_options
@click.pass_context
@handle_common_errors("gee-raster")
def get_gee_raster(
    ctx,
    source,
    variables,
    start_date,
    end_date,
    roi,
    clouds,
    out_dest,
    folder,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Download GEE raster data to gdrive or gbucket."""
    cli_ctx = ctx.obj
    cli_ctx.setup("gee-data", verbose, log_file, no_postgres_log)

    try:
        from ..gridded_data import download_GEE_raster, init_ee, load_roi, sources

        init_ee()

        # Load ROI from file
        if roi:
            roi_bounds = load_roi(roi)

        # Parse variables
        if variables:
            variable_list = list(variables)[0].replace(" ", "").split(",")
        else:
            variables = []

        # Download data
        cli_ctx.logger.info(f"Downloading from {source}: {variables}")
        download_GEE_raster(
            name=source,
            source=sources[source],
            bands=variable_list,
            roi=roi_bounds,
            start_date=start_date,
            end_date=end_date,
            out_dest=out_dest,
            folder=folder,
            clouds=clouds,
        )

        click.echo(f"GEE data downloaded to: {out_dest}/{folder}")

        # Log success to git
        operation = f"Download GEE data for variables: {', '.join(variables)}"

        parameters = {
            "variables": list(variables),
            "start_date": start_date,
            "end_date": end_date,
            "roi": roi,
            "out_dest": out_dest,
            "clouds": clouds,
            "folder": folder,
            "note": note,
        }

        results = {
            "success": True,
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "note": note,
        }

        additional_sections = {
            "Download Summary": f"- **Variables**: {', '.join(variables)}\n- **Date Range**: {start_date} to {end_date}"
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
            "roi": roi,
            "out_dest": out_dest,
            "clouds": clouds,
            "folder": folder,
            "note": note,
        }
        # cli_ctx.log_error("ERA5 error", e, parameters, __file__)
        raise


########################################################
# LIST AVAILABLE GEE DATASETS
# LIST AVAILABLE GEE DATASETS
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
# LIST AVAILABLE GEE VARIABLES
# LIST AVAILABLE GEE VARIABLES
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
        from ..gridded_data import init_ee, list_GEE_vars, sources

        init_ee()

        band_names = list_GEE_vars(sources[source])
        click.echo(f"Available GEE variables for {source}:")
        for band in band_names:
            click.echo(f"  {band}")

    except Exception as e:
        cli_ctx.log_error("GEE variables listing error", e, {"note": note}, __file__)
        raise


########################################################
# GEE AUTHENTICATE
########################################################
@gridded_data_cli.command()
@add_common_options
@click.pass_context
@handle_common_errors("gee-authenticate")
def gee_authenticate(ctx, verbose, log_file, no_postgres_log, note):
    """Google Earth Engine account authentication."""
    cli_ctx = ctx.obj
    cli_ctx.setup("gee-authenticate", verbose, log_file, no_postgres_log)

    import ee

    ee.Authenticate()


if __name__ == "__main__":
    gridded_data_cli()
