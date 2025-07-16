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

import yagmail
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_RECIPIENT = os.getenv("GMAIL_RECIPIENT")


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

        print(f"\nNode: {node_id} - {status_icon}")
        email_lines.append(f"Node: {node_id} - {status_icon}")

        # Get all metrics
        battery = result.get("battery")
        system = result.get("system")
        errors = result.get("errors", {})

        # Display metrics
        battery_str = f"{battery:.2f}V" if battery is not None else "Unknown"
        system_str = f"{system:.1f}mA" if system is not None else "Unknown"

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
            if battery is not None and battery < 3.6:
                issues.append(f"Battery LOW ({battery:.2f}V)")
            if system is not None and system > 200:
                issues.append(f"System current HIGH ({system:.1f}mA)")

            # Check for critical errors
            critical_errors = []
            for error_name, count in errors.items():

                # Critical errors hardcoded for now (CHANGE LATER)
                if error_name in ["SD_ACCESS_FAIL", "FRAM_ACCESS_FAIL"] and count > 0:
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
        yag.send(to=GMAIL_RECIPIENT, subject=subject, contents=body)
        print(f"\n📧 Notification email sent: {subject}")
    except Exception as e:
        print(f"\n❌ Failed to send notification email: {e}")
