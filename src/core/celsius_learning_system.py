#!/usr/bin/env python3
"""
Celsius AI Autonomous Learning System
======================================
Celsius AI continuously monitors all system processes and learns from them.
This system allows Celsius to:
- Learn from system behaviors
- Monitor all processes (Defender, Guardian, Hub, Dashboard, etc.)
- Identify patterns and improvements
- Request code changes (requires user approval)
- Optimize system performance
- Adapt to user preferences

LEARNING SCOPE: Unlimited and autonomous
CODE CHANGES: Requires explicit user approval via Code Approval System
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import psutil
import aiosqlite
import json

# Project setup
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOGS_DIR / "celsius_learning.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class CelsiusLearningSystem:
    """
    Autonomous learning system for Celsius AI.
    Monitors all processes, learns patterns, and suggests improvements.
    """

    def __init__(self):
        self.db_path = DATA_DIR / "celsius_learning.db"
        self.is_running = False

        # Learning data
        self.process_patterns: Dict[str, List[Dict]] = {}
        self.performance_metrics: Dict[str, List[float]] = {}
        self.user_interactions: List[Dict] = []
        self.system_events: List[Dict] = []

        # Monitoring targets
        self.monitored_processes = [
            "celsius_realtime_defender.py",
            "celsius_ultimate_guardian.py",
            "celsius_ultimate_hub.py",
            "enhanced_mobile_dashboard.py",
            "main.py",  # Core AI
            "celsius_web_learning_launcher.py",
            "celsius_hourly_reporter.py",
        ]

    async def initialize(self):
        """Initialize learning database and systems"""
        async with aiosqlite.connect(self.db_path) as db:
            # Learning observations table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS learning_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    observation_type TEXT NOT NULL,
                    source_process TEXT,
                    data TEXT NOT NULL,
                    insights TEXT,
                    confidence_score REAL
                )
            """
            )

            # Performance metrics table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    process_name TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_mb REAL,
                    response_time_ms REAL,
                    health_status TEXT
                )
            """
            )

            # Improvement suggestions table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS improvement_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    suggestion TEXT NOT NULL,
                    expected_benefit TEXT,
                    implementation_complexity TEXT,
                    approval_request_id TEXT
                )
            """
            )

            await db.commit()

        logger.info("[LEARNING] Celsius AI Learning System initialized")
        logger.info("[LEARNING] Monitoring processes: %s", ", ".join(self.monitored_processes))

    async def monitor_processes(self):
        """Continuously monitor all Celsius processes and learn from them"""
        while self.is_running:
            try:
                observations = []

                for proc in psutil.process_iter(["pid", "name", "cmdline", "cpu_percent", "memory_info"]):
                    try:
                        cmdline = proc.info.get("cmdline", [])
                        if not cmdline:
                            continue

                        # Check if this is a Celsius process
                        cmdline_str = " ".join(cmdline)
                        for target in self.monitored_processes:
                            if target in cmdline_str:
                                # Collect metrics
                                cpu = proc.cpu_percent(interval=0.1)
                                memory_mb = proc.info["memory_info"].rss / 1024 / 1024

                                observation = {
                                    "timestamp": datetime.now().isoformat(),
                                    "process": target,
                                    "pid": proc.info["pid"],
                                    "cpu_percent": cpu,
                                    "memory_mb": memory_mb,
                                    "status": "running",
                                }

                                observations.append(observation)

                                # Log to database
                                await self.log_performance_metric(
                                    process_name=target,
                                    cpu_percent=cpu,
                                    memory_mb=memory_mb,
                                    health_status="healthy" if cpu < 80 else "high_cpu",
                                )

                                # Learn from patterns
                                await self.analyze_process_behavior(observation)

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # Log learning cycle
                if observations:
                    await self.log_observation(
                        observation_type="process_monitoring",
                        data=json.dumps(observations),
                        insights=f"Monitored {len(observations)} Celsius processes",
                    )

                await asyncio.sleep(30)  # Monitor every 30 seconds

            except Exception as e:
                logger.error(f"[LEARNING] Error in process monitoring: {e}")
                await asyncio.sleep(30)

    async def analyze_process_behavior(self, observation: Dict[str, Any]):
        """
        Analyze a process observation and learn patterns.
        This is where Celsius AI learns from system behavior.
        """
        process = observation["process"]
        cpu = observation["cpu_percent"]
        memory = observation["memory_mb"]

        # Track patterns
        if process not in self.process_patterns:
            self.process_patterns[process] = []
        self.process_patterns[process].append(observation)

        # Keep only recent observations (last 1000)
        if len(self.process_patterns[process]) > 1000:
            self.process_patterns[process] = self.process_patterns[process][-1000:]

        # Analyze for anomalies or improvements
        if len(self.process_patterns[process]) > 10:
            recent = self.process_patterns[process][-10:]
            avg_cpu = sum(o["cpu_percent"] for o in recent) / len(recent)
            avg_mem = sum(o["memory_mb"] for o in recent) / len(recent)

            # Detect high resource usage
            if avg_cpu > 50:
                insight = f"{process} showing high CPU usage (avg {avg_cpu:.1f}%)"
                await self.log_observation(
                    observation_type="performance_concern",
                    source_process=process,
                    data=json.dumps({"avg_cpu": avg_cpu, "avg_memory": avg_mem}),
                    insights=insight,
                    confidence_score=0.8,
                )

                # Suggest optimization (this would trigger code approval request)
                await self.suggest_improvement(
                    category="performance",
                    suggestion=f"Optimize {process} to reduce CPU usage from {avg_cpu:.1f}%",
                    expected_benefit=f"Reduce system load by ~{avg_cpu - 10:.0f}%",
                    implementation_complexity="medium",
                )

    async def log_observation(
        self,
        observation_type: str,
        data: str,
        source_process: str = None,
        insights: str = None,
        confidence_score: float = 1.0,
    ):
        """Log a learning observation to database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO learning_observations
                (timestamp, observation_type, source_process, data, insights, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (datetime.now().isoformat(), observation_type, source_process, data, insights, confidence_score),
            )
            await db.commit()

    async def log_performance_metric(
        self,
        process_name: str,
        cpu_percent: float,
        memory_mb: float,
        health_status: str,
        response_time_ms: float = None,
    ):
        """Log performance metrics for analysis"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO performance_metrics
                (timestamp, process_name, cpu_percent, memory_mb, response_time_ms, health_status)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (datetime.now().isoformat(), process_name, cpu_percent, memory_mb, response_time_ms, health_status),
            )
            await db.commit()

    async def suggest_improvement(
        self, category: str, suggestion: str, expected_benefit: str, implementation_complexity: str
    ):
        """
        Suggest an improvement to the system.
        This will be reviewed and may result in a code approval request.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO improvement_suggestions
                (timestamp, category, suggestion, expected_benefit, implementation_complexity)
                VALUES (?, ?, ?, ?, ?)
            """,
                (datetime.now().isoformat(), category, suggestion, expected_benefit, implementation_complexity),
            )
            await db.commit()

        logger.info(f"[LEARNING] Improvement suggested: {suggestion}")

    async def get_learning_insights(self, hours: int = 24) -> Dict[str, Any]:
        """Get learning insights from the past N hours"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get recent observations
            async with db.execute(
                """
                SELECT observation_type, COUNT(*) as count
                FROM learning_observations
                WHERE datetime(timestamp) > datetime('now', '-' || ? || ' hours')
                GROUP BY observation_type
            """,
                (hours,),
            ) as cursor:
                observations = await cursor.fetchall()

            # Get performance trends
            async with db.execute(
                """
                SELECT process_name, AVG(cpu_percent) as avg_cpu, AVG(memory_mb) as avg_memory
                FROM performance_metrics
                WHERE datetime(timestamp) > datetime('now', '-' || ? || ' hours')
                GROUP BY process_name
            """,
                (hours,),
            ) as cursor:
                performance = await cursor.fetchall()

            # Get suggestions
            async with db.execute(
                """
                SELECT category, suggestion, expected_benefit
                FROM improvement_suggestions
                WHERE datetime(timestamp) > datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp DESC
                LIMIT 10
            """,
                (hours,),
            ) as cursor:
                suggestions = await cursor.fetchall()

            return {
                "observations": dict(observations),
                "performance": {p[0]: {"cpu": p[1], "memory": p[2]} for p in performance},
                "suggestions": [{"category": s[0], "suggestion": s[1], "benefit": s[2]} for s in suggestions],
            }

    async def run(self):
        """Main learning loop"""
        self.is_running = True
        await self.initialize()

        # Start monitoring tasks
        monitoring_task = asyncio.create_task(self.monitor_processes())

        logger.info("[LEARNING] Celsius AI autonomous learning active")
        logger.info("[LEARNING] Learning without interruption - monitoring all processes")

        try:
            while self.is_running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("[LEARNING] Learning system shutdown requested")
        finally:
            monitoring_task.cancel()
            logger.info("[LEARNING] Celsius AI learning system stopped")


# CELSIUS AI RULES:
# 1. LEARNING: Autonomous and continuous - no approval needed
# 2. MONITORING: All processes, all the time
# 3. INSIGHTS: Generate freely based on observations
# 4. SUGGESTIONS: Create improvement suggestions as needed
# 5. CODE CHANGES: MUST request approval via Code Approval System
# 6. CONTROL: Celsius AI, Defender, Guardian keep running unless user stops via Hub
