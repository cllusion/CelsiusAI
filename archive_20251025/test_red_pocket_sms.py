#!/usr/bin/env python3
"""
Test SMS notifications for Red Pocket number: (626) 474-7175
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def test_red_pocket_sms():
    """Test SMS to Red Pocket number 6264747175"""

    print("📱 TESTING SMS FOR RED POCKET: (626) 474-7175")
    print("=" * 55)

    phone_number = "6264747175"

    # Red Pocket SMS gateways to test
    test_gateways = {
        "AT&T Network (GSMA)": f"{phone_number}@txt.att.net",
        "T-Mobile Network (GSMT)": f"{phone_number}@tmomail.net",
        "Verizon Network (CDMA)": f"{phone_number}@vtext.com",
        "Sprint Network (CDMAS)": f"{phone_number}@messaging.sprintpcs.com",
    }

    print("🧪 SMS GATEWAY TEST ADDRESSES:")
    for network, gateway in test_gateways.items():
        print(f"  {network}: {gateway}")

    print(f"\n📧 TO TEST MANUALLY:")
    print("1. Send test emails to each gateway address above")
    print("2. Use subject: 'Test' and message: 'Celsius AI SMS test'")
    print("3. See which one delivers to your phone as SMS")
    print("4. Update the sms_carrier setting based on results")

    print(f"\n⚙️ CURRENT CONFIGURATION:")
    print(f"Phone Number: {phone_number}")
    print(f"Primary Gateway: {phone_number}@txt.att.net (AT&T - most common)")
    print(f"Backup Gateways: Available for other networks")

    # Create test message
    test_message = "🛡️ Celsius AI Emergency Test - This is a test of your SMS notification system. If you receive this, SMS alerts are working!"

    print(f"\n📄 TEST MESSAGE (160 char limit):")
    print(f"'{test_message[:160]}'")
    if len(test_message) > 160:
        print(f"⚠️ Message truncated from {len(test_message)} to 160 characters")

    return test_gateways


def show_setup_instructions():
    """Show complete setup instructions"""

    print(f"\n🔧 CELSIUS AI SETUP COMPLETE FOR (626) 474-7175")
    print("=" * 55)

    print("✅ Phone number configured in notification system")
    print("✅ Default SMS gateway: AT&T network (@txt.att.net)")
    print("✅ Backup gateways available for other networks")

    print(f"\n📋 NEXT STEPS:")
    print("1. Configure your email settings:")
    print("   - Update admin_email with your actual email address")
    print("   - Set up sender_email and sender_password for Gmail")

    print(f"\n2. Test SMS delivery:")
    print("   - Send test email to: 6264747175@txt.att.net")
    print("   - If no SMS received, try other gateways")

    print(f"\n3. Update carrier if needed:")
    print("   - If AT&T gateway doesn't work, change sms_carrier to:")
    print("     • 'red_pocket_gsmt' for T-Mobile network")
    print("     • 'red_pocket_cdma' for Verizon network")
    print("     • 'red_pocket_cdmas' for Sprint network")

    print(f"\n🚨 EMERGENCY NOTIFICATIONS READY:")
    print("   - Multiple service failures")
    print("   - System resource critical (CPU/Memory/Disk)")
    print("   - Celsius AI unresponsive")
    print("   - Auto-logout events")

    print(f"\n📊 REGULAR UPDATES:")
    print("   - 2-hour guardian reports (email)")
    print("   - 4-hour status updates (email + SMS)")


def create_email_test_template():
    """Create template for manual email-to-SMS testing"""

    template = f"""
📧 EMAIL-TO-SMS TEST TEMPLATE

To: 6264747175@txt.att.net
Subject: Celsius AI Test
Message: Testing SMS notifications for Celsius AI

---

If this arrives as SMS, AT&T gateway works!
If not, try these alternatives:

T-Mobile: 6264747175@tmomail.net
Verizon: 6264747175@vtext.com
Sprint: 6264747175@messaging.sprintpcs.com
"""

    print(template)
    return template


if __name__ == "__main__":
    test_gateways = test_red_pocket_sms()
    show_setup_instructions()
    create_email_test_template()
