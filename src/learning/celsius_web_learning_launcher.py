#!/usr/bin/env python3
"""
Celsius AI Web Learning Launcher (Async Edition)
================================================
A command-line interface to start, monitor, and interact with the
asynchronous web learning system.

Features:
- Provides a simple, interactive shell.
- All operations are non-blocking, using `asyncio`.
- Integrates with the async `CelsiusWebLearningIntegration`.
- Allows starting/stopping learning, checking status, and searching content.
"""

import asyncio
import sys
from pathlib import Path
import logging

# --- Project Imports ---
# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Track critical import errors without exiting immediately so the launcher
# won't make the console window appear and disappear. The hub sometimes
# starts this script in a new console; keeping the process alive helps
# capture and diagnose missing-dependency issues.
critical_import_error = None
try:
    from src.learning.celsius_web_learning_integration import (
        get_web_learning_integration,
        CelsiusWebLearningIntegration,
    )
    from src.learning.celsius_web_learning_dashboard import WebLearningDashboard
    from ttkthemes import ThemedTk
except ImportError as e:
    critical_import_error = str(e)
    # Print the error (also log later) but do not exit here; main() will handle it.
    print(
        f"❌ Critical Import Error: {critical_import_error}. Please ensure all dependencies are installed and paths are correct.",
        file=sys.stderr,
    )

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


class CelsiusWebLearningLauncher:
    """
    An asynchronous launcher for the Celsius AI web learning system.
    """

    def __init__(self, integration: CelsiusWebLearningIntegration):
        self.integration = integration
        self.logger = logging.getLogger("WebLearningLauncher")

    def display_banner(self):
        """Displays the startup banner."""
        print("\n" + "=" * 60)
        print("    CELSIUS AI WEB LEARNING LAUNCHER (ASYNC)")
        print("=" * 60)
        print("   Type 'help' for a list of available commands.")
        print()

    def show_menu(self):
        """Shows the main menu of available commands."""
        print("\nAVAILABLE COMMANDS:")
        print("-------------------")
        print("  start      - Start the continuous web learning process.")
        print("  stop       - Stop the web learning process gracefully.")
        print("  status     - Show the current status of the learning system.")
        print("  learn      - Perform a single, on-demand learning session.")
        print("  search     - Search the learned content database.")
        print("  dashboard  - Launch the graphical monitoring dashboard.")
        print("  help       - Display this menu.")
        print("  quit       - Exit the launcher.")
        print()

    async def handle_command(self, command: str):
        """Handles a user command asynchronously."""
        command_parts = command.lower().strip().split()
        if not command_parts:
            return

        cmd = command_parts[0]

        if cmd == "start":
            # start_learning_process is synchronous (starts a background thread);
            # run it in a thread to avoid awaiting a non-awaitable.
            await asyncio.to_thread(self.integration.start_learning_process)
        elif cmd == "stop":
            await asyncio.to_thread(self.integration.stop_learning)
        elif cmd == "status":
            await self.show_status()
        elif cmd == "learn":
            await asyncio.to_thread(self.integration.perform_learning_session)
        elif cmd == "search":
            query = " ".join(command_parts[1:])
            if not query:
                print("Usage: search <your query>")
                return
            await self.search_content(query)
        elif cmd == "dashboard":
            self.launch_dashboard()
        elif cmd == "help":
            self.show_menu()
        elif cmd in ["quit", "exit"]:
            return "exit"
        else:
            print(f"Unknown command: '{cmd}'. Type 'help' for options.")

    async def show_status(self):
        """Displays the current status of the learning system."""
        # get_learning_status is synchronous; execute in a thread.
        status = await asyncio.to_thread(self.integration.get_learning_status)
        print("\n--- LEARNING STATUS ---")
        for key, value in status.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        print("-----------------------")

    async def search_content(self, query: str):
        """Performs a search and displays the results."""
        print(f"\nSearching for '{query}'...")
        # search_learned_content is synchronous; run in a thread
        results = await asyncio.to_thread(self.integration.search_learned_content, query)
        if not results:
            print("No results found.")
            return

        print(f"\n--- Top {len(results)} Results ---")
        for i, res in enumerate(results, 1):
            print(f"{i}. {res['title']} (Quality: {res['quality']:.2f})")
            print(f"   Topic: {res['topic']} | URL: {res['url']}")
        print("-------------------------")

    def launch_dashboard(self):
        """Launches the GUI dashboard."""
        self.logger.info("Launching dashboard... This will open a new window.")

        # This part is tricky as tkinter needs to run in the main thread.
        # A common approach is to run the dashboard in a separate process
        # or handle the asyncio loop carefully with tkinter.
        # For simplicity, we'll just inform the user.
        print("\nNOTE: The async dashboard should ideally be run as a separate process.")
        print("To run dashboard: python src/learning/celsius_web_learning_dashboard.py")
        # In a real integrated app, you might use multiprocessing.
        # For this launcher, we keep it simple.

    async def run_shell(self):
        """Runs the interactive command shell."""
        self.display_banner()
        self.show_menu()

        while True:
            try:
                command = await asyncio.to_thread(input, "AsyncLearner> ")
                if await self.handle_command(command) == "exit":
                    break
            except (KeyboardInterrupt, EOFError):
                break

        print("\nShutting down...")
        await self.integration.stop_learning()
        print("Goodbye!")


async def main():
    """Main entry point for the async launcher."""
    import argparse

    parser = argparse.ArgumentParser(description="Celsius AI Web Learning Launcher")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode (no interactive shell)")
    parser.add_argument("--interval", type=int, default=3600, help="Learning interval in seconds for daemon mode")
    args = parser.parse_args()

    try:
        # If imports failed earlier, surface the error and keep the process
        # alive (especially important when started from the Hub which spawns
        # a new console window). This makes the error visible instead of
        # causing the window to open briefly and then disappear.
        if critical_import_error:
            err_path = PROJECT_ROOT / "logs" / "web_learning_launcher_error.txt"
            err_path.parent.mkdir(parents=True, exist_ok=True)
            with open(err_path, "w", encoding="utf-8") as f:
                f.write(f"Critical import error: {critical_import_error}\n")
            logging.critical(f"Critical import error detected: {critical_import_error}. Logged to {err_path}")
            print(f"A critical import error occurred. See {err_path} for details.")
            if args.daemon:
                print("Daemon mode: keeping process alive for diagnosis. Press Ctrl-C to exit.")
                try:
                    while True:
                        await asyncio.sleep(60)
                except KeyboardInterrupt:
                    print("Exiting due to user interrupt.")
                    return
            else:
                input("Press Enter to exit...")
                return

        integration = await get_web_learning_integration()

        if args.daemon:
            # Run in daemon mode - continuous learning without interactive shell
            logging.info("Starting Web Learning System in daemon mode...")
            logging.info(f"Learning interval: {args.interval} seconds")

            # Start continuous learning
            # integration.start_learning_process is blocking/synchronous (it starts a background thread)
            # so run it in a thread rather than awaiting directly.
            await asyncio.to_thread(integration.start_learning_process)

            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logging.info("Daemon mode interrupted, shutting down...")
                await asyncio.to_thread(integration.stop_learning)
        else:
            # Run interactive shell mode
            launcher = CelsiusWebLearningLauncher(integration)
            await launcher.run_shell()

    except Exception as e:
        logging.critical(f"Failed to start launcher: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nLauncher interrupted by user.")
