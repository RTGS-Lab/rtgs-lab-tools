"""CLI module for SD card dumping tools."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from ..core.cli_utils import (
    CLIContext,
    add_common_options,
    handle_common_errors,
)
from ..core.exceptions import RTGSLabToolsError


@click.group()
@click.pass_context
def sd_dump_cli(ctx):
    """SD card dump operations for Particle devices."""
    ctx.ensure_object(CLIContext)


@sd_dump_cli.command()
@click.option("--port", "-p", help="Serial port (auto-detected if not specified)")
@click.option("--baudrate", "-b", default=1000000, help="Baud rate (default: 1000000)")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="./sd_dump_output",
    help="Output directory (default: ./sd_dump_output)",
)
@click.option(
    "--timeout", default=60, help="Connection timeout in seconds (default: 60)"
)
@click.option(
    "--skip-trigger",
    is_flag=True,
    help="Skip trigger phase (device already in command mode)",
)
@click.option(
    "--recent",
    "-r",
    type=int,
    help="Only dump the most recent N files of each type (data, error, diag, meta)",
)
@add_common_options
@click.pass_context
@handle_common_errors("sd-dump")
def dump(
    ctx,
    port: Optional[str],
    baudrate: int,
    output_dir: str,
    timeout: int,
    skip_trigger: bool,
    recent: Optional[int],
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Dump SD card contents from Particle device over serial.

    This command:
    1. Connects to the Particle device
    2. Sends a trigger to enter command mode (during device startup)
    3. Initiates SD card dump with CRC verification
    4. Saves files to the specified output directory

    IMPORTANT: The device enters command mode only during startup when serial
    data is detected. You may need to power cycle or reset the device when
    the tool starts sending the trigger.

    Alternative: If your device is already in command mode, use --skip-trigger.

    Speed optimization: Use --recent N to only dump the most recent N files of each type (data, error, diag, meta).

    Examples:

    # Basic SD card dump with auto-detection
    rtgs sd-dump dump

    # Dump only recent 3 files of each type
    rtgs sd-dump dump --recent 3

    # Use specific port and output directory
    rtgs sd-dump dump --port /dev/ttyUSB0 --output-dir ./backup
    """
    cli_ctx = ctx.obj
    cli_ctx.setup("sd-dump", verbose, log_file, no_postgres_log)

    try:
        from .core import dump_sd_card

        success, results = dump_sd_card(
            port=port,
            baudrate=baudrate,
            output_dir=output_dir,
            timeout=timeout,
            skip_trigger=skip_trigger,
            recent=recent,
            logger_func=cli_ctx.logger.info,
            auto_commit_postgres_log=not no_postgres_log,
            note=note,
        )

        if success:
            click.echo(
                f"Successfully dumped {results['files_processed']} files ({results['bytes_transferred']} bytes)"
            )
            click.echo(f"Files saved to: {results['output_directory']}")
            click.echo(f"Duration: {results['duration']:.1f} seconds")

            # Log success to git
            operation = (
                f"SD Card Dump ({'recent ' + str(recent) if recent else 'all'} files)"
            )

            parameters = {
                "port": port or "auto-detected",
                "baudrate": baudrate,
                "output_dir": output_dir,
                "timeout": timeout,
                "skip_trigger": skip_trigger,
                "recent": recent,
                "note": note,
            }

            git_results = {
                **results,
                "start_time": cli_ctx.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "note": note,
            }

            additional_sections = {
                "Dump Summary": f"- **Files Processed**: {results['files_processed']}/{results['total_files']}\n- **Bytes Transferred**: {results['bytes_transferred']:,}\n- **Duration**: {results['duration']:.1f} seconds\n- **Output Directory**: {Path(results['output_directory']).name}"
            }

            if recent:
                additional_sections["Filter Applied"] = (
                    f"- **Recent Files**: Only most recent {recent} files of each type"
                )

            cli_ctx.log_success(
                operation=operation,
                parameters=parameters,
                results=git_results,
                script_path=__file__,
                additional_sections=additional_sections,
            )
        else:
            raise RTGSLabToolsError(
                f"SD dump failed: {results.get('error', 'Unknown error')}"
            )

    except Exception as e:
        # Log error
        parameters = {
            "port": port,
            "baudrate": baudrate,
            "output_dir": output_dir,
            "timeout": timeout,
            "skip_trigger": skip_trigger,
            "recent": recent,
            "note": note,
        }
        cli_ctx.log_error("SD dump error", e, parameters, __file__)
        raise


