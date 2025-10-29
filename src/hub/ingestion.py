"""Helpers for managing ingestion candidate files used by the Admin UI.

This module provides pure functions so unit tests can exercise the
ingestion approve/reject flow without creating GUI widgets.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List


def candidates_path(project_root: Path) -> Path:
    return project_root / "data" / "ingestion_candidates.json"


def approved_path(project_root: Path) -> Path:
    return project_root / "data" / "ingestion_approved.json"


def load_candidates(project_root: Path) -> List[Any]:
    p = candidates_path(project_root)
    if not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except Exception:
        return []


def save_candidates(project_root: Path, candidates: List[Any]) -> None:
    p = candidates_path(project_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)


def approve_candidate(project_root: Path, index: int) -> bool:
    candidates = load_candidates(project_root)
    if index < 0 or index >= len(candidates):
        return False
    item = candidates.pop(index)
    # append to approved
    ap = approved_path(project_root)
    approved = []
    if ap.exists():
        try:
            with open(ap, "r", encoding="utf-8") as f:
                approved = json.load(f) or []
        except Exception:
            approved = []
    approved.append(item)
    ap.parent.mkdir(parents=True, exist_ok=True)
    with open(ap, "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)
    save_candidates(project_root, candidates)
    return True


def reject_candidate(project_root: Path, index: int) -> bool:
    candidates = load_candidates(project_root)
    if index < 0 or index >= len(candidates):
        return False
    candidates.pop(index)
    save_candidates(project_root, candidates)
    return True
