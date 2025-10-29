#!/usr/bin/env python3
"""
🧹 CELSIUS AI - CLEANUP SCRIPT 🧹
═══════════════════════════════════════════════════════════════════════════════════════════

Intelligent cleanup script to organize and archive redundant files now that we have
unified versions of all major components.

Actions:
• 📦 Archive old server hub variants to /archive folder
• 🗂️ Archive old startup scripts
• 🧪 Archive individual test files
• 📋 Generate cleanup report
• 🔍 Identify additional optimization opportunities

═══════════════════════════════════════════════════════════════════════════════════════════
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
import zipfile


class CelsiusCleanupManager:
    """Intelligent cleanup and archival system"""

    def __init__(self):
        self.base_dir = Path.cwd()
        self.archive_dir = self.base_dir / "archive"
        self.backup_dir = self.base_dir / "backups"
        self.cleanup_report = []

        # Create archive directories
        self.archive_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)

        # Files to archive (not delete - just organize)
        self.archive_targets = {
            "old_server_hubs": [
                "celsius_server_hub_ultimate.py",
                "celsius_server_hub_efficient.py",
                "celsius_server_hub_clean.py",
                "celsius_server_hub_streamlined.py",
                "celsius_server_hub_old.py",
                "celsius_server_hub_backup.py",
            ],
            "old_startup_scripts": [
                "Start_Celsius_Clean.bat",
                "Start_Celsius_Streamlined.bat",
                "Start_Celsius.bat",
                "Start_Celsius_Enhanced.bat",
            ],
            "individual_test_files": [
                "test_twilio_sms.py",
                "test_responsiveness.py",
                "test_red_pocket_sms.py",
                "test_mobile_startup.py",
                "test_integration.py",
                "test_hourly_logging.py",
                "test_gui.py",
                "test_email_only_mode.py",
            ],
            "temp_and_logs": ["*.log", "*.tmp", "celsius_launch_*.log"],
        }

    def analyze_workspace(self):
        """Analyze current workspace and identify cleanup opportunities"""
        print("🔍 Analyzing Celsius AI workspace...")

        analysis = {"total_files": 0, "archivable_files": 0, "current_size_mb": 0, "categories": {}}

        for category, file_patterns in self.archive_targets.items():
            found_files = []

            for pattern in file_patterns:
                if "*" in pattern:
                    # Handle glob patterns
                    matches = list(self.base_dir.glob(pattern))
                    found_files.extend(matches)
                else:
                    # Handle specific files
                    file_path = self.base_dir / pattern
                    if file_path.exists():
                        found_files.append(file_path)

            analysis["categories"][category] = {
                "files": [f.name for f in found_files],
                "count": len(found_files),
                "size_mb": sum(f.stat().st_size for f in found_files if f.exists()) / 1024 / 1024,
            }

            analysis["archivable_files"] += len(found_files)
            analysis["current_size_mb"] += analysis["categories"][category]["size_mb"]

        # Count all files
        all_files = list(self.base_dir.glob("*"))
        analysis["total_files"] = len([f for f in all_files if f.is_file()])

        return analysis

    def create_archive_structure(self):
        """Create organized archive directory structure"""
        archive_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        archive_subdirs = {
            "server_hubs": self.archive_dir / f"server_hubs_{archive_timestamp}",
            "startup_scripts": self.archive_dir / f"startup_scripts_{archive_timestamp}",
            "test_files": self.archive_dir / f"test_files_{archive_timestamp}",
            "logs_temp": self.archive_dir / f"logs_temp_{archive_timestamp}",
        }

        for subdir in archive_subdirs.values():
            subdir.mkdir(exist_ok=True)

        return archive_subdirs

    def archive_files(self, dry_run=True):
        """Archive redundant files to organized structure"""
        print(f"📦 {'DRY RUN: ' if dry_run else ''}Archiving redundant files...")

        archive_dirs = self.create_archive_structure()
        archived_count = 0

        # Archive mapping
        archive_mapping = {
            "old_server_hubs": archive_dirs["server_hubs"],
            "old_startup_scripts": archive_dirs["startup_scripts"],
            "individual_test_files": archive_dirs["test_files"],
            "temp_and_logs": archive_dirs["logs_temp"],
        }

        for category, target_dir in archive_mapping.items():
            print(f"   📂 Processing {category}...")

            for pattern in self.archive_targets[category]:
                if "*" in pattern:
                    # Handle glob patterns
                    matches = list(self.base_dir.glob(pattern))
                    for file_path in matches:
                        if file_path.exists() and file_path.is_file():
                            self._archive_single_file(file_path, target_dir, dry_run)
                            archived_count += 1
                else:
                    # Handle specific files
                    file_path = self.base_dir / pattern
                    if file_path.exists():
                        self._archive_single_file(file_path, target_dir, dry_run)
                        archived_count += 1

        return archived_count

    def _archive_single_file(self, source_path, target_dir, dry_run=True):
        """Archive a single file with metadata"""
        target_path = target_dir / source_path.name

        action_text = "WOULD MOVE" if dry_run else "MOVING"
        print(f"      {action_text}: {source_path.name} -> {target_path}")

        if not dry_run:
            try:
                shutil.move(str(source_path), str(target_path))

                # Create metadata file
                metadata = {
                    "original_path": str(source_path),
                    "archived_date": datetime.now().isoformat(),
                    "file_size": target_path.stat().st_size,
                    "reason": "Superseded by unified version",
                }

                metadata_path = target_path.with_suffix(target_path.suffix + ".meta")
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

            except Exception as e:
                print(f"      ❌ ERROR: Could not archive {source_path.name}: {e}")

    def create_unified_backup(self):
        """Create a single backup ZIP of all important current files"""
        print("💾 Creating unified system backup...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"celsius_unified_system_{timestamp}.zip"

        important_files = [
            "celsius_ultimate_hub.py",
            "Start_Celsius_Ultimate.bat",
            "ultimate_test_suite.py",
            "celsius_server_hub.py",  # The redirect
            "main.py",
            "enhanced_mobile_dashboard.py",
            "enhanced_email_system.py",
            "celsius_lightweight_guardian.py",
        ]

        with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
            backed_up_count = 0

            for file_name in important_files:
                file_path = self.base_dir / file_name
                if file_path.exists():
                    zip_file.write(file_path, file_name)
                    backed_up_count += 1
                    print(f"   ✅ Added {file_name} to backup")

            # Add backup metadata
            backup_info = {
                "backup_date": datetime.now().isoformat(),
                "files_count": backed_up_count,
                "system_version": "Unified Ultimate System",
                "files_included": [f for f in important_files if (self.base_dir / f).exists()],
            }

            zip_file.writestr("backup_info.json", json.dumps(backup_info, indent=2))

        backup_size_mb = backup_file.stat().st_size / 1024 / 1024
        print(f"   💾 Backup created: {backup_file.name} ({backup_size_mb:.2f} MB)")
        return backup_file

    def generate_cleanup_report(self, analysis, archived_count):
        """Generate comprehensive cleanup report"""
        report = {
            "cleanup_date": datetime.now().isoformat(),
            "analysis": analysis,
            "archived_files_count": archived_count,
            "space_saved_mb": analysis["current_size_mb"],
            "remaining_files": analysis["total_files"] - archived_count,
            "cleanup_summary": {
                "old_server_hubs": analysis["categories"]["old_server_hubs"]["count"],
                "old_startup_scripts": analysis["categories"]["old_startup_scripts"]["count"],
                "individual_tests": analysis["categories"]["individual_test_files"]["count"],
                "temp_logs": analysis["categories"]["temp_and_logs"]["count"],
            },
            "unified_system_files": [
                "celsius_ultimate_hub.py",
                "Start_Celsius_Ultimate.bat",
                "ultimate_test_suite.py",
                "celsius_server_hub.py (redirect)",
            ],
        }

        report_file = self.base_dir / f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        return report, report_file

    def print_cleanup_summary(self, analysis, archived_count, report_file):
        """Print comprehensive cleanup summary"""
        print("\n" + "=" * 70)
        print("🧹 CELSIUS AI CLEANUP SUMMARY")
        print("=" * 70)

        print(f"\n📊 Workspace Analysis:")
        print(f"   Total files: {analysis['total_files']}")
        print(f"   Archivable files: {analysis['archivable_files']}")
        print(f"   Space to reclaim: {analysis['current_size_mb']:.2f} MB")

        print(f"\n📦 Archive Categories:")
        for category, data in analysis["categories"].items():
            if data["count"] > 0:
                print(f"   📂 {category}: {data['count']} files ({data['size_mb']:.2f} MB)")
                for file_name in data["files"][:3]:  # Show first 3
                    print(f"      • {file_name}")
                if len(data["files"]) > 3:
                    print(f"      • ... and {len(data['files']) - 3} more")

        print(f"\n🎯 Unified System Components:")
        unified_files = [
            "celsius_ultimate_hub.py (Combined server hub)",
            "Start_Celsius_Ultimate.bat (Unified launcher)",
            "ultimate_test_suite.py (Combined testing)",
            "celsius_server_hub.py (Redirect to ultimate)",
        ]

        for component in unified_files:
            file_name = component.split(" ")[0]
            status = "✅" if (self.base_dir / file_name).exists() else "❌"
            print(f"   {status} {component}")

        print(f"\n📋 Report saved to: {report_file.name}")
        print("\n💡 Next Steps:")
        print("   1. Review archived files in /archive directory")
        print("   2. Test unified system functionality")
        print("   3. Update documentation if needed")
        print("   4. Run performance optimization")


def main():
    """Main cleanup execution"""
    cleanup_manager = CelsiusCleanupManager()

    print("🛡️ Celsius AI Cleanup Script")
    print("=" * 40)

    # Analyze workspace
    analysis = cleanup_manager.analyze_workspace()

    # Show what would be archived
    print(f"\n📋 Found {analysis['archivable_files']} files to archive ({analysis['current_size_mb']:.2f} MB)")

    response = input("\nProceed with cleanup? (y/N): ").strip().lower()

    if response == "y":
        # Create backup first
        backup_file = cleanup_manager.create_unified_backup()

        # Perform actual archival
        archived_count = cleanup_manager.archive_files(dry_run=False)

        # Generate report
        report, report_file = cleanup_manager.generate_cleanup_report(analysis, archived_count)

        # Print summary
        cleanup_manager.print_cleanup_summary(analysis, archived_count, report_file)

        print(f"\n✅ Cleanup completed! Archived {archived_count} files.")
        print(f"💾 Backup: {backup_file.name}")

    else:
        print("\n🔍 Dry run completed. No files were moved.")
        cleanup_manager.archive_files(dry_run=True)


if __name__ == "__main__":
    main()
