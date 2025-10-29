#!/usr/bin/env python3
"""
🧠 Celsius Learning System Launcher
====================================
Autonomous monitoring and learning system for Celsius AI.

This system continuously monitors all Celsius processes, analyzes patterns,
and suggests improvements. It runs independently and requires NO APPROVAL
for learning - only for implementing code changes.

Features:
- Continuous process monitoring (every 30 seconds)
- Performance metrics collection (CPU, memory, disk, network)
- Pattern analysis and anomaly detection
- Improvement suggestions with detailed analysis
- Integration with Code Approval System for implementation

Usage:
    python celsius_learning_launcher.py [--daemon] [--interval SECONDS]

Options:
    --daemon        Run in background as daemon process
    --interval      Monitoring interval in seconds (default: 30)
    --verbose       Enable verbose logging
    --help          Show this help message
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path
import signal

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.core.celsius_learning_system import CelsiusLearningSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(PROJECT_ROOT / "logs" / "celsius_learning.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Global learning system instance
learning_system = None
running = True


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global running
    logger.info("Shutdown signal received. Stopping learning system...")
    running = False


async def run_learning_system(interval: int = 30, verbose: bool = False):
    """
    Run the learning system continuously.

    Args:
        interval: Monitoring interval in seconds
        verbose: Enable verbose logging
    """
    global learning_system, running

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("🧠 Celsius Learning System Starting...")
    logger.info(f"📊 Monitoring interval: {interval} seconds")
    logger.info(f"🎯 Monitored processes: Defender, Guardian, Hub, Dashboard, Core AI, Web Learning, Hourly Reporter")
    logger.info(f"💾 Database: {PROJECT_ROOT / 'celsius_learning.db'}")
    logger.info(f"⚡ Autonomous learning enabled - NO APPROVAL NEEDED")
    logger.info(f"📝 Code changes require approval through Ultimate Hub")

    # Initialize learning system
    learning_system = CelsiusLearningSystem()
    await learning_system.initialize()

    logger.info("Learning System initialized successfully")
    logger.info("🔄 Starting continuous monitoring...")

    # Set custom monitoring interval
    learning_system.monitor_interval = interval

    try:
        # Start monitoring in background
        monitor_task = asyncio.create_task(learning_system.monitor_processes())

        # Keep running until shutdown signal
        while running:
            await asyncio.sleep(1)

        # Cancel monitoring task
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        logger.info("🛑 Learning System stopped gracefully")

    except Exception as e:
        logger.error(f"❌ Error in learning system: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        if learning_system:
            logger.info("Cleaning up resources...")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Celsius AI - Autonomous Learning System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (30 second interval)
  python celsius_learning_launcher.py
  
  # Run with custom interval
  python celsius_learning_launcher.py --interval 60
  
  # Run in verbose mode
  python celsius_learning_launcher.py --verbose
  
  # Run as daemon (background process)
  python celsius_learning_launcher.py --daemon
  
Press Ctrl+C to stop the learning system.
        """,
    )

    parser.add_argument("--daemon", action="store_true", help="Run in background as daemon process")

    parser.add_argument("--interval", type=int, default=30, help="Monitoring interval in seconds (default: 30)")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Validate interval
    if args.interval < 5:
        logger.error("Interval must be at least 5 seconds")
        sys.exit(1)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Print banner
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║       🧠 CELSIUS AI - AUTONOMOUS LEARNING SYSTEM 🧠         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"📊 Monitoring Interval: {args.interval} seconds")
    print(f"🎯 Mode: {'Daemon (Background)' if args.daemon else 'Foreground'}")
    print(f"📝 Logging: {'Verbose' if args.verbose else 'Normal'}")
    print()
    print("🔄 Learning System will:")
    print("   • Monitor all Celsius processes continuously")
    print("   • Collect performance metrics (CPU, memory, disk, network)")
    print("   • Analyze patterns and detect anomalies")
    print("   • Suggest improvements automatically")
    print("   • Submit code changes to Code Approval System")
    print()
    print("⚠️  NOTE: Learning is AUTONOMOUS (no approval needed)")
    print("Code changes REQUIRE approval via Ultimate Hub")
    print()
    print("Press Ctrl+C to stop...")
    print()

    # Run the learning system
    try:
        asyncio.run(run_learning_system(interval=args.interval, verbose=args.verbose))
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    logger.info("👋 Learning System shutdown complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
