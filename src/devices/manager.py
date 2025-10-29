"""
Celsius AI - Device Management Module
=====================================

Description:
------------
This module provides a system for managing and coordinating security across
multiple devices running Celsius AI for a single user. It allows devices to
discover each other on a local network, share security status, and synchronize
threat intelligence.

Key Features:
-------------
- **Device Discovery**: (Simulated) Broadcasts and listens for other Celsius AI
  instances on the local network to build a registry of connected devices.
- **Device Registry**: Maintains a persistent list of known devices, including
  their platform, IP address, and security status.
- **Status Monitoring**: Provides a consolidated view of the security status of all
  managed devices.
- **Security Scoring**: Calculates a security score (0.0 to 1.0) for each device
  based on its platform, security status, and recent activity.
- **Data Synchronization**: (Simulated) Prepares and sends security data, such as
  threat signatures and intelligence, to other devices.
- **Stale Device Cleanup**: Automatically removes devices from the registry that
  have not been seen for a configurable period.

Usage:
------
The `DeviceManager` is typically initialized and managed by the main AI assistant.
It runs background tasks for discovery and synchronization.

    from core.config import load_config
    from devices.manager import DeviceManager

    async def main():
        config = load_config()
        device_manager = DeviceManager(config)

        # Initialize and start discovery
        await device_manager.initialize()
        await device_manager.discover_devices()

        # Get the status of all devices
        all_devices_status = await device_manager.get_device_status()
        print("Current Device Status:")
        for device in all_devices_status:
            print(
                f"- {device['name']} (Score: {device['security_score']:.2f}): {device['status']}"

            )

        # Manually trigger a sync
        await device_manager.sync_security_data()

        # Shutdown gracefully
        await device_manager.shutdown()

"""

import asyncio
import json
import logging
import socket
import platform
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Assuming a config object with attributes like `device_discovery_enabled` and `sync_interval`
from src.core.config import CelsiusConfig

logger = logging.getLogger(__name__)

# Define the root of the project to resolve paths correctly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


