#!/usr/bin/env python3
"""
Celsius AI Defense System - True Persistent Service Manager
Implements hardcore persistence for continuous cybersecurity protection
"""

import subprocess
import time
import json
import sys
import os
import threading
import signal
import logging
import winreg
import atexit
from pathlib import Path
from datetime import datetime, timedelta
import psutil
import shutil


class CelsiusDefenseSystem:
    """True persistent Celsius AI defense system with multiple layers of persistence"""

    def __init__(self):
        self.base_dir = Path("C:/Users/micro/Celsius AI")
        self.python_exe = sys.executable

        # Core services with enhanced persistence controls
        self.services = {
            "celsius_core": {
                "script": "main.py",
                "process": None,
                "restart_count": 0,
                "critical": True,
                "persistent": True,
                "user_controlled": False,
                "description": "Core Celsius AI Engine",
            },
            "enhanced_dashboard": {
                "script": "enhanced_mobile_dashboard.py",
                "process": None,
                "restart_count": 0,
                "critical": True,
                "persistent": True,
                "user_controlled": True,  # Server can be controlled by user
                "description": "Enhanced Mobile Dashboard Server",
            },
            "hourly_logger": {
                "script": "celsius_hourly_logger.py",
                "process": None,
                "restart_count": 0,
                "critical": True,
                "persistent": True,
                "user_controlled": False,
                "description": "Hourly Activity Logger",
            },
            "server_hub": {
                "script": "celsius_server_hub.py",
                "process": None,
                "restart_count": 0,
                "critical": True,  # Changed to critical for true persistence
                "persistent": True,
                "user_controlled": False,  # Hub itself is always persistent
                "description": "Server Hub Interface",
            },
        }

        # User control settings
        self.user_control_file = self.base_dir / "user_server_control.json"
        self.user_server_stopped = False

        # Persistence settings
        self.running = True
        self.persistence_enabled = True
        self.auto_restart = True
        self.max_restart_attempts = 10
        self.restart_delay = 30  # seconds
        self.health_check_interval = 60  # seconds

        # Status tracking
        self.system_start_time = datetime.now()
        self.total_restarts = 0
        self.last_health_check = None

        # Setup logging and persistence
        self.setup_logging()
        self.setup_persistence()

        # Register cleanup handlers
        atexit.register(self.cleanup_on_exit)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def setup_logging(self):
        """Setup comprehensive logging"""
        log_dir = self.base_dir / "logs"
        log_dir.mkdir(exist_ok=True)

        # Create rotating log handler
        from logging.handlers import RotatingFileHandler

        self.logger = logging.getLogger("CelsiusDefense")
        self.logger.setLevel(logging.INFO)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_dir / "celsius_defense.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)

        # Formatter
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(name)s] - %(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info("[SHIELD] Celsius AI Defense System - Logging Initialized")

    def load_user_server_control(self):
        """Load user server control settings"""
        try:
            if self.user_control_file.exists():
                with open(self.user_control_file, "r") as f:
                    data = json.load(f)
                self.user_server_stopped = data.get("server_stopped_by_user", False)
                if self.user_server_stopped:
                    self.logger.info("📋 Server was stopped by user - respecting user choice")
            else:
                self.user_server_stopped = False
        except Exception as e:
            self.logger.warning(f"[WARNING] Could not load user control settings: {e}")
            self.user_server_stopped = False

    def save_user_server_control(self):
        """Save user server control settings"""
        try:
            control_data = {
                "server_stopped_by_user": self.user_server_stopped,
                "timestamp": datetime.now().isoformat(),
                "note": "This file tracks if the user manually stopped the server via button",
            }
            with open(self.user_control_file, "w") as f:
                json.dump(control_data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"[WARNING] Could not save user control settings: {e}")

    def setup_persistence(self):
        """Setup multiple layers of persistence"""
        self.logger.info("[LOCKED] Setting up persistence layers...")

        # Load user control settings
        self.load_user_server_control()

        try:
            # 1. Windows Registry startup entry
            self.setup_registry_startup()

            # 2. Startup folder shortcut
            self.setup_startup_folder()

            # 3. Scheduled task (if available)
            self.setup_scheduled_task()

            # 4. Watchdog file
            self.setup_watchdog_file()

            self.logger.info("[OK] Persistence layers configured")

        except Exception as e:
            self.logger.error(f"[ERROR] Error setting up persistence: {e}")

    def setup_registry_startup(self):
        """Add to Windows startup registry"""
        try:
            startup_script = self.base_dir / "celsius_persistent_startup.py"

            # Create startup script
            startup_code = f"""
import subprocess
import sys
import os

# Change to Celsius AI directory
os.chdir(r"{self.base_dir}")

# Start the persistent defense system
subprocess.Popen([
    r"{self.python_exe}",
    r"{__file__.replace('_startup.py', '_defense_manager.py')}"
], creationflags=subprocess.CREATE_NO_WINDOW)
"""
            with open(startup_script, "w") as f:
                f.write(startup_code)

            # Add to registry
            key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "CelsiusAIDefense", 0, winreg.REG_SZ, f'"{self.python_exe}" "{startup_script}"')

            self.logger.info("[OK] Registry startup entry created")

        except Exception as e:
            self.logger.warning(f"[WARNING] Could not setup registry startup: {e}")

    def setup_startup_folder(self):
        """Add shortcut to Windows startup folder"""
        try:
            import win32com.client

            startup_folder = Path(os.getenv("APPDATA")) / "Microsoft/Windows/Start Menu/Programs/Startup"
            startup_folder.mkdir(parents=True, exist_ok=True)

            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(startup_folder / "Celsius AI Defense.lnk"))
            shortcut.Targetpath = self.python_exe
            shortcut.Arguments = f'"{__file__}"'
            shortcut.WorkingDirectory = str(self.base_dir)
            shortcut.Description = "Celsius AI Persistent Defense System"
            shortcut.save()

            self.logger.info("[OK] Startup folder shortcut created")

        except ImportError:
            self.logger.warning("[WARNING] pywin32 not available for startup shortcut")
        except Exception as e:
            self.logger.warning(f"[WARNING] Could not setup startup shortcut: {e}")

    def setup_scheduled_task(self):
        """Setup Windows scheduled task for additional persistence"""
        try:
            task_name = "CelsiusAIDefenseTask"
            task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <StartBoundary>2025-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>"{self.python_exe}"</Command>
      <Arguments>"{__file__}"</Arguments>
      <WorkingDirectory>{self.base_dir}</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
