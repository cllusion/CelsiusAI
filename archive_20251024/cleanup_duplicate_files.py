#!/usr/bin/env python3
"""
Celsius AI Duplicate File Cleanup Utility

This script safely removes duplicate launcher and persistent files that have been
consolidated into the unified launcher system. Only removes files after confirming
the unified launcher works properly.

Created: December 2024
Purpose: Clean up duplicate functionality files
"""

import os
import shutil
import datetime
from pathlib import Path


class CelsiusCleanup:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.backup_dir = self.base_dir / "backup_cleanup"
        self.removed_files = []

        # Files to remove (made obsolete by unified launcher)
        self.files_to_remove = [
            "celsius_taskbar_launcher.py",
            "celsius_defense_activator.py",
            "start_celsius.bat",
            "start_enhanced_celsius.bat",
            "start_integrated_celsius.bat",
            "start_persistent.bat",
            "start_public_celsius.bat",
            "Activate_Defense_System.bat",
            "Setup_Taskbar_Shortcuts.bat",
        ]

        # Files to keep (core functionality)
        self.files_to_keep = [
            "celsius_unified_launcher.py",
            "celsius_server_hub.py",
            "celsius_defense_manager.py",
            "Start_Server_Hub.bat",
            "service_manager.bat",
            "Server_Control.bat",
        ]

    def create_backup_directory(self):
        """Create backup directory with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.base_dir / f"backup_cleanup_{timestamp}"
        self.backup_dir.mkdir(exist_ok=True)
        print(f"[OK] Created backup directory: {self.backup_dir}")

    def backup_file(self, file_path):
        """Backup a file before removal"""
        try:
            if file_path.exists():
                backup_path = self.backup_dir / file_path.name
                shutil.copy2(file_path, backup_path)
                print(f"  📦 Backed up: {file_path.name}")
                return True
        except Exception as e:
            print(f"  [ERROR] Backup failed for {file_path.name}: {e}")
            return False
        return False

    def remove_file(self, file_path):
        """Safely remove a file"""
        try:
            if file_path.exists():
                if self.backup_file(file_path):
                    file_path.unlink()
                    self.removed_files.append(file_path.name)
                    print(f"  🗑️  Removed: {file_path.name}")
                    return True
        except Exception as e:
            print(f"  [ERROR] Removal failed for {file_path.name}: {e}")
            return False
        return False

    def verify_unified_launcher(self):
        """Verify unified launcher exists and can be imported"""
        unified_launcher = self.base_dir / "celsius_unified_launcher.py"
        if not unified_launcher.exists():
            print("[ERROR] Unified launcher not found! Cleanup aborted.")
            return False

        try:
            # Test import
            import subprocess

            result = subprocess.run(
                ["python", "-c", "import celsius_unified_launcher; print('OK')"],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and "OK" in result.stdout:
                print("[OK] Unified launcher verified working")
                return True
            else:
                print(f"[ERROR] Unified launcher test failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"[ERROR] Unified launcher verification error: {e}")
            return False

    def show_cleanup_plan(self):
        """Show what files will be removed"""
        print("\n🧹 CLEANUP PLAN")
        print("=" * 50)

        print("\n[FOLDER] Files to be removed:")
        for filename in self.files_to_remove:
            file_path = self.base_dir / filename
            status = "[OK] EXISTS" if file_path.exists() else "[ERROR] NOT FOUND"
            print(f"  - {filename:<35} {status}")

        print("\n[FOLDER] Files to be kept (core functionality):")
        for filename in self.files_to_keep:
            file_path = self.base_dir / filename
            status = "[OK] EXISTS" if file_path.exists() else "[ERROR] MISSING"
            print(f"  - {filename:<35} {status}")

    def run_cleanup(self):
        """Execute the cleanup process"""
        print("[START] CELSIUS AI DUPLICATE FILE CLEANUP")
        print("=" * 50)

        # Verify unified launcher works
        if not self.verify_unified_launcher():
            return False

        # Show cleanup plan
        self.show_cleanup_plan()

        # Confirm with user
        print(f"\n[WARNING]  This will remove {len(self.files_to_remove)} duplicate files.")
        print(f"📦 Backups will be saved to: {self.backup_dir.name}")

        response = input("\nProceed with cleanup? (y/N): ").strip().lower()
        if response != "y":
            print("[ERROR] Cleanup cancelled by user")
            return False

        # Create backup directory
        self.create_backup_directory()

        # Remove files
        print(f"\n🧹 Starting cleanup...")
        success_count = 0

        for filename in self.files_to_remove:
            file_path = self.base_dir / filename
            if self.remove_file(file_path):
                success_count += 1

        # Cleanup report
        print(f"\n[STATUS] CLEANUP COMPLETE")
        print("=" * 50)
        print(f"[OK] Files successfully removed: {success_count}")
        print(f"📦 Backup location: {self.backup_dir}")
        print(f"[TARGET] Unified launcher: celsius_unified_launcher.py")

        if self.removed_files:
            print(f"\n🗑️  Removed files:")
            for filename in self.removed_files:
                print(f"  - {filename}")

        print(f"\n[TIP] To restore files, copy from backup directory:")
        print(f"   {self.backup_dir}")

        return True


def main():
    """Main cleanup function"""
    cleanup = CelsiusCleanup()
    cleanup.run_cleanup()


if __name__ == "__main__":
    main()
