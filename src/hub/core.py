"""
Core compatibility wrapper for incremental refactor.

Exports a minimal set of helpers from the legacy `celsius_ultimate_hub`
module so we can gradually move implementation into smaller modules
without breaking callers.

New focused sub-modules (all follow the ``hub: Any`` standalone-function
pattern from ``src/hub/ui.py``):

- ``src.hub.notifications`` – email notification helpers
- ``src.hub.monitoring``    – process/service monitoring helpers
- ``src.hub.devices``       – hardware/device control helpers
- ``src.hub.reports``       – report generation helpers
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


# Re-export sub-module public APIs so callers can do:
#   from src.hub.core import send_email_notification
# or simply import the sub-modules directly.
from src.hub.notifications import (  # noqa: E402
    ensure_email_notifier,
    send_email_notification,
    reinit_email_clicked,
    periodic_update_email_status,
    update_email_status,
)

from src.hub.monitoring import (  # noqa: E402
    monitor_process_output,
    periodic_health_check,
    check_service_health,
    update_service_status_from_processes,
    refresh_dashboard,
)

from src.hub.devices import (  # noqa: E402
    refresh_hardware_status,
    open_hardware_web,
    set_fan_preset,
    apply_fan_settings,
    toggle_auto_fan,
    set_rgb_preset,
    apply_rgb_settings,
    apply_rgb_effect,
    apply_profile,
    check_temperatures,
)

from src.hub.reports import (  # noqa: E402
    refresh_learning_reports,
    generate_learning_report,
    refresh_hourly_reports_list,
    periodic_poll_hourly_reports,
    update_hourly_summary_text,
    show_guardian_report,
    show_security_report,
    show_performance_report,
)

__all__ = [
    # Legacy
    "initialize_async_components",
    "relogin",
    "get_celsius_ultimate_hub_class",
    # notifications
    "ensure_email_notifier",
    "send_email_notification",
    "reinit_email_clicked",
    "periodic_update_email_status",
    "update_email_status",
    # monitoring
    "monitor_process_output",
    "periodic_health_check",
    "check_service_health",
    "update_service_status_from_processes",
    "refresh_dashboard",
    # devices
    "refresh_hardware_status",
    "open_hardware_web",
    "set_fan_preset",
    "apply_fan_settings",
    "toggle_auto_fan",
    "set_rgb_preset",
    "apply_rgb_settings",
    "apply_rgb_effect",
    "apply_profile",
    "check_temperatures",
    # reports
    "refresh_learning_reports",
    "generate_learning_report",
    "refresh_hourly_reports_list",
    "periodic_poll_hourly_reports",
    "update_hourly_summary_text",
    "show_guardian_report",
    "show_security_report",
    "show_performance_report",
]
