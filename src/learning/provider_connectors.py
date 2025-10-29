"""
Provider connectors for AI-to-AI ingestion.

This module implements a small generic HTTP connector that posts a
fetch_payload to a configured endpoint and returns text content.

Configuration is read from PROJECT_ROOT/config/ai_providers.json (not committed
by default). See config/ai_providers.example.json for a template.
"""

from pathlib import Path
import json
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "ai_providers.json"


def load_providers() -> List[Dict[str, Any]]:
    if not CONFIG_FILE.exists():
        return []
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg.get("providers", [])
    except Exception:
        return []


def normalize_headers(h: Optional[Dict[str, str]]) -> Dict[str, str]:
    return h or {}


def build_fetch_payload(p: Dict[str, Any]) -> Dict[str, Any]:
    return p.get("fetch_payload", {"prompt": "Generate a short safe conversation between two AIs."})


def provider_summary(provider: Dict[str, Any]) -> str:
    return f"{provider.get('name')}@{provider.get('endpoint','(no endpoint)')}"
