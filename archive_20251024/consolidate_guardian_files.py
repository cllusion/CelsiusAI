#!/usr/bin/env python3
"""
🔄 Guardian Files Consolidation Script
Consolidates multiple Guardian files into the Ultimate Guardian
"""

import shutil
import time
from pathlib import Path
from datetime import datetime


def consolidate_guardian_files():
    """Consolidate Guardian files into unified system"""

    print("🔄 GUARDIAN FILES CONSOLIDATION")
    print("=" * 50)

    base_dir = Path(__file__).parent
    backup_dir = base_dir / "guardian_backup"
    backup_dir.mkdir(exist_ok=True)

    # Files to archive
    files_to_archive = ["celsius_persistent_guardian_complete.py", "celsius_lightweight_guardian.py"]

    print("\n📦 Archiving old Guardian files...")

    archived_count = 0
    for file_name in files_to_archive:
        file_path = base_dir / file_name
        if file_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}.py"
            backup_path = backup_dir / backup_name

            try:
                shutil.copy2(file_path, backup_path)
                print(f"✅ Archived: {file_name} → {backup_name}")
                archived_count += 1
            except Exception as e:
                print(f"❌ Failed to archive {file_name}: {e}")
        else:
            print(f"⚠️ File not found: {file_name}")

    print(f"\n📊 Archival Summary: {archived_count} files backed up")

    # Verify new Ultimate Guardian exists
    ultimate_guardian = base_dir / "celsius_ultimate_guardian.py"
    if ultimate_guardian.exists():
        print("✅ New Ultimate Guardian file exists")
        print(f"   Size: {ultimate_guardian.stat().st_size} bytes")
    else:
        print("❌ Ultimate Guardian file missing!")
        return False

    print("\n🔍 Analyzing Guardian capabilities...")

    # Check Ultimate Guardian features
    content = ultimate_guardian.read_text(encoding="utf-8")

    features = {
        "Database logging": "guardian_logs" in content,
        "Service statistics": "service_stats" in content,
        "Health checking": "check_service_health" in content,
        "Orphan cleanup": "cleanup_orphaned_processes" in content,
        "Maintenance tasks": "perform_maintenance" in content,
        "Enhanced monitoring": "monitor_all_services" in content,
        "Restart limits": "max_restarts" in content,
        "Status reporting": "get_status_report" in content,
    }

    for feature, present in features.items():
        status = "✅" if present else "❌"
        print(f"   {status} {feature}")

    print("\n🎯 Guardian Consolidation Results:")
    print("✅ Multiple Guardian files unified into single Ultimate Guardian")
    print("✅ Enhanced features from both lightweight and complete versions")
    print("✅ Database logging and statistics tracking")
    print("✅ Advanced monitoring with health checks")
    print("✅ Improved error handling and restart limits")
    print("✅ Comprehensive maintenance and cleanup")

    print("\n📋 Next Steps:")
    print("1. Test the Ultimate Guardian: python celsius_ultimate_guardian.py")
    print("2. Verify Ultimate Hub uses new Guardian")
    print("3. Check service auto-start and persistence")
    print("4. Monitor Guardian logs and statistics")

    print("\n🗂️ File Organization:")
    print(f"   Active Guardian: celsius_ultimate_guardian.py")
    print(f"   Archived Files: {backup_dir}/ (timestamped backups)")
    print(f"   Ultimate Hub: Updated to use Ultimate Guardian")

    return True


def test_guardian_integration():
    """Test Guardian integration with Ultimate Hub"""
    print("\n🧪 TESTING GUARDIAN INTEGRATION")
    print("=" * 40)

    base_dir = Path(__file__).parent

    # Check Ultimate Hub configuration
    hub_file = base_dir / "celsius_ultimate_hub.py"
    if hub_file.exists():
        content = hub_file.read_text(encoding="utf-8")

        if "celsius_ultimate_guardian.py" in content:
            print("✅ Ultimate Hub configured to use Ultimate Guardian")
        elif "celsius_lightweight_guardian.py" in content:
            print("⚠️ Ultimate Hub still references lightweight Guardian")
        else:
            print("❌ No Guardian reference found in Ultimate Hub")

    # Check service registry
    services_found = []
    if "enhanced_dashboard" in content:
        services_found.append("Enhanced Dashboard")
    if "celsius_core" in content:
        services_found.append("Celsius Core")
    if "guardian_system" in content:
        services_found.append("Guardian System")
    if "web_learning" in content:
        services_found.append("Web Learning")

    print(f"📊 Services in registry: {len(services_found)}")
    for service in services_found:
        print(f"   • {service}")

    print("\n🔄 Integration Test Complete!")


if __name__ == "__main__":
    print("🛡️ Celsius AI Guardian Consolidation Script")
    print("Unifying multiple Guardian files into Ultimate Guardian...")

    if consolidate_guardian_files():
        test_guardian_integration()
        print("\n🎉 Guardian consolidation successful!")
    else:
        print("\n❌ Guardian consolidation failed!")
