"""CLI module for unit conversion tools."""

import sys
from datetime import datetime
from pathlib import Path

import click

from ..core.cli_utils import (
    CLIContext,
    add_common_options,
    handle_common_errors,
)
from .crop_parameters import get_crop_names, get_crop_parameters, get_crop_status
from .distance_speed import (
    degrees_to_radians,
    feet_to_meters,
    meters_per_second_to_miles_per_hour,
    miles_per_hour_to_meters_per_second,
)
from .evapotranspiration import (
    calculate_reference_et,
    get_required_columns,
    validate_input_data,
)
from .growing_degree_days import (
    calculate_corn_heat_units,
    calculate_gdd_modified,
    calculate_gdd_original,
)
from .temperature import celsius_to_fahrenheit, fahrenheit_to_celsius


@click.group()
@click.pass_context
def agricultural_modeling_cli(ctx):
    """Agricultural modeling and unit conversion tools."""
    ctx.ensure_object(CLIContext)


@agricultural_modeling_cli.group()
def temperature():
    """Temperature conversion commands."""
    pass


@temperature.command()
@click.argument("value", type=float)
@add_common_options
@click.pass_context
@handle_common_errors("temperature-conversion")
def celsius_to_fahrenheit_cmd(ctx, value, verbose, log_file, no_postgres_log, note):
    """Convert temperature from Celsius to Fahrenheit."""
    cli_ctx = ctx.obj
    cli_ctx.setup("temperature-conversion", verbose, log_file, no_postgres_log)

    result = celsius_to_fahrenheit(value)
    click.echo(f"{value}°C = {result:.2f}°F")

    # Log operation
    parameters = {"input_celsius": value, "note": note}
    results = {"output_fahrenheit": result, "success": True}
    cli_ctx.log_success(
        operation=f"Convert {value}°C to Fahrenheit",
        parameters=parameters,
        results=results,
        script_path=__file__,
    )


@temperature.command()
@click.argument("value", type=float)
@add_common_options
@click.pass_context
@handle_common_errors("temperature-conversion")
def fahrenheit_to_celsius_cmd(ctx, value, verbose, log_file, no_postgres_log, note):
    """Convert temperature from Fahrenheit to Celsius."""
    cli_ctx = ctx.obj
    cli_ctx.setup("temperature-conversion", verbose, log_file, no_postgres_log)

    result = fahrenheit_to_celsius(value)
    click.echo(f"{value}°F = {result:.2f}°C")

    # Log operation
    parameters = {"input_fahrenheit": value, "note": note}
    results = {"output_celsius": result, "success": True}
    cli_ctx.log_success(
        operation=f"Convert {value}°F to Celsius",
        parameters=parameters,
        results=results,
        script_path=__file__,
    )


@agricultural_modeling_cli.group()
def distance():
    """Distance and angle conversion commands."""
    pass


@distance.command()
@click.argument("value", type=float)
@add_common_options
@click.pass_context
@handle_common_errors("distance-conversion")
def feet_to_meters_cmd(ctx, value, verbose, log_file, no_postgres_log, note):
    """Convert distance from feet to meters."""
    cli_ctx = ctx.obj
    cli_ctx.setup("distance-conversion", verbose, log_file, no_postgres_log)

    result = feet_to_meters(value)
    click.echo(f"{value} ft = {result:.4f} m")

    # Log operation
    parameters = {"input_feet": value, "note": note}
    results = {"output_meters": result, "success": True}
    cli_ctx.log_success(
        operation=f"Convert {value} ft to meters",
        parameters=parameters,
        results=results,
        script_path=__file__,
    )


@distance.command()
@click.argument("value", type=float)
@add_common_options
@click.pass_context
@handle_common_errors("angle-conversion")
def degrees_to_radians_cmd(ctx, value, verbose, log_file, no_postgres_log, note):
    """Convert angle from degrees to radians."""
    cli_ctx = ctx.obj
    cli_ctx.setup("angle-conversion", verbose, log_file, no_postgres_log)

    result = degrees_to_radians(value)
    click.echo(f"{value}° = {result:.6f} rad")

    # Log operation
    parameters = {"input_degrees": value, "note": note}
    results = {"output_radians": result, "success": True}
    cli_ctx.log_success(
        operation=f"Convert {value}° to radians",
        parameters=parameters,
        results=results,
        script_path=__file__,
    )


@agricultural_modeling_cli.group()
def speed():
    """Speed conversion commands."""
    pass


