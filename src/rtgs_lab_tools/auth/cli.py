"""CLI commands for Google Cloud authentication."""

import click
from rich.console import Console
from rich.table import Table

from .auth_service import AuthService

console = Console()


@click.group()
def auth_cli():
    """Google Cloud authentication commands."""
    pass


@auth_cli.command("login")
@click.option(
    "--headless",
    is_flag=True,
    help="Use headless authentication (no browser) for terminal-only environments",
)
def login(headless):
    """Authenticate with Google Cloud for Secret Manager access."""
    auth_service = AuthService()

    console.print(
        "🔐 [bold blue]RTGS Lab Tools - Google Cloud Authentication[/bold blue]"
    )
    console.print()

    # Check if gcloud is installed first
    if not auth_service.check_gcloud_installed():
        console.print("❌ [bold red]gcloud CLI not found[/bold red]")
        console.print()
        console.print(auth_service.install_gcloud_instructions())
        return

    # Check current status
    status = auth_service.get_auth_status()
    if status["authenticated"] and status["secret_manager_access"]:
        console.print(
            f"✅ Already authenticated as: [bold green]{status['user']}[/bold green]"
        )
        console.print(f"✅ Secret Manager access: [bold green]Working[/bold green]")
        if status["project"]:
            console.print(f"✅ Project: [bold green]{status['project']}[/bold green]")
        console.print()
        console.print(
            "You're already set up! Run [bold blue]rtgs sensing-data list-projects[/bold blue] to get started."
        )
        return

    # Show headless mode info
    if headless:
        console.print(
            "🖥️  [bold yellow]Headless Mode:[/bold yellow] Authentication will not open a browser"
        )
        console.print("📋 You'll need to copy a URL and verification code manually")
        console.print()

    # Perform login
    if headless:
        # Don't use spinner for headless mode as user needs to see the output
        result = auth_service.login(headless=True)
    else:
        with console.status(
            "[bold blue]Authenticating with Google Cloud...", spinner="dots"
        ):
            result = auth_service.login(headless=False)

    console.print()

    if result["success"]:
        console.print("✅ [bold green]Authentication successful![/bold green]")
        console.print()
        console.print(f"👤 User: [bold]{result.get('user', 'Unknown')}[/bold]")
        if result.get("project"):
            console.print(f"📋 Project: [bold]{result['project']}[/bold]")

        if result.get("secret_manager_access"):
            console.print("🔐 Secret Manager access: [bold green]Working[/bold green]")
        else:
            console.print(
                "⚠️  Secret Manager access: [bold yellow]Limited[/bold yellow]"
            )
            console.print(
                "   Contact your administrator for Secret Manager permissions"
            )

        console.print()
        console.print("[bold blue]Next steps:[/bold blue]")
        console.print("1. Your credentials are now configured")
        console.print("2. Test with: [bold]rtgs sensing-data list-projects[/bold]")
        console.print("3. Documentation: [bold]rtgs --help[/bold]")

    else:
        console.print("❌ [bold red]Authentication failed[/bold red]")
        console.print(f"Error: {result['error']}")

        if "instructions" in result:
            console.print()
            console.print(result["instructions"])


@auth_cli.command("status")
def status():
    """Check Google Cloud authentication status."""
    auth_service = AuthService()

    console.print("🔐 [bold blue]Google Cloud Authentication Status[/bold blue]")
    console.print()

    auth_status = auth_service.get_auth_status()

    # Create status table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="dim", width=25)
    table.add_column("Status", width=15)
    table.add_column("Details", style="dim")

    # gcloud CLI
    if auth_status["gcloud_installed"]:
        table.add_row("gcloud CLI", "✅ Installed", "")
    else:
        table.add_row(
            "gcloud CLI",
            "❌ Missing",
            "Run 'rtgs auth login' for installation instructions",
        )

    # Authentication
    if auth_status["authenticated"]:
        table.add_row("Authentication", "✅ Active", f"User: {auth_status['user']}")
    else:
        table.add_row("Authentication", "❌ Not authenticated", "Run 'rtgs auth login'")

    # Project
    if auth_status["project"]:
        table.add_row("Project", "✅ Set", auth_status["project"])
    else:
        table.add_row(
            "Project", "⚠️  Not set", "Run 'gcloud config set project PROJECT_ID'"
        )

    # Secret Manager
    if auth_status["secret_manager_access"]:
        table.add_row("Secret Manager", "✅ Accessible", "Ready to use secrets")
    elif auth_status["authenticated"]:
        table.add_row(
            "Secret Manager", "❌ No access", "Contact admin for IAM permissions"
        )
    else:
        table.add_row("Secret Manager", "❌ No access", "Authentication required")

    console.print(table)
    console.print()

    # Recommendations
    if not auth_status["authenticated"]:
        console.print(
            "[bold yellow]Recommendation:[/bold yellow] Run [bold]rtgs auth login[/bold] to authenticate"
        )
    elif not auth_status["secret_manager_access"]:
        console.print(
            "[bold yellow]Recommendation:[/bold yellow] Contact your administrator for Secret Manager permissions"
        )
    elif not auth_status["project"]:
        console.print(
            "[bold yellow]Recommendation:[/bold yellow] Set your project with [bold]gcloud config set project PROJECT_ID[/bold]"
        )
    else:
        console.print(
            "✅ [bold green]All systems ready![/bold green] You can use RTGS Lab Tools with Secret Manager."
        )


