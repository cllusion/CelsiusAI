"""
Authorization Manager

Provides safe, admin-only storage and review for uploaded authorization forms.
This module only stores files and metadata and provides an approve/reject audit
trail. It does NOT perform any automated actions or testing.
"""

from pathlib import Path
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
AUTH_DIR = DATA_DIR / "authorizations"
DB_PATH = DATA_DIR / "authorizations.db"


def _ensure_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS authorizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            uploader TEXT,
            filename TEXT,
            stored_path TEXT,
            status TEXT,
            notes TEXT
        )
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS authorization_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auth_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            actor TEXT,
            timestamp DATETIME NOT NULL,
            comment TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def save_authorization(source_path: str, uploader: Optional[str] = None) -> Dict[str, str]:
    """Save uploaded file into data/authorizations and record metadata.

    Returns a dict with status and id/timestamp.
    """
    try:
        _ensure_db()
        src = Path(source_path)
        if not src.exists():
            return {"status": "error", "error": "file not found"}
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{ts}_{src.name}"
        dest = AUTH_DIR / safe_name
        shutil.copy2(str(src), str(dest))

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """INSERT INTO authorizations (timestamp, uploader, filename, stored_path, status, notes)
                       VALUES (?, ?, ?, ?, ?, ?)""",
            (now, uploader or "", src.name, str(dest), "pending", ""),
        )
        aid = cur.lastrowid
        # audit entry
        cur.execute(
            """INSERT INTO authorization_audit (auth_id, action, actor, timestamp, comment)
                       VALUES (?, ?, ?, ?, ?)""",
            (aid, "uploaded", uploader or "", now, "uploaded"),
        )
        conn.commit()
        conn.close()
        return {"status": "ok", "id": aid, "timestamp": now}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def list_authorizations(limit: int = 200) -> List[Dict]:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """SELECT id, timestamp, uploader, filename, stored_path, status, notes FROM authorizations ORDER BY id DESC LIMIT ?""",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append(
            {
                "id": r[0],
                "timestamp": r[1],
                "uploader": r[2],
                "filename": r[3],
                "stored_path": r[4],
                "status": r[5],
                "notes": r[6],
            }
        )
    return result


def get_authorization(aid: int) -> Optional[Dict]:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """SELECT id, timestamp, uploader, filename, stored_path, status, notes FROM authorizations WHERE id = ?""",
        (aid,),
    )
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": r[0],
        "timestamp": r[1],
        "uploader": r[2],
        "filename": r[3],
        "stored_path": r[4],
        "status": r[5],
        "notes": r[6],
    }


def approve_authorization(aid: int, approver: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, str]:
    try:
        _ensure_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """UPDATE authorizations SET status = ?, notes = ? WHERE id = ?""", ("approved", comment or "", aid)
        )
        cur.execute(
            """INSERT INTO authorization_audit (auth_id, action, actor, timestamp, comment) VALUES (?, ?, ?, ?, ?)""",
            (aid, "approved", approver or "", now, comment or ""),
        )
        conn.commit()
        conn.close()
        return {"status": "ok", "id": aid, "timestamp": now}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def reject_authorization(aid: int, approver: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, str]:
    try:
        _ensure_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """UPDATE authorizations SET status = ?, notes = ? WHERE id = ?""", ("rejected", comment or "", aid)
        )
        cur.execute(
            """INSERT INTO authorization_audit (auth_id, action, actor, timestamp, comment) VALUES (?, ?, ?, ?, ?)""",
            (aid, "rejected", approver or "", now, comment or ""),
        )
        conn.commit()
        conn.close()
        return {"status": "ok", "id": aid, "timestamp": now}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def export_authorization(aid: int, dest_path: str) -> Dict[str, str]:
    """Copy the stored file to dest_path. dest_path can be a directory or full filename."""
    try:
        auth = get_authorization(aid)
        if not auth:
            return {"status": "error", "error": "not found"}
        src = Path(auth["stored_path"])
        if not src.exists():
            return {"status": "error", "error": "stored file missing"}
        dest = Path(dest_path)
        if dest.is_dir():
            dest = dest / src.name
        shutil.copy2(str(src), str(dest))
        return {"status": "ok", "path": str(dest)}
    except Exception as e:
        return {"status": "error", "error": str(e)}
