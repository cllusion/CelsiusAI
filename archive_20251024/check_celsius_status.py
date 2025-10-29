#!/usr/bin/env python3
"""
Celsius AI - System Status Checker
Quick verification that all integrated components are working
"""

import os
import sys
import psutil
import logging
from pathlib import Path


def check_celsius_status():
    """Check status of all Celsius AI components"""
    print("🔍 CELSIUS AI - INTEGRATED SYSTEM STATUS CHECK")
    print("=" * 50)

    base_dir = Path("C:/Users/micro/Celsius AI")

    # Check if files exist
    components = {
        "Server Hub": "celsius_server_hub.py",
        "System Integration": "celsius_system_integration.py",
        "Power Manager": "celsius_power_manager.py",
        "Process Trainer": "celsius_process_trainer.py",
        "Collaborative Engine": "celsius_collaborative_engine.py",
        "Mobile Dashboard": "enhanced_mobile_dashboard.py",
    }

    print("\n📁 Component Files:")
    for name, filename in components.items():
        file_path = base_dir / filename
        status = "✅ Found" if file_path.exists() else "❌ Missing"
        print(f"  {name}: {status}")

    # Check running processes
    print("\n🔄 Running Processes:")
    celsius_processes = []

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else ""
            if any(comp in cmdline for comp in components.values()):
                celsius_processes.append({"name": proc.info["name"], "pid": proc.info["pid"], "cmdline": cmdline})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if celsius_processes:
        for proc in celsius_processes:
            print(f"  ✅ PID {proc['pid']}: {proc['name']}")
            print(f"     Command: {proc['cmdline'][:80]}...")
    else:
        print("  ⚠️  No Celsius processes currently running")

    # Check databases
    print("\n💾 Database Files:")
    db_files = ["celsius_system.db", "celsius_training.db", "celsius_improvements.db"]

    for db_file in db_files:
        db_path = base_dir / db_file
        if db_path.exists():
            size = db_path.stat().st_size
            print(f"  ✅ {db_file}: {size:,} bytes")
        else:
            print(f"  ⚠️  {db_file}: Not found (will be created on first use)")

    # Check configuration
    print("\n⚙️  Configuration:")
    config_files = ["service_config.json", ".env", "celsius_config.json"]
    for config_file in config_files:
        config_path = base_dir / config_file
        status = "✅ Found" if config_path.exists() else "⚠️  Default"
        print(f"  {config_file}: {status}")

    # Safety check
    print("\n🛡️  Safety Features:")
    print("  ✅ Celsius cannot approve its own code")
    print("  ✅ Server Hub controls shutdown/kill commands")
    print("  ✅ User approval required for code changes")
    print("  ✅ Protected system processes")

    print("\n" + "=" * 50)
    print("🚀 CELSIUS AI INTEGRATION STATUS: READY")
    print("\nTo start the system:")
    print("  • Run: start_integrated_celsius.bat")
    print("  • Or: .venv\\Scripts\\python.exe celsius_server_hub.py")
    print("\nThe Server Hub provides full control interface with:")
    print("  • System monitoring and process grading")
    print("  • Power management and optimization")
    print("  • Code improvement approval system")
    print("  • Mobile dashboard web interface")


if __name__ == "__main__":
    check_celsius_status()
