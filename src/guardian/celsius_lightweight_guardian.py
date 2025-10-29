#!/usr/bin/env python3
"""
🛡️ Celsius AI - Lightweight Guardian 🛡️
A streamlined, asynchronous monitoring and recovery system for Celsius AI services.
"""

import asyncio
import logging
import sys
from pathlib import Path
import time
import json
import aiosqlite
from typing import List

# --- Configuration ---
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "celsius_monitoring.db"
CONFIG_PATH = PROJECT_ROOT / "config" / "guardian_config.json"

DEFAULT_CONFIG = {
    "check_interval_seconds": 30,
    "services": [
        {
            "name": "Celsius Core",
            "module": "src.core.main",
            "enabled": True,
            "max_restarts": 5,
            "restart_delay_seconds": 10,
        },
        {
            "name": "Enhanced Dashboard",
            "module": "src.dashboard.enhanced_mobile_dashboard",
            "enabled": True,
            "max_restarts": 3,
            "restart_delay_seconds": 5,
        },
        {
            "name": "Web Learning Engine",
            "module": "src.learning.celsius_web_learning_launcher",
            "enabled": False,
            "max_restarts": 2,
            "restart_delay_seconds": 20,
        },
    ],
}


class Service:
    """Represents a monitored service."""

    def __init__(self, config: dict):
        self.name = config["name"]
        self.module = config["module"]
        self.enabled = config.get("enabled", True)
        self.max_restarts = config.get("max_restarts", 5)
        self.restart_delay = config.get("restart_delay_seconds", 10)

        self.process: asyncio.subprocess.Process | None = None
        self.restart_count = 0
        self.last_start_time = 0.0

    @property
    def is_running(self) -> bool:
        """Check if the service process is currently running."""
        return self.process is not None and self.process.returncode is None

    async def start(self):
        """Start the service as a subprocess."""
        if not self.enabled:
            logging.info(f"Service '{self.name}' is disabled and will not be started.")
            return

        if self.is_running:
            logging.warning(f"Service '{self.name}' is already running.")
            return

        if self.restart_count >= self.max_restarts:
            logging.error(
                f"Service '{self.name}' has reached max restarts ({self.max_restarts}) and will not be started again."
            )
            self.enabled = False  # Disable for this session
            return

        logging.info(f"🚀 Starting service: {self.name}...")
        self.last_start_time = time.time()
        self.restart_count += 1

        try:
            self.process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                self.module,
                cwd=str(PROJECT_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            logging.info(f"✅ Service '{self.name}' started with PID: {self.process.pid}")
            await log_monitoring_event(self.name, "STARTED", f"PID: {self.process.pid}")
        except Exception as e:
            logging.error(f"❌ Failed to start service '{self.name}': {e}", exc_info=True)
            await log_monitoring_event(self.name, "START_FAILED", str(e))

    async def stop(self):
        """Stop the service process."""
        if not self.is_running or self.process is None:
            return

        logging.info(f"🛑 Stopping service: {self.name} (PID: {self.process.pid})...")
        try:
            self.process.terminate()
            await asyncio.wait_for(self.process.wait(), timeout=10)
            logging.info(f"   - Service '{self.name}' terminated gracefully.")
            await log_monitoring_event(self.name, "STOPPED", "Graceful termination.")
        except asyncio.TimeoutError:
            logging.warning(f"   - Service '{self.name}' did not terminate gracefully. Forcing kill...")
            self.process.kill()
            await log_monitoring_event(self.name, "KILLED", "Forced kill after timeout.")
        except Exception as e:
            logging.error(f"   - Error stopping service '{self.name}': {e}")
        finally:
            self.process = None


async def load_config() -> dict:
    """Load guardian configuration from a JSON file."""
    if not CONFIG_PATH.exists():
        logging.warning(f"Configuration file not found at {CONFIG_PATH}. Creating with default settings.")
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG

    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


async def log_monitoring_event(service_name: str, status: str, details: str):
    """Log a monitoring event to the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO monitoring_log (service_name, status, details) VALUES (?, ?, ?)",
            (service_name, status, details),
        )
        await db.commit()


async def guardian_main_loop(services: List[Service], check_interval: int):
    """The main monitoring and recovery loop for the guardian."""
    logging.info(f"Guardian monitoring loop started. Checking every {check_interval} seconds.")

    while True:
        for service in services:
            if not service.enabled:
                continue

            if not service.is_running:
                logging.warning(f"⚠️ Service '{service.name}' is not running. Attempting restart...")
                await log_monitoring_event(
                    service.name,
                    "RESTARTING",
                    f"Service detected as not running. Restart count: {service.restart_count}",
                )
                await asyncio.sleep(service.restart_delay)
                await service.start()

        await asyncio.sleep(check_interval)


async def main():
    """Main entry point for the Lightweight Guardian."""
    header = "🛡️ Celsius AI - Lightweight Guardian 🛡️"
    print("=" * len(header))
    print(header)
    print("=" * len(header))

    config = await load_config()
    services = [Service(s_config) for s_config in config.get("services", [])]
    check_interval = config.get("check_interval_seconds", 30)

    # Initial start of all enabled services
    startup_tasks = [s.start() for s in services if s.enabled]
    await asyncio.gather(*startup_tasks)

    # Start the main monitoring loop
    try:
        await guardian_main_loop(services, check_interval)
    except asyncio.CancelledError:
        logging.info("Guardian shutting down...")
    finally:
        shutdown_tasks = [s.stop() for s in services]
        await asyncio.gather(*shutdown_tasks)
        logging.info("All services have been stopped. Guardian exiting.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Shutting down guardian.")
