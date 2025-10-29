#!/usr/bin/env python3
"""
Celsius AI - Enhanced Asynchronous Email Notification System
===========================================================

Description:
------------
This script provides a robust, asynchronous, and enhanced email notification
system for the Celsius AI ecosystem. It handles sending alerts for security
events and system status changes using modern async libraries for high performance.

Key Features:
-------------
- **Fully Asynchronous**: Uses `aiosmtplib`, `aiosqlite`, and `aiofiles` for
  non-blocking operations, ensuring the AI's event loop is never stalled.
- **Persistent Configuration**: Saves SMTP settings to a JSON file asynchronously.
- **Asynchronous Notification Logging**: Records every notification attempt to a
  local SQLite database without blocking.
- **HTML-Formatted Emails**: Sends visually appealing HTML emails.
- **Priority Headers**: Supports high-priority emails for critical alerts.
- **Interactive Async Setup**: Includes an async command-line function to
  easily configure email settings.
- **Graceful Error Handling**: Manages and logs errors gracefully in an async context.

Dependencies:
-------------
- `aiosmtplib`: For sending emails asynchronously.
- `aiosqlite`: For asynchronous database operations.
- `aiofiles`: For asynchronous file I/O.

Usage:
------
This module is intended to be imported and used by other async components.
It can also be run directly to trigger the interactive setup:

    python src/utils/enhanced_email_system.py
"""

import asyncio
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
from pathlib import Path
import logging
from typing import Dict, Any, Optional

