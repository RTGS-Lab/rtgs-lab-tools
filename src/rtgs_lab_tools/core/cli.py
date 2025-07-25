"""Core CLI commands for RTGS Lab Tools."""

import sys

import click

from .update import check_for_updates, get_version_info, run_install_script


@click.group()
def core_cli():
    """Core utilities and system commands."""
    pass


@core_cli.command()
def update():
    """Check for updates and update to the latest release."""
    click.echo("Checking for updates...")

    has_update, current, message = check_for_updates()

    if has_update is None:
        click.echo(click.style(f"Warning: {message}", fg="yellow"))
        click.echo(f"Current version: {current}")
        return

    click.echo(f"Current version: {current}")

    if not has_update:
        click.echo(click.style(message, fg="green"))
        return

    click.echo(click.style(message, fg="yellow"))

    if click.confirm("Do you want to update now?"):
        if run_install_script():
            click.echo(click.style("Update completed successfully!", fg="green"))
            click.echo(
                "Please restart your terminal or reactivate your virtual environment."
            )
        else:
            click.echo(
                click.style("Update failed. Please check the output above.", fg="red")
            )
            sys.exit(1)
    else:
        click.echo("Update cancelled.")


@core_cli.command()
def version():
    """Show current version information."""
    version_info = get_version_info()

    click.echo(f"Current version: {version_info['current']}")
    if version_info["latest"]:
        click.echo(f"Latest release: {version_info['latest']}")
        if version_info["update_available"]:
            click.echo(
                click.style(
                    "Update available! Run 'rtgs core update' to update.", fg="yellow"
                )
            )
    else:
        click.echo("Could not fetch latest release information")


if __name__ == "__main__":
    core_cli()
