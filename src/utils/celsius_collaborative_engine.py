"""
Celsius AI - Collaborative Improvement & Code Analysis Engine
=============================================================

Description:
------------
This module provides the core engine for Celsius AI's self-improvement
capabilities. It is designed to analyze the project's codebase, identify
potential areas for improvement (such as performance, security, and code
quality), and generate suggested code changes.

Crucially, this engine operates under a strict safety protocol: it can
propose changes, but it can NEVER approve or apply them itself. All proposed
changes must be submitted to the `CelsiusCodeApprovalSystem` and be manually
reviewed and approved by a human user.

Key Features:
-------------
- **Automated Code Analysis**: Scans Python files to find common issues related
  to performance, security, error handling, and code quality using AST (Abstract
  Syntax Tree) parsing and regex.
- **Suggestion Generation**: Based on analysis findings, it can generate
  potential code modifications to address the identified issues.
- **Strict Safety Controls**: A multi-layered protection system prevents the
  engine from analyzing or modifying critical system files, its own source code,
  or any other file designated as protected.
- **Integration with Approval System**: All generated code improvements are
  automatically submitted as formal requests to the `CelsiusCodeApprovalSystem`.
- **Persistent Storage**: Analysis results and proposed improvements are logged
  in a SQLite database for tracking and auditing, using `aiosqlite` for async
  operations.
- **Configurable**: Analysis features can be enabled or disabled via a JSON
  configuration file.

Usage:
------
The engine is designed to run as a background service. It is initialized with
paths to the project's source code and a data directory.

    import asyncio
    from pathlib import Path
    from src.utils.celsius_code_approval import CelsiusCodeApprovalSystem
    from src.utils.celsius_collaborative_engine import CelsiusCollaborativeEngine

    async def main():
        project_root = Path("./src")
        data_path = Path("./data")
        db_path = data_path / "celsius_system.db"
        approval_db_path = data_path / "approvals.db"

        approval_system = CelsiusCodeApprovalSystem(approval_db_path)
        await approval_system.initialize()

        engine = CelsiusCollaborativeEngine(project_root, db_path, approval_system)
        await engine.initialize()

        # Start the continuous analysis loop as a background task
        analysis_task = asyncio.create_task(engine.start_continuous_analysis())

        # The engine will now run in the background.
        # To stop it:
        # await engine.stop_continuous_analysis()
        # await analysis_task
"""

import asyncio
import ast
import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import aiosqlite

try:
    from src.core.celsius_code_approval_system import CelsiusCodeApprovalSystem
except Exception:
    # Fallback for older installations that still ship the utils adaptor
    from src.utils.celsius_code_approval import CelsiusCodeApprovalSystem

logger = logging.getLogger(__name__)


