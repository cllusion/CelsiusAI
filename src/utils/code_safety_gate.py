"""
Code Safety Gate for Celsius AI Self-Improvement

Enforces that the test suite passes before any auto-generated code change is
written to disk. Use this module anywhere code is about to be modified
autonomously (self-improvement, code-gen daemons, ruff auto-fix runs, etc.).

Usage
-----
from src.utils.code_safety_gate import CodeSafetyGate

gate = CodeSafetyGate()

# Before applying a change
result = gate.check(changed_files=["src/core/assistant.py"])
if result.passed:
    # apply the change
    ...
else:
    logger.error("Safety gate blocked change: %s", result.reason)
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

# Project root is three levels up from this file (src/utils/code_safety_gate.py)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class GateResult:
    """Result from a safety gate check."""

    passed: bool
    reason: str = ""
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class CodeSafetyGate:
    """
    Runs the test suite and optional linting before allowing a code change.

    Parameters
    ----------
    project_root:
        Path to the project root (defaults to auto-detected root).
    test_dir:
        Relative path to the test directory (default: ``tests``).
    timeout:
        Maximum seconds for the test suite to run (default: 120).
    run_lint:
        Whether to also run ``ruff check`` before tests (default: True).
    python:
        Python executable to use (default: same interpreter as the caller).
    """

    def __init__(
        self,
        project_root: Path | str | None = None,
        test_dir: str = "tests",
        timeout: int = 120,
        run_lint: bool = True,
        python: str | None = None,
    ) -> None:
        self.project_root = Path(project_root) if project_root else _PROJECT_ROOT
        self.test_dir = self.project_root / test_dir
        self.timeout = timeout
        self.run_lint = run_lint
        self.python = python or sys.executable

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, changed_files: Sequence[str | Path] | None = None) -> GateResult:
        """
        Run linting + tests and return a GateResult.

        Parameters
        ----------
        changed_files:
            Optional list of files that will be changed. Used for targeted
            linting. If None, the whole project is linted.
        """
        if self.run_lint:
            lint_result = self._run_lint(changed_files)
            if not lint_result.passed:
                return lint_result

        return self._run_tests()

    def check_or_raise(self, changed_files: Sequence[str | Path] | None = None) -> None:
        """Like ``check`` but raises ``RuntimeError`` if the gate fails."""
        result = self.check(changed_files)
        if not result.passed:
            raise RuntimeError(f"Safety gate failed: {result.reason}\n{result.stderr}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_lint(self, files: Sequence[str | Path] | None) -> GateResult:
        """Run ruff check on the specified files (or full project)."""
        ruff = shutil.which("ruff") or self.python + " -m ruff"
        targets = [str(f) for f in files] if files else [str(self.project_root / "src")]

        cmd = [*ruff.split(), "check", "--quiet", *targets]
        logger.debug("Safety gate lint: %s", " ".join(cmd))

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root,
            )
        except subprocess.TimeoutExpired:
            return GateResult(passed=False, reason="Lint timed out after 30s")
        except FileNotFoundError:
            # ruff not available — skip lint, don't block
            logger.warning("ruff not found; skipping lint gate")
            return GateResult(passed=True, reason="ruff not found; lint skipped")

        if proc.returncode != 0:
            return GateResult(
                passed=False,
                reason="Lint errors detected — fix before applying change",
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )

        return GateResult(passed=True, reason="lint passed")

    def _run_tests(self) -> GateResult:
        """Run pytest and return the result."""
        if not self.test_dir.exists():
            logger.warning("Test directory %s not found; skipping test gate", self.test_dir)
            return GateResult(passed=True, reason="test directory not found; tests skipped")

        cmd = [
            self.python,
            "-m",
            "pytest",
            str(self.test_dir),
            "--tb=short",
            "-q",
            "--no-header",
        ]
        logger.info("Safety gate tests: %s", " ".join(cmd))

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.project_root,
            )
        except subprocess.TimeoutExpired:
            return GateResult(
                passed=False,
                reason=f"Tests timed out after {self.timeout}s",
            )
        except FileNotFoundError:
            return GateResult(passed=False, reason="Python interpreter not found")

        if proc.returncode != 0:
            return GateResult(
                passed=False,
                reason="Test suite FAILED — changes blocked until tests pass",
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )

        return GateResult(
            passed=True,
            reason="all tests passed",
            returncode=0,
            stdout=proc.stdout,
        )


# ---------------------------------------------------------------------------
# Convenience decorator
# ---------------------------------------------------------------------------

def requires_tests_pass(func):
    """
    Decorator that runs the safety gate before executing the wrapped function.

    The wrapped function must accept ``project_root`` as the first positional
    argument or keyword argument, or the decorator will use the auto-detected
    project root.

    Example
    -------
    @requires_tests_pass
    async def apply_ruff_fixes(project_root, files):
        ...
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        root = kwargs.get("project_root") or (args[0] if args else None)
        gate = CodeSafetyGate(project_root=root if isinstance(root, (str, Path)) else None)
        result = gate.check()
        if not result.passed:
            logger.error(
                "Safety gate BLOCKED call to %s: %s", func.__name__, result.reason
            )
            raise RuntimeError(
                f"Safety gate blocked {func.__name__}: {result.reason}"
            )
        return func(*args, **kwargs)

    return wrapper
