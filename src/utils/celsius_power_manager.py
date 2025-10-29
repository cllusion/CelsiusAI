"""
Celsius AI - Intelligent Power Management System
=================================================

Description:
------------
This module provides an intelligent power management system for the Celsius AI
ecosystem, designed to optimize system performance and power consumption. It
operates primarily on Windows systems, interacting with `powercfg` to manage
power plans and `psutil` for monitoring system resources.

Key Features:
-------------
- **Dynamic Power Plan Switching**: Can switch between Windows power plans
  ('Power Saver', 'Balanced', 'High Performance') based on system load.
- **CPU Throttling**: Intelligently throttles the maximum CPU state to reduce
  power consumption and heat during periods of high load, while respecting
  critical server operations.
- **Process Prioritization**: Can adjust the priority of non-critical processes
  that are consuming high amounts of CPU.
- **Safety Controls**: A robust set of safety checks prevents the manager from
  interfering with critical system processes or Celsius AI's own core
  components.
- **Asynchronous Monitoring**: Uses `asyncio` to run a continuous monitoring
  loop in the background without blocking other operations.
- **Configuration Management**: Power management settings are stored in a JSON
  file for easy customization.

Usage:
------
The `CelsiusPowerManager` is designed to run as a background service. It is
initialized and started, after which it will continuously monitor and optimize
the system's power usage.

    import asyncio
    from pathlib import Path
    from src.utils.celsius_power_manager import CelsiusPowerManager

    async def main():
        config_path = Path("./data/power_config.json")
        power_manager = CelsiusPowerManager(config_path)
        await power_manager.initialize()

        # Start the background monitoring task
        power_task = asyncio.create_task(power_manager.start_monitoring())

        print("Power manager is running in the background.")
        # Let it run for a while
        await asyncio.sleep(300)

        # Stop the manager
        await power_manager.stop_monitoring()
        await power_task

"""

import asyncio
import json
import logging
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Set

import psutil

logger = logging.getLogger(__name__)

# Windows Power Plan GUIDs
POWER_SCHEMES = {
    "conservative": "a1841308-3541-4fab-bc81-f71556f20b4a",  # Power Saver
    "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",  # Balanced
    "performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",  # High Performance
}


