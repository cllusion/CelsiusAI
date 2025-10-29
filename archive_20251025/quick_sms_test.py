#!/usr/bin/env python3
"""
Quick Red Pocket SMS Test - Minimal Format
"""

import smtplib
from email.mime.text import MIMEText


def send_minimal_sms():
    """Send minimal SMS to Red Pocket number"""

    phone = "6264747175"
    sender_email = "ndrwcbllr@gmail.com"
    sender_password = "vaurjpguxdcxoxcr"

    # Try the most common gateway first
    gateways = [
        f"{phone}@txt.att.net",  # AT&T (most common for Red Pocket)
        f"{phone}@tmomail.net",  # T-Mobile
        f"{phone}@vtext.com",  # Verizon
    ]

    for i, gateway in enumerate(gateways, 1):
        try:
            print(f"Test {i}: Sending minimal SMS to {gateway}")

            # Minimal message
            msg = MIMEText(f"Test{i}")
            msg["From"] = sender_email
            msg["To"] = gateway
            # No subject for SMS

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()

            print(f"  ✅ Sent to {gateway}")

        except Exception as e:
            print(f"  ❌ Failed: {e}")

    print("\n📱 Check your phone for 'Test1', 'Test2', or 'Test3' messages")
    print("💭 If no SMS arrives in 2-3 minutes:")
    print("   • Red Pocket may not support email-to-SMS")
    print("   • Your plan might need SMS forwarding enabled")
    print("   • Email notifications are working fine as backup")


if __name__ == "__main__":
    send_minimal_sms()
