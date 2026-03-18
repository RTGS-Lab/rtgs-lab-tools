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
from .winter_injury import (
    get_cultivar_names,
    get_cultivar_parameters,
    load_csv_column,
    run_simulation,
)


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


@agricultural_modeling_cli.group()
def winter_injury():
    """Winter cereal cold hardiness (LT50) simulation commands.

    Simulates the Winter Cereal Survival Model (WCSM) from Byrns et al. (2020).
    Predicts daily LT50 values based on crown temperature, daylength, and
    cultivar-specific parameters.
    """
    pass


@winter_injury.command()
@click.option("--cultivar", help="Cultivar preset name (e.g. Norstar)")
@add_common_options
@click.pass_context
@handle_common_errors("winter-injury-cultivars")
def cultivars(ctx, cultivar, verbose, log_file, no_postgres_log, note):
    """List available cultivar presets or show details for one."""
    cli_ctx = ctx.obj
    cli_ctx.setup("winter-injury-cultivars", verbose, log_file, no_postgres_log)

    if cultivar:
        params = get_cultivar_parameters(cultivar)
        click.echo(f"Parameters for {cultivar}:")
        click.echo(f"  Type:           {params['type']}")
        click.echo(f"  Origin:         {params['origin']}")
        click.echo(f"  LT50c:          {params['LT50c']}°C")
        click.echo(f"  Vern. Req.:     {params['vernReq']} days")
        click.echo(f"  Min DD:         {params['minDD'] or 'N/A (winter type)'}")
        click.echo(f"  Photo Coeff:    {params['photoCoeff']}")
        click.echo(f"  Photo Critical: {params['photoCritical']} h")
    else:
        names = get_cultivar_names()
        click.echo("Available cultivar presets:")
        for name in names:
            p = get_cultivar_parameters(name)
            click.echo(f"  {name:<20s} LT50c={p['LT50c']:6.1f}°C  {p['type']}")
        click.echo(f"\nTotal: {len(names)} cultivars")
        click.echo("Use --cultivar <name> for details")


@winter_injury.command()
@click.option(
    "--crown-temp-csv",
    required=True,
    type=click.Path(exists=True),
    help="CSV file with crown temperature data",
)
@click.option(
    "--crown-temp-col",
    default="crownTemp",
    help="Column name for crown temperature (default: crownTemp)",
)
@click.option(
    "--daylength-csv",
    required=True,
    type=click.Path(exists=True),
    help="CSV file with daylength data",
)
@click.option(
    "--daylength-col",
    default="daylength",
    help="Column name for daylength (default: daylength)",
)
@click.option("--cultivar", help="Cultivar preset name (e.g. Norstar)")
@click.option("--lt50c", type=float, help="LT50c parameter (overrides cultivar)")
@click.option(
    "--vern-req", type=float, help="Vernalization requirement (overrides cultivar)"
)
@click.option("--min-dd", type=float, help="Minimum degree days (overrides cultivar)")
@click.option(
    "--photo-coeff", type=float, help="Photoperiod coefficient (overrides cultivar)"
)
@click.option(
    "--photo-critical",
    type=float,
    default=13.5,
    help="Critical photoperiod (default: 13.5)",
)
@click.option("--output", "-o", help="Output CSV file path (default: stdout)")
@add_common_options
@click.pass_context
@handle_common_errors("winter-injury-simulate")
def simulate(
    ctx,
    crown_temp_csv,
    crown_temp_col,
    daylength_csv,
    daylength_col,
    cultivar,
    lt50c,
    vern_req,
    min_dd,
    photo_coeff,
    photo_critical,
    output,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Run a winter injury (LT50) simulation.

    Requires crown temperature and daylength time series as CSV files.
    Use a cultivar preset or specify parameters manually.

    Example:

        rtgs agricultural-modeling winter-injury simulate
            --cultivar Norstar
            --crown-temp-csv temps.csv --crown-temp-col crownTemp
            --daylength-csv daylengths.csv --daylength-col daylength
            -o results.csv
    """
    import csv as csv_mod

    cli_ctx = ctx.obj
    cli_ctx.setup("winter-injury-simulate", verbose, log_file, no_postgres_log)

    # Build parameters from cultivar preset + overrides
    if cultivar:
        preset = get_cultivar_parameters(cultivar)
        params = {
            "LT50c": lt50c if lt50c is not None else preset["LT50c"],
            "vernReq": vern_req if vern_req is not None else preset["vernReq"],
            "minDD": min_dd if min_dd is not None else (preset["minDD"] or 370),
            "photoCoeff": (
                photo_coeff if photo_coeff is not None else preset["photoCoeff"]
            ),
            "photoCritical": photo_critical,
            "initLT50": -3.0,
        }
    else:
        if lt50c is None:
            click.echo("Error: --lt50c is required when not using a cultivar preset")
            sys.exit(1)
        params = {
            "LT50c": lt50c,
            "vernReq": vern_req if vern_req is not None else 49,
            "minDD": min_dd if min_dd is not None else 370,
            "photoCoeff": photo_coeff if photo_coeff is not None else 50,
            "photoCritical": photo_critical,
            "initLT50": -3.0,
        }

    # Load input data
    crown_temps = load_csv_column(crown_temp_csv, crown_temp_col)
    daylengths = load_csv_column(daylength_csv, daylength_col)

    click.echo(f"Crown temps: {len(crown_temps)} days from {crown_temp_csv}")
    click.echo(f"Daylengths:  {len(daylengths)} days from {daylength_csv}")
    click.echo(
        f"Parameters:  LT50c={params['LT50c']}, vernReq={params['vernReq']}, "
        f"minDD={params['minDD']}, photoCoeff={params['photoCoeff']}"
    )

    # Run simulation
    records = run_simulation(params, crown_temps, daylengths)

    click.echo(f"Simulation:  {len(records)} timesteps")

    # Output
    out_fields = [
        "time",
        "LT50",
        "LT50raw",
        "temperature",
        "daylength",
        "accAmt",
        "dehardAmt",
        "dehardAmtStress",
        "vernDays",
        "vernProg",
        "photoReqFraction",
        "mflnFraction",
        "respProg",
        "minLT50",
        "respiration",
        "vernSaturation",
    ]
    # First record (initial state) lacks diagnostics; fill them
    for key in ["LT50", "temperature", "daylength", "respiration", "vernSaturation"]:
        if key not in records[0]:
            records[0][key] = "" if key != "LT50" else records[0]["LT50raw"]

    if output:
        from pathlib import Path as P

        with open(P(output), "w", newline="") as f:
            writer = csv_mod.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
        click.echo(f"Output:      {output}")
    else:
        writer = csv_mod.DictWriter(
            sys.stdout, fieldnames=out_fields, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(records)

    # Log
    parameters_dict = {
        "cultivar": cultivar,
        "crown_temp_csv": crown_temp_csv,
        "daylength_csv": daylength_csv,
        "params": params,
        "note": note,
    }
    results = {
        "success": True,
        "timesteps": len(records),
        "output_file": output or "stdout",
    }
    cli_ctx.log_success(
        operation=f"Winter injury simulation ({cultivar or 'custom'})",
        parameters=parameters_dict,
        results=results,
        script_path=__file__,
    )


if __name__ == "__main__":
    agricultural_modeling_cli()
