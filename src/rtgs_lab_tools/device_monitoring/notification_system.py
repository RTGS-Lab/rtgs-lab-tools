# should send email to email address with results of the operation


# send notification via email with the analysis result
# input: analysis_result dictionary
# output: None, but prints the notification to the console / sends email

import os
from dotenv import load_dotenv
import yagmail

yagmail.register('kennywyn706@gmail.com', None)
load_dotenv()  # Load environment variables from .env file

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_RECIPIENT = os.getenv("GMAIL_RECIPIENT")

# MVP version 1
# def notify(analysis_result):
#     if analysis_result["status"] == "flagged":
#         print("⚠️ ALERT: Battery issue detected!")
#         print(analysis_result["message"])
#     elif analysis_result["status"] == "ok":
#         print("✅ Battery status normal.")
#         print(analysis_result["message"])
#     elif analysis_result["status"] == "no_data":
#         print("ℹ️ No recent diagnostic data with Kestrel found.")


# MPV version (pre-email)
def notify(analysis_results):
    if isinstance(analysis_results, dict) and "status" in analysis_results:
        # Single node
        _notify_single(analysis_results)
    else:
        # Multiple nodes
        for node_id, result in analysis_results.items():
            print(f"\nNode: {node_id}")
            _notify_single(result)

def _notify_single(result):
    if result["status"] == "flagged":
        print("⚠️ ALERT: Battery issue detected!")
        print(result["message"])
    elif result["status"] == "ok":
        print("✅ Battery status normal.")
        print(result["message"])
    elif result["status"] == "no_data":
        print("ℹ️ No recent diagnostic data with Kestrel found.")
        print(result.get("message", ""))
    elif result["status"] == "unknown":
        print("❓ Battery voltage unknown.")
        print(result.get("message", ""))



def notify(analysis_results):
    email_lines = []
    if isinstance(analysis_results, dict) and "status" in analysis_results:
        # Single node
        email_lines.append(_notify_single(analysis_results))
    else:
        # Multiple nodes
        for node_id, result in analysis_results.items():
            email_lines.append(f"\nNode: {node_id}")
            print(f"\nNode: {node_id}")
            email_lines.append(_notify_single(result))
    # Send the email after printing
    _send_email("\n".join(email_lines))

def _notify_single(result):
    lines = []
    if result["status"] == "flagged":
        print("⚠️ ALERT: Battery issue detected!")
        print(result["message"])
        lines.append("⚠️ ALERT: Battery issue detected!")
        lines.append(result["message"])
    elif result["status"] == "ok":
        print("✅ Battery status normal.")
        print(result["message"])
        lines.append("✅ Battery status normal.")
        lines.append(result["message"])
    elif result["status"] == "no_data":
        print("ℹ️ No recent diagnostic data with Kestrel found.")
        print(result.get("message", ""))
        lines.append("ℹ️ No recent diagnostic data with Kestrel found.")
        lines.append(result.get("message", ""))
    elif result["status"] == "unknown":
        print("❓ Battery voltage unknown.")
        print(result.get("message", ""))
        lines.append("❓ Battery voltage unknown.")
        lines.append(result.get("message", ""))
    return ("\n".join(lines))

def _send_email(body):
    try:
        # yag = yagmail.SMTP(GMAIL_USER, GMAIL_APP_PASSWORD)
        yag = yagmail.SMTP(user=GMAIL_USER, password=GMAIL_APP_PASSWORD, oauth2_file=None)
        yag.send(
            to=GMAIL_RECIPIENT,
            subject="Battery & Error Notification Results",
            contents=body
        )
        print("\n📧 Notification email sent successfully.")
    except Exception as e:
        print(f"\n❌ Failed to send notification email: {e}")