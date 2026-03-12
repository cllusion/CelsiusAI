#!/usr/bin/env python3
"""
ðŸ§ª CELSIUS AI - ULTIMATE ASYNC TESTING SUITE ðŸ§ª
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

A comprehensive, asynchronous testing framework for the modernized Celsius AI ecosystem.
This suite is designed to validate the functionality, performance, and integration of
all refactored, async-native components.

Features:
â€¢ ðŸš€ Asynchronous Test Execution via `unittest.IsolatedAsyncioTestCase`
â€¢ ðŸ”§ System Responsiveness & Resource Monitoring
â€¢ ðŸ”— Full System Integration and Dependency Validation
â€¢ ðŸ“Š Advanced, Asynchronous Test Reporting to SQLite
â€¢ ðŸŽ¯ Performance Benchmarking for Async Operations
â€¢ ðŸ–¥ï¸ GUI Component Import and Availability Checks
â€¢ ðŸ“§ Email and Notification System Validation

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
"""

import unittest
import sys
import asyncio
import json
import aiosqlite
import subprocess
import tkinter as tk
import os
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import platform
import logging
from typing import Dict, List, Any, Optional
import importlib.util
import time

# --- Initial Setup ---
# Configure logging for the test suite
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("UltimateTestSuite")

# Add project root to the Python path to ensure modules are findable
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# --- Test Result Management ---


class AsyncTestResultManager:
    """
    Manages the storage and reporting of test results in an async-friendly way,
    logging everything to a dedicated SQLite database.
    """

    def __init__(self):
        self.test_dir = PROJECT_ROOT / "tests"
        self.test_dir.mkdir(exist_ok=True)
        self.results_db_path = self.test_dir / "test_results.db"
        self.current_session_id = datetime.now().isoformat()
        # Remove the event loop creation - will be handled by caller

    async def initialize_database(self):
        """Initializes the SQLite database for storing test results."""
        async with aiosqlite.connect(self.results_db_path) as db:
            await db.executescript(
                """
                DROP TABLE IF EXISTS test_sessions;
                DROP TABLE IF EXISTS test_results;

                CREATE TABLE test_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    total_tests INTEGER,
                    passed INTEGER,
                    failed INTEGER,
                    errors INTEGER,
                    skipped INTEGER,
                    duration_seconds REAL,
                    system_info TEXT
                );

                CREATE TABLE test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    test_class TEXT NOT NULL,
                    test_method TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    error_message TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES test_sessions(session_id)
                );
                """
            )
            await db.commit()

    def log_test_result(self, test_case, status: str, duration: float, error_message: Optional[str] = None):
        """Synchronous wrapper to log a test result to the database using the event loop."""
        # Create a new event loop for this operation since we don't have a persistent one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._log_test_result_async(test_case, status, duration, error_message))
        finally:
            loop.close()

    async def _log_test_result_async(
        self, test_case, status: str, duration: float, error_message: Optional[str] = None
    ):
        """Logs the result of a single test case to the database."""
        async with aiosqlite.connect(self.results_db_path) as db:
            await db.execute(
                """
                INSERT INTO test_results (session_id, test_class, test_method, status, duration_seconds, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.current_session_id,
                    test_case.__class__.__name__,
                    test_case._testMethodName,
                    status,
                    duration,
                    error_message,
                    datetime.now().isoformat(),
                ),
            )
            await db.commit()

    def log_session_summary(
        self,
        total_tests: int,
        passed: int,
        failed: int,
        errors: int,
        skipped: int,
        duration: float,
        start_time: datetime,
    ):
        """Synchronous wrapper to log the final session summary."""
        # Create a new event loop for this operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self._log_session_summary_async(total_tests, passed, failed, errors, skipped, duration, start_time)
            )
        finally:
            loop.close()

    async def _log_session_summary_async(
        self,
        total_tests: int,
        passed: int,
        failed: int,
        errors: int,
        skipped: int,
        duration: float,
        start_time: datetime,
    ):
        """Logs the final summary of the entire test session."""
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }
        async with aiosqlite.connect(self.results_db_path) as db:
            await db.execute(
                """
                INSERT INTO test_sessions (session_id, start_time, end_time, total_tests, passed, failed, errors, skipped, duration_seconds, system_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.current_session_id,
                    start_time.isoformat(),
                    datetime.now().isoformat(),
                    total_tests,
                    passed,
                    failed,
                    errors,
                    skipped,
                    duration,
                    json.dumps(system_info),
                ),
            )
            await db.commit()


# --- Custom Test Runner ---


