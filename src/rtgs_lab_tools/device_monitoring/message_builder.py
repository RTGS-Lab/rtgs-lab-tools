"""
Overview:
    - Builds notification-ready messages from analysis results.
    - Handles both terminal text formatting and HTML email generation.
    - Contains HTML methods moved from notification_system.py.
Inputs:
    - analysis_results: Dictionary with analysis results for each node from data_analyzer.
Outputs:
    - Dictionary containing formatted messages ready for notification system:
        - terminal_message: Text formatted for console output
        - email_subject: Subject line for email
        - email_body_text: Plain text email body
        - email_body_html: HTML formatted email body
"""

import os
from datetime import datetime

import requests
from dotenv import load_dotenv

from .config import BATTERY_VOLTAGE_MIN, CRITICAL_ERRORS, SYSTEM_POWER_MAX

load_dotenv()  # Load environment variables from .env file

PARTICLE_ACCESS_TOKEN = os.getenv("PARTICLE_ACCESS_TOKEN")


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
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
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
    battery_color = (
        "#dc3545"
        if (battery is not None and battery < BATTERY_VOLTAGE_MIN)
        else "#28a745"
    )
    system_color = (
        "#fd7e14" if (system is not None and system > SYSTEM_POWER_MAX) else "#17a2b8"
    )
    error_color = "#dc3545" if len(errors) > 0 else "#6c757d"

    # Console link
    console_link_html = ""
    if console_url:
        console_link_html = f"""
        <a href="{console_url}" style="display: inline-block; background-color: #007bff; color: white; padding: 6px 12px; text-decoration: none; border-radius: 3px; font-size: 12px; margin-top: 6px;">
            🔗 View in Particle Console
        </a>"""

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
            issues_html = f"""
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 3px; padding: 8px; margin-top: 6px;">
                <div style="font-weight: bold; color: #856404; margin-bottom: 3px; font-size: 12px;">🚨 Issues Detected:</div>
                <ul style="margin: 3px 0; padding-left: 16px; font-size: 11px;">
                    {issues_list}
                </ul>
            </div>"""

    return f"""
    <div style="background: white; border-radius: 6px; padding: 12px; margin-bottom: 10px; border-left: 4px solid {border_color}; font-family: Arial, sans-serif;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap;">
            <div style="font-weight: bold; font-size: 16px; color: #2c3e50;">{device_display}</div>
            <div style="padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; text-transform: uppercase; background-color: {status_bg}; color: {status_color};">{status_text}</div>
        </div>
        
        <table style="width: 100%; margin-bottom: 8px;">
            <tr>
                <td style="text-align: center; padding: 8px; background-color: #f8f9fa; border-radius: 4px; width: 33%;">
                    <div style="font-size: 20px; font-weight: bold; margin-bottom: 3px; color: {battery_color};">{battery_str}</div>
                    <div style="font-size: 11px; color: #6c757d; text-transform: uppercase;">Battery</div>
                </td>
                <td style="width: 2%;"></td>
                <td style="text-align: center; padding: 8px; background-color: #f8f9fa; border-radius: 4px; width: 33%;">
                    <div style="font-size: 20px; font-weight: bold; margin-bottom: 3px; color: {system_color};">{system_str}</div>
                    <div style="font-size: 11px; color: #6c757d; text-transform: uppercase;">System Power</div>
                </td>
                <td style="width: 2%;"></td>
                <td style="text-align: center; padding: 8px; background-color: #f8f9fa; border-radius: 4px; width: 33%;">
                    <div style="font-size: 20px; font-weight: bold; margin-bottom: 3px; color: {error_color};">{len(errors)}</div>
                    <div style="font-size: 11px; color: #6c757d; text-transform: uppercase;">Errors</div>
                </td>
            </tr>
        </table>
        
        {issues_html}
        
        {console_link_html}
        
        <div style="font-size: 11px; color: #6c757d; margin-top: 6px;">Last updated: {timestamp_str}</div>
    </div>"""


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
    current_time = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Device Monitoring Report</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.4; color: #333; max-width: 800px; margin: 0 auto; padding: 15px; background-color: #f5f5f5;">
    <div style="background: #667eea; color: white; padding: 15px; border-radius: 6px; text-align: center; margin-bottom: 15px;">
        <h1 style="margin: 0 0 6px 0; font-size: 20px;">🔋 Device Monitoring Report</h1>
        <p style="margin: 0; font-size: 14px;">Environmental Sensor Network Status</p>
    </div>

    {"".join(device_cards)}

    <div style="background: white; padding: 15px; border-radius: 6px; text-align: center; margin-top: 15px; font-family: Arial, sans-serif;">
        <h2 style="margin: 0 0 10px 0; font-size: 16px;">📊 Summary</h2>
        <p style="margin: 6px 0; font-size: 14px;"><strong>Total Nodes Analyzed:</strong> {len(analysis_results)}</p>
        <p style="margin: 6px 0; font-size: 14px;"><strong>Normal:</strong> {normal_count} devices | <strong>Alerts:</strong> {alert_count} devices</p>
        <p style="font-size: 11px; color: #6c757d; margin-top: 10px;">
            Generated on {current_time} | GEMS Environmental Monitoring System
        </p>
    </div>
