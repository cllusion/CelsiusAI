#!/usr/bin/env python3
"""
Celsius AI - Truly Persistent Guardian
Manages all persistent processes: Server Hub, Enhanced Dashboard, Code Approval, Web Learning
Automatically starts, monitors, and maintains the complete AI infrastructure
"""

import time
import subprocess
import sys
import os
import requests
import psutil
import threading
import schedule
from datetime import datetime, timedelta
from pathlib import Path
import json
import sqlite3
import shutil


class CelsiusPersistentGuardian:
    def __init__(self):
        self.is_running = True
        self.base_dir = Path(__file__).parent
        self.startup_time = datetime.now()

        # Process management
        self.managed_processes = {}
        self.process_configs = {
            "server_hub": {
                "file": "celsius_server_hub.py",
                "name": "Server Hub",
                "url": None,  # GUI application
                "required": True,
                "restart_count": 0,
            },
            "enhanced_dashboard": {
                "file": "enhanced_mobile_dashboard.py",
                "name": "Enhanced Dashboard",
                "url": "http://localhost:5000",
                "required": True,
                "restart_count": 0,
            },
            "web_learning": {
                "file": "celsius_web_learning_launcher.py",
                "name": "Web Learning Engine",
                "url": None,
                "required": False,  # Optional service
                "restart_count": 0,
            },
        }

        # Guardian state
        self.check_interval = 60  # Check every minute
        self.last_maintenance = datetime.now()
        self.maintenance_interval = timedelta(hours=6)  # Maintenance every 6 hours

        print("🛡️ Celsius AI Persistent Guardian Initializing...")
        print(f"📁 Base Directory: {self.base_dir}")
        print(f"🔄 Check Interval: {self.check_interval} seconds")
        print(f"⚙️ Managing {len(self.process_configs)} services")

    def log_event(self, event_type, message):
        """Log Guardian events with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{event_type}] {message}"
        print(log_message)

        # Also write to log file
        log_file = self.base_dir / "guardian_persistent.log"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")

    def check_process_running(self, process_name):
        """Check if a managed process is still running"""
        if process_name not in self.managed_processes:
            return False

        process = self.managed_processes[process_name]
        if process is None:
            return False

        return process.poll() is None

    def check_service_health(self, service_name):
        """Check if a service is healthy via HTTP"""
        config = self.process_configs.get(service_name)
        if not config or not config.get("url"):
            return True  # Can't check non-HTTP services

        try:
            response = requests.get(config["url"] + "/api/status", timeout=3)
            return response.status_code == 200
        except:
            return False

    def start_service(self, service_name):
        """Start a specific service"""
        config = self.process_configs.get(service_name)
        if not config:
            self.log_event("ERROR", f"Unknown service: {service_name}")
            return False

        service_file = self.base_dir / config["file"]
        if not service_file.exists():
            self.log_event("ERROR", f"Service file not found: {config['file']}")
            return False

        try:
            self.log_event("START", f"Starting {config['name']}...")

            # Start the process
            process = subprocess.Popen(
                [sys.executable, config["file"]],
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE if service_name == "server_hub" else 0,
            )

            self.managed_processes[service_name] = process
            config["restart_count"] += 1

            self.log_event("SUCCESS", f"{config['name']} started with PID: {process.pid}")

            # Wait and verify startup for HTTP services
            if config.get("url"):
                time.sleep(8)  # Allow startup time

                # Verify service is responding
                attempts = 0
                while attempts < 10:
                    if self.check_service_health(service_name):
                        self.log_event("VERIFY", f"{config['name']} verified and responding")
                        return True
                    attempts += 1
                    time.sleep(2)

                self.log_event("WARNING", f"{config['name']} started but not responding to health checks")
                return False
            else:
                # For non-HTTP services, just check if process is running
                time.sleep(3)
                if self.check_process_running(service_name):
                    self.log_event("VERIFY", f"{config['name']} process verified")
                    return True
                else:
                    self.log_event("ERROR", f"{config['name']} process died after startup")
                    return False

        except Exception as e:
            self.log_event("ERROR", f"Failed to start {config['name']}: {e}")
            return False

    def stop_service(self, service_name):
        """Stop a specific service"""
        if service_name not in self.managed_processes:
            return True

        process = self.managed_processes[service_name]
        if process is None:
            return True

        config = self.process_configs[service_name]

        try:
            self.log_event("STOP", f"Stopping {config['name']}...")

            # Graceful shutdown first
            process.terminate()

            # Wait for graceful shutdown
            try:
                process.wait(timeout=10)
                self.log_event("SUCCESS", f"{config['name']} stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if needed
                process.kill()
                process.wait()
                self.log_event("FORCE", f"{config['name']} force stopped")

            self.managed_processes[service_name] = None
            return True

        except Exception as e:
            self.log_event("ERROR", f"Error stopping {config['name']}: {e}")
            return False

    def cleanup_orphaned_processes(self):
        """Clean up any orphaned Celsius processes"""
        cleaned = 0
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["name"] == "python3.11.exe" or proc.info["name"] == "python.exe":
                    if proc.info["cmdline"]:
                        cmdline = " ".join(proc.info["cmdline"])

                        # Check if it's a Celsius process not managed by us
                        celsius_files = ["celsius_", "enhanced_mobile_dashboard", "celsius_server_hub"]
                        is_celsius = any(cf in cmdline for cf in celsius_files)

                        if is_celsius:
                            # Check if it's one of our managed processes
                            is_managed = False
                            for service_name, process in self.managed_processes.items():
                                if process and process.pid == proc.info["pid"]:
                                    is_managed = True
                                    break

                            if not is_managed:
                                proc.kill()
                                cleaned += 1
                                self.log_event("CLEANUP", f"Cleaned orphaned process PID {proc.info['pid']}")

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if cleaned > 0:
            self.log_event("MAINTENANCE", f"Cleaned up {cleaned} orphaned processes")

    def monitor_services(self):
        """Monitor all services and restart if needed"""
        for service_name, config in self.process_configs.items():
            try:
                process_running = self.check_process_running(service_name)
                service_healthy = self.check_service_health(service_name) if config.get("url") else True

                needs_restart = False
                reason = ""

                if not process_running:
                    needs_restart = True
                    reason = "process not running"
                elif config.get("url") and not service_healthy:
                    needs_restart = True
                    reason = "service not responding"

                if needs_restart:
                    if config["required"] or config["restart_count"] == 0:
                        self.log_event("MONITOR", f"{config['name']}: {reason} - restarting")
                        self.stop_service(service_name)
                        time.sleep(2)
                        self.start_service(service_name)
                    else:
                        self.log_event("SKIP", f"{config['name']}: {reason} - optional service, skipping restart")

            except Exception as e:
                self.log_event("ERROR", f"Error monitoring {service_name}: {e}")

    def perform_maintenance(self):
        """Perform periodic maintenance tasks"""
        self.log_event("MAINTENANCE", "Starting periodic maintenance")

        # Clean up orphaned processes
        self.cleanup_orphaned_processes()

        # Optimize databases
        db_files = ["celsius_activity.db", "celsius_code_approvals.db", "celsius_system.db", "celsius_web_learning.db"]
        for db_file in db_files:
            db_path = self.base_dir / db_file
            if db_path.exists():
                try:
                    conn = sqlite3.connect(db_path)
                    conn.execute("VACUUM")
                    conn.execute("REINDEX")
                    conn.close()
                    self.log_event("OPTIMIZE", f"Optimized database: {db_file}")
                except Exception as e:
                    self.log_event("ERROR", f"Could not optimize {db_file}: {e}")

        # Clean old log files (keep last 7 days)
        cutoff_date = datetime.now() - timedelta(days=7)
        logs_dir = self.base_dir / "logs"
        if logs_dir.exists():
            for log_file in logs_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    self.log_event("CLEANUP", f"Removed old log: {log_file.name}")

        self.last_maintenance = datetime.now()
        self.log_event("MAINTENANCE", "Periodic maintenance completed")

    def get_status_report(self):
        """Generate status report of all services"""
        uptime = datetime.now() - self.startup_time
        report = f"""
