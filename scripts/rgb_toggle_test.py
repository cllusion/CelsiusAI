#!/usr/bin/env python3
"""
Simple RGB toggle test for Celsius AI hardware controller.
Sets `motherboard` to red for 2 seconds then turns it off.
"""
import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path so `src` package can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.hardware.celsius_hardware_controller import CelsiusHardwareController


async def main():
    c = CelsiusHardwareController()
    await c.initialize()
    try:
        # Use 'all' to affect all detected RGB devices (safer when specific names differ)
        await c.set_rgb_color("all", 255, 0, 0)
        await asyncio.sleep(2)
        await c.set_rgb_color("all", 0, 0, 0)
        print("RGB_TOGGLE_DONE")
    except Exception as e:
        print("RGB_TOGGLE_FAILED", e)


if __name__ == "__main__":
    asyncio.run(main())
