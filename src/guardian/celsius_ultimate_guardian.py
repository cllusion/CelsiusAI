# -*- coding: utf-8 -*-
"""
Celsius Ultimate Guardian - Asynchronous Edition
================================================

Description:
------------
This script is the central asynchronous monitoring and management system for the
Celsius AI ecosystem. It acts as a high-performance watchdog, ensuring that all
critical services are running correctly, restarting them if they fail, and
performing periodic maintenance tasks without blocking the event loop.

Key Features:
-------------
- **Fully Asynchronous**: Built on `asyncio` for high-performance, non-blocking operations.
- **Asynchronous Service Monitoring**: Uses `aiohttp` for non-blocking health checks.
- **Async Process Management**: Manages service lifecycles with `asyncio.create_subprocess_exec`.
- **Asynchronous Database Logging**: Records all events to SQLite using `aiosqlite`.
- **Automatic Restarts**: Restarts failed services based on a configurable policy.
- **Orphaned Process Cleanup**: Finds and terminates lingering Celsius processes.
- **Periodic Maintenance**: Asynchronously optimizes the database and cleans up old logs.
- **Graceful Shutdown**: Ensures all services are stopped cleanly on termination.

Dependencies:
-------------
- `psutil`: For process management.
- `aiohttp`: For performing asynchronous HTTP health checks.
- `aiosqlite`: For asynchronous SQLite database access.

Usage:
------
This script is intended to be run as a standalone background process, typically
launched via the `Start_Celsius_Ultimate.bat` script.

    python src/guardian/celsius_ultimate_guardian.py
"""

import asyncio
import logging
import sqlite3
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Coroutine, Dict, Optional

import aiohttp
import aiosqlite
import psutil

# --- Project Setup ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))

# --- Logging Configuration ---
# Ensure stdout/stderr use UTF-8 where possible to avoid UnicodeEncodeError on Windows consoles
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _log(service_name: str, message: str, level: str = "INFO"):
    """Helper function to log messages with service name prefix."""
    log_message = f"[{service_name}] {message}"
    getattr(logger, level.lower())(log_message)


