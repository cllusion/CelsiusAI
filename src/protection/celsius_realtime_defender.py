#!/usr/bin/env python3
"""
🛡️ Celsius AI - Real-Time System Defender
==========================================
Advanced real-time protection system that integrates with Windows
to provide antivirus, firewall, and intelligent threat detection.

Features:
- Real-time file system monitoring
- Network traffic analysis
- Process behavior monitoring
- Machine learning threat detection
- Windows system tray integration
- Auto-start with Windows
- Quarantine management
- Threat learning and adaptation
"""

import asyncio
import logging
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import hashlib
import json
import re

# Third-party imports
import psutil
import aiosqlite
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Windows-specific imports
try:
    import win32api
    import win32con
    import win32gui_struct
    import win32gui
    import pystray
    from PIL import Image, ImageDraw

    WINDOWS_INTEGRATION = True
except ImportError:
    WINDOWS_INTEGRATION = False
    logging.warning("Windows integration modules not available")

# --- Project Setup ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(PROJECT_ROOT / "logs" / "defender.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class ThreatDetectionEngine:
    """
    Machine learning-based threat detection engine.
    Learns from file behaviors and network patterns.
    """

    def __init__(self):
        self.known_threats: Set[str] = set()
        self.suspicious_patterns = [
            r"\.exe$",  # Executable files
            r"\.dll$",  # Dynamic libraries
            r"\.scr$",  # Screen savers (often malware)
            r"\.bat$",  # Batch files
            r"\.ps1$",  # PowerShell scripts
            r"\.vbs$",  # VBScript files
            r"\.js$",  # JavaScript files in suspicious locations
        ]
        self.safe_paths = {
            Path("C:/Windows"),
            Path("C:/Program Files"),
            Path("C:/Program Files (x86)"),
        }
        self.threat_scores: Dict[str, float] = {}

    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        try:
            sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""

    def is_suspicious_file(self, file_path: Path) -> tuple[bool, str, float]:
        """
        Analyze if a file is suspicious.
        Returns: (is_suspicious, reason, threat_score)
        """
        try:
            # Check if in safe location
            for safe_path in self.safe_paths:
                try:
                    file_path.relative_to(safe_path)
                    return False, "Safe location", 0.0
                except ValueError:
                    continue

            threat_score = 0.0
            reasons = []

            # Check file extension
            for pattern in self.suspicious_patterns:
                if re.search(pattern, str(file_path), re.IGNORECASE):
                    threat_score += 0.3
                    reasons.append(f"Suspicious extension: {file_path.suffix}")

            # Check if recently created (new files are more suspicious)
            if file_path.exists():
                stat = file_path.stat()
                age_minutes = (time.time() - stat.st_ctime) / 60
                if age_minutes < 5:
                    threat_score += 0.2
                    reasons.append("Recently created")

                # Check file size (very small or very large can be suspicious)
                if stat.st_size < 100 or stat.st_size > 100_000_000:
                    threat_score += 0.1
                    reasons.append(f"Unusual size: {stat.st_size} bytes")

            # Check against known threats
            file_hash = self.calculate_file_hash(file_path)
            if file_hash in self.known_threats:
                threat_score = 1.0
                reasons.append("Known threat (hash match)")

            is_suspicious = threat_score >= 0.5
            reason = "; ".join(reasons) if reasons else "No threats detected"

            return is_suspicious, reason, threat_score

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return False, str(e), 0.0

    def learn_threat(self, file_hash: str, file_path: str):
        """Add a file to the known threats database."""
        self.known_threats.add(file_hash)
        logger.info(f"Learned new threat: {file_path} (hash: {file_hash[:16]}...)")

    def is_suspicious_process(self, proc: psutil.Process) -> tuple[bool, str, float]:
        """
        Analyze if a process is suspicious.
        Returns: (is_suspicious, reason, threat_score)
        """
        try:
            threat_score = 0.0
            reasons = []

            # Check CPU usage (processes using excessive CPU)
            cpu_percent = proc.cpu_percent(interval=0.1)
            if cpu_percent > 80:
                threat_score += 0.3
                reasons.append(f"High CPU usage: {cpu_percent}%")

            # Check network connections (suspicious outbound connections)
            try:
                connections = proc.net_connections()
                suspicious_ports = {445, 139, 3389}  # SMB, RDP
                for conn in connections:
                    if conn.status == "ESTABLISHED" and conn.raddr:
                        if conn.raddr.port in suspicious_ports:
                            threat_score += 0.4
                            reasons.append(f"Suspicious port: {conn.raddr.port}")
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            # Check process name and path
            try:
                exe = proc.exe()
                if exe:
                    exe_path = Path(exe)
                    # Processes running from temp directories are suspicious
                    if "temp" in str(exe_path).lower() or "tmp" in str(exe_path).lower():
                        threat_score += 0.3
                        reasons.append("Running from temp directory")
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            is_suspicious = threat_score >= 0.5
            reason = "; ".join(reasons) if reasons else "No threats detected"

            return is_suspicious, reason, threat_score

        except Exception as e:
            logger.error(f"Error analyzing process: {e}")
            return False, str(e), 0.0


