"""Report generation helpers for the Hub.

Standalone functions that accept a ``hub`` instance as the first argument so
they can be called from the UltimateHub class while keeping report-generation
logic in one focused module.

The pattern mirrors ``src/hub/ui.py``: each function takes ``hub: Any``
and uses ``getattr`` / attribute access on the hub.
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from tkinter import messagebox

logger = logging.getLogger("celsius.hub.reports")

# Resolve project root relative to this file
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _project_root(hub: Any) -> Path:
    """Return the project root, preferring the hub's attribute."""
    return getattr(hub, "PROJECT_ROOT", _PROJECT_ROOT)


# --------------------------------------------------------------------------- #
#   Learning reports                                                            #
# --------------------------------------------------------------------------- #


def refresh_learning_reports(hub: Any) -> None:
    """Refresh and display learning reports in the hub's reports text widget."""
    try:
        hub.learning_reports_text.delete("1.0", "end")

        reports_dir = _project_root(hub) / "learning_reports"
        if not reports_dir.exists():
            hub.learning_reports_text.insert(
                "1.0",
                "📁 No learning reports directory found.\n\nReports will appear here when the learning system generates them.",
            )
            return

        report_files = list(reports_dir.glob("celsius_learning_report_*.txt"))
        report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        if not report_files:
            hub.learning_reports_text.insert(
                "1.0", "No learning reports found. Reports will appear here after the learning system runs."
            )
            return

        report_text = "CELSIUS AI LEARNING REPORTS\n"
        report_text += "=" * 60 + "\n\n"

        for i, report_file in enumerate(report_files[:5]):
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    content = f.read()
                report_text += f"Report #{i + 1}: {report_file.name}\n"
                report_text += content
                report_text += "\n" + ("-" * 60) + "\n\n"
            except Exception as e:
                report_text += f"Error reading {report_file.name}: {e}\n\n"

        if len(report_files) > 5:
            report_text += f"\n{len(report_files) - 5} additional reports available in learning_reports folder."

        hub.learning_reports_text.insert("1.0", report_text)

    except Exception as e:
        hub.learning_reports_text.delete("1.0", "end")
        hub.learning_reports_text.insert("1.0", f"❌ Error loading learning reports:\n{e}")


def generate_learning_report(hub: Any) -> None:
    """Trigger generation of a new learning report via the web learning integration."""
    try:
        hub._msg(messagebox.showinfo, "Generating", "Generating a new learning report...")

        from src.learning.celsius_web_learning_integration import initialize_web_learning

        integration = initialize_web_learning()
        report = integration.generate_daily_report()

        if report:
            hub._msg(
                messagebox.showinfo,
                "Report Generated",
                "A new learning report was generated and saved to the learning_reports folder.",
            )
            refresh_learning_reports(hub)
        else:
            hub._msg(
                messagebox.showwarning,
                "No Report",
                "Could not generate a report right now. Ensure Web Learning is initialized and try again.",
            )
    except Exception as e:
        hub._msg(messagebox.showerror, "Error", f"Failed to generate learning report:\n{e}")


# --------------------------------------------------------------------------- #
#   Hourly reports                                                              #
# --------------------------------------------------------------------------- #