class DeviceManager:
    """
    Manages security coordination and data synchronization across multiple
    devices running Celsius AI for a single user.
    """

    def __init__(self, config: CelsiusConfig):
        """
        Initializes the DeviceManager.

        Args:
            config (CelsiusConfig): The application's configuration object.
        """
        self.config: CelsiusConfig = config
        self.devices: Dict[str, Dict[str, Any]] = {}
        self.local_device_id: str = self._get_or_create_device_id()
        self.sync_tasks: List[asyncio.Task] = []
        self.discovery_running: bool = False

        self.local_device: Dict[str, Any] = {
            "id": self.local_device_id,
            "name": platform.node(),
            "platform": platform.system(),
            "platform_version": platform.release(),
            "ip_address": self._get_local_ip(),
            "security_status": "unknown",
            "last_seen": datetime.now().isoformat(),
            "celsius_ai_version": "2.0.0",  # Example version
            "capabilities": [
                "threat_scanning",
                "network_monitoring",
                "file_analysis",
            ],
        }
        self.devices[self.local_device_id] = self.local_device
        logger.info(f"DeviceManager initialized for local device: {self.local_device['name']} ({self.local_device_id})")

    def _get_or_create_device_id(self) -> str:
        """
        Retrieves the persistent device ID or creates a new one.

        Returns:
            str: The unique ID for this device.
        """
        id_file = DATA_DIR / "device_id.txt"
        if id_file.exists():
            return id_file.read_text().strip()

        device_id = str(uuid.uuid4())
        id_file.parent.mkdir(parents=True, exist_ok=True)
        id_file.write_text(device_id)
        return device_id

    async def initialize(self):
        """
        Initializes the device manager by loading the device registry and
        updating local device information.
        """
        try:
            logger.info("Initializing DeviceManager...")
            await self._load_device_registry()
            await self._update_local_device_info()
            logger.info(f"DeviceManager initialized. Found {len(self.devices)} known devices.")
        except Exception as e:
            logger.error(f"Failed to initialize DeviceManager: {e}", exc_info=True)
            raise

    async def start_discovery(self):
        """
        Starts the background task for device discovery if it's enabled and
        not already running.
        """
        if not self.config.device_discovery_enabled:
            logger.info("Device discovery is disabled in the configuration.")
            return

        if self.discovery_running:
            logger.warning("Device discovery is already running.")
            return

        logger.info("Starting device discovery background task...")
        self.discovery_running = True
        task = asyncio.create_task(self._discovery_loop())
        self.sync_tasks.append(task)

    async def _discovery_loop(self):
        """
        The main loop for device discovery, which periodically broadcasts
        discovery messages and cleans up stale devices.
        """
        while self.discovery_running:
            try:
                await self._broadcast_discovery()
                await self._listen_for_devices()  # In a real implementation, this would be a separate, long-running listener
                await self._cleanup_stale_devices()

                await asyncio.sleep(self.config.sync_interval)
            except asyncio.CancelledError:
                logger.info("Discovery loop cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait longer after an error

    async def _broadcast_discovery(self):
        """
        Simulates broadcasting a device discovery message over UDP.
        In a real implementation, this would involve network socket programming.
        """
        discovery_message = {
            "type": "celsius_ai_discovery",
            "device_id": self.local_device_id,
            "device_info": self.local_device,
            "timestamp": datetime.now().isoformat(),
        }
        logger.debug(f"Broadcasting discovery message (simulated): {discovery_message}")
        # In a real implementation:
        # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        # sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # sock.sendto(json.dumps(discovery_message).encode(), ('<broadcast>', 31337))

    async def _listen_for_devices(self):
        """
        Simulates discovering other devices. In a real implementation, this
        would listen for UDP broadcast responses.
        """
        # For demonstration, we'll "discover" a mock device occasionally.
        import random

        if random.random() < 0.2 and len(self.devices) < 4:
            mock_device_id = str(uuid.uuid4())
            mock_device = {
                "id": mock_device_id,
                "name": f"Mock-Device-{random.randint(1, 100)}",
                "platform": random.choice(["Windows", "macOS", "Linux", "Android"]),
                "ip_address": f"192.168.1.{random.randint(100, 200)}",
                "security_status": random.choice(["secure", "warning", "critical"]),
                "last_seen": datetime.now().isoformat(),
                "celsius_ai_version": "2.0.0",
                "capabilities": ["threat_scanning"],
            }
            if mock_device_id not in self.devices:
                self.devices[mock_device_id] = mock_device
                logger.info(f"Discovered new device: {mock_device['name']} ({mock_device['platform']})")

    async def _cleanup_stale_devices(self):
        """Removes devices that have not been seen for a configured threshold."""
        stale_threshold = timedelta(hours=24)
        now = datetime.now()
        stale_ids = [
            dev_id
            for dev_id, dev in self.devices.items()
            if dev_id != self.local_device_id and now - datetime.fromisoformat(dev["last_seen"]) > stale_threshold
        ]

        for dev_id in stale_ids:
            logger.info(f"Removing stale device: {self.devices[dev_id]['name']}")
            del self.devices[dev_id]

    async def get_all_device_statuses(self) -> List[Dict[str, Any]]:
        """
        Retrieves the status and calculated security score for all known devices.

        Returns:
            List[Dict[str, Any]]: A list of device status dictionaries.
        """
        statuses = []
        for dev_id, dev in self.devices.items():
            security_score = await self._calculate_device_security_score(dev)
            statuses.append(
                {
                    "id": dev_id,
                    "name": dev["name"],
                    "platform": dev["platform"],
                    "ip_address": dev.get("ip_address", "N/A"),
                    "status": dev.get("security_status", "unknown"),
                    "last_seen": dev["last_seen"],
                    "is_local": dev_id == self.local_device_id,
                    "security_score": security_score,
                    "capabilities": dev.get("capabilities", []),
                }
            )

        statuses.sort(key=lambda x: x["security_score"], reverse=True)
        return statuses

    async def _calculate_device_security_score(self, device: Dict[str, Any]) -> float:
        """
        Calculates a security score for a device based on various factors.

        Args:
            device (Dict[str, Any]): The device dictionary.

        Returns:
            float: A security score between 0.0 and 1.0.
        """
        score = 0.5  # Start with a neutral base score

        # Adjust based on security status
        status_map = {"secure": 0.3, "warning": 0.0, "critical": -0.4}
        score += status_map.get(device.get("security_status", "unknown").lower(), -0.1)

        # Adjust based on recency
        hours_since_seen = (datetime.now() - datetime.fromisoformat(device["last_seen"]).total_seconds()) / 3600
        if hours_since_seen < 1:
            score += 0.1
        elif hours_since_seen > 24:
            score -= 0.1
        elif hours_since_seen > 168:
            score -= 0.2

        # Adjust based on capabilities
        if "network_monitoring" in device.get("capabilities", []):
            score += 0.1

        return max(0.0, min(1.0, score))

    async def sync_security_data(self, target_device_id: Optional[str] = None):
        """
        Simulates synchronizing security data with one or all other devices.

        Args:
            target_device_id (Optional[str]): The ID of a specific device to sync with.
                                              If None, syncs with all other devices.
        """
        target_devices = [
            dev
            for dev_id, dev in self.devices.items()
            if dev_id != self.local_device_id and (not target_device_id or dev_id == target_device_id)
        ]

        if not target_devices:
            logger.info("No target devices found for synchronization.")
            return

        sync_data = await self._prepare_sync_data()

        for device in target_devices:
            await self._sync_with_device(device, sync_data)

        logger.info(f"Security data synchronization initiated with {len(target_devices)} device(s).")

    async def _prepare_sync_data(self) -> Dict[str, Any]:
        """Prepares a payload of security data to be synchronized."""
        return {
            "source_device_id": self.local_device_id,
            "timestamp": datetime.now().isoformat(),
            "threat_intelligence": {},  # Placeholder for actual threat data
            "security_policies": {},  # Placeholder for policies
            "device_status_update": self.local_device,
        }

    async def _sync_with_device(self, device: Dict[str, Any], sync_data: Dict[str, Any]):
        """Simulates sending a sync payload to a specific device."""
        logger.info(f"Syncing with {device['name']} at {device.get('ip_address', 'N/A')} (simulated).")
        # In a real implementation, this would involve a secure API call or socket connection.
        device["last_seen"] = datetime.now().isoformat()  # Update last_seen on successful sync

    async def _update_local_device_info(self):
        """Updates the information for the local device."""
        self.local_device.update(
            {
                "last_seen": datetime.now().isoformat(),
                "ip_address": self._get_local_ip(),
                "platform_version": platform.release(),
                # This would be updated by the security analysis module
                "security_status": "secure",  # Placeholder
            }
        )

    def _get_local_ip(self) -> str:
        """
        Determines the local IP address of the machine.

        Returns:
            str: The local IP address, or '127.0.0.1' if undetectable.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    async def _load_device_registry(self):
        """Loads the device registry from a JSON file."""
        registry_file = DATA_DIR / "device_registry.json"
        if not registry_file.exists():
            return
        try:
            with open(registry_file, "r", encoding="utf-8") as f:
                saved_devices = json.load(f)

            # Merge saved devices, but prioritize current local device info
            saved_devices.pop(self.local_device_id, None)
            self.devices.update(saved_devices)
            logger.info(f"Loaded {len(saved_devices)} devices from registry.")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load device registry: {e}")

    async def _save_device_registry(self):
        """Saves the current device registry to a JSON file."""
        registry_file = DATA_DIR / "device_registry.json"
        try:
            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump(self.devices, f, indent=4)
        except IOError as e:
            logger.error(f"Failed to save device registry: {e}")

    async def shutdown(self):
        """Gracefully shuts down the DeviceManager."""
        logger.info("Shutting down DeviceManager...")
        self.discovery_running = False

        for task in self.sync_tasks:
            task.cancel()

        if self.sync_tasks:
            await asyncio.gather(*self.sync_tasks, return_exceptions=True)

        await self._save_device_registry()
        logger.info("DeviceManager shutdown complete.")
