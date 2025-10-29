#!/usr/bin/env python3
"""
Celsius AI Code Approval System
Handles code change requests with formatted submissions and user approval
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import logging


class CelsiusCodeApprovalSystem:
    """System for managing code approval requests with formatted submissions"""

    def __init__(self):
        self.db_path = "celsius_code_approvals.db"
        self.approval_log = "celsius_approval.log"
        self.pending_approvals = []

        self.setup_logging()
        self.init_database()

    def setup_logging(self):
        """Setup logging for approval activities"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(self.approval_log), logging.StreamHandler()],
        )
        self.logger = logging.getLogger("CelsiusCodeApproval")

    def init_database(self):
        """Initialize database for storing approval requests"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                file_path TEXT,
                original_code TEXT,
                proposed_code TEXT,
                change_type TEXT,
                priority INTEGER DEFAULT 1,
                submitted_by TEXT DEFAULT 'celsius_ai',
                submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                reviewed_by TEXT,
                reviewed_at DATETIME,
                review_comments TEXT,
                formatted_submission TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                action TEXT NOT NULL,
                performed_by TEXT,
                performed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                comments TEXT,
                FOREIGN KEY (request_id) REFERENCES approval_requests (request_id)
            )
        """
        )

        conn.commit()
        conn.close()

        self.logger.info("Code approval database initialized")

    def submit_code_change_request(
        self,
        title: str,
        description: str,
        file_path: str,
        original_code: str,
        proposed_code: str,
        change_type: str = "improvement",
        priority: int = 1,
    ) -> str:
        """Submit a code change request with formatted presentation"""
        try:
            # Generate unique request ID
            request_data = f"{title}{file_path}{datetime.now().isoformat()}"
            request_id = hashlib.md5(request_data.encode()).hexdigest()[:12]

            # Format the submission like a report
            formatted_submission = self.format_approval_request(
                request_id, title, description, file_path, original_code, proposed_code, change_type, priority
            )

            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO approval_requests 
                (request_id, title, description, file_path, original_code, 
                 proposed_code, change_type, priority, formatted_submission)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    request_id,
                    title,
                    description,
                    file_path,
                    original_code,
                    proposed_code,
                    change_type,
                    priority,
                    formatted_submission,
                ),
            )

            conn.commit()
            conn.close()

            # Log submission
            self.logger.info(f"Code change request submitted: {request_id} - {title}")

            # Add to pending list
            self.pending_approvals.append(
                {
                    "request_id": request_id,
                    "title": title,
                    "file_path": file_path,
                    "change_type": change_type,
                    "priority": priority,
                    "submitted_at": datetime.now().isoformat(),
                }
            )

            return request_id

        except Exception as e:
            self.logger.error(f"Error submitting code change request: {str(e)}")
            return None

    def format_approval_request(
        self,
        request_id: str,
        title: str,
        description: str,
        file_path: str,
        original_code: str,
        proposed_code: str,
        change_type: str,
        priority: int,
    ) -> str:
        """Format approval request using the same style as reports"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Priority indicators
            priority_indicators = {1: "🟢 Low", 2: "🟡 Medium", 3: "🔴 High", 4: "⚡ Critical"}
            priority_display = priority_indicators.get(priority, "🟡 Medium")

            # Change type icons
            change_icons = {
                "improvement": "✨",
                "bug_fix": "🐛",
                "optimization": "⚡",
                "security": "🛡️",
                "feature": "🚀",
                "refactor": "🔧",
            }
            change_icon = change_icons.get(change_type, "📝")

            formatted_request = f"""
╔══════════════════════════════════════════════════════════════╗
║                    🤖  CELSIUS AI CODE APPROVAL              ║
╚══════════════════════════════════════════════════════════════╝

📋 REQUEST DETAILS
   Request ID: {request_id}
   Generated: {current_time}
   Status: 🟡 PENDING APPROVAL
   Submitted By: Celsius AI System

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 CHANGE SUMMARY
   {change_icon} Title: {title}
   🎯 Priority: {priority_display}
   📁 File: {file_path}
   🔄 Change Type: {change_type.replace('_', ' ').title()}

