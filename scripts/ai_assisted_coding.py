#!/usr/bin/env python3
"""
AI-assisted coding scaffold (safe, human-in-the-loop)

This utility records a proposed change described by the user (or an AI),
saves it under `proposals/` as a JSON file with a placeholder for the
patch content, runs the project's test suite, and stores the test output
so a human can review before applying any changes.

Usage:
  python scripts/ai_assisted_coding.py --title "Add feature X" --desc "..." [--apply]

Important: This script does NOT apply patches automatically. It is a
safe scaffold for generating and reviewing proposed changes.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROPOSALS = ROOT / "proposals"
PROPOSALS.mkdir(parents=True, exist_ok=True)


def run_tests() -> str:
    """Run pytest and return captured output (stdout+stderr)."""
    try:
        cmd = [sys.executable, "-m", "pytest", "tests/", "-q"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        out = proc.stdout + "\n" + proc.stderr
        return out
    except Exception as e:
        return f"ERROR running tests: {e}"


def create_proposal(title: str, description: str, patch: str | None = None) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip().replace(" ", "_")[:60]
    filename = PROPOSALS / f"proposal_{ts}_{safe_title}.json"
    payload = {
        "title": title,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "status": "proposed",
        "patch": patch or "",  # place for AI or human to put a unified diff
        "test_output": None,
    }
    filename.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return filename


def save_test_output(proposal_path: Path, output: str) -> None:
    try:
        data = json.loads(proposal_path.read_text(encoding="utf-8"))
        data["test_output"] = output
        proposal_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--title", required=True, help="Short title for the proposal")
    p.add_argument("--desc", required=True, help="Longer description of the change")
    p.add_argument("--patch", help="Optional patch content (unified diff) to store in the proposal")
    args = p.parse_args()

    proposal = create_proposal(args.title, args.desc, args.patch)
    print(f"Created proposal: {proposal}")

    print("Running tests (this may take a moment)...")
    out = run_tests()
    save_test_output(proposal, out)
    print("Test run complete. Test output saved into the proposal file.")
    print("Review the proposal in the 'proposals' folder and apply patches manually after review.")


if __name__ == "__main__":
    main()