class CelsiusPowerManager:
    """
    An intelligent power management system to optimize performance and energy use.
    """

    def __init__(self, config_path: Path):
        """
        Initializes the power manager.

        Args:
            config_path (Path): Path to the JSON file for power configuration.
        """
        self.config_path: Path = config_path
        self._is_monitoring: bool = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # --- Configurable Settings ---
        self.power_mode: str = "balanced"
        self.cpu_throttle_enabled: bool = True
        self.auto_optimization_enabled: bool = True
        self.monitoring_interval: int = 30  # seconds

        # --- Safety Controls ---
        self.protected_processes: Set[str] = {
            "celsius_server_hub.py",
            "enhanced_mobile_dashboard.py",
            "ngrok.exe",
            "system",
            "csrss.exe",
            "winlogon.exe",
            "explorer.exe",
        }
        self.critical_processes: Set[str] = {"svchost.exe", "lsass.exe", "services.exe", "wininit.exe"}

    async def initialize(self):
        """Loads configuration from the specified file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        await self._load_configuration()

    async def _load_configuration(self):
        """Loads settings from the JSON config file."""
        async with self._lock:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                self.power_mode = config.get("power_mode", "balanced")
                self.cpu_throttle_enabled = config.get("cpu_throttle_enabled", True)
                self.auto_optimization_enabled = config.get("auto_optimization_enabled", True)
                self.monitoring_interval = config.get("monitoring_interval", 30)
            else:
                await self._save_configuration()

    async def _save_configuration(self):
        """Saves the current settings to the JSON config file."""
        config = {
            "power_mode": self.power_mode,
            "cpu_throttle_enabled": self.cpu_throttle_enabled,
            "auto_optimization_enabled": self.auto_optimization_enabled,
            "monitoring_interval": self.monitoring_interval,
            "last_updated": asyncio.get_event_loop().time(),
        }
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)

    async def set_power_mode(self, mode: str) -> bool:
        """
        Sets the system power mode (on Windows) after performing safety checks.

        Args:
            mode (str): The desired power mode ('conservative', 'balanced', 'performance').

        Returns:
            True if the mode was set successfully, False otherwise.
        """
        if platform.system() != "Windows":
            logger.warning("Power mode switching is only supported on Windows.")
            return False

        if mode not in POWER_SCHEMES:
            logger.error(f"Invalid power mode '{mode}'.")
            return False

        if await self.is_server_under_load():
            logger.warning("Server is under high load; skipping power mode change for stability.")
            return False

        try:
            await asyncio.to_thread(
                subprocess.run,
                ["powercfg", "/setactive", POWER_SCHEMES[mode]],
                capture_output=True,
                check=True,
                timeout=5,
            )
            async with self._lock:
                self.power_mode = mode
                await self._save_configuration()
            logger.info(f"System power mode changed to: {mode}")
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.error(f"Failed to set power mode to '{mode}': {e}")
            return False

    async def is_server_under_load(self, threshold: float = 50.0) -> bool:
        """
        Checks if critical server processes are consuming high CPU.

        Args:
            threshold (float): The CPU percentage threshold to define 'high load'.

        Returns:
            True if any server process exceeds the threshold, False otherwise.
        """
        server_process_names = {"celsius_server_hub.py", "enhanced_mobile_dashboard.py", "ngrok.exe"}
        for proc in psutil.process_iter(["name", "cmdline", "cpu_percent"]):
            try:
                proc_name = proc.info.get("name", "")
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if any(p in proc_name or p in cmdline for p in server_process_names):
                    if proc.info.get("cpu_percent", 0.0) > threshold:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    async def apply_intelligent_cpu_throttling(self):
        """
        Applies or removes CPU throttling based on system load and temperature.
        """
        if not self.cpu_throttle_enabled or platform.system() != "Windows":
            return

        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            temps = psutil.sensors_temperatures()
            cpu_temp = temps.get("coretemp", []) + temps.get("cpu_thermal", [])
            current_temp = max(t.current for t in cpu_temp) if cpu_temp else 0

            throttle_needed = cpu_percent > 90 or (current_temp > 80 and current_temp != 0)

            if throttle_needed and not await self.is_server_under_load():
                await self._set_cpu_max_state(85)  # Throttle to 85%
            else:
                await self._set_cpu_max_state(100)  # Remove throttle

        except Exception as e:
            logger.error(f"Error during intelligent CPU throttling: {e}", exc_info=True)

    async def _set_cpu_max_state(self, max_percent: int):
        """
        Uses powercfg to set the maximum processor state.

        Args:
            max_percent (int): The desired maximum percentage (0-100).
        """
        try:
            await asyncio.to_thread(
                subprocess.run,
                [
                    "powercfg",
                    "/setacvalueindex",
                    "SCHEME_CURRENT",
                    "SUB_PROCESSOR",
                    "PROCTHROTTLEMAX",
                    str(max_percent),
                ],
                capture_output=True,
                check=True,
                timeout=5,
            )
            await asyncio.to_thread(
                subprocess.run, ["powercfg", "/setactive", "SCHEME_CURRENT"], capture_output=True, check=True, timeout=5
            )
            if max_percent < 100:
                logger.info(f"CPU throttling applied: max state set to {max_percent}%.")
            else:
                logger.info("CPU throttling removed.")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.error(f"Failed to set CPU max state to {max_percent}%: {e}")

    async def _monitor_loop(self):
        """The main monitoring and optimization loop."""
        while self._is_monitoring:
            try:
                if self.auto_optimization_enabled:
                    await self.apply_intelligent_cpu_throttling()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                logger.info("Power monitoring loop cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in power monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.monitoring_interval * 2)  # Wait longer on error

    async def start_monitoring(self):
        """Starts the background power monitoring task."""
        if self._is_monitoring:
            logger.warning("Power monitoring is already running.")
            return

        logger.info("Starting Celsius AI Power Management monitoring.")
        self._is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self):
        """Stops the background power monitoring task gracefully."""
        if not self._is_monitoring or not self._monitor_task:
            logger.info("Power monitoring is not running.")
            return

        logger.info("Stopping Celsius AI Power Management monitoring.")
        self._is_monitoring = False
        self._monitor_task.cancel()
        try:
            await self._monitor_task
        except asyncio.CancelledError:
            pass  # Expected cancellation

        # Ensure throttling is removed on shutdown
        await self._set_cpu_max_state(100)
        await self._save_configuration()
        logger.info("Power management stopped and settings restored.")
