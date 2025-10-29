#!/usr/bin/env python3
"""
Celsius AI Code Approval Demonstration
Shows the complete workflow from code improvement detection to approval
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))

from celsius_code_approval import CelsiusCodeApprovalSystem
from celsius_collaborative_engine import CelsiusCollaborativeEngine


def demonstrate_code_approval_workflow():
    """Demonstrate the complete code approval workflow"""
    print("🤖 CELSIUS AI CODE APPROVAL WORKFLOW DEMONSTRATION")
    print("=" * 60)

    # Initialize systems
    print("\n1️⃣ Initializing Code Approval System...")
    approval_system = CelsiusCodeApprovalSystem()

    print("2️⃣ Initializing Collaborative Engine...")
    try:
        collaborative_engine = CelsiusCollaborativeEngine()
        print("✅ Collaborative engine initialized")
    except Exception as e:
        print(f"⚠️ Collaborative engine initialization failed: {e}")
        print("📝 Continuing with approval system demonstration...")

    # Submit sample code change requests
    print("\n3️⃣ Submitting Sample Code Change Requests...")

    sample_requests = [
        {
            "title": "Add error handling to network requests",
            "description": "Improve reliability by adding timeout and error handling to all network requests",
            "file_path": "celsius_web_learner.py",
            "original_code": """def fetch_data(url):
    response = requests.get(url)
    return response.json()""",
            "proposed_code": """def fetch_data(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None
    except ValueError as e:
        print(f"JSON parsing error: {e}")
        return None""",
            "change_type": "error_handling",
            "priority": 2,
        },
        {
            "title": "Optimize memory usage in data processing",
            "description": "Use generators instead of lists to reduce memory consumption for large datasets",
            "file_path": "celsius_analysis.py",
            "original_code": """def process_large_dataset(data):
    results = []
    for item in data:
        processed = expensive_operation(item)
        results.append(processed)
    return results""",
            "proposed_code": """def process_large_dataset(data):
    for item in data:
        processed = expensive_operation(item)
        yield processed""",
            "change_type": "memory_optimization",
            "priority": 1,
        },
        {
            "title": "Security improvement for file access",
            "description": "Add path validation to prevent directory traversal attacks",
            "file_path": "celsius_file_handler.py",
            "original_code": """def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()""",
            "proposed_code": """import os
def read_file(filename):
    # Validate and sanitize file path
    safe_path = os.path.normpath(filename)
    if '..' in safe_path or safe_path.startswith('/'):
        raise ValueError("Invalid file path")
    
    with open(safe_path, 'r') as f:
        return f.read()""",
            "change_type": "security",
            "priority": 3,
        },
    ]

    submitted_requests = []
    for i, request in enumerate(sample_requests, 1):
        print(f"\n   📝 Submitting request {i}: {request['title'][:40]}...")

        request_id = approval_system.submit_code_change_request(
            title=request["title"],
            description=request["description"],
            file_path=request["file_path"],
            original_code=request["original_code"],
            proposed_code=request["proposed_code"],
            change_type=request["change_type"],
            priority=request["priority"],
        )

        if request_id:
            submitted_requests.append(request_id)
            print(f"   ✅ Request submitted: {request_id}")
        else:
            print(f"   ❌ Failed to submit request {i}")

    print(f"\n✅ Successfully submitted {len(submitted_requests)} code change requests")

    # Display pending requests
    print("\n4️⃣ Viewing Pending Requests...")
    pending_requests = approval_system.get_pending_requests()

    print(f"\n📋 Pending Requests: {len(pending_requests)}")
    for i, request in enumerate(pending_requests, 1):
        priority_map = {1: "🟢 Low", 2: "🟡 Medium", 3: "🔴 High", 4: "⚡ Critical"}
        priority_display = priority_map.get(request["priority"], "🟡 Medium")

        print(f"   {i}. {request['title']}")
        print(f"      📁 File: {os.path.basename(request['file_path'])}")
        print(f"      🎯 Priority: {priority_display}")
        print(f"      🔄 Type: {request['change_type'].replace('_', ' ').title()}")
        print()

    # Show formatted submission for first request
    if pending_requests:
        print("5️⃣ Example Formatted Submission:")
        print("-" * 60)
        first_request = pending_requests[0]
        print(first_request["formatted_submission"])

    # Display statistics
    print("\n6️⃣ Approval Statistics...")
    stats = approval_system.get_approval_statistics()
    print(f"   📊 Total requests: {stats.get('total_requests', 0)}")
    print(f"   ⏳ Pending: {stats.get('pending', 0)}")
    print(f"   ✅ Approved: {stats.get('approved', 0)}")
    print(f"   ❌ Denied: {stats.get('denied', 0)}")
    print(f"   📈 Recent (7 days): {stats.get('recent_requests', 0)}")

    # Simulate approval workflow
    print("\n7️⃣ Simulating Approval Workflow...")
    if submitted_requests:
        # Approve first request
        first_id = submitted_requests[0]
        print(f"\n   ✅ Approving request: {first_id}")
        success = approval_system.approve_request(
            first_id, "demo_admin", "Approved during demonstration - good security improvement"
        )
        if success:
            print(f"   ✅ Request {first_id} approved successfully")

        # Deny second request if exists
        if len(submitted_requests) > 1:
            second_id = submitted_requests[1]
            print(f"\n   ❌ Denying request: {second_id}")
            success = approval_system.deny_request(
                second_id, "demo_admin", "Denied for demonstration - would need more testing"
            )
            if success:
                print(f"   ❌ Request {second_id} denied successfully")

    # Final statistics
    print("\n8️⃣ Final Statistics...")
    final_stats = approval_system.get_approval_statistics()
    print(f"   📊 Total requests: {final_stats.get('total_requests', 0)}")
    print(f"   ⏳ Pending: {final_stats.get('pending', 0)}")
    print(f"   ✅ Approved: {final_stats.get('approved', 0)}")
    print(f"   ❌ Denied: {final_stats.get('denied', 0)}")

    print("\n🎉 CODE APPROVAL WORKFLOW DEMONSTRATION COMPLETE!")
    print("=" * 60)
    print("📱 Use the Server Hub 'Code Approval' tab to manage requests in the GUI")
    print("🤖 Celsius AI will submit real improvement requests as it analyzes code")
    print("✅ All requests require manual approval before implementation")
    print("🛡️ This ensures human oversight of all code changes")


if __name__ == "__main__":
    demonstrate_code_approval_workflow()
