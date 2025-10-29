#!/usr/bin/env python3
"""
RGB Hardware Detection Script
Checks for available RGB control methods
"""

import os

#!/usr/bin/env python3
"""
RGB Hardware Detection Script
Checks for available RGB control methods (console-only, emoji removed)
"""

import os
import sys
import subprocess
from pathlib import Path


def check_openrgb():
    """Check if OpenRGB is available"""
    print("Checking for OpenRGB...")
    try:
        # Check common OpenRGB installation paths
        openrgb_paths = [
            r"C:\Program Files\OpenRGB\OpenRGB.exe",
            r"C:\Program Files (x86)\OpenRGB\OpenRGB.exe",
            r".\OpenRGB.exe",
        ]

        for path in openrgb_paths:
            if Path(path).exists():
                print(f"Found OpenRGB at: {path}")
                return True

        print("OpenRGB not found")
        return False
    except Exception as e:
        print(f"OpenRGB check failed: {e}")
        return False


def check_manufacturer_software():
    """Check for manufacturer RGB software"""
    print("Checking for manufacturer RGB software...")

    software_checks = [
        ("Corsair iCUE", [r"C:\Program Files\Corsair\CORSAIR iCUE Software"]),
        ("ASUS Aura", [r"C:\Program Files (x86)\ASUS\AuraCreator"]),
        ("MSI Dragon Center", [r"C:\Program Files (x86)\MSI\Dragon Center"]),
        ("Razer Synapse", [r"C:\Program Files (x86)\Razer\Synapse3"]),
        ("NZXT CAM", [r"C:\Program Files\NZXT\CAM"]),
    ]

    found_any = False
    for name, paths in software_checks:
        for path in paths:
            if Path(path).exists():
                print(f"Found {name} at: {path}")
                found_any = True
                break
        else:
            print(f"{name} not found")

    return found_any


def check_wmi_rgb():
    """Check for RGB devices via WMI"""
    print("Checking for RGB devices via WMI...")
    try:
        import wmi

        c = wmi.WMI()

        devices = c.Win32_PnPEntity()
        rgb_devices = []

        for device in devices:
            if device.Name and any(
                keyword in device.Name.lower() for keyword in ["rgb", "light", "illumination", "led"]
            ):
                rgb_devices.append(device.Name)

        if rgb_devices:
            print(f"Found {len(rgb_devices)} potential RGB devices:")
            for device in rgb_devices[:5]:
                print(f"   - {device}")
        else:
            print("No RGB devices found via WMI")

        return len(rgb_devices) > 0

    except ImportError:
        print("WMI module not available (install with: pip install WMI)")
        return False
    except Exception as e:
        print(f"WMI check failed: {e}")
        return False


def check_basic_rgb_methods():
    """Check basic RGB control methods"""
    print("Testing basic RGB control methods...")

    methods = {
        "Windows Registry": False,
        "USB HID Devices": False,
        "DirectX/D3D": False,
    }

    try:
        import winreg

        methods["Windows Registry"] = True
        print("Windows Registry access available")
    except Exception:
        print("Windows Registry access not available")

    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                'Get-PnpDevice -Class "HIDClass" | Where-Object {$_.FriendlyName -like "*RGB*" -or $_.FriendlyName -like "*Light*"}',
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            methods["USB HID Devices"] = True
            print("USB HID devices found")
        else:
            print("No RGB USB HID devices found")
    except Exception as e:
        print(f"USB HID check failed: {e}")

    return any(methods.values())


def suggest_rgb_solutions():
    """Suggest RGB control solutions"""
    print("RGB Control Solutions:")
    print("   1. Install OpenRGB (https://openrgb.org/) - Universal RGB control")
    print("   2. Install manufacturer software (Corsair iCUE, ASUS Aura, etc.)")
    print("   3. Use motherboard RGB headers with compatible software")
    print("   4. Check if keyboard/mouse has built-in RGB with vendor software")
    print("   5. For testing: Use simulation mode in Celsius AI")


def main():
    print("Celsius AI - RGB Hardware Detection")
    print("=" * 50)

    rgb_available = False

    rgb_available |= check_openrgb()
    rgb_available |= check_manufacturer_software()
    rgb_available |= check_wmi_rgb()
    rgb_available |= check_basic_rgb_methods()

    print("\n" + "=" * 50)
    if rgb_available:
        print("RGB control capabilities detected!")
        print("The hardware controller should be able to control RGB lighting.")
    else:
        print("No RGB control software detected.")
        print("RGB commands will run in simulation mode.")
        suggest_rgb_solutions()

    print("\nNote: Fan control worked because it uses standard system interfaces.")
    print("RGB control requires specific hardware/software integration.")


if __name__ == "__main__":
    main()