🛡️ CELSIUS AI PERSISTENT GUARDIAN STATUS
{'='*50}
⏰ Guardian Uptime: {uptime}
🔄 Check Interval: {self.check_interval} seconds
🛠️ Last Maintenance: {self.last_maintenance.strftime('%Y-%m-%d %H:%M:%S')}

📊 MANAGED SERVICES STATUS:
"""

        for service_name, config in self.process_configs.items():
            process_status = "🟢 Running" if self.check_process_running(service_name) else "🔴 Stopped"
            health_status = "🟢 Healthy" if self.check_service_health(service_name) else "🟡 Unknown"

            report += f"  • {config['name']}: {process_status} | Health: {health_status} | Restarts: {config['restart_count']}\n"

        return report

    def start_all_services(self):
        """Start all required services"""
        self.log_event("INIT", "Starting all Celsius AI services...")

        # Clean up any existing processes first
        self.cleanup_orphaned_processes()

        # Start services in order
        for service_name, config in self.process_configs.items():
            if config["required"]:
                self.start_service(service_name)
                time.sleep(3)  # Stagger starts to avoid conflicts

        self.log_event("INIT", "All services initialization complete")

    def run(self):
        """Main Guardian loop - truly persistent"""
        self.log_event("GUARDIAN", "Persistent Guardian starting...")

        # Initial service startup
        self.start_all_services()

        self.log_event("GUARDIAN", f"Guardian active - monitoring every {self.check_interval} seconds")

        try:
            check_count = 0
            while self.is_running:
                check_count += 1

                # Monitor services
                self.monitor_services()

                # Periodic maintenance
                if datetime.now() - self.last_maintenance > self.maintenance_interval:
                    self.perform_maintenance()

                # Status report every 10 checks (10 minutes)
                if check_count % 10 == 0:
                    status = self.get_status_report()
                    print(status)

                # Wait for next check
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.log_event("SHUTDOWN", "Guardian shutdown requested...")
            self.is_running = False

            # Graceful shutdown of all services
            for service_name in self.managed_processes:
                self.stop_service(service_name)

            self.log_event("SHUTDOWN", "Persistent Guardian shutdown complete")


def main():
    """Start the persistent guardian"""
    try:
        guardian = CelsiusPersistentGuardian()
        guardian.run()
    except Exception as e:
        print(f"❌ Persistent Guardian failed to start: {e}")
        input("Press Enter to continue...")


if __name__ == "__main__":
    main()