📖 DESCRIPTION
   {description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📜 ORIGINAL CODE
```python
{original_code[:500] + '...' if len(original_code) > 500 else original_code}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ PROPOSED CHANGES
```python
{proposed_code[:500] + '...' if len(proposed_code) > 500 else proposed_code}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 IMPACT ANALYSIS
   📊 Lines Modified: {len(proposed_code.splitlines()) - len(original_code.splitlines())}
   🎯 Change Scope: {change_type.replace('_', ' ').title()}
   ⚠️ Risk Level: {'High' if priority >= 3 else 'Medium' if priority == 2 else 'Low'}
   
🛡️ SAFETY NOTES
   • This change requires manual approval
   • Celsius AI cannot self-approve code modifications
   • Review carefully before approving
   • All changes are logged and reversible

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ ACTION REQUIRED
   ✅ APPROVE - Accept and apply these changes
   ❌ DENY - Reject this change request
   📝 REVIEW - Add comments before decision

🤖 Celsius AI - Awaiting Your Approval for Code Changes
   📱 Use Server Hub approval interface for easy management
   🔄 Request will remain pending until reviewed
   📊 View all pending requests in Code Approval tab

"""

            return formatted_request

        except Exception as e:
            return f"""
╔══════════════════════════════════════════════════════════════╗
║                    ⚠️  FORMATTING ERROR                      ║
╚══════════════════════════════════════════════════════════════╝

❌ Error formatting approval request: {str(e)}

📋 Raw Request Data:
   ID: {request_id}
   Title: {title}
   File: {file_path}
   Type: {change_type}
"""

    def get_pending_requests(self) -> List[Dict]:
        """Get all pending approval requests"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT request_id, title, file_path, change_type, priority, 
                       submitted_at, formatted_submission
                FROM approval_requests 
                WHERE status = 'pending'
                ORDER BY priority DESC, submitted_at ASC
            """
            )

            requests = cursor.fetchall()
            conn.close()

            return [
                {
                    "request_id": req[0],
                    "title": req[1],
                    "file_path": req[2],
                    "change_type": req[3],
                    "priority": req[4],
                    "submitted_at": req[5],
                    "formatted_submission": req[6],
                }
                for req in requests
            ]

        except Exception as e:
            self.logger.error(f"Error getting pending requests: {str(e)}")
            return []

    def approve_request(self, request_id: str, reviewer: str, comments: str = "") -> bool:
        """Approve a code change request"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Update request status
            cursor.execute(
                """
                UPDATE approval_requests 
                SET status = 'approved', reviewed_by = ?, reviewed_at = ?, 
                    review_comments = ?
                WHERE request_id = ?
            """,
                (reviewer, datetime.now().isoformat(), comments, request_id),
            )

            # Add to history
            cursor.execute(
                """
                INSERT INTO approval_history 
                (request_id, action, performed_by, comments)
                VALUES (?, 'approved', ?, ?)
            """,
                (request_id, reviewer, comments),
            )

            conn.commit()
            conn.close()

            # Remove from pending list
            self.pending_approvals = [req for req in self.pending_approvals if req["request_id"] != request_id]

            self.logger.info(f"Code change request approved: {request_id} by {reviewer}")
            return True

        except Exception as e:
            self.logger.error(f"Error approving request {request_id}: {str(e)}")
            return False

    def deny_request(self, request_id: str, reviewer: str, comments: str = "") -> bool:
        """Deny a code change request"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Update request status
            cursor.execute(
                """
                UPDATE approval_requests 
                SET status = 'denied', reviewed_by = ?, reviewed_at = ?, 
                    review_comments = ?
                WHERE request_id = ?
            """,
                (reviewer, datetime.now().isoformat(), comments, request_id),
            )

            # Add to history
            cursor.execute(
                """
                INSERT INTO approval_history 
                (request_id, action, performed_by, comments)
                VALUES (?, 'denied', ?, ?)
            """,
                (request_id, reviewer, comments),
            )

            conn.commit()
            conn.close()

            # Remove from pending list
            self.pending_approvals = [req for req in self.pending_approvals if req["request_id"] != request_id]

            self.logger.info(f"Code change request denied: {request_id} by {reviewer}")
            return True

        except Exception as e:
            self.logger.error(f"Error denying request {request_id}: {str(e)}")
            return False

    def get_request_details(self, request_id: str) -> Optional[Dict]:
        """Get detailed information about a specific request"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM approval_requests WHERE request_id = ?
            """,
                (request_id,),
            )

            result = cursor.fetchone()
            conn.close()

            if result:
                columns = [
                    "id",
                    "request_id",
                    "title",
                    "description",
                    "file_path",
                    "original_code",
                    "proposed_code",
                    "change_type",
                    "priority",
                    "submitted_by",
                    "submitted_at",
                    "status",
                    "reviewed_by",
                    "reviewed_at",
                    "review_comments",
                    "formatted_submission",
                ]

                return dict(zip(columns, result))

            return None

        except Exception as e:
            self.logger.error(f"Error getting request details for {request_id}: {str(e)}")
            return None

    def get_approval_statistics(self) -> Dict:
        """Get statistics about approval requests"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get counts by status
            cursor.execute(
                """
                SELECT status, COUNT(*) FROM approval_requests GROUP BY status
            """
            )
            status_counts = dict(cursor.fetchall())

            # Get recent activity
            cursor.execute(
                """
                SELECT COUNT(*) FROM approval_requests 
                WHERE submitted_at > datetime('now', '-7 days')
            """
            )
            recent_requests = cursor.fetchone()[0]

            conn.close()

            return {
                "total_requests": sum(status_counts.values()),
                "pending": status_counts.get("pending", 0),
                "approved": status_counts.get("approved", 0),
                "denied": status_counts.get("denied", 0),
                "recent_requests": recent_requests,
            }

        except Exception as e:
            self.logger.error(f"Error getting approval statistics: {str(e)}")
            return {}


# Test function
def test_approval_system():
    """Test the code approval system"""
    print("CELSIUS AI CODE APPROVAL SYSTEM TEST")
    print("=" * 50)

    approval_system = CelsiusCodeApprovalSystem()

    # Test submission
    request_id = approval_system.submit_code_change_request(
        title="Improve error handling in web learning",
        description="Add try-catch blocks to prevent crashes during web scraping",
        file_path="celsius_web_learner.py",
        original_code="def extract_content(url):\n    response = requests.get(url)\n    return response.text",
        proposed_code="def extract_content(url):\n    try:\n        response = requests.get(url, timeout=10)\n        response.raise_for_status()\n        return response.text\n    except Exception as e:\n        print(f'Error: {e}')\n        return None",
        change_type="improvement",
        priority=2,
    )

    if request_id:
        print(f"✅ Test request submitted: {request_id}")

        # Get pending requests
        pending = approval_system.get_pending_requests()
        print(f"📋 Pending requests: {len(pending)}")

        # Get statistics
        stats = approval_system.get_approval_statistics()
        print(f"📊 Total requests: {stats.get('total_requests', 0)}")

        print("✅ Code approval system is working!")
    else:
        print("❌ Failed to submit test request")


if __name__ == "__main__":
    test_approval_system()
