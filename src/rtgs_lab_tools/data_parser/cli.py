"""CLI module for data parsing tools."""

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import click
import pandas as pd

from ..core.cli_utils import (
    CLIContext,
    add_common_options,
    handle_common_errors,
)


@click.group()
@click.pass_context
def data_parser_cli(ctx):
    """GEMS sensing data parsing tools."""
    ctx.ensure_object(CLIContext)


@data_parser_cli.command()
@click.argument('input_file', type=click.Path(exists=True, readable=True))
@click.option(
    '--output-format',
    type=click.Choice(['csv', 'parquet']),
    default='csv',
    help='Output format for parsed data (default: csv)'
)
@click.option(
    '--packet-types',
    default='all',
    help='Comma-separated list of packet types to parse (default: all). Available: data/v2, diagnostic/v2, metadata/v2, error, csv'
)
@click.option(
    '--output-file',
    help='Output file path (optional, will auto-generate if not provided)'
)
@add_common_options
@click.pass_context
@handle_common_errors("data-parsing")
def parse(
    ctx,
    input_file,
    output_format,
    packet_types,
    output_file,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Parse GEMS sensing data from raw data file.
    
    INPUT_FILE: Path to the raw data CSV file to parse
    
    Examples:
    
    # Parse all packet types to CSV
    rtgs-lab-tools data-parser parse data/raw_data.csv
    
    # Parse only data/v2 and diagnostic/v2 to parquet
    rtgs-lab-tools data-parser parse data/raw_data.csv --output-format parquet --packet-types "data/v2,diagnostic/v2"
    
    # Parse with custom output file
    rtgs-lab-tools data-parser parse data/raw_data.csv --output-file data/parsed/my_parsed_data.csv
    """
    cli_ctx = ctx.obj
    cli_ctx.setup("data-parsing", verbose, log_file, no_postgres_log)

    try:
        from .core import parse_gems_data

        cli_ctx.logger.info(f"Loading raw data from {input_file}")
        
        # Load the input data
        input_path = Path(input_file)
        if input_path.suffix.lower() == '.csv':
            raw_df = pd.read_csv(input_file)
        elif input_path.suffix.lower() in ['.parquet', '.pq']:
            raw_df = pd.read_parquet(input_file)
        else:
            raise ValueError(f"Unsupported input file format: {input_path.suffix}")
        
        cli_ctx.logger.info(f"Loaded {len(raw_df)} raw records")

        # Determine output path
        if not output_file:
            # Auto-generate path in data/parsed
            parsed_df, results = parse_gems_data(
                raw_df=raw_df,
                packet_types=packet_types,
                output_format=output_format,
                save_to_parsed_dir=True,
                original_file_path=input_file,
                logger_func=cli_ctx.logger.info
            )
            output_path = Path(results['output_file'])
        else:
            # Use specified path
            repo_root = Path(__file__).parents[3]  # Go up from src/rtgs_lab_tools/data_parser/cli.py
            parsed_dir = repo_root / "data" / "parsed"
            
            output_path = Path(output_file)
            # If relative path, put it in data/parsed
            if not output_path.is_absolute():
                output_path = parsed_dir / output_path
            
            parsed_df, results = parse_gems_data(
                raw_df=raw_df,
                packet_types=packet_types,
                output_file=str(output_path),
                output_format=output_format,
                logger_func=cli_ctx.logger.info
            )

        click.echo(f"Successfully parsed {results['output_measurements']} measurements from {results['parsed_records']} records")
        click.echo(f"Parsed data saved to: {output_path}")

        # Log success to git
        operation = f"Parse GEMS data from {input_path.name}"

        parameters = {
            "input_file": input_file,
            "output_format": output_format,
            "packet_types": packet_types,
            "output_file": str(output_path),
            "note": note,
        }

        git_results = {
            **results,
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "note": note,
        }

        additional_sections = {
            "Parsing Summary": f"- **Input Records**: {results['input_records']}\n- **Parsed Records**: {results['parsed_records']}\n- **Output Measurements**: {results['output_measurements']}\n- **Skipped Records**: {results['skipped_records']}\n- **Output File**: {output_path.name}"
        }

        if results['packet_types'] != 'all':
            additional_sections["Packet Types"] = f"- **Filtered Types**: {results['packet_types']}"

        cli_ctx.log_success(
            operation=operation,
            parameters=parameters,
            results=git_results,
            script_path=__file__,
            additional_sections=additional_sections,
        )

    except Exception as e:
        # Log error
        parameters = {
            "input_file": input_file,
            "output_format": output_format,
            "packet_types": packet_types,
            "output_file": output_file,
            "note": note,
        }
        cli_ctx.log_error("Data parsing error", e, parameters, __file__)
        raise


@data_parser_cli.command()
@click.pass_context
def list_parsers(ctx):
    """List all available packet type parsers."""
    from .parsers.factory import ParserFactory
    from .parsers.data_parser import DataV2Parser
    from .parsers.diagnostic_parser import DiagnosticV2Parser
    from .parsers.metadata_parser import MetadataV2Parser
    from .parsers.error_parser import ErrorV2Parser

    click.echo("Available packet type parsers:")
    
    parsers = [
        ("data/v2", "DataV2Parser", "GEMS sensor data packets"),
        ("diagnostic/v2", "DiagnosticV2Parser", "System diagnostic information"),
        ("metadata/v2", "MetadataV2Parser", "System configuration metadata"),
        ("error", "ErrorParser", "Error code events"),
        ("csv", "CSVParser", "CSV format data packets"),
    ]
    
    for packet_type, parser_class, description in parsers:
        click.echo(f"  {packet_type:<15} - {description}")
    
    click.echo(f"\nUse 'all' to parse all available packet types, or specify types with --packet-types")


if __name__ == "__main__":
    data_parser_cli()