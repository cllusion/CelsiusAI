"""
Light shim for `enhanced_email_system`. Many modules import this via two paths:
- `src.utils.enhanced_email_system` (preferred)
- `enhanced_email_system` (legacy)

This file attempts to import the preferred module and exposes a minimal
`EnhancedEmailNotifier` class when the real implementation is not available.
This prevents static/analyzer warnings and makes the codebase easier to run
without enabling optional features.
"""

try:
    from src.utils.enhanced_email_system import EnhancedEmailNotifier  # type: ignore
except Exception:

    class EnhancedEmailNotifier:
        def __init__(self, *args, **kwargs):
            self.config_file = None

        async def initialize(self):
            return None

        def send(self, *args, **kwargs):
            return None

        async def send_async(self, *args, **kwargs):
            return None

        def is_enabled(self):
            return False