@speed.command()
@click.argument("value", type=float)
@add_common_options
@click.pass_context
@handle_common_errors("speed-conversion")
def ms_to_mph(ctx, value, verbose, log_file, no_postgres_log, note):
    """Convert speed from meters per second to miles per hour."""
    cli_ctx = ctx.obj
    cli_ctx.setup("speed-conversion", verbose, log_file, no_postgres_log)

    result = meters_per_second_to_miles_per_hour(value)
    click.echo(f"{value} m/s = {result:.4f} mph")

    # Log operation
    parameters = {"input_ms": value, "note": note}
    results = {"output_mph": result, "success": True}
    cli_ctx.log_success(
        operation=f"Convert {value} m/s to mph",
        parameters=parameters,
        results=results,
        script_path=__file__,
    )


@speed.command()
@click.argument("value", type=float)
@add_common_options
@click.pass_context
@handle_common_errors("speed-conversion")
def mph_to_ms(ctx, value, verbose, log_file, no_postgres_log, note):
    """Convert speed from miles per hour to meters per second."""
    cli_ctx = ctx.obj
    cli_ctx.setup("speed-conversion", verbose, log_file, no_postgres_log)

    result = miles_per_hour_to_meters_per_second(value)
    click.echo(f"{value} mph = {result:.4f} m/s")

    # Log operation
    parameters = {"input_mph": value, "note": note}
    results = {"output_ms": result, "success": True}
    cli_ctx.log_success(
        operation=f"Convert {value} mph to m/s",
        parameters=parameters,
        results=results,
        script_path=__file__,
    )


@agricultural_modeling_cli.group()
def crops():
    """Crop parameter and agricultural calculation commands."""
    pass


@crops.command()
@click.option("--crop", help="Specific crop to show parameters for")
@add_common_options
@click.pass_context
@handle_common_errors("crop-parameters")
def parameters(ctx, crop, verbose, log_file, no_postgres_log, note):
    """Show crop parameters for growing degree day calculations."""
    cli_ctx = ctx.obj
    cli_ctx.setup("crop-parameters", verbose, log_file, no_postgres_log)

    try:
        if crop:
            params = get_crop_parameters(crop)
            click.echo(f"Parameters for {crop}:")
            click.echo(f"  Base Temperature: {params['tBase']}°C")
            click.echo(f"  Upper Temperature: {params['tUpper']}°C")
            click.echo(f"  Status: {params['status']}")
            click.echo(f"  Verified By: {params['verifiedBy']}")
            click.echo(f"  Reference: {params['reference']}")

            operation = f"Show parameters for {crop}"
            results = {"crop": crop, "parameters": params, "success": True}
        else:
            crops_list = get_crop_names()
            status_dict = get_crop_status()

            click.echo("Available crops:")
            for crop_name in crops_list:
                status = status_dict[crop_name]
                click.echo(f"  {crop_name} ({status})")

            click.echo(f"\nTotal: {len(crops_list)} crops available")
            click.echo("Use --crop <name> to see detailed parameters")

            operation = "List available crops"
            results = {
                "crops_count": len(crops_list),
                "crops": crops_list,
                "success": True,
            }

        # Log operation
        parameters_dict = {"crop": crop, "note": note}
        cli_ctx.log_success(
            operation=operation,
            parameters=parameters_dict,
            results=results,
            script_path=__file__,
        )

    except KeyError as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


@crops.command()
@click.argument("t_min", type=float)
@click.argument("t_max", type=float)
@click.option(
    "--crop", required=True, help="Crop to use for base and upper temperatures"
)
@click.option(
    "--method",
    type=click.Choice(["original", "modified"]),
    default="modified",
    help="GDD calculation method",
)
@add_common_options
@click.pass_context
@handle_common_errors("gdd-calculation")
def gdd(ctx, t_min, t_max, crop, method, verbose, log_file, no_postgres_log, note):
    """Calculate Growing Degree Days for a crop."""
    cli_ctx = ctx.obj
    cli_ctx.setup("gdd-calculation", verbose, log_file, no_postgres_log)

    try:
        # Get crop parameters
        crop_params = get_crop_parameters(crop)
        t_base = crop_params["tBase"]
        t_upper = crop_params["tUpper"]

        # Calculate GDD
        if method == "original":
            result = calculate_gdd_original(t_min, t_max, t_base, t_upper)
        else:
            result = calculate_gdd_modified(t_min, t_max, t_base, t_upper)

        click.echo(f"Growing Degree Days ({method} method):")
        click.echo(f"  Crop: {crop}")
        click.echo(f"  Temperature Range: {t_min}°C to {t_max}°C")
        click.echo(f"  Base Temperature: {t_base}°C")
        click.echo(f"  Upper Temperature: {t_upper}°C")
        click.echo(f"  GDD: {result:.2f}")

        # Log operation
        parameters_dict = {
            "t_min": t_min,
            "t_max": t_max,
            "crop": crop,
            "method": method,
            "t_base": t_base,
            "t_upper": t_upper,
            "note": note,
        }
        results = {"gdd": result, "success": True}
        cli_ctx.log_success(
            operation=f"Calculate GDD for {crop} using {method} method",
            parameters=parameters_dict,
            results=results,
            script_path=__file__,
        )

    except KeyError as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


