"""CLI module for device configuration tools."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import click

from ..core.cli_utils import (
    CLIContext,
    add_common_options,
    device_config_parameters,
    handle_common_errors,
)
from ..core.config import Config
from ..core.exceptions import APIError, ValidationError
from .uid_decoding import (
    decode_both_configs,
    format_sensor_config,
    format_system_config,
    parse_uid,
)
from .update_configuration import ParticleConfigUpdater


@click.group()
@click.pass_context
def device_configuration_cli(ctx):
    """Device configuration management tools."""
    ctx.ensure_object(CLIContext)


@device_configuration_cli.command()
@device_config_parameters
@add_common_options
@click.pass_context
@handle_common_errors("device-configuration")
def update_config(
    ctx,
    config,
    devices,
    output,
    max_retries,
    restart_wait,
    online_timeout,
    max_concurrent,
    dry_run,
    no_particle_git_log,
    verbose,
    log_file,
    no_git_log,
    note,
):
    """Update configurations on multiple Particle devices."""
    cli_ctx = ctx.obj
    cli_ctx.setup("device-configuration", verbose, log_file, no_git_log)

    try:
        # Import here to handle potential import issues
        from .particle_client import (
            parse_config_input,
            parse_device_input,
            save_results,
        )

        # Initialize configuration
        app_config = Config()

        # Load configuration and device list
        config_data = parse_config_input(config)
        device_ids = parse_device_input(devices)

        cli_ctx.logger.info(f"Loaded configuration and {len(device_ids)} device IDs")

        if dry_run:
            cli_ctx.logger.info("DRY RUN MODE - No changes will be made")
            cli_ctx.logger.info(
                f"Would update {len(device_ids)} devices with configuration:"
            )
            cli_ctx.logger.info(json.dumps(config_data, indent=2))
            cli_ctx.logger.info("Device IDs:")
            for device_id in device_ids:
                cli_ctx.logger.info(f"  - {device_id}")
            cli_ctx.logger.info(f"Would use {max_concurrent} concurrent threads")
            return

        # Create updater with appropriate git logging settings
        # Disable particle-specific git logging if CLI git logging is enabled to avoid duplicates
        enable_particle_git_log = not no_particle_git_log and no_git_log

        updater = ParticleConfigUpdater(
            enable_git_logging=enable_particle_git_log, config=app_config
        )
        updater.max_retries = max_retries
        updater.restart_wait_time = restart_wait
        updater.online_check_timeout = online_timeout
        updater.max_concurrent_devices = max_concurrent

        # Create a simple args object for compatibility
        class Args:
            def __init__(self):
                self.config = config
                self.devices = devices
                self.note = note or "Configuration update"
                self.max_retries = max_retries
                self.restart_wait = restart_wait
                self.online_timeout = online_timeout
                self.max_concurrent = max_concurrent
                self.dry_run = dry_run

        args = Args()

        # Execute the update
        results = updater.update_multiple_devices(device_ids, config_data, args)

        # Save results
        save_results(results, output)

        # Log success to CLI git logger
        operation = f"Update configuration on {len(device_ids)} devices"

        parameters = {
            "config_source": config,
            "device_source": devices,
            "total_devices": len(device_ids),
            "max_retries": max_retries,
            "restart_wait": restart_wait,
            "online_timeout": online_timeout,
            "max_concurrent": max_concurrent,
            "dry_run": dry_run,
            "note": note,
        }

        cli_results = {
            "success": results["summary"]["failed"] == 0,
            "total_devices": results["summary"]["total_devices"],
            "successful_updates": results["summary"]["successful"],
            "failed_updates": results["summary"]["failed"],
            "success_rate": (
                results["summary"]["successful"]
                / results["summary"]["total_devices"]
                * 100
            ),
            "output_file": output,
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "note": note,
        }

        # Create device summary
        device_summary = ""
        for device_result in results["device_results"]:
            status = "✅" if device_result["success"] else "❌"
            device_summary += f"- {status} `{device_result['device_id']}` - "
            if device_result["success"]:
                device_summary += f"Success (System UID: {device_result.get('system_uid', 'N/A')}, Sensor UID: {device_result.get('sensor_uid', 'N/A')})\n"
            else:
                device_summary += (
                    f"Failed: {device_result.get('error', 'Unknown error')}\n"
                )

        additional_sections = {
            "Update Summary": f"- **Successful**: {results['summary']['successful']}/{results['summary']['total_devices']} devices\n- **Success Rate**: {cli_results['success_rate']:.1f}%\n- **Expected System UID**: {results['summary'].get('expected_system_uid', 'N/A')}\n- **Expected Sensor UID**: {results['summary'].get('expected_sensor_uid', 'N/A')}\n- **Results**: {output}",
            "Device List": device_summary.rstrip(),
            "Configuration Applied": f"```json\n{json.dumps(config_data, indent=2)}\n```",
        }

        cli_ctx.log_success(
            operation=operation,
            parameters=parameters,
            results=cli_results,
            script_path=__file__,
            additional_sections=additional_sections,
        )

        # Print summary
        click.echo(f"\nConfiguration update completed:")
        click.echo(f"  Total devices: {results['summary']['total_devices']}")
        click.echo(f"  Successful: {results['summary']['successful']}")
        click.echo(f"  Failed: {results['summary']['failed']}")
        click.echo(f"  Success rate: {cli_results['success_rate']:.1f}%")
        click.echo(f"  Results saved to: {output}")

        # Exit with error code if any devices failed
        if results["summary"]["failed"] > 0:
            sys.exit(1)

    except Exception as e:
        # Log error to CLI git logger
        parameters = {
            "config_source": config,
            "device_source": devices,
            "max_retries": max_retries,
            "note": note,
        }
        cli_ctx.log_error("Device configuration error", e, parameters, __file__)
        raise


@device_configuration_cli.command()
@click.argument("uid")
@add_common_options
@click.pass_context
@handle_common_errors("uid-decoding")
def decode_system(ctx, uid, verbose, log_file, no_git_log, note):
    """Decode system configuration UID."""
    cli_ctx = ctx.obj
    cli_ctx.setup("uid-decoding", verbose, log_file, no_git_log)

    try:
        parsed_uid = parse_uid(uid)
        output = format_system_config(parsed_uid)
        click.echo(output)

        # Log success
        operation = f"Decode system UID {uid}"
        parameters = {"uid": uid, "parsed_uid": parsed_uid, "note": note}
        results = {
            "success": True,
            "uid": parsed_uid,
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "note": note,
        }

        cli_ctx.log_success(
            operation=operation,
            parameters=parameters,
            results=results,
            script_path=__file__,
        )

    except Exception as e:
        parameters = {"uid": uid, "note": note}
        cli_ctx.log_error("System UID decoding error", e, parameters, __file__)
        raise


@device_configuration_cli.command()
@click.argument("uid")
@add_common_options
@click.pass_context
@handle_common_errors("uid-decoding")
def decode_sensor(ctx, uid, verbose, log_file, no_git_log, note):
    """Decode sensor configuration UID."""
    cli_ctx = ctx.obj
    cli_ctx.setup("uid-decoding", verbose, log_file, no_git_log)

    try:
        parsed_uid = parse_uid(uid)
        output = format_sensor_config(parsed_uid)
        click.echo(output)

        # Log success
        operation = f"Decode sensor UID {uid}"
        parameters = {"uid": uid, "parsed_uid": parsed_uid, "note": note}
        results = {
            "success": True,
            "uid": parsed_uid,
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "note": note,
        }

        cli_ctx.log_success(
            operation=operation,
            parameters=parameters,
            results=results,
            script_path=__file__,
        )

    except Exception as e:
        parameters = {"uid": uid, "note": note}
        cli_ctx.log_error("Sensor UID decoding error", e, parameters, __file__)
        raise


@device_configuration_cli.command()
@click.argument("system_uid")
@click.argument("sensor_uid")
@add_common_options
@click.pass_context
@handle_common_errors("uid-decoding")
def decode_both(ctx, system_uid, sensor_uid, verbose, log_file, no_git_log, note):
    """Decode both system and sensor configuration UIDs."""
    cli_ctx = ctx.obj
    cli_ctx.setup("uid-decoding", verbose, log_file, no_git_log)

    try:
        parsed_system_uid = parse_uid(system_uid)
        parsed_sensor_uid = parse_uid(sensor_uid)
        output = decode_both_configs(parsed_system_uid, parsed_sensor_uid)
        click.echo(output)

        # Log success
        operation = f"Decode both UIDs {system_uid} and {sensor_uid}"
        parameters = {
            "system_uid": system_uid,
            "sensor_uid": sensor_uid,
            "parsed_system_uid": parsed_system_uid,
            "parsed_sensor_uid": parsed_sensor_uid,
            "note": note,
        }
        results = {
            "success": True,
            "system_uid": parsed_system_uid,
            "sensor_uid": parsed_sensor_uid,
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "note": note,
        }

        cli_ctx.log_success(
            operation=operation,
            parameters=parameters,
            results=results,
            script_path=__file__,
        )

    except Exception as e:
        parameters = {
            "system_uid": system_uid,
            "sensor_uid": sensor_uid,
            "note": note,
        }
        cli_ctx.log_error("UID decoding error", e, parameters, __file__)
        raise


if __name__ == "__main__":
    device_configuration_cli()
