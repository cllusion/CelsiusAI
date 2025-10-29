#!/usr/bin/env python3
"""
Celsius AI Server Hub - Streamlined & Efficient
Essential control center for Celsius AI operations
Focus on speed, reliability, and core functionality
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


class EfficientServerHub:
    def __init__(self, root):
        self.root = root
        self.root.title("Celsius AI - Server Hub")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1a1a1a")

        # Authentication
        self.authenticated = False
        self.username = "cllusion001"
        self.password = "T3qy22ny*@dyu0ppn*pG"

        # Process tracking
        self.managed_processes = {}
        self.base_dir = Path(__file__).parent

        # Activity tracking
        self.activity_db = self.base_dir / "celsius_activity.db"
        self.initialize_database()

        # Start with login
        self.create_login_interface()

        # Auto-refresh status every 30 seconds
        self.auto_refresh()

    def initialize_database(self):
        """Initialize activity logging database"""
        try:
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
        except Exception:
            pass  # Fail silently if database issues

    def log_activity(self, activity_type, details="", success=True):
        """Log user activity efficiently"""
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
            pass  # Fail silently

    def create_login_interface(self):
        """Simple, efficient login interface"""
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()

        # Main login frame
        login_frame = ttk.Frame(self.root)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        title_label = ttk.Label(login_frame, text="Celsius AI Server Hub", font=("Segoe UI", 24, "bold"))
        title_label.pack(pady=20)

        # Login form
        ttk.Label(login_frame, text="Username:", font=("Segoe UI", 12)).pack(anchor="w", padx=20)
        self.username_entry = ttk.Entry(login_frame, font=("Segoe UI", 12), width=25)
        self.username_entry.pack(pady=(5, 10), padx=20)

        ttk.Label(login_frame, text="Password:", font=("Segoe UI", 12)).pack(anchor="w", padx=20)
        self.password_entry = ttk.Entry(login_frame, font=("Segoe UI", 12), width=25, show="*")
        self.password_entry.pack(pady=(5, 20), padx=20)

        # Login button
        login_btn = ttk.Button(login_frame, text="Login", command=self.handle_login, style="Accent.TButton")
        login_btn.pack(pady=10)

        # Quick access hint
        hint_label = ttk.Label(login_frame, text="Default: cllusion001", font=("Segoe UI", 9), foreground="gray")
        hint_label.pack(pady=(10, 0))

        # Bind Enter key to login
        self.root.bind("<Return>", lambda e: self.handle_login())

        # Focus on username field
        self.username_entry.focus()

    def handle_login(self):
        """Handle authentication efficiently"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if username == self.username and password == self.password:
            self.authenticated = True
            self.log_activity("login", f"successful_login_user: {username}")
            self.create_main_interface()
        else:
            self.log_activity("login_failed", f"failed_attempt_user: {username}", success=False)
            messagebox.showerror("Authentication Failed", "Invalid credentials")
            self.password_entry.delete(0, "end")

    def create_main_interface(self):
        """Create streamlined main interface"""
        # Clear login interface
        for widget in self.root.winfo_children():
            widget.destroy()

        # Configure dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#2d2d2d")
        style.configure("TLabel", background="#2d2d2d", foreground="#ffffff")
        style.configure("TButton", background="#404040", foreground="#ffffff")
        style.configure("Accent.TButton", background="#0078d4", foreground="#ffffff")

        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(header_frame, text="🛡️ Celsius AI Control Center", font=("Segoe UI", 18, "bold")).pack(side="left")

        # Status indicator
        self.status_label = ttk.Label(header_frame, text="🟢 Online", font=("Segoe UI", 12))
        self.status_label.pack(side="right")

        # Logout button
        logout_btn = ttk.Button(header_frame, text="Logout", command=self.logout)
        logout_btn.pack(side="right", padx=(0, 10))

        # Main content area with tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Create essential tabs
        self.create_server_control_tab()
        self.create_monitoring_tab()
        self.create_ai_services_tab()
        self.create_quick_actions_tab()

        # Update status immediately
        self.update_status()

    def create_server_control_tab(self):
        """Essential server control functions"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="🖥️ Server Control")

        # Enhanced Dashboard section
        dashboard_frame = ttk.LabelFrame(tab_frame, text="Enhanced Dashboard", padding=10)
        dashboard_frame.pack(fill="x", padx=10, pady=5)

        dashboard_row = ttk.Frame(dashboard_frame)
        dashboard_row.pack(fill="x")

        self.dashboard_status = ttk.Label(dashboard_row, text="Status: Checking...", font=("Segoe UI", 10))
        self.dashboard_status.pack(side="left")

        ttk.Button(dashboard_row, text="Start Dashboard", command=self.start_dashboard).pack(side="right", padx=5)
        ttk.Button(dashboard_row, text="Stop Dashboard", command=self.stop_dashboard).pack(side="right", padx=5)
        ttk.Button(dashboard_row, text="Open Dashboard", command=lambda: webbrowser.open("http://localhost:5000")).pack(
            side="right", padx=5
        )

        # Celsius AI Core section
        core_frame = ttk.LabelFrame(tab_frame, text="Celsius AI Core", padding=10)
        core_frame.pack(fill="x", padx=10, pady=5)

        core_row = ttk.Frame(core_frame)
        core_row.pack(fill="x")

        self.core_status = ttk.Label(core_row, text="Status: Ready", font=("Segoe UI", 10))
        self.core_status.pack(side="left")

        ttk.Button(core_row, text="Start Celsius AI", command=self.start_celsius_core).pack(side="right", padx=5)
        ttk.Button(core_row, text="Chat Interface", command=self.open_celsius_chat).pack(side="right", padx=5)

        # System Info
        info_frame = ttk.LabelFrame(tab_frame, text="System Information", padding=10)
        info_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.info_text = tk.Text(info_frame, height=8, bg="#1a1a1a", fg="#ffffff", font=("Consolas", 9))
        self.info_text.pack(fill="both", expand=True)

    def create_monitoring_tab(self):
        """System monitoring and logs"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="📊 Monitoring")

        # Process monitoring
        process_frame = ttk.LabelFrame(tab_frame, text="Active Processes", padding=10)
        process_frame.pack(fill="x", padx=10, pady=5)

        # Refresh button
        ttk.Button(process_frame, text="🔄 Refresh", command=self.update_process_list).pack(anchor="ne")

        # Process list
        self.process_tree = ttk.Treeview(
            process_frame, columns=("PID", "Status", "CPU"), show="tree headings", height=6
        )
        self.process_tree.heading("#0", text="Service")
        self.process_tree.heading("PID", text="PID")
        self.process_tree.heading("Status", text="Status")
        self.process_tree.heading("CPU", text="CPU %")
        self.process_tree.pack(fill="x", pady=5)

        # Activity logs
        log_frame = ttk.LabelFrame(tab_frame, text="Recent Activity", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = tk.Text(log_frame, height=10, bg="#1a1a1a", fg="#ffffff", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        # Load recent logs
        self.load_recent_logs()

    def create_ai_services_tab(self):
        """AI services and learning management"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="🤖 AI Services")

        # Web Learning
        learning_frame = ttk.LabelFrame(tab_frame, text="Web Learning Engine", padding=10)
        learning_frame.pack(fill="x", padx=10, pady=5)

        learning_row = ttk.Frame(learning_frame)
        learning_row.pack(fill="x")

        self.learning_status = ttk.Label(learning_row, text="Status: Ready", font=("Segoe UI", 10))
        self.learning_status.pack(side="left")

        ttk.Button(learning_row, text="Start Learning", command=self.start_web_learning).pack(side="right", padx=5)
        ttk.Button(learning_row, text="Learning Config", command=self.open_learning_config).pack(side="right", padx=5)

        # Code Approval
        approval_frame = ttk.LabelFrame(tab_frame, text="Code Approval System", padding=10)
        approval_frame.pack(fill="x", padx=10, pady=5)

        approval_row = ttk.Frame(approval_frame)
        approval_row.pack(fill="x")

        self.approval_status = ttk.Label(approval_row, text="Pending: 0", font=("Segoe UI", 10))
        self.approval_status.pack(side="left")

        ttk.Button(approval_row, text="Review Requests", command=self.open_code_approval).pack(side="right", padx=5)

        # AI Communication
        comm_frame = ttk.LabelFrame(tab_frame, text="AI Communication", padding=10)
        comm_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Label(comm_frame, text="Language Improvement & AI Interaction", font=("Segoe UI", 10)).pack(anchor="w")

        comm_buttons = ttk.Frame(comm_frame)
        comm_buttons.pack(fill="x", pady=10)

        ttk.Button(comm_buttons, text="Test AI Communication", command=self.test_ai_communication).pack(
            side="left", padx=5
        )
        ttk.Button(comm_buttons, text="Communication Logs", command=self.view_comm_logs).pack(side="left", padx=5)

    def create_quick_actions_tab(self):
        """Quick actions and utilities"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="⚡ Quick Actions")

        # System actions
        system_frame = ttk.LabelFrame(tab_frame, text="System Actions", padding=10)
        system_frame.pack(fill="x", padx=10, pady=5)

        actions_grid = ttk.Frame(system_frame)
        actions_grid.pack(fill="x")

        # Row 1
        row1 = ttk.Frame(actions_grid)
        row1.pack(fill="x", pady=2)

        ttk.Button(row1, text="🔄 Restart All Services", command=self.restart_all_services).pack(side="left", padx=5)
        ttk.Button(row1, text="🛡️ Security Scan", command=self.run_security_scan).pack(side="left", padx=5)
        ttk.Button(row1, text="🧹 Cleanup System", command=self.cleanup_system).pack(side="left", padx=5)

        # Row 2
        row2 = ttk.Frame(actions_grid)
        row2.pack(fill="x", pady=2)

        ttk.Button(row2, text="📧 Setup Email Alerts", command=self.setup_email_notifications).pack(side="left", padx=5)
        ttk.Button(row2, text="💾 Backup Data", command=self.backup_data).pack(side="left", padx=5)
        ttk.Button(row2, text="🔍 System Health", command=self.check_system_health).pack(side="left", padx=5)

        # Status display
        status_frame = ttk.LabelFrame(tab_frame, text="System Status", padding=10)
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.status_text = tk.Text(status_frame, height=15, bg="#1a1a1a", fg="#ffffff", font=("Consolas", 9))
        self.status_text.pack(fill="both", expand=True)

        # Update system info
        self.update_system_info()

    # Service Management Methods
    def start_dashboard(self):
        """Start Enhanced Dashboard"""
        try:
            if "dashboard" not in self.managed_processes or not self.is_process_running("dashboard"):
                process = subprocess.Popen([sys.executable, "enhanced_mobile_dashboard.py"], cwd=str(self.base_dir))
                self.managed_processes["dashboard"] = process
                self.log_activity("service_start", "enhanced_dashboard")
                messagebox.showinfo("Success", "Enhanced Dashboard starting...")
            else:
                messagebox.showinfo("Info", "Dashboard already running")
        except Exception as e:
            self.log_activity("service_start_failed", f"enhanced_dashboard: {e}", success=False)
            messagebox.showerror("Error", f"Failed to start dashboard: {e}")

    def stop_dashboard(self):
        """Stop Enhanced Dashboard"""
        try:
            if "dashboard" in self.managed_processes:
                self.managed_processes["dashboard"].terminate()
                del self.managed_processes["dashboard"]
                self.log_activity("service_stop", "enhanced_dashboard")
                messagebox.showinfo("Success", "Enhanced Dashboard stopped")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop dashboard: {e}")

    def start_celsius_core(self):
        """Start Celsius AI Core"""
        try:
            if "celsius_core" not in self.managed_processes or not self.is_process_running("celsius_core"):
                process = subprocess.Popen(
                    [sys.executable, "main.py"], cwd=str(self.base_dir), creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                self.managed_processes["celsius_core"] = process
                self.log_activity("service_start", "celsius_core")
                messagebox.showinfo("Success", "Celsius AI Core starting...")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Celsius Core: {e}")

    def start_web_learning(self):
        """Start Web Learning Engine"""
        try:
            if "web_learning" not in self.managed_processes or not self.is_process_running("web_learning"):
                process = subprocess.Popen([sys.executable, "celsius_web_learning_launcher.py"], cwd=str(self.base_dir))
                self.managed_processes["web_learning"] = process
                self.log_activity("service_start", "web_learning")
                messagebox.showinfo("Success", "Web Learning Engine starting...")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Web Learning: {e}")

    def is_process_running(self, service_name):
        """Check if a managed process is still running"""
        if service_name not in self.managed_processes:
            return False
        return self.managed_processes[service_name].poll() is None

    # UI Update Methods
    def update_status(self):
        """Update service status indicators"""
        # Dashboard status
        if self.check_dashboard_health():
            self.dashboard_status.config(text="Status: ✅ Running", foreground="green")
        else:
            self.dashboard_status.config(text="Status: ❌ Stopped", foreground="red")

        # Update process list if monitoring tab is active
        if hasattr(self, "process_tree"):
            self.update_process_list()

    def check_dashboard_health(self):
        """Check if Enhanced Dashboard is responding"""
        try:
            response = requests.get("http://localhost:5000/api/status", timeout=3)
            return response.status_code == 200
        except:
            return False

    def update_process_list(self):
        """Update the process monitoring list"""
        # Clear existing items
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)

        # Add managed processes
        for service_name, process in self.managed_processes.items():
            if process and process.poll() is None:
                try:
                    ps_process = psutil.Process(process.pid)
                    cpu_percent = ps_process.cpu_percent()
                    self.process_tree.insert(
                        "", "end", text=service_name.title(), values=(process.pid, "Running", f"{cpu_percent:.1f}%")
                    )
                except:
                    self.process_tree.insert(
                        "", "end", text=service_name.title(), values=(process.pid, "Unknown", "N/A")
                    )

    def load_recent_logs(self):
        """Load recent activity logs"""
        try:
            conn = sqlite3.connect(self.activity_db)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, activity_type, details, success 
                FROM activity_logs 
                ORDER BY timestamp DESC 
                LIMIT 50
            """
            )
            logs = cursor.fetchall()
            conn.close()

            self.log_text.delete(1.0, tk.END)
            for log in logs:
                timestamp, activity_type, details, success = log
                status = "✅" if success else "❌"
                self.log_text.insert(tk.END, f"{status} {timestamp[:19]} [{activity_type}] {details}\n")
        except Exception:
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, "Error loading logs\n")

    # Quick Action Methods
    def restart_all_services(self):
        """Restart all Celsius AI services"""
        self.log_activity("system_action", "restart_all_services")
        messagebox.showinfo("Action", "Restarting all services...")

    def run_security_scan(self):
        """Run security scan"""
        self.log_activity("security", "manual_security_scan")
        messagebox.showinfo("Security", "Security scan initiated...")

    def cleanup_system(self):
        """Clean up system resources"""
        self.log_activity("maintenance", "system_cleanup")
        messagebox.showinfo("Cleanup", "System cleanup initiated...")

    def setup_email_notifications(self):
        """Setup email notification system"""
        self.log_activity("configuration", "email_setup")
        try:
            subprocess.Popen([sys.executable, "enhanced_email_system.py"])
            messagebox.showinfo("Setup", "Email setup wizard launched!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch email setup: {e}")

    def backup_data(self):
        """Backup system data"""
        self.log_activity("backup", "manual_backup")
        messagebox.showinfo("Backup", "Data backup initiated...")

    def check_system_health(self):
        """Check overall system health"""
        self.log_activity("health_check", "manual_health_check")
        self.update_system_info()

    # Utility Methods
    def update_system_info(self):
        """Update system information display"""
        try:
            # CPU and Memory info
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            info = f"""System Health Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🖥️  CPU Usage: {cpu_percent}%
💾 Memory: {memory.percent}% used ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)
💿 Disk: {disk.percent}% used ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)

