#!/usr/bin/env python3
"""
Celsius AI Health Monitor Dashboard
Real-time monitoring of service status and automatic recovery
"""

import json
import time
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading


class CelsiusHealthMonitor:
    """Real-time health monitoring dashboard for Celsius AI"""

    def __init__(self):
        self.base_dir = Path("C:/Users/micro/Celsius AI")
        self.url_file = self.base_dir / "current_url.json"
        self.log_file = self.base_dir / "logs/celsius_service.log"

        self.current_url = None
        self.last_check = None
        self.service_status = {"celsius_ai": False, "ngrok": False, "url_accessible": False}

        self.setup_gui()

    def setup_gui(self):
        """Setup the monitoring GUI"""
        self.root = tk.Tk()
        self.root.title("🌡️ Celsius AI Health Monitor")
        self.root.geometry("800x600")
        self.root.configure(bg="#000000")

        # Header
        header_frame = tk.Frame(self.root, bg="#1e40af", pady=10)
        header_frame.pack(fill="x")

        title_label = tk.Label(
            header_frame, text="🌡️ Celsius AI Health Monitor", font=("Arial", 16, "bold"), bg="#1e40af", fg="#60a5fa"
        )
        title_label.pack()

        # Status Frame
        status_frame = tk.Frame(self.root, bg="#000000", pady=10)
        status_frame.pack(fill="x", padx=10)

        # Service Status Indicators
        self.status_labels = {}
        services = ["Celsius AI", "ngrok", "URL Access"]

        for i, service in enumerate(services):
            service_frame = tk.Frame(status_frame, bg="#000000")
            service_frame.grid(row=0, column=i, padx=20, pady=5, sticky="ew")

            status_frame.grid_columnconfigure(i, weight=1)

            service_label = tk.Label(
                service_frame, text=service, font=("Arial", 12, "bold"), bg="#000000", fg="#ffffff"
            )
            service_label.pack()

            status_indicator = tk.Label(
                service_frame, text="●", font=("Arial", 20), bg="#000000", fg="#ff0000"  # Red by default
            )
            status_indicator.pack()

            self.status_labels[service.lower().replace(" ", "_")] = status_indicator

        # URL Display
        url_frame = tk.Frame(self.root, bg="#000000", pady=10)
        url_frame.pack(fill="x", padx=10)

        url_title = tk.Label(
            url_frame, text="Current Public URL:", font=("Arial", 12, "bold"), bg="#000000", fg="#60a5fa"
        )
        url_title.pack()

        self.url_var = tk.StringVar()
        self.url_label = tk.Label(
            url_frame, textvariable=self.url_var, font=("Arial", 11), bg="#000000", fg="#00ff00", cursor="hand2"
        )
        self.url_label.pack()
        self.url_label.bind("<Button-1>", self.open_url)

        # Statistics Frame
        stats_frame = tk.Frame(self.root, bg="#1e1b4b", pady=10)
        stats_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.stats_labels = {}
        stats = ["Uptime", "Restarts", "Last Check", "Response Time"]

        for i, stat in enumerate(stats):
            stat_frame = tk.Frame(stats_frame, bg="#1e1b4b")
            stat_frame.grid(row=0, column=i, padx=15, pady=5)

            stat_title = tk.Label(stat_frame, text=stat, font=("Arial", 10, "bold"), bg="#1e1b4b", fg="#60a5fa")
            stat_title.pack()

            stat_value = tk.Label(stat_frame, text="--", font=("Arial", 10), bg="#1e1b4b", fg="#ffffff")
            stat_value.pack()

            self.stats_labels[stat.lower().replace(" ", "_")] = stat_value

        # Control Buttons
        button_frame = tk.Frame(self.root, bg="#000000", pady=10)
        button_frame.pack(fill="x", padx=10)

        restart_btn = tk.Button(
            button_frame,
            text="🔄 Restart Services",
            font=("Arial", 11, "bold"),
            bg="#dc2626",
            fg="#ffffff",
            command=self.restart_services,
            padx=20,
        )
        restart_btn.pack(side="left", padx=5)

        open_url_btn = tk.Button(
            button_frame,
            text="🌐 Open URL",
            font=("Arial", 11, "bold"),
            bg="#1e40af",
            fg="#ffffff",
            command=self.open_url,
            padx=20,
        )
        open_url_btn.pack(side="left", padx=5)

        refresh_btn = tk.Button(
            button_frame,
            text="🔍 Check Now",
            font=("Arial", 11, "bold"),
            bg="#059669",
            fg="#ffffff",
            command=self.check_services,
            padx=20,
        )
        refresh_btn.pack(side="left", padx=5)

        # Log Display
        log_frame = tk.Frame(self.root, bg="#000000")
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        log_title = tk.Label(log_frame, text="📋 Recent Logs:", font=("Arial", 12, "bold"), bg="#000000", fg="#60a5fa")
        log_title.pack(anchor="w")

        self.log_display = scrolledtext.ScrolledText(
            log_frame, bg="#1a1a1a", fg="#ffffff", font=("Consolas", 9), height=10
        )
        self.log_display.pack(fill="both", expand=True, pady=(5, 0))

        # Start monitoring
        self.start_monitoring()

    def check_services(self):
        """Check the status of all services"""
        try:
            # Check if processes are running
            result = subprocess.run(
                'tasklist | findstr "python.exe ngrok.exe"', shell=True, capture_output=True, text=True
            )

            processes = result.stdout.lower()
            self.service_status["celsius_ai"] = "python.exe" in processes
            self.service_status["ngrok"] = "ngrok.exe" in processes

            # Update status indicators
            self.update_status_indicator("celsius_ai", self.service_status["celsius_ai"])
            self.update_status_indicator("ngrok", self.service_status["ngrok"])

            # Check URL accessibility
            self.check_url_access()

            # Update last check time
            self.last_check = datetime.now()
            self.stats_labels["last_check"].config(text=self.last_check.strftime("%H:%M:%S"))

            # Load current URL
            self.load_current_url()

            # Update logs
            self.update_logs()

        except Exception as e:
            self.log_display.insert(tk.END, f"Error checking services: {e}\n")
            self.log_display.see(tk.END)

    def update_status_indicator(self, service, status):
        """Update status indicator color"""
        color = "#00ff00" if status else "#ff0000"  # Green if running, red if not
        self.status_labels[service].config(fg=color)

    def check_url_access(self):
        """Check if the current URL is accessible"""
        try:
            if self.current_url:
                start_time = time.time()
                response = requests.get(self.current_url, timeout=5)
                response_time = round((time.time() - start_time) * 1000)  # ms

                accessible = response.status_code == 200
                self.service_status["url_accessible"] = accessible
                self.update_status_indicator("url_access", accessible)
                self.stats_labels["response_time"].config(text=f"{response_time}ms")
            else:
                self.service_status["url_accessible"] = False
                self.update_status_indicator("url_access", False)
                self.stats_labels["response_time"].config(text="--")
        except:
            self.service_status["url_accessible"] = False
            self.update_status_indicator("url_access", False)
            self.stats_labels["response_time"].config(text="Error")

    def load_current_url(self):
        """Load current URL from file"""
        try:
            if self.url_file.exists():
                with open(self.url_file, "r") as f:
                    data = json.load(f)
                    self.current_url = data.get("url")
                    if self.current_url:
                        self.url_var.set(self.current_url)
                        restart_count = data.get("restart_count", 0)
                        self.stats_labels["restarts"].config(text=str(restart_count))
        except:
            pass

    def update_logs(self):
        """Update log display with recent entries"""
        try:
            if self.log_file.exists():
                with open(self.log_file, "r") as f:
                    lines = f.readlines()
                    recent_lines = lines[-10:]  # Last 10 lines

                    # Clear and update log display
                    self.log_display.delete(1.0, tk.END)
                    for line in recent_lines:
                        self.log_display.insert(tk.END, line)
                    self.log_display.see(tk.END)
        except:
            pass

    def restart_services(self):
        """Restart all services"""
        self.log_display.insert(tk.END, "🔄 Restarting services...\n")
        self.log_display.see(tk.END)

        try:
            # Stop existing services
            subprocess.run('taskkill /f /im python.exe /fi "windowtitle eq celsius*"', shell=True)
            subprocess.run("taskkill /f /im ngrok.exe", shell=True)

            time.sleep(2)

            # Start persistent service
            subprocess.Popen(
                [str(self.base_dir / ".venv/Scripts/python.exe"), "persistent_celsius_service.py"],
                cwd=str(self.base_dir),
            )

            self.log_display.insert(tk.END, "✅ Services restarted\n")
            self.log_display.see(tk.END)

        except Exception as e:
            self.log_display.insert(tk.END, f"❌ Restart failed: {e}\n")
            self.log_display.see(tk.END)

    def open_url(self, event=None):
        """Open current URL in browser"""
        if self.current_url:
            subprocess.run(f"start {self.current_url}", shell=True)

    def monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                self.check_services()
                time.sleep(10)  # Check every 10 seconds
            except:
                time.sleep(30)  # Wait longer if error

    def start_monitoring(self):
        """Start the monitoring thread"""
        monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        monitor_thread.start()

        # Initial check
        self.check_services()

    def run(self):
        """Start the GUI"""
        self.root.mainloop()


if __name__ == "__main__":
    monitor = CelsiusHealthMonitor()
    monitor.run()
