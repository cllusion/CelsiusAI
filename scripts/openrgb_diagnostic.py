#!/usr/bin/env python3
"""
OpenRGB diagnostic: lists devices, modes, zones, and attempts a controlled color change for ASRock device.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import time

try:
    from openrgb import OpenRGBClient
    from openrgb.utils import RGBColor
except Exception as e:
    print("OPENRGB_IMPORT_FAILED", e)
    sys.exit(2)

try:
    import psutil
except Exception:
    psutil = None


def main():
    try:
        client = OpenRGBClient()
        print("OPENRGB_CONNECTED", client.protocol_version)
    except Exception as e:
        print("OPENRGB_CONNECT_FAILED", e)
        sys.exit(3)

    devices = client.devices
    print(f"DEVICE_COUNT: {len(devices)}")
    # Extra diagnostics: which process is listening on port 6742 and OpenRGB processes
    try:
        print("CURRENT_USER:", Path().owner() if hasattr(Path(), "owner") else "")
    except Exception:
        pass

    if psutil:
        try:
            listeners = [c for c in psutil.net_connections(kind="tcp") if c.laddr and c.laddr.port == 6742]
            if listeners:
                for c in listeners:
                    print(f"PORT_LISTENER: pid={c.pid} laddr={c.laddr} status={c.status}")
            else:
                print("PORT_LISTENER: none")

            # List OpenRGB processes
            or_procs = [
                p
                for p in psutil.process_iter(["pid", "name", "exe"])
                if p.info.get("name") and "openrgb" in p.info["name"].lower()
            ]
            if or_procs:
                for p in or_procs:
                    print(f"OPENRGB_PROC: pid={p.info['pid']} name={p.info['name']} exe={p.info.get('exe')}")
            else:
                print("OPENRGB_PROC: none")
        except Exception as e:
            print("PSUTIL_ERROR", e)
    else:
        # Fallback: show netstat output to find port listener
        try:
            import subprocess

            out = subprocess.check_output("netstat -ano | findstr 6742", shell=True, text=True)
            print("NETSTAT:", out.strip())
        except Exception as e:
            print("NETSTAT_FAILED", e)
    for idx, dev in enumerate(devices):
        try:
            print("---")
            print(f"INDEX: {idx}")
            print(f"NAME: {dev.name}")
            # print number of LEDs/zones
            try:
                leds = getattr(dev, "leds", None)
                if leds is not None:
                    print(f"LED_COUNT: {len(leds)}")
                else:
                    print("LED_COUNT: unknown")
            except Exception:
                print("LED_COUNT: error")

            try:
                modes = dev.modes
                print(f"MODES: {[m.name for m in modes]}")
            except Exception:
                print("MODES: unavailable")

            try:
                colors = dev.colors
                sample = ",".join(str(c) for c in colors[:3])
                print(f"CURRENT_COLORS_SAMPLE: {sample}")
            except Exception:
                print("CURRENT_COLORS: unavailable")
        except Exception as e:
            print("DEVICE_INFO_ERR", e)

    # Try to find ASRock device
    asrock_idx = None
    for i, d in enumerate(devices):
        if "asrock" in d.name.lower() or "b650" in d.name.lower() or "motherboard" in d.name.lower():
            asrock_idx = i
            break

    if asrock_idx is None:
        print("ASROCK_NOT_FOUND: Please verify OpenRGB device list above")
        sys.exit(0)

    print(f"ASROCK_DEVICE_INDEX: {asrock_idx}")
    dev = devices[asrock_idx]

    print("Attempting to set ASRock device to green for 3s and read back colors...")
    try:
        green = RGBColor(0, 255, 0)
        # Some devices accept set_color on the device; others require per-LED
        try:
            dev.set_color(green)
            print("SET_COLOR_CMD_OK: device.set_color(green)")
        except Exception as e:
            print("SET_COLOR_CMD_FAILED_device.set_color", e)
            try:
                # fallback: set per-led
                for led in getattr(dev, "leds", []):
                    led.set_color(green)
                print("SET_COLOR_CMD_OK_per_led")
            except Exception as e2:
                print("SET_COLOR_CMD_FAILED_per_led", e2)

        time.sleep(3)
        # Read back colors
        try:
            colors = dev.colors
            print("READBACK_SAMPLE:", ",".join(str(c) for c in colors[:6]))
        except Exception as e:
            print("READBACK_FAILED", e)

        # revert to off
        try:
            black = RGBColor(0, 0, 0)
            dev.set_color(black)
            print("REVERT_OK")
        except Exception:
            print("REVERT_FAILED")

    except Exception as e:
        print("ASROCK_TOGGLE_FAILED", e)


if __name__ == "__main__":
    main()
