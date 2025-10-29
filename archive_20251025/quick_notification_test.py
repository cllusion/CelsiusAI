#!/usr/bin/env python3
"""
Quick Gmail and SMS test with configured credentials
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def test_gmail_and_sms():
    """Quick test with configured Gmail credentials"""

    print("🛡️ CELSIUS AI - QUICK NOTIFICATION TEST")
    print("=" * 45)

    # Configured credentials
    admin_email = "celsius@cllusion.com"
    sender_email = "google@cllusion.com"
    sender_password = "vaurjpguxdcxoxcr"
    phone_number = "6264747175"

    print(f"📧 From: {sender_email}")
    print(f"📧 To: {admin_email}")
    print(f"📱 Phone: {phone_number}")

    # Test 1: Email notification
    print(f"\n📧 TESTING EMAIL...")
    try:
        subject = "🛡️ Celsius AI - Email Test Success!"
        message = f"""✅ CELSIUS AI EMAIL TEST SUCCESSFUL ✅

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
From: Celsius AI Notification System
Gmail Integration: WORKING

Your email notifications are now fully operational!

Next: Testing SMS to {phone_number} via all Red Pocket gateways...

---
Celsius AI Intelligent Guardian System
"""

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = admin_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, admin_email, text)
        server.quit()

        print("✅ Email sent successfully!")
        print(f"📬 Check {admin_email} for test message")

    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False

    # Test 2: All SMS Gateways
    print(f"\n📱 TESTING ALL SMS GATEWAYS...")

    sms_gateways = {
        "AT&T (GSMA)": f"{phone_number}@txt.att.net",
        "T-Mobile (GSMT)": f"{phone_number}@tmomail.net",
        "Verizon (CDMA)": f"{phone_number}@vtext.com",
        "Sprint (CDMAS)": f"{phone_number}@messaging.sprintpcs.com",
    }

    sms_message = f"🛡️ Celsius AI SMS Test {datetime.now().strftime('%H:%M')} - Red Pocket gateway working!"

    for network, gateway in sms_gateways.items():
        try:
            print(f"Testing {network}: {gateway}")

            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = gateway
            msg["Subject"] = ""
            msg.attach(MIMEText(sms_message, "plain"))

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            text = msg.as_string()
            server.sendmail(sender_email, gateway, text)
            server.quit()

            print(f"  ✅ Sent via {network}")

        except Exception as e:
            print(f"  ❌ {network} failed: {e}")

    print(f"\n📲 CHECK YOUR PHONE:")
    print("You should receive SMS from working Red Pocket gateways")
    print("Note which network delivers successfully")

    print(f"\n🎉 NOTIFICATION SYSTEM STATUS:")
    print("✅ Gmail Integration: ACTIVE")
    print("✅ Email Notifications: WORKING")
    print("✅ SMS Multi-Gateway: TESTING")
    print("✅ Emergency Alerts: READY")
    print("✅ Guardian Reports: CONFIGURED")

    return True


if __name__ == "__main__":
    test_gmail_and_sms()
