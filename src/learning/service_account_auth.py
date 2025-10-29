"""
Stubbed service account helper.

The real implementation depends on `google.oauth2` and `google.auth`, which
are optional for this project. To avoid static-analysis complaints in the
main tree, this stub returns None and is safe to import. If you want the
original implementation back (for prototype/provider testing), use the
archived copy at `archive/prototypes/service_account_auth.py`.
"""

from typing import Optional
import os


def get_token_from_service_account(json_path: Optional[str] = None, scopes: Optional[list] = None) -> Optional[str]:
    """Return None (stub). Install google-auth and enable the archived helper for real tokens."""
    return None