</Task>"""

            # Save task XML and try to import it
            task_file = self.base_dir / "celsius_task.xml"
            with open(task_file, "w", encoding="utf-16") as f:
                f.write(task_xml)

            # Try to create the task (may require admin rights)
            result = subprocess.run(
                ["schtasks", "/create", "/tn", task_name, "/xml", str(task_file), "/f"], capture_output=True, text=True
            )

            if result.returncode == 0:
                self.logger.info("[OK] Scheduled task created")
            else:
                self.logger.warning("[WARNING] Could not create scheduled task (admin rights may be needed)")

        except Exception as e:
            self.logger.warning(f"[WARNING] Could not setup scheduled task: {e}")

    def setup_watchdog_file(self):
        """Create a watchdog file that other systems can monitor"""
        try:
            watchdog_file = self.base_dir / "celsius_watchdog.json"
            watchdog_data = {
                "status": "starting",
                "pid": os.getpid(),
                "start_time": self.system_start_time.isoformat(),
                "last_heartbeat": datetime.now().isoformat(),
                "services": list(self.services.keys()),
            }

            with open(watchdog_file, "w") as f:
                json.dump(watchdog_data, f, indent=2)

            self.logger.info("[OK] Watchdog file created")

        except Exception as e:
            self.logger.warning(f"[WARNING] Could not create watchdog file: {e}")

    def update_watchdog(self):
        """Update watchdog heartbeat"""
        try:
            watchdog_file = self.base_dir / "celsius_watchdog.json"

            service_status = {}
            for name, service in self.services.items():
                service_status[name] = {
                    "running": service["process"] and service["process"].poll() is None,
                    "restart_count": service["restart_count"],
                    "pid": service["process"].pid if service["process"] and service["process"].poll() is None else None,
                }

            watchdog_data = {
                "status": "running",
                "pid": os.getpid(),
                "start_time": self.system_start_time.isoformat(),
                "last_heartbeat": datetime.now().isoformat(),
                "total_restarts": self.total_restarts,
                "services": service_status,
            }

            with open(watchdog_file, "w") as f:
                json.dump(watchdog_data, f, indent=2)

        except Exception as e:
            self.logger.warning(f"[WARNING] Could not update watchdog: {e}")

    def start_service(self, service_name):
        """Start a specific service"""
        try:
            service = self.services[service_name]
            script_path = self.base_dir / service["script"]

            if not script_path.exists():
                self.logger.error(f"[ERROR] Script not found: {script_path}")
                return False

            self.logger.info(f"[START] Starting {service['description']}...")

            # Start the process
            if service_name == "server_hub":
                # Server hub runs in visible window
                process = subprocess.Popen([self.python_exe, str(script_path)], cwd=str(self.base_dir))
            else:
                # Other services run hidden
                process = subprocess.Popen(
                    [self.python_exe, str(script_path)],
                    cwd=str(self.base_dir),
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

            service["process"] = process
            self.logger.info(f"[OK] {service['description']} started (PID: {process.pid})")
            return True

        except Exception as e:
            self.logger.error(f"[ERROR] Error starting {service_name}: {e}")
            return False

    def stop_service(self, service_name):
        """Stop a specific service"""
        try:
            service = self.services[service_name]
            if service["process"] and service["process"].poll() is None:
                self.logger.info(f"[STOP] Stopping {service['description']}...")
                service["process"].terminate()

                # Wait for graceful shutdown
                try:
                    service["process"].wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"[WARNING] Force killing {service_name}")
                    service["process"].kill()

                self.logger.info(f"[OK] {service['description']} stopped")

        except Exception as e:
            self.logger.error(f"[ERROR] Error stopping {service_name}: {e}")

    def restart_service(self, service_name):
        """Restart a specific service"""
        service = self.services[service_name]

        self.logger.info(f"[REFRESH] Restarting {service['description']}...")
        self.stop_service(service_name)
        time.sleep(5)  # Wait a moment

        if self.start_service(service_name):
            service["restart_count"] += 1
            self.total_restarts += 1
            self.logger.info(f"[OK] {service['description']} restarted (attempt #{service['restart_count']})")
        else:
            self.logger.error(f"[ERROR] Failed to restart {service_name}")

    def check_service_health(self):
        """Check health of all services and restart if needed"""
        self.last_health_check = datetime.now()

        # Reload user control settings to check for changes
        self.load_user_server_control()

        for service_name, service in self.services.items():
            try:
                # Check if process is running
                if not service["process"] or service["process"].poll() is not None:
                    # Check if this service should be restarted
                    should_restart = False

                    if service["persistent"]:
                        if service["user_controlled"] and service_name == "enhanced_dashboard":
                            # For server: only restart if user hasn't manually stopped it
                            if not self.user_server_stopped:
                                should_restart = True
                                self.logger.warning(
                                    f"[WARNING] {service['description']} is down - restarting (not stopped by user)..."
                                )
                            else:
                                self.logger.info(
                                    f"📋 {service['description']} stopped by user - respecting user choice"
                                )
                        else:
                            # For non-user-controlled services: always restart
                            should_restart = True
                            self.logger.warning(f"[WARNING] {service['description']} is down - restarting...")

                    if should_restart and service["restart_count"] < self.max_restart_attempts:
                        self.restart_service(service_name)
                    elif should_restart:
                        self.logger.error(f"[ERROR] {service_name} exceeded max restart attempts")

            except Exception as e:
                self.logger.error(f"[ERROR] Error checking {service_name}: {e}")

    def start_all_services(self):
        """Start all Celsius AI services"""
        self.logger.info("[START] Starting Celsius AI Defense System...")

        # Start services in order of importance
        service_order = ["celsius_core", "enhanced_dashboard", "hourly_logger", "server_hub"]

        for service_name in service_order:
            if service_name in self.services:
                self.start_service(service_name)
                time.sleep(2)  # Stagger startup

        self.logger.info("[OK] All services started")

    def run_defense_loop(self):
        """Main defense loop - monitors and maintains services"""
        self.logger.info("[SHIELD] Entering defense monitoring loop...")

        try:
            while self.running:
                # Update watchdog
                self.update_watchdog()

                # Check service health
                self.check_service_health()

                # Wait for next check
                time.sleep(self.health_check_interval)

        except KeyboardInterrupt:
            self.logger.info("[STOP] Shutdown signal received")
            self.running = False
        except Exception as e:
            self.logger.error(f"[ERROR] Error in defense loop: {e}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"[STOP] Received signal {signum}")
        self.running = False

    def cleanup_on_exit(self):
        """Cleanup when exiting"""
        self.logger.info("🧹 Cleaning up...")

        # Stop all services
        for service_name in self.services:
            self.stop_service(service_name)

        # Update watchdog status
        try:
            watchdog_file = self.base_dir / "celsius_watchdog.json"
            if watchdog_file.exists():
                with open(watchdog_file) as f:
                    data = json.load(f)
                data["status"] = "stopped"
                data["stop_time"] = datetime.now().isoformat()
                with open(watchdog_file, "w") as f:
                    json.dump(data, f, indent=2)
        except:
            pass

    def run(self):
        """Main entry point"""
        self.logger.info("🔥 CELSIUS AI DEFENSE SYSTEM ACTIVATED 🔥")
        self.logger.info(f"System Start Time: {self.system_start_time}")
        self.logger.info(f"Persistence Enabled: {self.persistence_enabled}")

        # Start all services
        self.start_all_services()

        # Enter defense monitoring loop
        self.run_defense_loop()

        self.logger.info("[SHIELD] Celsius AI Defense System shutdown complete")


def main():
    """Main entry point"""
    # Change to the Celsius AI directory
    os.chdir("C:/Users/micro/Celsius AI")

    # Create and run the defense system
    defense_system = CelsiusDefenseSystem()
    defense_system.run()


if __name__ == "__main__":
    main()
