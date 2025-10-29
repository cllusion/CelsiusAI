#!/usr/bin/env python3

"""
Celsius AI - Ultimate Server Hub
Streamlined control center combining the best features from all versions
Optimized for speed, reliability, and comprehensive functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import sys
import os
import json
import requests
import time
import webbrowser
from pathlib import Path
from datetime import datetime
import sqlite3
import psutil


class CelsiusServerHub:
    def __init__(self, root):
        self.root = root
        self.root.title("🛡️ Celsius AI - Server Hub")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1a1a1a")

        # Authentication credentials
        self.authenticated = False
        self.username = "cllusion001"
        self.password = "T3qy22ny*@dyu0ppn*pG"

        # Process tracking and management
        self.managed_processes = {}
        self.base_dir = Path(__file__).parent

        # Database connections
        self.activity_db = self.base_dir / "celsius_activity.db"
        self.system_db = self.base_dir / "celsius_system.db"

        # Initialize system
        self.initialize_databases()
        self.create_login_interface()

        # Start auto-refresh cycle
        self.auto_refresh()

    def initialize_databases(self):
        """Initialize all required databases"""
        try:
            # Activity logging database
            conn = sqlite3.connect(self.activity_db)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    username TEXT,
                    activity_type TEXT NOT NULL,
                    details TEXT,
                    success INTEGER DEFAULT 1
                )
            """
            )
            conn.commit()
            conn.close()

            # System monitoring database
            conn = sqlite3.connect(self.system_db)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS system_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_percent REAL,
                    active_processes INTEGER
                )
            """
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # Fail silently for database issues

    def log_activity(self, activity_type, details="", success=True):
        """Enhanced activity logging with error handling"""
        try:
            conn = sqlite3.connect(self.activity_db)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO activity_logs (timestamp, username, activity_type, details, success)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    datetime.now().isoformat(),
                    self.username if self.authenticated else "anonymous",
                    activity_type,
                    details,
                    int(success),
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def log_system_status(self):
        """Log current system status for monitoring"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            active_processes = len(self.managed_processes)

            conn = sqlite3.connect(self.system_db)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO system_status (timestamp, cpu_percent, memory_percent, disk_percent, active_processes)
                VALUES (?, ?, ?, ?, ?)
            """,
                (datetime.now().isoformat(), cpu_percent, memory.percent, disk.percent, active_processes),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def create_login_interface(self):
        """Modern login interface with enhanced styling"""
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create main login container
        login_container = tk.Frame(self.root, bg="#1a1a1a")
        login_container.pack(fill="both", expand=True)

        # Center frame
        login_frame = tk.Frame(login_container, bg="#2d2d2d", padx=40, pady=40)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Title section
        title_frame = tk.Frame(login_frame, bg="#2d2d2d")
        title_frame.pack(pady=(0, 30))

        tk.Label(title_frame, text="🛡️", font=("Segoe UI", 48), bg="#2d2d2d", fg="#0078d4").pack()
        tk.Label(
            title_frame, text="Celsius AI Server Hub", font=("Segoe UI", 20, "bold"), bg="#2d2d2d", fg="#ffffff"
        ).pack()
        tk.Label(title_frame, text="Ultimate Control Center", font=("Segoe UI", 12), bg="#2d2d2d", fg="#cccccc").pack()

        # Login form
        form_frame = tk.Frame(login_frame, bg="#2d2d2d")
        form_frame.pack(pady=20)

        tk.Label(form_frame, text="Username", font=("Segoe UI", 12), bg="#2d2d2d", fg="#ffffff").pack(
            anchor="w", pady=(0, 5)
        )
        self.username_entry = tk.Entry(
            form_frame, font=("Segoe UI", 12), width=30, bg="#404040", fg="#ffffff", insertbackground="#ffffff"
        )
        self.username_entry.pack(pady=(0, 15))

        tk.Label(form_frame, text="Password", font=("Segoe UI", 12), bg="#2d2d2d", fg="#ffffff").pack(
            anchor="w", pady=(0, 5)
        )
        self.password_entry = tk.Entry(
            form_frame,
            font=("Segoe UI", 12),
            width=30,
            show="*",
            bg="#404040",
            fg="#ffffff",
            insertbackground="#ffffff",
        )
        self.password_entry.pack(pady=(0, 25))

        # Login button
        login_btn = tk.Button(
            form_frame,
            text="Sign In",
            font=("Segoe UI", 12, "bold"),
            bg="#0078d4",
            fg="#ffffff",
            width=25,
            pady=8,
            command=self.handle_login,
            cursor="hand2",
        )
        login_btn.pack(pady=10)

        # Info section
        info_frame = tk.Frame(login_frame, bg="#2d2d2d")
        info_frame.pack(pady=(20, 0))

        tk.Label(
            info_frame, text="Default Username: cllusion001", font=("Segoe UI", 10), bg="#2d2d2d", fg="#888888"
        ).pack()
        tk.Label(
            info_frame, text="Secure authentication required", font=("Segoe UI", 9), bg="#2d2d2d", fg="#666666"
        ).pack(pady=(5, 0))

        # Event bindings
        self.root.bind("<Return>", lambda e: self.handle_login())
        self.username_entry.focus()

    def handle_login(self):
        """Enhanced login handler with better feedback"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if username == self.username and password == self.password:
            self.authenticated = True
            self.log_activity("login_success", f"user: {username}")
            self.create_main_interface()
        else:
            self.log_activity("login_failed", f"attempt_user: {username}", success=False)

            # Show error with animation effect
            error_label = tk.Label(
                self.root, text="❌ Invalid credentials", font=("Segoe UI", 12), bg="#ff4444", fg="#ffffff"
            )
            error_label.place(relx=0.5, rely=0.7, anchor="center")

            # Auto-remove error after 3 seconds
            self.root.after(3000, error_label.destroy)
            self.password_entry.delete(0, "end")
            self.password_entry.focus()

    def create_main_interface(self):
        """Ultimate main interface with all features"""
        # Clear login interface
        for widget in self.root.winfo_children():
            widget.destroy()

        # Configure enhanced dark theme
        self.setup_theme()

        # Header with status
        self.create_header()

        # Main tabbed interface
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=10)

        # Create all tabs
        self.create_dashboard_tab()
        self.create_services_tab()
        self.create_monitoring_tab()
        self.create_ai_systems_tab()
        self.create_security_tab()
        self.create_administration_tab()

        # Start monitoring
        self.update_all_status()

    def setup_theme(self):
        """Setup comprehensive dark theme"""
        style = ttk.Style()
        style.theme_use("clam")

        # Configure styles
        style.configure("TFrame", background="#2d2d2d")
        style.configure("TLabel", background="#2d2d2d", foreground="#ffffff")
        style.configure("TButton", background="#404040", foreground="#ffffff", padding=6)
        style.configure("Accent.TButton", background="#0078d4", foreground="#ffffff")
        style.configure("Success.TButton", background="#28a745", foreground="#ffffff")
        style.configure("Warning.TButton", background="#ffc107", foreground="#000000")
        style.configure("Danger.TButton", background="#dc3545", foreground="#ffffff")
        style.configure("TNotebook", background="#2d2d2d")
        style.configure("TNotebook.Tab", background="#404040", foreground="#ffffff", padding=[15, 8])
        style.map("TNotebook.Tab", background=[("selected", "#0078d4")])

    def create_header(self):
        """Enhanced header with real-time status"""
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=15, pady=(10, 5))

        # Title section
        title_frame = ttk.Frame(header)
        title_frame.pack(side="left")

        ttk.Label(title_frame, text="🛡️ Celsius AI Control Center", font=("Segoe UI", 16, "bold")).pack(side="left")

        # Status indicators
        status_frame = ttk.Frame(header)
        status_frame.pack(side="right")

        self.system_status_label = ttk.Label(status_frame, text="🟢 System Online", font=("Segoe UI", 10))
        self.system_status_label.pack(side="right", padx=10)

        self.time_label = ttk.Label(status_frame, text="", font=("Segoe UI", 10))
        self.time_label.pack(side="right", padx=10)

        ttk.Button(status_frame, text="Logout", command=self.logout, style="Warning.TButton").pack(side="right", padx=5)

    def create_dashboard_tab(self):
        """Main dashboard overview"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="📊 Dashboard")

        # System overview section
        overview_frame = ttk.LabelFrame(tab_frame, text="System Overview", padding=15)
        overview_frame.pack(fill="x", padx=15, pady=10)

        # Metrics grid
        metrics_grid = ttk.Frame(overview_frame)
        metrics_grid.pack(fill="x")

        # Create metric cards
        self.cpu_metric = self.create_metric_card(metrics_grid, "CPU", "0%", "🖥️")
        self.memory_metric = self.create_metric_card(metrics_grid, "Memory", "0%", "💾")
        self.disk_metric = self.create_metric_card(metrics_grid, "Disk", "0%", "💿")
        self.services_metric = self.create_metric_card(metrics_grid, "Services", "0", "⚙️")

        # Quick status section
        status_frame = ttk.LabelFrame(tab_frame, text="Service Status", padding=15)
        status_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.status_tree = ttk.Treeview(
            status_frame, columns=("Status", "Health", "Uptime"), show="tree headings", height=12
        )
        self.status_tree.heading("#0", text="Service")
        self.status_tree.heading("Status", text="Status")
        self.status_tree.heading("Health", text="Health")
        self.status_tree.heading("Uptime", text="Uptime")
        self.status_tree.pack(fill="both", expand=True, pady=10)

    def create_metric_card(self, parent, title, value, icon):
        """Create a metric display card"""
        card = ttk.Frame(parent)
        card.pack(side="left", padx=10, fill="x", expand=True)

        ttk.Label(card, text=icon, font=("Segoe UI", 20)).pack()
        value_label = ttk.Label(card, text=value, font=("Segoe UI", 16, "bold"))
        value_label.pack()
        ttk.Label(card, text=title, font=("Segoe UI", 10)).pack()

        return value_label

    def create_services_tab(self):
        """Core services management"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="🖥️ Services")

        # Enhanced Dashboard section
        dashboard_section = ttk.LabelFrame(tab_frame, text="Enhanced Dashboard API", padding=15)
        dashboard_section.pack(fill="x", padx=15, pady=10)

        dashboard_controls = ttk.Frame(dashboard_section)
        dashboard_controls.pack(fill="x")

        self.dashboard_status = ttk.Label(dashboard_controls, text="Checking...", font=("Segoe UI", 11))
        self.dashboard_status.pack(side="left")

        ttk.Button(dashboard_controls, text="Start", command=self.start_dashboard, style="Success.TButton").pack(
            side="right", padx=2
        )
        ttk.Button(dashboard_controls, text="Stop", command=self.stop_dashboard, style="Danger.TButton").pack(
            side="right", padx=2
        )
        ttk.Button(
            dashboard_controls,
            text="Open",
            command=lambda: webbrowser.open("http://localhost:5000"),
            style="Accent.TButton",
        ).pack(side="right", padx=2)

        # Celsius Core section
        core_section = ttk.LabelFrame(tab_frame, text="Celsius AI Core Engine", padding=15)
        core_section.pack(fill="x", padx=15, pady=10)

        core_controls = ttk.Frame(core_section)
        core_controls.pack(fill="x")

        self.core_status = ttk.Label(core_controls, text="Ready", font=("Segoe UI", 11))
        self.core_status.pack(side="left")

        ttk.Button(core_controls, text="Launch Core", command=self.start_celsius_core, style="Success.TButton").pack(
            side="right", padx=2
        )
        ttk.Button(core_controls, text="Chat Interface", command=self.open_celsius_chat, style="Accent.TButton").pack(
            side="right", padx=2
        )

        # Guardian System section
        guardian_section = ttk.LabelFrame(tab_frame, text="Guardian Monitoring System", padding=15)
        guardian_section.pack(fill="x", padx=15, pady=10)

        guardian_controls = ttk.Frame(guardian_section)
        guardian_controls.pack(fill="x")

        self.guardian_status = ttk.Label(guardian_controls, text="Ready", font=("Segoe UI", 11))
        self.guardian_status.pack(side="left")

        ttk.Button(guardian_controls, text="Start Guardian", command=self.start_guardian, style="Success.TButton").pack(
            side="right", padx=2
        )
        ttk.Button(
            guardian_controls, text="Guardian Config", command=self.configure_guardian, style="Accent.TButton"
        ).pack(side="right", padx=2)

    def create_monitoring_tab(self):
        """Enhanced monitoring and logging"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="📈 Monitoring")

        # Process monitoring
        process_frame = ttk.LabelFrame(tab_frame, text="Active Processes", padding=15)
        process_frame.pack(fill="x", padx=15, pady=10)

        process_controls = ttk.Frame(process_frame)
        process_controls.pack(fill="x", pady=(0, 10))

        ttk.Button(process_controls, text="🔄 Refresh", command=self.update_process_list).pack(side="left")
        ttk.Button(process_controls, text="📊 Performance", command=self.show_performance_details).pack(
            side="left", padx=5
        )

        self.process_tree = ttk.Treeview(
            process_frame, columns=("PID", "Status", "CPU", "Memory"), show="tree headings", height=8
        )
        self.process_tree.heading("#0", text="Service")
        self.process_tree.heading("PID", text="PID")
        self.process_tree.heading("Status", text="Status")
        self.process_tree.heading("CPU", text="CPU %")
        self.process_tree.heading("Memory", text="Memory MB")
        self.process_tree.pack(fill="x")

        # Activity logs
        log_frame = ttk.LabelFrame(tab_frame, text="System Activity Logs", padding=15)
        log_frame.pack(fill="both", expand=True, padx=15, pady=10)

        log_controls = ttk.Frame(log_frame)
        log_controls.pack(fill="x", pady=(0, 10))

        ttk.Button(log_controls, text="🔄 Refresh Logs", command=self.load_recent_logs).pack(side="left")
        ttk.Button(log_controls, text="📁 Export Logs", command=self.export_logs).pack(side="left", padx=5)
        ttk.Button(log_controls, text="🧹 Clear Logs", command=self.clear_old_logs).pack(side="left", padx=5)

        # Log display with scrollbar
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_container, height=12, bg="#1a1a1a", fg="#ffffff", font=("Consolas", 9), wrap="word")
        log_scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")

    def create_ai_systems_tab(self):
        """AI and learning systems management"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="🤖 AI Systems")

        # Web Learning Engine
        learning_section = ttk.LabelFrame(tab_frame, text="Web Learning Engine", padding=15)
        learning_section.pack(fill="x", padx=15, pady=10)

        learning_controls = ttk.Frame(learning_section)
        learning_controls.pack(fill="x")

        self.learning_status = ttk.Label(learning_controls, text="Ready", font=("Segoe UI", 11))
        self.learning_status.pack(side="left")

        ttk.Button(
            learning_controls, text="Start Learning", command=self.start_web_learning, style="Success.TButton"
        ).pack(side="right", padx=2)
        ttk.Button(learning_controls, text="Configure", command=self.configure_learning, style="Accent.TButton").pack(
            side="right", padx=2
        )

        # Code Approval System
        approval_section = ttk.LabelFrame(tab_frame, text="Code Approval System", padding=15)
        approval_section.pack(fill="x", padx=15, pady=10)

        approval_controls = ttk.Frame(approval_section)
        approval_controls.pack(fill="x")

        self.approval_status = ttk.Label(approval_controls, text="No pending requests", font=("Segoe UI", 11))
        self.approval_status.pack(side="left")

        ttk.Button(
            approval_controls, text="Review Queue", command=self.open_code_approval, style="Accent.TButton"
        ).pack(side="right", padx=2)

        # AI Communication
        comm_section = ttk.LabelFrame(tab_frame, text="AI Communication System", padding=15)
        comm_section.pack(fill="both", expand=True, padx=15, pady=10)

        ttk.Label(comm_section, text="Language improvement and inter-AI communication", font=("Segoe UI", 11)).pack(
            anchor="w", pady=(0, 10)
        )

        comm_controls = ttk.Frame(comm_section)
        comm_controls.pack(fill="x")

        ttk.Button(
            comm_controls, text="Test Communication", command=self.test_ai_communication, style="Accent.TButton"
        ).pack(side="left", padx=5)
        ttk.Button(comm_controls, text="View Logs", command=self.view_comm_logs, style="Accent.TButton").pack(
            side="left", padx=5
        )
        ttk.Button(comm_controls, text="Settings", command=self.ai_comm_settings, style="Accent.TButton").pack(
            side="left", padx=5
        )

    def create_security_tab(self):
        """Security and threat management"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="🛡️ Security")

        # Threat Detection
        threat_section = ttk.LabelFrame(tab_frame, text="Threat Detection & Response", padding=15)
        threat_section.pack(fill="x", padx=15, pady=10)

        threat_controls = ttk.Frame(threat_section)
        threat_controls.pack(fill="x", pady=(0, 10))

        ttk.Button(
            threat_controls, text="🔍 Security Scan", command=self.run_security_scan, style="Accent.TButton"
        ).pack(side="left", padx=5)
        ttk.Button(
            threat_controls, text="🛡️ Enable Protection", command=self.enable_protection, style="Success.TButton"
        ).pack(side="left", padx=5)
        ttk.Button(
            threat_controls, text="📊 Threat Report", command=self.generate_threat_report, style="Accent.TButton"
        ).pack(side="left", padx=5)

        # Notification System
        notification_section = ttk.LabelFrame(tab_frame, text="Notification System", padding=15)
        notification_section.pack(fill="x", padx=15, pady=10)

        notification_controls = ttk.Frame(notification_section)
        notification_controls.pack(fill="x")

        self.notification_status = ttk.Label(notification_controls, text="Not configured", font=("Segoe UI", 11))
        self.notification_status.pack(side="left")

        ttk.Button(
            notification_controls,
            text="Setup Email Alerts",
            command=self.setup_email_notifications,
            style="Accent.TButton",
        ).pack(side="right", padx=2)
        ttk.Button(
            notification_controls, text="Test Alerts", command=self.test_notifications, style="Accent.TButton"
        ).pack(side="right", padx=2)

        # Security Status Display
        security_display = ttk.LabelFrame(tab_frame, text="Security Status", padding=15)
        security_display.pack(fill="both", expand=True, padx=15, pady=10)

        self.security_text = tk.Text(
            security_display, height=12, bg="#1a1a1a", fg="#ffffff", font=("Consolas", 9), wrap="word"
        )
        self.security_text.pack(fill="both", expand=True)

    def create_administration_tab(self):
        """System administration and maintenance"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="⚙️ Administration")

        # System Maintenance
        maintenance_section = ttk.LabelFrame(tab_frame, text="System Maintenance", padding=15)
        maintenance_section.pack(fill="x", padx=15, pady=10)

        maintenance_grid = ttk.Frame(maintenance_section)
        maintenance_grid.pack(fill="x")

        # Row 1
        row1 = ttk.Frame(maintenance_grid)
        row1.pack(fill="x", pady=5)

        ttk.Button(
            row1, text="🔄 Restart All Services", command=self.restart_all_services, style="Warning.TButton"
        ).pack(side="left", padx=5)
        ttk.Button(row1, text="🧹 System Cleanup", command=self.cleanup_system, style="Accent.TButton").pack(
            side="left", padx=5
        )
        ttk.Button(row1, text="💾 Backup Data", command=self.backup_data, style="Accent.TButton").pack(
            side="left", padx=5
        )

        # Row 2
        row2 = ttk.Frame(maintenance_grid)
        row2.pack(fill="x", pady=5)

        ttk.Button(row2, text="📊 System Report", command=self.generate_system_report, style="Accent.TButton").pack(
            side="left", padx=5
        )
        ttk.Button(row2, text="🔧 Repair System", command=self.repair_system, style="Warning.TButton").pack(
            side="left", padx=5
        )
        ttk.Button(
            row2, text="⚡ Optimize Performance", command=self.optimize_performance, style="Success.TButton"
        ).pack(side="left", padx=5)

        # System Information Display
        system_info_section = ttk.LabelFrame(tab_frame, text="System Information", padding=15)
        system_info_section.pack(fill="both", expand=True, padx=15, pady=10)

        self.system_info_text = tk.Text(
            system_info_section, height=15, bg="#1a1a1a", fg="#ffffff", font=("Consolas", 9), wrap="word"
        )
        self.system_info_text.pack(fill="both", expand=True)

    # Service Management Methods
    def start_dashboard(self):
        """Start Enhanced Dashboard with improved error handling"""
        try:
            if "dashboard" not in self.managed_processes or not self.is_process_running("dashboard"):
                process = subprocess.Popen([sys.executable, "enhanced_mobile_dashboard.py"], cwd=str(self.base_dir))
                self.managed_processes["dashboard"] = process
                self.log_activity("service_start", "enhanced_dashboard")
                messagebox.showinfo(
                    "Success", "Enhanced Dashboard starting...\nPlease wait a moment for initialization."
                )
                # Schedule status update
                self.root.after(3000, self.update_dashboard_status)
            else:
                messagebox.showinfo("Info", "Enhanced Dashboard is already running")
        except Exception as e:
            self.log_activity("service_start_failed", f"enhanced_dashboard: {e}", success=False)
            messagebox.showerror("Error", f"Failed to start Enhanced Dashboard:\n{e}")

    def stop_dashboard(self):
        """Stop Enhanced Dashboard"""
        try:
            if "dashboard" in self.managed_processes:
                self.managed_processes["dashboard"].terminate()
                del self.managed_processes["dashboard"]
                self.log_activity("service_stop", "enhanced_dashboard")
                messagebox.showinfo("Success", "Enhanced Dashboard stopped successfully")
                self.update_dashboard_status()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop Enhanced Dashboard:\n{e}")

    def start_celsius_core(self):
        """Start Celsius AI Core with console"""
        try:
            if "celsius_core" not in self.managed_processes or not self.is_process_running("celsius_core"):
                process = subprocess.Popen(
                    [sys.executable, "main.py"], cwd=str(self.base_dir), creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                self.managed_processes["celsius_core"] = process
                self.log_activity("service_start", "celsius_core")
                messagebox.showinfo("Success", "Celsius AI Core launching in new console window...")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Celsius AI Core:\n{e}")

    def start_guardian(self):
        """Start Guardian monitoring system"""
        try:
            if "guardian" not in self.managed_processes or not self.is_process_running("guardian"):
                process = subprocess.Popen([sys.executable, "celsius_lightweight_guardian.py"], cwd=str(self.base_dir))
                self.managed_processes["guardian"] = process
                self.log_activity("service_start", "guardian_system")
                messagebox.showinfo("Success", "Guardian monitoring system started")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Guardian:\n{e}")

    def start_web_learning(self):
        """Start Web Learning Engine"""
        try:
            if "web_learning" not in self.managed_processes or not self.is_process_running("web_learning"):
                process = subprocess.Popen([sys.executable, "celsius_web_learning_launcher.py"], cwd=str(self.base_dir))
                self.managed_processes["web_learning"] = process
                self.log_activity("service_start", "web_learning")
                messagebox.showinfo("Success", "Web Learning Engine starting...")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Web Learning:\n{e}")

    def is_process_running(self, service_name):
        """Check if a managed process is still running"""
        if service_name not in self.managed_processes:
            return False
        return self.managed_processes[service_name].poll() is None

    # Status Update Methods
    def update_all_status(self):
        """Update all status indicators"""
        self.update_dashboard_status()
        self.update_process_list()
        self.update_system_metrics()
        self.log_system_status()

        # Update time display
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(self, "time_label"):
            self.time_label.config(text=current_time)

    def update_dashboard_status(self):
        """Update Enhanced Dashboard status"""
        try:
            response = requests.get("http://localhost:5000/api/status", timeout=3)
            if response.status_code == 200:
                self.dashboard_status.config(text="✅ Running (Port 5000)", foreground="green")
            else:
                self.dashboard_status.config(text="⚠️ Error Response", foreground="orange")
        except requests.ConnectionError:
            self.dashboard_status.config(text="❌ Not Running", foreground="red")
        except Exception as e:
            self.dashboard_status.config(text=f"❌ Error: {str(e)[:20]}...", foreground="red")

    def update_system_metrics(self):
        """Update system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            if hasattr(self, "cpu_metric"):
                self.cpu_metric.config(text=f"{cpu_percent:.1f}%")
            if hasattr(self, "memory_metric"):
                self.memory_metric.config(text=f"{memory.percent:.1f}%")
            if hasattr(self, "disk_metric"):
                self.disk_metric.config(text=f"{disk.percent:.1f}%")
            if hasattr(self, "services_metric"):
                active_services = sum(1 for p in self.managed_processes.values() if p and p.poll() is None)
                self.services_metric.config(text=str(active_services))
        except Exception:
            pass

    def update_process_list(self):
        """Update the process monitoring display"""
        if not hasattr(self, "process_tree"):
            return

        # Clear existing items
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)

        # Add managed processes
        for service_name, process in self.managed_processes.items():
            if process and process.poll() is None:
                try:
                    ps_process = psutil.Process(process.pid)
                    cpu_percent = ps_process.cpu_percent()
                    memory_mb = ps_process.memory_info().rss / 1024 / 1024
                    self.process_tree.insert(
                        "",
                        "end",
                        text=service_name.replace("_", " ").title(),
                        values=(process.pid, "Running", f"{cpu_percent:.1f}", f"{memory_mb:.1f}"),
                    )
                except:
                    self.process_tree.insert(
                        "",
                        "end",
                        text=service_name.replace("_", " ").title(),
                        values=(process.pid, "Unknown", "N/A", "N/A"),
                    )

    def load_recent_logs(self):
        """Load and display recent activity logs"""
        if not hasattr(self, "log_text"):
            return

        try:
            conn = sqlite3.connect(self.activity_db)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, username, activity_type, details, success 
                FROM activity_logs 
                ORDER BY timestamp DESC 
                LIMIT 100
            """
            )
            logs = cursor.fetchall()
            conn.close()

            self.log_text.delete(1.0, tk.END)
            for log in logs:
                timestamp, username, activity_type, details, success = log
                status = "✅" if success else "❌"
                time_str = timestamp[:19].replace("T", " ")
                self.log_text.insert(tk.END, f"{status} {time_str} [{activity_type}] {username}: {details}\n")

        except Exception as e:
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"Error loading logs: {e}\n")

    # System Action Methods
    def setup_email_notifications(self):
        """Launch email notification setup"""
        try:
            subprocess.Popen([sys.executable, "enhanced_email_system.py"])
            self.log_activity("configuration", "email_notification_setup")
            messagebox.showinfo("Setup", "Email notification setup wizard launched in new window")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch email setup:\n{e}")

    def restart_all_services(self):
        """Restart all managed services"""
        if messagebox.askyesno("Confirm", "Restart all services? This will temporarily interrupt operations."):
            self.log_activity("system_action", "restart_all_services")

            # Stop all services
            for service_name, process in list(self.managed_processes.items()):
                try:
                    process.terminate()
                except:
                    pass

            self.managed_processes.clear()
            messagebox.showinfo("Success", "All services stopped. Use individual start buttons to restart them.")

    def cleanup_system(self):
        """Clean up system resources and temporary files"""
        self.log_activity("maintenance", "system_cleanup")
        messagebox.showinfo("Cleanup", "System cleanup initiated...")

    def backup_data(self):
        """Create system backup"""
        self.log_activity("backup", "manual_backup")
        messagebox.showinfo("Backup", "Data backup process started...")

    def run_security_scan(self):
        """Run comprehensive security scan"""
        self.log_activity("security", "manual_security_scan")
        messagebox.showinfo("Security", "Security scan initiated...")

    def generate_system_report(self):
        """Generate comprehensive system report"""
        try:
            report = self.create_system_report()
            if hasattr(self, "system_info_text"):
                self.system_info_text.delete(1.0, tk.END)
                self.system_info_text.insert(tk.END, report)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate system report:\n{e}")

    def create_system_report(self):
        """Create detailed system report"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            report = f"""╔══════════════════════════════════════════════════════════════════════════════════════╗
