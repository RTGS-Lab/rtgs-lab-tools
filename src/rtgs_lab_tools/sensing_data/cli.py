"""CLI module for sensing data extraction tools."""

import sys
from datetime import datetime

import click

from ..core.cli_utils import (
    CLIContext,
    add_common_options,
    create_setup_credentials_command,
    handle_common_errors,
    sensing_data_parameters,
)
from ..sensing_data import extract_data, list_available_projects


@click.group()
@click.pass_context
def sensing_data_cli(ctx):
    """Sensing data extraction tools."""
    ctx.ensure_object(CLIContext)


@sensing_data_cli.command()
@sensing_data_parameters
@add_common_options
@click.pass_context
@handle_common_errors("data-extraction")
def extract(
    ctx,
    project,
    list_projects,
    setup_credentials,
    start_date,
    end_date,
    node_id,
    output_dir,
    output,
    create_zip,
    retry_count,
    verbose,
    log_file,
    no_postgres_log,
    note,
):
    """Extract sensing data from GEMS database."""
    cli_ctx = ctx.obj
    cli_ctx.setup("data-extraction", verbose, log_file, no_postgres_log)

    # Handle setup credentials
    if setup_credentials:
        setup_creds_cmd = create_setup_credentials_command()
        ctx.invoke(setup_creds_cmd)
        return

    # Handle list projects
    if list_projects:
        try:
            projects = list_available_projects(retry_count)
            if projects:
                click.echo("Available projects:")
                for project_name, node_count in projects:
                    click.echo(f"  {project_name} ({node_count} nodes)")
            else:
                click.echo("No projects found.")
        except Exception as e:
            cli_ctx.log_error("Project listing error", e, {"note": note}, __file__)
            raise
        return

    # Validate required arguments
    if not project:
        click.echo("Error: --project is required when not listing projects")
        sys.exit(1)

    try:
        # Use high-level extract_data function
        results = extract_data(
            project=project,
            start_date=start_date,
            end_date=end_date,
            node_ids=node_id,  # Function will parse the string
            output_dir=output_dir,
            output_format=output,
            create_zip=create_zip,
            retry_count=retry_count,
            note=note,
        )

        # Display results to user
        if results["records_extracted"] == 0:
            click.echo("No data found for the specified parameters")
            return

        if results["zip_file"]:
            click.echo(f"Created zip archive: {results['zip_file']}")
        else:
            click.echo(f"Data saved to: {results['output_file']}")

        click.echo(f"Successfully extracted {results['records_extracted']} records")

        # Log success to git
        operation = f"Extract data from project '{project}'"

        git_results = {
            "success": True,
            "records_extracted": results["records_extracted"],
            "output_file": results["output_file"],
            "start_time": cli_ctx.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "note": note,  # Add note to results for commit message
        }

        additional_sections = {
            "Data Summary": f"- **Records**: {results['records_extracted']}\n- **Output**: {results['output_file']}\n- **Format**: {output.upper()}"
        }

        if results["zip_file"]:
            additional_sections["Archive"] = f"- **Zip Archive**: {results['zip_file']}"

        cli_ctx.log_success(
            operation=operation,
            parameters=results,  # Use results dict which contains all parameters
            results=git_results,
            script_path=__file__,
            additional_sections=additional_sections,
        )

    except Exception as e:
        # Log error
        parameters = {
            "project": project,
            "start_date": start_date,
            "end_date": end_date,
            "node_ids": node_id,
            "output_format": output,
            "retry_count": retry_count,
            "note": note,
        }
        cli_ctx.log_error("Data extraction error", e, parameters, __file__)
        raise


@sensing_data_cli.command()
@add_common_options
@click.pass_context
@handle_common_errors("project-listing")
def list_projects_cmd(ctx, verbose, log_file, no_postgres_log, note):
    """List all available projects in the database."""
    cli_ctx = ctx.obj
    cli_ctx.setup("project-listing", verbose, log_file, no_postgres_log)

    try:
        projects = list_available_projects()
        if projects:
            click.echo("Available projects:")
            for project_name, node_count in projects:
                click.echo(f"  {project_name} ({node_count} nodes)")
        else:
            click.echo("No projects found.")
    except Exception as e:
        cli_ctx.log_error("Project listing error", e, {"note": note}, __file__)
        raise


if __name__ == "__main__":
    sensing_data_cli()