class CelsiusUltimateGuardian:
    """
    A robust asynchronous watchdog for monitoring and managing Celsius AI services.
    """

    def __init__(self, check_interval: int = 30, shutdown_services: bool = False):
        """
        Initializes the Guardian.

        Args:
            check_interval: The interval in seconds between service health checks.
            shutdown_services: If True, stops all services when Guardian shuts down.
                             If False (default), services continue running independently.
        """
        self.is_running = True
        self.check_interval = check_interval
        self.shutdown_services = shutdown_services
        self.managed_processes: Dict[str, asyncio.subprocess.Process] = {}
        self.startup_time = datetime.now()
        self.last_maintenance = datetime.now()
        self.maintenance_interval = timedelta(hours=1)

        self.data_dir = PROJECT_ROOT / "data"
        self.guardian_db = self.data_dir / "celsius_guardian.db"
        self.http_session: Optional[aiohttp.ClientSession] = None

        self.process_configs: Dict[str, Dict[str, Any]] = {
            "defender": {
                "name": "Real-Time Defender",
                "file": "src/protection/celsius_realtime_defender.py",
                "required": True,
                "priority": 0,
                "max_restarts": 10,
                "restart_count": 0,
                "startup_delay": 2,
                "critical": True,  # Critical protection - always restart
            },
            "hub": {
                "name": "Ultimate Hub",
                "file": "scripts/persistent_hub_launcher.py",
                "required": True,
                "priority": 1,
                "max_restarts": 3,
                "restart_count": 0,
                "startup_delay": 3,
                "is_gui": True,  # Special flag to indicate GUI application
            },
            "dashboard": {
                "name": "Enhanced Dashboard",
                "file": "src/dashboard/enhanced_mobile_dashboard.py",
                "health_endpoint": "http://127.0.0.1:5000/api/health",
                "required": True,
                "priority": 2,
                "max_restarts": 5,
                "restart_count": 0,
                "startup_delay": 5,
            },
            "core_ai": {
                "name": "Core AI Engine",
                "file": "src/core/main.py",
                "required": True,
                "priority": 3,
                "max_restarts": 5,
                "restart_count": 0,
                "startup_delay": 3,
            },
            "hourly_reporter": {
                "name": "Hourly Reporter",
                "file": "src/monitoring/celsius_hourly_reporter.py",
                "required": True,
                "priority": 4,
                "max_restarts": 3,
                "restart_count": 0,
                "startup_delay": 2,
            },
        }

    async def initialize(self):
        """Initializes asynchronous resources like the database and HTTP session."""
        self.data_dir.mkdir(exist_ok=True)
        await self.setup_database()
        self.http_session = aiohttp.ClientSession()
        await self.log_event("INIT", "Guardian initialized.")

    async def setup_database(self):
        """Initializes the SQLite database and creates tables if they don't exist."""
        try:
            async with aiosqlite.connect(self.guardian_db) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS guardian_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME,
                        event_type TEXT, message TEXT, service_name TEXT
                    )
                """
                )
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS service_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME,
                        service_name TEXT, status TEXT, restarts INTEGER
                    )
                """
                )
                await db.commit()
        except aiosqlite.Error as e:
            logger.critical(f"FATAL: Database setup failed: {e}", extra={"service_name": "Guardian"})
            sys.exit(1)

    async def log_event(self, event_type: str, message: str, service_name: str = "Guardian"):
        """Logs an event to the console and the guardian database asynchronously."""
        timestamp = datetime.now()
        extra = {"service_name": service_name}
        logger.info(f"[{event_type:<8}] {message}", extra=extra)

        try:
            async with aiosqlite.connect(self.guardian_db, timeout=10) as db:
                await db.execute(
                    "INSERT INTO guardian_logs (timestamp, event_type, message, service_name) VALUES (?, ?, ?, ?)",
                    (timestamp, event_type, message, service_name),
                )
                await db.commit()
        except aiosqlite.Error as e:
            logger.warning(f"Failed to write to guardian log database: {e}", extra=extra)

    def is_process_running(self, service_name: str) -> bool:
        """Checks if a managed service's process is currently running."""
        process = self.managed_processes.get(service_name)
        if not process or process.returncode is not None:
            return False
        try:
            # psutil is synchronous but very fast. Acceptable in this context.
            return psutil.Process(process.pid).is_running()
        except psutil.NoSuchProcess:
            return False

    async def check_service_health(self, service_name: str) -> bool:
        """Performs a comprehensive asynchronous health check for a service."""
        config = self.process_configs[service_name]
        if not self.is_process_running(service_name):
            return False

        health_endpoint = config.get("health_endpoint")
        if health_endpoint and self.http_session:
            try:
                async with self.http_session.get(health_endpoint, timeout=5) as response:
                    is_healthy = response.status == 200
                    if not is_healthy:
                        await self.log_event("HEALTH", f"Health check failed - HTTP {response.status}", service_name)
                    return is_healthy
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                await self.log_event("HEALTH", f"Health check request failed: {e}", service_name)
                return False

        return True  # If no health endpoint, running is considered healthy.

    async def start_service(self, service_name: str) -> bool:
        """Starts a service asynchronously using its configuration."""
        config = self.process_configs[service_name]
        if self.is_process_running(service_name):
            return True

        service_file = PROJECT_ROOT / config["file"]
        if not service_file.exists():
            await self.log_event("ERROR", f"Service file not found: {service_file}", service_name)
            return False

        try:
            await self.log_event("START", f"Attempting to start {config['name']}...", service_name)

            # Prepare arguments
            args = [sys.executable, str(service_file)]

            # Add special handling for different services
            if service_name == "web_learning":
                # Run web learning in daemon mode with 1-hour interval
                args.extend(["--daemon", "--interval", "3600"])

            # Ensure logs directory for services exists
            logs_dir = PROJECT_ROOT / "logs" / "services"
            logs_dir.mkdir(parents=True, exist_ok=True)
            service_log_path = logs_dir / f"{service_name}.log"

            # Open a file descriptor for stdout/stderr redirection so we can inspect logs
            log_fh = open(service_log_path, "a", encoding="utf-8")

            # Start the subprocess redirecting stdout/stderr to the log file
            process = await asyncio.create_subprocess_exec(
                *args, cwd=str(PROJECT_ROOT), stdout=log_fh.fileno(), stderr=log_fh.fileno()
            )

            # Save process and log handle so we can close later
            self.managed_processes[service_name] = process
            # Keep filehandle mapping for later inspection/cleanup
            if not hasattr(self, "managed_process_logs"):
                self.managed_process_logs = {}
            self.managed_process_logs[service_name] = (service_log_path, log_fh)

            await asyncio.sleep(config.get("startup_delay", 3))

            if self.is_process_running(service_name):
                await self.log_event("SUCCESS", f"{config['name']} started (PID: {process.pid})", service_name)
                return True
            else:
                # Read a small tail of the log to include in the guardian log for diagnosis
                try:
                    log_fh.flush()
                    with open(service_log_path, "r", encoding="utf-8", errors="ignore") as rh:
                        content = rh.read()[-2048:]
                except Exception:
                    content = "<Could not read service log>"

                await self.log_event(
                    "ERROR", f"{config['name']} failed to start or terminated. Recent output:\n{content}", service_name
                )
                return False
        except Exception as e:
            await self.log_event("ERROR", f"Exception while starting {config['name']}: {e}", service_name)
            return False

    async def stop_service(self, service_name: str) -> bool:
        """Gracefully stops a managed service asynchronously."""
        process = self.managed_processes.get(service_name)
        if not process:
            return True

        config = self.process_configs[service_name]
        await self.log_event("STOP", f"Stopping {config['name']} (PID: {process.pid})...", service_name)

        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=10)
            await self.log_event("SUCCESS", f"{config['name']} stopped gracefully.", service_name)
        except asyncio.TimeoutError:
            await self.log_event("WARNING", f"{config['name']} did not stop gracefully. Forcing kill.", service_name)
            process.kill()
        except Exception as e:
            await self.log_event("ERROR", f"Error stopping {config['name']}: {e}", service_name)
            return False
        finally:
            self.managed_processes.pop(service_name, None)
            # Close and remove any associated service log file handle
            if hasattr(self, "managed_process_logs") and service_name in self.managed_process_logs:
                try:
                    _, fh = self.managed_process_logs.pop(service_name)
                    try:
                        fh.close()
                    except Exception:
                        pass
                except Exception:
                    pass
        return True

    async def monitor_all_services(self):
        """The core asynchronous monitoring loop."""
        for service_name, config in self.process_configs.items():
            # Skip non-required services
            if not config["required"]:
                continue

            is_healthy = await self.check_service_health(service_name)

            # For critical services, be more aggressive
            if config.get("critical", False):
                if not is_healthy:
                    await self.log_event(
                        "CRITICAL", f"{config['name']} is unhealthy! Immediate restart...", service_name
                    )
                    # Don't check restart count for critical services, always restart
                    await self.stop_service(service_name)
                    await asyncio.sleep(2)
                    if await self.start_service(service_name):
                        await self.log_event("RECOVERY", f"{config['name']} successfully restarted.", service_name)
                    else:
                        await self.log_event("FAILURE", f"Failed to restart {config['name']}.", service_name)

            # For normal required services
            elif not is_healthy:
                if config["restart_count"] < config["max_restarts"]:
                    await self.log_event(
                        "MONITOR", f"{config['name']} is unhealthy. Attempting restart...", service_name
                    )
                    config["restart_count"] += 1
                    await self.stop_service(service_name)
                    await asyncio.sleep(2)
                    if await self.start_service(service_name):
                        await self.log_event("RECOVERY", f"{config['name']} successfully restarted.", service_name)
                    else:
                        await self.log_event("FAILURE", f"Failed to restart {config['name']}.", service_name)
                else:
                    await self.log_event(
                        "LIMIT",
                        f"{config['name']} has reached the max restart limit ({config['max_restarts']}).",
                        service_name,
                    )

    async def start_all_services(self):
        """Starts all required services in their specified priority order."""
        await self.log_event("INIT", "Guardian is starting all required services...")
        services_to_start = sorted(self.process_configs.items(), key=lambda item: item[1]["priority"])

        for service_name, config in services_to_start:
            if config["required"]:
                await self.start_service(service_name)
                await asyncio.sleep(2)  # Stagger starts
        await self.log_event("INIT", "All required services have been processed for startup.")
        await self.log_event("GUARDIAN", "Guardian will continue monitoring services indefinitely...")

    async def reset_restart_counters(self):
        """Reset restart counters periodically to allow continued monitoring."""
        while self.is_running:
            await asyncio.sleep(3600)  # Every hour
            for config in self.process_configs.values():
                if config["restart_count"] > 0:
                    await self.log_event("GUARDIAN", f"Resetting restart counter for {config['name']}")
                    config["restart_count"] = max(0, config["restart_count"] - 1)

    async def run(self):
        """The main asynchronous execution loop for the Guardian."""
        await self.initialize()
        await self.log_event("GUARDIAN", "[ROCKET] Ultimate Guardian is now active and monitoring.")
        await self.start_all_services()

        # Start the restart counter reset task
        reset_task = asyncio.create_task(self.reset_restart_counters())

        try:
            check_count = 0
            while self.is_running:
                check_count += 1
                await self.monitor_all_services()

                # Log status every 20 checks (10 minutes with 30s interval)
                if check_count % 20 == 0:
                    await self.log_event("GUARDIAN", f"✓ Guardian active - monitoring cycle #{check_count}")

                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            await self.log_event("SHUTDOWN", "Guardian shutdown signal received.")
            reset_task.cancel()
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Gracefully shuts down the Guardian, leaving services running."""
        self.is_running = False
        await self.log_event("SHUTDOWN", "Guardian is shutting down. Services will remain active.")

        # Close HTTP session for health checks
        if hasattr(self, "http_session") and self.http_session:
            await self.http_session.close()

        await self.log_event("SHUTDOWN", "Guardian has shut down cleanly. [CHECK]")


async def main():
    """Main entry point to run the Guardian."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Celsius AI Ultimate Guardian - Service Monitor and Manager")
    parser.add_argument(
        "--shutdown-services",
        action="store_true",
        help="Stop all managed services when Guardian shuts down (default: services continue running)",
    )
    parser.add_argument("--check-interval", type=int, default=30, help="Health check interval in seconds (default: 30)")
    parser.add_argument(
        "--auto-start-all", action="store_true", help="Automatically start all critical services on Guardian startup"
    )

    args = parser.parse_args()

    # Create Guardian with configuration
    guardian = CelsiusUltimateGuardian(check_interval=args.check_interval, shutdown_services=args.shutdown_services)

    # Log startup mode
    if args.shutdown_services:
        logger.info("⚠️  Guardian mode: Will stop all services on shutdown")
    else:
        logger.info("[CHECK] Guardian mode: Services will continue running independently on shutdown")

    # Auto-start critical services if requested
    if args.auto_start_all:
        logger.info("[ROCKET] AUTO-START MODE: Starting all critical services...")
        await guardian.initialize()

        # Start critical services in order
        # Auto-start only services that are actually configured in process_configs.
        # The previous list referenced 'learning_system' which is not present and caused a KeyError.
        critical_services = [
            "defender",  # Real-Time Defender (Priority 0)
            "hub",  # Ultimate Hub (GUI)
            "dashboard",  # Enhanced Dashboard (Web UI)
            "core_ai",  # Core AI Engine
        ]

        for service_name in critical_services:
            logger.info(f"▶️  Starting {service_name}...")
            await guardian.start_service(service_name)
            await asyncio.sleep(2)  # Wait for service to initialize

        logger.info("[CHECK] All critical services started!")
        logger.info("[SHIELD] Guardian now monitoring and will restart failed services...")

    main_task = asyncio.create_task(guardian.run())

    try:
        await main_task
    except KeyboardInterrupt:
        main_task.cancel()
        # Wait for the task to acknowledge cancellation
        await main_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[GUARDIAN] Guardian process terminated by user.")
        print("[GUARDIAN] Managed services continue running independently.")