import aiosmtplib
import aiosqlite
import aiofiles

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class EnhancedEmailNotifier:
    """
    Manages the configuration, sending, and logging of email notifications
    in an asynchronous manner.
    """

    def __init__(self):
        """Initializes the notifier, setting up paths and default config."""
        self.base_dir = Path(__file__).resolve().parent
        self.config_file = self.base_dir / "email_config.json"
        self.notification_db = self.base_dir.parent.parent / "data" / "celsius_notifications.db"

        self.config: Dict[str, Any] = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "",
            "sender_password": "",
            "recipient_email": "",
            "enabled": False,
        }
        self._db_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """
        Asynchronously initializes the notifier, loading configuration and
        ensuring the database is ready.
        """
        await self.load_config()
        await self.initialize_database()

    async def load_config(self) -> None:
        """
        Asynchronously loads email configuration from the JSON file.
        If the file doesn't exist or is invalid, it uses default settings.
        """
        if not self.config_file.exists():
            return
        try:
            async with aiofiles.open(self.config_file, "r") as f:
                content = await f.read()
                saved_config = json.loads(content)
                self.config.update(saved_config)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load email config. Using defaults. Error: {e}")

    async def save_config(self) -> None:
        """Asynchronously saves the current email configuration to the JSON file."""
        try:
            async with aiofiles.open(self.config_file, "w") as f:
                await f.write(json.dumps(self.config, f, indent=4))
        except IOError as e:
            logger.error(f"Failed to save email config: {e}")

    async def initialize_database(self) -> None:
        """
        Asynchronously initializes the SQLite database for logging notifications.
        """
        try:
            self.notification_db.parent.mkdir(exist_ok=True)
            async with self._db_lock:
                async with aiosqlite.connect(self.notification_db) as db:
                    await db.execute(
                        """
                        CREATE TABLE IF NOT EXISTS notifications (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            notification_type TEXT NOT NULL,
                            subject TEXT NOT NULL,
                            recipient TEXT NOT NULL,
                            success INTEGER NOT NULL,
                            error_message TEXT
                        )
                    """
                    )
                    await db.commit()
        except aiosqlite.Error as e:
            logger.error(f"Could not initialize notification database: {e}")

    async def configure_email(
        self, smtp_server: str, smtp_port: int, sender_email: str, sender_password: str, recipient_email: str
    ) -> None:
        """Asynchronously updates the email configuration and saves it."""
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
        await self.save_config()

    async def send_notification(
        self, notification_type: str, subject: str, message: str, priority: str = "normal"
    ) -> bool:
        """
        Asynchronously sends an email notification and logs the attempt.
        """
        if not self.is_configured():
            await self.log_notification(
                notification_type,
                subject,
                "Email not configured",
                False,
                "Attempted to send but system is not configured.",
            )
            return False

        try:
            msg = self._create_email_message(notification_type, subject, message, priority)

            await aiosmtplib.send(
                msg,
                hostname=self.config["smtp_server"],
                port=self.config["smtp_port"],
                username=self.config["sender_email"],
                password=self.config["sender_password"],
                start_tls=True,
            )

            await self.log_notification(notification_type, subject, self.config["recipient_email"], True, None)
            logger.info(f"✅ Email notification sent successfully: '{subject}'")
            return True

        except aiosmtplib.SMTPException as e:
            error_msg = str(e)
            await self.log_notification(
                notification_type, subject, self.config.get("recipient_email", "unknown"), False, error_msg
            )
            logger.error(f"❌ Failed to send email notification: {error_msg}")
            return False

    def _create_email_message(self, notification_type: str, subject: str, message: str, priority: str) -> MIMEMultipart:
        """Constructs the MIMEMultipart email message with HTML formatting."""
        # This method remains synchronous as it's CPU-bound.
        msg = MIMEMultipart()
        msg["From"] = self.config["sender_email"]
        msg["To"] = self.config["recipient_email"]
        msg["Subject"] = f"[Celsius AI] {subject}"

        if priority == "high":
            msg["X-Priority"] = "1 (Highest)"
            msg["X-MSMail-Priority"] = "High"

        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f7f6; padding: 20px;">
                <div style="max-width: 600px; margin: auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                    <h2 style="color: #005a9e; border-bottom: 2px solid #005a9e; padding-bottom: 10px;">🛡️ Celsius AI Notification</h2>
                    <div style="background-color: #eaf3fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <strong>Type:</strong> {notification_type}<br>
                        <strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                        <strong>Priority:</strong> {priority.upper()}
                    </div>
                    <div>
                        <h3 style="color: #333;">Details:</h3>
                        <p style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; line-height: 1.6;">
                            {message.replace(chr(10), '<br>')}
                        </p>
                    </div>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #888; font-size: 12px; text-align: center;">
                        This is an automated notification from the Celsius AI Personal Cybersecurity Assistant.
                    </p>
                </div>
            </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))
        return msg

    async def log_notification(
        self, notification_type: str, subject: str, recipient: str, success: bool, error_message: Optional[str] = None
    ) -> None:
        """Asynchronously logs a notification attempt to the SQLite database."""
        try:
            async with self._db_lock:
                async with aiosqlite.connect(self.notification_db) as db:
                    await db.execute(
                        """
                        INSERT INTO notifications (timestamp, notification_type, subject, recipient, success, error_message)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            datetime.now().isoformat(),
                            notification_type,
                            subject,
                            recipient,
                            int(success),
                            error_message,
                        ),
                    )
                    await db.commit()
        except aiosqlite.Error as e:
            logger.error(f"Could not log notification to database: {e}")

    async def send_security_alert(self, threat_type: str, details: str, severity: str = "medium") -> bool:
        """Sends a pre-formatted security alert email asynchronously."""
        subject = f"Security Alert: {threat_type}"
        message = f"""A security event has been detected by your Celsius AI system.

**Threat Type:** {threat_type}
**Severity:** {severity.upper()}
**Detection Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Details:**
{details}

**Recommended Actions:**
- Review system logs for suspicious activity.
- Verify the integrity of critical files.
- Isolate the system if the threat is severe.

This is an automated alert.
"""
        priority = "high" if severity in ["high", "critical"] else "normal"
        return await self.send_notification("SECURITY_ALERT", subject, message, priority)

    async def send_system_notification(self, event_type: str, details: str) -> bool:
        """Sends a pre-formatted system event notification asynchronously."""
        subject = f"System Event: {event_type}"
        message = f"""A system event has occurred.

**Event:** {event_type}
**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Details:**
{details}
"""
        return await self.send_notification("SYSTEM_EVENT", subject, message)

    async def send_test_notification(self) -> bool:
        """Sends a test notification to verify the email configuration asynchronously."""
        subject = "Celsius AI - Test Notification"
        message = f"""This is a test notification to confirm that your Celsius AI email system is working correctly.

- **Configuration:** ✅ Loaded
- **SMTP Connection:** ✅ Ready to Connect
- **Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

If you have received this email, your notification system is properly configured and ready to send alerts.
"""
        return await self.send_notification("TEST", subject, message)

    def is_configured(self) -> bool:
        """Checks if the email system has all necessary configuration values."""
        required = ["sender_email", "sender_password", "recipient_email", "smtp_server", "smtp_port"]
        return self.config.get("enabled", False) and all(self.config.get(field) for field in required)


# Lazily-created singleton accessor to avoid import-time side-effects.
_enhanced_notifier = None


def get_enhanced_notifier() -> EnhancedEmailNotifier:
    """Return a shared EnhancedEmailNotifier instance, creating it lazily.

    Creation is fast (no I/O); callers that need the notifier to be fully
    initialized should call `await notifier.initialize()` separately.
    """
    global _enhanced_notifier
    if _enhanced_notifier is None:
        _enhanced_notifier = EnhancedEmailNotifier()
    return _enhanced_notifier


async def setup_email_system():
    """
    An interactive async command-line function to guide the user through setting up
    their email notification settings.
    """
    print("\n" + "=" * 50)
    print("🔧 Celsius AI Enhanced Email Notification Setup 🔧")
    print("=" * 50)

    notifier = get_enhanced_notifier()
    await notifier.initialize()

    if notifier.is_configured():
        print(f"\n✅ System is already configured for: {notifier.config['recipient_email']}")
        choice = input(
            "\nChoose an option:\n  1. Send a test email\n  2. Reconfigure\n  3. Exit\nEnter option (1-3): "
        ).strip()

        if choice == "1":
            print("\n📧 Sending test email...")
            if await notifier.send_test_notification():
                print("✅ Test email sent successfully!")
            else:
                print("❌ Test email failed. Please check credentials and reconfigure.")
            return
        elif choice != "2":
            print("\nExiting setup.")
            return

    print("\nPlease provide your email configuration details.")
    print("Note: For Gmail, you must use an 'App Password'.")

    sender_email = input("\nSender Email (e.g., your.email@gmail.com): ").strip()
    sender_password = input("App Password: ").strip()
    recipient_email = input("Recipient Email (for alerts): ").strip()

    if all([sender_email, sender_password, recipient_email]):
        await notifier.configure_email("smtp.gmail.com", 587, sender_email, sender_password, recipient_email)
        print("\n✅ Email configuration saved!")

        print("\n📧 Sending a confirmation test email...")
        if await notifier.send_test_notification():
            print("✅ Test email sent successfully! Notifications are active.")
        else:
            print("❌ Failed to send test email. Please re-check your configuration.")
    else:
        print("\n❌ Setup cancelled. All fields are required.")


async def main():
    """Main entry point for the script."""
    try:
        await setup_email_system()
    except (KeyboardInterrupt, EOFError):
        print("\n\nSetup interrupted. Exiting.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
