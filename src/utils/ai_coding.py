"""Small helpers for AI-assisted coding workflows.

These helpers are intentionally minimal: they create proposal files and
offer a helper to run tests. The heavy lifting (patch generation,
applying changes) is left to a human reviewer.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PROPOSALS = ROOT / "proposals"
PROPOSALS.mkdir(parents=True, exist_ok=True)


def create_proposal(title: str, description: str, patch: str | None = None) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip().replace(" ", "_")[:60]
    filename = PROPOSALS / f"proposal_{ts}_{safe_title}.json"
    payload = {
        "title": title,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "status": "proposed",
        "patch": patch or "",
        "test_output": None,
    }
    filename.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return filename


def run_tests() -> str:
    try:
        cmd = [sys.executable, "-m", "pytest", "tests/", "-q"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        return proc.stdout + "\n" + proc.stderr
    except Exception as e:
        return f"ERROR running tests: {e}"


def generate_patch_for_approved_sources(sources: list[str]) -> str:
    """Generate a small proposed patch (informational) that shows how to
    integrate approved sources into the web learning integration.

    This returns a textual diff-like string for human review. It is NOT
    applied automatically by this helper.
    """
    lines = []
    lines.append("--- Proposed change: add approved sources into web learning integration")
    lines.append("File: src/learning/celsius_web_learning_integration.py")
    lines.append("")
    lines.append("# Insert the following in initialize_integration() after web_learner is created:")
    lines.append("approved_sources = [")
    for s in sources:
        lines.append(f"    \"{s}\",")
    lines.append("]")
    lines.append(
        "# The integration will add these to the web_learner.trusted_sources and create an\n# 'approved_sources' learning topic so the learner considers them. Example runtime code:\n"
    )
    lines.append("try:")
    lines.append("    for src in approved_sources:")
    lines.append("        from urllib.parse import urlparse")
    lines.append("        net = urlparse(src).netloc or src")
    lines.append("        self.web_learner.trusted_sources.add(net.lower())")
    lines.append("    topic_name = 'approved_sources'")
    lines.append("    if topic_name not in self.web_learner.learning_topics:")
    lines.append("        self.web_learner.learning_topics[topic_name] = { 'keywords': [], 'sources': [] }")
    lines.append("    for src in approved_sources:")
    lines.append("        if src not in self.web_learner.learning_topics[topic_name]['sources']:")
    lines.append("            self.web_learner.learning_topics[topic_name]['sources'].append(src)")
    lines.append("except Exception as e:")
    lines.append("    # Non-fatal; record and continue")
    lines.append("    pass")

    return "\n".join(lines)
