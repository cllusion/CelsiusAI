#!/usr/bin/env python3
"""
Celsius Self-Improvement System
Applies machine learning to automatically enhance system code and functionality
"""

import json
import ast
import sqlite3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging
import re
import shutil

try:
    from src.utils.code_safety_gate import CodeSafetyGate
    _SAFETY_GATE_AVAILABLE = True
except ImportError:
    _SAFETY_GATE_AVAILABLE = False


class SelfImprovementEngine:
    """
    Applies learning from web sources to automatically improve system code
    """

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.learning_reports_dir = self.project_root / "learning_reports"
        self.improvement_db = self.project_root / "data" / "self_improvement.db"
        self.backup_dir = self.project_root / "backups" / "self_improvement"
        self.config_file = self.project_root / "config" / "self_improvement_config.json"

        # Create directories
        self.improvement_db.parent.mkdir(exist_ok=True, parents=True)
        self.backup_dir.mkdir(exist_ok=True, parents=True)
        self.config_file.parent.mkdir(exist_ok=True, parents=True)

        self.setup_logging()
        self.load_configuration()
        self.setup_database()

    def setup_logging(self):
        """Setup logging for self-improvement"""
        log_file = self.project_root / "logs" / "self_improvement.log"
        log_file.parent.mkdir(exist_ok=True, parents=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
        )
        self.logger = logging.getLogger("SelfImprovement")

    def load_configuration(self):
        """Load self-improvement configuration"""
        default_config = {
            "auto_apply_improvements": False,  # Safety first - require approval
            "require_tests_pass_before_apply": True,  # Gate: tests must pass before any auto-apply
            "max_daily_changes": 3,
            "backup_before_changes": True,
            "learning_analysis_interval": 7200,  # 2 hours
            "code_quality_threshold": 0.8,
            "allowed_improvement_types": [
                "performance_optimization",
                "error_handling",
                "code_quality",
                "documentation",
                "logging",
                "security",
            ],
            "protected_files": ["celsius_ultimate_hub.py", "main.py"],
            "improvement_sources": ["learning_reports", "error_logs", "performance_metrics"],
        }

        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
        except Exception as e:
            self.logger.warning(f"Could not load config, using defaults: {e}")

        self.config = default_config
        self.save_configuration()

    def save_configuration(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")

    def setup_database(self):
        """Setup SQLite database for tracking improvements"""
        try:
            conn = sqlite3.connect(self.improvement_db)
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS improvements (
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
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS learning_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    insights_analyzed INTEGER,
                    improvements_identified INTEGER,
                    improvements_applied INTEGER,
                    analysis_summary TEXT
                )
            """
            )

            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Database setup failed: {e}")

    async def analyze_learning_for_improvements(self) -> List[Dict[str, Any]]:
        """Analyze learning reports for code improvement opportunities"""
        improvements = []

        if not self.learning_reports_dir.exists():
            self.logger.warning("Learning reports directory not found")
            return improvements

        # Get recent learning reports
        report_files = list(self.learning_reports_dir.glob("*.json"))
        if not report_files:
            self.logger.info("No learning reports found")
            return improvements

        # Analyze reports for improvement insights
        for report_file in sorted(report_files, key=lambda p: p.stat().st_mtime, reverse=True)[:3]:
            try:
                with open(report_file, "r") as f:
                    report_data = json.load(f)

                # Extract improvement opportunities
                if "recent_items" in report_data:
                    for item in report_data["recent_items"]:
                        improvement_ideas = self.extract_improvement_opportunities(item)
                        improvements.extend(improvement_ideas)

            except Exception as e:
                self.logger.error(f"Error analyzing report {report_file}: {e}")

        return improvements

    def extract_improvement_opportunities(self, learning_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract improvement opportunities from learning item"""
        opportunities = []

        try:
            content = str(learning_item).lower()

            # Performance optimization opportunities
            if any(word in content for word in ["performance", "optimization", "faster", "efficient"]):
                opportunities.append(
                    {
                        "type": "performance_optimization",
                        "description": f"Performance improvement based on: {learning_item.get('title', 'N/A')[:100]}",
                        "source": learning_item.get("source", "unknown"),
                        "confidence": 0.7,
                        "applicable_files": self.find_applicable_files("performance"),
                        "recommendations": [
                            "Optimize database queries",
                            "Implement caching",
                            "Reduce memory usage",
                            "Optimize loops and algorithms",
                        ],
                    }
                )

            # Error handling improvements
            if any(word in content for word in ["error", "exception", "handling", "try", "catch"]):
                opportunities.append(
                    {
                        "type": "error_handling",
                        "description": f"Error handling improvement from: {learning_item.get('title', 'N/A')[:100]}",
                        "source": learning_item.get("source", "unknown"),
                        "confidence": 0.8,
                        "applicable_files": self.find_applicable_files("error_handling"),
                        "recommendations": [
                            "Add more specific exception handling",
                            "Improve error logging",
                            "Add graceful degradation",
                            "Implement retry mechanisms",
                        ],
                    }
                )

            # Code quality improvements
            if any(word in content for word in ["best practice", "clean code", "refactor", "maintainable"]):
                opportunities.append(
                    {
                        "type": "code_quality",
                        "description": f"Code quality insight: {learning_item.get('title', 'N/A')[:100]}",
                        "source": learning_item.get("source", "unknown"),
                        "confidence": 0.6,
                        "applicable_files": self.find_applicable_files("code_quality"),
                        "recommendations": [
                            "Improve code documentation",
                            "Refactor complex functions",
                            "Add type hints",
                            "Improve variable naming",
                        ],
                    }
                )

            # Logging improvements
            if any(word in content for word in ["logging", "monitoring", "observability", "debugging"]):
                opportunities.append(
                    {
                        "type": "logging",
                        "description": f"Logging improvement: {learning_item.get('title', 'N/A')[:100]}",
                        "source": learning_item.get("source", "unknown"),
                        "confidence": 0.9,
                        "applicable_files": self.find_applicable_files("logging"),
                        "recommendations": [
                            "Add structured logging",
                            "Improve log levels",
                            "Add performance metrics",
                            "Implement log aggregation",
                        ],
                    }
                )

        except Exception as e:
            self.logger.error(f"Error extracting opportunities: {e}")

        return opportunities

    def find_applicable_files(self, improvement_type: str) -> List[str]:
        """Find files applicable for specific improvement type"""
        applicable_files = []

        # Define file patterns for different improvement types
        patterns = {
            "performance": ["*.py"],
            "error_handling": ["*.py"],
            "code_quality": ["*.py"],
            "logging": ["*.py"],
            "security": ["*dashboard*.py", "*hub*.py", "*auth*.py"],
        }

        search_patterns = patterns.get(improvement_type, ["*.py"])

        for pattern in search_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and file_path.suffix == ".py":
                    # Skip protected files
                    if file_path.name not in self.config.get("protected_files", []):
                        applicable_files.append(str(file_path))

        return applicable_files[:5]  # Limit to 5 files

    def _run_safety_gate(self, files: List[str] | None = None) -> bool:
        """Run the code safety gate (lint + tests). Returns True if safe to proceed."""
        if not self.config.get("require_tests_pass_before_apply", True):
            self.logger.warning("Safety gate DISABLED via config — skipping test run")
            return True

        if not _SAFETY_GATE_AVAILABLE:
            self.logger.warning("CodeSafetyGate not available — proceeding without gate")
            return True

        gate = CodeSafetyGate(project_root=self.project_root)
        result = gate.check(changed_files=files)
        if result.passed:
            self.logger.info("Safety gate passed: %s", result.reason)
        else:
            self.logger.error(
                "Safety gate BLOCKED: %s\n%s", result.reason, result.stderr[:500]
            )
        return result.passed

    async def generate_code_improvements(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate specific code improvements from opportunities"""
        improvements = []
        daily_changes = self.count_daily_changes()

        if daily_changes >= self.config.get("max_daily_changes", 3):
            self.logger.warning("Daily change limit reached")
            return improvements

        # Safety gate: only proceed if tests currently pass.
        # This establishes a clean baseline before generating improvements.
        if self.config.get("auto_apply_improvements", False):
            if not self._run_safety_gate():
                self.logger.error(
                    "Safety gate failed — auto-apply blocked. Fix existing test failures first."
                )
                return improvements

        for opportunity in opportunities:
            if opportunity["confidence"] >= self.config.get("code_quality_threshold", 0.8):
                improvement = await self.create_specific_improvement(opportunity)
                if improvement:
                    improvements.append(improvement)

        return improvements

    async def create_specific_improvement(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a specific code improvement from an opportunity"""
        try:
            improvement_type = opportunity["type"]

            if improvement_type == "logging":
                return await self.create_logging_improvement(opportunity)
            elif improvement_type == "error_handling":
                return await self.create_error_handling_improvement(opportunity)
            elif improvement_type == "performance_optimization":
                return await self.create_performance_improvement(opportunity)
            elif improvement_type == "code_quality":
                return await self.create_code_quality_improvement(opportunity)
            else:
                return await self.create_general_improvement(opportunity)

        except Exception as e:
            self.logger.error(f"Error creating improvement: {e}")
            return None

    async def create_logging_improvement(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Create logging improvement"""
        improvement = {
            "type": "logging_enhancement",
            "description": f"Enhanced logging: {opportunity['description'][:100]}...",
            "files_affected": opportunity.get("applicable_files", [])[:2],
            "confidence": opportunity["confidence"],
            "auto_apply": False,  # Requires approval
            "changes": [
                "Add structured logging with JSON format",
                "Implement performance timing logs",
                "Add error context logging",
                "Implement log rotation",
            ],
            "source_insight": opportunity["source"],
            "timestamp": datetime.now().isoformat(),
            "status": "pending_approval",
        }

        # Store in database
        self.store_improvement(improvement)
        self.logger.info(f"Created logging improvement: {improvement['description']}")

        return improvement

    async def create_error_handling_improvement(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Create error handling improvement"""
        improvement = {
            "type": "error_handling_enhancement",
            "description": f"Better error handling: {opportunity['description'][:100]}...",
            "files_affected": opportunity.get("applicable_files", [])[:2],
            "confidence": opportunity["confidence"],
            "auto_apply": False,
            "changes": [
                "Add specific exception types",
                "Implement graceful error recovery",
                "Add error context information",
                "Implement user-friendly error messages",
            ],
            "source_insight": opportunity["source"],
            "timestamp": datetime.now().isoformat(),
            "status": "pending_approval",
        }

        self.store_improvement(improvement)
        self.logger.info(f"Created error handling improvement: {improvement['description']}")

        return improvement

    async def create_performance_improvement(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Create performance improvement"""
        improvement = {
            "type": "performance_optimization",
            "description": f"Performance optimization: {opportunity['description'][:100]}...",
            "files_affected": opportunity.get("applicable_files", [])[:2],
            "confidence": opportunity["confidence"],
            "auto_apply": False,
            "changes": [
                "Optimize database queries",
                "Implement response caching",
                "Reduce memory allocations",
                "Optimize critical loops",
            ],
            "source_insight": opportunity["source"],
            "timestamp": datetime.now().isoformat(),
            "status": "pending_approval",
        }

        self.store_improvement(improvement)
        self.logger.info(f"Created performance improvement: {improvement['description']}")

        return improvement

    async def create_code_quality_improvement(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Create code quality improvement"""
        improvement = {
            "type": "code_quality_enhancement",
            "description": f"Code quality improvement: {opportunity['description'][:100]}...",
            "files_affected": opportunity.get("applicable_files", [])[:2],
            "confidence": opportunity["confidence"],
            "auto_apply": False,
            "changes": [
                "Add comprehensive type hints",
                "Improve function documentation",
                "Refactor complex functions",
                "Improve variable naming",
            ],
            "source_insight": opportunity["source"],
            "timestamp": datetime.now().isoformat(),
            "status": "pending_approval",
        }

        self.store_improvement(improvement)
        self.logger.info(f"Created code quality improvement: {improvement['description']}")

        return improvement

    async def create_general_improvement(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Create general improvement"""
        improvement = {
            "type": "general_enhancement",
            "description": f"General improvement: {opportunity['description'][:100]}...",
            "files_affected": opportunity.get("applicable_files", [])[:1],
            "confidence": opportunity["confidence"],
            "auto_apply": False,
            "changes": [
                "Apply best practices from learning",
                "Improve code maintainability",
                "Add documentation",
                "Enhance functionality",
            ],
            "source_insight": opportunity["source"],
            "timestamp": datetime.now().isoformat(),
            "status": "pending_approval",
        }

        self.store_improvement(improvement)
        self.logger.info(f"Created general improvement: {improvement['description']}")

        return improvement

    def store_improvement(self, improvement: Dict[str, Any]):
        """Store improvement in database"""
        try:
            conn = sqlite3.connect(self.improvement_db)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO improvements 
                (file_path, improvement_type, description, source_insight, status, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    ",".join(improvement.get("files_affected", [])),
                    improvement["type"],
                    improvement["description"],
                    improvement["source_insight"],
                    improvement["status"],
                    improvement["confidence"],
                ),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to store improvement: {e}")

    def count_daily_changes(self) -> int:
        """Count changes made today"""
        try:
            conn = sqlite3.connect(self.improvement_db)
            cursor = conn.cursor()

            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                """
                SELECT COUNT(*) FROM improvements 
                WHERE DATE(timestamp) = ? AND status = 'applied'
            """,
                (today,),
            )

            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            self.logger.error(f"Error counting daily changes: {e}")
            return 0

    async def generate_improvement_report(self) -> Dict[str, Any]:
        """Generate comprehensive improvement report"""
        opportunities = await self.analyze_learning_for_improvements()
        improvements = await self.generate_code_improvements(opportunities)

        # Get statistics from database
        try:
            conn = sqlite3.connect(self.improvement_db)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM improvements WHERE status = ?", ("pending_approval",))
            pending_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM improvements WHERE status = ?", ("applied",))
            applied_count = cursor.fetchone()[0]

            conn.close()
        except Exception:
            self.logger.exception("Failed to query improvement stats")
            pending_count = applied_count = 0

        report = {
            "timestamp": datetime.now().isoformat(),
            "opportunities_found": len(opportunities),
            "improvements_generated": len(improvements),
            "pending_approvals": pending_count,
            "total_applied": applied_count,
            "daily_changes": self.count_daily_changes(),
            "improvement_types": list(set(opp["type"] for opp in opportunities)),
            "recent_improvements": improvements[:5],
            "configuration": self.config,
            "system_status": "active",
        }

        return report


async def main():
    """Main function for standalone execution"""
    engine = SelfImprovementEngine()

    # Generate improvement report
    report = await engine.generate_improvement_report()

    print("\n=== CELSIUS SELF-IMPROVEMENT REPORT ===")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Opportunities Found: {report['opportunities_found']}")
    print(f"Improvements Generated: {report['improvements_generated']}")
    print(f"Pending Approvals: {report['pending_approvals']}")
    print(f"Total Applied: {report['total_applied']}")
    print(f"Daily Changes: {report['daily_changes']}")
    print(f"System Status: {report['system_status']}")

    if report["improvement_types"]:
        print(f"\nImprovement Types: {', '.join(report['improvement_types'])}")

    if report["recent_improvements"]:
        print("\nRecent Improvements:")
        for improvement in report["recent_improvements"]:
            print(f"  - {improvement['type']}: {improvement['description']}")

    print("\nSelf-improvement system active and analyzing!")


if __name__ == "__main__":
    asyncio.run(main())
