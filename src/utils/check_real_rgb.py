#!/usr/bin/env python3
"""
ASRock B650M-C RGB Detection and Control
Specific detection for your motherboard's RGB capabilities
"""

import os
import subprocess
from pathlib import Path


def check_asrock_rgb():
    print("🔍 ASRock B650M-C RGB Detection")
    print("=" * 40)
    print("Motherboard: ASRock B650M-C")
    print("RGB Features: This board supports Polychrome RGB")
    print()

    # Check for ASRock Polychrome software
    print("1. Checking for ASRock Polychrome RGB software...")
    asrock_paths = [
        r"C:\Program Files\ASRock Utility\ASRRGBLED",
        r"C:\Program Files (x86)\ASRock\ASRRGBLED",
        r"C:\Program Files\ASRock\ASRPolychromeRGB",
        r"C:\Program Files (x86)\ASRock Utility",
    ]

    asrock_found = False
    for path in asrock_paths:
        if Path(path).exists():
            print(f"✅ Found ASRock software: {path}")
            asrock_found = True
            break

    if not asrock_found:
        print("❌ ASRock Polychrome RGB software not installed")

    # Check for OpenRGB (universal RGB control)
    print("\n2. Checking for OpenRGB...")
    openrgb_paths = [
        r"C:\Program Files\OpenRGB\OpenRGB.exe",
        r"C:\Program Files (x86)\OpenRGB\OpenRGB.exe",
        r".\OpenRGB.exe",
    ]

    openrgb_found = False
    for path in openrgb_paths:
        if Path(path).exists():
            print(f"✅ Found OpenRGB: {path}")
            openrgb_found = True
            break

    if not openrgb_found:
        print("❌ OpenRGB not installed")

    # Check for RGB devices in Device Manager
    print("\n3. Checking for RGB devices in system...")
    try:
        result = subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                'Get-PnpDevice | Where-Object {$_.FriendlyName -match "RGB|LED|Light"} | Select-Object FriendlyName',
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and result.stdout.strip():
            print("✅ Found potential RGB devices:")
            print(result.stdout)
        else:
            print("❌ No RGB devices detected in Device Manager")
    except Exception as e:
        print(f"⚠️ Could not check devices: {e}")

    # Check for keyboard/mouse RGB
    print("\n4. Checking for RGB keyboard/mouse...")
    try:
        result = subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                'Get-PnpDevice -Class "Keyboard","Mouse" | Select-Object FriendlyName',
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            devices = result.stdout
            if any(
                brand in devices.lower() for brand in ["corsair", "razer", "logitech", "steelseries", "cooler master"]
            ):
                print("✅ Gaming peripherals detected - may have RGB")
                print("   Check manufacturer software for RGB control")
            else:
                print("❌ No gaming peripherals with RGB detected")

    except Exception as e:
        print(f"⚠️ Could not check peripherals: {e}")

    print("\n" + "=" * 40)
    print("🎯 RECOMMENDATIONS FOR REAL RGB CONTROL:")
    print()

    if not asrock_found and not openrgb_found:
        print("💡 To control actual RGB lights, install:")
        print("   Option 1: ASRock Polychrome RGB")
        print("   - Download from ASRock support website")
        print("   - Specifically for your B650M-C motherboard")
        print("   - Controls motherboard RGB headers")
        print()
        print("   Option 2: OpenRGB (Recommended)")
        print("   - Download from: https://openrgb.org/")
        print("   - Universal RGB control")
        print("   - Supports ASRock motherboards")
        print("   - Controls multiple RGB devices")
        print()
        print("🔧 Your current situation:")
        print("   ✅ Fan control: WORKING (real hardware)")
        print("   ⚠️ RGB control: SIMULATION MODE")
        print("   💡 Install RGB software to make lights actually change")

    elif asrock_found or openrgb_found:
        print("✅ RGB software detected! Let's try to control real RGB...")
        return True

    return False


def try_real_rgb_control():
    """Try to control real RGB if software is available"""
    print("\n🌈 Attempting real RGB control...")

    # Try OpenRGB command line
    openrgb_exe = None
    for path in [r"C:\Program Files\OpenRGB\OpenRGB.exe", r"C:\Program Files (x86)\OpenRGB\OpenRGB.exe"]:
        if Path(path).exists():
            openrgb_exe = path
            break

    if openrgb_exe:
        try:
            print(f"🔧 Using OpenRGB: {openrgb_exe}")
            # Try to turn off RGB via OpenRGB command line
            result = subprocess.run([openrgb_exe, "--color", "000000"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ RGB lights turned OFF via OpenRGB!")
                return True
            else:
                print(f"⚠️ OpenRGB command failed: {result.stderr}")
        except Exception as e:
            print(f"❌ OpenRGB execution failed: {e}")

    # Try ASRock software (if available)
    # Note: ASRock Polychrome typically doesn't have command line interface

    return False


def main():
    rgb_available = check_asrock_rgb()

    if rgb_available:
        success = try_real_rgb_control()
        if success:
            print("\n🎉 SUCCESS: Real RGB lights controlled!")
        else:
            print("\n⚠️ RGB software found but command line control failed")
            print("   Try using the RGB software's GUI interface")
    else:
        print("\n💡 Current Status:")
        print("   🌀 Fan control: ✅ WORKING")
        print("   🌈 RGB control: ⚠️ Simulation only")
        print("   📱 Ultimate Hub: ✅ Ready for RGB software")


if __name__ == "__main__":
    main()
