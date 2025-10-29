#!/usr/bin/env python3
"""
Fix Ultimate Hub scrolling by updating all tab methods to use scrollable_content
"""

import re
from pathlib import Path


def fix_scrollable_content():
    """Replace all content_frame references with scrollable_content in tab methods"""

    hub_file = Path("celsius_ultimate_hub.py")
    if not hub_file.exists():
        print("❌ Ultimate Hub file not found!")
        return False

    print("🔄 Fixing scrollable content in Ultimate Hub...")

    content = hub_file.read_text(encoding="utf-8")

    # Find all tab method sections and replace content_frame with scrollable_content
    # Methods to update: show_services, show_monitoring, show_ai_systems, show_security, show_administration, show_testing_suite

    # Pattern to find content_frame within tab methods
    methods_to_fix = [
        "show_services",
        "show_monitoring",
        "show_ai_systems",
        "show_security",
        "show_administration",
        "show_testing_suite",
    ]

    replacements_made = 0

    for method in methods_to_fix:
        # Find the method definition
        method_pattern = rf"(def {method}\(self\):.*?)(?=\n    def|\nclass|\n\nif __name__|\Z)"
        method_match = re.search(method_pattern, content, re.DOTALL)

        if method_match:
            method_content = method_match.group(1)
            original_method = method_content

            # Replace content_frame with scrollable_content in this method
            updated_method = method_content.replace("self.content_frame", "self.scrollable_content")

            if updated_method != original_method:
                content = content.replace(original_method, updated_method)
                count = original_method.count("self.content_frame")
                replacements_made += count
                print(f"✅ Fixed {method}: {count} replacements")
            else:
                print(f"ℹ️ {method}: Already using scrollable_content")
        else:
            print(f"⚠️ {method}: Method not found")

    if replacements_made > 0:
        # Write back to file
        hub_file.write_text(content, encoding="utf-8")
        print(f"\n🎉 Successfully updated {replacements_made} references to use scrollable_content")
        return True
    else:
        print("\nℹ️ No changes needed - all methods already use scrollable_content")
        return True


if __name__ == "__main__":
    print("🔧 Ultimate Hub Scrolling Fix")
    print("=" * 40)

    if fix_scrollable_content():
        print("\n✅ Scrolling fix complete!")
        print("📋 Benefits:")
        print("   • All tab content now scrollable")
        print("   • No more UI squishing")
        print("   • Mouse wheel scrolling supported")
        print("   • Better UX for long content")
    else:
        print("\n❌ Scrolling fix failed!")