class DatabaseTestResult(unittest.TextTestResult):
    """A custom test result class that logs results to the database."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result_manager = AsyncTestResultManager()
        self.test_starts: Dict[str, float] = {}
        self.db_initialized = False

    def startTest(self, test):
        self.test_starts[test.id()] = time.perf_counter()
        super().startTest(test)

    def addSuccess(self, test):
        super().addSuccess(test)
        duration = time.perf_counter() - self.test_starts.get(test.id(), time.perf_counter())
        self.result_manager.log_test_result(test, "passed", duration)
        logger.info(f"âœ… PASSED: {test.id()} ({duration:.4f}s)")

    def addError(self, test, err):
        super().addError(test, err)
        duration = time.perf_counter() - self.test_starts.get(test.id(), time.perf_counter())
        error_message = self._exc_info_to_string(err, test)
        self.result_manager.log_test_result(test, "error", duration, error_message)
        logger.error(f"âŒ ERROR: {test.id()} ({duration:.4f}s)")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        duration = time.perf_counter() - self.test_starts.get(test.id(), time.perf_counter())
        error_message = self._exc_info_to_string(err, test)
        self.result_manager.log_test_result(test, "failed", duration, error_message)
        logger.error(f"ðŸ”¥ FAILED: {test.id()} ({duration:.4f}s)")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        duration = time.perf_counter() - self.test_starts.get(test.id(), 0)
        self.result_manager.log_test_result(test, "skipped", duration, reason)
        logger.warning(f"â­ï¸ SKIPPED: {test.id()} - {reason}")


class DatabaseTestRunner(unittest.TextTestRunner):
    """A test runner that uses the DatabaseTestResult class."""

    def __init__(self, *args, **kwargs):
        kwargs["resultclass"] = DatabaseTestResult
        super().__init__(*args, **kwargs)

    def run(self, test):
        """Runs the given test case or test suite."""
        start_time = datetime.now()
        result = super().run(test)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Log session summary
        if hasattr(result, "result_manager"):
            passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
            result.result_manager.log_session_summary(
                result.testsRun,
                passed,
                len(result.failures),
                len(result.errors),
                len(result.skipped),
                duration,
                start_time,
            )

        logger.info(f"Test session finished in {duration:.2f} seconds.")
        return result


# --- Test Cases ---


class SystemResponsivenessTests(unittest.IsolatedAsyncioTestCase):
    """Tests the responsiveness and resource usage of the system."""

    async def test_cpu_performance(self):
        """Tests CPU responsiveness by measuring the time for a short sleep."""
        start_time = asyncio.get_event_loop().time()
        await asyncio.sleep(0.1)
        response_time = asyncio.get_event_loop().time() - start_time
        self.assertLess(response_time, 0.2, "CPU event loop should be responsive.")

        cpu_percent = psutil.cpu_percent(interval=None)
        self.assertLessEqual(cpu_percent, 95.0, "CPU usage should be below 95%.")

    async def test_memory_availability(self):
        """Checks for sufficient available memory."""
        memory = psutil.virtual_memory()
        self.assertGreater(memory.available, 100 * 1024 * 1024, "At least 100MB of RAM should be available.")
        self.assertLess(memory.percent, 95.0, "Memory usage should be under 95%.")

    async def test_disk_space(self):
        """Ensures there is adequate free disk space."""
        disk = psutil.disk_usage(str(PROJECT_ROOT))
        self.assertGreater(disk.free, 100 * 1024 * 1024, "At least 100MB of disk space should be available.")


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Tests the integration and existence of core application components."""

    def assertModuleExists(self, module_path: Path, module_name: str):
        """Helper to assert that a Python module file exists."""
        self.assertTrue(module_path.exists(), f"Module file not found: {module_path}")
        spec = importlib.util.find_spec(module_name)
        self.assertIsNotNone(
            spec, f"Module '{module_name}' could not be imported. Check PYTHONPATH and file structure."
        )

    async def test_core_files_existence_and_imports(self):
        """Verifies that all essential source files exist and are importable."""
        core_modules = {
            "src.core.main": PROJECT_ROOT / "src" / "core" / "main.py",
            "src.hub.celsius_ultimate_hub": PROJECT_ROOT / "src" / "hub" / "celsius_ultimate_hub.py",
            "src.guardian.celsius_lightweight_guardian": PROJECT_ROOT
            / "src"
            / "guardian"
            / "celsius_lightweight_guardian.py",
            "src.dashboard.enhanced_mobile_dashboard": PROJECT_ROOT
            / "src"
            / "dashboard"
            / "enhanced_mobile_dashboard.py",
            "src.utils.enhanced_email_system": PROJECT_ROOT / "src" / "utils" / "enhanced_email_system.py",
        }
        for name, path in core_modules.items():
            with self.subTest(module=name):
                self.assertModuleExists(path, name)

    async def test_python_dependencies_availability(self):
        """Checks if all required third-party Python packages are installed."""
        required_modules = [
            "aiohttp",
            "aiosqlite",
            "bcrypt",
            "bs4",
            "fastapi",
            "matplotlib",
            "psutil",
            "ttkthemes",
            "uvicorn",
            "yara",
        ]
        for module in required_modules:
            with self.subTest(module=module):
                try:
                    importlib.import_module(module)
                except ImportError:
                    self.fail(f"Required dependency '{module}' is not installed.")

    async def test_database_initialization_and_schema(self):
        """Tests that the database initialization script runs and creates the correct tables."""
        init_script_path = PROJECT_ROOT / "scripts" / "init_db.py"
        self.assertTrue(init_script_path.exists(), "Database initialization script not found.")

        # Run the init script
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(init_script_path), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        self.assertEqual(process.returncode, 0, f"Database init script failed: {stderr.decode()}")

        # Verify databases and tables
        db_paths = {
            "activity": PROJECT_ROOT / "data" / "celsius_activity.db",
            "system": PROJECT_ROOT / "data" / "celsius_system.db",
            "monitoring": PROJECT_ROOT / "data" / "celsius_monitoring.db",
        }

        expected_tables = {
            "activity": ["activity_log", "security_log", "users"],
            "system": ["system_metrics"],
            "monitoring": ["monitoring_log"],
        }

        for db_name, db_path in db_paths.items():
            with self.subTest(database=db_name):
                self.assertTrue(db_path.exists(), f"Database file '{db_path.name}' was not created.")
                async with aiosqlite.connect(db_path) as db:
                    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = [row[0] for row in await cursor.fetchall()]
                    for table in expected_tables[db_name]:
                        self.assertIn(table, tables, f"Table '{table}' missing in '{db_name}' database.")


