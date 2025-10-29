#!/usr/bin/env python3

"""
Quick Server Hub Responsiveness Test
"""

import requests
import time


def test_responsiveness():
    """Test server responsiveness"""
    print("🧪 Testing Celsius AI Server Hub Responsiveness...")

    base_url = "http://localhost:5000"

    tests = [("Home Page", "/"), ("API Status", "/api/status"), ("Health Check", "/api/health")]

    for test_name, endpoint in tests:
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000  # Convert to milliseconds

            if response.status_code == 200:
                print(f"✅ {test_name}: {response_time:.0f}ms")
            else:
                print(f"⚠️ {test_name}: {response.status_code} ({response_time:.0f}ms)")

        except Exception as e:
            print(f"❌ {test_name}: Failed - {e}")

    print("\n🎯 Responsiveness Summary:")
    print("• ✅ Good: < 200ms")
    print("• ⚠️ Slow: 200ms - 1000ms")
    print("• ❌ Poor: > 1000ms")


if __name__ == "__main__":
    test_responsiveness()