@auth_cli.command("particle-login")
def particle_login():
    """Authenticate with Particle Cloud and create a temporary access token."""
    import os
    import subprocess

    console.print("🔌 [bold blue]Particle Cloud Authentication[/bold blue]")
    console.print()
    console.print(
        "This will create a temporary 7-day access token using the Particle CLI."
    )
    console.print("You'll need to login with your Particle credentials when prompted.")
    console.print()

    # Check if particle CLI is installed
    try:
        subprocess.run(["particle", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("❌ [bold red]Particle CLI not found[/bold red]")
        console.print()
        console.print("Please install the Particle CLI first:")
        console.print("npm install -g particle-cli")
        console.print(
            "or visit: https://docs.particle.io/tutorials/developer-tools/cli/"
        )
        return

    try:
        # Create token with 7-day expiry
        console.print("Creating Particle access token (expires in 7 days)...")
        console.print("You may be prompted to login to your Particle account.")
        console.print()

        # Run interactively to allow user login
        console.print("Running: particle token create --expires-in 604800")
        console.print("(This may prompt for your Particle credentials)")
        console.print()

        result = subprocess.run(
            ["particle", "token", "create", "--expires-in", "604800"]
        )

        if result.returncode == 0:
            console.print()
            console.print("Token created successfully!")

            # Now get the token by asking user to paste it
            console.print(
                "Please copy the token from the output above and paste it here:"
            )
            token = click.prompt("Particle token", type=str).strip()

            if token and len(token) == 40:
                # Write to .env file
                env_file_path = os.path.join(os.getcwd(), ".env")

                # Read existing .env content
                env_lines = []
                if os.path.exists(env_file_path):
                    with open(env_file_path, "r") as f:
                        env_lines = f.readlines()

                # Remove any existing PARTICLE_ACCESS_TOKEN line
                env_lines = [
                    line
                    for line in env_lines
                    if not line.strip().startswith("PARTICLE_ACCESS_TOKEN=")
                ]

                # Add new token
                env_lines.append(f"PARTICLE_ACCESS_TOKEN={token}\n")

                # Write back to .env file
                with open(env_file_path, "w") as f:
                    f.writelines(env_lines)

                console.print(
                    "✅ [bold green]Particle authentication successful![/bold green]"
                )
                console.print()
                console.print(f"🔑 Access token created and saved to .env file")
                console.print(f"⏰ Token expires in 7 days")
                console.print()
                console.print("[bold blue]Next steps:[/bold blue]")
                console.print("1. Your Particle MCP server should now work")
                console.print("2. Token will automatically expire in 7 days")
                console.print("3. Run this command again when the token expires")
            else:
                console.print("❌ [bold red]Invalid token format[/bold red]")
                console.print("Particle tokens should be 40 characters long")
        else:
            console.print("❌ [bold red]Token creation failed[/bold red]")
            console.print("Please check your Particle CLI installation and credentials")

    except Exception as e:
        console.print("❌ [bold red]Error creating token[/bold red]")
        console.print(f"Error: {str(e)}")


@auth_cli.command("logout")
def logout():
    """Logout from Google Cloud."""
    auth_service = AuthService()

    console.print("🔐 [bold blue]Google Cloud Logout[/bold blue]")
    console.print()

    # Check current status
    status = auth_service.get_auth_status()
    if not status["authenticated"]:
        console.print("ℹ️  [bold yellow]Not currently authenticated[/bold yellow]")
        return

    console.print(f"Currently authenticated as: [bold]{status['user']}[/bold]")
    console.print()

    if click.confirm("Are you sure you want to logout?"):
        with console.status("[bold blue]Logging out...", spinner="dots"):
            result = auth_service.logout()

        console.print()
        if result["success"]:
            console.print("✅ [bold green]Successfully logged out[/bold green]")
            console.print(
                "Your application will now fall back to .env file credentials"
            )
        else:
            console.print("❌ [bold red]Logout failed[/bold red]")
            console.print(f"Error: {result['error']}")
    else:
        console.print("Logout cancelled")


if __name__ == "__main__":
    auth_cli()
