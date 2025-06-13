"""Main CLI router for RTGS Lab Tools."""

import click


@click.group()
def cli():
    """RTGS Lab Tools - Environmental sensing and climate data toolkit."""
    pass


# Import and add the grouped CLI commands
def register_commands():
    """Register all tool command groups with the main CLI."""

    # Import the grouped CLI commands from each tool
    from .agricultural_modeling.cli import agricultural_modeling_cli
    from .data_parser.cli import data_parser_cli
    from .device_configuration.cli import device_configuration_cli
    from .error_analysis.cli import error_analysis_cli
    from .gridded_data.cli import gridded_data_cli
    from .sensing_data.cli import sensing_data_cli
    from .visualization.cli import visualization_cli

    # Add them to the main CLI with their specific names
    cli.add_command(sensing_data_cli, name="sensing-data")
    cli.add_command(data_parser_cli, name="data-parser")
    cli.add_command(visualization_cli, name="visualization")
    cli.add_command(gridded_data_cli, name="gridded-data")
    cli.add_command(device_configuration_cli, name="device-configuration")
    cli.add_command(error_analysis_cli, name="error-analysis")
    cli.add_command(agricultural_modeling_cli, name="agricultural-modeling")


# Register commands when the module is imported
register_commands()


if __name__ == "__main__":
    cli()
