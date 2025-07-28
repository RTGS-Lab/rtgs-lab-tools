"""
Overview:
    - Sends notifications showing analyzed metrics for nodes specified in core.py.
    - Builds notification messages based on analysis results.
Inputs:
    - analysis_results: Dictionary with analysis results for each node.
Outputs:
    - Prints notification results to the console.
    - Sends an email with the notification results.
"""

import os
import requests

import yagmail
from dotenv import load_dotenv

from .config import BATTERY_VOLTAGE_MIN, CRITICAL_ERRORS, SYSTEM_POWER_MAX

load_dotenv()  # Load environment variables from .env file

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_RECIPIENT = os.getenv("GMAIL_RECIPIENT")
PARTICLE_ACCESS_TOKEN = os.getenv("PARTICLE_ACCESS_TOKEN")

# Parse comma-separated email addresses into a list
if GMAIL_RECIPIENT:
    GMAIL_RECIPIENTS = [email.strip() for email in GMAIL_RECIPIENT.split(",")]
else:
    GMAIL_RECIPIENTS = None


def get_device_name(node_id):
    """Fetch device name from Particle API using node_id."""
    if not PARTICLE_ACCESS_TOKEN:
        return None
    
    try:
        url = f"https://api.particle.io/v1/devices/{node_id}"
        headers = {"Authorization": f"Bearer {PARTICLE_ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            device_data = response.json()
            return device_data.get("name")
        else:
            return None
    except Exception:
        return None


def notify(analysis_results, no_email=False):
    """Send notifications showing all metrics for all nodes."""
    if not analysis_results:
        print("ℹ️ No analysis results to process.")
        return

    email_lines = []

    for node_id, result in analysis_results.items():

        # Determine status
        flagged = result.get("flagged", False)
        status_icon = "⚠️ ALERT" if flagged else "✅ Normal"

        # Get device name from Particle API
        device_name = get_device_name(node_id)
        if device_name:
            node_display = f"{device_name} ({node_id})"
        else:
            node_display = node_id

        # Get all metrics first
        battery = result.get("battery")
        system = result.get("system")
        errors = result.get("errors", {})
        battery_timestamp = result.get("battery_timestamp")
        system_timestamp = result.get("system_timestamp")

        # Format timestamp - use the most recent one available
        timestamp = system_timestamp or battery_timestamp
        timestamp_str = ""
        if timestamp is not None:
            if hasattr(timestamp, "strftime"):
                timestamp_str = f" [{timestamp.strftime('%Y-%m-%d %H:%M:%S')}]"
            else:
                timestamp_str = f" [{timestamp}]"

        print(f"\nNode: {node_display} - {status_icon}{timestamp_str}")
        email_lines.append(f"Node: {node_display} - {status_icon}{timestamp_str}")

        # Display metrics
        battery_str = f"{battery:.2f}V" if battery is not None else "Unknown"
        system_str = f"{system:.3f}W" if system is not None else "Unknown"

        metrics_line = f"  Battery: {battery_str} | System: {system_str} | Errors: {len(errors)} types"
        print(metrics_line)
        email_lines.append(metrics_line)

        # Show errors if any
        if errors:
            errors_line = f"  Error Details: {errors}"
            print(errors_line)
            email_lines.append(errors_line)

        # Generate status message
        if flagged:
            issues = []
            if battery is not None and battery < BATTERY_VOLTAGE_MIN:
                issues.append(f"Battery LOW ({battery:.2f}V < {BATTERY_VOLTAGE_MIN}V)")
            if system is not None and system > SYSTEM_POWER_MAX:
                issues.append(f"System power HIGH ({system:.3f} > {SYSTEM_POWER_MAX})")

            # Check for critical errors
            critical_errors = []
            for error_name, count in errors.items():
                if error_name in CRITICAL_ERRORS and count > 0:
                    critical_errors.append(f"{error_name} ({count})")

            if critical_errors:
                issues.append(f"Critical errors: {', '.join(critical_errors)}")

            message = f"  🚨 ISSUES: {' | '.join(issues)}"
        else:
            message = "  ✅ All systems operating normally"

        print(message)
        email_lines.append(message)
        email_lines.append("")  # Add spacing between nodes

    print("\nTotal Nodes Analyzed:", len(analysis_results))

    # include total number of nodes
    total_nodes = len(analysis_results)
    email_lines.append(f"\nTotal Nodes Analyzed: {total_nodes}")

    # Send email with all results
    subject = "Device Monitoring Report"
    body = "\n".join(email_lines)
    if no_email:
        print("\n📧 Email notifications are disabled. Skipping email sending.")
    else:
        print("\n📧 Sending notification email...")
        _send_email(subject, body)


def _send_email(subject, body):
    """Send email notification."""
    try:
        yag = yagmail.SMTP(
            user=GMAIL_USER, password=GMAIL_APP_PASSWORD, oauth2_file=None
        )
        yag.send(to=GMAIL_RECIPIENTS, subject=subject, contents=body)
        print(f"\n📧 Notification email sent: {subject}")
    except Exception as e:
        print(f"\n❌ Failed to send notification email: {e}")
