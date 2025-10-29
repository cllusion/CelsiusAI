"""
Core compatibility wrapper for incremental refactor.

Exports a minimal set of helpers from the legacy `celsius_ultimate_hub`
module so we can gradually move implementation into smaller modules
without breaking callers.
"""

from __future__ import annotations

import importlib
from typing import Any

_hub = importlib.import_module("src.hub.celsius_ultimate_hub")


def initialize_async_components(*args: Any, **kwargs: Any) -> Any:
    return getattr(_hub, "initialize_async_components")(*args, **kwargs)


def relogin(*args: Any, **kwargs: Any) -> Any:
    return getattr(_hub, "relogin")(*args, **kwargs)


def get_celsius_ultimate_hub_class():
    """Return the CelsiusUltimateHub class from the legacy module."""
    return getattr(_hub, "CelsiusUltimateHub")


__all__ = ["initialize_async_components", "relogin", "get_celsius_ultimate_hub_class"]