def refresh_hourly_reports_list(hub: Any) -> None:
    """Populate the hourly reports treeview with files from data/reports."""
    try:
        reports_dir = _project_root(hub) / "data" / "reports"
        tree = getattr(hub, "hourly_reports_tree", None)
        if tree is None:
            return

        # Clear existing rows
        for row in tree.get_children():
            tree.delete(row)

        if not reports_dir.exists():
            return

        files = sorted(
            reports_dir.glob("celsius_hourly_report_*.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for f in files:
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                mtime = "unknown"
            tree.insert("", "end", values=(f.name, mtime))
    except Exception:
        pass  # non-fatal


async def periodic_poll_hourly_reports(hub: Any) -> None:
    """Poll the hourly reports DB periodically and update the Reports tab.

    Checks ``PROJECT_ROOT/data/celsius_reports.db`` every 60 seconds and
    schedules a main-thread UI update when a new report row is found.
    """
    try:
        import aiosqlite
    except ImportError:
        logger.warning("aiosqlite not available; hourly report polling disabled")
        return

    db_path = _project_root(hub) / "data" / "celsius_reports.db"
    while True:
        try:
            if not getattr(hub, "enable_hourly_updates", True):
                await asyncio.sleep(60)
                continue

            if not db_path.exists():
                hub.schedule_on_main_thread(update_hourly_summary_text, hub, "No hourly reports DB found.")
                await asyncio.sleep(60)
                continue

            async with aiosqlite.connect(db_path) as db:
                async with db.execute(
                    "SELECT id, timestamp, report_data FROM hourly_reports ORDER BY id DESC LIMIT 1"
                ) as cur:
                    row = await cur.fetchone()
                    if row:
                        row_id, ts, data = row[0], row[1], row[2]
                        last_id = getattr(hub, "_last_hourly_id", None)
                        if row_id != last_id:
                            hub._last_hourly_id = row_id
                            snippet = (data[:1000] + "...") if data and len(data) > 1000 else (data or "")
                            summary = f"{ts}\n{snippet}"
                            hub.schedule_on_main_thread(update_hourly_summary_text, hub, summary)
            await asyncio.sleep(60)
        except Exception:
            logger.exception("Error polling hourly reports")
            await asyncio.sleep(60)


def update_hourly_summary_text(hub: Any, text: str) -> None:
    """Update the hourly summary widget on the main thread."""
    try:
        if hasattr(hub, "hourly_summary_text"):
            hub.hourly_summary_text.delete("1.0", "end")
            hub.hourly_summary_text.insert("1.0", text)
    except Exception:
        logger.exception("Failed to update hourly summary UI")


# --------------------------------------------------------------------------- #
#   System reports                                                              #
# --------------------------------------------------------------------------- #


def show_guardian_report(hub: Any) -> None:
    """Display Guardian system report in the hub's system reports text widget."""
    try:
        hub.system_reports_text.delete("1.0", "end")

        report_text = "🛡️ GUARDIAN SYSTEM REPORT\n"
        report_text += "=" * 60 + "\n\n"

        guardian_db = _project_root(hub) / "data" / "celsius_guardian.db"
        if guardian_db.exists():
            report_text += "📊 Guardian Database: ✅ Active\n"
            try:
                conn = sqlite3.connect(guardian_db)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT timestamp, service_name, event_type, message
                    FROM guardian_logs
                    ORDER BY timestamp DESC
                    LIMIT 10
                    """
                )
                events = cursor.fetchall()
                if events:
                    report_text += f"\n🔍 Recent Guardian Events ({len(events)} shown):\n"
                    report_text += "-" * 60 + "\n"
                    for event in events:
                        timestamp, service, event_type, message = event
                        report_text += f"[{timestamp}] {service} - {event_type}\n"
                        report_text += f"  {message}\n\n"
                conn.close()
            except Exception as e:
                report_text += f"⚠️ Error reading Guardian database: {e}\n"
        else:
            report_text += "📊 Guardian Database: ❌ Not Found\n"

        # Check Guardian processes using psutil
        try:
            import psutil

            guardian_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
                try:
                    cmdline = " ".join(proc.info.get("cmdline") or [])
                    if "celsius_ultimate_guardian" in cmdline:
                        uptime = datetime.now() - datetime.fromtimestamp(proc.info.get("create_time", 0))
                        guardian_processes.append({"pid": proc.info.get("pid"), "uptime": uptime})
                except Exception:
                    pass

            if guardian_processes:
                report_text += f"\n🛡️ Active Guardian Processes: {len(guardian_processes)}\n"
                for guard in guardian_processes:
                    hours = guard["uptime"].seconds // 3600
                    minutes = (guard["uptime"].seconds % 3600) // 60
                    report_text += (
                        f"  • PID {guard['pid']}: {guard['uptime'].days}d {hours}h {minutes}m uptime\n"
                    )
            else:
                report_text += "\n❌ No Guardian processes detected!\n"
        except ImportError:
            report_text += "\n⚠️ psutil not available; process check skipped\n"

        report_text += f"\n📅 Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        hub.system_reports_text.insert("1.0", report_text)

    except Exception as e:
        hub.system_reports_text.delete("1.0", "end")
        hub.system_reports_text.insert("1.0", f"❌ Error generating Guardian report:\n{e}")


def show_security_report(hub: Any) -> None:
    """Display security system report in the hub's system reports text widget."""
    try:
        hub.system_reports_text.delete("1.0", "end")

        report_text = "🔒 SECURITY SYSTEM REPORT\n"
        report_text += "=" * 60 + "\n\n"

        username = getattr(hub, "username", "unknown")
        email_notifier = getattr(hub, "email_notifier", None)

        report_text += f"👤 Current User: {username}\n"
        report_text += "🔐 Authentication: ✅ Active\n"
        report_text += f"📧 Email Notifications: {'✅ Enabled' if email_notifier else '❌ Disabled'}\n\n"

        auth_db = _project_root(hub) / "celsius_auth.json"
        report_text += (
            "🗃️ Authentication Database: ✅ Present\n"
            if auth_db.exists()
            else "🗃️ Authentication Database: ❌ Missing\n"
        )

        report_text += "\n🛡️ System Integrity:\n"
        critical_files = [
            "src/guardian/celsius_ultimate_guardian.py",
            "src/hub/celsius_ultimate_hub.py",
            "src/core/main.py",
        ]
        for file_path in critical_files:
            full_path = _project_root(hub) / file_path
            if full_path.exists():
                report_text += f"  ✅ {file_path}\n"
            else:
                report_text += f"  ❌ {file_path} - MISSING!\n"

        report_text += f"\n📅 Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        hub.system_reports_text.insert("1.0", report_text)

    except Exception as e:
        hub.system_reports_text.delete("1.0", "end")
        hub.system_reports_text.insert("1.0", f"❌ Error generating security report:\n{e}")


def show_performance_report(hub: Any) -> None:
    """Display performance report in the hub's system reports text widget."""
    try:
        hub.system_reports_text.delete("1.0", "end")

        report_text = "⚡ PERFORMANCE REPORT\n"
        report_text += "=" * 60 + "\n\n"

        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            report_text += "💻 System Resources:\n"
            report_text += f"  CPU Usage: {cpu_percent:.1f}%\n"
            report_text += (
                f"  Memory Usage: {memory.percent:.1f}% ({memory.used // 1024**3:.1f}GB"
                f" / {memory.total // 1024**3:.1f}GB)\n"
            )
            report_text += (
                f"  Disk Usage: {disk.percent:.1f}% ({disk.used // 1024**3:.1f}GB"
                f" / {disk.total // 1024**3:.1f}GB)\n\n"
            )

            celsius_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info", "cpu_percent"]):
                try:
                    cmdline = " ".join(proc.info.get("cmdline") or [])
                    if any(term in cmdline for term in ["celsius", "guardian", "hub"]):
                        celsius_processes.append(
                            {
                                "pid": proc.info.get("pid"),
                                "memory": (
                                    proc.info.get("memory_info").rss // 1024**2
                                    if proc.info.get("memory_info")
                                    else 0
                                ),
                                "cpu": proc.info.get("cpu_percent", 0),
                            }
                        )
                except Exception:
                    pass

            if celsius_processes:
                total_memory = sum(p["memory"] for p in celsius_processes)
                report_text += f"🔧 Celsius AI Processes: {len(celsius_processes)} running\n"
                report_text += f"  Total Memory Usage: {total_memory}MB\n"
                report_text += "  Process Details:\n"
                for proc in celsius_processes:
                    report_text += f"    • PID {proc['pid']}: {proc['memory']}MB RAM\n"
            else:
                report_text += "❌ No Celsius AI processes detected\n"

        except ImportError:
            report_text += "⚠️ psutil not available; resource metrics skipped\n"

        report_text += f"\n📅 Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        hub.system_reports_text.insert("1.0", report_text)

    except Exception as e:
        hub.system_reports_text.delete("1.0", "end")
        hub.system_reports_text.insert("1.0", f"❌ Error generating performance report:\n{e}")


__all__ = [
    "refresh_learning_reports",
    "generate_learning_report",
    "refresh_hourly_reports_list",
    "periodic_poll_hourly_reports",
    "update_hourly_summary_text",
    "show_guardian_report",
    "show_security_report",
    "show_performance_report",
]
