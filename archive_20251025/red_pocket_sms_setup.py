#!/usr/bin/env python3
"""
Red Pocket Mobile SMS Gateway Detector
Helps identify which network your Red Pocket service uses
"""


def detect_red_pocket_network():
    """Guide to identify Red Pocket network for SMS gateway"""

    print("🔍 RED POCKET MOBILE - SMS GATEWAY SETUP")
    print("=" * 50)

    print("\nRed Pocket operates on different carrier networks.")
    print("You need to identify which network YOUR plan uses:\n")

    networks = {
        "GSMA": {"network": "AT&T", "gateway": "@txt.att.net", "description": "AT&T Network (GSM)"},
        "GSMT": {"network": "T-Mobile", "gateway": "@tmomail.net", "description": "T-Mobile Network (GSM)"},
        "CDMA": {"network": "Verizon", "gateway": "@vtext.com", "description": "Verizon Network (CDMA)"},
        "CDMAS": {
            "network": "Sprint/T-Mobile",
            "gateway": "@tmomail.net",  # Now uses T-Mobile
            "description": "Sprint Network (now T-Mobile)",
        },
    }

    print("📋 RED POCKET NETWORK IDENTIFICATION:")
    for code, info in networks.items():
        print(f"  {code}: {info['description']} → {info['gateway']}")

    print("\n🔍 HOW TO FIND YOUR NETWORK:")
    print("1. Check your Red Pocket account/plan details")
    print("2. Look at your phone settings:")
    print("   - Android: Settings → About Phone → Network")
    print("   - iPhone: Settings → General → About → Carrier")
    print("3. Check your SIM card packaging")
    print("4. Test each gateway to see which works")

    print("\n🧪 TESTING METHOD:")
    print("Send a test email to: your_number@gateway")
    print("Example: 1234567890@txt.att.net")
    print("Try each gateway until you get an SMS")

    print("\n⚙️ FOR CELSIUS AI SETUP:")
    print("Once you identify your network, update the notifier:")
    print("self.sms_carrier = 'att'      # for GSMA")
    print("self.sms_carrier = 'tmobile'  # for GSMT/CDMAS")
    print("self.sms_carrier = 'verizon'  # for CDMA")

    return networks


def update_notifier_for_red_pocket():
    """Show how to update the notification system for Red Pocket"""

    print("\n📝 UPDATE CELSIUS AI NOTIFIER:")
    print("In celsius_intelligent_guardian_notifier.py, add Red Pocket support:")

    code_snippet = """
# Add this to the sms_gateways dictionary:
sms_gateways = {
    'verizon': '@vtext.com',        # Red Pocket CDMA
    'att': '@txt.att.net',          # Red Pocket GSMA  
    'tmobile': '@tmomail.net',      # Red Pocket GSMT/CDMAS
    'sprint': '@tmomail.net',       # Red Pocket CDMAS (legacy)
    'red_pocket_gsma': '@txt.att.net',     # Red Pocket on AT&T
    'red_pocket_gsmt': '@tmomail.net',     # Red Pocket on T-Mobile
    'red_pocket_cdma': '@vtext.com',       # Red Pocket on Verizon
    'red_pocket_cdmas': '@tmomail.net',    # Red Pocket on Sprint
    'google_voice': '@txt.voice.google.com'
}

# Set your carrier:
self.sms_carrier = 'red_pocket_gsma'  # Change based on your network
"""

    print(code_snippet)

    return code_snippet


if __name__ == "__main__":
    networks = detect_red_pocket_network()
    update_notifier_for_red_pocket()
