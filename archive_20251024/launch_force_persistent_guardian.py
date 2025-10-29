#!/usr/bin/env python3
"""
🛡️ Celsius AI - Force Persistent Guardian Launcher
Standalone Guardian that forces all 4 services to be persistent
Including Ultimate Hub, Enhanced Dashboard, Core AI, and Web Learning
"""

import sys
import time
from pathlib import Path


def launch_force_persistent_guardian():
    """Launch Guardian that forces all services to be persistent"""

    print("🛡️ CELSIUS AI - FORCE PERSISTENT LAUNCHER")
    print("=" * 55)
    print("🚀 Starting Guardian that forces all 4 services persistent...")
    print("   1. Ultimate Control Hub")
    print("   2. Enhanced Dashboard")
    print("   3. Celsius AI Core")
    print("   4. Web Learning Engine")
    print()

    # Import and start the Ultimate Guardian
    try:
        from celsius_ultimate_guardian import CelsiusUltimateGuardian

        print("🔄 Initializing Ultimate Guardian...")
        guardian = CelsiusUltimateGuardian()

        print("🛡️ Guardian configured for 4 services:")
        for service_name, config in guardian.process_configs.items():
            print(f"   • {config['name']} ({config['file']})")

        print()
        print("🚀 Starting Force Persistent Mode...")
        print("⚠️  All services will be monitored and auto-restarted")
        print("⚠️  Services will only stop when manually commanded")
        print("⚠️  Guardian will run continuously in background")
        print()
        print("📊 Monitoring interval: 30 seconds")
        print("🔄 Maintenance interval: 6 hours")
        print("🗄️ Database logging: Enabled")
        print()
        print("Press Ctrl+C to stop Guardian (will also stop all managed services)")
        print("=" * 55)

        # Start the Guardian
        guardian.run()

    except KeyboardInterrupt:
        print("\n🛑 Force Persistent Guardian shutdown requested")
    except Exception as e:
        print(f"\n❌ Guardian failed to start: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    launch_force_persistent_guardian()
