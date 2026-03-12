"""
src.hub — Celsius AI Hub package.

This package exposes the CelsiusUltimateHub class and its decomposed helpers.

The monolith is being split incrementally into focused sub-modules:
  core.py       — initialization & async helpers (compatibility wrapper)
  ui.py         — tab/widget creation functions
  login.py      — login dialog
  account.py    — account management
  ingestion.py  — ingestion candidate helpers
  async_loop.py — AsyncTkinter event loop bridge

Import the Hub class via:
    from src.hub import CelsiusUltimateHub
"""

from __future__ import annotations

try:
    from src.hub.celsius_ultimate_hub import CelsiusUltimateHub
except Exception:
    CelsiusUltimateHub = None  # type: ignore

__all__ = ["CelsiusUltimateHub"]
