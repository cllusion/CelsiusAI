#!/usr/bin/env python3
"""
Fix Unicode encoding issues in Celsius AI files by replacing emojis with ASCII equivalents
"""

import os
import re
from pathlib import Path


def fix_unicode_in_file(file_path):
    """Fix Unicode characters in a file by replacing with ASCII equivalents"""

    # Emoji to ASCII mapping
    replacements = {
        "🚀": "[START]",
        "🛑": "[STOP]",
        "❌": "[ERROR]",
        "✅": "[OK]",
        "⚠️": "[WARNING]",
        "📊": "[STATUS]",
        "🔧": "[CONFIG]",
        "🎯": "[TARGET]",
        "🛡️": "[SHIELD]",
        "ℹ️": "[INFO]",
        "🖥️": "[SERVER]",
        "💻": "[COMPUTER]",
        "🌐": "[NETWORK]",
        "📁": "[FOLDER]",
        "📂": "[FILES]",
        "🔐": "[SECURE]",
        "🔒": "[LOCKED]",
        "🔓": "[UNLOCKED]",
        "🟢": "[ONLINE]",
        "🔴": "[OFFLINE]",
        "🟡": "[PENDING]",
        "⭐": "[STAR]",
        "🎉": "[SUCCESS]",
        "💡": "[TIP]",
        "🔍": "[SEARCH]",
        "⚡": "[FAST]",
        "🔄": "[REFRESH]",
        "📈": "[STATS]",
        "🏠": "[HOME]",
        "⚙️": "[SETTINGS]",
        "📱": "[MOBILE]",
        "🌡️": "[CELSIUS]",
        "⚕️": "[HEALTH]",
        "🛠️": "[TOOLS]",
    }

    try:
        # Read file content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Track changes
        original_content = content
        changes_made = 0

        # Replace each emoji
        for emoji, replacement in replacements.items():
            if emoji in content:
                content = content.replace(emoji, replacement)
                changes_made += 1
                print(f"  Replaced '{emoji}' with '{replacement}'")

        # Write back if changes were made
        if changes_made > 0:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ Fixed {changes_made} Unicode characters in {file_path}")
            return True
        else:
            print(f"- No Unicode issues found in {file_path}")
            return False

    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False


def main():
    """Fix Unicode issues in all Python files"""
    base_dir = Path(__file__).parent

    # Files to fix
    python_files = [
        "celsius_server_control.py",
        "celsius_unified_launcher.py",
        "celsius_server_hub.py",
        "celsius_defense_manager.py",
        "celsius_system_status.py",
        "cleanup_duplicate_files.py",
        "enhanced_mobile_dashboard.py",
        "celsius_hourly_logger.py",
    ]

    print("[CONFIG] FIXING UNICODE ENCODING ISSUES")
    print("=" * 50)

    total_fixed = 0

    for filename in python_files:
        file_path = base_dir / filename
        if file_path.exists():
            print(f"\nProcessing: {filename}")
            if fix_unicode_in_file(file_path):
                total_fixed += 1
        else:
            print(f"⚠ File not found: {filename}")

    print(f"\n📊 SUMMARY")
    print("=" * 20)
    print(f"Files processed: {len([f for f in python_files if (base_dir / f).exists()])}")
    print(f"Files fixed: {total_fixed}")
    print(f"Status: {'✓ Complete' if total_fixed >= 0 else '✗ Issues remain'}")


if __name__ == "__main__":
    main()
