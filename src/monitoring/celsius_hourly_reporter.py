#!/usr/bin/env python3
"""
Celsius AI - Hourly System Reporter
===================================
Generates comprehensive hourly reports of all Celsius AI activities,
system health, and performance metrics.

Features:
- System activity tracking
- Service health monitoring
- Performance metrics
- Email notifications (optional)
- Database logging
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import psutil
import aiosqlite
import aiofiles

# --- Project Setup ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


class CelsiusHourlyReporter:
    """
    Generates hourly system reports and sends notifications.
    """

    def __init__(self, report_interval: int = 3600):
        """
        Initialize the hourly reporter.

        Args:
            report_interval: Interval in seconds between reports (default: 3600 = 1 hour)
        """
        self.report_interval = report_interval
        self.is_running = False
        self.last_report_time = datetime.now()

        # Database paths
        self.data_dir = PROJECT_ROOT / "data"
        self.hub_db = self.data_dir / "celsius_hub.db"
        self.guardian_db = self.data_dir / "celsius_guardian.db"
        self.reports_db = self.data_dir / "celsius_reports.db"

        # Email notifier (optional)
        self.email_notifier = None

    async def initialize(self):
        """Initialize the reporter and databases."""
        self.data_dir.mkdir(exist_ok=True)
        await self.setup_database()

        # Try to initialize email notifier if available (use lazy accessor to avoid import-time side-effects)
        try:
            from src.utils.enhanced_email_system import get_enhanced_notifier

            notifier = get_enhanced_notifier()
            notifier.config_file = PROJECT_ROOT / "config" / "email_config.json"
            await notifier.initialize()
            self.email_notifier = notifier
            logger.info("Email notifications enabled for hourly reports")
        except ImportError:
            # Try alternative import path
            try:
                from enhanced_email_system import get_enhanced_notifier

                notifier = get_enhanced_notifier()
                notifier.config_file = PROJECT_ROOT / "config" / "email_config.json"
                await notifier.initialize()
                self.email_notifier = notifier
                logger.info("Email notifications enabled for hourly reports")
            except Exception as e:
                logger.warning(f"Email notifications disabled: {e}")
                self.email_notifier = None
        except Exception as e:
            logger.warning(f"Email notifications disabled: {e}")
            self.email_notifier = None

        logger.info("Hourly Reporter initialized")

    async def setup_database(self):
        """Create the reports database tables."""
        try:
            async with aiosqlite.connect(self.reports_db) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS hourly_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        report_type TEXT NOT NULL,
                        report_data TEXT NOT NULL,
                        services_running INTEGER,
                        cpu_percent REAL,
                        memory_percent REAL,
                        disk_percent REAL
                    )
                """
                )
                await db.commit()
            logger.info("Reports database initialized")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage("/")._asdict(),
            "processes": len(psutil.pids()),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
        }

    async def get_service_status(self) -> Dict[str, Any]:
        """Get status of all Celsius services."""
        services = {}
        python_processes = []

        # Find all Python processes
        for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
            try:
                if proc.info["name"] and "python" in proc.info["name"].lower():
                    cmdline = proc.info.get("cmdline", [])
                    if cmdline:
                        python_processes.append(
                            {
                                "pid": proc.info["pid"],
                                "cmdline": " ".join(cmdline),
                                "create_time": datetime.fromtimestamp(proc.info["create_time"]),
                            }
                        )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Identify known services
        service_patterns = {
            "Ultimate Hub": "celsius_ultimate_hub",
            "Enhanced Dashboard": "enhanced_mobile_dashboard",
            "Core AI Engine": "main.py",
            "Guardian System": "celsius_ultimate_guardian",
            "Web Learning": "celsius_web_learning",
            "Hourly Reporter": "celsius_hourly_reporter",
        }

        for service_name, pattern in service_patterns.items():
            for proc in python_processes:
                if pattern in proc["cmdline"]:
                    services[service_name] = {
                        "status": "Running",
                        "pid": proc["pid"],
                        "uptime": str(datetime.now() - proc["create_time"]).split(".")[0],
                    }
                    break
            if service_name not in services:
                services[service_name] = {"status": "Stopped"}

        return services

    async def get_recent_activities(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent activities from the Hub database."""
        activities = []

        if not self.hub_db.exists():
            return activities

        try:
            since = datetime.now() - timedelta(hours=hours)
            async with aiosqlite.connect(self.hub_db) as db:
                async with db.execute(
                    "SELECT timestamp, service, action, details FROM activity_log WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 100",
                    (since.strftime("%Y-%m-%d %H:%M:%S"),),
                ) as cursor:
                    async for row in cursor:
                        activities.append({"timestamp": row[0], "service": row[1], "action": row[2], "details": row[3]})
        except Exception as e:
            logger.error(f"Error fetching activities: {e}")

        return activities

    async def generate_report(self) -> str:
        """Generate a comprehensive hourly report."""
        now = datetime.now()

        # Gather all data
        system_metrics = await self.get_system_metrics()
        services = await self.get_service_status()
        activities = await self.get_recent_activities(1)

        # Build report
        report = f"\n{'=' * 80}\n"
        report += f"🛡️ CELSIUS AI - HOURLY SYSTEM REPORT\n"
        report += f"{'=' * 80}\n"
        report += f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Report Period: Last 1 hour\n\n"

        # Service Status
        running_services = [s for s, info in services.items() if info["status"] == "Running"]
        report += f"📊 SERVICE STATUS:\n"
        report += f"{'-' * 80}\n"
        for service_name, info in services.items():
            status_icon = "🟢" if info["status"] == "Running" else "🔴"
            report += f"{status_icon} {service_name}: {info['status']}"
            if "pid" in info:
                report += f" (PID: {info['pid']}, Uptime: {info['uptime']})"
            report += "\n"
        report += f"\nRunning Services: {len(running_services)}/{len(services)}\n\n"

        # System Metrics
        report += f"💻 SYSTEM METRICS:\n"
        report += f"{'-' * 80}\n"
        report += f"CPU Usage: {system_metrics['cpu_percent']}%\n"
        report += f"Memory Usage: {system_metrics['memory']['percent']}% "
        report += f"({system_metrics['memory']['used'] // (1024**3)}GB / {system_metrics['memory']['total'] // (1024**3)}GB)\n"
        report += f"Disk Usage: {system_metrics['disk']['percent']}% "
        report += (
            f"({system_metrics['disk']['used'] // (1024**3)}GB / {system_metrics['disk']['total'] // (1024**3)}GB)\n"
        )
        report += f"Total Processes: {system_metrics['processes']}\n"
        report += f"System Boot Time: {system_metrics['boot_time']}\n\n"

        # Activity Summary
        report += f"📝 ACTIVITY SUMMARY (Last Hour):\n"
        report += f"{'-' * 80}\n"
        if activities:
            # Group by service
            service_activities = {}
            for activity in activities:
                service = activity["service"]
                if service not in service_activities:
                    service_activities[service] = []
                service_activities[service].append(activity)

            report += f"Total Activities: {len(activities)}\n\n"
            for service, acts in service_activities.items():
                report += f"  • {service}: {len(acts)} activities\n"
                # Show last 3 activities for this service
                for act in acts[:3]:
                    report += f"    - [{act['timestamp']}] {act['action']}: {act['details'][:60]}\n"
        else:
            report += "No activities recorded in the last hour.\n"

        report += f"\n{'=' * 80}\n"
        report += f"Report generated by Celsius AI Hourly Reporter\n"
        report += f"{'=' * 80}\n"

        # Store report in database
        await self.store_report(now, report, len(running_services), system_metrics)

        return report

    async def store_report(self, timestamp: datetime, report: str, services_running: int, metrics: Dict[str, Any]):
        """Store the generated report in the database."""
        try:
            async with aiosqlite.connect(self.reports_db) as db:
                await db.execute(
                    """INSERT INTO hourly_reports 
                       (timestamp, report_type, report_data, services_running, cpu_percent, memory_percent, disk_percent)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "hourly",
                        report,
                        services_running,
                        metrics["cpu_percent"],
                        metrics["memory"]["percent"],
                        metrics["disk"]["percent"],
                    ),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error storing report: {e}")

    async def send_report_email(self, report: str):
        """Send the report via email if email notifier is available."""
        if not self.email_notifier:
            return

        try:
            await self.email_notifier.send_notification(
                "Hourly Report", "Celsius AI - Hourly System Report", report, "normal"
            )
            logger.info("Hourly report email sent successfully")
        except Exception as e:
            logger.error(f"Failed to send report email: {e}")

    async def run(self):
        """Main loop - generate reports at specified intervals."""
        self.is_running = True
        logger.info(f"Hourly Reporter started - generating reports every {self.report_interval} seconds")

        while self.is_running:
            try:
                now = datetime.now()
                time_since_last = (now - self.last_report_time).total_seconds()

                if time_since_last >= self.report_interval:
                    logger.info("Generating hourly report...")
                    report = await self.generate_report()

                    # Print to console
                    print(report)
                    # Also save a plain-text copy to logs for easy inspection
                    try:
                        await self.save_report_file(report)
                    except Exception:
                        logger.exception("Failed to save report file")

                    # Send email if configured
                    await self.send_report_email(report)

                    self.last_report_time = now
                    logger.info("Hourly report generated and distributed")

                # Sleep for a minute before checking again
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in report generation loop: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def stop(self):
        """Stop the reporter."""
        self.is_running = False
        logger.info("Hourly Reporter stopped")

    async def save_report_file(self, report: str) -> None:
        """Save the report as a timestamped .txt file under data/reports.

        Uses aiofiles for non-blocking file I/O.
        """
        try:
            reports_dir = self.data_dir / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"celsius_hourly_report_{timestamp}.txt"
            filepath = reports_dir / filename
            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(report)
            logger.info(f"Saved hourly report to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save report file: {e}")

    async def save_report_file(self, report_str: str):
        """Save a plain-text copy of the report into the logs directory."""
        try:
            logs_dir = PROJECT_ROOT / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = logs_dir / f"celsius_report_{timestamp}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(report_str)

            # Keep only the most recent 48 reports (48 hours)
            files = sorted(logs_dir.glob("celsius_report_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old in files[48:]:
                try:
                    old.unlink()
                except Exception:
                    pass
        except Exception:
            logger.exception("Error saving report file")


async def main():
    """Main entry point for the hourly reporter."""
    import argparse

    parser = argparse.ArgumentParser(description="Celsius AI Hourly Reporter")
    parser.add_argument(
        "--interval", type=int, default=3600, help="Report interval in seconds (default: 3600 = 1 hour)"
    )
    parser.add_argument("--test", action="store_true", help="Generate one report immediately and exit")
    args = parser.parse_args()

    reporter = CelsiusHourlyReporter(report_interval=args.interval)
    await reporter.initialize()

    if args.test:
        # Generate one report and exit
        logger.info("Test mode - generating single report...")
        report = await reporter.generate_report()
        print(report)
        # save a plain-text copy when running in test mode as well
        try:
            await reporter.save_report_file(report)
        except Exception:
            logger.exception("Failed to save report file in test mode")
        logger.info("Test complete")
    else:
        # Run continuous reporting
        try:
            await reporter.run()
        except KeyboardInterrupt:
            logger.info("Reporter interrupted by user")
            await reporter.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Avoid printing non-encodable emojis to Windows consoles
        print("\nHourly Reporter terminated by user.")
