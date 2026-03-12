"""Process and service monitoring helpers for the Hub.

Standalone functions that accept a ``hub`` instance as the first argument so
they can be called from the UltimateHub class while keeping monitoring logic
in one focused module.

The pattern mirrors ``src/hub/ui.py``: each function takes ``hub: Any``
and uses ``getattr`` / attribute access to read or write hub state.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("celsius.hub.monitoring")


async def monitor_process_output(hub: Any, service_name: str, process: Any) -> None:
    """Monitor and log the stdout/stderr of a service process.

    Streams output lines to a log file under ``{PROJECT_ROOT}/logs/``.
    """
    project_root: Path = getattr(hub, "PROJECT_ROOT", Path(__file__).resolve().parents[2])
    log_path = project_root / "logs" / f"{service_name.replace(' ', '_').lower()}.log"

    try:
        with open(log_path, "a") as log_file:
            async for line in process.stdout:
                log_file.write(line.decode("utf-8", errors="ignore"))
                log_file.flush()
            async for line in process.stderr:
                log_file.write(f"ERROR: {line.decode('utf-8', errors='ignore')}")
                log_file.flush()
    except Exception as e:
        logger.error("Error monitoring output for %s: %s", service_name, e)


async def periodic_health_check(hub: Any) -> None:
    """Periodically check the health of running services on *hub*.

    Runs indefinitely (until the task is cancelled); checks every 30 seconds.
    """
    while True:
        await asyncio.sleep(30)
        for name, service in hub.services.items():
            if service.get("status") == "Running" and "health_uri" in service:
                await check_service_health(hub, name, service["health_uri"])


async def check_service_health(hub: Any, service_name: str, uri: str) -> None:
    """Check the health of a service by sending a GET request to its health URI."""
    http_session = getattr(hub, "http_session", None)
    if not http_session:
        return
    try:
        import aiohttp

        async with http_session.get(uri, timeout=5) as response:
            if response.status == 200:
                hub.log_activity(service_name, "Health Check", "OK")
            else:
                hub.log_activity(service_name, "Health Check", f"Failed with status {response.status}")
    except Exception as e:
        hub.log_activity(service_name, "Health Check", f"Failed: {e}")


def update_service_status_from_processes(hub: Any) -> None:
    """Update service status by checking actual running Python processes.

    Requires ``psutil``; silently skips if not available.
    """
    try:
        import psutil
    except ImportError:
        return

    try:
        # Get all Python processes
        python_processes = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["name"] and "python" in proc.info["name"].lower():
                    python_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Map service modules to check
        service_module_map = {
            "defender": "celsius_realtime_defender.py",
            "core_ai": "main.py",
            "dashboard": "enhanced_mobile_dashboard.py",
            "guardian": "celsius_ultimate_guardian.py",
            "web_learning": "web_learning",
            "hourly_reporter": "celsius_hourly_reporter.py",
        }

        for service_name, module_pattern in service_module_map.items():
            if service_name not in hub.services:
                continue

            is_running = False
            for proc in python_processes:
                try:
                    cmdline = proc.info.get("cmdline", [])
                    if cmdline and any(module_pattern in str(arg) for arg in cmdline):
                        is_running = True
                        if service_name not in hub.processes:
                            hub.processes[service_name] = proc
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if is_running:
                hub.services[service_name]["status"] = "Running"
            else:
                hub.services[service_name]["status"] = "Stopped"
                if service_name in hub.processes:
                    del hub.processes[service_name]

    except Exception as e:
        logger.error("Error updating service status from processes: %s", e)


def refresh_dashboard(hub: Any) -> None:
    """Refresh the dashboard metrics on *hub* using psutil.

    Updates CPU/memory/disk labels and the service status overview text.
    Requires ``psutil``; logs an error if unavailable.
    """
    try:
        import psutil
        import tkinter as tk

        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        hub.cpu_label.config(text=f"CPU: {cpu_percent}%")
        hub.memory_label.config(
            text=f"Memory: {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)"
        )
        hub.disk_label.config(
            text=f"Disk: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)"
        )

        # Update service status by checking actual running processes
        update_service_status_from_processes(hub)

        # Update service status display
        hub.service_status_text.delete("1.0", tk.END)
        for name, service in hub.services.items():
            status = service.get("status", "Unknown")
            status_symbol = "🟢" if status == "Running" else "🔴" if status == "Stopped" else "⚠️"
            hub.service_status_text.insert(tk.END, f"{status_symbol} {service['name']}: {status}\n")
    except Exception as e:
        logger.error("Dashboard refresh error: %s", e)


__all__ = [
    "monitor_process_output",
    "periodic_health_check",
    "check_service_health",
    "update_service_status_from_processes",
    "refresh_dashboard",
]
