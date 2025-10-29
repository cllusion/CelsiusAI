#!/usr/bin/env python3
"""
Celsius AI - Persistent Guardian
Manages all persistent processes: Server Hub, Enhanced Dashboard, Code Approval, Web Learning
"""

import time
import subprocess
import sys
import os
import requests
import psutil
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3


class CelsiusLightweightGuardian:
    def __init__(self):
        self.is_running = True
        self.base_dir = Path(__file__).parent
        self.check_interval = 60  # Check every minute for persistence
        self.startup_time = datetime.now()

        # Managed processes for true persistence
        self.managed_processes = {"enhanced_dashboard": None, "celsius_core": None, "web_learning": None}

        # Process configurations - all essential services
        self.process_configs = {
            "enhanced_dashboard": {
                "file": "enhanced_mobile_dashboard.py",
                "name": "Enhanced Dashboard",
                "url": "http://localhost:5000",
                "required": True,
                "startup_delay": 3,
            },
            "celsius_core": {
                "file": "main.py",
                "name": "Celsius AI Core Engine",
                "url": None,  # Console application
                "required": True,
                "startup_delay": 2,
            },
            "web_learning": {
                "file": "celsius_web_learning_launcher.py",
                "name": "Web Learning Engine",
                "url": None,
                "required": True,  # Now required for full functionality
                "startup_delay": 5,
            },
        }

        # Maintenance tracking
        self.last_maintenance = datetime.now()
        self.maintenance_interval = timedelta(hours=6)

        print("🛡️ Celsius AI Persistent Guardian Starting...")
        print(f"📁 Base Directory: {self.base_dir}")
        print(f"🔄 Managing {len(self.process_configs)} services")
        print("🎯 Essential Services: Server Hub (GUI) + Enhanced Dashboard (API)")
        print(f"⏱️ Check Interval: {self.check_interval} seconds")

    def log_event(self, event_type, message):
        """Log Guardian events with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{event_type}] {message}"
        print(log_message)

        # Write to persistent log file
        try:
            log_file = self.base_dir / "guardian_persistent.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except:
            pass  # Don't fail on logging errors

    def check_process_running(self, service_name):
        """Check if a managed process is still running"""
        if service_name not in self.managed_processes:
            return False

        process = self.managed_processes[service_name]
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

    def cleanup_orphaned_processes(self):
        """Clean up any orphaned Celsius processes not managed by Guardian"""
        cleaned = 0
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["name"] == "python3.11.exe" or proc.info["name"] == "python.exe":
                    if proc.info["cmdline"]:
                        cmdline = " ".join(proc.info["cmdline"])

                        # Check if it's a Celsius process
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

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if cleaned > 0:
            self.log_event("CLEANUP", f"Cleaned up {cleaned} orphaned processes")
        time.sleep(2)

    def start_service(self, service_name):
        """Start a specific persistent service"""
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

            # Start the process with appropriate console settings
            creation_flags = subprocess.CREATE_NEW_CONSOLE if service_name == "celsius_core" else 0

            process = subprocess.Popen(
                [sys.executable, config["file"]],
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creation_flags,
            )

            self.managed_processes[service_name] = process
            self.log_event("SUCCESS", f"{config['name']} started with PID: {process.pid}")

            # Allow startup delay based on service type
            startup_delay = config.get("startup_delay", 3)
            time.sleep(startup_delay)

            # Verify startup for HTTP services
            if config.get("url"):
                attempts = 0
                while attempts < 15:
                    if self.check_service_health(service_name):
                        self.log_event("VERIFY", f"{config['name']} verified and responding")
                        return True
                    attempts += 1
                    time.sleep(2)

                self.log_event("WARNING", f"{config['name']} started but not responding")
                return False
            else:
                # For console/GUI services, just check if process is running
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
        """Stop a specific service gracefully"""
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

    def monitor_all_services(self):
        """Monitor all managed services and restart if needed"""
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

                if needs_restart and config["required"]:
                    self.log_event("MONITOR", f"{config['name']}: {reason} - restarting")
                    self.stop_service(service_name)
                    time.sleep(2)
                    self.start_service(service_name)

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

        # Clean old logs (keep last 7 days)
        cutoff_date = datetime.now() - timedelta(days=7)
        logs_dir = self.base_dir / "logs"
        if logs_dir.exists():
            for log_file in logs_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    self.log_event("CLEANUP", f"Removed old log: {log_file.name}")

        self.last_maintenance = datetime.now()
        self.log_event("MAINTENANCE", "Periodic maintenance completed")

    def get_uptime(self):
        """Get Guardian uptime"""
        delta = datetime.now() - self.startup_time
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{delta.days}d {hours}h {minutes}m"

    def start_all_services(self):
        """Start all required persistent services"""
        self.log_event("INIT", "Starting all Celsius AI services...")

        # Clean up any orphaned processes first
        self.cleanup_orphaned_processes()

        # Start services in priority order
        for service_name, config in self.process_configs.items():
            if config["required"]:
                try:
                    success = self.start_service(service_name)
                    if not success:
                        self.log_event("WARNING", f"Failed to start required service: {config['name']}")
                    time.sleep(3)  # Stagger starts to avoid conflicts
                except Exception as e:
                    self.log_event("ERROR", f"Exception starting {config['name']}: {e}")

        # Try to start optional services (don't fail if they don't work)
        for service_name, config in self.process_configs.items():
            if not config["required"]:
                try:
                    self.start_service(service_name)
                    time.sleep(2)
                except Exception as e:
                    self.log_event("WARNING", f"Optional service {config['name']} failed: {e}")

        self.log_event("INIT", "All services initialization complete")

    def get_status_report(self):
        """Generate comprehensive status report"""
        uptime = datetime.now() - self.startup_time
        running_services = sum(1 for svc in self.process_configs if self.check_process_running(svc))

        report = f"""
