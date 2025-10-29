"""Compatibility shim for code approval.

This module previously contained a full implementation. During consolidation
the canonical implementation moved to `src/core/celsius_code_approval_system.py`.
Keep a small shim here that re-exports the canonical class for backward
compatibility so other internal modules don't break.
"""

try:
    # Preferred canonical implementation
    from src.core.celsius_code_approval_system import CelsiusCodeApprovalSystem
except Exception:
    # As a last-resort fallback, import the archived duplicate (read-only)
    from archive.dups.celsius_code_approval import CelsiusCodeApprovalSystem

__all__ = ["CelsiusCodeApprovalSystem"]
