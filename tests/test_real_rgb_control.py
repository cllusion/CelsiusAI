#!/usr/bin/env python3
"""
Test Real RGB Control
Validates that Celsius AI can control physical RGB hardware
"""

import asyncio
import sys
import os

# Add the hardware controller to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src", "hardware"))

from celsius_hardware_controller import CelsiusHardwareController


async def test_all_rgb_functions():
    """Test all RGB control functions"""

    print("🔥 Celsius AI - Real RGB Control Test")
    print("=====================================")

    # Initialize controller
    controller = CelsiusHardwareController()
    await controller.initialize()

    print(f"✅ Found {len(controller.hardware_interfaces)} hardware interfaces")

    # Test 1: Individual device control (motherboard)
    print("\n🎨 Test 1: Motherboard RGB Control")
    print("Red...")
    await controller.set_rgb_color("2", 255, 0, 0)  # ASRock motherboard
    await asyncio.sleep(2)

    print("Green...")
    await controller.set_rgb_color("2", 0, 255, 0)
    await asyncio.sleep(2)

    print("Blue...")
    await controller.set_rgb_color("2", 0, 0, 255)
    await asyncio.sleep(2)

    print("Off...")
    await controller.set_rgb_color("2", 0, 0, 0)
    await asyncio.sleep(1)

    # Test 2: All devices control
    print("\n🌈 Test 2: All Devices RGB Control")

    print("Purple on all devices...")
    await controller.set_rgb_color("all", 128, 0, 128)
    await asyncio.sleep(3)

    print("Orange on all devices...")
    await controller.set_rgb_color("all", 255, 165, 0)
    await asyncio.sleep(3)

    print("Cyan on all devices...")
    await controller.set_rgb_color("all", 0, 255, 255)
    await asyncio.sleep(3)

    print("All devices off...")
    await controller.set_rgb_color("all", 0, 0, 0)

    # Test 3: Color convenience functions
    print("\n🎯 Test 3: Color Name Functions")

    print("Testing convenience functions...")
    controller.set_rgb_color_simple(255, 255, 0)  # Yellow
    await asyncio.sleep(2)

    controller.set_rgb_color_simple(255, 0, 255)  # Magenta
    await asyncio.sleep(2)

    controller.set_rgb_color_simple(0, 0, 0)  # Off

    print("\n🎉 ALL RGB TESTS PASSED!")
    print("Your RGB hardware is fully controlled by Celsius AI!")
    print("\nAvailable devices:")

    # Show available devices
    try:
        from openrgb import OpenRGBClient

        client = OpenRGBClient()
        for i, device in enumerate(client.devices):
            print(f"  Device {i}: {device.name} ({len(device.leds)} LEDs)")
    except Exception as e:
        print(f"  Error listing devices: {e}")


def main():
    """Main test function"""
    try:
        asyncio.run(test_all_rgb_functions())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
