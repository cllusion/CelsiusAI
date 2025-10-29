"""
Celsius AI - Real-Time Security Monitoring Module
=================================================

Description:
------------
This module provides a real-time security monitoring system for the Celsius AI
ecosystem. It runs as a background service, continuously observing system
activities such as running processes, network connections, and file system
changes to detect and report potential threats as they happen.

Key Features:
-------------
- **Asynchronous Monitoring**: Utilizes `asyncio` to run multiple monitoring
  coroutines concurrently for processes, network, and files without blocking.
- **Configurable Intervals**: Monitoring frequency for each subsystem (process,
  network, file) can be configured independently.
- **Alerting System**: Features a callback-based alerting mechanism. Other parts
  of the system can register functions to be called when an alert is triggered.
- **Threat Statistics**: Maintains statistics on the number and types of alerts,
  providing a high-level overview of system security health.
- **Alert History**: Keeps a history of recent alerts for review and analysis.
- **Extensible Detection**: The detection logic for processes, network, and files
  is modular, allowing for easy integration with more sophisticated analysis
  tools (like the `ThreatAnalyzer`).
- **Graceful Shutdown**: Provides methods to safely start and stop all monitoring
  coroutines.

Usage:
------
The `SecurityMonitor` is designed to be run as a long-lived service. It is
initialized with a configuration object and started. Callbacks can be added
to handle alerts.

    import asyncio
    from core.config import load_config
    from security.monitor import SecurityMonitor

    async def handle_alert(alert: dict):
        print(f"ALERT RECEIVED: {alert['message']}")

    async def main():
        config = load_config()
        monitor = SecurityMonitor(config)
        monitor.add_alert_callback(handle_alert)

        await monitor.start_monitoring()

        try:
            # Let the monitor run for a while
            await asyncio.sleep(300)
        finally:
            await monitor.stop_monitoring()

"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Callable, Coroutine, Set

from src.core.config import CelsiusConfig
from src.security.analyzer import ThreatAnalyzer

logger = logging.getLogger(__name__)


class SecurityMonitor:
    """
    A real-time security monitoring system that observes system activity and
    triggers alerts for suspicious behavior.
    """

    def __init__(self, config: CelsiusConfig, analyzer: ThreatAnalyzer):
        """
        Initializes the SecurityMonitor.

        Args:
            config (CelsiusConfig): The application's configuration object.
            analyzer (ThreatAnalyzer): The threat analysis engine for performing scans.
        """
        self.config: CelsiusConfig = config
        self.analyzer: ThreatAnalyzer = analyzer
        self.is_monitoring: bool = False
        self.alert_callbacks: List[Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]] = []
        self.monitoring_tasks: Set[asyncio.Task] = set()
        self.alert_history: List[Dict[str, Any]] = []

        # Monitoring intervals from config or defaults
        self.process_monitor_interval: int = self.config.get("monitoring", {}).get("process_interval", 60)
        self.network_monitor_interval: int = self.config.get("monitoring", {}).get("network_interval", 120)
        self.file_monitor_interval: int = self.config.get("monitoring", {}).get("file_interval", 300)

        # Threat statistics
        self.threat_stats: Dict[str, Any] = {
            "total_alerts": 0,
            "process_alerts": 0,
            "network_alerts": 0,
            "file_alerts": 0,
            "last_alert_timestamp": None,
        }

    async def start_monitoring(self):
        """
        Starts the real-time security monitoring tasks if they are not already running.
        """
        if self.is_monitoring:
            logger.warning("Security monitoring is already running.")
            return

        logger.info("Starting real-time security monitoring...")
        self.is_monitoring = True

        try:
            if self.config.get("monitoring", {}).get("enable_process_monitor", True):
                self.monitoring_tasks.add(
                    asyncio.create_task(
                        self._monitor_loop(self._run_process_scan, self.process_monitor_interval, "Process")
                    )
                )
            if self.config.get("monitoring", {}).get("enable_network_monitor", True):
                self.monitoring_tasks.add(
                    asyncio.create_task(
                        self._monitor_loop(self._run_network_scan, self.network_monitor_interval, "Network")
                    )
                )
            if self.config.get("monitoring", {}).get("enable_file_monitor", True):
                self.monitoring_tasks.add(
                    asyncio.create_task(self._monitor_loop(self._run_file_scan, self.file_monitor_interval, "File"))
                )

            logger.info(f"Security monitoring started with {len(self.monitoring_tasks)} tasks.")
        except Exception as e:
            logger.error(f"Failed to start security monitoring: {e}", exc_info=True)
            self.is_monitoring = False
            raise

    async def stop_monitoring(self):
        """
        Stops all active security monitoring tasks gracefully.
        """
        if not self.is_monitoring:
            logger.info("Security monitoring is not running.")
            return

        logger.info("Stopping security monitoring...")
        self.is_monitoring = False

        for task in self.monitoring_tasks:
            if not task.done():
                task.cancel()

        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)

        self.monitoring_tasks.clear()
        logger.info("Security monitoring stopped successfully.")

    async def _monitor_loop(self, scan_func: Callable[[], Coroutine], interval: int, name: str):
        """
        Generic monitoring loop that periodically runs a scan function.

        Args:
            scan_func (Callable): The async scan function to execute.
            interval (int): The time in seconds to wait between scans.
            name (str): The name of the monitor for logging purposes.
        """
        logger.info(f"{name} monitor started with a {interval}s interval.")
        while self.is_monitoring:
            try:
                await scan_func()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info(f"{name} monitor task cancelled.")
                break
            except Exception as e:
                logger.error(f"An error occurred in the {name} monitor loop: {e}", exc_info=True)
                # Wait before retrying to avoid rapid failure loops
                await asyncio.sleep(interval)
        logger.info(f"{name} monitor stopped.")

    async def _run_process_scan(self):
        """Runs a process scan and triggers alerts for any threats found."""
        threats = await self.analyzer._scan_processes()
        for threat in threats:
            alert = self._create_alert(
                "process_alert",
                threat.get("severity", "medium"),
                "process_monitor",
                threat,
                f"Suspicious process detected: {threat.get('name', 'Unknown')}",
            )
            await self._trigger_alert(alert)

    async def _run_network_scan(self):
        """Runs a network scan and triggers alerts for any anomalies found."""
        anomalies = await self.analyzer._scan_network()
        for anomaly in anomalies:
            alert = self._create_alert(
                "network_alert",
                anomaly.get("severity", "high"),
                "network_monitor",
                anomaly,
                f"Network anomaly detected: {anomaly.get('type', 'Unknown')}",
            )
            await self._trigger_alert(alert)

    async def _run_file_scan(self):
        """Runs a file scan and triggers alerts for any threats found."""
        threats = await self.analyzer._scan_files()
        for threat in threats:
            alert = self._create_alert(
                "file_alert",
                threat.get("severity", "critical"),
                "file_monitor",
                threat,
                f"File threat detected: {threat.get('name', 'Unknown')}",
            )
            await self._trigger_alert(alert)

    def _create_alert(self, type: str, severity: str, source: str, data: Dict, message: str) -> Dict[str, Any]:
        """
        Creates a standardized alert dictionary.
        """
        return {
            "type": type,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "data": data,
            "message": message,
        }

    async def _trigger_alert(self, alert: Dict[str, Any]):
        """
        Processes a security alert by updating stats, logging, and notifying callbacks.
        """
        logger.warning(f"SECURITY ALERT: {alert['message']} (Severity: {alert['severity']})")

        # Update statistics
        self.threat_stats["total_alerts"] += 1
        self.threat_stats["last_alert_timestamp"] = alert["timestamp"]
        alert_type_key = f"{alert.get('type', 'unknown').replace('_alert', '')}_alerts"
        if alert_type_key in self.threat_stats:
            self.threat_stats[alert_type_key] += 1

        # Add to history, maintaining a fixed size
        self.alert_history.append(alert)
        max_history = self.config.get("monitoring", {}).get("alert_history_size", 100)
        if len(self.alert_history) > max_history:
            self.alert_history = self.alert_history[-max_history:]

        # Notify registered callbacks concurrently
        if self.alert_callbacks:
            callback_tasks = [cb(alert) for cb in self.alert_callbacks]
            await asyncio.gather(*callback_tasks, return_exceptions=True)

        # TODO: Implement auto-response actions based on config
        # await self._handle_auto_response(alert)

    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]):
        """
        Registers a coroutine function to be called when a security alert is triggered.

        Args:
            callback: An async function that accepts a single argument (the alert dict).
        """
        if callback not in self.alert_callbacks:
            self.alert_callbacks.append(callback)
            logger.info(f"Alert callback '{callback.__name__}' added.")

    def remove_alert_callback(self, callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]):
        """Removes a registered alert callback function."""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
            logger.info(f"Alert callback '{callback.__name__}' removed.")

    def get_monitoring_status(self) -> Dict[str, Any]:
        """

        Retrieves the current status of the monitoring system, including statistics
        and recent alerts.

        Returns:
            A dictionary containing the monitoring status.
        """
        return {
            "is_monitoring": self.is_monitoring,
            "active_tasks": len([task for task in self.monitoring_tasks if not task.done()]),
            "threat_stats": self.threat_stats.copy(),
            "recent_alerts": self.alert_history[-5:],
        }
