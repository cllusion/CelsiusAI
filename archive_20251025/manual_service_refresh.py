#!/usr/bin/env python3
"""
Manual Service Status Refresh
Manually trigger service status update in the Server Hub
"""

import psutil
from datetime import datetime


def check_celsius_service_status():
    """Check the status of all Celsius services"""
    print("🔄 MANUAL SERVICE STATUS CHECK")
    print("=" * 40)
    print()

    services = {
        "Enhanced Dashboard": "enhanced_mobile_dashboard.py",
        "Hourly Logger": "celsius_hourly_logger.py",
        "Persistent Service": "persistent_celsius_service.py",
        "Server Hub": "celsius_server_hub.py",
    }

    print("📊 SERVICE STATUS:")
    running_services = []

    for service_name, process_name in services.items():
        found = False

        for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
            try:
                cmdline = " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else ""

                if process_name in cmdline:
                    uptime = datetime.now() - datetime.fromtimestamp(proc.info["create_time"])
                    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                    print(f"   ✅ {service_name}: RUNNING (PID {proc.info['pid']}, Uptime: {uptime_str})")
                    running_services.append(service_name)
                    found = True
                    break

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if not found:
            print(f"   ❌ {service_name}: STOPPED")

    print()
    print(f"📈 SUMMARY: {len(running_services)}/{len(services)} services running")

    if len(running_services) == len(services):
        print("💚 ALL SERVICES RUNNING - System fully operational!")
    elif len(running_services) >= len(services) - 1:
        print("💛 MOSTLY OPERATIONAL - One service may need attention")
    else:
        print("❤️ ATTENTION NEEDED - Multiple services stopped")

    # Check additional processes
    print()
    print("🔍 ADDITIONAL CELSIUS PROCESSES:")
    additional_found = 0

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else ""

            if ("celsius" in cmdline.lower() or "ngrok" in cmdline.lower()) and not any(
                service in cmdline for service in services.values()
            ):
                print(f"   🔧 PID {proc.info['pid']}: {proc.info['name']} - {cmdline[:60]}...")
                additional_found += 1

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if additional_found == 0:
        print("   ℹ️ No additional Celsius processes found")

    print()
    print(f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("💡 TIP: The Server Hub should auto-refresh service status every 5 seconds")


if __name__ == "__main__":
    check_celsius_service_status()
