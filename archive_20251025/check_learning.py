#!/usr/bin/env python3
"""
Quick check of Celsius learning activity
"""
import sqlite3
import os
from datetime import datetime


def check_learning_status():
    print("CELSIUS LEARNING STATUS - LIVE CHECK")
    print("=" * 40)

    # Check if databases exist and have recent activity
    databases = {
        "System Learning": "celsius_system.db",
        "Process Training": "celsius_training.db",
        "Code Learning": "celsius_improvements.db",
    }

    active_learning = False

    for db_name, db_file in databases.items():
        if os.path.exists(db_file):
            print(f"✅ {db_name}: Active")
            active_learning = True

            # Check recent activity
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()

                if db_file == "celsius_system.db":
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]

                    if "process_grades" in tables:
                        cursor.execute("SELECT COUNT(*) FROM process_grades")
                        total_grades = cursor.fetchone()[0]
                        print(f"   📊 Total process grades: {total_grades}")

                    if "system_metrics" in tables:
                        cursor.execute("SELECT COUNT(*) FROM system_metrics")
                        total_metrics = cursor.fetchone()[0]
                        print(f"   📈 System metrics collected: {total_metrics}")

                conn.close()

            except Exception as e:
                print(f"   ⚠️ Error reading database: {e}")

        else:
            print(f"⏳ {db_name}: Will start when component activates")

    print()
    if active_learning:
        print("🧠 CELSIUS IS ACTIVELY LEARNING!")
        print("   • Monitoring system performance")
        print("   • Grading process efficiency (0-100)")
        print("   • Learning power usage patterns")
        print("   • Analyzing code for improvements")
        print("   • Building optimization knowledge")
    else:
        print("💤 Learning systems ready to activate")
        print("   Run system integration to start learning")

    print(f"\nLast checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    check_learning_status()
