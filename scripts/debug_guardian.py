#!/usr/bin/env python3
"""
🛡️ Debug Guardian - Asynchronous Troubleshooting Tool

A modernized, asynchronous version of the debug guardian script for launching and
monitoring Celsius AI services. This script is designed for troubleshooting and
development, providing a lightweight way to manage core components.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# --- Configuration ---
# Define the root directory of the project
# Assumes this script is in a 'scripts' subdirectory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Define services to be managed
# Each service is a dictionary with its name, module path, and startup delay.
SERVICES = [
    {
        "name": "Enhanced Dashboard",
        "module": "src.dashboard.enhanced_mobile_dashboard",
        "delay": 3,
    },
    {
        "name": "Celsius Core",
        "module": "src.core.main",
        "delay": 2,
    },
    {
        "name": "Web Learning",
        "module": "src.learning.celsius_web_learning_launcher",
        "delay": 5,
    },
]


async def run_service(service: dict, processes: dict) -> None:
    """
    Starts a single service as a subprocess and monitors its startup.

    Args:
        service (dict): A dictionary containing service configuration.
        processes (dict): A dictionary to store active subprocess objects.
    """
    name = service["name"]
    module = service["module"]
    delay = service["delay"]

    logging.info(f"Attempting to start service: {name}...")

    try:
        # Use '-m' to run modules, which is more robust for packages
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            module,
            cwd=str(PROJECT_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Asynchronously wait for the specified delay
        await asyncio.sleep(delay)

        # Check if the process is still running after the delay
        if process.returncode is None:
            logging.info(f"✅ {name} started successfully (PID: {process.pid})")
            processes[name] = process
        else:
            logging.error(f"❌ {name} failed to start (exit code: {process.returncode})")
            # Log any error output from the process
            stdout, stderr = await process.communicate()
            if stderr:
                logging.error(f"Error output for {name}:\n{stderr.decode().strip()}")

    except FileNotFoundError:
        logging.error(
            f"❌ Could not find the Python interpreter '{sys.executable}'.",
        )
    except Exception as e:
        logging.critical(f"💥 Critical error starting {name}: {e}", exc_info=True)


async def monitor_services(processes: dict) -> None:
    """
    Periodically checks the status of running services.

    Args:
        processes (dict): A dictionary of active subprocesses.
    """
    logging.info("🔍 Starting service monitoring loop (Press Ctrl+C to stop).")
    check_count = 0
    while True:
        check_count += 1
        active_services = []

        for name, process in list(processes.items()):
            if process.returncode is None:
                active_services.append(name)
            else:
                logging.warning(f"⚠️ {name} has stopped (exit code: {process.returncode}). Removing from monitoring.")
                del processes[name]

        if check_count % 10 == 0:  # Log status periodically
            logging.info(
                f"🛡️ Monitor check #{check_count}: {len(active_services)} services running: {', '.join(active_services)}"
            )

        await asyncio.sleep(30)  # Check every 30 seconds


async def main() -> None:
    """
    Main entry point for the Debug Guardian.
    Launches and monitors all defined services.
    """
    print("=" * 40)
    print("🛡️  Celsius AI - Asynchronous Debug Guardian  🛡️")
    print(f"🕒  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 40)

    processes = {}

    # Create and run startup tasks concurrently
    startup_tasks = [run_service(service, processes) for service in SERVICES]
    await asyncio.gather(*startup_tasks)

    logging.info(f"🚀 Service startup phase complete. {len(processes)} services active.")

    if not processes:
        logging.warning("No services were started successfully. Exiting.")
        return

    # Start the long-running monitoring task
    try:
        await monitor_services(processes)
    except asyncio.CancelledError:
        logging.info("Guardian task was cancelled.")
    finally:
        # --- Cleanup ---
        logging.info("\n🛑 Shutting down all services...")
        for name, process in processes.items():
            if process.returncode is None:
                try:
                    process.terminate()
                    logging.info(f"   🔄 Terminated {name} (PID: {process.pid})")
                except ProcessLookupError:
                    logging.warning(f"   - {name} (PID: {process.pid}) already exited.")
                except Exception as e:
                    logging.error(f"   ❌ Error terminating {name}: {e}")

        # Allow a moment for processes to terminate
        await asyncio.sleep(1)
        logging.info("✅ Debug Guardian has shut down cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\n👋 KeyboardInterrupt received. Guardian is shutting down.")
