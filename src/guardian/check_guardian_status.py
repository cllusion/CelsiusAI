#!/usr/bin/env python3
"""
Celsius Guardian Status Checker
Quickly check if Guardian is running and view service status
"""

import psutil
import sys
from pathlib import Path
from datetime import datetime


def check_guardian_status():
    """Check if Guardian process is running"""
    print("\n" + "=" * 70)
    print("  CELSIUS AI - GUARDIAN STATUS CHECK")
    print("=" * 70 + "\n")

    base_dir = Path(__file__).parent

    # Check for Guardian processes
    guardian_processes = []
    celsius_processes = []

    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            if proc.info["cmdline"]:
                cmdline = " ".join(proc.info["cmdline"])

                if "celsius_ultimate_guardian" in cmdline or "celsius_lightweight_guardian" in cmdline:
                    guardian_processes.append(proc)
                elif any(x in cmdline for x in ["celsius_", "enhanced_mobile_dashboard", "main.py"]):
                    celsius_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Report Guardian status
    if guardian_processes:
        print("✅ GUARDIAN STATUS: RUNNING")
        print(f"   Found {len(guardian_processes)} Guardian process(es):\n")
        for proc in guardian_processes:
            uptime = datetime.now() - datetime.fromtimestamp(proc.info["create_time"])
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            cmdline = " ".join(proc.info["cmdline"])
            guardian_type = "Ultimate" if "ultimate" in cmdline else "Lightweight"
            print(f"   • PID {proc.info['pid']}: {guardian_type} Guardian")
            print(f"     Uptime: {uptime.days}d {hours}h {minutes}m")
            print()
    else:
        print("❌ GUARDIAN STATUS: NOT RUNNING")
        print("   ⚠️  No Guardian process detected!")
        print("   ⚠️  Services will NOT be automatically restarted if they fail!")
        print()

    # Report Celsius services
    print(f"📊 CELSIUS SERVICES: {len(celsius_processes)} running")
    if celsius_processes:
        print()
        for proc in celsius_processes:
            try:
                cmdline = " ".join(proc.info["cmdline"])
                # Extract service name
                if "enhanced_mobile_dashboard" in cmdline:
                    service_name = "Enhanced Dashboard (Web API)"
                elif "main.py" in cmdline:
                    service_name = "Core AI Engine"
                elif "celsius_web_learning" in cmdline:
                    service_name = "Web Learning System"
                elif "celsius_server_hub" in cmdline:
                    service_name = "Server Hub (GUI)"
                else:
                    service_name = "Unknown Service"

                uptime = datetime.now() - datetime.fromtimestamp(proc.info["create_time"])
                hours = uptime.seconds // 3600
                minutes = (uptime.seconds % 3600) // 60

                print(f"   • {service_name}")
                print(f"     PID: {proc.info['pid']} | Uptime: {uptime.days}d {hours}h {minutes}m")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    else:
        print("   ⚠️  No Celsius services detected!")

    print("\n" + "=" * 70)

    # Check log file
    log_file = base_dir / "logs" / "guardian.log"
    if log_file.exists():
        print(f"\n📋 Last Guardian log entries:")
        print("-" * 70)
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-5:]:
                    print(f"   {line.rstrip()}")
        except Exception as e:
            print(f"   Error reading log: {e}")
        print("-" * 70)

    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if not guardian_processes:
        print("   → Start Guardian: Run 'Start_Guardian_Persistent.bat'")
        print("   → Auto-start: Run 'Install_Guardian_Service.bat' to start at login")
    else:
        print("   ✓ Guardian is actively monitoring services")
        print("   ✓ Failed services will be automatically restarted")

    print("\n" + "=" * 70 + "\n")

    return len(guardian_processes) > 0


if __name__ == "__main__":
    try:
        is_running = check_guardian_status()
        sys.exit(0 if is_running else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(2)
