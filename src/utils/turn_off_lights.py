#!/usr/bin/env python3
"""
Celsius AI - Turn Off RGB Lights
Quick command to turn off all RGB lighting
"""

import sys
import os


def turn_off_rgb_lights():
    """Turn off all RGB lights (set to black/off).

    This function attempts to use the local hardware controller if available.
    If not available, it prints a simulation message and exits gracefully.
    """
    print("Celsius AI - Turning Off RGB Lights")
    print("=" * 40)

    try:
        # Prefer a local hardware controller module (may not be present on all systems)
        from celsius_hardware_controller import CelsiusHardwareController
    except ImportError:
        print("❌ Hardware controller not available. Running in simulation mode.")
        print("RGB control available via Ultimate Hub interface or install the hardware controller.")
        return

    try:
        controller = CelsiusHardwareController()
        print("✅ Hardware controller initialized")

        print("🔄 Turning off RGB lights...")
        controller.set_rgb_color_simple(0, 0, 0)
        controller.apply_effect_simple("static")

        print("✅ All RGB lights turned off successfully!")
        print("RGB Lighting Status:")
        print("   Red: 0")
        print("   Green: 0")
        print("   Blue: 0")
        print("   Effect: Static (Off)")
        print("   All devices: Lights OFF")

    except Exception as e:
        print(f"❌ Error turning off lights: {e}")


if __name__ == "__main__":
    turn_off_rgb_lights()