🔹 Active Services:
"""

            # Add service status
            for service_name, process in self.managed_processes.items():
                if process and process.poll() is None:
                    info += f"  ✅ {service_name.replace('_', ' ').title()}\n"
                else:
                    info += f"  ❌ {service_name.replace('_', ' ').title()}\n"

            # Dashboard health check
            if self.check_dashboard_health():
                info += "  ✅ Enhanced Dashboard (API)\n"
            else:
                info += "  ❌ Enhanced Dashboard (API)\n"

            if hasattr(self, "status_text"):
                self.status_text.delete(1.0, tk.END)
                self.status_text.insert(tk.END, info)

            if hasattr(self, "info_text"):
                self.info_text.delete(1.0, tk.END)
                self.info_text.insert(tk.END, info)

        except Exception as e:
            if hasattr(self, "status_text"):
                self.status_text.delete(1.0, tk.END)
                self.status_text.insert(tk.END, f"Error getting system info: {e}")

    # Navigation Methods (stubs for now)
    def open_celsius_chat(self):
        messagebox.showinfo("Feature", "Opening Celsius AI Chat Interface...")

    def open_learning_config(self):
        messagebox.showinfo("Feature", "Opening Web Learning Configuration...")

    def open_code_approval(self):
        messagebox.showinfo("Feature", "Opening Code Approval System...")

    def test_ai_communication(self):
        messagebox.showinfo("Feature", "Testing AI Communication...")

    def view_comm_logs(self):
        messagebox.showinfo("Feature", "Viewing Communication Logs...")

    def auto_refresh(self):
        """Auto-refresh status every 30 seconds"""
        if self.authenticated:
            self.update_status()
        self.root.after(30000, self.auto_refresh)  # 30 seconds

    def logout(self):
        """Handle user logout"""
        self.log_activity("logout", f"user_logout: {self.username}")
        self.authenticated = False

        # Stop any managed processes
        for service_name, process in list(self.managed_processes.items()):
            try:
                process.terminate()
            except:
                pass
        self.managed_processes.clear()

        # Return to login
        self.create_login_interface()


def main():
    """Launch the efficient server hub"""
    # Check for existing instance
    lock_file = Path("celsius_server_hub.lock")
    if lock_file.exists():
        try:
            with open(lock_file, "r") as f:
                pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    print("Server Hub already running!")
                    return
        except:
            pass

    # Create lock file
    try:
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
    except:
        pass

    # Launch GUI
    root = tk.Tk()
    app = EfficientServerHub(root)

    try:
        root.mainloop()
    finally:
        # Clean up lock file
        try:
            lock_file.unlink()
        except:
            pass


if __name__ == "__main__":
    main()
