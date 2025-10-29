#!/usr/bin/env python3
"""
🛡️ Celsius AI - Smart Asynchronous Launcher
An intelligent, asynchronous launcher that starts services in an optimal order,
monitors their status, and handles graceful shutdown.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# --- Configuration ---
# Configure logging for clear and informative output
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# Define the project's root directory relative to this script's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Define the services to be launched in an optimal order
SERVICES = [
    {
        "name": "Enhanced Dashboard",
        "module": "src.dashboard.enhanced_mobile_dashboard",
        "delay": 3,
        "critical": True,
    },
    {
        "name": "Celsius Core",
        "module": "src.core.main",
        "delay": 2,
        "critical": True,
    },
    {
        "name": "Web Learning Engine",
        "module": "src.learning.celsius_web_learning_launcher",
        "delay": 5,
        "critical": False,
    },
    {
        "name": "Lightweight Guardian",
        "module": "src.guardian.celsius_lightweight_guardian",
        "delay": 3,
        "critical": True,
    },
]


async def launch_service(service: dict, processes: dict) -> None:
    """
    Asynchronously launches a single service as a subprocess.

    Args:
        service (dict): Configuration for the service to launch.
        processes (dict): A dictionary to store active subprocess objects.
    """
    name = service["name"]
    module = service["module"]
    delay = service["delay"]
    is_critical = service["critical"]

    logging.info(f"🚀 Attempting to launch: {name}...")
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            module,
            cwd=str(PROJECT_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for a specified delay to allow for initialization
        await asyncio.sleep(delay)

        # Verify that the process has not terminated immediately
        if process.returncode is None:
            logging.info(f"✅ {name} launched successfully (PID: {process.pid})")
            processes[name] = process
        else:
            logging.error(f"❌ {name} failed to launch (exit code: {process.returncode})")
            if is_critical:
                logging.warning(f"⚠️ Critical service '{name}' failed. System may be unstable.")
            # Log error output for debugging
            _, stderr = await process.communicate()
            if stderr:
                logging.error(f"Error output for {name}:\n{stderr.decode().strip()}")

    except FileNotFoundError:
        logging.error(f"❌ Could not find the Python interpreter '{sys.executable}'.")
    except Exception as e:
        logging.critical(f"💥 Critical error launching {name}: {e}", exc_info=True)


async def monitor_running_services(processes: dict) -> None:
    """
    A simple monitoring loop to report the status of launched services.
    This is not a replacement for the Guardian, but a launcher-level check.
    """
    logging.info("👀 Starting simple monitoring loop (Press Ctrl+C to shut down)...")
    while True:
        guardian_running = False
        for name, process in list(processes.items()):
            if process.returncode is not None:
                logging.warning(f"⚠️ Service '{name}' has terminated unexpectedly (exit code: {process.returncode}).")
                # Remove from active processes
                del processes[name]
            elif "Guardian" in name:
                guardian_running = True

        if guardian_running:
            logging.info("🛡️ Guardian monitoring is active.")
        else:
            logging.warning("⚠️ Guardian service not detected. Services may not be persistent.")

        await asyncio.sleep(60)  # Check status every minute


async def main() -> None:
    """Main entry point for the Smart Asynchronous Launcher."""
    header = "🛡️  Celsius AI - Smart Asynchronous Launcher  🛡️"
    print("=" * len(header))
    print(header)
    print(f"🕒  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * len(header))

    logging.info("📋 Service Startup Plan:")
    for i, service in enumerate(SERVICES, 1):
        critical_flag = " (Critical)" if service["critical"] else ""
        logging.info(f"   {i}. {service['name']}{critical_flag}")

    active_processes = {}

    # Launch services sequentially to respect dependencies and order
    for service in SERVICES:
        await launch_service(service, active_processes)

    print("\n" + "-" * 30)
    logging.info("📊 Startup Summary:")
    logging.info(f"   - Planned Services: {len(SERVICES)}")
    logging.info(f"   - Active Services:  {len(active_processes)}")
    print("-" * 30 + "\n")

    if not active_processes:
        logging.error("❌ No services were started successfully. Please check logs.")
        return

    logging.info("🎯 Running Services:")
    for name in active_processes:
        logging.info(f"   • {name}")

    try:
        await monitor_running_services(active_processes)
    except asyncio.CancelledError:
        logging.info("Launcher task was cancelled.")
    finally:
        # --- Graceful Shutdown ---
        logging.info("\n🛑 Shutting down all managed services...")
        # Terminate processes in reverse order of startup
        for name, process in reversed(list(active_processes.items())):
            if process.returncode is None:
                try:
                    process.terminate()
                    logging.info(f"   🔄 Terminated {name} (PID: {process.pid})")
                except ProcessLookupError:
                    logging.warning(f"   - {name} (PID: {process.pid}) already exited.")
                except Exception as e:
                    logging.error(f"   ❌ Error terminating {name}: {e}")

        # Wait for processes to terminate
        await asyncio.sleep(2)
        logging.info("✅ All services have been instructed to shut down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\n👋 KeyboardInterrupt received. Initiating graceful shutdown.")
