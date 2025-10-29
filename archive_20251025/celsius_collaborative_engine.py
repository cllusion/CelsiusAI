#!/usr/bin/env python3
"""
Celsius AI - Collaborative Improvement Engine
Server Hub and Celsius work together to analyze and improve Celsius code
CRITICAL SAFETY: Celsius cannot approve its own code changes - requires user approval
"""

import os
import sys
import json
import sqlite3
import subprocess
import threading
import time
import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
import ast
import re

# Import the new code approval system
from celsius_code_approval import CelsiusCodeApprovalSystem

logger = logging.getLogger(__name__)


class CelsiusCollaborativeEngine:
    """Collaborative code improvement engine with strict safety controls"""

    def __init__(self):
        self.base_dir = Path("C:/Users/micro/Celsius AI")
        self.db_path = self.base_dir / "celsius_system.db"
        self.improvement_config_path = self.base_dir / "improvement_config.json"

        # Code analysis settings
        self.analysis_enabled = True
        self.auto_backup_enabled = True
        self.suggestion_generation_enabled = True

        # CRITICAL SAFETY CONTROLS
        # Celsius can NEVER approve changes to these files
        self.celsius_protected_files = {
            "celsius_server_hub.py",  # Server Hub has final authority
            "celsius_system_integration.py",  # System integration controls
            "celsius_collaborative_engine.py",  # This file - prevent self-modification
            "celsius_process_trainer.py",  # Training system
            "celsius_power_manager.py",  # Power management
        }

        # Files that require user approval for any changes
        self.user_approval_required_files = {
            "enhanced_mobile_dashboard.py",  # Mobile interface
            "celsius_hourly_logger.py",  # Logging system
            "main.py",  # Main entry points
            "universal_celsius_ai.py",  # Core AI system
        }

        # System files that are completely off-limits
        self.system_protected_files = {"shutdown", "reboot", "halt", "poweroff", "taskkill", "net stop", "sc stop"}

        # Code improvement categories
        self.improvement_categories = {
            "performance": "Optimize for better performance",
            "power_efficiency": "Reduce power consumption",
            "memory_optimization": "Optimize memory usage",
            "error_handling": "Improve error handling",
            "code_quality": "Enhance code readability and structure",
            "security": "Strengthen security measures",
        }

        # Pending improvements awaiting approval
        self.pending_improvements = []

        # Code analysis history
        self.analysis_history = {}

        # Initialize code approval system
        self.approval_system = CelsiusCodeApprovalSystem()

        self.running = True
        self.load_improvement_config()
        self.init_improvement_database()

    def load_improvement_config(self):
        """Load collaborative improvement configuration"""
        try:
            if self.improvement_config_path.exists():
                with open(self.improvement_config_path, "r") as f:
                    config = json.load(f)

                self.analysis_enabled = config.get("analysis_enabled", True)
                self.auto_backup_enabled = config.get("auto_backup_enabled", True)
                self.suggestion_generation_enabled = config.get("suggestion_generation_enabled", True)
            else:
                self.save_improvement_config()

        except Exception as e:
            logger.error(f"Improvement config loading error: {e}")

    def save_improvement_config(self):
        """Save collaborative improvement configuration"""
        try:
            config = {
                "analysis_enabled": self.analysis_enabled,
                "auto_backup_enabled": self.auto_backup_enabled,
                "suggestion_generation_enabled": self.suggestion_generation_enabled,
                "last_updated": datetime.now().isoformat(),
            }

            with open(self.improvement_config_path, "w") as f:
                json.dump(config, f, indent=2)

        except Exception as e:
            logger.error(f"Improvement config saving error: {e}")

    def init_improvement_database(self):
        """Initialize collaborative improvement database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Code improvements table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS code_improvements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    improvement_type TEXT NOT NULL,
                    original_code TEXT,
                    improved_code TEXT,
                    description TEXT,
                    estimated_benefit TEXT,
                    requires_approval BOOLEAN DEFAULT TRUE,
                    approved_by TEXT,
                    approval_status TEXT DEFAULT 'pending',
                    created_by TEXT DEFAULT 'celsius_ai',
                    timestamp TEXT NOT NULL,
                    implementation_status TEXT DEFAULT 'pending'
                )
            """
            )

            # Code analysis results table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS code_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    findings TEXT,
                    suggestions TEXT,
                    priority_score INTEGER,
                    timestamp TEXT NOT NULL
                )
            """
            )

            # Safety audit log
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS safety_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    file_path TEXT,
                    safety_check_result TEXT,
                    blocked_reason TEXT,
                    timestamp TEXT NOT NULL
                )
            """
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Improvement database initialization error: {e}")

    def analyze_code_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a code file for potential improvements"""
        try:
            # CRITICAL SAFETY CHECK
            if self.is_protected_file(file_path):
                self.log_safety_audit("code_analysis_blocked", file_path, "protected_file")
                return {"status": "blocked", "reason": "protected_file", "findings": []}

            if not Path(file_path).exists():
                return {"status": "error", "reason": "file_not_found", "findings": []}

            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                code_content = f.read()

            # Perform various code analyses
            findings = []

            # Performance analysis
            performance_issues = self.analyze_performance_issues(code_content, file_path)
            findings.extend(performance_issues)

            # Power efficiency analysis
            power_issues = self.analyze_power_efficiency(code_content, file_path)
            findings.extend(power_issues)

            # Memory optimization analysis
            memory_issues = self.analyze_memory_usage(code_content, file_path)
            findings.extend(memory_issues)

            # Error handling analysis
            error_handling_issues = self.analyze_error_handling(code_content, file_path)
            findings.extend(error_handling_issues)

            # Security analysis
            security_issues = self.analyze_security_concerns(code_content, file_path)
            findings.extend(security_issues)

            # Store analysis results
            self.store_code_analysis(file_path, findings)

            return {
                "status": "completed",
                "findings": findings,
                "file_path": file_path,
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Code analysis error for {file_path}: {e}")
            return {"status": "error", "reason": str(e), "findings": []}

    def analyze_performance_issues(self, code_content: str, file_path: str) -> List[Dict]:
        """Analyze code for performance optimization opportunities"""
        issues = []

        try:
            lines = code_content.split("\n")

            # Check for common performance issues
            for i, line in enumerate(lines):
                line_stripped = line.strip()

                # Inefficient loops
                if "for" in line_stripped and "range(len(" in line_stripped:
                    issues.append(
                        {
                            "type": "performance",
                            "category": "inefficient_loop",
                            "line_number": i + 1,
                            "description": "Consider using enumerate() instead of range(len())",
                            "priority": 3,
                            "suggestion": "Use enumerate() for better performance and readability",
                        }
                    )

                # Repeated string concatenation
                if "+=" in line_stripped and "str" in line_stripped.lower():
                    issues.append(
                        {
                            "type": "performance",
                            "category": "string_concatenation",
                            "line_number": i + 1,
                            "description": "String concatenation in loop - consider using join()",
                            "priority": 4,
                            "suggestion": "Use list.append() and join() for better performance",
                        }
                    )

                # Inefficient list operations
                if ".append(" in line_stripped and "for" in line_stripped:
                    issues.append(
                        {
                            "type": "performance",
                            "category": "list_comprehension_opportunity",
                            "line_number": i + 1,
                            "description": "Consider using list comprehension",
                            "priority": 2,
                            "suggestion": "List comprehensions are typically faster than append() in loops",
                        }
                    )

                # Unnecessary function calls
                if "len(" in line_stripped and "for" in line_stripped and "range" in line_stripped:
                    issues.append(
                        {
                            "type": "performance",
                            "category": "unnecessary_len_call",
                            "line_number": i + 1,
                            "description": "Repeated len() calls in loop",
                            "priority": 3,
                            "suggestion": "Store len() result in variable before loop",
                        }
                    )

        except Exception as e:
            logger.error(f"Performance analysis error: {e}")

        return issues

    def analyze_power_efficiency(self, code_content: str, file_path: str) -> List[Dict]:
        """Analyze code for power efficiency improvements"""
        issues = []

        try:
            lines = code_content.split("\n")

            for i, line in enumerate(lines):
                line_stripped = line.strip()

                # CPU-intensive operations
                if (
                    "while True:" in line_stripped
                    and "time.sleep(" not in code_content[code_content.find(line) : code_content.find(line) + 200]
                ):
                    issues.append(
                        {
                            "type": "power_efficiency",
                            "category": "busy_wait_loop",
                            "line_number": i + 1,
                            "description": "Busy wait loop without sleep - high CPU usage",
                            "priority": 5,
                            "suggestion": "Add time.sleep() to reduce CPU usage",
                        }
                    )

                # Frequent file I/O
                if line_stripped.count("open(") > 0 and "with" not in line_stripped:
                    issues.append(
                        {
                            "type": "power_efficiency",
                            "category": "file_io_optimization",
                            "line_number": i + 1,
                            "description": "File I/O without context manager",
                            "priority": 3,
                            "suggestion": "Use with statement for efficient file handling",
                        }
                    )

                # Excessive logging
                if line_stripped.count("print(") > 0 or line_stripped.count("logger.") > 0:
                    if i > 0 and ("print(" in lines[i - 1] or "logger." in lines[i - 1]):
                        issues.append(
                            {
                                "type": "power_efficiency",
                                "category": "excessive_logging",
                                "line_number": i + 1,
                                "description": "Frequent logging operations",
                                "priority": 2,
                                "suggestion": "Consider batching log messages or reducing log level",
                            }
                        )

        except Exception as e:
            logger.error(f"Power efficiency analysis error: {e}")

        return issues

    def analyze_memory_usage(self, code_content: str, file_path: str) -> List[Dict]:
        """Analyze code for memory optimization opportunities"""
        issues = []

        try:
            lines = code_content.split("\n")

            for i, line in enumerate(lines):
                line_stripped = line.strip()

                # Large data structures
                if "list(" in line_stripped and "range(" in line_stripped:
                    issues.append(
                        {
                            "type": "memory_optimization",
                            "category": "large_list_creation",
                            "line_number": i + 1,
                            "description": "Large list creation - consider generator",
                            "priority": 4,
                            "suggestion": "Use generator expressions for memory efficiency",
                        }
                    )

                # Global variables
                if line_stripped.startswith("global "):
                    issues.append(
                        {
                            "type": "memory_optimization",
                            "category": "global_variable_usage",
                            "line_number": i + 1,
                            "description": "Global variable usage",
                            "priority": 2,
                            "suggestion": "Consider passing variables as parameters",
                        }
                    )

                # Memory leaks potential
                if "threading." in line_stripped and "daemon=" not in line_stripped:
                    issues.append(
                        {
                            "type": "memory_optimization",
                            "category": "thread_cleanup",
                            "line_number": i + 1,
                            "description": "Thread without daemon flag",
                            "priority": 3,
                            "suggestion": "Set daemon=True or ensure proper thread cleanup",
                        }
                    )

        except Exception as e:
            logger.error(f"Memory usage analysis error: {e}")

        return issues

    def analyze_error_handling(self, code_content: str, file_path: str) -> List[Dict]:
        """Analyze code for error handling improvements"""
        issues = []

        try:
            lines = code_content.split("\n")

            in_try_block = False
            has_except = False

            for i, line in enumerate(lines):
                line_stripped = line.strip()

                # Try blocks without specific exception handling
                if line_stripped.startswith("try:"):
                    in_try_block = True
                    has_except = False

                elif line_stripped.startswith("except:") and in_try_block:
                    has_except = True
                    issues.append(
                        {
                            "type": "error_handling",
                            "category": "bare_except",
                            "line_number": i + 1,
                            "description": "Bare except clause - catches all exceptions",
                            "priority": 4,
                            "suggestion": "Use specific exception types for better error handling",
                        }
                    )

                elif line_stripped.startswith("except ") and "Exception" in line_stripped:
                    has_except = True
                    issues.append(
                        {
                            "type": "error_handling",
                            "category": "generic_exception",
                            "line_number": i + 1,
                            "description": "Generic Exception catching",
                            "priority": 3,
                            "suggestion": "Use more specific exception types when possible",
                        }
                    )

                elif not line_stripped.startswith(" ") and in_try_block:
                    if not has_except:
                        issues.append(
                            {
                                "type": "error_handling",
                                "category": "missing_exception_handling",
                                "line_number": i,
                                "description": "Try block without exception handling",
                                "priority": 4,
                                "suggestion": "Add appropriate except clauses",
                            }
                        )
                    in_try_block = False

        except Exception as e:
            logger.error(f"Error handling analysis error: {e}")

        return issues

    def analyze_security_concerns(self, code_content: str, file_path: str) -> List[Dict]:
        """Analyze code for security concerns"""
        issues = []

        try:
            lines = code_content.split("\n")

            for i, line in enumerate(lines):
                line_stripped = line.strip()

                # Potential security risks
                if "subprocess.call(" in line_stripped or "os.system(" in line_stripped:
                    issues.append(
                        {
                            "type": "security",
                            "category": "command_injection_risk",
                            "line_number": i + 1,
                            "description": "Potential command injection vulnerability",
                            "priority": 5,
                            "suggestion": "Use subprocess.run() with shell=False and validate inputs",
                        }
                    )

                # Hardcoded credentials or secrets
                if any(keyword in line_stripped.lower() for keyword in ["password", "secret", "key", "token"]):
                    if "=" in line_stripped and ('"' in line_stripped or "'" in line_stripped):
                        issues.append(
                            {
                                "type": "security",
                                "category": "hardcoded_credentials",
                                "line_number": i + 1,
                                "description": "Potential hardcoded credentials",
                                "priority": 4,
                                "suggestion": "Use environment variables or secure storage for credentials",
                            }
                        )

                # SQL injection potential
                if "execute(" in line_stripped and ('"SELECT' in line_stripped or "'SELECT" in line_stripped):
                    if "%" in line_stripped or ".format(" in line_stripped:
                        issues.append(
                            {
                                "type": "security",
                                "category": "sql_injection_risk",
                                "line_number": i + 1,
                                "description": "Potential SQL injection vulnerability",
                                "priority": 5,
                                "suggestion": "Use parameterized queries instead of string formatting",
                            }
                        )

        except Exception as e:
            logger.error(f"Security analysis error: {e}")

        return issues

    def generate_code_improvement(self, file_path: str, finding: Dict) -> Dict[str, Any]:
        """Generate a specific code improvement based on analysis finding"""
        try:
            # CRITICAL SAFETY CHECK - Celsius cannot improve its own files
            if self.is_celsius_protected_file(file_path):
                self.log_safety_audit("improvement_blocked", file_path, "celsius_protected")
                return {
                    "status": "blocked",
                    "reason": "celsius_cannot_improve_own_code",
                    "requires_user_approval": True,
                }

            # Read original code
            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            improvement_id = self.generate_improvement_id(file_path, finding)

            # Generate improvement based on finding type
            improved_code = None
            description = ""
            estimated_benefit = ""

            if finding["type"] == "performance":
                improved_code, description, estimated_benefit = self.generate_performance_improvement(
                    original_code, finding
                )
            elif finding["type"] == "power_efficiency":
                improved_code, description, estimated_benefit = self.generate_power_efficiency_improvement(
                    original_code, finding
                )
            elif finding["type"] == "memory_optimization":
                improved_code, description, estimated_benefit = self.generate_memory_optimization_improvement(
                    original_code, finding
                )
            elif finding["type"] == "error_handling":
                improved_code, description, estimated_benefit = self.generate_error_handling_improvement(
                    original_code, finding
                )
            elif finding["type"] == "security":
                improved_code, description, estimated_benefit = self.generate_security_improvement(
                    original_code, finding
                )

            if improved_code:
                # Submit to new code approval system with formatted presentation
                request_id = self.approval_system.submit_code_change_request(
                    title=f"{finding['type'].replace('_', ' ').title()} improvement in {os.path.basename(file_path)}",
                    description=f"{description}\n\nEstimated Benefit: {estimated_benefit}",
                    file_path=file_path,
                    original_code=original_code,
                    proposed_code=improved_code,
                    change_type=finding["type"],
                    priority=self.get_priority_from_finding(finding),
                )

                # Also store in old system for compatibility
                improvement = {
                    "id": improvement_id,
                    "request_id": request_id,  # Link to new approval system
                    "file_path": file_path,
                    "improvement_type": finding["type"],
                    "original_code": original_code,
                    "improved_code": improved_code,
                    "description": description,
                    "estimated_benefit": estimated_benefit,
                    "requires_approval": True,  # All improvements require approval
                    "approved_by": None,
                    "approval_status": "pending",
                    "created_by": "celsius_ai",
                    "timestamp": datetime.now().isoformat(),
                    "finding": finding,
                }

                self.store_code_improvement(improvement)
                self.pending_improvements.append(improvement)

                return {
                    "status": "generated",
                    "improvement_id": improvement_id,
                    "request_id": request_id,
                    "requires_user_approval": True,
                    "description": description,
                    "estimated_benefit": estimated_benefit,
                    "formatted_for_approval": True,
                }

            return {"status": "no_improvement_generated", "reason": "unable_to_generate_improvement"}

        except Exception as e:
            logger.error(f"Code improvement generation error: {e}")
            return {"status": "error", "reason": str(e)}

    def generate_performance_improvement(self, original_code: str, finding: Dict) -> Tuple[str, str, str]:
        """Generate performance improvement"""
        # This is a simplified example - in reality, would use more sophisticated analysis
        improved_code = original_code
        description = f"Performance improvement for {finding['category']}"
        estimated_benefit = "5-15% performance improvement expected"

        if finding["category"] == "inefficient_loop":
            # Replace range(len()) with enumerate()
            improved_code = re.sub(
                r"for\s+(\w+)\s+in\s+range\(len\((\w+)\)\):", r"for \1, item in enumerate(\2):", improved_code
            )
            description = "Replaced range(len()) with enumerate() for better performance"

        elif finding["category"] == "string_concatenation":
            description = "Suggested replacement of string concatenation with join() method"
            estimated_benefit = "10-30% performance improvement for string operations"

        return improved_code, description, estimated_benefit

    def generate_power_efficiency_improvement(self, original_code: str, finding: Dict) -> Tuple[str, str, str]:
        """Generate power efficiency improvement"""
        improved_code = original_code
        description = f"Power efficiency improvement for {finding['category']}"
        estimated_benefit = "5-20% reduction in CPU usage expected"

        if finding["category"] == "busy_wait_loop":
            # Add sleep to busy wait loops
            improved_code = re.sub(
                r"(\s+)(while\s+True:)", r"\1\2\n\1    time.sleep(0.1)  # Added for power efficiency", improved_code
            )
            description = "Added sleep() to busy wait loop to reduce CPU usage"

        return improved_code, description, estimated_benefit

    def generate_memory_optimization_improvement(self, original_code: str, finding: Dict) -> Tuple[str, str, str]:
        """Generate memory optimization improvement"""
        improved_code = original_code
        description = f"Memory optimization for {finding['category']}"
        estimated_benefit = "10-25% memory usage reduction expected"

        return improved_code, description, estimated_benefit

    def generate_error_handling_improvement(self, original_code: str, finding: Dict) -> Tuple[str, str, str]:
        """Generate error handling improvement"""
        improved_code = original_code
        description = f"Error handling improvement for {finding['category']}"
        estimated_benefit = "Improved reliability and error diagnostics"

        if finding["category"] == "bare_except":
            # Replace bare except with specific exception
            improved_code = re.sub(r"except:", r"except Exception as e:", improved_code)
            description = "Replaced bare except with specific Exception handling"

        return improved_code, description, estimated_benefit

    def generate_security_improvement(self, original_code: str, finding: Dict) -> Tuple[str, str, str]:
        """Generate security improvement"""
        improved_code = original_code
        description = f"Security improvement for {finding['category']}"
        estimated_benefit = "Enhanced security and reduced vulnerability risk"

        return improved_code, description, estimated_benefit

    def is_protected_file(self, file_path: str) -> bool:
        """Check if file is protected from automatic modification"""
        file_name = Path(file_path).name
        return (
            any(protected in file_name for protected in self.celsius_protected_files)
            or any(protected in file_name for protected in self.user_approval_required_files)
            or any(protected in file_name for protected in self.system_protected_files)
        )

    def is_celsius_protected_file(self, file_path: str) -> bool:
        """Check if file is specifically protected from Celsius modification"""
        file_name = Path(file_path).name
        return any(protected in file_name for protected in self.celsius_protected_files)

    def generate_improvement_id(self, file_path: str, finding: Dict) -> str:
        """Generate unique improvement ID"""
        content = f"{file_path}_{finding['type']}_{finding.get('line_number', 0)}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def get_priority_from_finding(self, finding: Dict) -> int:
        """Convert finding severity to priority level for approval system"""
        severity = finding.get("severity", "low").lower()
        finding_type = finding.get("type", "").lower()

        # Security issues get higher priority
        if finding_type == "security":
            return 4 if severity == "critical" else 3

        # Performance issues
        if finding_type == "performance":
            return 3 if severity in ["high", "critical"] else 2

        # Power efficiency (important for Celsius)
        if finding_type == "power_efficiency":
            return 2 if severity in ["medium", "high"] else 1

        # Default mappings
        priority_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}

        return priority_map.get(severity, 1)

    def store_code_improvement(self, improvement: Dict):
        """Store code improvement in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO code_improvements 
                (file_path, improvement_type, original_code, improved_code, description,
                 estimated_benefit, requires_approval, approved_by, approval_status,
                 created_by, timestamp, implementation_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    improvement["file_path"],
                    improvement["improvement_type"],
                    improvement["original_code"],
                    improvement["improved_code"],
                    improvement["description"],
                    improvement["estimated_benefit"],
                    improvement["requires_approval"],
                    improvement["approved_by"],
                    improvement["approval_status"],
                    improvement["created_by"],
                    improvement["timestamp"],
                    "pending",
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Code improvement storage error: {e}")

    def store_code_analysis(self, file_path: str, findings: List[Dict]):
        """Store code analysis results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO code_analysis 
                (file_path, analysis_type, findings, suggestions, priority_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    file_path,
                    "comprehensive_analysis",
                    json.dumps(findings),
                    json.dumps([f["suggestion"] for f in findings if "suggestion" in f]),
                    max([f.get("priority", 0) for f in findings]) if findings else 0,
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Code analysis storage error: {e}")

    def log_safety_audit(self, action_type: str, file_path: str, result: str, blocked_reason: str = None):
        """Log safety audit information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO safety_audit_log 
                (action_type, file_path, safety_check_result, blocked_reason, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """,
                (action_type, file_path, result, blocked_reason, datetime.now().isoformat()),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Safety audit logging error: {e}")

    def get_pending_improvements(self) -> List[Dict]:
        """Get all pending improvements awaiting approval"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM code_improvements 
                WHERE approval_status = 'pending'
                ORDER BY timestamp DESC
            """
            )

            improvements = []
            for row in cursor.fetchall():
                improvements.append(
                    {
                        "id": row[0],
                        "file_path": row[1],
                        "improvement_type": row[2],
                        "description": row[5],
                        "estimated_benefit": row[6],
                        "created_by": row[9],
                        "timestamp": row[10],
                    }
                )

            conn.close()
            return improvements

        except Exception as e:
            logger.error(f"Pending improvements retrieval error: {e}")
            return []

    def approve_improvement(self, improvement_id: int, approved_by: str) -> bool:
        """Approve a code improvement (USER ONLY - never Celsius)"""
        try:
            # CRITICAL: Ensure this is never called by Celsius AI
            if approved_by.lower() in ["celsius", "celsius_ai", "ai", "system"]:
                self.log_safety_audit(
                    "approval_blocked", "", "celsius_cannot_approve", "AI cannot approve its own changes"
                )
                logger.warning("SECURITY: Celsius AI attempted to approve its own code changes - BLOCKED")
                return False

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE code_improvements 
                SET approval_status = 'approved', approved_by = ?
                WHERE id = ?
            """,
                (approved_by, improvement_id),
            )

            conn.commit()
            conn.close()

            logger.info(f"Code improvement {improvement_id} approved by {approved_by}")
            return True

        except Exception as e:
            logger.error(f"Improvement approval error: {e}")
            return False

    def start_collaborative_improvement(self):
        """Start the collaborative improvement system"""
        logger.info("Starting Celsius AI Collaborative Improvement Engine")
        logger.warning("SAFETY: Celsius AI cannot approve its own code changes")
        logger.info(f"Protected files: {len(self.celsius_protected_files)}")

        # Start analysis thread
        analysis_thread = threading.Thread(target=self.continuous_analysis, daemon=True)
        analysis_thread.start()

        logger.info("Collaborative improvement system started")

    def continuous_analysis(self):
        """Continuous code analysis loop"""
        while self.running and self.analysis_enabled:
            try:
                # Analyze Celsius AI files for improvements
                celsius_files = ["enhanced_mobile_dashboard.py", "celsius_hourly_logger.py", "universal_celsius_ai.py"]

                for file_path in celsius_files:
                    full_path = self.base_dir / file_path
                    if full_path.exists():
                        analysis_result = self.analyze_code_file(str(full_path))

                        if analysis_result["status"] == "completed":
                            # Generate improvements for findings
                            for finding in analysis_result["findings"]:
                                if finding.get("priority", 0) >= 3:  # Only high priority
                                    improvement_result = self.generate_code_improvement(str(full_path), finding)

                                    if improvement_result["status"] == "generated":
                                        logger.info(
                                            f"Generated improvement for {file_path}: {improvement_result['description']}"
                                        )

                # Wait before next analysis cycle
                time.sleep(300)  # Analyze every 5 minutes

            except Exception as e:
                logger.error(f"Continuous analysis error: {e}")
                time.sleep(600)  # Wait longer on error

    def stop_collaborative_improvement(self):
        """Stop the collaborative improvement system"""
        logger.info("Stopping Celsius AI Collaborative Improvement Engine")
        self.running = False
        self.save_improvement_config()


def main():
    """Main function for testing"""
    engine = CelsiusCollaborativeEngine()
    engine.start_collaborative_improvement()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        engine.stop_collaborative_improvement()


if __name__ == "__main__":
    main()
