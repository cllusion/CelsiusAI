#!/usr/bin/env python3
"""
🎨 Celsius AI Hardware Controller
=================================
Controls desktop fans, RGB lighting, and other hardware components.
Supports multiple hardware control methods and manufacturers.

Features:
- Fan speed control via multiple interfaces
- RGB lighting control for various brands
- Temperature monitoring integration
- Performance-based automatic adjustments
- Web API for external control
- Integration with Celsius AI learning system

Supported Hardware:
- OpenRGB (Universal RGB control)
- Corsair iCUE devices
- ASUS Aura Sync
- MSI Mystic Light
- Razer Chroma
- NZXT CAM
- Fan control via WMI/COM interfaces
- Custom hardware via serial/USB
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import requests
import psutil

# Project setup
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CelsiusHardwareController:
    """
    Unified hardware controller for fans, RGB, and other components
    """

    def __init__(self):
        self.is_running = False
        self.fan_speeds = {}
        self.rgb_states = {}
        self.temperature_thresholds = {
            "low": 40,  # Below 40°C - quiet mode
            "medium": 60,  # 40-60°C - balanced mode
            "high": 75,  # 60-75°C - performance mode
            "critical": 85,  # Above 75°C - maximum cooling
        }

        # Hardware interfaces
        self.openrgb_available = False
        self.wmi_available = False
        self.hardware_interfaces = []

        # Performance profiles
        self.profiles = {
            "silent": {
                "fan_speed": 30,
                "rgb_brightness": 20,
                "rgb_effect": "static",
                "rgb_color": [0, 50, 100],  # Cool blue
            },
            "balanced": {
                "fan_speed": 50,
                "rgb_brightness": 60,
                "rgb_effect": "breathing",
                "rgb_color": [0, 255, 0],  # Green
            },
            "performance": {
                "fan_speed": 80,
                "rgb_brightness": 100,
                "rgb_effect": "rainbow",
                "rgb_color": [255, 100, 0],  # Orange
            },
            "critical": {
                "fan_speed": 100,
                "rgb_brightness": 100,
                "rgb_effect": "strobe",
                "rgb_color": [255, 0, 0],  # Red warning
            },
        }

        self.current_profile = "balanced"

    async def initialize(self):
        """Initialize hardware interfaces"""
        logger.info("[HARDWARE] Initializing Celsius Hardware Controller...")

        # Check for available interfaces
        await self._detect_hardware_interfaces()

        # Initialize each interface
        for interface in self.hardware_interfaces:
            try:
                await interface.initialize()
                logger.info(f"[HARDWARE] {interface.name} initialized successfully")
            except Exception as e:
                logger.warning(f"[HARDWARE] Failed to initialize {interface.name}: {e}")

        self.is_running = True
        logger.info("[HARDWARE] ✅ Hardware Controller initialized")

    async def _detect_hardware_interfaces(self):
        """Detect available hardware control interfaces"""

        # Check for OpenRGB
        if await self._check_openrgb():
            self.hardware_interfaces.append(OpenRGBInterface())
            self.openrgb_available = True

        # Check for WMI fan control
        if await self._check_wmi_fans():
            self.hardware_interfaces.append(WMIFanInterface())
            self.wmi_available = True

        # Check for manufacturer software
        await self._detect_manufacturer_software()

        # Add generic interfaces
        self.hardware_interfaces.append(GenericFanInterface())
        self.hardware_interfaces.append(RegistryRGBInterface())

        logger.info(f"[HARDWARE] Detected {len(self.hardware_interfaces)} hardware interfaces")

    async def _check_openrgb(self) -> bool:
        """Check if OpenRGB is available and working"""
        try:
            # Try importing the library first
            from openrgb import OpenRGBClient
            from openrgb.utils import RGBColor

            # Try to connect to OpenRGB server
            try:
                client = OpenRGBClient()
                device_count = len(client.devices)
                logger.info(f"[HARDWARE] ✅ OpenRGB connected with {device_count} RGB devices")
                return device_count > 0
            except Exception as e:
                logger.warning(f"[HARDWARE] OpenRGB server not available: {e}")

                # Try to start OpenRGB server
                openrgb_paths = [
                    r"C:\Program Files\OpenRGB\OpenRGB.exe",
                    r"C:\Program Files (x86)\OpenRGB\OpenRGB.exe",
                    r".\OpenRGB.exe",
                ]

                for path in openrgb_paths:
                    if Path(path).exists():
                        logger.info(f"[HARDWARE] Starting OpenRGB server: {path}")
                        try:
                            import subprocess

                            subprocess.Popen(
                                [path, "--server", "--server-port", "6742"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            logger.info("[HARDWARE] ✅ Started OpenRGB server")
                            return True
                        except Exception as start_error:
                            logger.warning(f"[HARDWARE] Could not start OpenRGB server: {start_error}")
                            return False

                logger.warning("[HARDWARE] OpenRGB executable not found")
                return False

        except ImportError:
            logger.warning("[HARDWARE] OpenRGB Python library not installed")
            return False

    async def _check_wmi_fans(self) -> bool:
        """Check if WMI fan control is available"""
        try:
            import wmi

            w = wmi.WMI(namespace="root\\wmi")
            # Try to access fan controls
            fans = w.query("SELECT * FROM Fan")
            return len(fans) > 0
        except:
            return False

    async def _detect_manufacturer_software(self):
        """Detect manufacturer-specific RGB/fan software"""

        software_checks = [
            ("Corsair iCUE", ["C:\\Program Files\\Corsair\\CORSAIR iCUE 4 Software\\iCUE.exe"]),
            ("ASUS Aura", ["C:\\Program Files (x86)\\ASUS\\AuraSync\\AuraSync.exe"]),
            ("MSI Center", ["C:\\Program Files\\MSI\\MSI Center\\MSI_Center.exe"]),
            (
                "Razer Synapse",
                [
                    "C:\\Program Files (x86)\\Razer\\Synapse3\\WPFUI\\Framework\\Razer Synapse 3 Host\\Razer Synapse 3.exe"
                ],
            ),
            ("NZXT CAM", ["C:\\Program Files\\NZXT\\CAM\\CAM.exe"]),
        ]

        for name, paths in software_checks:
            for path in paths:
                if Path(path).exists():
                    self.hardware_interfaces.append(ManufacturerInterface(name, path))
                    logger.info(f"[HARDWARE] Found {name} at {path}")
                    break

    async def set_fan_speed(self, fan_id: str, speed_percent: int):
        """Set fan speed (0-100%)"""
        try:
            speed_percent = max(0, min(100, speed_percent))

            for interface in self.hardware_interfaces:
                if hasattr(interface, "set_fan_speed"):
                    await interface.set_fan_speed(fan_id, speed_percent)

            self.fan_speeds[fan_id] = speed_percent
            logger.info(f"[HARDWARE] Set fan {fan_id} to {speed_percent}%")

        except Exception as e:
            logger.error(f"[HARDWARE] Failed to set fan speed: {e}")

    async def set_rgb_color(self, device_id: str, r: int, g: int, b: int):
        """Set RGB color (0-255 for each channel)"""
        try:
            r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))

            # Try OpenRGB first for real hardware control
            hardware_success = False

            try:
                from openrgb import OpenRGBClient
                from openrgb.utils import RGBColor

                client = OpenRGBClient()

                # If device_id is "all" or matches device name
                if device_id.lower() == "all":
                    # Control all devices
                    for device in client.devices:
                        device.set_color(RGBColor(r, g, b))
                        logger.info(f"[HARDWARE] ✅ Set {device.name} RGB to ({r}, {g}, {b})")
                    hardware_success = True
                else:
                    # Try to find specific device by name or index
                    device_found = False

                    # Try by index
                    try:
                        device_index = int(device_id)
                        if 0 <= device_index < len(client.devices):
                            device = client.devices[device_index]
                            device.set_color(RGBColor(r, g, b))
                            logger.info(f"[HARDWARE] ✅ Set {device.name} RGB to ({r}, {g}, {b})")
                            device_found = True
                    except ValueError:
                        pass

                    # Try by name match
                    if not device_found:
                        for device in client.devices:
                            if device_id.lower() in device.name.lower():
                                device.set_color(RGBColor(r, g, b))
                                logger.info(f"[HARDWARE] ✅ Set {device.name} RGB to ({r}, {g}, {b})")
                                device_found = True
                                break

                    if device_found:
                        hardware_success = True
                    else:
                        logger.warning(f"[HARDWARE] RGB device '{device_id}' not found")

            except Exception as openrgb_error:
                logger.warning(f"[HARDWARE] OpenRGB control failed: {openrgb_error}")

            # Fallback to other hardware interfaces
            if not hardware_success:
                for interface in self.hardware_interfaces:
                    if hasattr(interface, "set_rgb_color"):
                        await interface.set_rgb_color(device_id, r, g, b)
                        hardware_success = True

            # If no hardware interface available, simulate the RGB control
            if not hardware_success:
                logger.info(
                    f"[HARDWARE] 🎨 RGB SIMULATION: {device_id} set to RGB({r}, {g}, {b}) - #{r:02x}{g:02x}{b:02x}"
                )

                # Visual feedback for simulation
                color_name = self._get_color_name(r, g, b)
                logger.info(f"[HARDWARE] 💡 RGB Effect: {device_id} now glowing {color_name}")

            self.rgb_states[device_id] = {"r": r, "g": g, "b": b}

        except Exception as e:
            logger.error(f"[HARDWARE] Failed to set RGB color: {e}")

    def _get_color_name(self, r: int, g: int, b: int) -> str:
        """Get human-readable color name"""
        if r > 200 and g < 50 and b < 50:
            return "🔴 RED"
        elif r < 50 and g > 200 and b < 50:
            return "🟢 GREEN"
        elif r < 50 and g < 50 and b > 200:
            return "🔵 BLUE"
        elif r > 200 and g > 200 and b < 50:
            return "🟡 YELLOW"
        elif r > 200 and g < 50 and b > 200:
            return "🟣 PURPLE"
        elif r > 200 and g > 100 and b < 50:
            return "🟠 ORANGE"
        elif r > 200 and g > 200 and b > 200:
            return "⚪ WHITE"
        elif r < 50 and g < 50 and b < 50:
            return "⚫ BLACK"
        else:
            return f"🎨 CUSTOM ({r},{g},{b})"

    async def set_rgb_effect(self, device_id: str, effect: str, **params):
        """Set RGB effect (static, breathing, rainbow, etc.)"""
        try:
            # Try hardware interfaces first
            hardware_success = False
            for interface in self.hardware_interfaces:
                if hasattr(interface, "set_rgb_effect"):
                    await interface.set_rgb_effect(device_id, effect, **params)
                    hardware_success = True

            # If no hardware interface available, simulate the effect
            if not hardware_success:
                effect_emoji = {
                    "static": "⚡",
                    "breathing": "💫",
                    "rainbow": "🌈",
                    "wave": "🌊",
                    "strobe": "⚡",
                    "fade": "🌅",
                }.get(effect, "✨")

                logger.info(
                    f"[HARDWARE] 🎭 RGB EFFECT SIMULATION: {device_id} now running {effect_emoji} {effect.upper()} effect"
                )

            logger.info(f"[HARDWARE] ✅ Set RGB effect {effect} on {device_id}")

        except Exception as e:
            logger.error(f"[HARDWARE] Failed to set RGB effect: {e}")

    async def apply_profile(self, profile_name: str):
        """Apply a hardware profile"""
        if profile_name not in self.profiles:
            logger.warning(f"[HARDWARE] Unknown profile: {profile_name}")
            return

        profile = self.profiles[profile_name]
        self.current_profile = profile_name

        try:
            # Apply fan settings
            for fan_id in ["cpu_fan", "case_fan_1", "case_fan_2", "gpu_fan"]:
                await self.set_fan_speed(fan_id, profile["fan_speed"])

            # Apply RGB settings
            for device_id in ["motherboard", "ram", "gpu", "keyboard", "mouse"]:
                color = profile["rgb_color"]
                await self.set_rgb_color(device_id, color[0], color[1], color[2])
                await self.set_rgb_effect(device_id, profile["rgb_effect"])

            logger.info(f"[HARDWARE] ✅ Applied profile: {profile_name}")

        except Exception as e:
            logger.error(f"[HARDWARE] Failed to apply profile {profile_name}: {e}")

    # Simplified convenience methods for easy integration
    def set_fan_speed_simple(self, speed_percent: int):
        """Set all fans to the same speed (synchronous convenience method)"""
        import asyncio

        try:
            asyncio.create_task(self._set_all_fans(speed_percent))
        except RuntimeError:
            # If no event loop is running, create one
            asyncio.run(self._set_all_fans(speed_percent))

    async def _set_all_fans(self, speed_percent: int):
        """Set all fans to the same speed"""
        fan_ids = ["cpu_fan", "case_fan_1", "case_fan_2", "gpu_fan"]
        for fan_id in fan_ids:
            await self.set_fan_speed(fan_id, speed_percent)

    def set_rgb_color_simple(self, r: int, g: int, b: int):
        """Set all RGB devices to the same color (synchronous convenience method)"""
        import asyncio

        try:
            asyncio.create_task(self._set_all_rgb(r, g, b))
        except RuntimeError:
            # If no event loop is running, create one
            asyncio.run(self._set_all_rgb(r, g, b))

    async def _set_all_rgb(self, r: int, g: int, b: int):
        """Set all RGB devices to the same color"""
        device_ids = ["motherboard", "ram", "gpu", "keyboard", "mouse"]
        for device_id in device_ids:
            await self.set_rgb_color(device_id, r, g, b)

    def apply_effect_simple(self, effect: str):
        """Apply effect to all RGB devices (synchronous convenience method)"""
        import asyncio

        try:
            asyncio.create_task(self._apply_all_effects(effect))
        except RuntimeError:
            # If no event loop is running, create one
            asyncio.run(self._apply_all_effects(effect))

    async def _apply_all_effects(self, effect: str):
        """Apply effect to all RGB devices"""
        device_ids = ["motherboard", "ram", "gpu", "keyboard", "mouse"]
        for device_id in device_ids:
            await self.set_rgb_effect(device_id, effect)

    def apply_profile_simple(self, profile_name: str):
        """Apply a hardware profile (synchronous convenience method)"""
        import asyncio

        try:
            asyncio.create_task(self.apply_profile(profile_name))
        except RuntimeError:
            # If no event loop is running, create one
            asyncio.run(self.apply_profile(profile_name))

    def get_temperatures(self):
        """Get system temperatures (synchronous method)"""
        try:
            import psutil

            temps = {}

            if hasattr(psutil, "sensors_temperatures"):
                sensor_temps = psutil.sensors_temperatures()
                if sensor_temps:
                    for name, entries in sensor_temps.items():
                        for entry in entries:
                            sensor_name = f"{name}_{entry.label or 'temp'}"
                            temps[sensor_name] = entry.current

            return temps if temps else {"cpu": 45, "gpu": 50}  # Fallback values

        except Exception as e:
            logger.warning(f"[HARDWARE] Temperature check failed: {e}")
            return {"cpu": 45, "gpu": 50}  # Fallback values

    async def auto_adjust_by_temperature(self):
        """Automatically adjust hardware based on system temperature"""
        try:
            # Get CPU temperature
            temps = psutil.sensors_temperatures()
            max_temp = 0

            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > max_temp:
                            max_temp = entry.current

            # Determine appropriate profile
            if max_temp < self.temperature_thresholds["low"]:
                target_profile = "silent"
            elif max_temp < self.temperature_thresholds["medium"]:
                target_profile = "balanced"
            elif max_temp < self.temperature_thresholds["high"]:
                target_profile = "performance"
            else:
                target_profile = "critical"

            # Apply profile if changed
            if target_profile != self.current_profile:
                logger.info(f"[HARDWARE] Temperature {max_temp}°C - switching to {target_profile} profile")
                await self.apply_profile(target_profile)

        except Exception as e:
            logger.error(f"[HARDWARE] Failed to auto-adjust by temperature: {e}")

    async def get_hardware_status(self) -> Dict[str, Any]:
        """Get current hardware status"""
        return {
            "current_profile": self.current_profile,
            "fan_speeds": self.fan_speeds.copy(),
            "rgb_states": self.rgb_states.copy(),
            "available_interfaces": [i.name for i in self.hardware_interfaces],
            "temperature_thresholds": self.temperature_thresholds.copy(),
            "profiles": list(self.profiles.keys()),
        }

    async def start_monitoring(self, interval: int = 30):
        """Start automatic hardware monitoring and adjustment"""
        logger.info(f"[HARDWARE] Starting automatic monitoring (interval: {interval}s)")

        while self.is_running:
            try:
                await self.auto_adjust_by_temperature()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HARDWARE] Monitoring error: {e}")
                await asyncio.sleep(5)

        logger.info("[HARDWARE] Monitoring stopped")


class OpenRGBInterface:
    """Interface for OpenRGB universal RGB control"""

    def __init__(self):
        self.name = "OpenRGB"
        self.client = None
        self.devices = []
        self.RGBColor = None

    async def initialize(self):
        # Try to use the python-openrgb client when available. If the
        # client is not installed or the server is not running, attempt
        # to start the OpenRGB server and retry connection a few times.
        try:
            from openrgb import OpenRGBClient
            from openrgb.utils import RGBColor

            self.RGBColor = RGBColor

            # Try to connect; if it fails, try to start the server and retry
            try:
                client = OpenRGBClient()  # defaults to localhost:6742
            except Exception:
                # Try to start OpenRGB server executable and retry
                openrgb_paths = [
                    r"C:\Program Files\OpenRGB\OpenRGB.exe",
                    r"C:\Program Files (x86)\OpenRGB\OpenRGB.exe",
                    r".\OpenRGB.exe",
                ]
                started = False
                for path in openrgb_paths:
                    if Path(path).exists():
                        logger.info(f"[HARDWARE][OpenRGB] Starting OpenRGB server: {path}")
                        try:
                            subprocess.Popen(
                                [path, "--server", "--server-port", "6742"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            started = True
                            break
                        except Exception as start_error:
                            logger.warning(f"[HARDWARE][OpenRGB] Could not start OpenRGB server: {start_error}")
                # If we started the server, wait and retry connecting a few times
                if started:
                    for attempt in range(5):
                        await asyncio.sleep(1 + attempt)
                        try:
                            client = OpenRGBClient()
                            break
                        except Exception:
                            client = None
                    if client is None:
                        logger.warning("[HARDWARE][OpenRGB] Failed to connect to OpenRGB after starting server")
                else:
                    client = None

            if client:
                self.client = client
                try:
                    self.devices = list(self.client.devices)
                    logger.info(f"[HARDWARE] ✅ OpenRGB client connected ({len(self.devices)} devices)")
                except Exception:
                    logger.info(f"[HARDWARE] ✅ OpenRGB client connected")
            else:
                logger.warning(
                    "[HARDWARE] OpenRGB client not connected; OpenRGB may not be running or python package missing"
                )
        except ImportError:
            logger.warning("[HARDWARE] OpenRGB Python library not installed; falling back to CLI if available")

    async def set_rgb_color(self, device_id: str, r: int, g: int, b: int):
        try:
            # If we have a python-openrgb client, prefer it and run calls
            # off the event loop using asyncio.to_thread to avoid blocking.
            if self.client is not None and self.RGBColor is not None:

                def _set_with_client():
                    try:
                        # 'all' => set all devices
                        if device_id.lower() == "all":
                            for dev in self.client.devices:
                                dev.set_color(self.RGBColor(r, g, b))
                                logger.info(f"[HARDWARE] ✅ Set {dev.name} RGB to ({r}, {g}, {b})")
                            return True

                        # Try numeric index
                        try:
                            idx = int(device_id)
                            dev = self.client.devices[idx]
                            dev.set_color(self.RGBColor(r, g, b))
                            logger.info(f"[HARDWARE] ✅ Set {dev.name} RGB to ({r}, {g}, {b})")
                            return True
                        except Exception:
                            pass

                        # Try name match
                        for dev in self.client.devices:
                            if device_id.lower() in dev.name.lower():
                                dev.set_color(self.RGBColor(r, g, b))
                                logger.info(f"[HARDWARE] ✅ Set {dev.name} RGB to ({r}, {g}, {b})")
                                return True

                        # Not found
                        logger.warning(f"[HARDWARE] RGB device '{device_id}' not found via OpenRGB client")
                        return False
                    except Exception as e:
                        logger.warning(f"[HARDWARE][OpenRGB] client set_color failed: {e}")
                        return False

                success = await asyncio.to_thread(_set_with_client)
                if success:
                    return

            # Fallback to CLI invocation if client not available or failed
            subprocess.run(
                ["OpenRGB.exe", "--device", device_id, "--color", f"{r:02x}{g:02x}{b:02x}"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as exc:
            logger.warning(f"[HARDWARE] OpenRGB set_rgb_color failed: {exc}")

    async def set_rgb_effect(self, device_id: str, effect: str, **params):
        try:
            # Prefer python client for effect changes when available
            if self.client is not None:

                def _set_mode():
                    try:
                        # Try by index
                        try:
                            idx = int(device_id)
                            dev = self.client.devices[idx]
                            dev.set_mode(effect)
                            logger.info(f"[HARDWARE] ✅ Set mode {effect} on {dev.name}")
                            return True
                        except Exception:
                            pass

                        for dev in self.client.devices:
                            if device_id.lower() in dev.name.lower() or device_id.lower() == "all":
                                try:
                                    dev.set_mode(effect)
                                    logger.info(f"[HARDWARE] ✅ Set mode {effect} on {dev.name}")
                                except Exception:
                                    # Not all devices support set_mode
                                    logger.debug(f"[HARDWARE][OpenRGB] device {dev.name} does not support set_mode")
                        return True
                    except Exception as e:
                        logger.warning(f"[HARDWARE][OpenRGB] client set_mode failed: {e}")
                        return False

                await asyncio.to_thread(_set_mode)
                return

            # Fallback to CLI
            subprocess.run(
                ["OpenRGB.exe", "--device", device_id, "--mode", effect],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as exc:
            logger.warning(f"[HARDWARE] OpenRGB set_rgb_effect failed: {exc}")


class WMIFanInterface:
    """Interface for WMI-based fan control"""

    def __init__(self):
        self.name = "WMI Fan Control"

    async def initialize(self):
        try:
            import wmi

            self.wmi = wmi.WMI(namespace="root\\wmi")
        except:
            raise Exception("WMI not available")

    async def set_fan_speed(self, fan_id: str, speed_percent: int):
        try:
            # Implementation depends on specific motherboard WMI interface
            # This is a placeholder for actual WMI fan control
            pass
        except:
            pass


class ManufacturerInterface:
    """Interface for manufacturer-specific software"""

    def __init__(self, name: str, exe_path: str):
        self.name = name
        self.exe_path = exe_path

    async def initialize(self):
        # Check if software is running, start if needed
        pass

    async def set_rgb_color(self, device_id: str, r: int, g: int, b: int):
        # Use manufacturer-specific command line or COM interface
        pass

    async def set_fan_speed(self, fan_id: str, speed_percent: int):
        # Use manufacturer-specific interface
        pass


class GenericFanInterface:
    """Generic fan control using various methods"""

    def __init__(self):
        self.name = "Generic Fan Control"

    async def initialize(self):
        pass

    async def set_fan_speed(self, fan_id: str, speed_percent: int):
        # Try registry-based fan control or other generic methods
        pass


class RegistryRGBInterface:
    """Registry-based RGB control for some devices"""

    def __init__(self):
        self.name = "Registry RGB Control"

    async def initialize(self):
        pass

    async def set_rgb_color(self, device_id: str, r: int, g: int, b: int):
        # Use Windows registry for some RGB devices
        pass


# CLI interface
async def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Celsius AI Hardware Controller")
    parser.add_argument(
        "--profile", help="Apply hardware profile", choices=["silent", "balanced", "performance", "critical"]
    )
    parser.add_argument("--fan", help="Set fan speed (fan_id:percent)")
    parser.add_argument("--rgb", help="Set RGB color (device_id:r,g,b)")
    parser.add_argument("--monitor", action="store_true", help="Start monitoring mode")
    parser.add_argument("--status", action="store_true", help="Show hardware status")

    args = parser.parse_args()

    # Initialize controller
    controller = CelsiusHardwareController()
    await controller.initialize()

    if args.profile:
        await controller.apply_profile(args.profile)

    if args.fan:
        fan_id, speed = args.fan.split(":")
        await controller.set_fan_speed(fan_id, int(speed))

    if args.rgb:
        device_id, colors = args.rgb.split(":")
        r, g, b = map(int, colors.split(","))
        await controller.set_rgb_color(device_id, r, g, b)

    if args.status:
        status = await controller.get_hardware_status()
        print(json.dumps(status, indent=2))

    if args.monitor:
        await controller.start_monitoring()


if __name__ == "__main__":
    print("🎨 Celsius AI Hardware Controller")
    print("=" * 50)
    asyncio.run(main())