class CelsiusCollaborativeEngine:
    """
    Analyzes code for improvements and generates suggestions for user approval.
    Operates under strict safety controls, preventing self-modification or auto-approval.
    """

    def __init__(self, project_root: Path, db_path: Path, approval_system: CelsiusCodeApprovalSystem):
        """
        Initializes the collaborative engine.

        Args:
            project_root (Path): The root directory of the source code to analyze.
            db_path (Path): Path to the SQLite database for storing analysis results.
            approval_system (CelsiusCodeApprovalSystem): The system for submitting change requests.
        """
        self.project_root: Path = project_root
        self.db_path: Path = db_path
        self.approval_system: CelsiusCodeApprovalSystem = approval_system
        self.config_path: Path = self.db_path.parent / "improvement_config.json"
        self._lock = asyncio.Lock()
        self._is_running = False
        self._analysis_task: Optional[asyncio.Task] = None

        # --- Configuration ---
        self.analysis_enabled: bool = True
        self.suggestion_generation_enabled: bool = True

        # --- Safety Controls ---
        # Files this engine can NEVER propose changes for.
        self.protected_files: set = {
            "celsius_collaborative_engine.py",  # Cannot modify itself.
            "celsius_code_approval.py",  # Cannot modify the approval system.
            "celsius_auth.py",  # Cannot modify the authentication system.
        }

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
                CREATE TABLE IF NOT EXISTS code_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    findings TEXT,
                    timestamp TEXT NOT NULL
                )
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS safety_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    file_path TEXT,
                    details TEXT,
                    timestamp TEXT NOT NULL
                )
            """
            )
            await db.commit()
        logger.info(f"Collaborative engine database initialized at {self.db_path}")

    async def _load_config(self):
        """Loads configuration from a JSON file."""
        async with self._lock:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                self.analysis_enabled = config.get("analysis_enabled", True)
                self.suggestion_generation_enabled = config.get("suggestion_generation_enabled", True)
            else:
                await self._save_config()

    async def _save_config(self):
        """Saves the current configuration to a JSON file."""
        config = {
            "analysis_enabled": self.analysis_enabled,
            "suggestion_generation_enabled": self.suggestion_generation_enabled,
            "last_updated": datetime.now().isoformat(),
        }
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)

    async def _log_safety_audit(self, action: str, file_path: str, details: str):
        """Logs a safety-related event to the audit log."""
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO safety_audit_log (action_type, file_path, details, timestamp) VALUES (?, ?, ?, ?)",
                (action, file_path, details, datetime.now().isoformat()),
            )
            await db.commit()

    def is_file_protected(self, file_path: Path) -> bool:
        """Checks if a file is protected from analysis or modification."""
        return file_path.name in self.protected_files

    async def analyze_codebase(self) -> List[Dict[str, Any]]:
        """
        Analyzes all Python files in the project root for potential improvements.

        Returns:
            A list of all findings across all analyzed files.
        """
        all_findings = []
        for file_path in self.project_root.rglob("*.py"):
            if self.is_file_protected(file_path):
                logger.warning(f"Skipping analysis of protected file: {file_path.name}")
                await self._log_safety_audit("analysis_skipped", str(file_path), "File is protected.")
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()

                findings = self._analyze_code_content(code, str(file_path))
                if findings:
                    all_findings.extend(findings)
                    await self._store_analysis_results(str(file_path), findings)

            except Exception as e:
                logger.error(f"Failed to analyze file {file_path}: {e}", exc_info=True)

        return all_findings

    def _analyze_code_content(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Performs various analyses on a string of Python code.
        """
        findings = []
        try:
            tree = ast.parse(code)
            # Example analysis: find bare 'except:' clauses
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    findings.append(
                        {
                            "type": "error_handling",
                            "category": "bare_except",
                            "file_path": file_path,
                            "line_number": node.lineno,
                            "description": "Bare 'except:' clause catches all exceptions, including system-exiting ones.",
                            "priority": 3,
                        }
                    )
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}, skipping AST analysis: {e}")

        # Example analysis: find hardcoded passwords (simple regex)
        password_pattern = re.compile(r"['\"](password|secret|token)['\"]\s*[:=]\s*['\"].+['\"]", re.IGNORECASE)
        for i, line in enumerate(code.splitlines()):
            if password_pattern.search(line):
                findings.append(
                    {
                        "type": "security",
                        "category": "hardcoded_credentials",
                        "file_path": file_path,
                        "line_number": i + 1,
                        "description": "Potential hardcoded credential found.",
                        "priority": 4,
                    }
                )
        return findings

    async def _store_analysis_results(self, file_path: str, findings: List[Dict[str, Any]]):
        """Stores the results of a file analysis in the database."""
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO code_analysis (file_path, analysis_type, findings, timestamp) VALUES (?, ?, ?, ?)",
                (file_path, "collaborative_engine", json.dumps(findings), datetime.now().isoformat()),
            )
            await db.commit()

    async def generate_and_submit_suggestions(self, findings: List[Dict[str, Any]]):
        """
        Generates improvement suggestions from findings and submits them for approval.
        """
        if not self.suggestion_generation_enabled:
            logger.info("Suggestion generation is disabled. Skipping.")
            return

        for finding in findings:
            file_path = Path(finding["file_path"])
            if self.is_file_protected(file_path):
                logger.warning(f"Skipping suggestion for protected file: {file_path.name}")
                await self._log_safety_audit("suggestion_skipped", str(file_path), "File is protected.")
                continue

            # This is where more sophisticated suggestion logic would go.
            # For now, we'll create a basic suggestion.
            original_code = file_path.read_text()
            proposed_code = self._generate_proposed_code(original_code, finding)

            if proposed_code and proposed_code != original_code:
                await self.approval_system.submit_request(
                    title=f"Fix for {finding['category']} in {file_path.name}",
                    description=finding["description"],
                    file_path=str(file_path),
                    original_code=original_code,
                    proposed_code=proposed_code,
                    change_type=finding["type"],
                    priority=finding.get("priority", 1),
                )
                logger.info(f"Submitted suggestion for {finding['category']} in {file_path.name}")

    def _generate_proposed_code(self, original_code: str, finding: Dict[str, Any]) -> Optional[str]:
        """
        Generates a proposed code change for a given finding.
        This is a simplified example.
        """
        if finding["category"] == "bare_except":
            lines = original_code.splitlines()
            line_index = finding["line_number"] - 1
            if "except:" in lines[line_index]:
                lines[line_index] = lines[line_index].replace(
                    "except:", "except Exception as e:  # TODO: Specify exception"
                )
                return "\n".join(lines)
        return None

    async def _continuous_analysis_loop(self):
        """The main loop for continuous background analysis."""
        while self._is_running:
            if self.analysis_enabled:
                logger.info("Starting collaborative analysis cycle...")
                try:
                    findings = await self.analyze_codebase()
                    if findings:
                        await self.generate_and_submit_suggestions(findings)
                    logger.info("Collaborative analysis cycle complete.")
                except Exception as e:
                    logger.error(f"Error in continuous analysis loop: {e}", exc_info=True)

            # Wait for the next cycle
            await asyncio.sleep(3600)  # Analyze once per hour

    async def start_continuous_analysis(self):
        """Starts the background analysis task."""
        if self._is_running:
            logger.warning("Continuous analysis is already running.")
            return

        logger.info("Starting Celsius AI Collaborative Improvement Engine in the background.")
        self._is_running = True
        self._analysis_task = asyncio.create_task(self._continuous_analysis_loop())

    async def stop_continuous_analysis(self):
        """Stops the background analysis task gracefully."""
        if not self._is_running or not self._analysis_task:
            logger.info("Continuous analysis is not running.")
            return

        logger.info("Stopping Celsius AI Collaborative Improvement Engine.")
        self._is_running = False
        self._analysis_task.cancel()
        try:
            await self._analysis_task
        except asyncio.CancelledError:
            logger.info("Analysis task successfully cancelled.")
        self._analysis_task = None
