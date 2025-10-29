#!/usr/bin/env python3
"""
Celsius AI System Integration Status Report

This script provides a comprehensive status of the unified launcher system,
single instance control, and file consolidation efforts.

Created: December 2024
Purpose: System status verification and reporting
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path


class CelsiusStatusReport:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.report_data = {}

    def check_unified_launcher(self):
        """Check unified launcher status"""
        launcher_path = self.base_dir / "celsius_unified_launcher.py"

        status = {
            "exists": launcher_path.exists(),
            "size": launcher_path.stat().st_size if launcher_path.exists() else 0,
            "importable": False,
            "features": [],
        }

        if status["exists"]:
            try:
                # Test import
                result = subprocess.run(
                    [
                        "python",
                        "-c",
                        "import celsius_unified_launcher; "
                        "launcher = celsius_unified_launcher.CelsiusUnifiedLauncher(); "
                        "print('IMPORT_OK')",
                    ],
                    cwd=self.base_dir,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                status["importable"] = result.returncode == 0 and "IMPORT_OK" in result.stdout

                # Check for key features by reading file
                with open(launcher_path, "r") as f:
                    content = f.read()

                if "pystray" in content:
                    status["features"].append("System Tray Integration")
                if "SingleInstanceLock" in content:
                    status["features"].append("Single Instance Control")
                if "tkinter" in content:
                    status["features"].append("GUI Interface")
                if "subprocess" in content:
                    status["features"].append("Process Management")
                if "monitor_status" in content:
                    status["features"].append("Status Monitoring")

            except Exception as e:
                status["error"] = str(e)

        self.report_data["unified_launcher"] = status

    def check_single_instance_control(self):
        """Check single instance control implementation"""
        server_hub_path = self.base_dir / "celsius_server_hub.py"

        status = {
            "server_hub_exists": server_hub_path.exists(),
            "has_lock_class": False,
            "lock_file_path": str(self.base_dir / "celsius_server_hub.lock"),
            "lock_file_exists": False,
        }

        if status["server_hub_exists"]:
            try:
                with open(server_hub_path, "r") as f:
                    content = f.read()
                    status["has_lock_class"] = "class SingleInstanceLock" in content
            except Exception as e:
                status["error"] = str(e)

        # Check for existing lock file
        lock_file = Path(status["lock_file_path"])
        status["lock_file_exists"] = lock_file.exists()

        if status["lock_file_exists"]:
            try:
                with open(lock_file, "r") as f:
                    pid = f.read().strip()
                    status["current_pid"] = pid

                    # Check if process is running
                    try:
                        import psutil

                        if psutil.pid_exists(int(pid)):
                            status["process_running"] = True
                        else:
                            status["process_running"] = False
                    except:
                        status["process_running"] = "unknown"
            except Exception as e:
                status["lock_error"] = str(e)

        self.report_data["single_instance"] = status

    def check_file_consolidation(self):
        """Check file consolidation status"""

        # Files that should exist (unified system)
        core_files = [
            "celsius_unified_launcher.py",
            "celsius_server_hub.py",
            "celsius_defense_manager.py",
            "Start_Server_Hub.bat",
        ]

        # Files that are duplicates/obsolete
        obsolete_files = [
            "celsius_taskbar_launcher.py",
            "celsius_defense_activator.py",
            "start_celsius.bat",
            "start_enhanced_celsius.bat",
            "start_integrated_celsius.bat",
            "start_persistent.bat",
            "Activate_Defense_System.bat",
        ]

        status = {"core_files": {}, "obsolete_files": {}, "consolidation_complete": False}

        # Check core files
        for filename in core_files:
            file_path = self.base_dir / filename
            status["core_files"][filename] = {
                "exists": file_path.exists(),
                "size": file_path.stat().st_size if file_path.exists() else 0,
            }

        # Check obsolete files
        obsolete_count = 0
        for filename in obsolete_files:
            file_path = self.base_dir / filename
            exists = file_path.exists()
            status["obsolete_files"][filename] = {"exists": exists, "should_remove": exists}
            if exists:
                obsolete_count += 1

        # Consolidation is complete if all core files exist and no obsolete files exist
        core_complete = all(status["core_files"][f]["exists"] for f in core_files)
        status["consolidation_complete"] = core_complete and obsolete_count == 0
        status["obsolete_count"] = obsolete_count

        self.report_data["file_consolidation"] = status

    def check_dependencies(self):
        """Check required dependencies"""
        required_packages = ["tkinter", "psutil", "PIL", "pystray", "threading", "subprocess", "pathlib"]

        status = {"packages": {}}

        for package in required_packages:
            try:
                if package == "tkinter":
                    import tkinter

                    status["packages"][package] = "[OK] Available"
                elif package == "psutil":
                    import psutil

                    status["packages"][package] = f"[OK] Available (v{psutil.__version__})"
                elif package == "PIL":
                    from PIL import Image

                    status["packages"][package] = "[OK] Available"
                elif package == "pystray":
                    import pystray

                    status["packages"][package] = "[OK] Available"
                else:
                    exec(f"import {package}")
                    status["packages"][package] = "[OK] Available"
            except ImportError:
                status["packages"][package] = "[ERROR] Missing"
            except Exception as e:
                status["packages"][package] = f"[WARNING]  Error: {e}"

        self.report_data["dependencies"] = status

    def generate_report(self):
        """Generate comprehensive status report"""
        print("[TARGET] CELSIUS AI SYSTEM INTEGRATION STATUS REPORT")
        print("=" * 60)
        print(f"📅 Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[FOLDER] Base Directory: {self.base_dir}")
        print()

        # Unified Launcher Status
        print("[START] UNIFIED LAUNCHER STATUS")
        print("-" * 30)
        launcher = self.report_data["unified_launcher"]
        print(f"File Exists: {'[OK] Yes' if launcher['exists'] else '[ERROR] No'}")
        print(f"File Size: {launcher['size']:,} bytes")
        print(f"Importable: {'[OK] Yes' if launcher['importable'] else '[ERROR] No'}")

        if launcher.get("features"):
            print("Features Detected:")
            for feature in launcher["features"]:
                print(f"  [OK] {feature}")

        if launcher.get("error"):
            print(f"[WARNING]  Error: {launcher['error']}")
        print()

        # Single Instance Control
        print("[LOCKED] SINGLE INSTANCE CONTROL")
        print("-" * 30)
        instance = self.report_data["single_instance"]
        print(f"Server Hub Exists: {'[OK] Yes' if instance['server_hub_exists'] else '[ERROR] No'}")
        print(f"Lock Class Implemented: {'[OK] Yes' if instance['has_lock_class'] else '[ERROR] No'}")
        print(f"Lock File Path: {instance['lock_file_path']}")
        print(f"Lock File Exists: {'[OK] Yes' if instance['lock_file_exists'] else '[ERROR] No'}")

        if instance.get("current_pid"):
            print(f"Current PID: {instance['current_pid']}")
            print(f"Process Running: {'[OK] Yes' if instance['process_running'] else '[ERROR] No'}")
        print()

        # File Consolidation Status
        print("[FOLDER] FILE CONSOLIDATION STATUS")
        print("-" * 30)
        consolidation = self.report_data["file_consolidation"]
        print(
            f"Consolidation Complete: {'[OK] Yes' if consolidation['consolidation_complete'] else '[WARNING]  In Progress'}"
        )
        print(f"Obsolete Files Remaining: {consolidation['obsolete_count']}")

        print("\nCore Files:")
        for filename, info in consolidation["core_files"].items():
            status = "[OK] Present" if info["exists"] else "[ERROR] Missing"
            size = f"({info['size']:,} bytes)" if info["exists"] else ""
            print(f"  {filename:<35} {status} {size}")

        if consolidation["obsolete_count"] > 0:
            print("\nObsolete Files (Should be removed):")
            for filename, info in consolidation["obsolete_files"].items():
                if info["exists"]:
                    print(f"  {filename:<35} [WARNING]  Still exists")
        print()

        # Dependencies
        print("📦 DEPENDENCY STATUS")
        print("-" * 30)
        deps = self.report_data["dependencies"]
        for package, status in deps["packages"].items():
            print(f"  {package:<15} {status}")
        print()

        # Recommendations
        print("[TIP] RECOMMENDATIONS")
        print("-" * 30)

        if not launcher["exists"]:
            print("❗ Create unified launcher file")
        elif not launcher["importable"]:
            print("❗ Fix unified launcher import errors")

        if not instance["has_lock_class"]:
            print("❗ Implement SingleInstanceLock in server hub")

        if consolidation["obsolete_count"] > 0:
            print("❗ Run cleanup script to remove obsolete files:")
            print("   python cleanup_duplicate_files.py")

        missing_deps = [pkg for pkg, status in deps["packages"].items() if "[ERROR]" in status]
        if missing_deps:
            print("❗ Install missing dependencies:")
            for dep in missing_deps:
                if dep == "pystray":
                    print(f"   pip install {dep}")
                elif dep == "PIL":
                    print(f"   pip install Pillow")

        if consolidation["consolidation_complete"] and launcher["importable"]:
            print("[OK] System ready! Use: python celsius_unified_launcher.py")

        print()

    def run_report(self):
        """Run complete system status check"""
        print("Checking unified launcher...")
        self.check_unified_launcher()

        print("Checking single instance control...")
        self.check_single_instance_control()

        print("Checking file consolidation...")
        self.check_file_consolidation()

        print("Checking dependencies...")
        self.check_dependencies()

        print("\nGenerating report...\n")
        self.generate_report()


def main():
    """Main status report function"""
    reporter = CelsiusStatusReport()
    reporter.run_report()


if __name__ == "__main__":
    main()
