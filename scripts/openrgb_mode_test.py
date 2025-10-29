#!/usr/bin/env python3
"""
OpenRGB mode test: set ASRock device to Static mode, then set color to green, read back.
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


def main():
    try:
        client = OpenRGBClient()
        print("OPENRGB_CONNECTED", client.protocol_version)
    except Exception as e:
        print("OPENRGB_CONNECT_FAILED", e)
        sys.exit(3)

    devices = client.devices
    asrock_idx = None
    for i, d in enumerate(devices):
        if "asrock" in d.name.lower() or "b650" in d.name.lower():
            asrock_idx = i
            break

    if asrock_idx is None:
        print("ASROCK_NOT_FOUND")
        return

    dev = devices[asrock_idx]
    print("ASROCK_FOUND", dev.name, "LEDs", len(getattr(dev, "leds", [])))

    # Try set mode to Static then set color
    try:
        print("Available modes:", [m.name for m in dev.modes])
    except Exception:
        print("Could not read modes")

    try:
        if "Static" in [m.name for m in dev.modes]:
            dev.set_mode("Static")
            print("SET_MODE_OK Static")
        elif "Direct" in [m.name for m in dev.modes]:
            dev.set_mode("Direct")
            print("SET_MODE_OK Direct")
        else:
            print("NO_SUPPORTED_MODE_SET")
    except Exception as e:
        print("SET_MODE_FAILED", e)

    try:
        green = RGBColor(0, 255, 0)
        dev.set_color(green)
        print("SET_COLOR_CMD_OK")
    except Exception as e:
        print("SET_COLOR_FAILED", e)

    time.sleep(2)
    try:
        print("READBACK_COLORS_SAMPLE:", ",".join(str(c) for c in dev.colors[:8]))
    except Exception as e:
        print("READBACK_FAILED", e)

    # revert
    try:
        dev.set_mode("Off")
        dev.set_color(RGBColor(0, 0, 0))
        print("REVERTED")
    except Exception as e:
        print("REVERT_FAILED", e)


if __name__ == "__main__":
    main()
