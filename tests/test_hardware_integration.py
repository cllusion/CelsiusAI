#!/usr/bin/env python3
"""
Celsius AI - Hardware Integration Test
Tests the hardware control system integration
"""

import requests
import time
import sys
import os


def test_hardware_api():
    """Test hardware API endpoints"""
    print("🧪 Testing Hardware API Integration...")

    base_url = "http://localhost:5001"

    try:
        # Test status endpoint
        print("\n1. Testing status endpoint...")
        response = requests.get(f"{base_url}/api/hardware/status", timeout=5)
        if response.status_code == 200:
            print("✅ Status endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            return False

        # Test fan control
        print("\n2. Testing fan control...")
        response = requests.post(f"{base_url}/api/hardware/fan", json={"speed": 50}, timeout=5)
        if response.status_code == 200:
            print("✅ Fan control endpoint working")
        else:
            print(f"❌ Fan control failed: {response.status_code}")

        # Test RGB control
        print("\n3. Testing RGB control...")
        response = requests.post(f"{base_url}/api/hardware/rgb", json={"r": 255, "g": 0, "b": 0}, timeout=5)
        if response.status_code == 200:
            print("✅ RGB control endpoint working")
        else:
            print(f"❌ RGB control failed: {response.status_code}")

        # Test web interface
        print("\n4. Testing web interface...")
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("✅ Web interface accessible")
        else:
            print(f"❌ Web interface failed: {response.status_code}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API connection failed: {e}")
        print("💡 Make sure hardware_api.py is running on port 5001")
        return False


def test_hardware_controller():
    """Test local hardware controller"""
    print("\n🧪 Testing Local Hardware Controller...")

    try:
        # Add hardware directory to path
        hardware_path = os.path.join(os.path.dirname(__file__), "src", "hardware")
        if hardware_path not in sys.path:
            sys.path.append(hardware_path)

        from celsius_hardware_controller import CelsiusHardwareController

        print("✅ Hardware controller imported successfully")

        # Test controller initialization
        controller = CelsiusHardwareController()
        print("✅ Hardware controller initialized")

        # Test fan control
        print("\n1. Testing fan control...")
        controller.set_fan_speed_simple(50)
        print("✅ Fan speed set to 50%")

        # Test RGB control
        print("\n2. Testing RGB control...")
        controller.set_rgb_color_simple(255, 0, 0)  # Red
        print("✅ RGB color set to red")

        # Test temperature monitoring
        print("\n3. Testing temperature monitoring...")
        temps = controller.get_temperatures()
        if temps:
            print(f"✅ Temperature data: {temps}")
        else:
            print("⚠️ No temperature data available")

        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("💡 Make sure celsius_hardware_controller.py exists in src/hardware/")
        return False
    except Exception as e:
        print(f"❌ Controller test failed: {e}")
        return False


def main():
    """Main test function"""
    print("🎮 Celsius AI Hardware Integration Test Suite")
    print("=" * 50)

    # Test hardware API
    api_success = test_hardware_api()

    print("\n" + "=" * 50)

    # Test local hardware controller
    controller_success = test_hardware_controller()

    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    if api_success:
        print("✅ Hardware API: PASS")
    else:
        print("❌ Hardware API: FAIL")

    if controller_success:
        print("✅ Hardware Controller: PASS")
    else:
        print("❌ Hardware Controller: FAIL")

    if api_success and controller_success:
        print("\n🎉 All tests passed! Hardware integration is working correctly.")
        print("\n💡 Next steps:")
        print("   1. Open Ultimate Hub and check the 🎮 Hardware tab")
        print("   2. Visit http://localhost:5001 for web interface")
        print("   3. Test fan and RGB controls")
    else:
        print("\n⚠️ Some tests failed. Check the error messages above.")

    return api_success and controller_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
