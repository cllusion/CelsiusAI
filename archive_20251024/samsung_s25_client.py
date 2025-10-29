#!/usr/bin/env python3
"""
Celsius AI Universal Mobile Client
Works with Samsung Galaxy S25 Ultra and other Android devices
"""

import requests
import json
import sys


class CelsiusUniversalClient:
    def __init__(self, server_ip="192.168.1.100", port=5000):
        self.base_url = f"http://{server_ip}:{port}"
        self.chat_url = f"{self.base_url}/api/chat"
        print(f"Connecting to Celsius AI Universal Server at {self.base_url}")

    def test_connection(self):
        """Test if server is reachable"""
        try:
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200:
                print("✅ Server connection successful!")
                return True
            else:
                print(f"⚠️ Server returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection failed: {e}")
            return False

    def send_message(self, message):
        """Send message to Celsius AI"""
        try:
            data = {"message": message}
            print(f"📤 Sending: {message}")

            response = requests.post(self.chat_url, json=data, timeout=15)

            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", "No response")
                print(f"🤖 Celsius AI: {ai_response}")
                return ai_response
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            return None

    def interactive_chat(self):
        """Start interactive chat session"""
        print("\n🛡️ Celsius AI - Personal Cybersecurity Defense Assistant")
        print("🔒 Samsung S25 Ultra Edition")
        print("📱 Type 'quit' to exit, 'help' for commands\n")

        if not self.test_connection():
            print("Cannot connect to server. Check your network connection.")
            return

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if user_input.lower() in ["quit", "exit"]:
                    print("👋 Goodbye!")
                    break
                elif user_input.lower() == "help":
                    self.show_help()
                elif user_input:
                    self.send_message(user_input)

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

    def show_help(self):
        """Show available commands"""
        print("\n🛡️ Celsius AI Commands:")
        print("Security Commands:")
        print("  • scan network - Check network for threats")
        print("  • check threats - Analyze current security status")
        print("  • analyze file <path> - Scan specific file")
        print("\nDevice Commands:")
        print("  • list devices - Show connected devices")
        print("  • device status <name> - Check device security")
        print("  • sync security - Synchronize protection")
        print("\nIntelligence Commands:")
        print("  • threat intel <query> - Get threat information")
        print("  • vulnerability check - Check for vulnerabilities")
        print("\nGeneral Commands:")
        print("  • status - Show system status")
        print("  • help - Show this help")
        print("  • quit - Exit application")


if __name__ == "__main__":
    print("🚀 Starting Celsius AI Mobile Client...")

    # Use your Windows PC's IP address
    client = CelsiusUniversalClient(server_ip="192.168.1.100", port=5000)

    # Start interactive mode
    client.interactive_chat()
