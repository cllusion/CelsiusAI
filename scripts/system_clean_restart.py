#!/usr/bin/env python3
"""
🔄 Celsius AI - Asynchronous System Clean & Restart
A modern, async-native script to gracefully stop, clean, and restart all
Celsius AI services.
"""

import asyncio
import logging
import sys
from pathlib import Path
import psutil
import shutil

# --- Configuration ---
# Configure logging for clear and informative output
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# Define the project's root directory relative to this script's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# List of identifiable strings for Celsius AI processes
# These should be unique parts of the command line arguments for each service
CELSIUS_PROCESS_IDENTIFIERS = [
    "src.hub.celsius_ultimate_hub",
    "src.guardian.celsius_lightweight_guardian",
    "src.dashboard.enhanced_mobile_dashboard",
    "src.core.main",
    "src.learning.celsius_web_learning_launcher",
]

# --- Main Functions ---


async def stop_existing_processes() -> None:
    """Find and terminate all running Celsius AI processes."""
    logging.info("🛑 Stopping all existing Celsius AI processes...")
    found_procs = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if not proc.info["cmdline"]:
                continue

            cmd_str = " ".join(proc.info["cmdline"])
            if any(identifier in cmd_str for identifier in CELSIUS_PROCESS_IDENTIFIERS):
                found_procs.append(proc)
                logging.info(f"   - Found process: {proc.name()} (PID: {proc.pid})")

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not found_procs:
        logging.info("   ✅ No running Celsius AI processes found.")
        return

    for proc in found_procs:
        try:
            proc.terminate()
            logging.info(f"   - Terminating PID {proc.pid}...")
        except psutil.Error as e:
            logging.warning(f"   - Could not terminate PID {proc.pid}: {e}")

    # Wait for processes to terminate
    await asyncio.sleep(3)
    logging.info("   ✅ Termination commands sent.")


async def clean_system_state() -> None:
    """Clean up temporary files, logs, and databases for a fresh start."""
    logging.info("🧹 Cleaning system state (logs and databases)...")

    # Option 1: Delete and re-initialize (cleanest)
    if DATA_DIR.exists():
        try:
            shutil.rmtree(DATA_DIR)
            logging.info(f"   - Removed data directory: {DATA_DIR}")
        except OSError as e:
            logging.error(f"   - Error removing data directory: {e}")

    # Re-run the main initialization script to recreate everything cleanly
    logging.info("   - Running database and directory initialization script...")
    init_script_path = PROJECT_ROOT / "scripts" / "init_db.py"

    process = await asyncio.create_subprocess_exec(
        sys.executable, str(init_script_path), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        logging.info("   ✅ System state successfully re-initialized.")
        if stdout:
            logging.debug(f"Init script output:\n{stdout.decode()}")
    else:
        logging.error("   ❌ Failed to re-initialize system state.")
        if stderr:
            logging.error(f"Init script error:\n{stderr.decode()}")


async def start_services() -> None:
    """Start all core services using the smart launcher."""
    logging.info("🚀 Starting all services using the Smart Asynchronous Launcher...")
    launcher_script_path = PROJECT_ROOT / "scripts" / "smart_persistent_launcher.py"

    try:
        # We launch this in a new console so the user can see the output
        # and so it runs independently of this restart script.
        await asyncio.create_subprocess_exec(
            sys.executable, str(launcher_script_path), creationflags=asyncio.subprocess.CREATE_NEW_CONSOLE
        )
        logging.info("   ✅ Smart launcher initiated in a new window.")
        logging.info("   - The launcher will now manage the startup of all services.")
    except Exception as e:
        logging.critical(f"   💥 Failed to start the smart launcher: {e}", exc_info=True)


async def main() -> None:
    """Main entry point for the system clean and restart script."""
    header = "🔄  Celsius AI - Asynchronous System Clean & Restart  🔄"
    print("=" * len(header))
    print(header)
    print("=" * len(header))

    try:
        # Step 1: Stop all running services
        await stop_existing_processes()

        # Step 2: Clean the environment
        await clean_system_state()

        # Step 3: Start all services
        await start_services()

        print("\n" + "=" * len(header))
        logging.info("🎉 System restart sequence initiated successfully!")
        logging.info("👀 Please monitor the new launcher window for service status.")
        logging.info("🖥️  The Ultimate Hub can be started separately if needed.")
        print("=" * len(header))

    except Exception as e:
        logging.critical(f"💥 A critical error occurred during the restart sequence: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Ensure psutil is installed
    try:
        import psutil
    except ImportError:
        print("Error: 'psutil' package not found. Please install it using: pip install psutil")
        sys.exit(1)

    asyncio.run(main())
    sys.exit(0)
