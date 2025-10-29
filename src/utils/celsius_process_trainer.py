#!/usr/bin/env python3
"""
Celsius AI - Process Training & Grading System
==============================================

Description:
------------
This module provides an advanced system for monitoring, grading, and training
on the performance of system processes. It is a key component of Celsius AI's
self-learning capabilities, allowing the AI to understand how different
processes behave and how to manage them optimally.

Key Features:
-------------
- **Comprehensive Process Grading**: Assigns a detailed performance grade (0-100)
  to each running process based on multiple categories: efficiency, resource
  usage, stability, security, and power efficiency.
- **Asynchronous Monitoring**: Uses `asyncio` to run a continuous monitoring and
  grading loop in the background without blocking other system operations.
- **Persistent Storage**: All grading data and training summaries are stored in
  a SQLite database using `aiosqlite` for non-blocking I/O.
- **Safety Controls**: Implements strict safety protocols to prevent the system
  from grading or interfering with its own core processes or critical system
  processes.
- **Learning & Trend Analysis**: Tracks the performance of processes over time
  to identify trends, such as performance degradation or improvement.
- **Configurable**: Training parameters like grading thresholds and learning
  rates can be configured via a JSON file.

Usage:
------
The `CelsiusProcessTrainer` is designed to run as a background service. It is
initialized with a path to its database and then started.

    import asyncio
    from pathlib import Path
    from src.utils.celsius_process_trainer import CelsiusProcessTrainer

    async def main():
        db_path = Path("./data/celsius_system.db")
        trainer = CelsiusProcessTrainer(db_path)
        await trainer.initialize()

        # Start the background training task
        training_task = asyncio.create_task(trainer.start_training())

        print("Process trainer is running in the background.")
        # Let it run for a while
        await asyncio.sleep(300)

        # Stop the trainer
        await trainer.stop_training()
        await training_task
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Set

import aiosqlite
import psutil

logger = logging.getLogger(__name__)


class CelsiusProcessTrainer:
    """
    An advanced process training and grading system for Celsius AI to learn
    optimal system management.
    """

    def __init__(self, db_path: Path):
        """
        Initializes the process trainer.

        Args:
            db_path (Path): Path to the SQLite database for storing training data.
        """
        self.db_path: Path = db_path
        self.config_path: Path = self.db_path.parent / "training_config.json"
        self._is_running: bool = False
        self._training_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

        # --- Configurable Settings ---
        self.training_enabled: bool = True
        self.auto_grading_enabled: bool = True
        self.learning_rate: float = 0.1
        self.grade_threshold: int = 50  # Processes below this need attention.
        self.monitoring_interval: int = 60  # seconds

        # --- Safety Controls ---
        self.protected_processes: Set[str] = {
            "celsius_server_hub.py",
            "celsius_process_trainer.py",
            "celsius_collaborative_engine.py",
            "enhanced_mobile_dashboard.py",
        }
        self.system_critical_processes: Set[str] = {"system", "csrss.exe", "winlogon.exe", "lsass.exe", "svchost.exe"}

    async def initialize(self):
        """Initializes the database and loads configuration."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        await self._init_database()
        await self._load_config()

    async def _init_database(self):
        """Sets up the necessary SQLite tables."""
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS process_grades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    process_name TEXT NOT NULL,
                    pid INTEGER,
                    overall_grade INTEGER,
                    grade_details TEXT,
                    recommendations TEXT,
                    timestamp TEXT NOT NULL
                )
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS training_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_processes INTEGER,
                    low_grade_count INTEGER,
                    low_grade_processes TEXT
                )
            """
            )
            await db.commit()
        logger.info(f"Process trainer database initialized at {self.db_path}")

    async def _load_config(self):
        """Loads settings from the JSON config file."""
        async with self._lock:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                self.training_enabled = config.get("training_enabled", True)
                self.auto_grading_enabled = config.get("auto_grading_enabled", True)
                self.learning_rate = config.get("learning_rate", 0.1)
                self.grade_threshold = config.get("grade_threshold", 50)
            else:
                await self._save_config()

    async def _save_config(self):
        """Saves the current settings to the JSON config file."""
        config = {
            "training_enabled": self.training_enabled,
            "auto_grading_enabled": self.auto_grading_enabled,
            "learning_rate": self.learning_rate,
            "grade_threshold": self.grade_threshold,
            "last_updated": datetime.now().isoformat(),
        }
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)

    async def grade_process(self, process: psutil.Process) -> Dict[str, Any]:
        """
        Assigns a comprehensive performance grade to a single process.

        Returns:
            A dictionary containing detailed grades and an overall score.
        """
        grades = {"overall": 50, "efficiency": 50, "resource": 50, "stability": 50}
        try:
            with process.oneshot():
                cpu = process.cpu_percent()
                mem = process.memory_info()

                # Efficiency Grade (lower is better)
                cpu_score = 100 - (cpu * 1.5)
                mem_score = 100 - (mem.rss / (1024**2) * 0.1)  # Penalize per MB
                grades["efficiency"] = max(0, min(100, (cpu_score + mem_score) / 2))

                # Resource Grade (similar to efficiency but harsher penalties)
                grades["resource"] = max(0, min(100, 100 - (cpu / 10) - (mem.rss / (1024**2) / 50)))

                # Stability Grade (older process is more stable)
                age_hours = (datetime.now().timestamp() - process.create_time()) / 3600
                grades["stability"] = min(100, 50 + (age_hours * 5))

            # Overall weighted grade
            grades["overall"] = int(grades["efficiency"] * 0.4 + grades["resource"] * 0.3 + grades["stability"] * 0.3)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.debug(f"Could not grade process {process.pid}: {e}")
            return {k: 0 for k in grades}
        return grades

    async def _training_loop(self):
        """The main loop for continuously training on all system processes."""
        while self._is_running:
            if not self.training_enabled or not self.auto_grading_enabled:
                await asyncio.sleep(self.monitoring_interval)
                continue

            logger.info("Starting new process training cycle...")
            process_count = 0
            low_grade_processes = []

            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    proc_name = proc.info.get("name", "").lower()
                    cmdline = " ".join(proc.info.get("cmdline") or [])

                    is_protected = any(p in proc_name or p in cmdline for p in self.protected_processes)
                    is_critical = any(c in proc_name for c in self.system_critical_processes)

                    if is_protected or is_critical:
                        continue

                    grades = await self.grade_process(proc)
                    await self._store_process_grade(proc_name, proc.pid, grades)

                    if grades["overall"] < self.grade_threshold:
                        low_grade_processes.append({"name": proc_name, "pid": proc.pid, "grade": grades["overall"]})
                    process_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                except Exception as e:
                    logger.error(f"Error grading process {proc.pid}: {e}", exc_info=True)

            await self._store_training_summary(process_count, low_grade_processes)
            logger.info(f"Training cycle complete. Graded {process_count} processes.")
            await asyncio.sleep(self.monitoring_interval)

    async def _store_process_grade(self, name: str, pid: int, grades: Dict[str, Any]):
        """Stores the grading results for a process in the database."""
        recommendations = self._generate_recommendations(grades, name)
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO process_grades
                (process_name, pid, overall_grade, grade_details, recommendations, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    pid,
                    grades["overall"],
                    json.dumps(grades),
                    json.dumps(recommendations),
                    datetime.now().isoformat(),
                ),
            )
            await db.commit()

    def _generate_recommendations(self, grades: Dict[str, Any], name: str) -> List[str]:
        """Generates human-readable recommendations based on process grades."""
        recs = []
        if grades["overall"] < self.grade_threshold:
            recs.append(f"Overall performance is low. Consider optimizing or restarting '{name}'.")
        if grades["efficiency"] < 50:
            recs.append(f"'{name}' is running inefficiently. Check for high CPU or memory usage.")
        if grades["resource"] < 50:
            recs.append(f"'{name}' is consuming excessive resources.")
        return recs

    async def _store_training_summary(self, count: int, low_grades: List[Dict]):
        """Stores a summary of a training cycle in the database."""
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO training_summaries
                (timestamp, total_processes, low_grade_count, low_grade_processes)
                VALUES (?, ?, ?, ?)
                """,
                (datetime.now().isoformat(), count, len(low_grades), json.dumps(low_grades)),
            )
            await db.commit()

    async def start_training(self):
        """Starts the background process training task."""
        if self._is_running:
            logger.warning("Process training is already running.")
            return

        logger.info("Starting Celsius AI Process Training System.")
        self._is_running = True
        self._training_task = asyncio.create_task(self._training_loop())

    async def stop_training(self):
        """Stops the background process training task gracefully."""
        if not self._is_running or not self._training_task:
            logger.info("Process training is not running.")
            return

        logger.info("Stopping Celsius AI Process Training.")
        self._is_running = False
        self._training_task.cancel()
        try:
            await self._training_task
        except asyncio.CancelledError:
            pass  # Expected cancellation
        await self._save_config()
        logger.info("Process training stopped.")
