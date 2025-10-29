#!/usr/bin/env python3
"""
🛡️ Celsius AI - Persistent Hub Launcher 🛡️
================================================
This script ensures the Celsius Ultimate Hub GUI is always running.
If the Hub window is closed, this launcher will automatically restart it.

To stop this persistent behavior, simply close this terminal window
or press Ctrl+C.
"""

import logging
import subprocess
import sys
import time
import os
from pathlib import Path

import psutil

# --- Configuration ---
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HUB_SCRIPT_PATH = PROJECT_ROOT / "src" / "hub" / "celsius_ultimate_hub.py"
PYTHON_EXECUTABLE = sys.executable
CHECK_INTERVAL_SECONDS = 5  # Check every 5 seconds


def is_hub_running() -> bool:
    """Check if the Celsius Ultimate Hub process is currently running."""
    current_pid = psutil.Process().pid
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            # Exclude the launcher script itself from the check
            if proc.pid == current_pid:
                continue

            # A more specific check to prevent false positives.
            # 1. Is it a python process?
            # 2. Is it running the correct script?
            cmdline = proc.info["cmdline"]
            if cmdline and ("python" in proc.info["name"].lower() or "python.exe" in proc.info["name"].lower()):
                # Check if the second argument is the hub script path
                if len(cmdline) > 1 and Path(cmdline[1]).resolve() == HUB_SCRIPT_PATH.resolve():
                    logging.debug(f"Found running hub process with PID: {proc.pid}")
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Ignore processes that can't be accessed
            pass
    return False


def launch_hub():
    """Launches the Celsius Ultimate Hub GUI as a non-blocking subprocess."""
    if not HUB_SCRIPT_PATH.exists():
        logging.error(f"Hub script not found at: {HUB_SCRIPT_PATH}")
        return

    logging.info("🚀 Relaunching Celsius Ultimate Hub...")
    try:
        # Use Popen to launch the Hub in a new, independent process,
        # setting the current working directory to the project root.
        subprocess.Popen([PYTHON_EXECUTABLE, str(HUB_SCRIPT_PATH)], cwd=PROJECT_ROOT)
        logging.info("Hub has been restarted.")
    except Exception as e:
        logging.error(f"Failed to launch Hub: {e}")


def main():
    """Main loop to ensure the Hub is always running."""
    logging.info("🛡️ Starting Persistent Hub Launcher. Press Ctrl+C in this terminal to stop.")

    while True:
        try:
            if not is_hub_running():
                logging.warning("Hub process not detected. Attempting to launch...")
                launch_hub()

            # Wait for the specified interval before checking again
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logging.info("\n🛑 KeyboardInterrupt received. Shutting down persistent launcher.")
            # Optional: kill the hub process on exit
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                if proc.info["cmdline"] and str(HUB_SCRIPT_PATH) in " ".join(proc.info["cmdline"]):
                    logging.info(f"Terminating Hub process {proc.pid}...")
                    proc.terminate()
                    proc.wait()
            break
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            time.sleep(10)  # Wait longer after an error


if __name__ == "__main__":
    main()
