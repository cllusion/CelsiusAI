"""Email notification helpers for the Hub.

Standalone functions that accept a ``hub`` instance as the first argument so
they can be called from the UltimateHub class while keeping the
notification logic in one focused module.

The pattern mirrors ``src/hub/ui.py``: each function takes ``hub: Any``
and uses ``getattr`` / ``setattr`` to read or write hub state so the
module has no hard import dependency on the hub class.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("celsius.hub.notifications")


async def ensure_email_notifier(hub: Any, force: bool = False) -> None:
    """Ensure the email notifier is initialized on *hub*.

    If initialization fails a background retry task is started.  Calling
    with ``force=True`` will attempt re-initialization even if a notifier
    already exists.
    """
    if getattr(hub, "email_notifier", None) is not None and not force:
        return

    # Avoid creating multiple concurrent retry loops
    existing_task = getattr(hub, "_email_retry_task", None)
    if existing_task and not existing_task.done():
        # a retry loop is already running; still attempt an immediate try
        pass

    try:
        from src.utils.enhanced_email_system import EnhancedEmailNotifier as _EnhancedEmailNotifier
    except Exception:
        _EnhancedEmailNotifier = None

    if _EnhancedEmailNotifier is None:
        logging.info("Email notifier module not available; notifications disabled for now")
        hub._email_last_error = "module_missing"
        hub._email_retry_count = getattr(hub, "_email_retry_count", 0) + 1
        # Start retry loop if not already running
        if not getattr(hub, "_email_retry_task", None):
            hub._email_retry_task = hub.async_loop.create_task(_email_init_retry_loop(hub))
        return

    try:
        from pathlib import Path

        # PROJECT_ROOT is two levels up from the hub package
        _project_root = getattr(hub, "PROJECT_ROOT", Path(__file__).resolve().parents[2])

        notifier = _EnhancedEmailNotifier()
        notifier.config_file = _project_root / "config" / "email_config.json"
        await notifier.initialize()
        hub.email_notifier = notifier
        logging.info("Email notifier initialized successfully (ensure_email_notifier)")
        # Cancel any retry loop if running
        retry_task = getattr(hub, "_email_retry_task", None)
        if retry_task:
            try:
                retry_task.cancel()
            except Exception:
                pass
            hub._email_retry_task = None
    except Exception as e:
        logging.warning("ensure_email_notifier: failed to initialize notifier: %s", e)
        try:
            hub._email_last_error = str(e)
            hub._email_retry_count = getattr(hub, "_email_retry_count", 0) + 1
        except Exception:
            pass
        # Start or ensure a retry loop is running
        if not getattr(hub, "_email_retry_task", None):
            hub._email_retry_task = hub.async_loop.create_task(_email_init_retry_loop(hub))


async def _email_init_retry_loop(hub: Any) -> None:
    """Background retry loop to attempt email notifier initialization.

    Keeps retrying with exponential backoff up to a cap.  Runs until the
    notifier becomes available or the task is cancelled.
    """
    delay = 5
    max_delay = 300
    while getattr(hub, "email_notifier", None) is None:
        try:
            await ensure_email_notifier(hub, force=True)
            if getattr(hub, "email_notifier", None) is not None:
                return
        except Exception as ex:
            logging.debug("_email_init_retry_loop: transient failure, will retry", exc_info=True)
            try:
                hub._email_last_error = str(ex)
                hub._email_retry_count = getattr(hub, "_email_retry_count", 0) + 1
            except Exception:
                pass

        await asyncio.sleep(delay)
        delay = min(delay * 2, max_delay)


async def send_email_notification(hub: Any, tag: str, subject: str, body: str, priority: str = "normal") -> None:
    """Send an email notification via *hub*.

    Attempts to initialize the notifier if not present.  Logs instead of
    raising when notifications cannot be sent.
    """
    try:
        if not getattr(hub, "email_notifier", None):
            await ensure_email_notifier(hub)

        if getattr(hub, "email_notifier", None):
            try:
                await hub.email_notifier.send_notification(tag, subject, body, priority)
                logging.info("Email notification sent: %s", subject)
            except Exception as e:
                logging.warning("Failed to send email notification: %s", e)
        else:
            logging.info("Email notifier not available; skipping sending email: %s", subject)
    except Exception:
        logging.exception("send_email_notification: unexpected error")


async def reinit_email_clicked(hub: Any) -> None:
    """Handler for the Re-init Email button on *hub*.

    Attempts immediate re-initialization and schedules a UI status update.
    """
    try:
        await ensure_email_notifier(hub, force=True)
        hub.schedule_on_main_thread(update_email_status, hub)
    except Exception:
        logging.exception("reinit_email_clicked failed")


def periodic_update_email_status(hub: Any) -> None:
    """Called on the Tk main thread to update the email status label periodically."""
    try:
        update_email_status(hub)
        # also update admin tab labels if present
        try:
            retry_lbl = getattr(hub, "_email_admin_retry_lbl", None)
            if retry_lbl:
                retry_lbl.config(text=f"Retry Count: {getattr(hub, '_email_retry_count', 0)}")
            err_lbl = getattr(hub, "_email_admin_last_error_lbl", None)
            if err_lbl:
                err_lbl.config(text=f"Last Error: {getattr(hub, '_email_last_error', 'None')}")
        except Exception:
            pass
    except Exception:
        logging.debug("periodic_update_email_status: failed to update status", exc_info=True)
    # reschedule
    try:
        hub.root.after(5000, periodic_update_email_status, hub)
    except Exception:
        pass


def update_email_status(hub: Any) -> None:
    """Update the email status label widget on *hub*."""
    try:
        if getattr(hub, "email_notifier", None):
            if hasattr(hub, "email_status_label"):
                hub.email_status_label.config(text="📧 Email: Enabled", foreground="green")
        else:
            if hasattr(hub, "email_status_label"):
                hub.email_status_label.config(text="📧 Email: Disabled", foreground="orange")
    except Exception:
        try:
            if hasattr(hub, "email_status_label"):
                hub.email_status_label.config(text="📧 Email: Unknown", foreground="gray")
        except Exception:
            pass


__all__ = [
    "ensure_email_notifier",
    "send_email_notification",
    "reinit_email_clicked",
    "periodic_update_email_status",
    "update_email_status",
]
