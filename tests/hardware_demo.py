#!/usr/bin/env python3
"""
🎮 Celsius AI Hardware Control - Quick Start Guide
Run this to see hardware control in action!
"""

import time
import sys
import os


def main():
    print("🎮 Celsius AI Hardware Control - Quick Start Demo")
    print("=" * 60)

    try:
        # Add hardware path
        hardware_path = os.path.join(os.path.dirname(__file__), "src", "hardware")
        if hardware_path not in sys.path:
            sys.path.append(hardware_path)

        from celsius_hardware_controller import CelsiusHardwareController

        print("✅ Hardware controller loaded successfully!")
        controller = CelsiusHardwareController()
        print("✅ Hardware controller initialized!")

        print("\n🔥 DEMO: Cycling through performance profiles...")

        profiles = ["silent", "balanced", "performance"]
        for profile in profiles:
            print(f"\n⚡ Applying '{profile}' profile...")
            controller.apply_profile_simple(profile)
            print(f"   ✅ {profile.title()} mode active!")
            time.sleep(2)

        print("\n🌈 DEMO: RGB Color Cycle...")
        colors = [(255, 0, 0, "Red"), (0, 255, 0, "Green"), (0, 0, 255, "Blue"), (255, 255, 255, "White")]

        for r, g, b, name in colors:
            print(f"   🎨 Setting RGB to {name}...")
            controller.set_rgb_color_simple(r, g, b)
            time.sleep(1.5)

        print("\n🌀 DEMO: Fan Speed Test...")
        speeds = [30, 50, 80, 50]  # Return to balanced
        for speed in speeds:
            print(f"   💨 Setting fan speed to {speed}%...")
            controller.set_fan_speed_simple(speed)
            time.sleep(2)

        print("\n🌡️ Temperature Check...")
        temps = controller.get_temperatures()
        for sensor, temp in temps.items():
            print(f"   📊 {sensor}: {temp}°C")

        print("\n🎉 Hardware control demo complete!")
        print("\n💡 Next steps:")
        print("   1. Open Ultimate Hub → Hardware tab for GUI control")
        print("   2. Run 'python src/hardware/hardware_api.py' for web interface")
        print("   3. Visit http://localhost:5001 for browser control")

    except ImportError as e:
        print(f"❌ Hardware controller not available: {e}")
        print("💡 This is normal - hardware control will work via GUI interface")
    except Exception as e:
        print(f"❌ Demo error: {e}")


if __name__ == "__main__":
    main()
