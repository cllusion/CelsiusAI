"""
Archived duplicate of `src/utils/celsius_code_approval.py` moved to archive/dups during consolidation.
Keep for history; do not import from here in active code.
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import aiosqlite

logger = logging.getLogger(__name__)


class CelsiusCodeApprovalSystem:
    """
    Manages the lifecycle of code approval requests using an async SQLite backend.
    """

    def __init__(self, db_path: Path):
        self.db_path: Path = db_path
        self._lock = asyncio.Lock()

    async def initialize(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
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
                        submitted_at TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        reviewed_by TEXT,
                        reviewed_at TEXT,
                        review_comments TEXT,
                        formatted_submission TEXT
                    )
                """
                )
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS approval_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        performed_by TEXT,
                        performed_at TEXT NOT NULL,
                        comments TEXT,
                        FOREIGN KEY (request_id) REFERENCES approval_requests (request_id)
                    )
                """
                )
                await db.commit()
        logger.info(f"Archived code approval database initialized at {self.db_path}")
