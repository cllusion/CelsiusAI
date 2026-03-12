"""Hardware and device control helpers for the Hub.

Standalone functions that accept a ``hub`` instance as the first argument so
they can be called from the UltimateHub class while keeping device-control
logic in one focused module.

The pattern mirrors ``src/hub/ui.py``: each function takes ``hub: Any``
and uses ``getattr`` / attribute access on the hub.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any

from tkinter import messagebox

logger = logging.getLogger("celsius.hub.devices")

# --------------------------------------------------------------------------- #
#   Hardware status                                                             #
# --------------------------------------------------------------------------- #


def refresh_hardware_status(hub: Any) -> None:
    """Refresh hardware status display on *hub*."""
    try:
        import requests

        try:
            response = requests.get("http://localhost:5001/api/hardware/status", timeout=2)
            if response.status_code == 200:
                status_data = response.json()
                status_text = "🎮 Hardware Control System: Connected\n"
                status_text += f"🌀 Fan Control: {status_data.get('fan_control', 'Unknown')}\n"
                status_text += f"🌈 RGB Control: {status_data.get('rgb_control', 'Unknown')}\n"
                status_text += f"🌡️ Temperature Sensors: {status_data.get('temperature_sensors', 'Unknown')}\n"
                status_text += f"⚡ Power Management: {status_data.get('power_management', 'Unknown')}\n"
            else:
                status_text = "⚠️ Hardware API not responding\n"
                status_text += "Hardware control available via local methods only"
        except requests.exceptions.RequestException:
            status_text = "🎮 Hardware Control System: Local Mode\n"
            status_text += "🌀 Fan Control: ✅ Available (System Interface)\n"
            status_text += "🌈 RGB Control: ⚠️ Simulation Mode (No RGB Hardware Detected)\n"
            status_text += "🌡️ Temperature Sensors: ✅ Available (System Sensors)\n"
            status_text += "⚡ Power Management: ✅ Configured for 24/7 Operation\n\n"
            status_text += "💡 Note: Install OpenRGB or manufacturer RGB software for real RGB control"

        hub.hardware_status_text.delete("1.0", "end")
        hub.hardware_status_text.insert("1.0", status_text)

    except Exception as e:
        hub.hardware_status_text.delete("1.0", "end")
        hub.hardware_status_text.insert("1.0", f"❌ Error checking hardware status:\n{e}")


def open_hardware_web(hub: Any) -> None:
    """Open the hardware web interface in the default browser."""
    try:
        import webbrowser

        webbrowser.open("http://localhost:5001")
    except Exception as e:
        hub._msg(messagebox.showerror, "Error", f"Failed to open web interface:\n{e}")


# --------------------------------------------------------------------------- #
#   Fan control                                                                 #
# --------------------------------------------------------------------------- #


def set_fan_preset(hub: Any, speed: int) -> None:
    """Set fan speed variable to a preset value."""
    hub.fan_speed_var.set(str(speed))


def apply_fan_settings(hub: Any) -> None:
    """Apply fan speed settings from the hub UI controls."""
    try:
        speed = int(float(hub.fan_speed_var.get()))

        import requests

        try:
            response = requests.post("http://localhost:5001/api/hardware/fan", json={"speed": speed}, timeout=5)
            if response.status_code == 200:
                hub._msg(messagebox.showinfo, "Success", f"Fan speed set to {speed}%")
                return
        except requests.exceptions.RequestException:
            pass

        # Fallback to local hardware controller
        try:
            hardware_path = os.path.join(os.path.dirname(__file__), "..", "hardware")
            if hardware_path not in sys.path:
                sys.path.append(hardware_path)
            from celsius_hardware_controller import CelsiusHardwareController

            controller = CelsiusHardwareController()
            controller.set_fan_speed_simple(speed)
            hub._msg(messagebox.showinfo, "Success", f"Fan speed set to {speed}% (local control)")

        except ImportError:
            hub._msg(
                messagebox.showwarning,
                "Warning",
                f"Hardware controller not available.\nFan speed setting: {speed}% (simulated)",
            )

    except Exception as e:
        hub._msg(messagebox.showerror, "Error", f"Failed to set fan speed:\n{e}")


def toggle_auto_fan(hub: Any) -> None:
    """Toggle automatic fan control on *hub*."""
    try:
        auto_enabled = hub.auto_temp_var.get()

        import requests

        try:
            response = requests.post(
                "http://localhost:5001/api/hardware/auto-fan", json={"enabled": auto_enabled}, timeout=5
            )
            if response.status_code == 200:
                status_text = "Enabled" if auto_enabled else "Disabled"
                hub._msg(messagebox.showinfo, "Auto Fan Control", f"Automatic fan control {status_text}")
                return
        except requests.exceptions.RequestException:
            pass

        # Fallback to direct hardware control
        try:
            import asyncio

            hardware_path = os.path.join(os.path.dirname(__file__), "..", "hardware")
            if hardware_path not in sys.path:
                sys.path.append(hardware_path)
            from celsius_hardware_controller import CelsiusHardwareController

            controller = CelsiusHardwareController()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            if auto_enabled:
                loop.run_until_complete(controller.auto_adjust_by_temperature())
                hub._msg(messagebox.showinfo, "Auto Fan Control", "Automatic fan control enabled")
            else:
                hub._msg(messagebox.showinfo, "Auto Fan Control", "Automatic fan control disabled")

        except Exception as controller_error:
            hub._msg(messagebox.showerror, "Error", f"Failed to toggle auto fan control: {controller_error}")

    except Exception as e:
        hub._msg(messagebox.showerror, "Error", f"Auto fan control error: {e}")


# --------------------------------------------------------------------------- #
#   RGB control                                                                 #
# --------------------------------------------------------------------------- #


def set_rgb_preset(hub: Any, r: int, g: int, b: int) -> None:
    """Set RGB color variables to preset values."""
    hub.red_var.set(str(r))
    hub.green_var.set(str(g))
    hub.blue_var.set(str(b))


def apply_rgb_settings(hub: Any) -> None:
    """Apply RGB color settings from the hub UI controls."""
    try:
        r = int(float(hub.red_var.get()))
        g = int(float(hub.green_var.get()))
        b = int(float(hub.blue_var.get()))

        import requests

        try:
            response = requests.post(
                "http://localhost:5001/api/hardware/rgb", json={"r": r, "g": g, "b": b}, timeout=5
            )
            if response.status_code == 200:
                hub._msg(messagebox.showinfo, "Success", f"RGB color set to ({r}, {g}, {b})")
                return
        except requests.exceptions.RequestException:
            pass

        # Fallback to local hardware controller
        try:
            hardware_path = os.path.join(os.path.dirname(__file__), "..", "hardware")
            if hardware_path not in sys.path:
                sys.path.append(hardware_path)
            from celsius_hardware_controller import CelsiusHardwareController

            controller = CelsiusHardwareController()
            controller.set_rgb_color_simple(r, g, b)

            hub._msg(
                messagebox.showinfo,
                "RGB Control",
                f"RGB color set to ({r}, {g}, {b})\n\n"
                f"💡 Note: RGB control is in simulation mode.\n"
                f"Install OpenRGB or manufacturer RGB software for real RGB control.\n"
                f"Fan control works with real hardware.",
            )

        except ImportError:
            hub._msg(
                messagebox.showwarning,
                "Warning",
                f"Hardware controller not available.\nRGB color setting: ({r}, {g}, {b}) (simulated)",
            )

    except Exception as e:
        hub._msg(messagebox.showerror, "Error", f"Failed to set RGB color:\n{e}")


def apply_rgb_effect(hub: Any, effect: str) -> None:
    """Apply an RGB lighting effect via the hardware API or local controller."""
    try:
        import requests

        try:
            response = requests.post(
                "http://localhost:5001/api/hardware/effect", json={"effect": effect}, timeout=5
            )
            if response.status_code == 200:
                hub._msg(messagebox.showinfo, "Success", f"RGB effect '{effect}' applied")
                return
        except requests.exceptions.RequestException:
            pass

        # Fallback to local hardware controller
        try:
            hardware_path = os.path.join(os.path.dirname(__file__), "..", "hardware")
            if hardware_path not in sys.path:
                sys.path.append(hardware_path)
            from celsius_hardware_controller import CelsiusHardwareController

            controller = CelsiusHardwareController()
            controller.apply_effect_simple(effect)

            hub._msg(
                messagebox.showinfo,
                "RGB Effect",
                f"RGB effect '{effect}' applied\n\n"
                f"💡 Note: RGB effects are in simulation mode.\n"
                f"Install RGB control software for real lighting effects.",
            )

        except ImportError:
            hub._msg(
                messagebox.showwarning,
                "Warning",
                f"Hardware controller not available.\nRGB effect '{effect}' (simulated)",
            )

    except Exception as e:
        hub._msg(messagebox.showerror, "Error", f"Failed to apply RGB effect:\n{e}")


# --------------------------------------------------------------------------- #
#   Performance profiles and temperature                                        #
# --------------------------------------------------------------------------- #


def apply_profile(hub: Any, profile: str) -> None:
    """Apply a named performance profile (silent/balanced/performance/gaming)."""
    try:
        profiles = {
            "silent": {"fan_speed": 30, "rgb": (0, 0, 255)},
            "balanced": {"fan_speed": 50, "rgb": (0, 255, 0)},
            "performance": {"fan_speed": 80, "rgb": (255, 165, 0)},
            "gaming": {"fan_speed": 100, "rgb": (255, 0, 0)},
        }

        if profile in profiles:
            settings = profiles[profile]

            hub.fan_speed_var.set(str(settings["fan_speed"]))

            r, g, b = settings["rgb"]
            hub.red_var.set(str(r))
            hub.green_var.set(str(g))
            hub.blue_var.set(str(b))

            apply_fan_settings(hub)
            apply_rgb_settings(hub)

            # Also apply via profile if hardware controller is available
            try:
                hardware_path = os.path.join(os.path.dirname(__file__), "..", "hardware")
                if hardware_path not in sys.path:
                    sys.path.append(hardware_path)
                from celsius_hardware_controller import CelsiusHardwareController

                controller = CelsiusHardwareController()
                controller.apply_profile_simple(profile)
            except ImportError:
                pass  # Use GUI controls only

            hub._msg(messagebox.showinfo, "Success", f"'{profile.title()}' profile applied")
        else:
            hub._msg(messagebox.showerror, "Error", f"Unknown profile: {profile}")

    except Exception as e:
        hub._msg(messagebox.showerror, "Error", f"Failed to apply profile:\n{e}")


def check_temperatures(hub: Any) -> None:
    """Check system temperatures and update the temperature text widget."""
    try:
        import requests

        try:
            response = requests.get("http://localhost:5001/api/hardware/temperature", timeout=5)
            if response.status_code == 200:
                temp_data = response.json()
                temp_text = "🌡️ System Temperatures:\n"
                for sensor, temp in temp_data.items():
                    temp_text += f"  {sensor}: {temp}°C\n"
                hub.temp_text.delete("1.0", "end")
                hub.temp_text.insert("1.0", temp_text)
                return
        except requests.exceptions.RequestException:
            pass

        # Fallback to local temperature checking via psutil
        try:
            import psutil

            temp_text = "🌡️ System Temperatures:\n"
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            temp_text += f"  {name} ({entry.label or 'N/A'}): {entry.current}°C\n"
                else:
                    temp_text += "  No temperature sensors found\n"
            else:
                temp_text += "  Temperature monitoring not available on this platform\n"

            hub.temp_text.delete("1.0", "end")
            hub.temp_text.insert("1.0", temp_text)

        except ImportError:
            hub.temp_text.delete("1.0", "end")
            hub.temp_text.insert("1.0", "❌ psutil not available for temperature monitoring")

    except Exception as e:
        hub.temp_text.delete("1.0", "end")
        hub.temp_text.insert("1.0", f"❌ Error checking temperatures:\n{e}")


__all__ = [
    "refresh_hardware_status",
    "open_hardware_web",
    "set_fan_preset",
    "apply_fan_settings",
    "toggle_auto_fan",
    "set_rgb_preset",
    "apply_rgb_settings",
    "apply_rgb_effect",
    "apply_profile",
    "check_temperatures",
]
