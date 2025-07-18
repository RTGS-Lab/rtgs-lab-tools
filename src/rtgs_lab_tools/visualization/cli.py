"""CLI module for visualization tools."""

import sys
from datetime import datetime
from pathlib import Path

import click
import pandas as pd

from ..core.cli_utils import (
    CLIContext,
    add_common_options,
    handle_common_errors,
    visualization_parameters,
)
from ..visualization import (
    create_multi_parameter_plot,
    create_time_series_plot,
)


@click.group()
@click.pass_context
def visualization_cli(ctx):
    """Visualization tools."""
    ctx.ensure_object(CLIContext)


@visualization_cli.command()
@visualization_parameters
@add_common_options
@click.pass_context
@handle_common_errors("visualization")
def create(
    ctx,
    file,
    parameter,
    node_id,
    multi_param,
    output_dir,
    output_file,
    output_format,
    list_params,
    title,
    no_markers,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Create visualizations from sensor data."""
    cli_ctx = ctx.obj
    cli_ctx.setup("visualization", verbose, log_file, no_postgres_log)

    try:
        from .data_utils import get_available_measurements, load_and_prepare_data

        # Load and prepare data (handles both raw and parsed data)
        df, data_type, parsing_results = load_and_prepare_data(
            file_path=file,
            packet_types="all",  # Parse all packet types for visualization
            cli_ctx=cli_ctx,
            auto_parse=True,  # Automatically parse without asking for confirmation
        )

        cli_ctx.logger.info(
            f"Loaded {len(df)} records from {file} (data type: {data_type})"
        )

        if list_params:
            # List available measurements from parsed data
            from .data_utils import get_all_available_measurements
            
            all_measurements = get_all_available_measurements(df)

            click.echo("Available measurements:")
            click.echo(
                "(Array measurements show individual indices that can be plotted)"
            )

            # Organize measurements by device type
            device_measurements = {}
            
            for measurement in all_measurements:
                # Extract device type from measurement
                if "." in measurement:
                    device_type, measurement_part = measurement.split(".", 1)
                    if device_type not in device_measurements:
                        device_measurements[device_type] = {"scalar": set(), "array": {}}
                    
                    if "[" in measurement_part and "]" in measurement_part:
                        # This is an indexed measurement
                        base_name = measurement_part.split("[")[0]
                        full_base_name = f"{device_type}.{base_name}"
                        if full_base_name not in device_measurements[device_type]["array"]:
                            device_measurements[device_type]["array"][full_base_name] = []
                        device_measurements[device_type]["array"][full_base_name].append(measurement)
                    else:
                        # Check if this measurement has array indices
                        has_array_version = any(
                            m.startswith(f"{measurement}[") for m in all_measurements
                        )
                        if not has_array_version:
                            device_measurements[device_type]["scalar"].add(measurement)

            # Display measurements organized by device type
            for device_type in sorted(device_measurements.keys()):
                click.echo(f"\n{device_type} measurements:")
                
                # Display scalar measurements
                if device_measurements[device_type]["scalar"]:
                    click.echo("  Scalar measurements:")
                    for measurement in sorted(device_measurements[device_type]["scalar"]):
                        click.echo(f"    {measurement}")

                # Display array measurements with their indices
                if device_measurements[device_type]["array"]:
                    click.echo("  Array measurements (with available indices):")
                    for base_name in sorted(device_measurements[device_type]["array"].keys()):
                        indices = sorted(device_measurements[device_type]["array"][base_name])
                        click.echo(f"    {base_name}")
                        for idx_measurement in indices:
                            click.echo(f"      {idx_measurement}")

                        # Show usage example
                        if indices:
                            click.echo(f'      Example: --parameter "{indices[0]}"')

            click.echo(f"\nUsage examples:")
            click.echo(f'  Device-specific: --parameter "Kestrel.Temperature" --node-id "<node_id>"')
            click.echo(f'  Device-specific array: --parameter "Kestrel.PORT_V[0]" --node-id "<node_id>"')
            return

        output_path = None

        if multi_param:
            # Multi-parameter plot
            measurements = []
            for param_spec in multi_param:
                if "," in param_spec:
                    node, measurement_name = param_spec.split(",", 1)
                    measurements.append((measurement_name.strip(), node.strip()))
                else:
                    measurements.append((param_spec.strip(), None))

            output_path = create_multi_parameter_plot(
                df=df,
                measurements=measurements,
                title=title,
                output_file=output_file,
                output_dir=output_dir,
                show_markers=not no_markers,
                format=output_format,
            )

        elif parameter:
            # Single parameter plot
            node_ids = [node_id] if node_id else None

            output_path = create_time_series_plot(
                df=df,
                measurement_name=parameter,
                node_ids=node_ids,
                title=title,
                output_file=output_file,
                output_dir=output_dir,
                show_markers=not no_markers,
                format=output_format,
            )

        else:
            click.echo(
                "Error: Must specify --parameter, --multi-param, or --list-params"
            )
            sys.exit(1)

        click.echo(f"Plot saved to: {output_path}")

        # Log success to git
        if multi_param:
            operation = f"Create multi-parameter visualization from {Path(file).name}"
            param_info = f"Multiple parameters: {', '.join([p[0] for p in parameters])}"
        elif parameter:
            operation = (
                f"Create time series plot for {parameter} from {Path(file).name}"
            )
            param_info = f"Measurement: {parameter}"
        else:
            operation = f"List parameters from {Path(file).name}"
            param_info = "Parameter listing"

        parameters_dict = {
            "input_file": file,
            "parameter": parameter,
            "node_id": node_id,
            "multi_param": list(multi_param) if multi_param else None,
            "output_dir": output_dir,
            "output_file": output_file,
            "format": output_format,
            "title": title,
            "show_markers": not no_markers,
            "note": note,
        }

        results = {
            "success": True,
            "output_file": output_path,
            "records_processed": len(df),
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "note": note,
        }

        additional_sections = {
            "Visualization Summary": f"- **Input**: {file}\n- **{param_info}**\n- **Output**: {output_path if output_path else 'Parameter listing'}\n- **Format**: {output_format.upper()}"
        }

        cli_ctx.log_success(
            operation=operation,
            parameters=parameters_dict,
            results=results,
            script_path=__file__,
            additional_sections=additional_sections,
        )

    except Exception as e:
        # Log error
        parameters_dict = {
            "input_file": file,
            "parameter": parameter,
            "node_id": node_id,
            "multi_param": list(multi_param) if multi_param else None,
            "note": note,
        }
        cli_ctx.log_error("Visualization error", e, parameters_dict, __file__)
        raise


@visualization_cli.command()
@click.argument("file")
@add_common_options
@click.pass_context
@handle_common_errors("parameter-listing")
def list_parameters(ctx, file, verbose, log_file, no_postgres_log, note):
    """List available parameters in a sensor data file."""
    cli_ctx = ctx.obj
    cli_ctx.setup("parameter-listing", verbose, log_file, no_postgres_log)

    try:
        from .data_utils import get_available_measurements, load_and_prepare_data

        # Load and prepare data (handles both raw and parsed data)
        df, data_type, parsing_results = load_and_prepare_data(
            file_path=file,
            packet_types="all",  # Parse all packet types for listing
            cli_ctx=cli_ctx,
            auto_parse=True,  # Automatically parse without asking for confirmation
        )

        cli_ctx.logger.info(
            f"Loaded {len(df)} records from {file} (data type: {data_type})"
        )

        # List available measurements from parsed data
        from .data_utils import get_all_available_measurements
        
        all_measurements = get_all_available_measurements(df)

        click.echo("Available measurements:")
        
        # Organize measurements by device type
        device_measurements = {}
        
        for measurement in all_measurements:
            # Extract device type from measurement
            if "." in measurement:
                device_type, measurement_part = measurement.split(".", 1)
                if device_type not in device_measurements:
                    device_measurements[device_type] = {"scalar": set(), "array": {}}
                
                if "[" in measurement_part and "]" in measurement_part:
                    # This is an indexed measurement
                    base_name = measurement_part.split("[")[0]
                    full_base_name = f"{device_type}.{base_name}"
                    if full_base_name not in device_measurements[device_type]["array"]:
                        device_measurements[device_type]["array"][full_base_name] = []
                    device_measurements[device_type]["array"][full_base_name].append(measurement)
                else:
                    # Check if this measurement has array indices
                    has_array_version = any(
                        m.startswith(f"{measurement}[") for m in all_measurements
                    )
                    if not has_array_version:
                        device_measurements[device_type]["scalar"].add(measurement)

        # Display measurements organized by device type
        for device_type in sorted(device_measurements.keys()):
            click.echo(f"\n{device_type} measurements:")
            
            # Display scalar measurements
            if device_measurements[device_type]["scalar"]:
                click.echo("  Scalar measurements:")
                for measurement in sorted(device_measurements[device_type]["scalar"]):
                    click.echo(f"    {measurement}")

            # Display array measurements with their indices
            if device_measurements[device_type]["array"]:
                click.echo("  Array measurements (with available indices):")
                for base_name in sorted(device_measurements[device_type]["array"].keys()):
                    indices = sorted(device_measurements[device_type]["array"][base_name])
                    click.echo(f"    {base_name}")
                    for idx_measurement in indices:
                        click.echo(f"      {idx_measurement}")

    except Exception as e:
        cli_ctx.log_error(
            "Parameter listing error", e, {"file": file, "note": note}, __file__
        )
        raise


if __name__ == "__main__":
    visualization_cli()
