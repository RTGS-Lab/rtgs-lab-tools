"""
Overview:
    - Sends notifications using pre-built messages from message_builder.
    - Only handles email sending and terminal printing, no message construction.
Inputs:
    - message_dict: Dictionary with pre-built messages from message_builder containing:
        - terminal_message: Text formatted for console output
        - email_subject: Subject line for email
        - email_body_text: Plain text email body
        - email_body_html: HTML formatted email body
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

# Parse comma-separated email addresses into a list
if GMAIL_RECIPIENT:
    GMAIL_RECIPIENTS = [email.strip() for email in GMAIL_RECIPIENT.split(",")]
else:
    GMAIL_RECIPIENTS = None


def notify(message_dict, no_email=False):
    """Send notifications using pre-built messages from message_builder."""
    if not message_dict:
        print("ℹ️ No message data to process.")
        return

    # Print terminal message
    terminal_message = message_dict.get("terminal_message", "No terminal message available.")
    print(terminal_message)

    # Send email if requested
    if no_email:
        print("\n📧 Email notifications are disabled. Skipping email sending.")
    else:
        print("\n📧 Sending notification email...")
        subject = message_dict.get("email_subject", "Device Monitoring Report")
        body_text = message_dict.get("email_body_text", "No email body available.")
        body_html = message_dict.get("email_body_html", None)
        
        # Use HTML email if available, otherwise fall back to text
        if body_html:
            _send_email_html(subject, body_text, body_html)
        else:
            _send_email(subject, body_text)


def _send_email(subject, body):
    """Send plain text email notification."""
    try:
        yag = yagmail.SMTP(
            user=GMAIL_USER, password=GMAIL_APP_PASSWORD, oauth2_file=None
        )
        yag.send(to=GMAIL_RECIPIENTS, subject=subject, contents=body)
        print(f"\n📧 Notification email sent: {subject}")
    except Exception as e:
        print(f"\n❌ Failed to send notification email: {e}")


def _send_email_html(subject, body_text, body_html):
    """Send HTML email notification with text fallback."""
    try:
        yag = yagmail.SMTP(
            user=GMAIL_USER, password=GMAIL_APP_PASSWORD, oauth2_file=None
        )
        # Send both text and HTML versions
        contents = [body_text, body_html]
        yag.send(to=GMAIL_RECIPIENTS, subject=subject, contents=contents)
        print(f"\n📧 HTML notification email sent: {subject}")
    except Exception as e:
        print(f"\n❌ Failed to send HTML notification email: {e}")
        # Fallback to text email
        print("Attempting to send text-only email as fallback...")
        _send_email(subject, body_text)
