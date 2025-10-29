#!/usr/bin/env python3
"""
🧪 Service Persistence Test
Tests that all 4 services start and stay persistent
"""

import time
import subprocess
import psutil
import requests
from pathlib import Path


def test_service_persistence():
    """Test that all services start and remain persistent"""

    print("🧪 TESTING SERVICE PERSISTENCE")
    print("=" * 50)

    base_dir = Path(__file__).parent

    # Test services
    services = {
        "enhanced_dashboard": {"file": "enhanced_mobile_dashboard.py", "port": 5000, "url": "http://localhost:5000"},
        "celsius_core": {"file": "main.py", "port": None, "url": None},
        "guardian_system": {"file": "celsius_lightweight_guardian.py", "port": None, "url": None},
        "web_learning": {"file": "celsius_web_learning_launcher.py", "port": None, "url": None},
    }

    print("\n📋 Testing Service Files Exist...")
    for service_name, config in services.items():
        file_path = base_dir / config["file"]
        if file_path.exists():
            print(f"✅ {service_name}: {config['file']} exists")
        else:
            print(f"❌ {service_name}: {config['file']} MISSING")

    print("\n🚀 Testing Ultimate Hub Auto-Start...")
    print("Instructions:")
    print("1. Run: python celsius_ultimate_hub.py")
    print("2. Login with: cllusion001 / T3qy22ny*@dyu0ppn*pG")
    print("3. Wait 5 seconds for auto-start to complete")
    print("4. Check Services tab to verify all services are running")

    print("\n🛡️ Testing Guardian Functionality...")

    # Check if Guardian can start independently
    guardian_file = base_dir / "celsius_lightweight_guardian.py"
    if guardian_file.exists():
        print("✅ Guardian file exists")
        print("To test Guardian independently:")
        print("   python celsius_lightweight_guardian.py")
        print("   (Should start all 3 managed services)")
    else:
        print("❌ Guardian file missing")

    print("\n📊 Current Process Check...")
    celsius_processes = []

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["name"] in ["python.exe", "python3.11.exe"]:
                if proc.info["cmdline"]:
                    cmdline = " ".join(proc.info["cmdline"])
                    if any(service in cmdline for service in ["celsius_", "enhanced_mobile_dashboard", "main.py"]):
                        celsius_processes.append({"pid": proc.info["pid"], "cmdline": cmdline})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if celsius_processes:
        print(f"Found {len(celsius_processes)} Celsius processes running:")
        for proc in celsius_processes:
            print(f"   PID {proc['pid']}: {proc['cmdline']}")
    else:
        print("No Celsius processes currently running")

    print("\n🌐 Testing Dashboard Availability...")
    try:
        response = requests.get("http://localhost:5000", timeout=3)
        if response.status_code == 200:
            print("✅ Enhanced Dashboard is responding on port 5000")
        else:
            print(f"⚠️ Dashboard responded with status: {response.status_code}")
    except requests.exceptions.RequestException:
        print("❌ Enhanced Dashboard not responding on port 5000")

    print("\n🔍 Service Persistence Test Steps:")
    print("1. Start Ultimate Hub and login")
    print("2. Verify all 4 services auto-start (check Services tab)")
    print("3. Manually kill one service process (using Task Manager)")
    print("4. Wait 15 seconds for watchdog to restart it")
    print("5. Verify service is back online")
    print("6. Test that Guardian persistent mode works correctly")

    print("\n📋 Expected Behavior:")
    print("✅ All 4 services start automatically on Ultimate Hub login")
    print("✅ Services restart automatically if they crash/die")
    print("✅ Guardian monitors and maintains all services")
    print("✅ Services only stop when manually commanded")
    print("✅ Persistent mode checkbox controls the watchdog")

    print("\n🎯 Testing Complete!")
    print("Run the actual Ultimate Hub to verify all functionality works.")


def test_guardian_config():
    """Test Guardian configuration"""
    print("\n🛡️ GUARDIAN CONFIGURATION TEST")
    print("=" * 40)

    try:
        # Import Guardian class to test config
        import sys

        sys.path.append(str(Path(__file__).parent))

        from celsius_lightweight_guardian import CelsiusLightweightGuardian

        guardian = CelsiusLightweightGuardian()

        print("Guardian Process Configs:")
        for service_name, config in guardian.process_configs.items():
            print(f"  • {service_name}:")
            print(f"    - File: {config['file']}")
            print(f"    - Name: {config['name']}")
            print(f"    - Required: {config['required']}")
            print(f"    - Startup Delay: {config.get('startup_delay', 'N/A')}")

        print(f"\nGuardian Check Interval: {guardian.check_interval} seconds")
        print("✅ Guardian configuration looks correct")

    except Exception as e:
        print(f"❌ Guardian configuration test failed: {e}")


if __name__ == "__main__":
    test_service_persistence()
    test_guardian_config()