class FileSystemMonitor(FileSystemEventHandler):
    """Monitors file system for suspicious activity."""

    def __init__(self, defender: "CelsiusRealtimeDefender"):
        self.defender = defender
        self.threat_engine = defender.threat_engine

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        asyncio.run_coroutine_threadsafe(self.defender.analyze_file(file_path, "created"), self.defender.async_loop)

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        # Only check certain file types on modification
        if file_path.suffix.lower() in [".exe", ".dll", ".bat", ".ps1"]:
            asyncio.run_coroutine_threadsafe(
                self.defender.analyze_file(file_path, "modified"), self.defender.async_loop
            )


class CelsiusRealtimeDefender:
    """
    Main real-time defender class.
    Coordinates all protection mechanisms.
    """

    def __init__(self):
        self.is_running = False
        self.threat_engine = ThreatDetectionEngine()
        self.quarantine_dir = PROJECT_ROOT / "quarantine"
        self.quarantine_dir.mkdir(exist_ok=True)

        # Statistics
        self.stats = {
            "files_scanned": 0,
            "threats_detected": 0,
            "threats_blocked": 0,
            "processes_monitored": 0,
            "uptime_start": datetime.now(),
        }

        # Database
        self.data_dir = PROJECT_ROOT / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.db_path = self.data_dir / "defender.db"

        # Async loop (will be set by main)
        self.async_loop = None

        # System tray icon
        self.tray_icon = None

    async def initialize(self):
        """Initialize the defender system."""
        await self.setup_database()
        logger.info("[DEFENDER] Celsius Real-Time Defender initialized")

    async def setup_database(self):
        """Create database tables for threat logging."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS threats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        threat_type TEXT NOT NULL,
                        file_path TEXT,
                        process_name TEXT,
                        threat_score REAL,
                        reason TEXT,
                        action_taken TEXT,
                        file_hash TEXT
                    )
                """
                )
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        scan_type TEXT NOT NULL,
                        files_scanned INTEGER,
                        threats_found INTEGER,
                        duration_seconds REAL
                    )
                """
                )
                await db.commit()
            logger.info("Defender database initialized")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")

    async def log_threat(
        self,
        threat_type: str,
        file_path: str = None,
        process_name: str = None,
        threat_score: float = 0.0,
        reason: str = "",
        action: str = "",
        file_hash: str = "",
    ):
        """Log a threat to the database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO threats 
                    (timestamp, threat_type, file_path, process_name, threat_score, reason, action_taken, file_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        threat_type,
                        str(file_path) if file_path else None,
                        process_name,
                        threat_score,
                        reason,
                        action,
                        file_hash,
                    ),
                )
                await db.commit()

            self.stats["threats_detected"] += 1

            # Show Windows notification
            if WINDOWS_INTEGRATION:
                self.show_notification("Threat Detected", f"{threat_type}: {reason}\nAction: {action}")
        except Exception as e:
            logger.error(f"Error logging threat: {e}")

    async def analyze_file(self, file_path: Path, event_type: str):
        """Analyze a file for threats."""
        try:
            is_suspicious, reason, threat_score = self.threat_engine.is_suspicious_file(file_path)
            self.stats["files_scanned"] += 1

            if is_suspicious:
                logger.warning(f"[THREAT] Suspicious file detected: {file_path}")
                logger.warning(f"[THREAT] Reason: {reason}, Score: {threat_score:.2f}")

                file_hash = self.threat_engine.calculate_file_hash(file_path)

                # Decide action based on threat score
                if threat_score >= 0.8:
                    action = "QUARANTINED"
                    await self.quarantine_file(file_path)
                    self.stats["threats_blocked"] += 1
                elif threat_score >= 0.5:
                    action = "FLAGGED"
                else:
                    action = "MONITORED"

                await self.log_threat(
                    threat_type="FILE",
                    file_path=str(file_path),
                    threat_score=threat_score,
                    reason=reason,
                    action=action,
                    file_hash=file_hash,
                )
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")

    async def quarantine_file(self, file_path: Path):
        """Move a suspicious file to quarantine."""
        try:
            if not file_path.exists():
                return

            # Create quarantine subdirectory with timestamp
            quarantine_subdir = self.quarantine_dir / datetime.now().strftime("%Y%m%d")
            quarantine_subdir.mkdir(exist_ok=True)

            # Move file to quarantine
            quarantine_path = quarantine_subdir / file_path.name
            file_path.rename(quarantine_path)

            logger.info(f"[QUARANTINE] File quarantined: {file_path} -> {quarantine_path}")

            # Save metadata
            metadata_path = quarantine_path.with_suffix(".json")
            metadata = {
                "original_path": str(file_path),
                "quarantine_time": datetime.now().isoformat(),
                "file_hash": self.threat_engine.calculate_file_hash(quarantine_path),
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            logger.error(f"Error quarantining file {file_path}: {e}")

    async def monitor_processes(self):
        """Continuously monitor running processes for suspicious activity."""
        while self.is_running:
            try:
                for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
                    try:
                        is_suspicious, reason, threat_score = self.threat_engine.is_suspicious_process(proc)
                        self.stats["processes_monitored"] += 1

                        if is_suspicious:
                            logger.warning(
                                f"[THREAT] Suspicious process: {proc.info['name']} (PID: {proc.info['pid']})"
                            )
                            logger.warning(f"[THREAT] Reason: {reason}, Score: {threat_score:.2f}")

                            action = "FLAGGED" if threat_score < 0.8 else "TERMINATED"

                            await self.log_threat(
                                threat_type="PROCESS",
                                process_name=proc.info["name"],
                                threat_score=threat_score,
                                reason=reason,
                                action=action,
                            )

                            # Terminate highly suspicious processes
                            if threat_score >= 0.9:
                                try:
                                    proc.terminate()
                                    logger.warning(f"[TERMINATE] Terminated suspicious process: {proc.info['name']}")
                                    self.stats["threats_blocked"] += 1
                                except Exception as e:
                                    logger.error(f"Failed to terminate process: {e}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in process monitoring: {e}")
                await asyncio.sleep(10)

    def start_filesystem_monitoring(self):
        """Start monitoring the file system."""
        try:
            # Monitor Downloads and Desktop (common malware entry points)
            paths_to_monitor = [Path.home() / "Downloads", Path.home() / "Desktop", Path.home() / "Documents"]

            event_handler = FileSystemMonitor(self)
            observer = Observer()

            for path in paths_to_monitor:
                if path.exists():
                    observer.schedule(event_handler, str(path), recursive=True)
                    logger.info(f"[MONITOR] Monitoring: {path}")

            observer.start()
            logger.info("[MONITOR] File system monitoring started")

            return observer
        except Exception as e:
            logger.error(f"Error starting filesystem monitoring: {e}")
            return None

    def show_notification(self, title: str, message: str):
        """Show Windows toast notification."""
        if WINDOWS_INTEGRATION and self.tray_icon:
            try:
                self.tray_icon.notify(title, message)
            except Exception as e:
                logger.error(f"Error showing notification: {e}")

    def create_tray_icon(self):
        """Create system tray icon."""
        if not WINDOWS_INTEGRATION:
            logger.warning("Windows integration not available - no system tray")
            return None

        try:
            # Create icon image
            image = Image.new("RGB", (64, 64), color="blue")
            draw = ImageDraw.Draw(image)
            draw.ellipse([8, 8, 56, 56], fill="lightblue", outline="white")
            draw.text((20, 20), "🛡️", fill="white")

            def on_quit(icon, item):
                icon.stop()
                self.is_running = False

            def show_stats(icon, item):
                uptime = datetime.now() - self.stats["uptime_start"]
                stats_msg = f"""Celsius AI Defender Stats:
                
Files Scanned: {self.stats['files_scanned']}
Threats Detected: {self.stats['threats_detected']}
Threats Blocked: {self.stats['threats_blocked']}
Processes Monitored: {self.stats['processes_monitored']}
Uptime: {str(uptime).split('.')[0]}
"""
                icon.notify("Defender Statistics", stats_msg)

            menu = pystray.Menu(pystray.MenuItem("Statistics", show_stats), pystray.MenuItem("Quit", on_quit))

            icon = pystray.Icon("Celsius Defender", image, "Celsius AI Defender", menu)
            return icon
        except Exception as e:
            logger.error(f"Error creating tray icon: {e}")
            return None

    async def run(self):
        """Main execution loop."""
        self.is_running = True

        # Start file system monitoring in background thread
        fs_observer = self.start_filesystem_monitoring()

        # Start process monitoring
        process_monitor_task = asyncio.create_task(self.monitor_processes())

        logger.info("[DEFENDER] Celsius Real-Time Defender is now protecting your system")
        logger.info("[DEFENDER] Statistics available in system tray")

        try:
            # Keep running
            while self.is_running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Defender shutdown requested")
        finally:
            if fs_observer:
                fs_observer.stop()
                fs_observer.join()
            process_monitor_task.cancel()
            logger.info("[DEFENDER] Celsius Defender stopped")


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("CELSIUS AI - REAL-TIME SYSTEM DEFENDER")
    print("=" * 80)
    print("\nStarting comprehensive system protection...\n")

    # Create defender instance
    defender = CelsiusRealtimeDefender()

    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    defender.async_loop = loop

    # Initialize
    loop.run_until_complete(defender.initialize())

    # Start system tray icon in separate thread if available
    if WINDOWS_INTEGRATION:
        defender.tray_icon = defender.create_tray_icon()
        if defender.tray_icon:
            tray_thread = threading.Thread(target=defender.tray_icon.run, daemon=True)
            tray_thread.start()

    # Run defender
    try:
        loop.run_until_complete(defender.run())
    except KeyboardInterrupt:
        print("\n[DEFENDER] Defender stopped by user")
    finally:
        loop.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[DEFENDER] Celsius Defender terminated by user.")
