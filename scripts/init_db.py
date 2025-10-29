#!/usr/bin/env python3
"""
Database and System Initialization Script for Celsius AI

This script performs the essential first-time setup for the Celsius AI system.
It creates the necessary directories, initializes the SQLite databases with the
correct schema, and seeds the database with default data, such as the admin user.
"""

import asyncio
import logging
import sqlite3
from pathlib import Path
import bcrypt
import sys
import os

# --- Configuration ---
# Configure logging for clear and informative output
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# Define the project's root directory relative to this script's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Define paths for essential directories and database files
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
BACKUPS_DIR = PROJECT_ROOT / "backups"
DATABASES = {
    "activity": DATA_DIR / "celsius_activity.db",
    "system": DATA_DIR / "celsius_system.db",
    "monitoring": DATA_DIR / "celsius_monitoring.db",
}

# --- Database Schema ---
# SQL statements to create the necessary tables for each database
SCHEMA = {
    "activity": [
        """
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            service TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS security_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT NOT NULL,
            username TEXT,
            ip_address TEXT,
            details TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ],
    "system": [
        """
        CREATE TABLE IF NOT EXISTS system_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            network_sent INTEGER,
            network_recv INTEGER
        );
        """
    ],
    "monitoring": [
        """
        CREATE TABLE IF NOT EXISTS monitoring_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            service_name TEXT NOT NULL,
            status TEXT NOT NULL,
            response_time REAL,
            details TEXT
        );
        """
    ],
}

# --- Default Data ---
# Default administrator credentials
DEFAULT_ADMIN_USER = "cllusion001"
DEFAULT_ADMIN_PASSWORD = "T3qy22ny*@dyu0ppn*pG"


def create_directories() -> None:
    """Create all necessary directories for the system to function."""
    logging.info("Creating system directories...")
    dirs_to_create = [DATA_DIR, LOGS_DIR, BACKUPS_DIR]
    for dir_path in dirs_to_create:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"  ✅ Directory ensured: {dir_path}")
        except OSError as e:
            logging.error(f"  ❌ Failed to create directory {dir_path}: {e}")
            raise


async def execute_sql(db_path: Path, sql: str, params: tuple = ()) -> None:
    """
    Asynchronously execute a single SQL statement on a given database.

    Args:
        db_path (Path): The path to the SQLite database file.
        sql (str): The SQL statement to execute.
        params (tuple): Optional parameters for the SQL statement.
    """
    try:
        # Use a synchronous connection in a separate thread for compatibility
        def db_operation():
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()

        await asyncio.to_thread(db_operation)
    except sqlite3.Error as e:
        logging.error(f"  ❌ SQL error in {db_path.name} for statement '{sql[:30]}...': {e}")
        raise


async def initialize_database(name: str, db_path: Path) -> None:
    """
    Initialize a single database, creating its schema.

    Args:
        name (str): The logical name of the database (e.g., 'activity').
        db_path (Path): The path to the database file.
    """
    logging.info(f"Initializing database: {name} at {db_path}...")
    if not db_path.exists():
        logging.info(f"  - Database file not found. Creating...")
        db_path.touch()

    if name in SCHEMA:
        for statement in SCHEMA[name]:
            await execute_sql(db_path, statement)
        logging.info(f"  ✅ Schema for '{name}' database created successfully.")
    else:
        logging.warning(f"  - No schema found for database '{name}'.")


async def seed_admin_user() -> None:
    """Seed the database with the default administrator account."""
    logging.info("Seeding default administrator user...")
    db_path = DATABASES["activity"]

    # Hash the password using bcrypt
    password_bytes = DEFAULT_ADMIN_PASSWORD.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    sql = """
    INSERT INTO users (username, hashed_password, role)
    VALUES (?, ?, 'admin')
    ON CONFLICT(username) DO NOTHING;
    """
    try:
        await execute_sql(db_path, sql, (DEFAULT_ADMIN_USER, hashed_password))
        logging.info("  ✅ Default admin user ensured.")
    except sqlite3.Error as e:
        logging.error(f"  ❌ Failed to seed admin user: {e}")


async def main() -> None:
    """Main entry point for the initialization script."""
    print("=" * 50)
    print("   Celsius AI System Initialization   ")
    print("=" * 50)

    try:
        # Step 1: Create directories
        create_directories()

        # Step 2: Initialize all databases concurrently
        init_tasks = [initialize_database(name, path) for name, path in DATABASES.items()]
        await asyncio.gather(*init_tasks)

        # Step 3: Seed the database with initial data
        await seed_admin_user()

        logging.info("=" * 50)
        logging.info("🎉 System initialization completed successfully! 🎉")
        logging.info("=" * 50)

    except Exception as e:
        logging.critical(f"💥 A critical error occurred during initialization: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
