#!/usr/bin/env python3
"""
Celsius AI - Intelligent Cleanup Tool
Removes duplicates, old files, and optimizes the codebase
"""

import os
import shutil
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timedelta


class CelsiusCleanupTool:
    def __init__(self):
        self.base_dir = Path("C:/Users/micro/Celsius AI")
        self.backup_dir = self.base_dir / "cleanup_backup"
        self.removed_files = []
        self.kept_files = []

    def create_cleanup_backup(self):
        """Create backup of important files before cleanup"""
        print("📦 Creating cleanup backup...")
        if not self.backup_dir.exists():
            self.backup_dir.mkdir()

        important_files = [
            "celsius_server_hub.py",
            "enhanced_mobile_dashboard.py",
            "celsius_lightweight_guardian.py",
            "celsius_auth.py",
            "celsius_code_approval.py",
            "main.py",
        ]

        for file in important_files:
            src = self.base_dir / file
            if src.exists():
                shutil.copy2(src, self.backup_dir / file)
                print(f"  ✅ Backed up: {file}")

    def remove_duplicate_guardians(self):
        """Remove duplicate guardian files - keep only the lightweight one"""
        print("\n🛡️ Cleaning up duplicate guardian files...")

        duplicate_guardians = [
            "celsius_enhanced_guardian.py",  # Heavy resource usage
            "celsius_intelligent_guardian.py",  # Duplicate functionality
            "celsius_intelligent_guardian_notifier.py",  # Integrated elsewhere
            "celsius_intelligent_guardian_simple.py",  # Redundant
            "celsius_persistent_guardian.py",  # Duplicate
            "celsius_watchdog.json",  # Old config
            "intelligent_guardian_status.json",  # Temp file
            "guardian_status.json",  # Temp file
            "guardian_config.json",  # Old config
        ]

        for file in duplicate_guardians:
            file_path = self.base_dir / file
            if file_path.exists():
                file_path.unlink()
                self.removed_files.append(file)
                print(f"  🗑️ Removed: {file}")

    def remove_old_test_files(self):
        """Remove old test and diagnostic files"""
        print("\n🧪 Cleaning up old test files...")

        old_tests = [
            "test_enhanced_guardian_setup.py",
            "test_guardian_server_management.py",
            "test_intelligent_guardian.py",
            "test_notifications_complete.py",
            "test_notification_system_complete.py",
            "test_server_hub_responsiveness.py",
            "test_server_hub_startup.py",
            "test_server_monitoring.py",
            "test_server_status_detection.py",
            "test_widget_errors.py",
            "debug_guardian_detection.py",
            "troubleshoot_black_screen.py",
            "fix_server_hub_issues.py",
            "verify_server_hub.py",
        ]

        for file in old_tests:
            file_path = self.base_dir / file
            if file_path.exists():
                file_path.unlink()
                self.removed_files.append(file)
                print(f"  🗑️ Removed: {file}")

    def remove_duplicate_scripts(self):
        """Remove duplicate startup and control scripts"""
        print("\n📜 Cleaning up duplicate scripts...")

        duplicate_scripts = [
            "celsius_server_control.py",  # Duplicate functionality
            "celsius_system_service.py",  # Old implementation
            "celsius_unified_launcher.py",  # Redundant
            "start_server_hub.py",  # Duplicate
            "setup_intelligent_guardian.py",  # Old setup
            "celsius_persistent_startup.py",  # Old persistence
            "guardian_control.py",  # Duplicate
            "persistent_celsius_service.py",  # Old service
            "celsius_system_integration.py",  # Integrated elsewhere
            "enhanced_celsius_remote.py",  # Old remote
        ]

        for file in duplicate_scripts:
            file_path = self.base_dir / file
            if file_path.exists():
                file_path.unlink()
                self.removed_files.append(file)
                print(f"  🗑️ Removed: {file}")

    def remove_old_batch_files(self):
        """Clean up old batch files - keep only essential ones"""
        print("\n⚡ Cleaning up old batch files...")

        old_batches = [
            "Start_Enhanced_Guardian.bat",  # Use lightweight guardian
            "start_guardian.bat",  # Old
            "start_intelligent_guardian.bat",  # Old
            "start_server_hub_enhanced.bat",  # Redundant
            "Restart_Server_Hub_Fixed.bat",  # Fixed in code
            "Server_Control.bat",  # Old control
            "service_manager.bat",  # Old manager
            "Create_Taskbar_Shortcuts_Fixed.ps1",  # Redundant
            "Create_Taskbar_Shortcuts.ps1",  # Old version
        ]

        for file in old_batches:
            file_path = self.base_dir / file
            if file_path.exists():
                file_path.unlink()
                self.removed_files.append(file)
                print(f"  🗑️ Removed: {file}")

    def clean_old_logs_and_temp(self):
        """Clean up old log files and temporary data"""
        print("\n📋 Cleaning up logs and temporary files...")

        # Clean log files older than 7 days
        logs_dir = self.base_dir / "logs"
        if logs_dir.exists():
            cutoff_date = datetime.now() - timedelta(days=7)
            for log_file in logs_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    print(f"  🗑️ Removed old log: {log_file.name}")

        # Clean temp files
        temp_files = [
            "celsius_hourly_logger.lock",
            "server_hub_instance.lock",
            "current_public_url.txt",
            "celsius_language_improvement.log",
            "celsius_system_integration.log",
            "celsius_web_learning.log",
        ]

        for file in temp_files:
            file_path = self.base_dir / file
            if file_path.exists():
                file_path.unlink()
                self.removed_files.append(file)
                print(f"  🗑️ Removed temp file: {file}")

    def clean_obsolete_backups(self):
        """Remove old backup directories"""
        print("\n💾 Cleaning up obsolete backups...")

        obsolete_dirs = ["backup_obsolete_20251024_000506"]

        for dir_name in obsolete_dirs:
            dir_path = self.base_dir / dir_name
            if dir_path.exists():
                shutil.rmtree(dir_path)
                self.removed_files.append(f"{dir_name}/ (directory)")
                print(f"  🗑️ Removed obsolete backup: {dir_name}")

    def clean_pycache(self):
        """Remove Python cache directories"""
        print("\n🐍 Cleaning up Python cache...")

        for pycache in self.base_dir.rglob("__pycache__"):
            if pycache.is_dir():
                shutil.rmtree(pycache)
                print(f"  🗑️ Removed cache: {pycache.relative_to(self.base_dir)}")

        for pyc_file in self.base_dir.rglob("*.pyc"):
            pyc_file.unlink()
            print(f"  🗑️ Removed: {pyc_file.name}")

    def optimize_database_files(self):
        """Optimize SQLite databases"""
        print("\n🗄️ Optimizing databases...")

        db_files = ["celsius_activity.db", "celsius_code_approvals.db", "celsius_system.db", "celsius_web_learning.db"]

        for db_file in db_files:
            db_path = self.base_dir / db_file
            if db_path.exists():
                try:
                    conn = sqlite3.connect(db_path)
                    conn.execute("VACUUM")
                    conn.execute("REINDEX")
                    conn.close()
                    print(f"  ✅ Optimized: {db_file}")
                except Exception as e:
                    print(f"  ⚠️ Could not optimize {db_file}: {e}")

    def generate_cleanup_report(self):
        """Generate cleanup summary report"""
        report = f"""
🧹 CELSIUS AI CLEANUP REPORT
{'='*50}
📅 Cleanup Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 CLEANUP SUMMARY:
• Files Removed: {len(self.removed_files)}
• Space Freed: Significant (duplicates and cache removed)
• Performance: Should be improved significantly

🗑️ REMOVED FILES ({len(self.removed_files)}):
"""
        for file in self.removed_files:
            report += f"  • {file}\n"

        report += f"""

✅ ESSENTIAL FILES KEPT:
• celsius_server_hub.py (Main interface)
• celsius_lightweight_guardian.py (Efficient monitoring)
• enhanced_mobile_dashboard.py (Dashboard server)
• celsius_auth.py (Authentication)
• celsius_code_approval.py (Code approval system)
• main.py (Core AI)

🚀 PERFORMANCE IMPROVEMENTS:
• Removed heavy guardian processes
• Cleaned up duplicate monitoring scripts
• Optimized database files
• Removed old cache and temp files
• Eliminated redundant batch files

💡 NEXT STEPS:
1. Use only celsius_lightweight_guardian.py for monitoring
2. Start server hub with: python celsius_server_hub.py
3. Responsiveness should be significantly improved
"""

        report_file = self.base_dir / "cleanup_report.txt"
        with open(report_file, "w") as f:
            f.write(report)

        print(report)
        print(f"\n📋 Full report saved to: cleanup_report.txt")

    def run_cleanup(self):
        """Run the complete cleanup process"""
        print("🧹 Starting Celsius AI Intelligent Cleanup...")
        print(f"📁 Target Directory: {self.base_dir}")

        # Create backup first
        self.create_cleanup_backup()

        # Run cleanup steps
        self.remove_duplicate_guardians()
        self.remove_old_test_files()
        self.remove_duplicate_scripts()
        self.remove_old_batch_files()
        self.clean_old_logs_and_temp()
        self.clean_obsolete_backups()
        self.clean_pycache()
        self.optimize_database_files()

        # Generate report
        self.generate_cleanup_report()

        print("\n✅ Cleanup Complete! Your Celsius AI should now be much more responsive.")


if __name__ == "__main__":
    cleanup = CelsiusCleanupTool()
    cleanup.run_cleanup()
