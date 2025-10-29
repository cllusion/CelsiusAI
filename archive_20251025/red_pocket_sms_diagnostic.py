#!/usr/bin/env python3
"""
Red Pocket SMS Diagnostic Tool
Tests each gateway individually with delays to identify which network works
"""

import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


class RedPocketSMSDiagnostic:
    """Diagnose Red Pocket SMS gateway issues"""

    def __init__(self):
        self.phone = "6264747175"
        self.sender_email = "ndrwcbllr@gmail.com"
        self.sender_password = "vaurjpguxdcxoxcr"

        # Test each gateway individually
        self.gateways = {
            "1_ATT": f"{self.phone}@txt.att.net",
            "2_TMobile": f"{self.phone}@tmomail.net",
            "3_Verizon": f"{self.phone}@vtext.com",
            "4_Sprint": f"{self.phone}@messaging.sprintpcs.com",
        }

    def send_test_sms(self, gateway_name, gateway_email, test_number):
        """Send individual test SMS"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            message = f"Test {test_number}: {gateway_name} @ {timestamp}"

            print(f"Sending Test {test_number} to {gateway_name}: {gateway_email}")

            # Create email
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = gateway_email
            msg["Subject"] = ""  # Empty subject for SMS

            msg.attach(MIMEText(message, "plain"))

            # Send via Gmail
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            text = msg.as_string()
            server.sendmail(self.sender_email, gateway_email, text)
            server.quit()

            print(f"  ✅ Email sent to {gateway_email}")
            return True

        except Exception as e:
            print(f"  ❌ Failed: {e}")
            return False

    def run_sequential_test(self):
        """Run sequential SMS tests with delays"""

        print("📱 RED POCKET SMS DIAGNOSTIC TEST")
        print("=" * 40)
        print(f"Phone: {self.phone}")
        print(f"Testing {len(self.gateways)} gateways with 30-second delays")
        print("Watch your phone for incoming SMS messages!")
        print()

        results = {}
        test_number = 1

        for gateway_name, gateway_email in self.gateways.items():
            print(f"🧪 TEST {test_number}/4: {gateway_name}")

            success = self.send_test_sms(gateway_name, gateway_email, test_number)
            results[gateway_name] = success

            if success:
                print(f"📲 Check your phone for SMS from {gateway_name}")
                print("⏳ Waiting 30 seconds before next test...")
                time.sleep(30)

            test_number += 1
            print()

        return results

    def show_results_and_next_steps(self, results):
        """Show test results and troubleshooting steps"""

        print("📊 TEST RESULTS SUMMARY")
        print("=" * 30)

        for gateway, success in results.items():
            status = "✅ SENT" if success else "❌ FAILED"
            print(f"{gateway}: {status}")

        print("\n🔍 TROUBLESHOOTING GUIDE:")
        print("1. Check which SMS messages (if any) you received")
        print("2. Note the gateway name that delivered successfully")
        print("3. If NO SMS received, try these solutions:")

        print("\n💡 POSSIBLE SOLUTIONS:")
        print("• Red Pocket SMS forwarding may be disabled")
        print("• Your Red Pocket plan might not support SMS via email")
        print("• Email-to-SMS delay (can take 1-5 minutes)")
        print("• Try different message format")

        print("\n📋 NEXT STEPS IF NO SMS:")
        print("1. Wait 5 more minutes for delayed delivery")
        print("2. Check Red Pocket account settings for SMS forwarding")
        print("3. Consider using Twilio for reliable SMS ($1/month)")
        print("4. Use email notifications only (already working)")

        print(f"\n🔄 RE-TEST SPECIFIC GATEWAY:")
        print("If you received SMS from a specific gateway, we can")
        print("configure Celsius AI to use that gateway primarily.")


def main():
    """Run the diagnostic"""

    diagnostic = RedPocketSMSDiagnostic()

    print("🚀 Starting Red Pocket SMS diagnostic...")
    print("This will send 4 test messages with 30-second delays")

    proceed = input("Ready to start? (y/n): ").strip().lower()

    if proceed != "y":
        print("Test cancelled. Run again when ready.")
        return

    results = diagnostic.run_sequential_test()
    diagnostic.show_results_and_next_steps(results)


if __name__ == "__main__":
    main()
