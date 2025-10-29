#!/usr/bin/env python3
"""
Celsius AI Code Approval System
================================
CRITICAL: All code changes MUST be approved by the user.
Celsius AI submits detailed requests explaining:
- What will be changed
- Why it's needed
- Benefits to system
- Potential detriments to user experience
- Alternative approaches considered

The user has final authority on ALL code modifications.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import aiosqlite

# Project setup
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CodeApprovalRequest:
    """Represents a single code approval request from Celsius AI"""

    def __init__(
        self,
        request_id: str,
        title: str,
        description: str,
        files_to_modify: List[str],
        changes_detail: str,
        benefits: str,
        detriments: str,
        alternatives: str,
    ):
        self.request_id = request_id
        self.title = title
        self.description = description
        self.files_to_modify = files_to_modify
        self.changes_detail = changes_detail
        self.benefits = benefits
        self.detriments = detriments
        self.alternatives = alternatives
        self.timestamp = datetime.now()
        self.status = "pending"  # pending, approved, rejected
        self.user_response = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "request_id": self.request_id,
            "title": self.title,
            "description": self.description,
            "files_to_modify": json.dumps(self.files_to_modify),
            "changes_detail": self.changes_detail,
            "benefits": self.benefits,
            "detriments": self.detriments,
            "alternatives": self.alternatives,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "user_response": self.user_response,
        }


class CelsiusCodeApprovalSystem:
    """
    Manages all code approval requests from Celsius AI.
    NO CODE CHANGES are allowed without explicit user approval.
    """

    def __init__(self):
        self.db_path = DATA_DIR / "code_approvals.db"
        self.pending_requests: List[CodeApprovalRequest] = []

    async def initialize(self):
        """Initialize the approval database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    files_to_modify TEXT NOT NULL,
                    changes_detail TEXT NOT NULL,
                    benefits TEXT NOT NULL,
                    detriments TEXT NOT NULL,
                    alternatives TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    user_response TEXT
                )
            """
            )
            await db.commit()
        logger.info("[CODE APPROVAL] System initialized")

    async def submit_request(
        self,
        title: str,
        description: str,
        files_to_modify: List[str],
        changes_detail: str,
        benefits: str,
        detriments: str,
        alternatives: str,
    ) -> str:
        """
        Submit a code change request for user approval.

        Args:
            title: Short title of the change
            description: Detailed description of what and why
            files_to_modify: List of file paths that will be changed
            changes_detail: Detailed explanation of specific changes
            benefits: How this will improve the system
            detriments: Potential negative impacts on user experience
            alternatives: Other approaches that were considered

        Returns:
            request_id: Unique ID for tracking this request
        """
        request_id = f"CAR_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        request = CodeApprovalRequest(
            request_id=request_id,
            title=title,
            description=description,
            files_to_modify=files_to_modify,
            changes_detail=changes_detail,
            benefits=benefits,
            detriments=detriments,
            alternatives=alternatives,
        )

        # Store in database
        async with aiosqlite.connect(self.db_path) as db:
            data = request.to_dict()
            await db.execute(
                """
                INSERT INTO approval_requests 
                (request_id, title, description, files_to_modify, changes_detail,
                 benefits, detriments, alternatives, timestamp, status, user_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data["request_id"],
                    data["title"],
                    data["description"],
                    data["files_to_modify"],
                    data["changes_detail"],
                    data["benefits"],
                    data["detriments"],
                    data["alternatives"],
                    data["timestamp"],
                    data["status"],
                    data["user_response"],
                ),
            )
            await db.commit()

        self.pending_requests.append(request)

        logger.info(f"[CODE APPROVAL REQUEST] {request_id}: {title}")
        logger.info(f"  Files to modify: {', '.join(files_to_modify)}")
        logger.info(f"  Benefits: {benefits[:100]}...")
        logger.info(f"  Detriments: {detriments[:100]}...")

        return request_id

    async def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending approval requests"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM approval_requests WHERE status = "pending" ORDER BY timestamp DESC'
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

    async def approve_request(self, request_id: str, user_notes: str = "") -> bool:
        """User approves a code change request"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE approval_requests 
                SET status = 'approved', user_response = ?
                WHERE request_id = ?
            """,
                (user_notes, request_id),
            )
            await db.commit()

        logger.info(f"[APPROVED] {request_id} - User notes: {user_notes}")
        return True

    async def reject_request(self, request_id: str, reason: str = "") -> bool:
        """User rejects a code change request"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE approval_requests 
                SET status = 'rejected', user_response = ?
                WHERE request_id = ?
            """,
                (reason, request_id),
            )
            await db.commit()

        logger.info(f"[REJECTED] {request_id} - Reason: {reason}")
        return True

    async def get_request_status(self, request_id: str) -> Optional[str]:
        """Check status of a specific request"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT status FROM approval_requests WHERE request_id = ?", (request_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def wait_for_approval(self, request_id: str, timeout: int = None) -> bool:
        """
        Wait for user to approve or reject a request.

        Args:
            request_id: The request to wait for
            timeout: Max seconds to wait (None = wait indefinitely)

        Returns:
            True if approved, False if rejected or timeout
        """
        start_time = datetime.now()

        while True:
            status = await self.get_request_status(request_id)

            if status == "approved":
                return True
            elif status == "rejected":
                return False

            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    logger.warning(f"[TIMEOUT] Request {request_id} timed out after {timeout}s")
                    return False

            await asyncio.sleep(5)  # Check every 5 seconds


# CRITICAL RULE FOR CELSIUS AI:
# Before making ANY code changes, you MUST:
# 1. Create a detailed approval request using submit_request()
# 2. Wait for user approval using wait_for_approval()
# 3. ONLY proceed if approved
# 4. Log all changes made
#
# NO exceptions to this rule. User has final authority on ALL code modifications.
