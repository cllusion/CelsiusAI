#!/usr/bin/env python3
"""
Check if Celsius Server Hub is Running
Quick status check for the server hub process
"""

import psutil
import os
from datetime import datetime


def check_server_hub_status():
    """Check if the Celsius Server Hub is currently running"""
    print("🔍 CELSIUS SERVER HUB STATUS CHECK")
    print("=" * 45)
    print()

    # Look for server hub processes
    hub_processes = []

    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time", "cpu_percent", "memory_info"]):
        try:
            cmdline = " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else ""

            # Check if this is our server hub
            if "celsius_server_hub.py" in cmdline:
                hub_processes.append(
                    {
                        "pid": proc.info["pid"],
                        "name": proc.info["name"],
                        "cmdline": cmdline,
                        "start_time": datetime.fromtimestamp(proc.info["create_time"]),
                        "cpu_percent": proc.cpu_percent(),
                        "memory_mb": proc.info["memory_info"].rss / 1024 / 1024,
                    }
                )

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if hub_processes:
        print("🟢 SERVER HUB STATUS: RUNNING")
        print()

        for i, proc in enumerate(hub_processes, 1):
            print(f"📋 Process #{i}:")
            print(f"   PID: {proc['pid']}")
            print(f"   Name: {proc['name']}")
            print(f"   Started: {proc['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Uptime: {datetime.now() - proc['start_time']}")
            print(f"   CPU: {proc['cpu_percent']:.1f}%")
            print(f"   Memory: {proc['memory_mb']:.1f} MB")
            print(f"   Command: {proc['cmdline'][:80]}...")
            print()

        print("🎯 SERVER CAPABILITIES:")
        print("   ✅ Self-monitoring active")
        print("   ✅ Health analysis running")
        print("   ✅ Component status tracking")
        print("   ✅ Real-time uptime calculation")
        print("   ✅ Performance metrics collection")
        print("   ✅ Visual status updates in GUI")

    else:
        print("🔴 SERVER HUB STATUS: NOT RUNNING")
        print()
        print("📋 No Celsius Server Hub processes found")
        print()
        print("🚀 To start the server hub:")
        print("   • Run: start_integrated_celsius.bat")
        print("   • Or: .venv\\Scripts\\python.exe celsius_server_hub.py")
        print()
        print("💡 When running, the server hub will:")
        print("   ❌ Monitor its own health and status")
        print("   ❌ Track uptime and performance")
        print("   ❌ Display real-time metrics")
        print("   ❌ Log health data periodically")

    # Check related processes
    related_processes = []
    related_keywords = ["celsius", "enhanced_mobile_dashboard", "ngrok"]

    print()
    print("🔍 RELATED CELSIUS PROCESSES:")

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else ""

            if any(keyword in cmdline.lower() for keyword in related_keywords):
                if "celsius_server_hub.py" not in cmdline:  # Don't duplicate hub processes
                    related_processes.append(
                        {
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "cmdline": cmdline[:60] + "..." if len(cmdline) > 60 else cmdline,
                        }
                    )

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if related_processes:
        for proc in related_processes:
            print(f"   ✅ PID {proc['pid']}: {proc['name']} - {proc['cmdline']}")
    else:
        print("   ⚠️ No related Celsius processes found")

    print()
    print(f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    check_server_hub_status()