🛡️ CELSIUS AI PERSISTENT GUARDIAN STATUS
{'='*50}
⏰ Guardian Uptime: {uptime}
🔄 Check Interval: {self.check_interval} seconds  
📊 Services Running: {running_services}/{len(self.process_configs)}
🛠️ Last Maintenance: {self.last_maintenance.strftime('%H:%M:%S')}

📋 MANAGED SERVICES:
"""

        for service_name, config in self.process_configs.items():
            status = "� Running" if self.check_process_running(service_name) else "🔴 Stopped"
            health = "🟢 Healthy" if self.check_service_health(service_name) else "🟡 Unknown"
            report += f"  • {config['name']}: {status} | Health: {health}\n"

        return report

    def run(self):
        """Main Guardian loop - truly persistent"""
        self.log_event("GUARDIAN", "Persistent Guardian starting...")

        # Initial startup of all services
        self.start_all_services()

        self.log_event("GUARDIAN", f"Guardian active - monitoring every {self.check_interval} seconds")

        try:
            check_count = 0
            while self.is_running:
                check_count += 1

                # Monitor all services
                self.monitor_all_services()

                # Periodic maintenance
                if datetime.now() - self.last_maintenance > self.maintenance_interval:
                    self.perform_maintenance()

                # Status report every 10 checks (10 minutes)
                if check_count % 10 == 0:
                    status = self.get_status_report()
                    print(status)

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.log_event("SHUTDOWN", "Guardian shutdown requested...")
            self.is_running = False

            # Graceful shutdown of all managed services
            for service_name in self.managed_processes:
                self.stop_service(service_name)

            self.log_event("SHUTDOWN", "Persistent Guardian shutdown complete")


def main():
    """Start the lightweight guardian"""
    try:
        guardian = CelsiusLightweightGuardian()
        guardian.run()
    except Exception as e:
        print(f"❌ Guardian failed: {e}")


if __name__ == "__main__":
    main()