class PerformanceBenchmarkTests(unittest.IsolatedAsyncioTestCase):
    """Performs basic performance benchmarks on critical async operations."""

    async def test_async_database_write_performance(self):
        """Benchmarks the performance of writing 1000 records to the database."""
        db_path = PROJECT_ROOT / "tests" / "perf_test.db"
        if db_path.exists():
            db_path.unlink()

        start_time = asyncio.get_event_loop().time()
        async with aiosqlite.connect(db_path) as db:
            await db.execute("CREATE TABLE perf (id INTEGER PRIMARY KEY, data TEXT);")
            await db.executemany("INSERT INTO perf (data) VALUES (?);", [(f"data_{i}",) for i in range(1000)])
            await db.commit()
        duration = asyncio.get_event_loop().time() - start_time

        self.assertLess(duration, 2.0, "Writing 1000 records should take less than 2 seconds.")
        logger.info(f"Database write benchmark: {duration:.4f} seconds.")
        db_path.unlink()


# --- Test Runner ---


class AsyncTestRunner:
    """A custom test runner to execute tests and manage results asynchronously."""

    def __init__(self, result_manager: AsyncTestResultManager):
        self.result_manager = result_manager
        self.suite = unittest.TestSuite()

    def add_tests(self, test_classes: List[unittest.TestCase]):
        """Adds test classes to the test suite."""
        for test_class in test_classes:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            self.suite.addTest(tests)

    async def run(self):
        """Runs the entire test suite and logs the results."""
        start_time = datetime.now()
        logger.info(f"Starting test session: {self.result_manager.current_session_id}")

        await self.result_manager.initialize_database()

        runner = unittest.TextTestRunner(verbosity=2)

        # This is a simplified way to run and collect results.
        # A more robust solution might wrap each test case to capture duration and status.
        result = runner.run(self.suite)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Log session summary
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }

        async with aiosqlite.connect(self.result_manager.results_db_path) as db:
            await db.execute(
                """
                INSERT INTO test_sessions (session_id, start_time, end_time, total_tests, passed, failed, errors, skipped, duration_seconds, system_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.result_manager.current_session_id,
                    start_time.isoformat(),
                    end_time.isoformat(),
                    result.testsRun,
                    result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
                    len(result.failures),
                    len(result.errors),
                    len(result.skipped),
                    duration,
                    json.dumps(system_info),
                ),
            )
            await db.commit()

        logger.info(f"Test session finished in {duration:.2f} seconds.")
        logger.info(f"Results stored in session: {self.result_manager.current_session_id}")


def main():
    """The main entry point for running the test suite."""
    logger.info("Setting up the test suite...")
    suite = unittest.TestSuite()

    # Define the test classes to be included in the run
    test_classes_to_run = [
        SystemResponsivenessTests,
        IntegrationTests,
        PerformanceBenchmarkTests,
    ]

    loader = unittest.TestLoader()
    for test_class in test_classes_to_run:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    logger.info("Starting the test runner...")
    runner = DatabaseTestRunner(verbosity=2)
    runner.run(suite)


def run_tests_programmatically():
    """Run the test suite programmatically without launching GUI."""
    logger.info("Running tests programmatically...")
    
    suite = unittest.TestSuite()

    # Define the test classes to be included in the run
    test_classes_to_run = [
        SystemResponsivenessTests,
        IntegrationTests,
        PerformanceBenchmarkTests,
    ]

    loader = unittest.TestLoader()
    for test_class in test_classes_to_run:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    logger.info("Starting the test runner...")
    
    # Use standard unittest runner without async complications
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    return {
        'testsRun': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'skipped': len(result.skipped),
        'wasSuccessful': result.wasSuccessful()
    }


if __name__ == "__main__":
    # Check if we're being run programmatically
    if os.environ.get('CELSIUS_TEST_MODE') == '1':
        # Run programmatically and exit
        result = run_tests_programmatically()
        print(f"Test Results: {result}")
        sys.exit(0 if result['wasSuccessful'] else 1)
    
    # Ensure the script is run from the project root for correct pathing
    if "src" not in [p.name for p in Path.cwd().iterdir()]:
        logger.warning("This script is best run from the 'Celsius AI' project root directory.")

    main()


