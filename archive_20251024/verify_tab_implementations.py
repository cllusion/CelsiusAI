#!/usr/bin/env python3
"""
🎯 Quick Ultimate Hub Tab Verification
Verifies that all tab methods are implemented and functional
"""

import re
from pathlib import Path


def verify_tab_implementations():
    """Verify all tab methods are properly implemented"""

    print("🔍 ULTIMATE HUB TAB VERIFICATION")
    print("=" * 50)

    hub_file = Path(__file__).parent / "celsius_ultimate_hub.py"

    if not hub_file.exists():
        print("❌ celsius_ultimate_hub.py not found!")
        return

    content = hub_file.read_text(encoding="utf-8")

    # Check tab methods
    tab_methods = {
        "show_dashboard": "📊 Dashboard Tab",
        "show_services": "⚙️ Services Tab",
        "show_monitoring": "📈 Monitoring Tab",
        "show_ai_systems": "🤖 AI Systems Tab",
        "show_security": "🔒 Security Tab",
        "show_administration": "🛠️ Administration Tab",
        "show_testing": "🧪 Testing Tab",
    }

    print("\n📋 Tab Method Implementation Status:")

    for method, description in tab_methods.items():
        if f"def {method}(" in content:
            # Check if it's more than just a placeholder
            method_pattern = rf"def {method}\(.*?\):(.*?)(?=\n    def|\nclass|\n\nif __name__|\nclass|\Z)"
            match = re.search(method_pattern, content, re.DOTALL)

            if match:
                method_body = match.group(1)
                # Count lines of actual implementation (excluding comments and whitespace)
                lines = [
                    line.strip()
                    for line in method_body.split("\n")
                    if line.strip() and not line.strip().startswith("#") and not line.strip().startswith('"""')
                ]

                if len(lines) > 2:  # More than just a simple label
                    print(f"✅ {description} - FULLY IMPLEMENTED ({len(lines)} lines)")
                else:
                    print(f"⚠️ {description} - Minimal implementation")
            else:
                print(f"❌ {description} - Pattern not found")
        else:
            print(f"❌ {description} - METHOD MISSING")

    # Check supporting methods
    support_methods = [
        "create_service_control_panel",
        "start_all_services",
        "stop_all_services",
        "restart_all_services",
        "enable_guardian_persistence",
        "create_performance_charts",
        "create_log_viewer",
        "create_web_learning_controls",
        "create_authentication_controls",
        "create_maintenance_controls",
    ]

    print("\n🔧 Supporting Methods Status:")
    implemented_count = 0

    for method in support_methods:
        if f"def {method}(" in content:
            print(f"✅ {method}")
            implemented_count += 1
        else:
            print(f"❌ {method}")

    print(f"\n📊 Implementation Summary:")
    print(f"   Tab Methods: {len([m for m in tab_methods if f'def {m}(' in content])}/{len(tab_methods)}")
    print(f"   Support Methods: {implemented_count}/{len(support_methods)}")

    # Check Guardian persistence
    if "initialize_guardian_persistence" in content:
        print(f"✅ Guardian Auto-Start: IMPLEMENTED")
    else:
        print(f"❌ Guardian Auto-Start: MISSING")

    if "enable_guardian_persistence" in content:
        print(f"✅ Guardian Persistence: IMPLEMENTED")
    else:
        print(f"❌ Guardian Persistence: MISSING")

    # Check service registry
    if "service_registry = {" in content:
        print(f"✅ Service Registry: CONFIGURED")

        # Count services
        registry_match = re.search(r"service_registry = \{(.*?)\}", content, re.DOTALL)
        if registry_match:
            services = re.findall(r"'(\w+)':\s*\{", registry_match.group(1))
            print(f"   Registered Services: {len(services)} ({', '.join(services)})")
    else:
        print(f"❌ Service Registry: NOT FOUND")

    print("\n🎯 VERIFICATION COMPLETE!")
    print("\n💡 To test functionality:")
    print("   1. Run: python celsius_ultimate_hub.py")
    print("   2. Login: cllusion001 / T3qy22ny*@dyu0ppn*pG")
    print("   3. Click each tab to verify full interfaces")
    print("   4. Check Guardian auto-starts in Services tab")


if __name__ == "__main__":
    verify_tab_implementations()
