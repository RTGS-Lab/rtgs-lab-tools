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
    get_available_parameters,
    parse_sensor_messages,
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
    no_git_log,
    note,
):
    """Create visualizations from sensor data."""
    cli_ctx = ctx.obj
    cli_ctx.setup("visualization", verbose, log_file, no_git_log)

    try:
        # Read CSV file
        df = pd.read_csv(file)
        cli_ctx.logger.info(f"Loaded {len(df)} records from {file}")

        # Parse sensor messages
        df = parse_sensor_messages(df)

        if list_params:
            # List available parameters
            params_by_node = get_available_parameters(df)

            click.echo("Available parameters by node:")
            for node, params in params_by_node.items():
                click.echo(f"\n{node}:")
                for param in sorted(params):
                    click.echo(f"  {param}")
            return

        output_path = None

        if multi_param:
            # Multi-parameter plot
            parameters = []
            for param_spec in multi_param:
                if "," in param_spec:
                    node, param_path = param_spec.split(",", 1)
                    parameters.append((param_path.strip(), node.strip()))
                else:
                    parameters.append((param_spec.strip(), None))

            output_path = create_multi_parameter_plot(
                df=df,
                parameters=parameters,
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
                parameter_path=parameter,
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
            param_info = f"Parameter: {parameter}"
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
def list_parameters(ctx, file, verbose, log_file, no_git_log, note):
    """List available parameters in a sensor data file."""
    cli_ctx = ctx.obj
    cli_ctx.setup("parameter-listing", verbose, log_file, no_git_log)

    try:
        # Read CSV file
        df = pd.read_csv(file)
        cli_ctx.logger.info(f"Loaded {len(df)} records from {file}")

        # Parse sensor messages
        df = parse_sensor_messages(df)

        # List available parameters
        params_by_node = get_available_parameters(df)

        click.echo("Available parameters by node:")
        for node, params in params_by_node.items():
            click.echo(f"\n{node}:")
            for param in sorted(params):
                click.echo(f"  {param}")

    except Exception as e:
        cli_ctx.log_error(
            "Parameter listing error", e, {"file": file, "note": note}, __file__
        )
        raise


if __name__ == "__main__":
    visualization_cli()
