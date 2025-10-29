#!/usr/bin/env python3
"""
Test script to verify reports are populating correctly in the Ultimate Hub
"""

import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))


def test_learning_reports():
    """Test learning reports availability"""
    print("🔍 Testing Learning Reports...")

    reports_dir = PROJECT_ROOT / "learning_reports"
    if not reports_dir.exists():
        print("❌ Learning reports directory not found")
        return False

    report_files = list(reports_dir.glob("celsius_learning_report_*.json"))
    if not report_files:
        print("❌ No learning report files found")
        return False

    print(f"✅ Found {len(report_files)} learning reports")

    # Test reading the latest report
    latest_report = sorted(report_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
    try:
        with open(latest_report, "r") as f:
            report_data = json.load(f)

        print(f"📄 Latest report: {latest_report.name}")
        print(f"   Generated: {report_data.get('generated_at', 'Unknown')[:19]}")
        print(f"   Topics: {report_data.get('topics_covered', 0)}")
        print(f"   Content: {report_data.get('total_content_learned', 0)}")
        return True

    except Exception as e:
        print(f"❌ Error reading latest report: {e}")
        return False


def test_guardian_database():
    """Test Guardian database availability"""
    print("\n🔍 Testing Guardian Database...")

    guardian_db = PROJECT_ROOT / "data" / "celsius_guardian.db"
    if not guardian_db.exists():
        print("❌ Guardian database not found")
        return False

    try:
        conn = sqlite3.connect(guardian_db)
        cursor = conn.cursor()

        # Check if guardian_logs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guardian_logs'")
        if not cursor.fetchone():
            print("❌ guardian_logs table not found")
            conn.close()
            return False

        # Get record count
        cursor.execute("SELECT COUNT(*) FROM guardian_logs")
        count = cursor.fetchone()[0]

        # Get recent events
        cursor.execute(
            """
            SELECT timestamp, service_name, event_type, message 
            FROM guardian_logs 
            ORDER BY timestamp DESC 
            LIMIT 5
        """
        )

        recent_events = cursor.fetchall()
        conn.close()

        print(f"✅ Guardian database accessible")
        print(f"   Total log entries: {count}")
        print(f"   Recent events: {len(recent_events)}")

        if recent_events:
            print("   Latest events:")
            for event in recent_events[:3]:
                timestamp, service, event_type, message = event
                print(f"     [{timestamp}] {service} - {event_type}")

        return True

    except Exception as e:
        print(f"❌ Error accessing Guardian database: {e}")
        return False


def test_ultimate_hub_reports():
    """Test if Ultimate Hub reports functionality is available"""
    print("\n🔍 Testing Ultimate Hub Reports Integration...")

    try:
        # Check if the Ultimate Hub file exists and has the reports methods
        hub_file = PROJECT_ROOT / "src" / "hub" / "celsius_ultimate_hub.py"
        if not hub_file.exists():
            print("❌ Ultimate Hub file not found")
            return False

        with open(hub_file, "r", encoding="utf-8") as f:
            hub_content = f.read()

        required_methods = [
            "def create_reports_tab",
            "def refresh_learning_reports",
            "def show_guardian_report",
            "def show_security_report",
            "def show_performance_report",
        ]

        missing_methods = []
        for method in required_methods:
            if method not in hub_content:
                missing_methods.append(method)

        if missing_methods:
            print(f"❌ Missing methods in Ultimate Hub: {missing_methods}")
            return False

        print("✅ Ultimate Hub reports functionality present")
        print("   Available reports:")
        print("     • Learning Reports (from learning_reports/)")
        print("     • Guardian Reports (from Guardian database)")
        print("     • Security Reports (system integrity)")
        print("     • Performance Reports (system resources)")

        return True

    except Exception as e:
        print(f"❌ Error checking Ultimate Hub: {e}")
        return False


def main():
    """Run all report tests"""
    print("🛡️ CELSIUS AI - REPORTS INTEGRATION TEST")
    print("=" * 50)

    tests = [test_learning_reports, test_guardian_database, test_ultimate_hub_reports]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 50)
    print("📊 TEST RESULTS:")

    if all(results):
        print("✅ ALL TESTS PASSED - Reports are properly integrated!")
        print("\n💡 To view reports:")
        print("   1. Launch Ultimate Hub")
        print("   2. Navigate to the '📊 Reports' tab")
        print("   3. Use the refresh and view buttons")
    else:
        print("❌ Some tests failed - Reports may not work properly")
        failed_tests = sum(1 for r in results if not r)
        print(f"   {failed_tests}/{len(results)} tests failed")

    print(f"\n📅 Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