@sd_dump_cli.command()
@click.argument("file_path", type=click.Path(exists=True, readable=True))
@click.option(
    "--filename",
    "-f",
    help="Filename to save on device (defaults to original filename)",
)
@click.option("--port", "-p", help="Serial port (auto-detected if not specified)")
@click.option("--baudrate", "-b", default=1000000, help="Baud rate (default: 1000000)")
@click.option(
    "--timeout", default=60, help="Connection timeout in seconds (default: 60)"
)
@click.option(
    "--skip-trigger",
    is_flag=True,
    help="Skip trigger phase (device already in command mode)",
)
@add_common_options
@click.pass_context
@handle_common_errors("sd-dump")
def write(
    ctx,
    file_path: str,
    filename: Optional[str],
    port: Optional[str],
    baudrate: int,
    timeout: int,
    skip_trigger: bool,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Write a file to SD card on Particle device over serial.

    FILE_PATH: Path to the local file to upload to the device

    This command uploads a file to the root directory of the SD card on the
    Particle device. The main use case is uploading configuration files like
    config.json to update device settings.

    The device must be in command mode. If it's not already in command mode,
    the tool will attempt to trigger it during device startup.

    Examples:

    # Upload config.json to device
    rtgs sd-dump write config.json

    # Upload with custom filename on device
    rtgs sd-dump write local_config.json --filename config.json

    # Use specific port
    rtgs sd-dump write config.json --port /dev/ttyUSB0

    # Skip trigger (device already in command mode)
    rtgs sd-dump write config.json --skip-trigger
    """
    cli_ctx = ctx.obj
    cli_ctx.setup("sd-dump", verbose, log_file, no_postgres_log)

    try:
        from .core import write_file_to_sd

        success, results = write_file_to_sd(
            file_path=file_path,
            filename=filename,
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            skip_trigger=skip_trigger,
            logger_func=cli_ctx.logger.info,
            auto_commit_postgres_log=not no_postgres_log,
            note=note,
        )

        if success:
            click.echo(
                f"Successfully uploaded {results['bytes_sent']} bytes to {results['device_filename']}"
            )
            click.echo(f"Local file: {results['input_file']}")
            click.echo(f"Device file: {results['device_filename']}")
            click.echo(f"Duration: {results['duration']:.1f} seconds")

            # Log success to git
            operation = f"SD Card Write: {results['device_filename']}"

            parameters = {
                "file_path": file_path,
                "filename": filename or Path(file_path).name,
                "port": port or "auto-detected",
                "baudrate": baudrate,
                "timeout": timeout,
                "skip_trigger": skip_trigger,
                "note": note,
            }

            git_results = {
                **results,
                "start_time": cli_ctx.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "note": note,
            }

            additional_sections = {
                "Upload Summary": f"- **Local File**: {Path(results['input_file']).name}\n- **Device File**: {results['device_filename']}\n- **Bytes Uploaded**: {results['bytes_sent']:,}\n- **Chunks Sent**: {results['chunks_sent']}\n- **Duration**: {results['duration']:.1f} seconds"
            }

            cli_ctx.log_success(
                operation=operation,
                parameters=parameters,
                results=git_results,
                script_path=__file__,
                additional_sections=additional_sections,
            )
        else:
            raise RTGSLabToolsError(
                f"SD write failed: {results.get('error', 'Unknown error')}"
            )

    except Exception as e:
        # Log error
        parameters = {
            "file_path": file_path,
            "filename": filename,
            "port": port,
            "baudrate": baudrate,
            "timeout": timeout,
            "skip_trigger": skip_trigger,
            "note": note,
        }
        cli_ctx.log_error("SD write error", e, parameters, __file__)
        raise


@sd_dump_cli.command()
@click.pass_context
def list_ports(ctx):
    """List available serial ports."""
    from .core import list_available_ports

    ports = list_available_ports()

    if not ports:
        click.echo("No serial ports found.")
        return

    click.echo("Available serial ports:")
    for port_info in ports:
        particle_indicator = "🟢 Particle Device" if port_info["is_particle"] else ""
        click.echo(
            f"  {port_info['device']} - {port_info['description']} {particle_indicator}"
        )


if __name__ == "__main__":
    sd_dump_cli()