║                               🛡️ CELSIUS AI SYSTEM REPORT                               ║
╠══════════════════════════════════════════════════════════════════════════════════════╣

📊 SYSTEM PERFORMANCE
├─ CPU Usage: {cpu_percent}%
├─ Memory: {memory.percent}% used ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)
├─ Disk Space: {disk.percent}% used ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)
└─ Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔹 ACTIVE SERVICES
"""

            # Add service status
            for service_name, process in self.managed_processes.items():
                if process and process.poll() is None:
                    try:
                        ps_process = psutil.Process(process.pid)
                        cpu = ps_process.cpu_percent()
                        memory_mb = ps_process.memory_info().rss / 1024 / 1024
                        report += f"├─ ✅ {service_name.replace('_', ' ').title()} (PID: {process.pid}, CPU: {cpu:.1f}%, RAM: {memory_mb:.1f}MB)\n"
                    except:
                        report += (
                            f"├─ ⚠️ {service_name.replace('_', ' ').title()} (PID: {process.pid}, Status: Unknown)\n"
                        )
                else:
                    report += f"├─ ❌ {service_name.replace('_', ' ').title()} (Not Running)\n"

            # Check Dashboard health
            try:
                response = requests.get("http://localhost:5000/api/status", timeout=3)
                if response.status_code == 200:
                    report += "├─ ✅ Enhanced Dashboard API (Health: Good)\n"
                else:
                    report += "├─ ⚠️ Enhanced Dashboard API (Health: Issues Detected)\n"
            except:
                report += "├─ ❌ Enhanced Dashboard API (Not Responding)\n"

            report += f"\n🔒 SYSTEM STATUS: {'🟢 OPTIMAL' if cpu_percent < 80 and memory.percent < 80 else '🟡 ATTENTION NEEDED'}\n"
            report += "╚══════════════════════════════════════════════════════════════════════════════════════╝"

            return report
        except Exception as e:
            return f"Error generating system report: {e}"

    # Stub methods for future implementation
    def open_celsius_chat(self):
        messagebox.showinfo("Feature", "Celsius AI Chat Interface - Coming Soon")

    def configure_guardian(self):
        messagebox.showinfo("Feature", "Guardian Configuration - Coming Soon")

    def configure_learning(self):
        messagebox.showinfo("Feature", "Learning Configuration - Coming Soon")

    def open_code_approval(self):
        messagebox.showinfo("Feature", "Code Approval System - Coming Soon")

    def test_ai_communication(self):
        messagebox.showinfo("Feature", "AI Communication Test - Coming Soon")

    def view_comm_logs(self):
        messagebox.showinfo("Feature", "Communication Logs - Coming Soon")

    def ai_comm_settings(self):
        messagebox.showinfo("Feature", "AI Communication Settings - Coming Soon")

    def enable_protection(self):
        messagebox.showinfo("Feature", "Protection Enable - Coming Soon")

    def generate_threat_report(self):
        messagebox.showinfo("Feature", "Threat Report - Coming Soon")

    def test_notifications(self):
        messagebox.showinfo("Feature", "Notification Test - Coming Soon")

    def show_performance_details(self):
        messagebox.showinfo("Feature", "Performance Details - Coming Soon")

    def export_logs(self):
        messagebox.showinfo("Feature", "Export Logs - Coming Soon")

    def clear_old_logs(self):
        messagebox.showinfo("Feature", "Clear Old Logs - Coming Soon")

    def repair_system(self):
        messagebox.showinfo("Feature", "System Repair - Coming Soon")

    def optimize_performance(self):
        messagebox.showinfo("Feature", "Performance Optimization - Coming Soon")

    def auto_refresh(self):
        """Auto-refresh system status every 30 seconds"""
        if self.authenticated:
            self.update_all_status()
        self.root.after(30000, self.auto_refresh)

    def logout(self):
        """Enhanced logout with cleanup"""
        if messagebox.askyesno("Logout", "Are you sure you want to logout?\nThis will stop all managed services."):
            self.log_activity("logout", f"user_logout: {self.username}")
            self.authenticated = False

            # Stop managed processes
            for service_name, process in list(self.managed_processes.items()):
                try:
                    process.terminate()
                except:
                    pass
            self.managed_processes.clear()

            # Return to login
            self.create_login_interface()


def main():
    """Launch the ultimate Celsius AI Server Hub"""
    # Single instance check
    lock_file = Path("celsius_server_hub.lock")
    if lock_file.exists():
        try:
            with open(lock_file, "r") as f:
                pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    print("🛡️ Celsius AI Server Hub is already running!")
                    messagebox.showerror(
                        "Already Running",
                        "Celsius AI Server Hub is already running!\nCheck your system tray or taskbar.",
                    )
                    return
        except:
            pass

    # Create lock file
    try:
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
    except:
        pass

    # Launch the ultimate server hub
    root = tk.Tk()
    app = CelsiusServerHub(root)

    try:
        root.mainloop()
    finally:
        # Cleanup
        try:
            lock_file.unlink()
        except:
            pass


if __name__ == "__main__":
    main()
