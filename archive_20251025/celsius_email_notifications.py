#!/usr/bin/env python3
"""
Celsius AI Email Notification System
Provides email alerts for security events and system status
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
from pathlib import Path


class CelsiusEmailNotifier:
    def __init__(self):
        self.config_file = Path(__file__).parent / "email_config.json"
        self.load_config()

    def load_config(self):
        """Load email configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
            else:
                # Create default config
                self.config = {
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "sender_email": "",
                    "sender_password": "",
                    "recipient_email": "",
                    "enabled": False,
                }
                self.save_config()
        except Exception as e:
            print(f"Failed to load email config: {e}")
            self.config = {"enabled": False}

    def save_config(self):
        """Save email configuration to file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Failed to save email config: {e}")

    def setup_email(self, sender_email, sender_password, recipient_email, smtp_server="smtp.gmail.com", smtp_port=587):
        """Setup email configuration"""
        self.config.update(
            {
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "sender_email": sender_email,
                "sender_password": sender_password,
                "recipient_email": recipient_email,
                "enabled": True,
            }
        )
        self.save_config()
        print("✅ Email configuration saved successfully")
        return self.test_email_connection()

    def test_email_connection(self):
        """Test email connection and send test message"""
        if not self.config.get("enabled", False):
            print("❌ Email not configured")
            return False

        try:
            message = MIMEMultipart()
            message["From"] = self.config["sender_email"]
            message["To"] = self.config["recipient_email"]
            message["Subject"] = "Celsius AI - Email Test"

            body = f"""
🛡️ Celsius AI Email Notification Test

✅ Email system is working properly
📅 Test sent: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This confirms your email notifications are configured correctly.

Best regards,
Celsius AI Defense System
            """

            message.attach(MIMEText(body, "plain"))

            context = ssl.create_default_context()
            with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
                server.starttls(context=context)
                server.login(self.config["sender_email"], self.config["sender_password"])
                server.sendmail(self.config["sender_email"], self.config["recipient_email"], message.as_string())

            print("✅ Test email sent successfully!")
            return True

        except Exception as e:
            print(f"❌ Email test failed: {e}")
            return False

    def send_threat_alert(self, threat_type, details, severity="HIGH"):
        """Send threat detection alert"""
        if not self.config.get("enabled", False):
            return False

        subject = f"🚨 Celsius AI - {severity} Threat Alert: {threat_type}"

        body = f"""
🚨 SECURITY ALERT - Celsius AI Defense System

⚠️ Threat Type: {threat_type}
📊 Severity Level: {severity}
🕐 Detection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 Details:
{details}

🛡️ Recommended Actions:
- Review system immediately
- Check Celsius AI dashboard for more details
- Consider disconnecting affected systems if high severity

This is an automated alert from Celsius AI Defense System.
        """

        return self._send_email(subject, body)

    def send_system_status(self, status_type, message):
        """Send system status notification"""
        if not self.config.get("enabled", False):
            return False

        subject = f"📊 Celsius AI - System Status: {status_type}"

        body = f"""
📊 Celsius AI System Status Update

📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📋 Status: {status_type}

Message:
{message}

🔗 Dashboard: http://localhost:5000

This is an automated status update from Celsius AI.
        """

        return self._send_email(subject, body)

    def send_daily_report(self, threats_detected, scans_completed, system_health):
        """Send daily security report"""
        if not self.config.get("enabled", False):
            return False

        subject = f"📈 Celsius AI - Daily Security Report {datetime.now().strftime('%Y-%m-%d')}"

        body = f"""
📈 Daily Security Report - Celsius AI Defense System

📅 Report Date: {datetime.now().strftime('%Y-%m-%d')}

📊 Summary:
🚨 Threats Detected: {threats_detected}
🔍 Scans Completed: {scans_completed}
💚 System Health: {system_health}

🛡️ Protection Status: Active
🔄 Last Update: {datetime.now().strftime('%H:%M:%S')}

Access full details at: http://localhost:5000

Stay secure,
Celsius AI Defense System
        """

        return self._send_email(subject, body)

    def _send_email(self, subject, body):
        """Internal method to send email"""
        try:
            message = MIMEMultipart()
            message["From"] = self.config["sender_email"]
            message["To"] = self.config["recipient_email"]
            message["Subject"] = subject

            message.attach(MIMEText(body, "plain"))

            context = ssl.create_default_context()
            with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
                server.starttls(context=context)
                server.login(self.config["sender_email"], self.config["sender_password"])
                server.sendmail(self.config["sender_email"], self.config["recipient_email"], message.as_string())

            print(f"📧 Email sent: {subject}")
            return True

        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False


def setup_email_interactive():
    """Interactive setup for email notifications"""
    notifier = CelsiusEmailNotifier()

    print("📧 Celsius AI Email Notification Setup")
    print("=" * 50)

    sender_email = input("Enter sender email (Gmail recommended): ")
    sender_password = input("Enter email password or app password: ")
    recipient_email = input("Enter recipient email (can be same as sender): ")

    print("\n🔄 Testing email configuration...")
    success = notifier.setup_email(sender_email, sender_password, recipient_email)

    if success:
        print("\n✅ Email notifications are now configured!")
        print("🚨 You will receive alerts for:")
        print("   • Security threats")
        print("   • System status changes")
        print("   • Daily security reports")
    else:
        print("\n❌ Email configuration failed")
        print("💡 For Gmail, you may need to:")
        print("   • Enable 2-factor authentication")
        print("   • Generate an app-specific password")
        print("   • Use the app password instead of your regular password")


def send_test_notification():
    """Send a test notification"""
    notifier = CelsiusEmailNotifier()
    return notifier.test_email_connection()


if __name__ == "__main__":
    setup_email_interactive()