@crops.command()
@click.argument("t_min", type=float)
@click.argument("t_max", type=float)
@click.option(
    "--t-base", type=float, default=10.0, help="Base temperature (default: 10.0°C)"
)
@add_common_options
@click.pass_context
@handle_common_errors("chu-calculation")
def chu(ctx, t_min, t_max, t_base, verbose, log_file, no_postgres_log, note):
    """Calculate Corn Heat Units (CHU)."""
    cli_ctx = ctx.obj
    cli_ctx.setup("chu-calculation", verbose, log_file, no_postgres_log)

    result = calculate_corn_heat_units(t_min, t_max, t_base)

    click.echo(f"Corn Heat Units:")
    click.echo(f"  Temperature Range: {t_min}°C to {t_max}°C")
    click.echo(f"  Base Temperature: {t_base}°C")
    click.echo(f"  CHU: {result:.2f}")

    # Log operation
    parameters_dict = {"t_min": t_min, "t_max": t_max, "t_base": t_base, "note": note}
    results = {"chu": result, "success": True}
    cli_ctx.log_success(
        operation=f"Calculate CHU for temperature range {t_min}°C to {t_max}°C",
        parameters=parameters_dict,
        results=results,
        script_path=__file__,
    )


@agricultural_modeling_cli.group()
def evapotranspiration():
    """Evapotranspiration calculation commands."""
    pass


@evapotranspiration.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output CSV file path")
@click.option(
    "--validate-only", is_flag=True, help="Only validate input data without calculation"
)
@add_common_options
@click.pass_context
@handle_common_errors("evapotranspiration")
def calculate(
    ctx, input_file, output, validate_only, verbose, log_file, no_postgres_log, note
):
    """Calculate reference evapotranspiration from weather data CSV."""
    import pandas as pd

    cli_ctx = ctx.obj
    cli_ctx.setup("evapotranspiration", verbose, log_file, no_postgres_log)

    try:
        # Read input file
        df = pd.read_csv(input_file)
        cli_ctx.logger.info(f"Loaded {len(df)} records from {input_file}")

        # Validate input data
        validation = validate_input_data(df)

        if not validation["valid"]:
            click.echo("Input data validation failed:")
            for error in validation["errors"]:
                click.echo(f"  - {error}")
            sys.exit(1)

        click.echo("✓ Input data validation passed")

        if validate_only:
            click.echo(
                "Validation complete. Use without --validate-only to perform calculation."
            )
            return

        # Calculate ET
        result_df = calculate_reference_et(df)

        # Determine output file
        if not output:
            input_path = Path(input_file)
            output = input_path.parent / f"{input_path.stem}_with_ET.csv"

        # Save results
        result_df.to_csv(output, index=False)
        click.echo(f"Results saved to: {output}")
        click.echo(f"Added columns: ETo (in/day), ETr (in/day)")

        # Log operation
        parameters_dict = {
            "input_file": input_file,
            "output_file": str(output),
            "validate_only": validate_only,
            "note": note,
        }
        results = {
            "success": True,
            "records_processed": len(df),
            "output_file": str(output),
            "columns_added": ["ETo (in/day)", "ETr (in/day)"],
        }
        cli_ctx.log_success(
            operation=f"Calculate reference evapotranspiration from {Path(input_file).name}",
            parameters=parameters_dict,
            results=results,
            script_path=__file__,
        )

    except Exception as e:
        parameters_dict = {"input_file": input_file, "output": output, "note": note}
        cli_ctx.log_error(
            "Evapotranspiration calculation error", e, parameters_dict, __file__
        )
        raise


@evapotranspiration.command()
@add_common_options
@click.pass_context
@handle_common_errors("et-requirements")
def requirements(ctx, verbose, log_file, no_postgres_log, note):
    """Show required columns for evapotranspiration calculation."""
    cli_ctx = ctx.obj
    cli_ctx.setup("et-requirements", verbose, log_file, no_postgres_log)

    required_cols = get_required_columns()

    click.echo("Required columns for evapotranspiration calculation:")
    click.echo()
    for col, description in required_cols.items():
        click.echo(f"  {col:<15} - {description}")

    click.echo()
    click.echo("Output columns added:")
    click.echo(
        "  ETo (in/day)    - Reference evapotranspiration for alfalfa (inches/day)"
    )
    click.echo(
        "  ETr (in/day)    - Reference evapotranspiration for grass (inches/day)"
    )


if __name__ == "__main__":
    agricultural_modeling_cli()
