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
from datetime import datetime

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


def get_device_info(node_id):
    """Fetch device name and product_id from Particle API using node_id."""
    if not PARTICLE_ACCESS_TOKEN:
        return None, None
    
    try:
        url = f"https://api.particle.io/v1/devices/{node_id}"
        headers = {"Authorization": f"Bearer {PARTICLE_ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            device_data = response.json()
            name = device_data.get("name")
            product_id = device_data.get("product_id")
            return name, product_id
        else:
            return None, None
    except Exception:
        return None, None


def get_product_slug(product_id):
    """Fetch product slug from Particle API using product_id."""
    if not PARTICLE_ACCESS_TOKEN or not product_id:
        return None
    
    try:
        url = f"https://api.particle.io/v1/products/{product_id}"
        headers = {"Authorization": f"Bearer {PARTICLE_ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            product_data = response_data.get("product", {})
            return product_data.get("slug")
        else:
            return None
    except Exception:
        return None


def get_console_url(node_id, product_id, slug):
    """Generate Particle console URL for a device."""
    if not slug or not product_id:
        return None
    return f"https://console.particle.io/{slug}/devices/{node_id}"


def generate_device_card_html(node_id, result, device_name, console_url):
    """Generate HTML card for a single device with inline styles."""
    flagged = result.get("flagged", False)
    battery = result.get("battery")
    system = result.get("system")
    errors = result.get("errors", {})
    battery_timestamp = result.get("battery_timestamp")
    system_timestamp = result.get("system_timestamp")
    
    # Format timestamp
    timestamp = system_timestamp or battery_timestamp
    timestamp_str = "Unknown"
    if timestamp is not None:
        if hasattr(timestamp, "strftime"):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            timestamp_str = str(timestamp)
    
    # Format device name
    if device_name:
        device_display = f"{device_name} ({node_id})"
    else:
        device_display = node_id
    
    # Styling based on status
    border_color = "#dc3545" if flagged else "#28a745"
    status_bg = "#f8d7da" if flagged else "#d4edda"
    status_color = "#721c24" if flagged else "#155724"
    status_text = "⚠️ Alert" if flagged else "✅ Normal"
    
    # Format metrics
    battery_str = f"{battery:.2f}V" if battery is not None else "Unknown"
    system_str = f"{system:.3f}W" if system is not None else "Unknown"
    
    # Color code metrics
    battery_color = "#dc3545" if (battery is not None and battery < BATTERY_VOLTAGE_MIN) else "#28a745"
    system_color = "#fd7e14" if (system is not None and system > SYSTEM_POWER_MAX) else "#17a2b8"
    error_color = "#dc3545" if len(errors) > 0 else "#6c757d"
    
    # Console link
    console_link_html = ""
    if console_url:
        console_link_html = f'''
        <a href="{console_url}" style="display: inline-block; background-color: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; font-size: 14px; margin-top: 10px;">
            🔗 View in Particle Console
        </a>'''
    
    # Issues section
    issues_html = ""
    if flagged:
        issues = []
        if battery is not None and battery < BATTERY_VOLTAGE_MIN:
            issues.append(f"Battery LOW ({battery:.2f}V < {BATTERY_VOLTAGE_MIN}V)")
        if system is not None and system > SYSTEM_POWER_MAX:
            issues.append(f"System power HIGH ({system:.3f}W > {SYSTEM_POWER_MAX}W)")
        
        # Check for critical errors
        critical_errors = []
        for error_name, count in errors.items():
            if error_name in CRITICAL_ERRORS and count > 0:
                critical_errors.append(f"{error_name} ({count})")
        
        if critical_errors:
            issues.append(f"Critical errors: {', '.join(critical_errors)}")
        
        if issues:
            issues_list = "".join([f"<li>{issue}</li>" for issue in issues])
            issues_html = f'''
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 10px; margin-top: 10px;">
                <div style="font-weight: bold; color: #856404; margin-bottom: 5px;">🚨 Issues Detected:</div>
                <ul style="margin: 5px 0; padding-left: 20px;">
                    {issues_list}
                </ul>
            </div>'''
    
    return f'''
    <div style="background: white; border-radius: 8px; padding: 20px; margin-bottom: 15px; border-left: 4px solid {border_color}; font-family: Arial, sans-serif;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap;">
            <div style="font-weight: bold; font-size: 18px; color: #2c3e50;">{device_display}</div>
            <div style="padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase; background-color: {status_bg}; color: {status_color};">{status_text}</div>
        </div>
        
        <table style="width: 100%; margin-bottom: 15px;">
            <tr>
                <td style="text-align: center; padding: 10px; background-color: #f8f9fa; border-radius: 6px; width: 33%;">
                    <div style="font-size: 24px; font-weight: bold; margin-bottom: 5px; color: {battery_color};">{battery_str}</div>
                    <div style="font-size: 12px; color: #6c757d; text-transform: uppercase;">Battery</div>
                </td>
                <td style="width: 2%;"></td>
                <td style="text-align: center; padding: 10px; background-color: #f8f9fa; border-radius: 6px; width: 33%;">
                    <div style="font-size: 24px; font-weight: bold; margin-bottom: 5px; color: {system_color};">{system_str}</div>
                    <div style="font-size: 12px; color: #6c757d; text-transform: uppercase;">System Power</div>
                </td>
                <td style="width: 2%;"></td>
                <td style="text-align: center; padding: 10px; background-color: #f8f9fa; border-radius: 6px; width: 33%;">
                    <div style="font-size: 24px; font-weight: bold; margin-bottom: 5px; color: {error_color};">{len(errors)}</div>
                    <div style="font-size: 12px; color: #6c757d; text-transform: uppercase;">Errors</div>
                </td>
            </tr>
        </table>
        
        {issues_html}
        
        {console_link_html}
        
        <div style="font-size: 12px; color: #6c757d; margin-top: 10px;">Last updated: {timestamp_str}</div>
    </div>'''


def generate_html_email(analysis_results):
    """Generate complete HTML email from analysis results with inline styles."""
    device_cards = []
    normal_count = 0
    alert_count = 0
    
    for node_id, result in analysis_results.items():
        # Get device info
        device_name, product_id = get_device_info(node_id)
        
        # Get console URL
        console_url = None
        if product_id:
            slug = get_product_slug(product_id)
            if slug:
                console_url = get_console_url(node_id, product_id, slug)
        
        # Generate card HTML
        card_html = generate_device_card_html(node_id, result, device_name, console_url)
        device_cards.append(card_html)
        
        # Count status
        if result.get("flagged", False):
            alert_count += 1
        else:
            normal_count += 1
    
    # Get current timestamp
    current_time = datetime.now().strftime('%Y-%m-%d at %H:%M:%S')
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Device Monitoring Report</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
    <div style="background: #667eea; color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
        <h1 style="margin: 0 0 10px 0;">🔋 Device Monitoring Report</h1>
        <p style="margin: 0;">Environmental Sensor Network Status</p>
    </div>

    {"".join(device_cards)}

    <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; margin-top: 20px; font-family: Arial, sans-serif;">
        <h2 style="margin: 0 0 15px 0;">📊 Summary</h2>
        <p style="margin: 10px 0;"><strong>Total Nodes Analyzed:</strong> {len(analysis_results)}</p>
        <p style="margin: 10px 0;"><strong>Normal:</strong> {normal_count} devices | <strong>Alerts:</strong> {alert_count} devices</p>
        <p style="font-size: 12px; color: #6c757d; margin-top: 15px;">
            Generated on {current_time} | GEMS Environmental Monitoring System
        </p>
    </div>
</body>
</html>'''


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

        # Get device info from Particle API
        device_name, product_id = get_device_info(node_id)
        
        # Get console URL if we have the required info
        console_url = None
        if product_id:
            slug = get_product_slug(product_id)
            if slug:
                console_url = get_console_url(node_id, product_id, slug)
        
        # Format node display with console link
        if device_name:
            node_display = f"{device_name} ({node_id})"
        else:
            node_display = node_id
            
        if console_url:
            node_display += f" - Console: {console_url}"

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
    body = "\n".join(email_lines)  # Plain text fallback
    html_body = generate_html_email(analysis_results)  # HTML version
    
    if no_email:
        print("\n📧 Email notifications are disabled. Skipping email sending.")
    else:
        print("\n📧 Sending HTML notification email...")
        _send_email(subject, body, html_body)


def _send_email(subject, body, html_body=None):
    """Send email notification with optional HTML content."""
    try:
        yag = yagmail.SMTP(
            user=GMAIL_USER, password=GMAIL_APP_PASSWORD, oauth2_file=None
        )
        
        # If HTML body is provided, send HTML email
        if html_body:
            yag.send(to=GMAIL_RECIPIENTS, subject=subject, contents=html_body)
        else:
            yag.send(to=GMAIL_RECIPIENTS, subject=subject, contents=body)
            
        print(f"\n📧 Notification email sent: {subject}")
    except Exception as e:
        print(f"\n❌ Failed to send notification email: {e}")
