"""
AI-to-AI training queue module.

This module provides a safe, opt-in queue for storing multi-AI conversation
transcripts for later human review and ingestion into the learning system.

Workflow:
- submit_conversation_for_training(...) -> stores transcript with status 'pending'
- list_pending() -> list pending items
- approve_item(item_id) -> sanitize and move to learning_conversations DB via conversation_ingest
- reject_item(item_id) -> mark as rejected or delete

Automated training should only run on approved items after manual review.
"""

from pathlib import Path
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "ai_training.db"


def _ensure_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_training (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            participants TEXT,
            source TEXT,
            raw_text TEXT,
            status TEXT DEFAULT 'pending',
            processed_at DATETIME
        )
    """
    )
    conn.commit()
    conn.close()


def submit_conversation_for_training(
    raw_text: str, participants: Optional[str] = None, source: str = "external"
) -> Dict[str, str]:
    """Submit a conversation transcript for human review and training ingestion."""
    try:
        _ensure_db()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO ai_training (timestamp, participants, source, raw_text) VALUES (?, ?, ?, ?)""",
            (ts, participants or "", source, raw_text),
        )
        conn.commit()
        rowid = cur.lastrowid
        conn.close()
        return {"status": "ok", "id": rowid}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def list_pending(limit: int = 50) -> List[Dict]:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, timestamp, participants, source, raw_text FROM ai_training WHERE status = 'pending' ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "timestamp": r[1], "participants": r[2], "source": r[3], "raw_text": r[4]} for r in rows]


def approve_item(item_id: int) -> Dict[str, str]:
    """Approve and process an item: sanitize and move to learning_conversations DB.

    Returns status dict.
    """
    try:
        _ensure_db()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT raw_text, participants FROM ai_training WHERE id = ? AND status = ?", (item_id, "pending"))
        row = cur.fetchone()
        if not row:
            conn.close()
            return {"status": "error", "error": "Not found or already processed"}

        raw_text, participants = row[0], row[1]
        conn.close()

        # Use conversation_ingest to sanitize & store
        from src.learning.conversation_ingest import store_conversation

        resp = store_conversation(raw_text, participants=participants, source="ai_to_ai")
        if resp.get("status") != "ok":
            return {"status": "error", "error": resp.get("error")}

        # Mark as approved
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "UPDATE ai_training SET status = 'approved', processed_at = ? WHERE id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item_id),
        )
        conn.commit()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def reject_item(item_id: int) -> Dict[str, str]:
    try:
        _ensure_db()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "UPDATE ai_training SET status = 'rejected', processed_at = ? WHERE id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item_id),
        )
        conn.commit()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