</body>
</html>"""


def build_terminal_message(analysis_results):
    """Build terminal message from analysis results."""
    if not analysis_results:
        return "ℹ️ No analysis results to process."

    terminal_lines = []

    # Separate missing nodes from active nodes
    missing_nodes = {}
    active_nodes = {}

    for node_id, result in analysis_results.items():
        if result.get("is_missing", False):
            missing_nodes[node_id] = result
        else:
            active_nodes[node_id] = result

    # Process missing nodes first
    if missing_nodes:
        terminal_lines.append("\n🚨 MISSING NODES (Not heard from in 24+ hours):")
        terminal_lines.append("=" * 60)

    for node_id, result in missing_nodes.items():

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

        terminal_lines.append(f"\nNode: {node_display} - {status_icon}{timestamp_str}")

        # Display metrics
        battery_str = f"{battery:.2f}V" if battery is not None else "Unknown"
        system_str = f"{system:.3f}W" if system is not None else "Unknown"

        metrics_line = f"  Battery: {battery_str} | System: {system_str} | Errors: {len(errors)} types"
        terminal_lines.append(metrics_line)

        # Show errors if any
        if errors:
            errors_line = f"  Error Details: {errors}"
            terminal_lines.append(errors_line)

        # Check if this is a missing node
        is_missing = result.get("is_missing", False)
        last_heard = result.get("last_heard")

        # Generate status message
        if is_missing:
            # Handle missing node alert
            if last_heard:
                time_diff = datetime.now() - last_heard
                if time_diff.days > 0:
                    time_str = f"{time_diff.days} days"
                else:
                    hours = time_diff.seconds // 3600
                    time_str = f"{hours} hours"
            else:
                time_str = "unknown time"

            message = f"  ⚠️ MISSING: Node hasn't written to database in {time_str}"
            if last_heard:
                last_heard_str = (
                    last_heard.strftime("%Y-%m-%d %H:%M:%S")
                    if hasattr(last_heard, "strftime")
                    else str(last_heard)
                )
                message += f". Last heard from {last_heard_str}"

                # Include last known metrics
                if battery is not None or system is not None:
                    metrics_parts = []
                    if battery is not None:
                        metrics_parts.append(f"Battery: {battery:.2f}V")
                    if system is not None:
                        metrics_parts.append(f"System: {system:.3f}W")
                    if errors:
                        metrics_parts.append(f"Errors: {errors}")
                    if metrics_parts:
                        message += f" with {', '.join(metrics_parts)}"

        elif flagged:
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

        terminal_lines.append(message)

    # Process active nodes
    if active_nodes:
        terminal_lines.append("\n\n✅ ACTIVE NODES (Recent activity):")
        terminal_lines.append("=" * 40)

    for node_id, result in active_nodes.items():
        # Same processing logic as missing nodes but without the missing-specific handling
        flagged = result.get("flagged", False)
        status_icon = "⚠️ ALERT" if flagged else "✅ Normal"

        device_name, product_id = get_device_info(node_id)
        console_url = None
        if product_id:
            slug = get_product_slug(product_id)
            if slug:
                console_url = get_console_url(node_id, product_id, slug)

        if device_name:
            node_display = f"{device_name} ({node_id})"
        else:
            node_display = node_id

        if console_url:
            node_display += f" - Console: {console_url}"

        battery = result.get("battery")
        system = result.get("system")
        errors = result.get("errors", {})
        battery_timestamp = result.get("battery_timestamp")
        system_timestamp = result.get("system_timestamp")

        timestamp = system_timestamp or battery_timestamp
        timestamp_str = ""
        if timestamp is not None:
            if hasattr(timestamp, "strftime"):
                timestamp_str = f" [{timestamp.strftime('%Y-%m-%d %H:%M:%S')}]"
            else:
                timestamp_str = f" [{timestamp}]"

        terminal_lines.append(f"\nNode: {node_display} - {status_icon}{timestamp_str}")

        battery_str = f"{battery:.2f}V" if battery is not None else "Unknown"
        system_str = f"{system:.3f}W" if system is not None else "Unknown"
        metrics_line = f"  Battery: {battery_str} | System: {system_str} | Errors: {len(errors)} types"
        terminal_lines.append(metrics_line)

        if errors:
            errors_line = f"  Error Details: {errors}"
            terminal_lines.append(errors_line)

        if flagged:
            issues = []
            if battery is not None and battery < BATTERY_VOLTAGE_MIN:
                issues.append(f"Battery LOW ({battery:.2f}V < {BATTERY_VOLTAGE_MIN}V)")
            if system is not None and system > SYSTEM_POWER_MAX:
                issues.append(
                    f"System power HIGH ({system:.3f}W > {SYSTEM_POWER_MAX}W)"
                )

            critical_errors = []
            for error_name, count in errors.items():
                if error_name in CRITICAL_ERRORS and count > 0:
                    critical_errors.append(f"{error_name} ({count})")

            if critical_errors:
                issues.append(f"Critical errors: {', '.join(critical_errors)}")

            message = f"  🚨 ISSUES: {' | '.join(issues)}"
        else:
            message = "  ✅ All systems operating normally"

        terminal_lines.append(message)

    # Summary
    missing_count = len(missing_nodes)
    active_count = len(active_nodes)
    terminal_lines.append(f"\n📊 SUMMARY:")
    terminal_lines.append(f"Total Nodes Analyzed: {len(analysis_results)}")
    terminal_lines.append(
        f"Missing Nodes: {missing_count} | Active Nodes: {active_count}"
    )

    return "\n".join(terminal_lines)


def build_email_message(analysis_results):
    """Build email message from analysis results."""
    if not analysis_results:
        return "ℹ️ No analysis results to process."

    email_lines = []

    # Separate missing nodes from active nodes
    missing_nodes = {}
    active_nodes = {}

    for node_id, result in analysis_results.items():
        if result.get("is_missing", False):
            missing_nodes[node_id] = result
        else:
            active_nodes[node_id] = result

    # Process missing nodes first
    if missing_nodes:
        email_lines.append("🚨 MISSING NODES (Not heard from in 24+ hours):")
        email_lines.append("=" * 60)

    for node_id, result in missing_nodes.items():

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

        email_lines.append(f"Node: {node_display} - {status_icon}{timestamp_str}")

        # Display metrics
        battery_str = f"{battery:.2f}V" if battery is not None else "Unknown"
        system_str = f"{system:.3f}W" if system is not None else "Unknown"

        metrics_line = f"  Battery: {battery_str} | System: {system_str} | Errors: {len(errors)} types"
        email_lines.append(metrics_line)

        # Show errors if any
        if errors:
            errors_line = f"  Error Details: {errors}"
            email_lines.append(errors_line)

        # Check if this is a missing node
        is_missing = result.get("is_missing", False)
        last_heard = result.get("last_heard")

        # Generate status message
        if is_missing:
            # Handle missing node alert
            if last_heard:
                time_diff = datetime.now() - last_heard
                if time_diff.days > 0:
                    time_str = f"{time_diff.days} days"
                else:
                    hours = time_diff.seconds // 3600
                    time_str = f"{hours} hours"
            else:
                time_str = "unknown time"

            message = f"  ⚠️ MISSING: Node hasn't written to database in {time_str}"
            if last_heard:
                last_heard_str = (
                    last_heard.strftime("%Y-%m-%d %H:%M:%S")
                    if hasattr(last_heard, "strftime")
                    else str(last_heard)
                )
                message += f". Last heard from {last_heard_str}"

                # Include last known metrics
                if battery is not None or system is not None:
                    metrics_parts = []
                    if battery is not None:
                        metrics_parts.append(f"Battery: {battery:.2f}V")
                    if system is not None:
                        metrics_parts.append(f"System: {system:.3f}W")
                    if errors:
                        metrics_parts.append(f"Errors: {errors}")
                    if metrics_parts:
                        message += f" with {', '.join(metrics_parts)}"

        elif flagged:
            issues = []
            if battery is not None and battery < BATTERY_VOLTAGE_MIN:
                issues.append(f"Battery LOW ({battery:.2f}V < {BATTERY_VOLTAGE_MIN}V)")
            if system is not None and system > SYSTEM_POWER_MAX:
                issues.append(
                    f"System power HIGH ({system:.3f}W > {SYSTEM_POWER_MAX}W)"
                )

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

        email_lines.append(message)
        email_lines.append("")  # Add spacing between nodes

    # Process active nodes
    if active_nodes:
        email_lines.append("\n\n✅ ACTIVE NODES (Recent activity):")
        email_lines.append("=" * 40)

    for node_id, result in active_nodes.items():
        flagged = result.get("flagged", False)
        status_icon = "⚠️ ALERT" if flagged else "✅ Normal"

        device_name, product_id = get_device_info(node_id)
        console_url = None
        if product_id:
            slug = get_product_slug(product_id)
            if slug:
                console_url = get_console_url(node_id, product_id, slug)

        if device_name:
            node_display = f"{device_name} ({node_id})"
        else:
            node_display = node_id

        if console_url:
            node_display += f" - Console: {console_url}"

        battery = result.get("battery")
        system = result.get("system")
        errors = result.get("errors", {})
        battery_timestamp = result.get("battery_timestamp")
        system_timestamp = result.get("system_timestamp")

        timestamp = system_timestamp or battery_timestamp
        timestamp_str = ""
        if timestamp is not None:
            if hasattr(timestamp, "strftime"):
                timestamp_str = f" [{timestamp.strftime('%Y-%m-%d %H:%M:%S')}]"
            else:
                timestamp_str = f" [{timestamp}]"

        email_lines.append(f"Node: {node_display} - {status_icon}{timestamp_str}")

        battery_str = f"{battery:.2f}V" if battery is not None else "Unknown"
        system_str = f"{system:.3f}W" if system is not None else "Unknown"
        metrics_line = f"  Battery: {battery_str} | System: {system_str} | Errors: {len(errors)} types"
        email_lines.append(metrics_line)

        if errors:
            errors_line = f"  Error Details: {errors}"
            email_lines.append(errors_line)

        if flagged:
            issues = []
            if battery is not None and battery < BATTERY_VOLTAGE_MIN:
                issues.append(f"Battery LOW ({battery:.2f}V < {BATTERY_VOLTAGE_MIN}V)")
            if system is not None and system > SYSTEM_POWER_MAX:
                issues.append(
                    f"System power HIGH ({system:.3f}W > {SYSTEM_POWER_MAX}W)"
                )

            critical_errors = []
            for error_name, count in errors.items():
                if error_name in CRITICAL_ERRORS and count > 0:
                    critical_errors.append(f"{error_name} ({count})")

            if critical_errors:
                issues.append(f"Critical errors: {', '.join(critical_errors)}")

            message = f"  🚨 ISSUES: {' | '.join(issues)}"
        else:
            message = "  ✅ All systems operating normally"

        email_lines.append(message)
        email_lines.append("")  # Add spacing between nodes

    # Summary
    missing_count = len(missing_nodes)
    active_count = len(active_nodes)
    email_lines.append("📊 SUMMARY:")
    email_lines.append(f"Total Nodes Analyzed: {len(analysis_results)}")
    email_lines.append(f"Missing Nodes: {missing_count} | Active Nodes: {active_count}")

    return "\n".join(email_lines)


def build_message(analysis_results):
    """
    Build notification messages from analysis results.

    Args:
        analysis_results: Dictionary with analysis results for each node from data_analyzer

    Returns:
        Dictionary containing formatted messages:
            - terminal_message: Text formatted for console output
            - email_subject: Subject line for email
            - email_body_text: Plain text email body
            - email_body_html: HTML formatted email body
    """
    if not analysis_results:
        return {
            "terminal_message": "ℹ️ No analysis results to process.",
            "email_subject": "Device Monitoring Report - No Data",
            "email_body_text": "ℹ️ No analysis results to process.",
            "email_body_html": "<p>ℹ️ No analysis results to process.</p>",
        }

    # Build terminal message
    terminal_message = build_terminal_message(analysis_results)

    # Build email components
    email_subject = "Device Monitoring Report"
    email_body_text = build_email_message(analysis_results)
    # email_body_html = generate_html_email(analysis_results)
    email_body_html = None  # Placeholder for HTML email generation

    return {
        "terminal_message": terminal_message,
        "email_subject": email_subject,
        "email_body_text": email_body_text,
        "email_body_html": email_body_html,
    }
