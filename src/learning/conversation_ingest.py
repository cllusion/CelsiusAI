"""
Conversation ingestion for opt-in training.

Provides simple sanitization (PII redaction) and storage of sanitized
conversation transcripts into a local sqlite database under data/.

This module is intentionally conservative: it redacts emails, phone
numbers, and simple SSN-like patterns, and stores only the sanitized text
with minimal metadata. Ingestion is opt-in only and the Hub must call
store_conversation() after explicit user consent.
"""

from pathlib import Path
import re
import sqlite3
from datetime import datetime
from typing import Optional, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "learning_conversations.db"


def _ensure_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            participants TEXT,
            source TEXT,
            sanitized_text TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def sanitize_text(text: str) -> str:
    """Sanitize text by redacting common PII patterns.

    Redactions:
    - Emails -> [REDACTED_EMAIL]
    - Phone numbers -> [REDACTED_PHONE]
    - SSN-like -> [REDACTED_SSN]
    - Very long numeric sequences -> [REDACTED]
    """
    if not text:
        return text

    # Email
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "[REDACTED_EMAIL]", text)

    # Phone numbers (very permissive)
    text = re.sub(r"(?:(?:\+?\d{1,3})?[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}", "[REDACTED_PHONE]", text)

    # SSN-like (XXX-XX-XXXX)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", text)

    # Long digit sequences
    text = re.sub(r"\b\d{8,}\b", "[REDACTED]", text)

    return text


def store_conversation(transcript: str, participants: Optional[str] = None, source: str = "hub") -> Dict[str, str]:
    """Sanitize and store the transcript. Returns a small dict with status.

    This function is synchronous and safe to call from the Hub's main thread.
    """
    try:
        _ensure_db()
        sanitized = sanitize_text(transcript)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO conversations (timestamp, participants, source, sanitized_text)
                       VALUES (?, ?, ?, ?)""",
            (ts, participants or "", source, sanitized),
        )
        conn.commit()
        conn.close()
        return {"status": "ok", "timestamp": ts}
    except Exception as e:
        return {"status": "error", "error": str(e)}
