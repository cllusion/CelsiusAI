"""
Database schema versioning and migration utilities for Celsius AI.

Usage
-----
from src.utils.db_migrations import MigrationRunner, Migration

runner = MigrationRunner("data/mydb.db")
runner.register(Migration(version=1, description="initial schema", sql=CREATE_TABLE_SQL))
runner.run()

Each database should create its own MigrationRunner with the relevant migrations
registered in version order. Migrations are applied in ascending version order and
are idempotent — already-applied migrations are skipped.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS _schema_version (
    version     INTEGER NOT NULL,
    description TEXT,
    applied_at  DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""


@dataclass
class Migration:
    """A single schema migration step."""

    version: int
    description: str
    # Either sql string(s) or a callable that receives a sqlite3.Connection
    sql: str | list[str] = field(default="")
    fn: Callable[[sqlite3.Connection], None] | None = field(default=None)


class MigrationRunner:
    """Applies pending migrations to a SQLite database."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._migrations: list[Migration] = []

    def register(self, migration: Migration) -> "MigrationRunner":
        """Register a migration. Returns self for chaining."""
        self._migrations.append(migration)
        return self

    def register_many(self, migrations: list[Migration]) -> "MigrationRunner":
        self._migrations.extend(migrations)
        return self

    def _current_version(self, conn: sqlite3.Connection) -> int:
        conn.execute(_SCHEMA_VERSION_TABLE)
        row = conn.execute("SELECT MAX(version) FROM _schema_version").fetchone()
        return row[0] if row and row[0] is not None else 0

    def run(self) -> int:
        """Apply all pending migrations. Returns number of migrations applied."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        pending = sorted(self._migrations, key=lambda m: m.version)

        applied = 0
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            current = self._current_version(conn)

            for migration in pending:
                if migration.version <= current:
                    continue

                logger.info(
                    "Applying migration v%d to %s: %s",
                    migration.version,
                    self.db_path.name,
                    migration.description,
                )
                try:
                    if migration.fn is not None:
                        migration.fn(conn)
                    else:
                        statements = (
                            migration.sql
                            if isinstance(migration.sql, list)
                            else [migration.sql]
                        )
                        for stmt in statements:
                            if stmt.strip():
                                conn.execute(stmt)

                    conn.execute(
                        "INSERT INTO _schema_version (version, description) VALUES (?, ?)",
                        (migration.version, migration.description),
                    )
                    conn.commit()
                    applied += 1
                    logger.info("Migration v%d applied successfully.", migration.version)

                except Exception:
                    conn.rollback()
                    logger.exception(
                        "Migration v%d failed — rolling back.", migration.version
                    )
                    raise

        return applied


# ---------------------------------------------------------------------------
# Pre-defined migration sets for each Celsius AI database
# ---------------------------------------------------------------------------

def get_hub_migrations() -> list[Migration]:
    """Schema migrations for the main hub (celsius_activity.db)."""
    return [
        Migration(
            version=1,
            description="initial hub tables",
            sql=[
                """CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    service TEXT,
                    action TEXT,
                    details TEXT,
                    status TEXT
                )""",
                """CREATE TABLE IF NOT EXISTS system_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )""",
            ],
        ),
        Migration(
            version=2,
            description="add index on activity_log timestamp",
            sql="CREATE INDEX IF NOT EXISTS idx_activity_log_ts ON activity_log(timestamp)",
        ),
    ]


def get_guardian_migrations() -> list[Migration]:
    """Schema migrations for celsius_guardian.db."""
    return [
        Migration(
            version=1,
            description="initial guardian tables",
            sql=[
                """CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    source TEXT,
                    details TEXT,
                    severity TEXT DEFAULT 'info',
                    resolved INTEGER DEFAULT 0
                )""",
                """CREATE TABLE IF NOT EXISTS blocked_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT UNIQUE,
                    reason TEXT,
                    blocked_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )""",
            ],
        ),
    ]


def get_learning_migrations() -> list[Migration]:
    """Schema migrations for the learning database."""
    return [
        Migration(
            version=1,
            description="initial learning tables",
            sql=[
                """CREATE TABLE IF NOT EXISTS learning_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,
                    title TEXT,
                    content TEXT,
                    processed INTEGER DEFAULT 0,
                    quality_score REAL
                )""",
                """CREATE TABLE IF NOT EXISTS learning_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ended_at DATETIME,
                    items_processed INTEGER DEFAULT 0,
                    summary TEXT
                )""",
            ],
        ),
        Migration(
            version=2,
            description="add full-text search index on learning_items",
            sql="CREATE INDEX IF NOT EXISTS idx_learning_items_source ON learning_items(source)",
        ),
    ]


def get_self_improvement_migrations() -> list[Migration]:
    """Schema migrations for self_improvement.db."""
    return [
        Migration(
            version=1,
            description="initial self-improvement tables",
            sql=[
                """CREATE TABLE IF NOT EXISTS improvements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    file_path TEXT NOT NULL,
                    improvement_type TEXT NOT NULL,
                    description TEXT,
                    source_insight TEXT,
                    code_before TEXT,
                    code_after TEXT,
                    status TEXT DEFAULT 'pending',
                    confidence_score REAL,
                    applied_timestamp DATETIME,
                    rollback_info TEXT
                )""",
                """CREATE TABLE IF NOT EXISTS learning_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    insights_analyzed INTEGER,
                    improvements_identified INTEGER,
                    improvements_applied INTEGER,
                    analysis_summary TEXT
                )""",
            ],
        ),
        Migration(
            version=2,
            description="add test_passed column to track safety gate results",
            sql="ALTER TABLE improvements ADD COLUMN test_passed INTEGER DEFAULT NULL",
        ),
    ]


def apply_all_migrations(data_dir: str | Path = "data") -> None:
    """Convenience function to apply migrations to all known databases.

    Call once at application startup before any database access.
    """
    data_dir = Path(data_dir)

    runners = [
        (MigrationRunner(data_dir / "celsius_activity.db"), get_hub_migrations()),
        (MigrationRunner(data_dir / "celsius_guardian.db"), get_guardian_migrations()),
        (MigrationRunner(data_dir / "learning.db"), get_learning_migrations()),
        (MigrationRunner(data_dir / "self_improvement.db"), get_self_improvement_migrations()),
    ]

    for runner, migrations in runners:
        runner.register_many(migrations)
        try:
            n = runner.run()
            if n:
                logger.info("Applied %d migration(s) to %s", n, runner.db_path.name)
        except Exception:
            logger.exception("Failed to migrate %s", runner.db_path.name)
