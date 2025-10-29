#!/usr/bin/env python3
"""
Direct Celsius AI Startup - Bypasses Guardian issues
Starts Server Hub and Enhanced Dashboard directly
"""

import subprocess
import sys
import time
import requests
from pathlib import Path


def start_services():
    """Start Celsius AI services directly"""
    base_dir = Path(__file__).parent

    print("🚀 Starting Celsius AI Services Directly...")
    print("=" * 50)

    # Start Server Hub (GUI)
    print("📱 Starting Server Hub...")
    try:
        server_hub = subprocess.Popen(
            [sys.executable, "celsius_server_hub.py"], cwd=str(base_dir), creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        print(f"✅ Server Hub started with PID: {server_hub.pid}")
    except Exception as e:
        print(f"❌ Failed to start Server Hub: {e}")

    time.sleep(3)

    # Start Enhanced Dashboard (API)
    print("📊 Starting Enhanced Dashboard...")
    try:
        dashboard = subprocess.Popen([sys.executable, "enhanced_mobile_dashboard.py"], cwd=str(base_dir))
        print(f"✅ Enhanced Dashboard started with PID: {dashboard.pid}")

        # Wait and verify dashboard
        print("🔍 Verifying dashboard startup...")
        time.sleep(8)

        attempts = 0
        while attempts < 10:
            try:
                response = requests.get("http://localhost:5000/api/status", timeout=3)
                if response.status_code == 200:
                    print("✅ Enhanced Dashboard verified and responding!")
                    break
            except:
                pass
            attempts += 1
            time.sleep(2)

        if attempts >= 10:
            print("⚠️ Dashboard started but not responding to health checks")

    except Exception as e:
        print(f"❌ Failed to start Enhanced Dashboard: {e}")

    print("\n🎯 Celsius AI Services Started!")
    print("📱 Server Hub: Running (GUI window should be open)")
    print("📊 Enhanced Dashboard: http://localhost:5000")
    print("=" * 50)

    # Check email notification system
    print("\n📧 Checking Email Notification System...")
    try:
        from celsius_email_notifications import CelsiusEmailNotifier

        notifier = CelsiusEmailNotifier()

        if notifier.config.get("enabled", False):
            print("✅ Email notifications configured and ready")
            # Test connection
            if notifier.test_email_connection():
                print("✅ Email system verified - test email sent")
            else:
                print("⚠️ Email configured but connection test failed")
        else:
            print("📋 Email notifications not configured")
            print("💡 Run: python celsius_email_notifications.py to set up email alerts")

    except ImportError:
        print("❌ Email notification system not found")
    except Exception as e:
        print(f"⚠️ Email notification system error: {e}")

    print("\n🛡️ Services are now running independently")
    print("Press Ctrl+C to exit this startup monitor")

    # Simple monitoring loop
    try:
        while True:
            time.sleep(60)
            print("💚 Services monitoring... (Ctrl+C to exit)")
    except KeyboardInterrupt:
        print("\n🔚 Startup monitor exited")


if __name__ == "__main__":
    start_services()
