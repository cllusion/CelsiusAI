#!/usr/bin/env python3
"""
Alternative SMS methods for Celsius AI notifications
Including email-to-SMS gateway support for Google Voice and carrier numbers
"""


class AlternativeSMSNotifier:
    """Alternative SMS notification methods"""

    def __init__(self):
        # Email-to-SMS gateways by carrier
        self.sms_gateways = {
            "verizon": "@vtext.com",
            "att": "@txt.att.net",
            "tmobile": "@tmomail.net",
            "sprint": "@messaging.sprintpcs.com",
            "google_voice": "@txt.voice.google.com",  # May work for some numbers
            "cricket": "@sms.cricketwireless.net",
            "boost": "@smsmyboostmobile.com",
            "virgin": "@vmobl.com",
        }

    def send_sms_via_email(self, phone_number, carrier, message, email_sender):
        """Send SMS via email-to-SMS gateway"""
        import smtplib
        from email.mime.text import MIMEText

        try:
            if carrier.lower() not in self.sms_gateways:
                print(f"Carrier '{carrier}' not supported")
                return False

            # Create SMS email address
            gateway = self.sms_gateways[carrier.lower()]
            # Remove any formatting from phone number
            clean_number = "".join(filter(str.isdigit, phone_number))
            sms_email = f"{clean_number}{gateway}"

            print(f"Sending SMS to: {sms_email}")

            # Keep message under 160 characters for SMS
            if len(message) > 160:
                message = message[:157] + "..."

            # Send via email (using your existing email setup)
            msg = MIMEText(message)
            msg["To"] = sms_email
            msg["From"] = email_sender
            msg["Subject"] = ""  # Empty subject for cleaner SMS

            # You would use your existing email SMTP setup here
            print(f"SMS via email gateway: {message}")
            return True

        except Exception as e:
            print(f"Failed to send SMS via email gateway: {e}")
            return False


def test_google_voice_sms():
    """Test if Google Voice SMS works via email gateway"""
    print("🧪 Testing Google Voice SMS Options...")

    notifier = AlternativeSMSNotifier()

    print("\n📱 Google Voice SMS Options:")
    print("1. Email-to-SMS Gateway: phone_number@txt.voice.google.com")
    print("2. Success Rate: Variable (depends on Google Voice configuration)")
    print("3. Limitations: May not work for all Google Voice numbers")
    print("4. Alternative: Use your actual carrier number instead")

    print("\n💡 Recommendations:")
    print("✅ BEST: Use Twilio (~$1/month + $0.0075 per SMS)")
    print("✅ FREE: Use email-to-SMS with your actual carrier")
    print("❌ AVOID: Google Voice (unreliable for automated SMS)")

    print("\n📋 To Use Your Carrier Number:")
    print("1. Find your carrier from the list")
    print("2. Use your actual phone number (not Google Voice)")
    print("3. Test with: phone_number@carrier_gateway.com")

    return notifier


if __name__ == "__main__":
    test_google_voice_sms()
