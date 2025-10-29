#!/usr/bin/env python3
"""
🛡️ CELSIUS AI - SERVER HUB REDIRECT 🛡️
═══════════════════════════════════════════════════════════════════════════════════════════

This file now redirects to the Ultimate Hub for a unified experience.
The new celsius_ultimate_hub.py combines all server hub functionality.

═══════════════════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """Redirect to Ultimate Hub"""
    print("🛡️ Celsius AI Server Hub")
    print("=" * 40)
    print("🔄 Redirecting to Ultimate Hub...")
    print("📍 Loading celsius_ultimate_hub.py...")

    ultimate_hub = Path("celsius_ultimate_hub.py")

    if ultimate_hub.exists():
        try:
            # Import and run the ultimate hub
            import celsius_ultimate_hub

            celsius_ultimate_hub.main()
        except ImportError:
            # Fallback to subprocess if import fails
            subprocess.run([sys.executable, "celsius_ultimate_hub.py"])
    else:
        print("❌ Ultimate hub not found. Please ensure celsius_ultimate_hub.py exists.")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
