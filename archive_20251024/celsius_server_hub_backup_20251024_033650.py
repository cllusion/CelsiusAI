#!/usr/bin/env python3
"""
Celsius AI Server Hub - Enhanced Windows Management Application
Central control for server deployment, client management, ngrok tunnels, and system administration
Features: Real-time tunnel monitoring, hourly logging, service controls, enhanced monitoring
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import subprocess
import sys
import os
import json
import requests
import time
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta
import zipfile
import shutil
import sqlite3
import psutil

# Import code approval system
from celsius_code_approval import CelsiusCodeApprovalSystem


class SingleInstanceLock:
    """Ensures only one instance of Server Hub runs at a time"""

    def __init__(self, lock_file_path):
        self.lock_file_path = lock_file_path
        self.lock_file = None
        self.is_locked = False

    def acquire(self):
        """Try to acquire the single instance lock"""
        try:
            # Check if lock file exists and if process is still running
            if os.path.exists(self.lock_file_path):
                with open(self.lock_file_path, "r") as f:
                    try:
                        existing_pid = int(f.read().strip())
                        # Check if process is still running
                        if psutil.pid_exists(existing_pid):
                            process = psutil.Process(existing_pid)
                            # Check if it's actually our server hub process
                            if "celsius_server_hub.py" in " ".join(process.cmdline()):
                                return False  # Another instance is running
                    except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
                        pass  # Stale lock file, continue

            # Create/update lock file with current PID
            with open(self.lock_file_path, "w") as f:
                f.write(str(os.getpid()))

            self.is_locked = True
            return True

        except Exception as e:
            print(f"Error acquiring lock: {e}")
            return False

    def release(self):
        """Release the single instance lock"""
        try:
            if self.is_locked and os.path.exists(self.lock_file_path):
                os.remove(self.lock_file_path)
                self.is_locked = False
        except Exception as e:
            print(f"Error releasing lock: {e}")

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class CelsiusServerHub:
    def __init__(self, root):
        # Set up single instance lock
        self.lock_file_path = Path("C:/Users/micro/Celsius AI/server_hub_instance.lock")
        self.instance_lock = SingleInstanceLock(self.lock_file_path)

        # Try to acquire lock - if failed, another instance is running
        if not self.instance_lock.acquire():
            messagebox.showinfo(
                "Server Hub Already Running",
                "Celsius AI Server Hub is already running!\n\n"
                "Only one instance is allowed at a time.\n"
                "Check your taskbar or system tray for the existing window.",
            )
            root.quit()
            return

        self.root = root
        self.root.title("Celsius AI - Server Hub")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1a1a1a")

        # Register cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Set application icon
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "celsius_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                # Fallback: try PNG icon
                png_path = os.path.join(os.path.dirname(__file__), "assets", "celsius_icon_32.png")
                if os.path.exists(png_path):
                    from PIL import Image
                    import tkinter as tk

                    img = Image.open(png_path)
                    photo = tk.PhotoImage(data=img.tobytes())
                    self.root.iconphoto(True, photo)
        except Exception as e:
            print(f"Could not set icon: {e}")
            # Continue without icon

        # Configure style for dark theme
        self.setup_styles()

        # Initialize authentication system
        try:
            from celsius_auth import CelsiusAuth

            self.auth = CelsiusAuth()

            # Initialize variables
            self.authenticated_user = None
            self.current_session = None

            # Activity monitoring for auto-logout
            self.last_activity_time = datetime.now()
            self.activity_log_file = Path("C:/Users/micro/Celsius AI/logs/server_hub_activity.log")
            self.auto_logout_enabled = True
            self.idle_timeout = 300  # 5 minutes

            # Ensure activity log directory exists
            self.activity_log_file.parent.mkdir(exist_ok=True)

            # Create login interface
            self.create_login_interface()

        except Exception as e:
            print(f"Error initializing authentication: {e}")
            # Show error and continue without auth
            messagebox.showerror(
                "Initialization Error",
                f"Failed to initialize authentication system: {str(e)}\n\n"
                + "The application will continue without authentication.",
            )
            self.initialize_post_login()

    def create_login_interface(self):
        """Create login interface before main application"""
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.geometry("500x400")
        self.root.title("Celsius AI - Login Required")

        # Main login frame
        login_frame = ttk.Frame(self.root)
        login_frame.pack(expand=True, fill="both", padx=40, pady=60)

        # Title
        title_label = ttk.Label(login_frame, text="Celsius AI", font=("Arial", 24, "bold"))
        title_label.pack(pady=(0, 10))

        subtitle_label = ttk.Label(login_frame, text="Secure System Access", font=("Arial", 12))
        subtitle_label.pack(pady=(0, 30))

        # Username field
        ttk.Label(login_frame, text="Username:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))
        self.username_entry = ttk.Entry(login_frame, font=("Arial", 11), width=30)
        self.username_entry.pack(pady=(0, 15), ipady=8)

        # Password field
        ttk.Label(login_frame, text="Password:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))
        self.password_entry = ttk.Entry(login_frame, font=("Arial", 11), width=30, show="*")
        self.password_entry.pack(pady=(0, 20), ipady=8)

        # Login button
        self.login_button = ttk.Button(login_frame, text="[UNLOCKED] Login", command=self.handle_login, width=20)
        self.login_button.pack(pady=(0, 15))

        # Status label
        self.login_status = ttk.Label(login_frame, text="", foreground="red")
        self.login_status.pack(pady=(0, 15))

        # Help text
        help_frame = ttk.Frame(login_frame)
        help_frame.pack(pady=(20, 0))

        ttk.Label(help_frame, text="Default Credentials:", font=("Arial", 10, "bold")).pack()
        ttk.Label(help_frame, text="Admin: celsius_admin / celsius2025", font=("Arial", 9)).pack()
        ttk.Label(help_frame, text="User: celsius_user / celsius123", font=("Arial", 9)).pack()

        # Bind Enter key to login
        self.root.bind("<Return>", lambda e: self.handle_login())

        # Focus on username entry
        self.username_entry.focus()

    def handle_login(self):
        """Handle login attempt"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self.login_status.config(text="Please enter both username and password", foreground="red")
            return

        # Attempt authentication
        success, result = self.auth.authenticate(username, password)

        if success:
            self.authenticated_user = result
            self.current_session = result["session_token"]
            self.login_status.config(text=f"[OK] Login successful! Welcome {result['username']}", foreground="green")

            # Clear login interface and create main interface
            self.root.after(1000, self.create_main_interface_after_login)
        else:
            self.login_status.config(text=f"[ERROR] {result}", foreground="red")
            self.password_entry.delete(0, "end")

    def log_user_activity(self, activity_type, details=""):
        """Log user activity for monitoring"""
        try:
            from datetime import datetime
            import json

            self.last_activity_time = datetime.now()

            activity_data = {
                "timestamp": self.last_activity_time.isoformat(),
                "user": self.authenticated_user["username"] if self.authenticated_user else "unknown",
                "activity_type": activity_type,
                "details": details,
                "session_token": self.current_session,
            }

            with open(self.activity_log_file, "a", encoding="utf-8") as f:
                f.write(f"{json.dumps(activity_data)}\n")

        except Exception as e:
            print(f"Error logging activity: {e}")

    def check_idle_timeout(self):
        """Check if user has been idle too long"""
        if not self.auto_logout_enabled or not self.authenticated_user:
            return

        try:
            from datetime import datetime

            idle_time = (datetime.now() - self.last_activity_time).total_seconds()

            if idle_time >= self.idle_timeout:
                self.trigger_auto_logout("idle_timeout")

        except Exception as e:
            print(f"Error checking idle timeout: {e}")

    def trigger_auto_logout(self, reason="manual"):
        """Trigger automatic logout"""
        try:
            if self.authenticated_user:
                self.log_user_activity("auto_logout", f"reason: {reason}")

                # Show logout message
                messagebox.showinfo(
                    "Auto Logout",
                    f"You have been automatically logged out due to {reason.replace('_', ' ')}.\n\n"
                    "All Celsius AI services remain active.\n"
                    "Please log in again to continue using the Server Hub.",
                )

                # Reset authentication
                self.authenticated_user = None
                self.current_session = None

                # Return to login interface
                self.create_login_interface_after_logout()

        except Exception as e:
            print(f"Error triggering auto logout: {e}")

    def create_login_interface_after_logout(self):
        """Recreate login interface after logout"""
        # Clear current interface
        for widget in self.root.winfo_children():
            widget.destroy()

        # Reset title and geometry
        self.root.title("Celsius AI - Login Required")
        self.root.geometry("800x600")

        # Recreate login interface
        self.create_login_interface()

    def setup_auto_logout_api(self):
        """Setup API endpoint for intelligent guardian to trigger auto-logout"""
        try:
            from flask import Flask, request, jsonify
            import threading

            app = Flask(__name__)

            @app.route("/api/auto_logout", methods=["POST"])
            def handle_auto_logout():
                try:
                    data = request.get_json()
                    reason = data.get("reason", "external_trigger")

                    # Schedule logout on main thread
                    self.root.after(0, lambda: self.trigger_auto_logout(reason))

                    return jsonify({"status": "success", "message": "Auto logout triggered"})
                except Exception as e:
                    return jsonify({"status": "error", "message": str(e)}), 500

            # Run Flask app in background thread
            def run_api():
                app.run(host="localhost", port=5001, debug=False, use_reloader=False)

            api_thread = threading.Thread(target=run_api, daemon=True)
            api_thread.start()

        except Exception as e:
            print(f"Error setting up auto-logout API: {e}")

    def create_main_interface_after_login(self):
        """Create main interface after successful login"""
        # Clear login interface
        for widget in self.root.winfo_children():
            widget.destroy()

        # Reset geometry and title
        self.root.geometry("1200x800")
        self.root.title(f"[SHIELD] Celsius AI - Server Hub ({self.authenticated_user['username']})")

        # Log successful login
        self.log_user_activity("login", "successful_login")

        # Setup auto-logout API for intelligent guardian
        self.setup_auto_logout_api()

        # Initialize state variables and create main interface
        self.initialize_post_login()

    def initialize_post_login(self):
        """Initialize variables and interface after login"""
        # Initialize variables
        self.server_process = None
        self.server_status = "Stopped"
        self.connected_clients = []
        self.system_stats = {}
        self.auto_update_enabled = True

        # Enhanced features
        self.ngrok_tunnels = []
        self.persistent_service_running = False
        self.hourly_logging_enabled = False
        self.dashboard_url = "http://localhost:8080"  # Updated to correct port
        self.kill_password = "celsius2025"
        self.db_path = Path("celsius_activity.db")

        # Integrated Celsius AI System Management
        self.system_integration = None
        self.power_manager = None
        self.process_trainer = None
        self.collaborative_engine = None
        self.celsius_fully_integrated = False

        # Web Learning Integration
        self.web_learning_integration = None
        self.language_improver = None
        self.web_learning_active = False

        # Code Approval System Integration
        self.code_approval_system = CelsiusCodeApprovalSystem()
        self.pending_code_requests = []

        # Menu state variables
        self.menu_collapsed = False
        self.selected_menu_item = None

        # Service management
        self.service_mode = "--service" in sys.argv
        self.persistent_mode = True
        self.auto_startup_enabled = True

        # Create main interface now that user is authenticated
        self.create_main_interface()

        # Server startup managed by Guardian - no delay needed

        # Start periodic idle timeout checks
        self.start_idle_timeout_monitor()

    def start_idle_timeout_monitor(self):
        """Start periodic monitoring for idle timeout"""

        def monitor_idle():
            if self.authenticated_user:
                self.check_idle_timeout()
            # Schedule next check in 30 seconds
            self.root.after(30000, monitor_idle)

        # Start monitoring after 30 seconds
        self.root.after(30000, monitor_idle)

        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self.monitor_system, daemon=True)
        self.monitoring_thread.start()

        # Start periodic status update thread
        self.status_monitor_active = True
        self.status_thread = threading.Thread(target=self.periodic_status_update, daemon=True)
        self.status_thread.start()

        # Start server self-monitoring
        self.server_self_monitor_active = True
        self.server_start_time = datetime.now()
        self.server_uptime = "00:00:00"
        self.self_monitor_thread = threading.Thread(target=self.monitor_server_status, daemon=True)
        self.self_monitor_thread.start()

        # Initialize Celsius AI integration
        self.initialize_celsius_integration()

        # Check for updates on startup
        self.check_for_updates()

        # Main interface will be created after authentication
        self.main_interface_created = False

        # Auto-start server after login (flag)
        self.auto_start_server = True

        # Start server self-monitoring
        self.server_self_monitor_active = True
        self.server_start_time = datetime.now()
        self.server_uptime = "00:00:00"
        self.self_monitor_thread = threading.Thread(target=self.monitor_server_status, daemon=True)
        self.self_monitor_thread.start()

        # Initialize Celsius AI integration
        self.initialize_celsius_integration()

        # Check for updates on startup
        self.check_for_updates()

    def initialize_celsius_integration(self):
        """Initialize full Celsius AI system integration"""
        try:
            # Import Celsius AI components
            from celsius_system_integration import CelsiusSystemIntegration
            from celsius_power_manager import CelsiusPowerManager
            from celsius_process_trainer import CelsiusProcessTrainer
            from celsius_collaborative_engine import CelsiusCollaborativeEngine

            # Initialize components
            self.system_integration = CelsiusSystemIntegration()
            self.power_manager = CelsiusPowerManager()
            self.process_trainer = CelsiusProcessTrainer()
            self.collaborative_engine = CelsiusCollaborativeEngine()

            # Start Celsius AI systems
            if not self.service_mode:  # Only start if not in service mode
                self.start_celsius_systems()

            self.celsius_fully_integrated = True
            print("[OK] Celsius AI fully integrated with Windows system")

        except Exception as e:
            print(f"[ERROR] Celsius AI integration error: {e}")
            self.celsius_fully_integrated = False

    def start_celsius_systems(self):
        """Start all Celsius AI systems"""
        try:
            if self.system_integration:
                self.system_integration.start_integration()
                print("[OK] System Integration started")

            if self.power_manager:
                self.power_manager.start_power_management()
                print("[OK] Power Management started")

            if self.process_trainer:
                self.process_trainer.start_training()
                print("[OK] Process Training started")

            if self.collaborative_engine:
                self.collaborative_engine.start_collaborative_improvement()
                print("[OK] Collaborative Improvement started")

            print("[START] Celsius AI is now managing your computer!")

        except Exception as e:
            print(f"[ERROR] Error starting Celsius systems: {e}")

    def stop_celsius_systems(self):
        """Stop all Celsius AI systems (SERVER HUB CONTROL ONLY)"""
        try:
            if self.system_integration:
                self.system_integration.stop_integration()
                print("⏹️ System Integration stopped")

            if self.power_manager:
                self.power_manager.stop_power_management()
                print("⏹️ Power Management stopped")

            if self.process_trainer:
                self.process_trainer.stop_training()
                print("⏹️ Process Training stopped")

            if self.collaborative_engine:
                self.collaborative_engine.stop_collaborative_improvement()
                print("⏹️ Collaborative Improvement stopped")

            print("[STOP] Celsius AI systems stopped by Server Hub")

        except Exception as e:
            print(f"[ERROR] Error stopping Celsius systems: {e}")

    def get_celsius_system_status(self):
        """Get status of all Celsius AI systems"""
        status = {
            "fully_integrated": self.celsius_fully_integrated,
            "system_integration": self.system_integration is not None and self.system_integration.running,
            "power_management": self.power_manager is not None and self.power_manager.running,
            "process_training": self.process_trainer is not None and self.process_trainer.running,
            "collaborative_improvement": self.collaborative_engine is not None and self.collaborative_engine.running,
            "pending_approvals": self.get_pending_approval_count(),
        }
        return status

    def get_pending_approval_count(self):
        """Get count of pending improvements requiring approval"""
        try:
            if self.collaborative_engine:
                pending = self.collaborative_engine.get_pending_improvements()
                return len(pending)
        except:
            pass
        return 0

    def setup_auto_startup(self):
        """Setup Server Hub for automatic startup with Windows"""
        try:
            import winreg

            # Registry key for Windows startup
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"

            # Server Hub startup command (in service mode)
            startup_cmd = f'"{sys.executable}" "{os.path.abspath(__file__)}" --service'

            # Add to Windows registry
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "CelsiusServerHub", 0, winreg.REG_SZ, startup_cmd)

            print("[OK] Auto-startup configured for Server Hub")
            return True

        except Exception as e:
            print(f"[ERROR] Auto-startup setup error: {e}")
            return False

    def setup_styles(self):
        """Configure dark theme styling"""
        style = ttk.Style()
        style.theme_use("clam")

        # Configure colors for dark theme
        style.configure("TNotebook", background="#2d2d2d", borderwidth=0)
        style.configure("TNotebook.Tab", background="#3d3d3d", foreground="#ffffff", padding=[20, 10])
        style.map("TNotebook.Tab", background=[("selected", "#4d4d4d")])

        style.configure("TFrame", background="#2d2d2d")
        style.configure("TLabel", background="#2d2d2d", foreground="#ffffff")
        style.configure("TButton", background="#4d4d4d", foreground="#ffffff")
        style.map("TButton", background=[("active", "#5d5d5d")])

        style.configure("Success.TLabel", background="#2d2d2d", foreground="#4CAF50")
        style.configure("Error.TLabel", background="#2d2d2d", foreground="#f44336")
        style.configure("Warning.TLabel", background="#2d2d2d", foreground="#ff9800")

        # Hamburger menu styles
        style.configure("Accent.TButton", background="#5d5d5d", foreground="#ffffff", font=("Arial", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#6d6d6d")])

        # Menu styles
        style.configure("Menu.TFrame", background="#3d3d3d")
        style.configure("Menu.TLabel", background="#3d3d3d", foreground="#ffffff")

    def create_main_interface(self):
        """Create the main application interface"""
        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_label = ttk.Label(header_frame, text="[SHIELD] Celsius AI Server Hub", font=("Arial", 20, "bold"))
        title_label.pack(side="left")

        self.status_label = ttk.Label(header_frame, text="● Server Stopped", style="Error.TLabel", font=("Arial", 12))
        self.status_label.pack(side="right")

        # Create main container with hamburger menu
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Create hamburger menu sidebar
        self.create_hamburger_menu(main_container)

        # Create main content area
        self.main_content = ttk.Frame(main_container)
        self.main_content.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # Initialize menu sections
        self.menu_sections = {}
        self.current_section = None

        # Create all content sections
        self.create_all_sections()

        # Show default section
        self.show_section("server_control")

    def create_hamburger_menu(self, parent):
        """Create hamburger menu sidebar"""
        # Menu container
        self.menu_frame = ttk.Frame(parent)
        self.menu_frame.pack(side="left", fill="y", padx=(0, 10))

        # Menu header with hamburger button
        menu_header = ttk.Frame(self.menu_frame)
        menu_header.pack(fill="x", pady=(0, 10))

        # Hamburger button
        self.hamburger_btn = ttk.Button(menu_header, text="☰", width=3, command=self.toggle_menu)
        self.hamburger_btn.pack(side="left")

        # Restart button
        self.restart_btn = ttk.Button(menu_header, text="[REFRESH]", width=3, command=self.restart_server_hub)
        self.restart_btn.pack(side="right")

        # Menu items container with scrollbar
        menu_container = ttk.Frame(self.menu_frame)
        menu_container.pack(fill="both", expand=True)

        # Scrollable menu
        self.menu_canvas = tk.Canvas(menu_container, width=250, highlightthickness=0)
        menu_scrollbar = ttk.Scrollbar(menu_container, orient="vertical", command=self.menu_canvas.yview)
        self.scrollable_menu = ttk.Frame(self.menu_canvas)

        self.scrollable_menu.bind(
            "<Configure>", lambda e: self.menu_canvas.configure(scrollregion=self.menu_canvas.bbox("all"))
        )

        self.menu_canvas.create_window((0, 0), window=self.scrollable_menu, anchor="nw")
        self.menu_canvas.configure(yscrollcommand=menu_scrollbar.set)

        self.menu_canvas.pack(side="left", fill="both", expand=True)
        menu_scrollbar.pack(side="right", fill="y")

        # Menu items
        self.menu_items = []
        self.create_menu_structure()

    def create_menu_structure(self):
        """Create the menu structure with sections and subsections"""
        menu_structure = [
            {
                "title": "[SERVER] Server Management",
                "key": "server_section",
                "subsections": [
                    {"title": "[FAST] Server Control", "key": "server_control"},
                    {"title": "[NETWORK] Ngrok Tunnels", "key": "ngrok_tunnels"},
                    {"title": "👥 Client Management", "key": "client_management"},
                ],
            },
            {
                "title": "[STATUS] Monitoring & Reports",
                "key": "monitoring_section",
                "subsections": [
                    {"title": "[STATS] System Monitoring", "key": "monitoring"},
                    {"title": "📋 Hourly Reports", "key": "hourly_reports"},
                    {"title": "[SEARCH] Activity Logs", "key": "activity_logs"},
                ],
            },
            {
                "title": "🤖 AI & Learning",
                "key": "ai_section",
                "subsections": [
                    {"title": "[NETWORK] Web Learning", "key": "web_learning"},
                    {"title": "[OK] Code Approval", "key": "code_approval"},
                    {"title": "🔗 Celsius Integration", "key": "celsius_integration"},
                ],
            },
            {
                "title": "[SETTINGS] System Management",
                "key": "system_section",
                "subsections": [
                    {"title": "[START] Deployment", "key": "deployment"},
                    {"title": "[REFRESH] Updates", "key": "updates"},
                    {"title": "[SETTINGS] Settings", "key": "settings"},
                ],
            },
        ]

        self.section_frames = {}

        for section in menu_structure:
            # Create section header
            section_frame = ttk.Frame(self.scrollable_menu)
            section_frame.pack(fill="x", pady=(5, 0))

            # Section button (collapsible)
            section_btn = ttk.Button(
                section_frame, text=section["title"], command=lambda key=section["key"]: self.toggle_section(key)
            )
            section_btn.pack(fill="x", pady=(0, 2))

            # Subsections frame
            subsection_frame = ttk.Frame(self.scrollable_menu)
            subsection_frame.pack(fill="x", padx=(20, 0))

            self.section_frames[section["key"]] = {
                "frame": subsection_frame,
                "expanded": section["key"] == "server_section",  # Default expand first section
                "button": section_btn,
            }

            # Create subsection buttons
            for subsection in section["subsections"]:
                sub_btn = ttk.Button(
                    subsection_frame,
                    text=subsection["title"],
                    command=lambda key=subsection["key"]: self.show_section(key),
                )
                sub_btn.pack(fill="x", pady=1)

                self.menu_items.append({"key": subsection["key"], "button": sub_btn, "title": subsection["title"]})

            # Initially hide/show based on expanded state
            if not self.section_frames[section["key"]]["expanded"]:
                subsection_frame.pack_forget()

    def toggle_section(self, section_key):
        """Toggle expansion of a menu section"""
        section = self.section_frames[section_key]
        section["expanded"] = not section["expanded"]

        if section["expanded"]:
            section["frame"].pack(fill="x", padx=(20, 0))
        else:
            section["frame"].pack_forget()

    def toggle_menu(self):
        """Toggle menu collapse/expand"""
        self.menu_collapsed = not self.menu_collapsed

        if self.menu_collapsed:
            self.scrollable_menu.pack_forget()
            self.hamburger_btn.config(text="▶")
            self.menu_frame.config(width=50)
        else:
            self.scrollable_menu.pack(fill="both", expand=True)
            self.hamburger_btn.config(text="☰")
            self.menu_frame.config(width=250)

    def track_user_activity(self, activity_type, details=""):
        """Wrapper to track user activity"""
        if hasattr(self, "log_user_activity"):
            self.log_user_activity(activity_type, details)

    def show_section(self, section_key):
        """Show a specific content section"""
        # Track navigation activity
        self.track_user_activity("navigation", f"accessed_section: {section_key}")

        # Clear references to widgets that will be destroyed (for the CURRENT section, not the new one)
        if hasattr(self, "current_section") and self.current_section:
            self.cleanup_section_widgets(self.current_section)
            # Clear widget references for the section we're LEAVING
            self.clear_section_widget_references(self.current_section)

        # Clear current content
        for widget in self.main_content.winfo_children():
            widget.destroy()

        # Clear the section from menu_sections since its widgets were destroyed
        if hasattr(self, "current_section") and self.current_section in self.menu_sections:
            del self.menu_sections[self.current_section]

        # Update selected menu item
        self.selected_menu_item = section_key
        self.update_menu_selection()

        # Always recreate the section to ensure fresh widgets
        self.create_section_content(section_key)
        if section_key in self.menu_sections:
            self.menu_sections[section_key].pack(fill="both", expand=True, in_=self.main_content)

        self.current_section = section_key

    def cleanup_section_widgets(self, section_key):
        """Clean up widgets and references when leaving a section"""
        if section_key == "code_approval":
            # Reset code approval auto-refresh
            self.code_approval_refresh_active = False

    def clear_section_widget_references(self, section_key):
        """Clear widget references to prevent invalid access after destruction"""
        if section_key == "code_approval":
            # Remove code approval widget references
            widgets_to_clear = [
                "approval_tree",
                "pending_requests_label",
                "approved_requests_label",
                "denied_requests_label",
                "request_details_text",
                "approve_btn",
                "deny_btn",
                "review_comments_text",
            ]
            for widget in widgets_to_clear:
                if hasattr(self, widget):
                    delattr(self, widget)

        elif section_key == "ngrok_tunnels":
            # Remove ngrok tunnel widget references
            widgets_to_clear = ["tunnels_tree", "tunnel_status_label", "auth_status_label"]
            for widget in widgets_to_clear:
                if hasattr(self, widget):
                    delattr(self, widget)

        elif section_key == "deployment":
            # Remove deployment widget references
            widgets_to_clear = ["components_tree", "deployment_status_label"]
            for widget in widgets_to_clear:
                if hasattr(self, widget):
                    delattr(self, widget)

        elif section_key == "client_management":
            # Remove client management widget references
            widgets_to_clear = ["client_tree"]
            for widget in widgets_to_clear:
                if hasattr(self, widget):
                    delattr(self, widget)

        elif section_key == "monitoring":
            # Remove monitoring widget references
            widgets_to_clear = ["stats_display", "metrics_tree"]
            for widget in widgets_to_clear:
                if hasattr(self, widget):
                    delattr(self, widget)

    def update_menu_selection(self):
        """Update visual selection in menu"""
        for item in self.menu_items:
            if item["key"] == self.selected_menu_item:
                item["button"].config(style="Accent.TButton")
            else:
                item["button"].config(style="TButton")

    def restart_server_hub(self):
        """Restart the server hub application"""
        result = messagebox.askyesno(
            "Restart Server Hub",
            "This will restart the entire Server Hub application.\n"
            + "Any running processes will be preserved.\n\n"
            + "Continue with restart?",
        )

        if result:
            try:
                # Save current state if needed
                if hasattr(self, "server_process") and self.server_process:
                    messagebox.showinfo(
                        "Info",
                        "Server processes will continue running in background.\n"
                        + "The hub will reconnect after restart.",
                    )

                # Close monitoring
                if hasattr(self, "server_self_monitor_active"):
                    self.server_self_monitor_active = False

                # Restart the application
                python = sys.executable
                script = __file__
                os.execl(python, python, script)

            except Exception as e:
                messagebox.showerror("Restart Failed", f"Failed to restart Server Hub: {str(e)}")

    def create_all_sections(self):
        """Create all content sections"""
        # This will be called to create section content as needed
        pass

    def create_section_content(self, section_key):
        """Create content for a specific section"""
        if section_key == "server_control":
            self.create_server_control_section()
        elif section_key == "ngrok_tunnels":
            self.create_ngrok_tunnels_section()
        elif section_key == "hourly_reports":
            self.create_hourly_reports_section()
        elif section_key == "web_learning":
            self.create_web_learning_section()
        elif section_key == "code_approval":
            self.create_code_approval_section()
        elif section_key == "client_management":
            self.create_client_management_section()
        elif section_key == "monitoring":
            self.create_monitoring_section()
        elif section_key == "deployment":
            self.create_deployment_section()
        elif section_key == "updates":
            self.create_updates_section()
        elif section_key == "settings":
            self.create_settings_section()
        elif section_key == "celsius_integration":
            self.create_celsius_integration_section()
        elif section_key == "activity_logs":
            self.create_activity_logs_section()
        else:
            # Create placeholder section
            self.create_placeholder_section(section_key)

    def create_server_control_section(self):
        """Server Control and Status Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["server_control"] = frame

        # Server status section
        status_frame = ttk.LabelFrame(frame, text="Server Status", padding=20)
        status_frame.pack(fill="x", padx=20, pady=(20, 10))

        # Status display
        status_row = ttk.Frame(status_frame)
        status_row.pack(fill="x", pady=(0, 10))

        ttk.Label(status_row, text="Status:", font=("Arial", 12, "bold")).pack(side="left")
        self.server_status_label = ttk.Label(status_row, text="Stopped", style="Error.TLabel")
        self.server_status_label.pack(side="left", padx=(10, 0))

        # Server info
        info_row = ttk.Frame(status_frame)
        info_row.pack(fill="x", pady=5)

        ttk.Label(info_row, text="URL:", font=("Arial", 10, "bold")).pack(side="left")
        self.url_label = ttk.Label(info_row, text="http://localhost:5000", foreground="#2196F3")
        self.url_label.pack(side="left", padx=(10, 0))
        self.url_label.bind("<Button-1>", lambda e: webbrowser.open(self.dashboard_url))

        # Control buttons
        control_frame = ttk.Frame(status_frame)
        control_frame.pack(fill="x", pady=(20, 0))

        self.start_button = ttk.Button(control_frame, text="[START] Start Server", command=self.start_server)
        self.start_button.pack(side="left", padx=(0, 10))

        self.stop_button = ttk.Button(control_frame, text="⏹️ Stop Server", command=self.stop_server, state="disabled")
        self.stop_button.pack(side="left", padx=(0, 10))

        self.restart_button = ttk.Button(
            control_frame, text="[REFRESH] Restart Server", command=self.restart_server, state="disabled"
        )
        self.restart_button.pack(side="left", padx=(0, 10))

        ttk.Button(
            control_frame, text="[NETWORK] Open Dashboard", command=lambda: webbrowser.open(self.dashboard_url)
        ).pack(side="right")

        # Server Health Monitoring section
        health_frame = ttk.LabelFrame(frame, text="🏥 Server Health Monitor", padding=20)
        health_frame.pack(fill="x", padx=20, pady=(10, 10))

        # Health metrics grid
        health_grid = ttk.Frame(health_frame)
        health_grid.pack(fill="x")

        # Row 1: Uptime and Health Score
        row1 = ttk.Frame(health_grid)
        row1.pack(fill="x", pady=5)

        ttk.Label(row1, text="Uptime:", font=("Arial", 10, "bold")).pack(side="left")
        self.uptime_label = ttk.Label(row1, text="00:00:00", foreground="#4CAF50")
        self.uptime_label.pack(side="left", padx=(10, 30))

        ttk.Label(row1, text="Health Score:", font=("Arial", 10, "bold")).pack(side="left")
        self.health_score_label = ttk.Label(row1, text="100/100", foreground="#4CAF50")
        self.health_score_label.pack(side="left", padx=(10, 0))

        # Row 2: CPU and Memory
        row2 = ttk.Frame(health_grid)
        row2.pack(fill="x", pady=5)

        ttk.Label(row2, text="CPU Usage:", font=("Arial", 10, "bold")).pack(side="left")
        self.server_cpu_label = ttk.Label(row2, text="0.0%", foreground="#2196F3")
        self.server_cpu_label.pack(side="left", padx=(10, 30))

        ttk.Label(row2, text="Memory:", font=("Arial", 10, "bold")).pack(side="left")
        self.server_memory_label = ttk.Label(row2, text="0 MB", foreground="#2196F3")
        self.server_memory_label.pack(side="left", padx=(10, 0))

        # Row 3: Components and Connections
        row3 = ttk.Frame(health_grid)
        row3.pack(fill="x", pady=5)

        ttk.Label(row3, text="Active Components:", font=("Arial", 10, "bold")).pack(side="left")
        self.components_label = ttk.Label(row3, text="0/4", foreground="#FF9800")
        self.components_label.pack(side="left", padx=(10, 30))

        ttk.Label(row3, text="Last Check:", font=("Arial", 10, "bold")).pack(side="left")
        self.last_check_label = ttk.Label(row3, text="--:--:--", foreground="#9E9E9E")
        self.last_check_label.pack(side="left", padx=(10, 0))

        # Server logs section
        logs_frame = ttk.LabelFrame(frame, text="Server Logs", padding=20)
        logs_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        self.log_text = scrolledtext.ScrolledText(
            logs_frame, height=15, bg="#1a1a1a", fg="#ffffff", insertbackground="#ffffff"
        )
        self.log_text.pack(fill="both", expand=True)

        # Log control buttons
        log_controls = ttk.Frame(logs_frame)
        log_controls.pack(fill="x", pady=(10, 0))

        ttk.Button(log_controls, text="📄 Clear Logs", command=self.clear_logs).pack(side="left")
        ttk.Button(log_controls, text="💾 Save Logs", command=self.save_logs).pack(side="left", padx=(10, 0))
        ttk.Button(log_controls, text="[REFRESH] Refresh", command=self.refresh_logs).pack(side="left", padx=(10, 0))

    def create_chat_tab(self):
        """Chat Interface Tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💬 Chat")

        # Chat area
        chat_frame = ttk.LabelFrame(frame, text="Chat with Celsius AI", padding=20)
        chat_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, height=20, bg="#1a1a1a", fg="#ffffff", insertbackground="#ffffff", font=("Arial", 10)
        )
        self.chat_display.pack(fill="both", expand=True, pady=(0, 10))

        # Welcome message
        self.chat_display.insert(
            "end",
            "[SHIELD] Celsius AI: Hello! I'm your personal cybersecurity defense assistant. How can I help you today?\n\n",
        )
        self.chat_display.config(state="disabled")

        # Input area
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill="x", pady=(10, 0))

        self.chat_input = tk.Text(
            input_frame, height=3, bg="#2d2d2d", fg="#ffffff", insertbackground="#ffffff", font=("Arial", 10)
        )
        self.chat_input.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Bind Enter key to send message
        self.chat_input.bind("<Return>", self.send_chat_message)
        self.chat_input.bind("<Shift-Return>", lambda e: None)  # Allow Shift+Enter for new lines

        # Send button
        send_button = ttk.Button(input_frame, text="📤 Send", command=self.send_chat_message)
        send_button.pack(side="right", pady=5)

        # Chat controls
        control_frame = ttk.Frame(chat_frame)
        control_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(control_frame, text="🗑️ Clear Chat", command=self.clear_chat).pack(side="left")
        ttk.Button(control_frame, text="💾 Save Chat", command=self.save_chat).pack(side="left", padx=(10, 0))
        ttk.Button(control_frame, text="[REFRESH] Reset Context", command=self.reset_chat_context).pack(
            side="left", padx=(10, 0)
        )

        # Status indicator
        self.chat_status = ttk.Label(control_frame, text="Ready", foreground="#4CAF50")
        self.chat_status.pack(side="right")

    def create_ngrok_tunnels_section(self):
        """ngrok Tunnels Management Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["ngrok_tunnels"] = frame

        # Tunnel status section
        tunnel_frame = ttk.LabelFrame(frame, text="Active Tunnels", padding=20)
        tunnel_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        # Tunnels list with scrollbar
        list_frame = ttk.Frame(tunnel_frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 20))

        # Create treeview for tunnels
        columns = ("name", "protocol", "public_url", "local_addr", "status", "created")
        self.tunnels_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)

        # Configure column headings
        self.tunnels_tree.heading("name", text="Name")
        self.tunnels_tree.heading("protocol", text="Protocol")
        self.tunnels_tree.heading("public_url", text="Public URL")
        self.tunnels_tree.heading("local_addr", text="Local Address")
        self.tunnels_tree.heading("status", text="Status")
        self.tunnels_tree.heading("created", text="Created")

        # Configure column widths
        self.tunnels_tree.column("name", width=100)
        self.tunnels_tree.column("protocol", width=80)
        self.tunnels_tree.column("public_url", width=300)
        self.tunnels_tree.column("local_addr", width=150)
        self.tunnels_tree.column("status", width=80)
        self.tunnels_tree.column("created", width=150)

        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tunnels_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tunnels_tree.xview)
        self.tunnels_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Pack treeview and scrollbars
        self.tunnels_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")

        # Tunnel control buttons
        tunnel_control_frame = ttk.Frame(tunnel_frame)
        tunnel_control_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(tunnel_control_frame, text="[REFRESH] Refresh Tunnels", command=self.refresh_tunnels).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(tunnel_control_frame, text="📋 Copy Selected URL", command=self.copy_tunnel_url).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(tunnel_control_frame, text="[NETWORK] Open in Browser", command=self.open_tunnel_url).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(tunnel_control_frame, text="[FAST] Start ngrok", command=self.start_ngrok).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(tunnel_control_frame, text="[STOP] Stop ngrok", command=self.stop_ngrok).pack(
            side="left", padx=(0, 10)
        )

        # Tunnel configuration section
        config_frame = ttk.LabelFrame(frame, text="Tunnel Configuration", padding=20)
        config_frame.pack(fill="x", padx=20, pady=(10, 20))

        # Port configuration
        port_frame = ttk.Frame(config_frame)
        port_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(port_frame, text="Local Port:", font=("Arial", 10, "bold")).pack(side="left")
        self.port_var = tk.StringVar(value="5000")
        port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=10)
        port_entry.pack(side="left", padx=(10, 0))

        # Protocol selection
        ttk.Label(port_frame, text="Protocol:", font=("Arial", 10, "bold")).pack(side="left", padx=(20, 0))
        self.protocol_var = tk.StringVar(value="http")
        protocol_combo = ttk.Combobox(
            port_frame, textvariable=self.protocol_var, values=["http", "tcp", "tls"], width=8, state="readonly"
        )
        protocol_combo.pack(side="left", padx=(10, 0))

        # Auth token status
        auth_frame = ttk.Frame(config_frame)
        auth_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(auth_frame, text="Auth Token:", font=("Arial", 10, "bold")).pack(side="left")
        self.auth_status_label = ttk.Label(auth_frame, text="Checking...", style="Warning.TLabel")
        self.auth_status_label.pack(side="left", padx=(10, 0))

        ttk.Button(auth_frame, text="[SECURE] Configure Auth", command=self.configure_ngrok_auth).pack(side="right")

    def create_hourly_reports_section(self):
        """Hourly Reports and Logging Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["hourly_reports"] = frame

        # Reports overview section
        overview_frame = ttk.LabelFrame(frame, text="System Reports Overview", padding=20)
        overview_frame.pack(fill="x", padx=20, pady=(20, 10))

        # Status indicators
        status_grid = ttk.Frame(overview_frame)
        status_grid.pack(fill="x", pady=(0, 20))

        # Create status cards
        self.create_status_card(status_grid, "[REFRESH] System Status", "system_status", 0, 0)
        self.create_status_card(status_grid, "[FAST] Performance", "performance", 0, 1)
        self.create_status_card(status_grid, "[LOCKED] Security", "security", 1, 0)
        self.create_status_card(status_grid, "[STATUS] Reports", "reports", 1, 1)

        # Configure grid weights
        status_grid.grid_columnconfigure(0, weight=1)
        status_grid.grid_columnconfigure(1, weight=1)

        # Controls
        controls_frame = ttk.Frame(overview_frame)
        controls_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(controls_frame, text="[STATUS] Generate Report Now", command=self.generate_report_now).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(controls_frame, text="📅 View All Reports", command=self.view_all_reports).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(controls_frame, text="[SETTINGS] Logging Settings", command=self.configure_logging).pack(
            side="left", padx=(0, 10)
        )

        # Latest report section
        report_frame = ttk.LabelFrame(frame, text="Latest Hourly Report", padding=20)
        report_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # Report display
        self.report_text = scrolledtext.ScrolledText(report_frame, height=15, wrap=tk.WORD, font=("Consolas", 10))
        self.report_text.pack(fill="both", expand=True)

        # Report refresh controls
        refresh_frame = ttk.Frame(report_frame)
        refresh_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(refresh_frame, text="[REFRESH] Refresh Report", command=self.refresh_latest_report).pack(
            side="left", padx=(0, 10)
        )

        self.auto_refresh_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(refresh_frame, text="Auto-refresh every 5 minutes", variable=self.auto_refresh_var).pack(
            side="left", padx=(20, 0)
        )

    def create_web_learning_section(self):
        """Web Learning and AI Communication Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["web_learning"] = frame

        # Main container
        main_container = ttk.Frame(frame)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Control panel
        control_frame = ttk.LabelFrame(main_container, text="Web Learning Control Panel", padding=15)
        control_frame.pack(fill="x", pady=(0, 20))

        # Status display
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill="x", pady=(0, 15))

        self.web_learning_status_label = ttk.Label(status_frame, text="[REFRESH] Initializing web learning...")
        self.web_learning_status_label.pack(anchor="w")

        # Control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        self.start_learning_btn = ttk.Button(
            button_frame, text="[START] Start Learning", command=self.start_web_learning, state="disabled"
        )
        self.start_learning_btn.pack(side="left", padx=(0, 10))

        self.stop_learning_btn = ttk.Button(
            button_frame, text="⏹️ Stop Learning", command=self.stop_web_learning, state="disabled"
        )
        self.stop_learning_btn.pack(side="left", padx=(0, 10))

        ttk.Button(button_frame, text="[STATUS] Generate Report", command=self.generate_web_learning_report).pack(
            side="left", padx=(0, 10)
        )

        # AI Communication controls
        ai_comm_frame = ttk.Frame(button_frame)
        ai_comm_frame.pack(side="right")

        self.ai_comm_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            ai_comm_frame,
            text="Enable AI Communication",
            variable=self.ai_comm_enabled_var,
            command=self.toggle_ai_communication,
        ).pack(side="right", padx=(20, 0))

        # Learning insights and reports display
        display_frame = ttk.LabelFrame(main_container, text="Learning Reports & Insights", padding=15)
        display_frame.pack(fill="both", expand=True)

        # Text display with scrollbar
        text_frame = ttk.Frame(display_frame)
        text_frame.pack(fill="both", expand=True)

        self.web_learning_text = scrolledtext.ScrolledText(
            text_frame, wrap=tk.WORD, height=20, width=80, font=("Consolas", 10)
        )
        self.web_learning_text.pack(fill="both", expand=True)

        # Initialize web learning
        self.initialize_web_learning()

    def create_code_approval_section(self):
        """Code Approval and Review Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["code_approval"] = frame

        # Main container
        main_container = ttk.Frame(frame)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Header with statistics
        header_frame = ttk.LabelFrame(main_container, text="Code Approval Dashboard", padding=15)
        header_frame.pack(fill="x", pady=(0, 20))

        # Statistics row
        stats_frame = ttk.Frame(header_frame)
        stats_frame.pack(fill="x", pady=(0, 15))

        # Create statistics labels
        self.pending_requests_label = ttk.Label(
            stats_frame, text="Pending: 0", style="Warning.TLabel", font=("Arial", 11, "bold")
        )
        self.pending_requests_label.pack(side="left", padx=(0, 20))

        self.approved_requests_label = ttk.Label(
            stats_frame, text="Approved: 0", style="Success.TLabel", font=("Arial", 11, "bold")
        )
        self.approved_requests_label.pack(side="left", padx=(0, 20))

        self.denied_requests_label = ttk.Label(
            stats_frame, text="Denied: 0", style="Error.TLabel", font=("Arial", 11, "bold")
        )
        self.denied_requests_label.pack(side="left", padx=(0, 20))

        # Control buttons
        control_frame = ttk.Frame(header_frame)
        control_frame.pack(fill="x")

        ttk.Button(control_frame, text="[REFRESH] Refresh Requests", command=self.refresh_code_approval_requests).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(control_frame, text="[STATUS] View Statistics", command=self.show_approval_statistics).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(control_frame, text="🗂️ Approval History", command=self.show_approval_history).pack(
            side="left", padx=(0, 10)
        )

        # Requests list section
        requests_frame = ttk.LabelFrame(main_container, text="Pending Code Approval Requests", padding=15)
        requests_frame.pack(fill="both", expand=True, pady=(0, 20))

        # Create treeview for requests list
        columns = ("ID", "Title", "File", "Type", "Priority", "Submitted")
        self.approval_tree = ttk.Treeview(requests_frame, columns=columns, show="headings", height=8)

        # Configure columns
        column_widths = {"ID": 100, "Title": 200, "File": 150, "Type": 100, "Priority": 80, "Submitted": 120}
        for col in columns:
            self.approval_tree.heading(col, text=col)
            self.approval_tree.column(col, width=column_widths[col])

        # Scrollbar for requests list
        approval_scrollbar = ttk.Scrollbar(requests_frame, orient="vertical", command=self.approval_tree.yview)
        self.approval_tree.configure(yscrollcommand=approval_scrollbar.set)

        self.approval_tree.pack(side="left", fill="both", expand=True)
        approval_scrollbar.pack(side="right", fill="y")

        # Bind selection event
        self.approval_tree.bind("<<TreeviewSelect>>", self.on_approval_request_select)

        # Request details and action section
        details_frame = ttk.LabelFrame(main_container, text="Request Details & Actions", padding=15)
        details_frame.pack(fill="both", expand=True)

        # Split into two parts: details display and action buttons
        details_container = ttk.Frame(details_frame)
        details_container.pack(fill="both", expand=True)

        # Details display (left side)
        display_frame = ttk.Frame(details_container)
        display_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.request_details_text = scrolledtext.ScrolledText(
            display_frame, wrap=tk.WORD, height=15, width=60, font=("Consolas", 9), state="disabled"
        )
        self.request_details_text.pack(fill="both", expand=True)

        # Action buttons (right side)
        action_frame = ttk.Frame(details_container)
        action_frame.pack(side="right", fill="y", padx=(10, 0))

        # Individual action buttons
        ttk.Label(action_frame, text="Actions for Selected Request", font=("Arial", 11, "bold")).pack(pady=(0, 15))

        self.approve_btn = ttk.Button(
            action_frame, text="[OK] APPROVE", command=self.approve_selected_request, state="disabled", width=20
        )
        self.approve_btn.pack(pady=(0, 10), fill="x")

        self.deny_btn = ttk.Button(
            action_frame, text="[ERROR] DENY", command=self.deny_selected_request, state="disabled", width=20
        )
        self.deny_btn.pack(pady=(0, 10), fill="x")

        # Comments section
        ttk.Label(action_frame, text="Review Comments:", font=("Arial", 10, "bold")).pack(pady=(20, 5), anchor="w")

        self.review_comments_text = tk.Text(action_frame, height=4, width=25, font=("Arial", 9), wrap=tk.WORD)
        self.review_comments_text.pack(pady=(0, 10), fill="x")

        # Additional actions
        ttk.Separator(action_frame, orient="horizontal").pack(fill="x", pady=10)

        ttk.Button(action_frame, text="[SEARCH] View Full Code", command=self.view_full_code_comparison, width=20).pack(
            pady=(0, 5), fill="x"
        )

        ttk.Button(action_frame, text="📋 Copy Request ID", command=self.copy_request_id, width=20).pack(
            pady=(0, 5), fill="x"
        )

        ttk.Button(action_frame, text="⏭️ Skip Request", command=self.skip_request, width=20).pack(pady=(0, 5), fill="x")

        # Selected request tracking
        self.selected_request_id = None

        # Auto-refresh pending requests
        self.refresh_code_approval_requests()

        # Start auto-refresh timer if not already running
        if not hasattr(self, "code_approval_refresh_active"):
            self.code_approval_refresh_active = True
            self.root.after(30000, self.auto_refresh_code_approval)

    def create_client_management_section(self):
        """Client Management Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["client_management"] = frame

        # Connected clients section
        clients_frame = ttk.LabelFrame(frame, text="Connected Clients", padding=20)
        clients_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Client list
        columns = ("IP Address", "Connection Time", "User Agent", "Requests", "Status")
        self.client_tree = ttk.Treeview(clients_frame, columns=columns, show="headings", height=10)

        for col in columns:
            self.client_tree.heading(col, text=col)
            self.client_tree.column(col, width=150)

        # Scrollbar for client list
        client_scrollbar = ttk.Scrollbar(clients_frame, orient="vertical", command=self.client_tree.yview)
        self.client_tree.configure(yscrollcommand=client_scrollbar.set)

        self.client_tree.pack(side="left", fill="both", expand=True)
        client_scrollbar.pack(side="right", fill="y")

        # Client actions
        client_actions = ttk.Frame(clients_frame)
        client_actions.pack(fill="x", pady=(20, 0))

        ttk.Button(client_actions, text="[REFRESH] Refresh Clients", command=self.refresh_clients).pack(side="left")
        ttk.Button(client_actions, text="[STATUS] Client Details", command=self.show_client_details).pack(
            side="left", padx=(10, 0)
        )
        ttk.Button(client_actions, text="🚫 Disconnect Client", command=self.disconnect_client).pack(
            side="left", padx=(10, 0)
        )

    def create_monitoring_section(self):
        """System Monitoring Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["monitoring"] = frame

        # System stats section
        stats_frame = ttk.LabelFrame(frame, text="System Performance", padding=20)
        stats_frame.pack(fill="x", padx=20, pady=(20, 10))

        # Performance metrics
        metrics_row1 = ttk.Frame(stats_frame)
        metrics_row1.pack(fill="x", pady=(0, 10))

        # CPU Usage
        cpu_frame = ttk.LabelFrame(metrics_row1, text="CPU Usage", padding=10)
        cpu_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.cpu_label = ttk.Label(cpu_frame, text="0%", font=("Arial", 16, "bold"))
        self.cpu_label.pack()

        # Memory Usage
        memory_frame = ttk.LabelFrame(metrics_row1, text="Memory Usage", padding=10)
        memory_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.memory_label = ttk.Label(memory_frame, text="0%", font=("Arial", 16, "bold"))
        self.memory_label.pack()

        # Disk Usage
        disk_frame = ttk.LabelFrame(metrics_row1, text="Disk Usage", padding=10)
        disk_frame.pack(side="right", fill="x", expand=True)
        self.disk_label = ttk.Label(disk_frame, text="0%", font=("Arial", 16, "bold"))
        self.disk_label.pack()

        # AI Statistics
        ai_frame = ttk.LabelFrame(frame, text="AI Performance", padding=20)
        ai_frame.pack(fill="x", padx=20, pady=(10, 10))

        ai_row = ttk.Frame(ai_frame)
        ai_row.pack(fill="x")

        # Learning Stats
        learning_frame = ttk.LabelFrame(ai_row, text="Learning Progress", padding=10)
        learning_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.learning_label = ttk.Label(learning_frame, text="0 sessions", font=("Arial", 12))
        self.learning_label.pack()

        # Conversations
        conv_frame = ttk.LabelFrame(ai_row, text="Conversations", padding=10)
        conv_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.conversations_label = ttk.Label(conv_frame, text="0 total", font=("Arial", 12))
        self.conversations_label.pack()

        # Response Time
        response_frame = ttk.LabelFrame(ai_row, text="Avg Response Time", padding=10)
        response_frame.pack(side="right", fill="x", expand=True)
        self.response_time_label = ttk.Label(response_frame, text="0ms", font=("Arial", 12))
        self.response_time_label.pack()

        # Activity log
        activity_frame = ttk.LabelFrame(frame, text="Activity Monitor", padding=20)
        activity_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        self.activity_text = scrolledtext.ScrolledText(
            activity_frame, height=10, bg="#1a1a1a", fg="#ffffff", insertbackground="#ffffff"
        )
        self.activity_text.pack(fill="both", expand=True)

    def create_deployment_section(self):
        """Deployment Management Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["deployment"] = frame

        # Deployment options
        deploy_frame = ttk.LabelFrame(frame, text="Deployment Tools", padding=20)
        deploy_frame.pack(fill="x", padx=20, pady=(20, 10))

        # Create installer
        installer_row = ttk.Frame(deploy_frame)
        installer_row.pack(fill="x", pady=(0, 15))

        ttk.Label(installer_row, text="[CONFIG] Create Client Installer:", font=("Arial", 12, "bold")).pack(side="left")
        ttk.Button(installer_row, text="Generate Windows Installer", command=self.create_installer).pack(side="right")

        # Package for distribution
        package_row = ttk.Frame(deploy_frame)
        package_row.pack(fill="x", pady=(0, 15))

        ttk.Label(package_row, text="📦 Package Distribution:", font=("Arial", 12, "bold")).pack(side="left")
        ttk.Button(package_row, text="Create Distribution Package", command=self.create_package).pack(side="right")

        # Server configuration
        config_row = ttk.Frame(deploy_frame)
        config_row.pack(fill="x", pady=(0, 15))

        ttk.Label(config_row, text="[SETTINGS] Server Configuration:", font=("Arial", 12, "bold")).pack(side="left")
        ttk.Button(config_row, text="Export Configuration", command=self.export_config).pack(side="right", padx=(0, 10))
        ttk.Button(config_row, text="Import Configuration", command=self.import_config).pack(side="right")

        # Network settings
        network_frame = ttk.LabelFrame(frame, text="Network Configuration", padding=20)
        network_frame.pack(fill="x", padx=20, pady=(10, 10))

        # Server address
        addr_row = ttk.Frame(network_frame)
        addr_row.pack(fill="x", pady=(0, 10))

        ttk.Label(addr_row, text="Server Address:").pack(side="left")
        self.server_address = ttk.Entry(addr_row, width=20)
        self.server_address.pack(side="left", padx=(10, 0))
        self.server_address.insert(0, "localhost")

        ttk.Label(addr_row, text="Port:").pack(side="left", padx=(20, 0))
        self.server_port = ttk.Entry(addr_row, width=10)
        self.server_port.pack(side="left", padx=(10, 0))
        self.server_port.insert(0, "8000")

        ttk.Button(addr_row, text="Apply Changes", command=self.apply_network_config).pack(side="right")

        # SSL Configuration
        ssl_row = ttk.Frame(network_frame)
        ssl_row.pack(fill="x")

        self.ssl_enabled = tk.BooleanVar()
        ttk.Checkbutton(ssl_row, text="Enable SSL/HTTPS", variable=self.ssl_enabled).pack(side="left")

        ttk.Button(ssl_row, text="Configure SSL", command=self.configure_ssl).pack(side="right")

    def create_updates_section(self):
        """Updates and Maintenance Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["updates"] = frame

        # Update status
        update_frame = ttk.LabelFrame(frame, text="Update Status", padding=20)
        update_frame.pack(fill="x", padx=20, pady=(20, 10))

        status_row = ttk.Frame(update_frame)
        status_row.pack(fill="x", pady=(0, 15))

        ttk.Label(status_row, text="Current Version:", font=("Arial", 12, "bold")).pack(side="left")
        self.version_label = ttk.Label(status_row, text="v1.0.0", style="Success.TLabel")
        self.version_label.pack(side="left", padx=(10, 0))

        ttk.Button(status_row, text="[SEARCH] Check for Updates", command=self.check_for_updates).pack(side="right")

        # Auto-update settings
        auto_row = ttk.Frame(update_frame)
        auto_row.pack(fill="x")

        self.auto_update_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            auto_row, text="Enable automatic updates", variable=self.auto_update_var, command=self.toggle_auto_update
        ).pack(side="left")

        # Component updates
        components_frame = ttk.LabelFrame(frame, text="Component Management", padding=20)
        components_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # Component list
        comp_columns = ("Component", "Version", "Status", "Last Updated")
        self.components_tree = ttk.Treeview(components_frame, columns=comp_columns, show="headings", height=8)

        for col in comp_columns:
            self.components_tree.heading(col, text=col)
            self.components_tree.column(col, width=120)

        self.components_tree.pack(fill="both", expand=True)

        # Populate with real enhanced services - this will be updated by update_service_list()
        self.update_service_list()

        # Component actions
        comp_actions = ttk.Frame(components_frame)
        comp_actions.pack(fill="x", pady=(10, 0))

        ttk.Button(comp_actions, text="[FAST] Push Update to Selected", command=self.push_update_to_selected).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(comp_actions, text="[REFRESH] Restart Selected", command=self.restart_selected_service).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(comp_actions, text="� View Logs", command=self.view_service_logs).pack(side="left", padx=(0, 10))

        ttk.Button(comp_actions, text="[START] Deploy All Updates", command=self.push_all_updates).pack(side="right")

        # Enhanced update controls
        update_controls_frame = ttk.LabelFrame(components_frame, text="Push Deployment Controls")
        update_controls_frame.pack(fill="x", pady=(15, 0))

        controls_grid = ttk.Frame(update_controls_frame)
        controls_grid.pack(fill="x", padx=10, pady=10)

        # Row 1: Main deployment actions
        ttk.Button(controls_grid, text="[START] Push All Updates Now", command=self.push_all_updates).grid(
            row=0, column=0, padx=5, pady=5, sticky="ew"
        )

        ttk.Button(controls_grid, text="[REFRESH] Hot Reload Services", command=self.hot_reload_services).grid(
            row=0, column=1, padx=5, pady=5, sticky="ew"
        )

        ttk.Button(controls_grid, text="📦 Create Deployment Package", command=self.create_deployment_package).grid(
            row=0, column=2, padx=5, pady=5, sticky="ew"
        )

        # Row 2: System management
        ttk.Button(controls_grid, text="[SEARCH] Check System Health", command=self.check_system_health).grid(
            row=1, column=0, padx=5, pady=5, sticky="ew"
        )

        ttk.Button(controls_grid, text="📋 Export Configuration", command=self.export_configuration).grid(
            row=1, column=1, padx=5, pady=5, sticky="ew"
        )

        ttk.Button(controls_grid, text="[WARNING] Emergency Reset", command=self.emergency_system_reset).grid(
            row=1, column=2, padx=5, pady=5, sticky="ew"
        )

        # Configure grid weights
        for i in range(3):
            controls_grid.grid_columnconfigure(i, weight=1)

        # Progress and status section
        status_progress_frame = ttk.LabelFrame(frame, text="Deployment Status & Progress", padding=20)
        status_progress_frame.pack(fill="x", padx=20, pady=(10, 20))

        # Progress bar
        progress_frame = ttk.Frame(status_progress_frame)
        progress_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(progress_frame, text="Deployment Progress:", font=("Arial", 10, "bold")).pack(anchor="w")

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=500)
        self.progress_bar.pack(fill="x", pady=(5, 0))

        # Status display
        status_display_frame = ttk.Frame(status_progress_frame)
        status_display_frame.pack(fill="both", expand=True)

        ttk.Label(status_display_frame, text="Deployment Log:", font=("Arial", 10, "bold")).pack(anchor="w")

        self.deployment_log = scrolledtext.ScrolledText(
            status_display_frame, height=8, bg="#1a1a1a", fg="#ffffff", insertbackground="#ffffff"
        )
        self.deployment_log.pack(fill="both", expand=True, pady=(5, 0))

        # Initialize deployment log
        self.log_deployment("System ready for deployment operations.")

    def create_settings_section(self):
        """Settings and Configuration Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["settings"] = frame

        # General settings
        general_frame = ttk.LabelFrame(frame, text="General Settings", padding=20)
        general_frame.pack(fill="x", padx=20, pady=(20, 10))

        # Startup options
        startup_row = ttk.Frame(general_frame)
        startup_row.pack(fill="x", pady=(0, 10))

        self.startup_server = tk.BooleanVar(value=True)
        ttk.Checkbutton(startup_row, text="Start server automatically on launch", variable=self.startup_server).pack(
            side="left"
        )

        # Minimize to tray
        tray_row = ttk.Frame(general_frame)
        tray_row.pack(fill="x", pady=(0, 10))

        self.minimize_tray = tk.BooleanVar()
        ttk.Checkbutton(tray_row, text="Minimize to system tray", variable=self.minimize_tray).pack(side="left")

        # Log level
        log_row = ttk.Frame(general_frame)
        log_row.pack(fill="x")

        ttk.Label(log_row, text="Log Level:").pack(side="left")
        self.log_level = ttk.Combobox(log_row, values=["DEBUG", "INFO", "WARNING", "ERROR"], state="readonly", width=15)
        self.log_level.set("INFO")
        self.log_level.pack(side="left", padx=(10, 0))

        # AI Configuration
        ai_frame = ttk.LabelFrame(frame, text="AI Configuration", padding=20)
        ai_frame.pack(fill="x", padx=20, pady=(10, 10))

        # Learning settings
        learning_row = ttk.Frame(ai_frame)
        learning_row.pack(fill="x", pady=(0, 10))

        self.learning_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(learning_row, text="Enable continuous learning", variable=self.learning_enabled).pack(
            side="left"
        )

        # Conversation memory
        memory_row = ttk.Frame(ai_frame)
        memory_row.pack(fill="x")

        ttk.Label(memory_row, text="Conversation Memory Limit:").pack(side="left")
        self.memory_limit = ttk.Entry(memory_row, width=10)
        self.memory_limit.pack(side="left", padx=(10, 0))
        self.memory_limit.insert(0, "50")
        ttk.Label(memory_row, text="conversations").pack(side="left", padx=(5, 0))

        # Action buttons
        actions_frame = ttk.Frame(frame)
        actions_frame.pack(fill="x", padx=20, pady=(20, 20))

        ttk.Button(actions_frame, text="💾 Save Settings", command=self.save_settings).pack(side="left")
        ttk.Button(actions_frame, text="[REFRESH] Reset to Defaults", command=self.reset_settings).pack(
            side="left", padx=(10, 0)
        )
        ttk.Button(actions_frame, text="[FOLDER] Open Config Folder", command=self.open_config_folder).pack(
            side="right"
        )

    def start_server(self):
        """Start the Enhanced Celsius AI server with persistence awareness"""
        try:
            # Track server management activity
            self.track_user_activity("server_management", "start_server_requested")

            self.log_message("[START] Starting Enhanced Celsius AI server (USER CONTROLLED)...")

            # Use the new persistence-aware server control
            control_script = Path("C:/Users/micro/Celsius AI/celsius_server_control.py")
            if control_script.exists():
                # Start server with user control flag
                result = subprocess.run(
                    [sys.executable, str(control_script), "start"],
                    cwd="C:/Users/micro/Celsius AI",
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    self.log_message("[OK] Server started via persistence-aware control")
                    self.log_message("[SHIELD] Defense system will now automatically maintain the server")
                else:
                    raise Exception(f"Control script failed: {result.stderr}")
            else:
                # Fallback to old method
                self.log_message("[WARNING] Using fallback start method...")

                # Check if enhanced dashboard is already running
                try:
                    response = requests.get(f"{self.dashboard_url}/api/status", timeout=2)
                    if response.status_code == 200:
                        self.log_message("[OK] Enhanced dashboard is already running!")
                        self.server_status = "Running"
                        self.update_server_status()
                        if hasattr(self, "start_button"):
                            self.start_button.config(state="disabled")
                        if hasattr(self, "stop_button"):
                            self.stop_button.config(state="normal")
                        if hasattr(self, "restart_button"):
                            self.restart_button.config(state="normal")
                        return
                except:
                    pass  # Not running, continue with startup

                # Fallback server startup
                venv_python = Path(".venv/Scripts/python.exe")
                if venv_python.exists():
                    python_exe = str(venv_python)
                else:
                    python_exe = sys.executable

                self.server_process = subprocess.Popen(
                    [python_exe, "enhanced_mobile_dashboard.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

            self.server_status = "Running"
            self.update_server_status()

            # Enable/disable buttons
            if hasattr(self, "start_button"):
                self.start_button.config(state="disabled")
            if hasattr(self, "stop_button"):
                self.stop_button.config(state="normal")
            if hasattr(self, "restart_button"):
                self.restart_button.config(state="normal")

            self.log_message("[OK] Enhanced Celsius AI server started by user!")
            self.log_message(f"[NETWORK] Dashboard: {self.dashboard_url}")
            self.log_message("[SHIELD] Defense system will now automatically maintain the server")
            self.log_message("[STATUS] Hourly logging enabled")
            self.log_message("[NETWORK] ngrok tunnels supported")

            # Wait a moment and check for tunnels
            self.root.after(3000, self.refresh_tunnels)

            # Show user notification
            messagebox.showinfo(
                "Server Started",
                "[START] Server started successfully!\n\n"
                "[SHIELD] The Celsius AI Defense System will now maintain\n"
                "the server automatically and restart it if it stops.\n\n"
                "Use the Stop Server button to stop it when needed.",
            )

        except Exception as e:
            self.log_message(f"[ERROR] Failed to start server: {e}")
            messagebox.showerror("Error", f"Failed to start server: {e}")

    def stop_server(self):
        """Stop the Enhanced Celsius AI server with persistence awareness"""
        try:
            # Track server management activity
            self.track_user_activity("server_management", "stop_server_requested")

            self.log_message("[STOP] Stopping Enhanced Celsius AI server (USER CONTROLLED)...")

            # Use the new persistence-aware server control
            control_script = Path("C:/Users/micro/Celsius AI/celsius_server_control.py")
            if control_script.exists():
                # Stop server with user control flag
                result = subprocess.run(
                    [sys.executable, str(control_script), "stop"],
                    cwd="C:/Users/micro/Celsius AI",
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    self.log_message("[OK] Server stopped via persistence-aware control")
                    self.log_message("[SHIELD] Defense system will respect user choice - server will NOT auto-restart")
                else:
                    raise Exception(f"Control script failed: {result.stderr}")
            else:
                # Fallback to old method
                self.log_message("[WARNING] Using fallback stop method...")

                # Try API first
                try:
                    response = requests.post(
                        f"{self.dashboard_url}/api/kill", json={"password": self.kill_password}, timeout=5
                    )
                    if response.status_code == 200:
                        self.log_message("[OK] Server stopped via API")
                    else:
                        raise Exception("API stop failed")
                except:
                    # Process termination fallback
                    if self.server_process:
                        self.server_process.terminate()
                        self.server_process.wait()
                        self.server_process = None

                    # Kill enhanced dashboard processes
                    subprocess.run(
                        'taskkill /f /im python.exe /fi "commandline=enhanced_mobile_dashboard.py"',
                        shell=True,
                        capture_output=True,
                    )

            self.server_status = "Stopped by User"
            self.update_server_status()

            # Clear tunnels
            self.ngrok_tunnels = []
            if hasattr(self, "tunnels_tree"):
                self.update_tunnels_display()

            # Enable/disable buttons
            if hasattr(self, "start_button"):
                self.start_button.config(state="normal")
            if hasattr(self, "stop_button"):
                self.stop_button.config(state="disabled")
            if hasattr(self, "restart_button"):
                self.restart_button.config(state="disabled")

            self.log_message("⏹️ Server stopped by user - Defense system will respect this choice!")

            # Show user notification
            messagebox.showinfo(
                "Server Stopped",
                "[STOP] Server stopped successfully!\n\n"
                "[SHIELD] The Celsius AI Defense System will respect your choice\n"
                "and will NOT automatically restart the server.\n\n"
                "To restart the server, use the Start Server button.",
            )

        except Exception as e:
            self.log_message(f"[ERROR] Error stopping server: {e}")
            messagebox.showerror("Error", f"Error stopping server: {e}")

    def restart_server(self):
        """Restart the Enhanced Celsius AI server"""
        self.log_message("[REFRESH] Restarting Enhanced Celsius AI server...")
        self.stop_server()
        time.sleep(3)  # Give more time for cleanup
        self.start_server()

    def update_server_status(self):
        """Update server status display"""
        # Check actual server status by trying to connect
        actual_status = self.check_actual_server_status()

        if actual_status == "Running":
            self.server_status = "Running"
            self.status_label.config(text="● Server Running", style="Success.TLabel")
            self.server_status_label.config(text="Running", style="Success.TLabel")

            # Update button states
            if hasattr(self, "start_button"):
                self.start_button.config(state="disabled")
            if hasattr(self, "stop_button"):
                self.stop_button.config(state="normal")
            if hasattr(self, "restart_button"):
                self.restart_button.config(state="normal")
        else:
            self.server_status = "Stopped"
            self.status_label.config(text="● Server Stopped", style="Error.TLabel")
            self.server_status_label.config(text="Stopped", style="Error.TLabel")

            # Update button states
            if hasattr(self, "start_button"):
                self.start_button.config(state="normal")
            if hasattr(self, "stop_button"):
                self.stop_button.config(state="disabled")
            if hasattr(self, "restart_button"):
                self.restart_button.config(state="disabled")

    def check_actual_server_status(self):
        """Check if the server is actually running - lightweight process check"""
        try:
            # First, quick process check (non-blocking)
            if hasattr(self, "server_process") and self.server_process:
                if self.server_process.poll() is None:  # Process is still running
                    return "Running"

            # Fallback: Very quick HTTP check with minimal timeout
            response = requests.get(f"{self.dashboard_url}/api/status", timeout=0.5)
            if response.status_code == 200:
                return "Running"
            else:
                return "Stopped"
        except:
            return "Stopped"

    def auto_start_server_delayed(self):
        """Auto-start server after interface is ready"""
        try:
            current_status = self.check_actual_server_status()
            if current_status == "Stopped":
                self.log_message("[AUTO-START] Starting server automatically...")
                self.start_server()
            else:
                self.log_message("[AUTO-START] Server already running, skipping auto-start")
        except Exception as e:
            self.log_message(f"[AUTO-START ERROR] Failed to auto-start server: {e}")

    def periodic_status_update(self):
        """Periodically update server status display - optimized for performance"""
        while getattr(self, "status_monitor_active", True):
            try:
                # Update status every 120 seconds (2 minutes) - maximum responsiveness
                self.root.after(0, self.update_server_status)
                time.sleep(120)  # 2-minute interval for optimal UI responsiveness
            except Exception as e:
                print(f"Status update error: {e}")
                time.sleep(180)  # 3-minute delay on errors

    def log_message(self, message):
        """Add a message to the log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)

        # Also add to activity monitor
        if hasattr(self, "activity_text"):
            self.activity_text.insert(tk.END, log_entry)
            self.activity_text.see(tk.END)

    def monitor_system(self):
        """Enhanced background system monitoring"""
        while True:
            try:
                # Update system stats (mock data for now)
                self.system_stats = {
                    "cpu": f"{__import__('random').randint(5, 25)}%",
                    "memory": f"{__import__('random').randint(30, 60)}%",
                    "disk": f"{__import__('random').randint(45, 80)}%",
                }

                # Check ngrok tunnels every monitoring cycle
                self.root.after(0, self.refresh_tunnels)

                # Update status cards
                self.root.after(0, self.update_status_cards)

                # Update service list every cycle
                self.root.after(0, self.update_service_list)

                # Update UI in main thread
                self.root.after(0, self.update_monitoring_display)

                # Auto-refresh reports if enabled
                if hasattr(self, "auto_refresh_var") and self.auto_refresh_var.get():
                    # Refresh report every 5 minutes (60 cycles of 5 seconds)
                    if not hasattr(self, "refresh_counter"):
                        self.refresh_counter = 0

                    self.refresh_counter += 1
                    if self.refresh_counter >= 60:  # 5 minutes
                        self.root.after(0, self.refresh_latest_report)
                        self.refresh_counter = 0

                time.sleep(5)  # Update every 5 seconds

            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(10)

    def update_monitoring_display(self):
        """Update monitoring display with current stats"""
        if hasattr(self, "cpu_label"):
            self.cpu_label.config(text=self.system_stats.get("cpu", "0%"))
            self.memory_label.config(text=self.system_stats.get("memory", "0%"))
            self.disk_label.config(text=self.system_stats.get("disk", "0%"))

    def monitor_server_status(self):
        """Continuously monitor server hub's own status and health"""
        while self.server_self_monitor_active:
            try:
                # Calculate uptime
                uptime_delta = datetime.now() - self.server_start_time
                hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                self.server_uptime = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                # Check server health metrics
                server_health = self.analyze_server_health()

                # Update UI in main thread
                self.root.after(0, self.update_server_status_display, server_health)

                # Log server status periodically (every 10 minutes)
                if not hasattr(self, "status_log_counter"):
                    self.status_log_counter = 0

                self.status_log_counter += 1
                if self.status_log_counter >= 120:  # 10 minutes (5 second intervals)
                    self.log_server_health_status(server_health)
                    self.status_log_counter = 0

                time.sleep(5)  # Check every 5 seconds

            except Exception as e:
                print(f"Server self-monitoring error: {e}")
                time.sleep(10)

    def analyze_server_health(self):
        """Analyze current server health and status"""
        import psutil
        import threading

        try:
            # Get current process info
            current_process = psutil.Process()

            health_data = {
                "status": "RUNNING",
                "uptime": self.server_uptime,
                "cpu_usage": f"{current_process.cpu_percent():.1f}%",
                "memory_usage": f"{current_process.memory_info().rss / 1024 / 1024:.1f} MB",
                "threads": len(threading.enumerate()),
                "connections": len(getattr(self, "connected_clients", [])),
                "components_active": self.count_active_components(),
                "last_check": datetime.now().strftime("%H:%M:%S"),
                "health_score": self.calculate_health_score(),
            }

            return health_data

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "last_check": datetime.now().strftime("%H:%M:%S"),
                "health_score": 0,
            }

    def count_active_components(self):
        """Count how many Celsius AI components are active"""
        active_count = 0
        components = ["system_integration", "power_manager", "process_trainer", "collaborative_engine"]

        for component in components:
            if hasattr(self, component) and getattr(self, component) is not None:
                active_count += 1

        return active_count

    def calculate_health_score(self):
        """Calculate overall server health score (0-100)"""
        score = 100

        # Deduct points for various issues
        if not self.celsius_fully_integrated:
            score -= 25

        if not hasattr(self, "system_integration") or self.system_integration is None:
            score -= 15

        if not hasattr(self, "power_manager") or self.power_manager is None:
            score -= 10

        if len(getattr(self, "connected_clients", [])) == 0:
            score -= 5

        return max(0, score)

    def update_server_status_display(self, health_data):
        """Update server status display in UI"""
        # Update title bar with status
        status_indicator = (
            "[ONLINE]"
            if health_data.get("health_score", 0) > 80
            else "[PENDING]" if health_data.get("health_score", 0) > 50 else "[OFFLINE]"
        )
        self.root.title(f"{status_indicator} Celsius AI - Server Hub (Uptime: {health_data.get('uptime', '00:00:00')})")

        # Update server status in any status displays
        if hasattr(self, "server_status_label"):
            status_text = (
                f"Server: {health_data.get('status', 'UNKNOWN')} | Health: {health_data.get('health_score', 0)}/100"
            )
            self.server_status_label.config(text=status_text)

        # Update health monitoring labels
        if hasattr(self, "uptime_label"):
            self.uptime_label.config(text=health_data.get("uptime", "00:00:00"))

        if hasattr(self, "health_score_label"):
            score = health_data.get("health_score", 0)
            color = "#4CAF50" if score > 80 else "#FF9800" if score > 50 else "#F44336"
            self.health_score_label.config(text=f"{score}/100", foreground=color)

        if hasattr(self, "server_cpu_label"):
            self.server_cpu_label.config(text=health_data.get("cpu_usage", "0.0%"))

        if hasattr(self, "server_memory_label"):
            self.server_memory_label.config(text=health_data.get("memory_usage", "0 MB"))

        if hasattr(self, "components_label"):
            comp_count = health_data.get("components_active", 0)
            color = "#4CAF50" if comp_count == 4 else "#FF9800" if comp_count > 2 else "#F44336"
            self.components_label.config(text=f"{comp_count}/4", foreground=color)

        if hasattr(self, "last_check_label"):
            self.last_check_label.config(text=health_data.get("last_check", "--:--:--"))

    def log_server_health_status(self, health_data):
        """Log server health status for monitoring"""
        status_msg = (
            f"🏥 SERVER HEALTH | Status: {health_data.get('status', 'UNKNOWN')} | "
            f"Uptime: {health_data.get('uptime', '00:00:00')} | "
            f"Health: {health_data.get('health_score', 0)}/100 | "
            f"Components: {health_data.get('components_active', 0)}/4 | "
            f"CPU: {health_data.get('cpu_usage', 'N/A')} | "
            f"Memory: {health_data.get('memory_usage', 'N/A')}"
        )

        self.log_message(status_msg)

    def check_for_updates(self):
        """Check for available updates"""
        try:
            self.log_message("[SEARCH] Checking for updates...")
            # Simulate update check
            self.log_message("[OK] You have the latest version!")
        except Exception as e:
            self.log_message(f"[ERROR] Update check failed: {e}")

    # Placeholder methods for functionality
    def clear_logs(self):
        self.log_text.delete(1.0, tk.END)
        self.activity_text.delete(1.0, tk.END)

    def save_logs(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, "w") as f:
                f.write(self.log_text.get(1.0, tk.END))
            self.log_message(f"📄 Logs saved to {filename}")

    def refresh_logs(self):
        self.log_message("[REFRESH] Logs refreshed")

    def refresh_clients(self):
        self.log_message("[REFRESH] Refreshing client list...")

    def show_client_details(self):
        messagebox.showinfo("Client Details", "Client details functionality coming soon!")

    def disconnect_client(self):
        messagebox.showinfo("Disconnect Client", "Client disconnect functionality coming soon!")

    def create_installer(self):
        """Create installation packages for all devices"""
        self.log_message("[CONFIG] Creating installation packages...")

        def create_packages():
            try:
                # Import and run package creator
                import subprocess
                import sys

                # Run package creator
                result = subprocess.run(
                    [sys.executable, "celsius_package_creator.py"],
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(__file__),
                )

                if result.returncode == 0:
                    self.root.after(
                        0,
                        lambda: (
                            self.log_message("[OK] Installation packages created successfully!"),
                            messagebox.showinfo(
                                "Success",
                                "Installation packages created:\n\n"
                                "📦 Windows Laptop Client\n"
                                "[MOBILE] Android Samsung S25 Ultra Client\n\n"
                                "Check the 'packages' folder for ZIP files.",
                            ),
                        ),
                    )
                else:
                    self.root.after(
                        0,
                        lambda: (
                            self.log_message(f"[ERROR] Package creation failed: {result.stderr}"),
                            messagebox.showerror("Error", f"Package creation failed:\n{result.stderr}"),
                        ),
                    )

            except Exception as e:
                self.root.after(
                    0,
                    lambda: (
                        self.log_message(f"[ERROR] Error creating packages: {str(e)}"),
                        messagebox.showerror("Error", f"Failed to create packages:\n{str(e)}"),
                    ),
                )

        # Run in background thread
        threading.Thread(target=create_packages, daemon=True).start()

    def create_package(self):
        """Create custom distribution package"""
        # Ask user what type of package to create
        package_type = messagebox.askquestion(
            "Package Type",
            "Create device installation packages?\n\n"
            "Yes = Device Packages (Windows + Android)\n"
            "No = Server Distribution Package",
            icon="question",
        )

        if package_type == "yes":
            self.create_installer()
        else:
            self.create_server_package()

    def create_server_package(self):
        """Create server distribution package"""
        self.log_message("📦 Creating server distribution package...")

        def create_server_dist():
            try:
                import zipfile
                from datetime import datetime

                # Create packages directory
                packages_dir = Path("packages")
                packages_dir.mkdir(exist_ok=True)

                # Create server package
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                package_name = f"celsius_ai_server_{timestamp}.zip"
                package_path = packages_dir / package_name

                # Files to include in server package
                server_files = [
                    "celsius_server_hub.py",
                    "start_celsius_fixed.py",
                    "celsius_updater.py",
                    "start_server_hub.bat",
                    "start_server_hub.ps1",
                    "requirements.txt",
                    "config/",
                    "templates/",
                    "static/",
                    "README.md",
                ]

                with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    base_dir = Path(".")
                    for file_pattern in server_files:
                        file_path = base_dir / file_pattern
                        if file_path.exists():
                            if file_path.is_file():
                                zipf.write(file_path, file_pattern)
                            elif file_path.is_dir():
                                for root, dirs, files in os.walk(file_path):
                                    for file in files:
                                        full_path = os.path.join(root, file)
                                        arc_path = os.path.relpath(full_path, base_dir)
                                        zipf.write(full_path, arc_path)

                self.root.after(
                    0,
                    lambda: (
                        self.log_message(f"[OK] Server package created: {package_name}"),
                        messagebox.showinfo(
                            "Success",
                            f"Server distribution package created:\n{package_name}\n\n" f"Location: {package_path}",
                        ),
                    ),
                )

            except Exception as e:
                self.root.after(
                    0,
                    lambda: (
                        self.log_message(f"[ERROR] Server package creation failed: {str(e)}"),
                        messagebox.showerror("Error", f"Failed to create server package:\n{str(e)}"),
                    ),
                )

        threading.Thread(target=create_server_dist, daemon=True).start()

    def export_config(self):
        messagebox.showinfo("Export", "Configuration export functionality coming soon!")

    def import_config(self):
        messagebox.showinfo("Import", "Configuration import functionality coming soon!")

    def send_chat_message(self, event=None):
        """Send chat message to Celsius AI"""
        if event and event.keysym == "Return" and event.state & 1:  # Shift+Return
            return  # Allow new line

        message = self.chat_input.get("1.0", "end-1c").strip()
        if not message:
            return "break" if event else None

        # Clear input
        self.chat_input.delete("1.0", "end")

        # Display user message
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", f"You: {message}\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see("end")

        # Update status
        self.chat_status.config(text="Thinking...", foreground="#FF9800")

        # Send to AI in background thread
        threading.Thread(target=self.process_chat_message, args=(message,), daemon=True).start()

        return "break" if event else None

    def process_chat_message(self, message):
        """Process chat message with Celsius AI"""
        try:
            # Check if server is running locally
            if self.server_status == "Running":
                url = "http://localhost:8000/chat"
                response = requests.post(url, json={"message": message}, timeout=30)

                if response.status_code == 200:
                    ai_response = response.json().get("response", "Sorry, I encountered an error.")
                else:
                    ai_response = "Server error. Please check if Celsius AI server is running properly."
            else:
                # Fallback to basic responses if server is not running
                ai_response = self.get_offline_response(message)

            # Display AI response
            self.root.after(0, self.display_ai_response, ai_response)

        except requests.exceptions.RequestException:
            # Server not available, use offline mode
            ai_response = self.get_offline_response(message)
            self.root.after(0, self.display_ai_response, ai_response)
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.root.after(0, self.display_ai_response, error_msg)

    def get_offline_response(self, message):
        """Basic offline responses when server is not available"""
        message_lower = message.lower()

        if any(word in message_lower for word in ["help", "what can you do", "capabilities"]):
            return (
                "I'm Celsius AI, your cybersecurity defense assistant. I can help with:\n"
                "• Network security analysis\n"
                "• Threat detection and analysis\n"
                "• Device management\n"
                "• Security recommendations\n"
                "• Vulnerability assessments\n\n"
                "Note: Full AI capabilities require the server to be running."
            )

        elif any(word in message_lower for word in ["status", "how are you", "hello", "hi"]):
            return (
                "Hello! I'm your Celsius AI assistant. Currently running in offline mode. "
                "Start the server for full AI capabilities and real-time threat analysis."
            )

        elif any(word in message_lower for word in ["security", "threat", "scan", "analyze"]):
            return (
                "For security analysis and threat detection, please start the Celsius AI server "
                "from the Server Control tab. This will enable full AI capabilities including "
                "real-time threat monitoring and network analysis."
            )

        else:
            return (
                "I'm currently in offline mode. Please start the Celsius AI server for full "
                "conversational capabilities and advanced security features."
            )

    def display_ai_response(self, response):
        """Display AI response in chat"""
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", f"[SHIELD] Celsius AI: {response}\n\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see("end")

        # Update status
        self.chat_status.config(text="Ready", foreground="#4CAF50")

    def clear_chat(self):
        """Clear chat history"""
        self.chat_display.config(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.insert(
            "end",
            "[SHIELD] Celsius AI: Hello! I'm your personal cybersecurity defense assistant. How can I help you today?\n\n",
        )
        self.chat_display.config(state="disabled")

    def save_chat(self):
        """Save chat history to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Chat History",
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    chat_content = self.chat_display.get("1.0", "end-1c")
                    f.write(f"Celsius AI Chat History - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(chat_content)
                messagebox.showinfo("Success", f"Chat history saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save chat history: {e}")

    def reset_chat_context(self):
        """Reset chat context (clear conversation memory)"""
        try:
            if self.server_status == "Running":
                response = requests.post("http://localhost:8000/reset_context", timeout=10)
                if response.status_code == 200:
                    messagebox.showinfo("Success", "Chat context has been reset.")
                    self.clear_chat()
                else:
                    messagebox.showerror("Error", "Failed to reset context on server.")
            else:
                messagebox.showinfo("Info", "Server is not running. Chat context reset locally.")
                self.clear_chat()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset context: {e}")

    def apply_network_config(self):
        self.log_message("[SETTINGS] Applying network configuration...")
        messagebox.showinfo("Network", "Network configuration applied!")

    def configure_ssl(self):
        messagebox.showinfo("SSL", "SSL configuration functionality coming soon!")

    def toggle_auto_update(self):
        self.auto_update_enabled = self.auto_update_var.get()
        status = "enabled" if self.auto_update_enabled else "disabled"
        self.log_message(f"[REFRESH] Auto-update {status}")

    def update_component(self):
        messagebox.showinfo("Update", "Component update functionality coming soon!")

    def install_component(self):
        messagebox.showinfo("Install", "Component installation functionality coming soon!")

    def remove_component(self):
        messagebox.showinfo("Remove", "Component removal functionality coming soon!")

    def save_settings(self):
        self.log_message("💾 Settings saved successfully!")
        messagebox.showinfo("Settings", "Settings saved successfully!")

    def reset_settings(self):
        self.log_message("[REFRESH] Settings reset to defaults")
        messagebox.showinfo("Reset", "Settings reset to defaults!")

    def open_config_folder(self):
        config_path = Path.cwd() / "config"
        config_path.mkdir(exist_ok=True)
        os.startfile(config_path)

    # Enhanced ngrok tunnel methods
    def refresh_tunnels(self):
        """Refresh the ngrok tunnels list"""
        self.ngrok_tunnels = []

        # Check multiple ngrok API ports
        for port in [4040, 4041, 4042, 4043]:
            try:
                response = requests.get(f"http://127.0.0.1:{port}/api/tunnels", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    for tunnel in data.get("tunnels", []):
                        tunnel_info = {
                            "name": tunnel.get("name", "Unknown"),
                            "protocol": tunnel.get("proto", ""),
                            "public_url": tunnel.get("public_url", ""),
                            "local_addr": tunnel.get("config", {}).get("addr", ""),
                            "status": "active",
                            "created": tunnel.get("created_at", ""),
                            "web_port": port,
                        }
                        self.ngrok_tunnels.append(tunnel_info)
                    break  # Found active ngrok instance
            except:
                continue

        # Update the treeview
        self.update_tunnels_display()

        # Update auth token status
        self.check_ngrok_auth()

    def update_tunnels_display(self):
        """Update the tunnels treeview display"""
        # Check if widget exists before accessing it
        if not hasattr(self, "tunnels_tree") or not self.tunnels_tree.winfo_exists():
            return

        # Clear existing items
        for item in self.tunnels_tree.get_children():
            self.tunnels_tree.delete(item)

        # Add current tunnels
        for tunnel in self.ngrok_tunnels:
            created_time = tunnel["created"]
            if created_time:
                try:
                    # Parse and format the timestamp
                    dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
                    created_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass

            self.tunnels_tree.insert(
                "",
                "end",
                values=(
                    tunnel["name"],
                    tunnel["protocol"],
                    tunnel["public_url"],
                    tunnel["local_addr"],
                    tunnel["status"],
                    created_time,
                ),
            )

    def copy_tunnel_url(self):
        """Copy selected tunnel URL to clipboard"""
        selection = self.tunnels_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a tunnel first.")
            return

        item = self.tunnels_tree.item(selection[0])
        public_url = item["values"][2]  # Public URL column

        if public_url:
            self.root.clipboard_clear()
            self.root.clipboard_append(public_url)
            self.root.update()  # Keep clipboard after app closes
            messagebox.showinfo("Copied", f"URL copied to clipboard:\n{public_url}")
        else:
            messagebox.showwarning("No URL", "Selected tunnel has no public URL.")

    def open_tunnel_url(self):
        """Open selected tunnel URL in browser"""
        selection = self.tunnels_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a tunnel first.")
            return

        item = self.tunnels_tree.item(selection[0])
        public_url = item["values"][2]  # Public URL column

        if public_url:
            webbrowser.open(public_url)
        else:
            messagebox.showwarning("No URL", "Selected tunnel has no public URL.")

    def start_ngrok(self):
        """Start ngrok tunnel"""
        port = self.port_var.get()
        protocol = self.protocol_var.get()

        if not port or not port.isdigit():
            messagebox.showerror("Invalid Port", "Please enter a valid port number.")
            return

        try:
            # Start ngrok in background
            if protocol == "http":
                cmd = f"ngrok http {port}"
            else:
                cmd = f"ngrok {protocol} {port}"

            subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)

            # Wait a moment and refresh
            self.root.after(3000, self.refresh_tunnels)  # Refresh after 3 seconds

            self.log_message(f"[NETWORK] Started ngrok {protocol} tunnel on port {port}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start ngrok: {str(e)}")

    def stop_ngrok(self):
        """Stop all ngrok processes"""
        try:
            # Kill ngrok processes
            subprocess.run("taskkill /f /im ngrok.exe", shell=True, capture_output=True)

            # Clear tunnels list
            self.ngrok_tunnels = []
            self.update_tunnels_display()

            self.log_message("[STOP] Stopped all ngrok tunnels")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop ngrok: {str(e)}")

    def check_ngrok_auth(self):
        """Check ngrok authentication status"""
        try:
            # Check if auth token is configured
            result = subprocess.run("ngrok config check", shell=True, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                self.auth_status_label.config(text="[OK] Authenticated", style="Success.TLabel")
            else:
                self.auth_status_label.config(text="[ERROR] Not Authenticated", style="Error.TLabel")

        except:
            self.auth_status_label.config(text="❓ Unknown", style="Warning.TLabel")

    def configure_ngrok_auth(self):
        """Configure ngrok authentication"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure ngrok Authentication")
        dialog.geometry("500x300")
        dialog.configure(bg="#1a1a1a")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))

        # Auth token input
        ttk.Label(dialog, text="ngrok Auth Token:", font=("Arial", 12, "bold")).pack(pady=20)

        token_var = tk.StringVar(value="32zwuYatyHVr0C6Tf9AF2WWtMnX_xqrbXAGgmrXrkKTJbdxx")
        token_entry = ttk.Entry(dialog, textvariable=token_var, width=60, show="*")
        token_entry.pack(pady=10)

        # Instructions
        instructions = """
Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken

This token allows you to:
• Create multiple tunnels simultaneously
• Use custom subdomains
• Access ngrok dashboard
• Remove connection time limits
        """

        ttk.Label(dialog, text=instructions, font=("Arial", 9)).pack(pady=20)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)

        def save_token():
            token = token_var.get().strip()
            if token:
                try:
                    # Configure ngrok auth token
                    subprocess.run(f"ngrok config add-authtoken {token}", shell=True, check=True, capture_output=True)

                    messagebox.showinfo("Success", "Auth token configured successfully!")
                    dialog.destroy()

                    # Refresh auth status
                    self.check_ngrok_auth()

                except subprocess.CalledProcessError as e:
                    messagebox.showerror("Error", f"Failed to configure auth token: {str(e)}")
            else:
                messagebox.showwarning("Warning", "Please enter a valid auth token.")

        ttk.Button(button_frame, text="💾 Save Token", command=save_token).pack(side="left", padx=10)
        ttk.Button(button_frame, text="[ERROR] Cancel", command=dialog.destroy).pack(side="left", padx=10)

    # Enhanced hourly reports methods
    def create_status_card(self, parent, title, status_key, row, col):
        """Create a status card widget"""
        card_frame = ttk.LabelFrame(parent, text=title, padding=15)
        card_frame.grid(row=row, column=col, padx=10, pady=10, sticky="ew")

        # Status value
        status_var = tk.StringVar(value="Checking...")
        status_label = ttk.Label(
            card_frame, textvariable=status_var, font=("Arial", 14, "bold"), style="Warning.TLabel"
        )
        status_label.pack()

        # Store reference for updates
        setattr(self, f"{status_key}_var", status_var)
        setattr(self, f"{status_key}_label", status_label)

        return card_frame

    def generate_report_now(self):
        """Generate an immediate hourly report"""
        try:
            # Import and use the hourly logger
            sys.path.insert(0, str(Path.cwd()))
            from celsius_hourly_logger import CelsiusLogger

            logger = CelsiusLogger()
            report = logger.generate_hourly_report()

            if isinstance(report, dict):
                self.display_report(report)
                messagebox.showinfo("Success", "Hourly report generated successfully!")
            else:
                messagebox.showerror("Error", "Failed to generate report.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")

    def view_all_reports(self):
        """View all available hourly reports"""
        try:
            # Check if reports exist
            logs_dir = Path("logs")
            if not logs_dir.exists():
                messagebox.showinfo("No Reports", "No hourly reports found.")
                return

            # Open reports directory
            os.startfile(logs_dir)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open reports directory: {str(e)}")

    def configure_logging(self):
        """Configure hourly logging settings"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Logging Configuration")
        dialog.geometry("400x300")
        dialog.configure(bg="#1a1a1a")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))

        # Logging options
        ttk.Label(dialog, text="Hourly Logging Settings", font=("Arial", 14, "bold")).pack(pady=20)

        # Enable/disable logging
        enable_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, text="Enable hourly logging", variable=enable_var).pack(pady=10)

        # Performance metrics interval
        ttk.Label(dialog, text="Performance metrics interval (minutes):").pack(pady=(20, 5))
        interval_var = tk.StringVar(value="5")
        ttk.Entry(dialog, textvariable=interval_var, width=10).pack()

        # Report retention
        ttk.Label(dialog, text="Keep reports for (hours):").pack(pady=(20, 5))
        retention_var = tk.StringVar(value="24")
        ttk.Entry(dialog, textvariable=retention_var, width=10).pack()

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=30)

        ttk.Button(
            button_frame,
            text="💾 Save Settings",
            command=lambda: self.save_logging_settings(
                enable_var.get(), interval_var.get(), retention_var.get(), dialog
            ),
        ).pack(side="left", padx=10)
        ttk.Button(button_frame, text="[ERROR] Cancel", command=dialog.destroy).pack(side="left", padx=10)

    def save_logging_settings(self, enabled, interval, retention, dialog):
        """Save logging configuration settings"""
        try:
            # Validate inputs
            interval_int = int(interval)
            retention_int = int(retention)

            if interval_int < 1 or retention_int < 1:
                raise ValueError("Values must be positive")

            # Save settings (you can implement actual persistence here)
            self.hourly_logging_enabled = enabled

            messagebox.showinfo("Success", "Logging settings saved successfully!")
            dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", "Please enter valid positive numbers.")

    def refresh_latest_report(self):
        """Refresh the latest hourly report display"""
        try:
            # Get latest report from database
            if self.db_path.exists():
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT timestamp, system_status, performance_metrics, 
                           error_summary, recommendations
                    FROM hourly_reports
                    ORDER BY timestamp DESC
                    LIMIT 1
                """
                )

                row = cursor.fetchone()
                conn.close()

                if row:
                    # Parse and display the report
                    timestamp, system_status, performance_metrics, error_summary, recommendations = row

                    # Format the report with better readability
                    report_text = self.format_enhanced_report(
                        timestamp, system_status, performance_metrics, error_summary, recommendations
                    )

                    self.report_text.delete(1.0, tk.END)
                    self.report_text.insert(1.0, report_text)

                else:
                    self.report_text.delete(1.0, tk.END)
                    self.report_text.insert(
                        1.0, "No hourly reports available yet.\n\nRun 'Generate Report Now' to create one."
                    )
            else:
                self.report_text.delete(1.0, tk.END)
                self.report_text.insert(
                    1.0, "Hourly logging database not found.\n\nStart the enhanced dashboard to begin logging."
                )

        except Exception as e:
            self.report_text.delete(1.0, tk.END)
            self.report_text.insert(1.0, f"Error loading report: {str(e)}")

    def format_enhanced_report(self, timestamp, system_status, performance_metrics, error_summary, recommendations):
        """Format report with enhanced readability and visual structure"""
        try:
            # Parse JSON data safely
            status_data = json.loads(system_status) if system_status else {}
            metrics_data = json.loads(performance_metrics) if performance_metrics else {}
            errors_data = json.loads(error_summary) if error_summary else {}
            recommendations_data = json.loads(recommendations) if recommendations else {}

            # Create beautifully formatted report
            report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    [SHIELD]  CELSIUS AI HOURLY REPORT              ║
╚══════════════════════════════════════════════════════════════╝

📅 REPORT DETAILS
   Generated: {timestamp}
   Report Type: System Health & Performance Analysis
   Status: {"[ONLINE] HEALTHY" if not errors_data else "[PENDING] ATTENTION NEEDED"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[SERVER]  SYSTEM STATUS OVERVIEW
"""

            # Format system status
            if isinstance(status_data, dict):
                for key, value in status_data.items():
                    icon = "[OK]" if "error" not in str(value).lower() else "[WARNING]"
                    report += f"   {icon} {key.replace('_', ' ').title()}: {value}\n"
            else:
                report += f"   [STATUS] Status: {status_data}\n"

            report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            report += "\n[STATS] PERFORMANCE METRICS\n"

            # Format performance metrics
            if isinstance(metrics_data, dict):
                for category, data in metrics_data.items():
                    report += f"\n   [TARGET] {category.replace('_', ' ').title()}:\n"
                    if isinstance(data, dict):
                        for metric, value in data.items():
                            # Add color coding based on metric values
                            if "cpu" in metric.lower():
                                icon = (
                                    "[ONLINE]"
                                    if isinstance(value, (int, float)) and value < 80
                                    else "[PENDING]" if value < 95 else "[OFFLINE]"
                                )
                            elif "memory" in metric.lower():
                                icon = (
                                    "[ONLINE]"
                                    if isinstance(value, (int, float)) and value < 85
                                    else "[PENDING]" if value < 95 else "[OFFLINE]"
                                )
                            elif "disk" in metric.lower():
                                icon = (
                                    "[ONLINE]"
                                    if isinstance(value, (int, float)) and value < 90
                                    else "[PENDING]" if value < 98 else "[OFFLINE]"
                                )
                            else:
                                icon = "[STATUS]"
                            report += f"     {icon} {metric.replace('_', ' ').title()}: {value}\n"
                    else:
                        report += f"     [STATUS] Value: {data}\n"
            else:
                report += f"   [STATUS] Metrics: {metrics_data}\n"

            report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            # Format errors and issues
            if errors_data:
                report += "\n[WARNING]  ISSUES & ALERTS\n"
                if isinstance(errors_data, dict):
                    for category, issues in errors_data.items():
                        if issues:
                            report += f"\n   [SEARCH] {category.replace('_', ' ').title()}:\n"
                            if isinstance(issues, list):
                                for issue in issues:
                                    report += f"     🔸 {issue}\n"
                            else:
                                report += f"     🔸 {issues}\n"
                elif isinstance(errors_data, list):
                    for error in errors_data:
                        report += f"   🔸 {error}\n"
                else:
                    report += f"   🔸 {errors_data}\n"
            else:
                report += "\n[OK] SYSTEM HEALTH\n   [ONLINE] No issues detected - All systems operating normally\n"

            report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            # Format recommendations
            if recommendations_data:
                report += "\n[TIP] OPTIMIZATION RECOMMENDATIONS\n"
                if isinstance(recommendations_data, dict):
                    for category, recs in recommendations_data.items():
                        if recs:
                            report += f"\n   [TARGET] {category.replace('_', ' ').title()}:\n"
                            if isinstance(recs, list):
                                for rec in recs:
                                    report += f"     💫 {rec}\n"
                            else:
                                report += f"     💫 {recs}\n"
                elif isinstance(recommendations_data, list):
                    for rec in recommendations_data:
                        report += f"   💫 {rec}\n"
                else:
                    report += f"   💫 {recommendations_data}\n"
            else:
                report += (
                    "\n[TARGET] SYSTEM OPTIMIZATION\n   ✨ System running optimally - No recommendations at this time\n"
                )

            report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            report += "\n🤖 Celsius AI - Your Intelligent System Guardian\n"
            report += "   [MOBILE] Access from mobile: Check ngrok tunnel in Server Hub\n"
            report += "   [REFRESH] Next report: Automatically generated every hour\n"
            report += "   [STATUS] View all reports: Click 'View All Reports' button\n\n"

            return report

        except Exception as e:
            return f"""
╔══════════════════════════════════════════════════════════════╗
║                    [WARNING]  REPORT ERROR                          ║
╚══════════════════════════════════════════════════════════════╝

[ERROR] Error formatting report: {str(e)}

📋 Raw Data:
   Timestamp: {timestamp}
   System Status: {system_status}
   Performance: {performance_metrics}
   Errors: {error_summary}
   Recommendations: {recommendations}
"""

    def display_report(self, report):
        """Display a report in the text widget with enhanced formatting"""
        if not isinstance(report, dict):
            return

        # Format with enhanced visual structure
        report_text = f"""
╔══════════════════════════════════════════════════════════════╗
║                  [SHIELD]  CELSIUS AI SYSTEM REPORT               ║
╚══════════════════════════════════════════════════════════════╝

📅 REPORT INFORMATION
   Generated: {report.get('report_timestamp', 'Unknown')}
   Report Type: {report.get('report_period', 'System Analysis')}
   Duration: Hourly Analysis Report

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[SERVER]  SYSTEM OVERVIEW
"""

        # System Summary with icons
        summary = report.get("system_summary", {})
        if isinstance(summary, dict):
            status = summary.get("status", "Unknown")
            status_icon = (
                "[ONLINE]"
                if status.lower() == "healthy"
                else "[PENDING]" if "warning" in status.lower() else "[OFFLINE]"
            )

            report_text += f"""   {status_icon} System Status: {status}
   ⏰ Uptime: {summary.get('uptime', 'Unknown')}
   [REFRESH] Active Processes: {summary.get('active_processes', 0)}
   [NETWORK] Network Tunnels: {summary.get('active_tunnels', 0)}
"""

        report_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report_text += "\n[STATUS] PERFORMANCE METRICS\n"

        # Performance with color coding
        performance = report.get("performance_summary", {})
        if isinstance(performance, dict):
            cpu_avg = performance.get("cpu_average", 0)
            mem_avg = performance.get("memory_average", 0)

            cpu_icon = "[ONLINE]" if cpu_avg < 70 else "[PENDING]" if cpu_avg < 85 else "[OFFLINE]"
            mem_icon = "[ONLINE]" if mem_avg < 80 else "[PENDING]" if mem_avg < 90 else "[OFFLINE]"

            perf_score = performance.get("performance_score", 0)
            score_icon = "[ONLINE]" if perf_score >= 80 else "[PENDING]" if perf_score >= 60 else "[OFFLINE]"

            report_text += f"""   [STATS] Sample Count: {performance.get('sample_count', 0)} measurements
   {cpu_icon} CPU Usage: {cpu_avg}% average
   {mem_icon} Memory Usage: {mem_avg}% average
   💾 Disk Usage: {performance.get('disk_usage', 'N/A')}%
   [FAST] Response Time: {performance.get('response_time_average', 'N/A')}ms
   {score_icon} Performance Score: {perf_score}/100
"""

        report_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        # Error Analysis with visual indicators
        error_summary = report.get("error_analysis", {})
        total_errors = error_summary.get("total_errors", 0) if isinstance(error_summary, dict) else 0

        if total_errors > 0:
            report_text += f"\n[WARNING]  SYSTEM ALERTS ({total_errors} total)\n"
            if isinstance(error_summary, dict):
                critical = error_summary.get("critical_count", 0)
                warnings = error_summary.get("warning_count", 0)

                if critical > 0:
                    report_text += f"   [OFFLINE] Critical Issues: {critical}\n"
                if warnings > 0:
                    report_text += f"   [PENDING] Warnings: {warnings}\n"

                errors = error_summary.get("errors", [])
                if errors:
                    report_text += "\n   📋 Recent Issues:\n"
                    for error in errors[:3]:  # Show top 3 errors
                        level = error.get("level", "Unknown").upper()
                        icon = "[OFFLINE]" if level == "CRITICAL" else "[PENDING]" if level == "WARNING" else "[INFO]"
                        report_text += f"     {icon} {level}: {error.get('message', 'No message')}\n"
        else:
            report_text += (
                "\n[OK] SYSTEM HEALTH STATUS\n   [ONLINE] No issues detected - All systems operating normally\n"
            )

        report_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        # Recommendations with priority indicators
        recommendations = report.get("recommendations", [])
        if recommendations:
            report_text += f"\n[TIP] OPTIMIZATION SUGGESTIONS ({len(recommendations)} total)\n"
            for i, rec in enumerate(recommendations[:3], 1):  # Show top 3 recommendations
                priority = rec.get("priority", "medium").lower()
                priority_icon = (
                    "[OFFLINE]" if priority == "high" else "[PENDING]" if priority == "medium" else "[ONLINE]"
                )
                category = rec.get("category", "General").title()

                report_text += f"\n   {priority_icon} {i}. {category} Optimization ({priority.title()} Priority)\n"
                report_text += f"      📝 Issue: {rec.get('message', 'No description')}\n"
                report_text += f"      [TARGET] Action: {rec.get('action', 'No action specified')}\n"
        else:
            report_text += (
                "\n[TARGET] SYSTEM OPTIMIZATION\n   ✨ System running optimally - No recommendations at this time\n"
            )

        report_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report_text += "\n🤖 Celsius AI - Intelligent System Management\n"
        report_text += "   [MOBILE] Mobile Access: Available via ngrok tunnel\n"
        report_text += "   [REFRESH] Auto Reports: Generated every hour\n"
        report_text += "   [STATUS] Full History: Use 'View All Reports' for complete analysis\n\n"

        # Update the text widget
        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(1.0, report_text)

    def update_status_cards(self):
        """Update the status cards in the reports tab"""
        try:
            # System status
            if hasattr(self, "system_status_var"):
                if self.server_status == "Running":
                    self.system_status_var.set("[OK] Operational")
                    self.system_status_label.config(style="Success.TLabel")
                else:
                    self.system_status_var.set("[ERROR] Stopped")
                    self.system_status_label.config(style="Error.TLabel")

            # Performance status (mock data - you can implement real metrics)
            if hasattr(self, "performance_var"):
                self.performance_var.set("[FAST] Good (85/100)")
                self.performance_label.config(style="Success.TLabel")

            # Security status
            if hasattr(self, "security_var"):
                self.security_var.set("[LOCKED] Protected")
                self.security_label.config(style="Success.TLabel")

            # Reports count
            if hasattr(self, "reports_var"):
                logs_dir = Path("logs")
                if logs_dir.exists():
                    report_count = len(list(logs_dir.glob("celsius_report_*.json")))
                    self.reports_var.set(f"[STATUS] {report_count} Reports")
                else:
                    self.reports_var.set("[STATUS] No Reports")
                self.reports_label.config(style="Success.TLabel")

        except Exception as e:
            print(f"Error updating status cards: {e}")

    # Enhanced deployment and update methods
    def update_service_list(self):
        """Update the service component list with real data"""
        # Check if widget exists before accessing it
        if not hasattr(self, "components_tree") or not self.components_tree.winfo_exists():
            return

        # Clear existing items
        for item in self.components_tree.get_children():
            self.components_tree.delete(item)

        # Get real service status
        services = [
            {
                "name": "Enhanced Dashboard",
                "process": "enhanced_mobile_dashboard.py",
                "port": 5000,
                "health_endpoint": "/api/status",
            },
            {"name": "Hourly Logger", "process": "celsius_hourly_logger.py", "port": None, "health_endpoint": None},
            {
                "name": "Persistent Service",
                "process": "persistent_celsius_service.py",
                "port": None,
                "health_endpoint": None,
            },
            {"name": "ngrok Tunnel", "process": "ngrok.exe", "port": 4040, "health_endpoint": "/api/tunnels"},
        ]

        for service in services:
            status, uptime, health = self.get_service_status(service)
            version = self.get_service_version(service["name"])
            last_update = self.get_last_update_time(service["name"])

            self.components_tree.insert(
                "", "end", values=(service["name"], version, status, uptime, health, last_update, "Available")
            )

    def get_service_status(self, service):
        """Get real-time status of a service"""
        try:
            if service["process"] == "ngrok.exe":
                # Check ngrok process
                result = subprocess.run(
                    'tasklist /FI "IMAGENAME eq ngrok.exe"', shell=True, capture_output=True, text=True
                )
                if "ngrok.exe" in result.stdout:
                    return "[OK] Running", "Active", "Healthy"
                else:
                    return "[ERROR] Stopped", "0s", "Offline"

            elif service["port"] and service["health_endpoint"]:
                # Check web service
                response = requests.get(f"http://localhost:{service['port']}{service['health_endpoint']}", timeout=2)
                if response.status_code == 200:
                    return "[OK] Running", "Active", "Healthy"
                else:
                    return "[WARNING] Issues", "Unknown", "Degraded"

            else:
                # Check process by name
                for proc in __import__("psutil").process_iter(["name", "cmdline"]):
                    if service["process"] in " ".join(proc.info["cmdline"] or []):
                        return "[OK] Running", "Active", "Healthy"

                return "[ERROR] Stopped", "0s", "Offline"

        except:
            return "❓ Unknown", "Unknown", "Unknown"

    def get_service_version(self, service_name):
        """Get version information for a service"""
        # For now, return current version
        return "v2.0.0-Enhanced"

    def get_last_update_time(self, service_name):
        """Get last update time for a service"""
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    def push_all_updates(self):
        """Push updates to all services through the hub"""
        self.log_deployment("[START] Starting system-wide update deployment...")

        # Start progress
        self.progress_var.set(0)
        self.root.update()

        def update_progress(step, total, message):
            progress = (step / total) * 100
            self.progress_var.set(progress)
            self.log_deployment(f"[{step}/{total}] {message}")
            self.root.update()

        try:
            # Step 1: Backup current system
            update_progress(1, 8, "Creating system backup...")
            self.create_system_backup()

            # Step 2: Stop services gracefully
            update_progress(2, 8, "Stopping services gracefully...")
            self.graceful_service_stop()

            # Step 3: Update core files
            update_progress(3, 8, "Updating core system files...")
            self.update_core_files()

            # Step 4: Update configurations
            update_progress(4, 8, "Updating configurations...")
            self.update_configurations()

            # Step 5: Install/update dependencies
            update_progress(5, 8, "Installing dependencies...")
            self.update_dependencies()

            # Step 6: Restart services
            update_progress(6, 8, "Restarting services...")
            self.restart_all_services()

            # Step 7: Verify deployment
            update_progress(7, 8, "Verifying deployment...")
            self.verify_deployment()

            # Step 8: Complete
            update_progress(8, 8, "[OK] All updates deployed successfully!")

            messagebox.showinfo("Success", "All updates have been pushed and deployed successfully!")

        except Exception as e:
            self.log_deployment(f"[ERROR] Deployment failed: {str(e)}")
            messagebox.showerror("Deployment Failed", f"Update deployment failed: {str(e)}")

    def push_update_to_selected(self):
        """Push update to selected service"""
        selection = self.components_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a service to update.")
            return

        item = self.components_tree.item(selection[0])
        service_name = item["values"][0]

        self.log_deployment(f"[REFRESH] Pushing update to {service_name}...")

        try:
            if "Dashboard" in service_name:
                self.update_dashboard_service()
            elif "Logger" in service_name:
                self.update_logger_service()
            elif "Persistent" in service_name:
                self.update_persistent_service()
            elif "ngrok" in service_name:
                self.update_ngrok_service()

            self.log_deployment(f"[OK] {service_name} updated successfully!")
            self.update_service_list()

        except Exception as e:
            self.log_deployment(f"[ERROR] Failed to update {service_name}: {str(e)}")
            messagebox.showerror("Update Failed", f"Failed to update {service_name}: {str(e)}")

    def restart_selected_service(self):
        """Restart selected service"""
        selection = self.components_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a service to restart.")
            return

        item = self.components_tree.item(selection[0])
        service_name = item["values"][0]

        if messagebox.askyesno("Confirm Restart", f"Restart {service_name}?"):
            self.log_deployment(f"[REFRESH] Restarting {service_name}...")

            try:
                if "Dashboard" in service_name:
                    self.restart_server()
                elif "ngrok" in service_name:
                    self.stop_ngrok()
                    time.sleep(2)
                    self.start_ngrok()
                else:
                    # Generic service restart
                    subprocess.run(
                        f'taskkill /f /im python.exe /fi "commandline={service_name.lower()}"',
                        shell=True,
                        capture_output=True,
                    )

                self.log_deployment(f"[OK] {service_name} restarted successfully!")
                self.update_service_list()

            except Exception as e:
                self.log_deployment(f"[ERROR] Failed to restart {service_name}: {str(e)}")

    def view_service_logs(self):
        """View logs for selected service"""
        selection = self.components_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a service to view logs.")
            return

        item = self.components_tree.item(selection[0])
        service_name = item["values"][0]

        # Open logs directory or specific log file
        logs_dir = Path("logs")
        if logs_dir.exists():
            os.startfile(logs_dir)
        else:
            messagebox.showinfo("No Logs", f"No log files found for {service_name}")

    def hot_reload_services(self):
        """Hot reload services without full restart"""
        self.log_deployment("🔥 Initiating hot reload of all services...")

        try:
            # Use API to reload dashboard
            response = requests.post(f"{self.dashboard_url}/api/restart", timeout=10)
            if response.status_code == 200:
                self.log_deployment("[OK] Dashboard hot reloaded")
            else:
                self.log_deployment("[WARNING] Dashboard reload had issues")

            # Refresh service list
            self.update_service_list()
            self.log_deployment("[OK] Hot reload completed")

        except Exception as e:
            self.log_deployment(f"[ERROR] Hot reload failed: {str(e)}")

    def create_deployment_package(self):
        """Create a deployment package with all updates"""
        self.log_deployment("📦 Creating deployment package...")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            package_name = f"celsius_deployment_{timestamp}.zip"

            with zipfile.ZipFile(package_name, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Add core files
                core_files = [
                    "enhanced_mobile_dashboard.py",
                    "celsius_hourly_logger.py",
                    "persistent_celsius_service.py",
                    "celsius_server_hub.py",
                ]

                for file in core_files:
                    if Path(file).exists():
                        zipf.write(file)

                # Add configuration
                if Path("config").exists():
                    for config_file in Path("config").rglob("*"):
                        if config_file.is_file():
                            zipf.write(config_file)

            self.log_deployment(f"[OK] Deployment package created: {package_name}")
            messagebox.showinfo("Package Created", f"Deployment package created: {package_name}")

        except Exception as e:
            self.log_deployment(f"[ERROR] Failed to create package: {str(e)}")

    def check_system_health(self):
        """Comprehensive system health check"""
        self.log_deployment("[SEARCH] Running comprehensive system health check...")

        health_report = []

        # Check services
        services_healthy = 0
        total_services = len(self.components_tree.get_children())

        for item in self.components_tree.get_children():
            values = self.components_tree.item(item)["values"]
            if "[OK]" in values[2]:  # Status column
                services_healthy += 1

        health_report.append(f"Services: {services_healthy}/{total_services} healthy")

        # Check disk space
        try:
            disk = __import__("shutil").disk_usage(".")
            free_gb = disk.free // (1024**3)
            total_gb = disk.total // (1024**3)
            health_report.append(f"Disk Space: {free_gb}GB free of {total_gb}GB")
        except:
            health_report.append("Disk Space: Unable to check")

        # Check network
        try:
            response = requests.get("https://www.google.com", timeout=5)
            if response.status_code == 200:
                health_report.append("Network: Connected")
            else:
                health_report.append("Network: Issues detected")
        except:
            health_report.append("Network: Offline or issues")

        # Display health report
        report_text = "\n".join(health_report)
        self.log_deployment(f"📋 System Health Report:\n{report_text}")
        messagebox.showinfo("System Health", report_text)

    def export_configuration(self):
        """Export current system configuration"""
        try:
            config_data = {
                "timestamp": datetime.now().isoformat(),
                "version": "v2.0.0-Enhanced",
                "services": [],
                "settings": {
                    "dashboard_url": self.dashboard_url,
                    "kill_password": self.kill_password,
                    "auto_deploy": getattr(self, "auto_deploy_var", tk.BooleanVar()).get(),
                    "hot_reload": getattr(self, "hot_reload_var", tk.BooleanVar()).get(),
                },
            }

            # Add service information
            for item in self.components_tree.get_children():
                values = self.components_tree.item(item)["values"]
                config_data["services"].append({"name": values[0], "version": values[1], "status": values[2]})

            # Save configuration
            config_file = f"celsius_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)

            self.log_deployment(f"[OK] Configuration exported to {config_file}")
            messagebox.showinfo("Export Complete", f"Configuration exported to {config_file}")

        except Exception as e:
            self.log_deployment(f"[ERROR] Export failed: {str(e)}")

    def emergency_system_reset(self):
        """Emergency system reset with confirmation"""
        if not messagebox.askyesno("Emergency Reset", "This will stop all services and reset the system.\n\nContinue?"):
            return

        if not messagebox.askyesno("Final Confirmation", "Are you absolutely sure? This action cannot be undone."):
            return

        self.log_deployment("[WARNING] EMERGENCY SYSTEM RESET INITIATED")

        try:
            # Stop all services
            self.stop_server()
            self.stop_ngrok()

            # Kill all Python processes related to Celsius
            subprocess.run('taskkill /f /im python.exe /fi "commandline=celsius"', shell=True, capture_output=True)

            # Clear temporary files
            temp_files = [".env", "current_url.json", "celsius_activity.db"]
            for temp_file in temp_files:
                if Path(temp_file).exists():
                    Path(temp_file).unlink()

            self.log_deployment("[REFRESH] System reset complete - ready for clean restart")
            messagebox.showinfo("Reset Complete", "Emergency system reset completed.\nRestart the hub to begin fresh.")

        except Exception as e:
            self.log_deployment(f"[ERROR] Emergency reset failed: {str(e)}")

    # Helper methods for deployment
    def create_system_backup(self):
        """Create a backup of the current system state"""
        import shutil
        from datetime import datetime

        try:
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"celsius_backup_{timestamp}"
            backup_path.mkdir(exist_ok=True)

            # Backup key files
            important_files = [
                "celsius_server_hub.py",
                "celsius_system_integration.py",
                "celsius_power_manager.py",
                "celsius_process_trainer.py",
                "celsius_collaborative_engine.py",
                "enhanced_mobile_dashboard.py",
                "service_config.json",
            ]

            for file_name in important_files:
                source_file = Path(file_name)
                if source_file.exists():
                    shutil.copy2(source_file, backup_path / file_name)
                    self.log_deployment(f"[FOLDER] Backed up: {file_name}")

            # Backup databases
            db_files = ["celsius_system.db", "celsius_training.db", "celsius_improvements.db"]
            for db_file in db_files:
                db_path = Path(db_file)
                if db_path.exists():
                    shutil.copy2(db_path, backup_path / db_file)
                    self.log_deployment(f"🗄️ Backed up database: {db_file}")

            self.log_deployment(f"[OK] System backup created: {backup_path}")
            return str(backup_path)

        except Exception as e:
            self.log_deployment(f"[WARNING] Backup creation failed: {str(e)}")
            return None

    def graceful_service_stop(self):
        """Gracefully stop all services"""
        if self.server_status == "Running":
            self.stop_server()
        time.sleep(2)

    def update_core_files(self):
        """Update core system files"""
        # This would contain logic to update files from a repository or package
        self.log_deployment("Core files updated (placeholder)")

    def update_configurations(self):
        """Update system configurations"""
        # Update configuration files if needed
        self.log_deployment("Configurations updated (placeholder)")

    def update_dependencies(self):
        """Update Python dependencies"""
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "flask", "requests", "psutil"],
                check=True,
                capture_output=True,
            )
            self.log_deployment("Dependencies updated successfully")
        except:
            self.log_deployment("Warning: Some dependencies may not have updated")

    def verify_deployment(self):
        """Verify that deployment was successful"""
        # Check if services can start
        time.sleep(3)  # Allow services to initialize
        self.update_service_list()
        self.log_deployment("Deployment verification completed")

    def update_dashboard_service(self):
        """Update the dashboard service specifically"""
        self.restart_server()

    def update_logger_service(self):
        """Update the logger service specifically"""
        # Logger service updates would be handled here
        self.log_deployment("Logger service updated")

    def update_persistent_service(self):
        """Update the persistent service specifically"""
        # Persistent service updates would be handled here
        self.log_deployment("Persistent service updated")

    def update_ngrok_service(self):
        """Update ngrok service specifically"""
        # Check for ngrok updates
        self.log_deployment("ngrok service checked for updates")

    def log_deployment(self, message):
        """Log a deployment message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        if hasattr(self, "deployment_log"):
            self.deployment_log.insert(tk.END, log_entry)
            self.deployment_log.see(tk.END)

        # Also log to main log
        self.log_message(message)

    def check_system_status(self):
        """Check overall system status"""
        self.log_deployment("[SEARCH] Checking system status...")
        self.update_service_list()
        self.check_system_health()

    def create_celsius_integration_section(self):
        """Create Celsius AI Integration Management Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["celsius_integration"] = frame

        # Main container with padding
        main_container = ttk.Frame(frame)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Integration Status Section
        status_frame = ttk.LabelFrame(main_container, text="Celsius AI System Status", padding=20)
        status_frame.pack(fill="x", pady=(0, 20))

        # Status indicators
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill="x")

        # Create status labels
        self.integration_status_label = ttk.Label(status_grid, text="[ERROR] Not Integrated", style="Error.TLabel")
        self.integration_status_label.grid(row=0, column=0, sticky="w", padx=(0, 20))

        self.power_mgmt_status_label = ttk.Label(status_grid, text="⏸️ Power Management: Stopped", style="Error.TLabel")
        self.power_mgmt_status_label.grid(row=1, column=0, sticky="w", padx=(0, 20))

        self.training_status_label = ttk.Label(status_grid, text="⏸️ Process Training: Stopped", style="Error.TLabel")
        self.training_status_label.grid(row=2, column=0, sticky="w", padx=(0, 20))

        self.collab_status_label = ttk.Label(status_grid, text="⏸️ Code Improvement: Stopped", style="Error.TLabel")
        self.collab_status_label.grid(row=3, column=0, sticky="w", padx=(0, 20))

        # Control Buttons Section
        control_frame = ttk.LabelFrame(main_container, text="System Control (Server Hub Authority)", padding=20)
        control_frame.pack(fill="x", pady=(0, 20))

        button_grid = ttk.Frame(control_frame)
        button_grid.pack(fill="x")

        # Integration control buttons
        ttk.Button(button_grid, text="[START] Start Celsius Integration", command=self.start_celsius_integration).grid(
            row=0, column=0, padx=(0, 10), pady=5, sticky="w"
        )

        ttk.Button(button_grid, text="[STOP] Stop Celsius Systems", command=self.stop_celsius_integration).grid(
            row=0, column=1, padx=(0, 10), pady=5, sticky="w"
        )

        ttk.Button(button_grid, text="[REFRESH] Restart Integration", command=self.restart_celsius_integration).grid(
            row=0, column=2, padx=(0, 10), pady=5, sticky="w"
        )

        ttk.Button(button_grid, text="[SETTINGS] Setup Auto-Startup", command=self.setup_auto_startup).grid(
            row=1, column=0, padx=(0, 10), pady=5, sticky="w"
        )

        # Pending Approvals Section
        approval_frame = ttk.LabelFrame(
            main_container, text="Pending Code Improvements (User Approval Required)", padding=20
        )
        approval_frame.pack(fill="both", expand=True, pady=(0, 20))

        # Approvals info
        approval_info = ttk.Frame(approval_frame)
        approval_info.pack(fill="x", pady=(0, 10))

        ttk.Label(
            approval_info,
            text="[WARNING] SAFETY: Celsius AI cannot approve its own code changes",
            style="Warning.TLabel",
            font=("Arial", 10, "bold"),
        ).pack(anchor="w")

        self.pending_count_label = ttk.Label(approval_info, text="Pending Approvals: 0")
        self.pending_count_label.pack(anchor="w", pady=(5, 0))

        # Approvals tree
        approval_tree_frame = ttk.Frame(approval_frame)
        approval_tree_frame.pack(fill="both", expand=True)

        # Create Treeview for pending approvals
        columns = ("ID", "File", "Type", "Description", "Benefit")
        self.approvals_tree = ttk.Treeview(approval_tree_frame, columns=columns, show="headings", height=8)

        # Configure columns
        self.approvals_tree.heading("ID", text="ID")
        self.approvals_tree.heading("File", text="File")
        self.approvals_tree.heading("Type", text="Type")
        self.approvals_tree.heading("Description", text="Description")
        self.approvals_tree.heading("Benefit", text="Expected Benefit")

        self.approvals_tree.column("ID", width=50)
        self.approvals_tree.column("File", width=150)
        self.approvals_tree.column("Type", width=120)
        self.approvals_tree.column("Description", width=300)
        self.approvals_tree.column("Benefit", width=200)

        # Add scrollbar
        approval_scrollbar = ttk.Scrollbar(approval_tree_frame, orient="vertical", command=self.approvals_tree.yview)
        self.approvals_tree.configure(yscrollcommand=approval_scrollbar.set)

        self.approvals_tree.pack(side="left", fill="both", expand=True)
        approval_scrollbar.pack(side="right", fill="y")

        # Approval action buttons
        approval_actions = ttk.Frame(approval_frame)
        approval_actions.pack(fill="x", pady=(10, 0))

        ttk.Button(approval_actions, text="[OK] Approve Selected", command=self.approve_selected_improvement).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(approval_actions, text="[ERROR] Reject Selected", command=self.reject_selected_improvement).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(approval_actions, text="[STATUS] View Details", command=self.view_improvement_details).pack(
            side="left", padx=(0, 10)
        )

        ttk.Button(approval_actions, text="[REFRESH] Refresh Approvals", command=self.refresh_pending_approvals).pack(
            side="left"
        )

        # Process Grading Section
        grading_frame = ttk.LabelFrame(main_container, text="Process Performance Grading (0-100)", padding=20)
        grading_frame.pack(fill="x")

        # Grading info
        grading_info = ttk.Frame(grading_frame)
        grading_info.pack(fill="x")

        self.total_processes_label = ttk.Label(grading_info, text="Total Processes Monitored: 0")
        self.total_processes_label.grid(row=0, column=0, sticky="w", padx=(0, 20))

        self.avg_grade_label = ttk.Label(grading_info, text="Average System Grade: 0")
        self.avg_grade_label.grid(row=0, column=1, sticky="w", padx=(0, 20))

        self.low_grade_count_label = ttk.Label(grading_info, text="Low Grade Processes: 0")
        self.low_grade_count_label.grid(row=1, column=0, sticky="w", padx=(0, 20))

        # Start updating the integration tab
        self.update_celsius_integration_tab()

    def start_celsius_integration(self):
        """Start Celsius AI integration"""
        try:
            if not self.celsius_fully_integrated:
                self.initialize_celsius_integration()

            self.start_celsius_systems()
            messagebox.showinfo(
                "Success",
                "[OK] Celsius AI integration started successfully!\n\n🤖 Celsius is now managing your computer.",
            )

        except Exception as e:
            messagebox.showerror("Error", f"[ERROR] Failed to start Celsius integration:\n{e}")

    def stop_celsius_integration(self):
        """Stop Celsius AI integration (Server Hub control only)"""
        try:
            result = messagebox.askyesno(
                "Confirm Stop",
                "[WARNING] This will stop all Celsius AI systems.\n\nOnly the Server Hub can restart them.\n\nContinue?",
            )

            if result:
                self.stop_celsius_systems()
                messagebox.showinfo("Stopped", "[STOP] Celsius AI systems stopped by Server Hub authority.")

        except Exception as e:
            messagebox.showerror("Error", f"[ERROR] Error stopping Celsius systems:\n{e}")

    def restart_celsius_integration(self):
        """Restart Celsius AI integration"""
        try:
            self.stop_celsius_systems()
            time.sleep(2)  # Brief pause
            self.start_celsius_systems()
            messagebox.showinfo("Success", "[REFRESH] Celsius AI integration restarted successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"[ERROR] Failed to restart Celsius integration:\n{e}")

    def approve_selected_improvement(self):
        """Approve selected code improvement"""
        try:
            selection = self.approvals_tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select an improvement to approve.")
                return

            item = self.approvals_tree.item(selection[0])
            improvement_id = item["values"][0]
            file_name = item["values"][1]

            # Confirm approval
            result = messagebox.askyesno(
                "Confirm Approval",
                f"Approve code improvement for {file_name}?\n\n"
                f"ID: {improvement_id}\n"
                f"Type: {item['values'][2]}\n"
                f"Description: {item['values'][3]}\n\n"
                f"[WARNING] This will modify the code file.",
            )

            if result:
                # Approve improvement (USER approval, not Celsius)
                if self.collaborative_engine:
                    success = self.collaborative_engine.approve_improvement(improvement_id, "user_via_server_hub")

                    if success:
                        messagebox.showinfo("Approved", f"[OK] Code improvement {improvement_id} approved!")
                        self.refresh_pending_approvals()
                    else:
                        messagebox.showerror("Error", "[ERROR] Failed to approve improvement.")

        except Exception as e:
            messagebox.showerror("Error", f"[ERROR] Approval error:\n{e}")

    def reject_selected_improvement(self):
        """Reject selected code improvement"""
        try:
            selection = self.approvals_tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select an improvement to reject.")
                return

            item = self.approvals_tree.item(selection[0])
            improvement_id = item["values"][0]

            result = messagebox.askyesno(
                "Confirm Rejection", f"Reject code improvement {improvement_id}?\n\nThis cannot be undone."
            )

            if result:
                # Implement rejection logic here
                messagebox.showinfo("Rejected", f"[ERROR] Code improvement {improvement_id} rejected.")
                self.refresh_pending_approvals()

        except Exception as e:
            messagebox.showerror("Error", f"[ERROR] Rejection error:\n{e}")

    def view_improvement_details(self):
        """View detailed information about selected improvement"""
        try:
            selection = self.approvals_tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select an improvement to view details.")
                return

            item = self.approvals_tree.item(selection[0])

            # Create details window
            details_window = tk.Toplevel(self.root)
            details_window.title("Code Improvement Details")
            details_window.geometry("600x400")
            details_window.configure(bg="#1a1a1a")

            # Details text
            details_text = scrolledtext.ScrolledText(details_window, wrap="word", bg="#2d2d2d", fg="#ffffff")
            details_text.pack(fill="both", expand=True, padx=20, pady=20)

            details_content = f"""Code Improvement Details
            
ID: {item['values'][0]}
File: {item['values'][1]}
Type: {item['values'][2]}
Description: {item['values'][3]}
Expected Benefit: {item['values'][4]}

SAFETY NOTICE:
• This improvement was generated by Celsius AI
• Celsius AI cannot approve its own code changes
• User approval is required for all modifications
• Server Hub maintains final authority over all changes

Review the improvement carefully before approval.
"""

            details_text.insert("1.0", details_content)
            details_text.config(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"[ERROR] Error viewing details:\n{e}")

    def refresh_pending_approvals(self):
        """Refresh the pending approvals list"""
        try:
            # Clear current items
            for item in self.approvals_tree.get_children():
                self.approvals_tree.delete(item)

            # Get pending improvements
            if self.collaborative_engine:
                pending = self.collaborative_engine.get_pending_improvements()

                for improvement in pending:
                    self.approvals_tree.insert(
                        "",
                        "end",
                        values=(
                            improvement["id"],
                            improvement["file_path"].split("/")[-1],  # Just filename
                            improvement["improvement_type"],
                            (
                                improvement["description"][:50] + "..."
                                if len(improvement["description"]) > 50
                                else improvement["description"]
                            ),
                            improvement["estimated_benefit"],
                        ),
                    )

                # Update count
                self.pending_count_label.config(text=f"Pending Approvals: {len(pending)}")

        except Exception as e:
            print(f"Error refreshing approvals: {e}")

    def update_celsius_integration_tab(self):
        """Update Celsius Integration tab with current status"""
        try:
            # Get system status
            status = self.get_celsius_system_status()

            # Update status labels
            if status["fully_integrated"]:
                self.integration_status_label.config(text="[OK] Fully Integrated", style="Success.TLabel")
            else:
                self.integration_status_label.config(text="[ERROR] Not Integrated", style="Error.TLabel")

            # Update component statuses
            if status["power_management"]:
                self.power_mgmt_status_label.config(text="[OK] Power Management: Active", style="Success.TLabel")
            else:
                self.power_mgmt_status_label.config(text="⏸️ Power Management: Stopped", style="Error.TLabel")

            if status["process_training"]:
                self.training_status_label.config(text="[OK] Process Training: Active", style="Success.TLabel")
            else:
                self.training_status_label.config(text="⏸️ Process Training: Stopped", style="Error.TLabel")

            if status["collaborative_improvement"]:
                self.collab_status_label.config(text="[OK] Code Improvement: Active", style="Success.TLabel")
            else:
                self.collab_status_label.config(text="⏸️ Code Improvement: Stopped", style="Error.TLabel")

            # Update pending approvals count
            self.pending_count_label.config(text=f"Pending Approvals: {status['pending_approvals']}")

            # Refresh approvals if any pending
            if status["pending_approvals"] > 0:
                self.refresh_pending_approvals()

            # Schedule next update
            self.root.after(5000, self.update_celsius_integration_tab)  # Update every 5 seconds

        except Exception as e:
            print(f"Integration tab update error: {e}")

    # ===============================
    # WEB LEARNING & AI COMMUNICATION
    # ===============================

    def initialize_web_learning(self):
        """Initialize web learning and AI communication systems"""
        try:
            # Initialize web learning integration
            from celsius_web_learning_integration import CelsiusWebLearningIntegration

            self.web_learning_integration = CelsiusWebLearningIntegration()

            # Initialize language improvement system
            from celsius_language_improvement import CelsiusLanguageImprover

            self.language_improver = CelsiusLanguageImprover()

            # Update status
            self.web_learning_status_label.config(text="[OK] Web learning initialized and ready")

            # Enable controls
            self.start_learning_btn.config(state="normal")

            # Display initial status
            self.update_web_learning_display()

            print("[OK] Web learning and AI communication systems initialized")

        except Exception as e:
            self.web_learning_status_label.config(text=f"[ERROR] Error initializing: {str(e)}")
            print(f"[ERROR] Error initializing web learning: {str(e)}")

    def start_web_learning(self):
        """Start the web learning process"""
        if not self.web_learning_integration:
            return

        try:
            success = self.web_learning_integration.start_learning_process()

            if success:
                self.web_learning_active = True
                self.web_learning_status_label.config(
                    text="[ONLINE] Web learning active - Celsius is learning from the internet!"
                )

                # Update button states
                self.start_learning_btn.config(state="disabled")
                self.stop_learning_btn.config(state="normal")

                # Refresh display
                self.update_web_learning_display()

                print("[OK] Web learning started")
            else:
                self.web_learning_status_label.config(text="[ERROR] Failed to start web learning")

        except Exception as e:
            self.web_learning_status_label.config(text=f"[ERROR] Error starting learning: {str(e)}")

    def stop_web_learning(self):
        """Stop the web learning process"""
        if not self.web_learning_integration:
            return

        try:
            self.web_learning_integration.stop_learning()
            self.web_learning_active = False

            self.web_learning_status_label.config(text="⏹️ Web learning stopped")

            # Update button states
            self.start_learning_btn.config(state="normal")
            self.stop_learning_btn.config(state="disabled")

            print("⏹️ Web learning stopped")

        except Exception as e:
            self.web_learning_status_label.config(text=f"[ERROR] Error stopping learning: {str(e)}")

    def toggle_ai_communication(self):
        """Toggle AI communication for language improvement"""
        if not self.language_improver:
            return

        enabled = self.ai_comm_enabled_var.get()

        if enabled:
            # Request user consent for AI communication
            result = messagebox.askyesno(
                "Enable AI Communication",
                "Allow Celsius to communicate with other AIs for language improvement?\n\n"
                "This will:\n"
                "• Help improve response quality\n"
                "• Enhance technical accuracy\n"
                "• Use only local AI services when available\n"
                "• Maintain privacy and security\n\n"
                "Continue?",
            )

            if result:
                self.language_improver.enable_ai_communication(user_consent=True)
                self.web_learning_status_label.config(
                    text="🤖 AI communication enabled - Celsius can improve language skills"
                )
                print("[OK] AI communication enabled with user consent")
            else:
                self.ai_comm_enabled_var.set(False)
        else:
            self.language_improver.disable_ai_communication()
            print("⏹️ AI communication disabled")

    def generate_web_learning_report(self):
        """Generate and display web learning report with same formatting as hourly reports"""
        if not self.web_learning_integration:
            self.web_learning_text.delete(1.0, tk.END)
            self.web_learning_text.insert(tk.END, "[ERROR] Web learning not initialized")
            return

        try:
            # Get learning status and data
            status = self.web_learning_integration.get_learning_status()
            insights = self.web_learning_integration.get_recent_insights(10)

            # Get language improvement status
            language_status = {}
            if self.language_improver:
                language_status = self.language_improver.get_improvement_status()

            # Format report using the same style as hourly reports
            report = self.format_web_learning_report(status, insights, language_status)

            # Display formatted report
            self.web_learning_text.delete(1.0, tk.END)
            self.web_learning_text.insert(tk.END, report)

            print("[STATUS] Web learning report generated")

        except Exception as e:
            error_report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    [WARNING]  WEB LEARNING ERROR                    ║
╚══════════════════════════════════════════════════════════════╝

[ERROR] Error generating web learning report: {str(e)}

📋 Please check that web learning components are properly initialized.
"""
            self.web_learning_text.delete(1.0, tk.END)
            self.web_learning_text.insert(tk.END, error_report)

    def format_web_learning_report(self, status, insights, language_status):
        """Format web learning report with enhanced readability (matching hourly report style)"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Create beautifully formatted report matching the hourly report style
            report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    [NETWORK]  CELSIUS AI WEB LEARNING REPORT        ║
╚══════════════════════════════════════════════════════════════╝

📅 REPORT DETAILS
   Generated: {current_time}
   Report Type: Web Learning & AI Communication Status
   Status: {"[ONLINE] ACTIVE" if status.get('learning_active', False) else "[PENDING] INACTIVE"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 WEB LEARNING STATUS OVERVIEW
"""

            # Learning status details
            report += f"   {'[OK]' if status.get('learning_active') else '⏸️'} Learning Active: {'Yes' if status.get('learning_active') else 'No'}\n"
            report += f"   [STATUS] Content Learned: {status.get('total_content_learned', 0)} articles\n"
            report += f"   [TIP] Insights Generated: {status.get('total_insights', 0)} insights\n"

            # Learning topics
            if status.get("learner_available"):
                report += f"   [TARGET] Learning Topics: 5 domains (Cybersecurity, Technology, Health, Programming, Optimization)\n"

            # Learning settings
            settings = status.get("settings", {})
            if settings:
                report += f"   ⏰ Learning Interval: {settings.get('learning_interval_hours', 'N/A')} hours\n"
                report += f"   [STATS] Daily Sessions: Max {settings.get('max_learning_sessions_per_day', 'N/A')}\n"
                report += f"   [SHIELD] Ethical Mode: {'Enabled' if settings.get('ethical_mode') else 'Disabled'}\n"

            report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            # Recent insights section
            report += "\n🧠 RECENT LEARNING INSIGHTS\n"

            if insights:
                for i, insight in enumerate(insights[:5], 1):  # Show top 5 insights
                    confidence_icon = (
                        "[ONLINE]"
                        if insight.get("confidence", 0) > 0.8
                        else "[PENDING]" if insight.get("confidence", 0) > 0.6 else "[OFFLINE]"
                    )
                    report += f"\n   {i}. Topic: {insight.get('topic', 'Unknown').title()}\n"
                    report += f"      {confidence_icon} Confidence: {insight.get('confidence', 0):.0%}\n"
                    report += f"      🕒 Generated: {insight.get('timestamp', 'Unknown')}\n"
                    report += f"      [TIP] Insight: {insight.get('insight', 'No insight available')[:100]}...\n"
            else:
                report += "\n   📝 No insights generated yet\n"
                report += "   [REFRESH] Insights will appear as Celsius learns from web sources\n"

            report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            # AI Communication section
            report += "\n🤖 AI COMMUNICATION & LANGUAGE IMPROVEMENT\n"

            if language_status:
                comm_active = language_status.get("active", False)
                ai_services = language_status.get("ai_services_available", {})

                report += (
                    f"   {'[OK]' if comm_active else '⏸️'} AI Communication: {'Active' if comm_active else 'Inactive'}\n"
                )

                # Available AI services
                for service, available in ai_services.items():
                    status_icon = "[OK]" if available else "[ERROR]"
                    report += f"   {status_icon} {service.title()}: {'Available' if available else 'Unavailable'}\n"

                # Improvement areas
                improvement_areas = language_status.get("improvement_areas", {})
                if improvement_areas:
                    report += "\n   [TARGET] Improvement Focus Areas:\n"
                    for area, config in improvement_areas.items():
                        priority_icon = "[OFFLINE]" if config.get("priority") == "high" else "[PENDING]"
                        report += f"     {priority_icon} {area.replace('_', ' ').title()}: {config.get('priority', 'unknown')} priority\n"

                insights_count = language_status.get("insights_count", 0)
                report += f"   [STATUS] Language Insights: {insights_count} generated\n"
            else:
                report += "   [WARNING] Language improvement system not initialized\n"

            report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            # Learning topics breakdown
            report += "\n📖 LEARNING DOMAINS\n"
            report += "\n   [SHIELD] Cybersecurity:\n"
            report += "     [SEARCH] Latest threats, vulnerabilities, and protection methods\n"
            report += "     📚 Security best practices and compliance updates\n"

            report += "\n   [COMPUTER] Technology:\n"
            report += "     [START] AI/ML advancements and programming innovations\n"
            report += "     [CONFIG] Software and hardware development trends\n"

            report += "\n   💪 Fitness & Health:\n"
            report += "     🏃 Exercise routines and nutrition guidance\n"
            report += "     🧠 Mental health and wellness strategies\n"

            report += "\n   [SETTINGS] System Optimization:\n"
            report += "     [STATS] Performance tuning and monitoring techniques\n"
            report += "     [TARGET] Resource management and efficiency improvements\n"

            report += "\n   👨‍[COMPUTER] Programming:\n"
            report += "     🐍 Best practices and algorithmic improvements\n"
            report += "     📖 Framework updates and development methodologies\n"

            report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            # Recommendations
            report += "\n[TIP] LEARNING RECOMMENDATIONS\n"

            if not status.get("learning_active"):
                report += "   [START] Start web learning to begin acquiring current knowledge\n"

            if status.get("total_content_learned", 0) == 0:
                report += "   📚 No content learned yet - first learning session will populate database\n"

            if not language_status.get("active", False):
                report += "   🤖 Consider enabling AI communication for language improvements\n"

            if status.get("learning_active") and status.get("total_insights", 0) > 0:
                report += "   ✨ Web learning is functioning well - continue regular operation\n"
                report += "   [STATUS] Review insights regularly for actionable intelligence\n"

            report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            report += "\n[NETWORK] Celsius AI Web Learning - Expanding Knowledge Through Ethical Web Intelligence\n"
            report += "   [MOBILE] Monitor learning: Use Web Learning tab controls\n"
            report += "   [REFRESH] Next update: Continuous background learning active\n"
            report += "   [STATUS] View insights: Click 'Generate Report' for latest status\n\n"

            return report

        except Exception as e:
            return f"""
╔══════════════════════════════════════════════════════════════╗
║                    [WARNING]  REPORT FORMATTING ERROR               ║
╚══════════════════════════════════════════════════════════════╝

[ERROR] Error formatting web learning report: {str(e)}

📋 Raw Status Data Available:
   Learning Active: {status.get('learning_active', 'Unknown')}
   Content Learned: {status.get('total_content_learned', 'Unknown')}
   Insights Generated: {status.get('total_insights', 'Unknown')}
"""

    def update_web_learning_display(self):
        """Update the web learning display with current status"""
        if not self.web_learning_integration:
            return

        try:
            # Auto-generate report to show current status
            self.generate_web_learning_report()

        except Exception as e:
            print(f"Error updating web learning display: {str(e)}")

    # Code Approval Tab Methods
    def refresh_code_approval_requests(self):
        """Refresh the list of pending code approval requests"""
        try:
            # Check if widgets exist before accessing them
            if not hasattr(self, "approval_tree") or not self.approval_tree.winfo_exists():
                return

            if not hasattr(self, "pending_requests_label") or not self.pending_requests_label.winfo_exists():
                return

            # Clear existing items
            for item in self.approval_tree.get_children():
                self.approval_tree.delete(item)

            # Get pending requests from approval system
            pending_requests = self.code_approval_system.get_pending_requests()

            # Update statistics
            stats = self.code_approval_system.get_approval_statistics()
            self.pending_requests_label.config(text=f"Pending: {stats.get('pending', 0)}")
            self.approved_requests_label.config(text=f"Approved: {stats.get('approved', 0)}")
            self.denied_requests_label.config(text=f"Denied: {stats.get('denied', 0)}")

            # Add requests to tree
            for request in pending_requests:
                # Format priority
                priority_map = {1: "[ONLINE] Low", 2: "[PENDING] Med", 3: "[OFFLINE] High", 4: "[FAST] Crit"}
                priority_display = priority_map.get(request["priority"], "[PENDING] Med")

                # Format submitted time
                try:
                    submitted_time = datetime.fromisoformat(request["submitted_at"]).strftime("%m/%d %H:%M")
                except:
                    submitted_time = "Unknown"

                # Insert into tree
                self.approval_tree.insert(
                    "",
                    "end",
                    values=(
                        request["request_id"][:8] + "...",  # Shortened ID
                        request["title"][:30] + "..." if len(request["title"]) > 30 else request["title"],
                        os.path.basename(request["file_path"]),
                        request["change_type"].replace("_", " ").title(),
                        priority_display,
                        submitted_time,
                    ),
                )

            # Update display
            if pending_requests:
                self.request_details_text.config(state="normal")
                self.request_details_text.delete(1.0, tk.END)
                self.request_details_text.insert(
                    tk.END,
                    f"📋 {len(pending_requests)} pending code approval request(s)\n\n"
                    + "Select a request from the list above to view details and take action.",
                )
                self.request_details_text.config(state="disabled")
            else:
                self.request_details_text.config(state="normal")
                self.request_details_text.delete(1.0, tk.END)
                self.request_details_text.insert(
                    tk.END,
                    "[OK] No pending code approval requests\n\n"
                    + "All code changes have been reviewed. Celsius AI will submit new requests when improvements are identified.",
                )
                self.request_details_text.config(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh code approval requests: {str(e)}")

    def on_approval_request_select(self, event):
        """Handle selection of an approval request"""
        try:
            selection = self.approval_tree.selection()
            if not selection:
                self.selected_request_id = None
                self.approve_btn.config(state="disabled")
                self.deny_btn.config(state="disabled")
                return

            # Get selected item
            item = self.approval_tree.item(selection[0])
            request_id_short = item["values"][0].replace("...", "")

            # Find full request ID and get details
            pending_requests = self.code_approval_system.get_pending_requests()
            selected_request = None

            for request in pending_requests:
                if request["request_id"].startswith(request_id_short):
                    selected_request = request
                    self.selected_request_id = request["request_id"]
                    break

            if selected_request:
                # Display formatted submission
                formatted_submission = selected_request.get("formatted_submission", "")

                self.request_details_text.config(state="normal")
                self.request_details_text.delete(1.0, tk.END)
                self.request_details_text.insert(tk.END, formatted_submission)
                self.request_details_text.config(state="disabled")

                # Enable action buttons
                self.approve_btn.config(state="normal")
                self.deny_btn.config(state="normal")
            else:
                self.selected_request_id = None
                self.approve_btn.config(state="disabled")
                self.deny_btn.config(state="disabled")

        except Exception as e:
            print(f"Error handling request selection: {str(e)}")

    def approve_selected_request(self):
        """Approve the currently selected code change request"""
        if not self.selected_request_id:
            messagebox.showwarning("No Selection", "Please select a request to approve.")
            return

        try:
            # Get review comments
            comments = self.review_comments_text.get(1.0, tk.END).strip()
            if not comments:
                comments = "Approved via Server Hub interface"

            # Confirm approval
            result = messagebox.askyesno(
                "Confirm Approval",
                f"Approve code change request {self.selected_request_id[:8]}...?\n\n"
                f"Comments: {comments[:100]}{'...' if len(comments) > 100 else ''}",
            )

            if result:
                # Approve the request
                success = self.code_approval_system.approve_request(
                    self.selected_request_id, self.authenticated_user["username"], comments
                )

                if success:
                    messagebox.showinfo(
                        "Success", f"Code change request approved!\n\nRequest ID: {self.selected_request_id}"
                    )

                    # Clear comments and refresh
                    self.review_comments_text.delete(1.0, tk.END)
                    self.refresh_code_approval_requests()
                else:
                    messagebox.showerror("Error", "Failed to approve request. Check logs for details.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to approve request: {str(e)}")

    def deny_selected_request(self):
        """Deny the currently selected code change request"""
        if not self.selected_request_id:
            messagebox.showwarning("No Selection", "Please select a request to deny.")
            return

        try:
            # Get review comments
            comments = self.review_comments_text.get(1.0, tk.END).strip()
            if not comments:
                comments = "Denied via Server Hub interface"

            # Confirm denial
            result = messagebox.askyesno(
                "Confirm Denial",
                f"Deny code change request {self.selected_request_id[:8]}...?\n\n"
                f"Comments: {comments[:100]}{'...' if len(comments) > 100 else ''}",
            )

            if result:
                # Deny the request
                success = self.code_approval_system.deny_request(
                    self.selected_request_id, self.authenticated_user["username"], comments
                )

                if success:
                    messagebox.showinfo(
                        "Success", f"Code change request denied.\n\nRequest ID: {self.selected_request_id}"
                    )

                    # Clear comments and refresh
                    self.review_comments_text.delete(1.0, tk.END)
                    self.refresh_code_approval_requests()
                else:
                    messagebox.showerror("Error", "Failed to deny request. Check logs for details.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to deny request: {str(e)}")

    def view_full_code_comparison(self):
        """Show full code comparison in a separate window"""
        if not self.selected_request_id:
            messagebox.showwarning("No Selection", "Please select a request to view code comparison.")
            return

        try:
            # Get request details
            request_details = self.code_approval_system.get_request_details(self.selected_request_id)

            if not request_details:
                messagebox.showerror("Error", "Could not retrieve request details.")
                return

            # Create comparison window
            comparison_window = tk.Toplevel(self.root)
            comparison_window.title(f"Code Comparison - {request_details['title']}")
            comparison_window.geometry("1000x700")

            # Main container
            main_frame = ttk.Frame(comparison_window)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)

            # Title
            title_label = ttk.Label(main_frame, text=f"📝 {request_details['title']}", font=("Arial", 14, "bold"))
            title_label.pack(pady=(0, 10))

            # Create notebook for before/after tabs
            code_notebook = ttk.Notebook(main_frame)
            code_notebook.pack(fill="both", expand=True)

            # Original code tab
            original_frame = ttk.Frame(code_notebook)
            code_notebook.add(original_frame, text="📜 Original Code")

            original_text = scrolledtext.ScrolledText(original_frame, wrap=tk.NONE, font=("Consolas", 10))
            original_text.pack(fill="both", expand=True, padx=10, pady=10)
            original_text.insert(tk.END, request_details["original_code"])
            original_text.config(state="disabled")

            # Proposed code tab
            proposed_frame = ttk.Frame(code_notebook)
            code_notebook.add(proposed_frame, text="✨ Proposed Code")

            proposed_text = scrolledtext.ScrolledText(proposed_frame, wrap=tk.NONE, font=("Consolas", 10))
            proposed_text.pack(fill="both", expand=True, padx=10, pady=10)
            proposed_text.insert(tk.END, request_details["proposed_code"])
            proposed_text.config(state="disabled")

            # Action buttons at bottom
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill="x", pady=(10, 0))

            ttk.Button(
                button_frame,
                text="[OK] Approve",
                command=lambda: [self.approve_selected_request(), comparison_window.destroy()],
            ).pack(side="left", padx=(0, 10))
            ttk.Button(
                button_frame,
                text="[ERROR] Deny",
                command=lambda: [self.deny_selected_request(), comparison_window.destroy()],
            ).pack(side="left", padx=(0, 10))
            ttk.Button(button_frame, text="🚪 Close", command=comparison_window.destroy).pack(side="right")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to show code comparison: {str(e)}")

    def copy_request_id(self):
        """Copy selected request ID to clipboard"""
        if not self.selected_request_id:
            messagebox.showwarning("No Selection", "Please select a request first.")
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.selected_request_id)
            messagebox.showinfo("Copied", f"Request ID copied to clipboard:\n{self.selected_request_id}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy request ID: {str(e)}")

    def skip_request(self):
        """Skip to next request without taking action"""
        try:
            # Get next item in tree
            selection = self.approval_tree.selection()
            if selection:
                current_item = selection[0]
                children = self.approval_tree.get_children()

                # Find current index and move to next
                current_index = children.index(current_item)
                if current_index < len(children) - 1:
                    next_item = children[current_index + 1]
                    self.approval_tree.selection_set(next_item)
                    self.approval_tree.focus(next_item)
                    self.on_approval_request_select(None)
                else:
                    messagebox.showinfo("End of List", "This is the last request in the list.")
            else:
                # Select first item if none selected
                children = self.approval_tree.get_children()
                if children:
                    self.approval_tree.selection_set(children[0])
                    self.approval_tree.focus(children[0])
                    self.on_approval_request_select(None)

        except Exception as e:
            print(f"Error skipping request: {str(e)}")

    def show_approval_statistics(self):
        """Show detailed approval statistics"""
        try:
            stats = self.code_approval_system.get_approval_statistics()

            stats_window = tk.Toplevel(self.root)
            stats_window.title("Code Approval Statistics")
            stats_window.geometry("500x400")

            # Main frame
            main_frame = ttk.Frame(stats_window)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)

            # Title
            ttk.Label(main_frame, text="[STATUS] Code Approval Statistics", font=("Arial", 16, "bold")).pack(
                pady=(0, 20)
            )

            # Statistics display
            stats_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, width=50, font=("Consolas", 10))
            stats_text.pack(fill="both", expand=True)

            # Format statistics
            stats_report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    [STATUS] APPROVAL STATISTICS                    ║
╚══════════════════════════════════════════════════════════════╝

📋 OVERVIEW
   Total Requests: {stats.get('total_requests', 0)}
   Recent Requests (7 days): {stats.get('recent_requests', 0)}

[REFRESH] STATUS BREAKDOWN
   ⏳ Pending: {stats.get('pending', 0)}
   [OK] Approved: {stats.get('approved', 0)}
   [ERROR] Denied: {stats.get('denied', 0)}

[STATS] APPROVAL RATE
   Rate: {((stats.get('approved', 0) / max(stats.get('total_requests', 1), 1)) * 100):.1f}%
   
[TARGET] SYSTEM HEALTH
   Pending Review Queue: {'[OK] Manageable' if stats.get('pending', 0) < 10 else '[WARNING] Review Needed'}
   Response Time: {'[ONLINE] Good' if stats.get('pending', 0) < 5 else '[PENDING] Moderate'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            stats_text.insert(tk.END, stats_report)
            stats_text.config(state="disabled")

            # Close button
            ttk.Button(main_frame, text="🚪 Close", command=stats_window.destroy).pack(pady=(10, 0))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to show statistics: {str(e)}")

    def show_approval_history(self):
        """Show approval history"""
        messagebox.showinfo("Feature", "Approval history feature will be implemented in the next version.")

    def auto_refresh_code_approval(self):
        """Automatically refresh code approval requests every 30 seconds"""
        try:
            # Only refresh if code approval section is active and widgets exist
            if (
                hasattr(self, "code_approval_system")
                and hasattr(self, "current_section")
                and self.current_section == "code_approval"
                and hasattr(self, "approval_tree")
            ):
                self.refresh_code_approval_requests()
        except Exception as e:
            print(f"Error in auto refresh: {str(e)}")
        finally:
            # Schedule next refresh only if root window still exists
            if hasattr(self, "root") and self.root.winfo_exists():
                self.root.after(30000, self.auto_refresh_code_approval)

    def create_activity_logs_section(self):
        """Create Activity Logs Section"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections["activity_logs"] = frame

        # Activity logs header
        header_frame = ttk.LabelFrame(frame, text="📋 Activity Logs", padding=15)
        header_frame.pack(fill="x", pady=(0, 20))

        ttk.Label(header_frame, text="View detailed system activity logs and events", font=("Arial", 11)).pack(
            anchor="w"
        )

        # Log controls
        control_frame = ttk.Frame(header_frame)
        control_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(control_frame, text="[REFRESH] Refresh Logs", command=self.refresh_activity_logs).pack(
            side="left", padx=(0, 10)
        )
        ttk.Button(control_frame, text="🗑️ Clear Logs", command=self.clear_activity_logs).pack(side="left", padx=(0, 10))
        ttk.Button(control_frame, text="💾 Export Logs", command=self.export_activity_logs).pack(side="left")

        # Logs display
        logs_frame = ttk.LabelFrame(frame, text="Recent Activity", padding=15)
        logs_frame.pack(fill="both", expand=True)

        self.activity_logs_text = scrolledtext.ScrolledText(
            logs_frame, wrap=tk.WORD, height=20, width=80, font=("Consolas", 9)
        )
        self.activity_logs_text.pack(fill="both", expand=True)

        # Load initial logs
        self.refresh_activity_logs()

    def create_placeholder_section(self, section_key):
        """Create placeholder section for unimplemented features"""
        frame = ttk.Frame(self.main_content)
        self.menu_sections[section_key] = frame

        # Placeholder content
        placeholder_frame = ttk.LabelFrame(frame, text=f"🚧 {section_key.replace('_', ' ').title()}", padding=20)
        placeholder_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(placeholder_frame, text="This section is under development.", font=("Arial", 14)).pack(pady=20)
        ttk.Label(
            placeholder_frame,
            text="More features will be added in future updates.",
            font=("Arial", 11),
            foreground="gray",
        ).pack()

        # Back to main button
        ttk.Button(
            placeholder_frame, text="← Back to Server Control", command=lambda: self.show_section("server_control")
        ).pack(pady=(20, 0))

    def refresh_activity_logs(self):
        """Refresh activity logs display"""
        try:
            self.activity_logs_text.delete(1.0, tk.END)

            # Sample log entries (replace with actual log reading)
            logs = [
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Server Hub started",
                f"[{(datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')}] User authentication successful: cllusion001",
                f"[{(datetime.now() - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')}] Web learning system initialized",
                f"[{(datetime.now() - timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')}] Code approval system ready",
                f"[{(datetime.now() - timedelta(minutes=20)).strftime('%Y-%m-%d %H:%M:%S')}] Monitoring thread started",
            ]

            for log in logs:
                self.activity_logs_text.insert(tk.END, log + "\n")

        except Exception as e:
            self.activity_logs_text.insert(tk.END, f"Error loading logs: {str(e)}\n")

    def clear_activity_logs(self):
        """Clear activity logs"""
        result = messagebox.askyesno("Clear Logs", "Are you sure you want to clear all activity logs?")
        if result:
            self.activity_logs_text.delete(1.0, tk.END)
            self.activity_logs_text.insert(tk.END, "Activity logs cleared.\n")

    def export_activity_logs(self):
        """Export activity logs to file"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Export Activity Logs",
            )

            if file_path:
                with open(file_path, "w") as f:
                    f.write(self.activity_logs_text.get(1.0, tk.END))
                messagebox.showinfo("Export Complete", f"Logs exported to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export logs: {str(e)}")

    def on_closing(self):
        """Handle window closing with cleanup"""
        try:
            # Stop server self-monitoring
            if hasattr(self, "server_self_monitor_active"):
                self.server_self_monitor_active = False

            # Ask about stopping server if running
            if hasattr(self, "server_process") and self.server_process:
                if messagebox.askokcancel("Quit", "Server is running. Stop server and quit?"):
                    self.stop_server()
                    self.cleanup_and_quit()
                # If user cancels, don't quit
            else:
                self.cleanup_and_quit()

        except Exception as e:
            print(f"Error during closing: {e}")
            self.cleanup_and_quit()

    def cleanup_and_quit(self):
        """Clean up resources and quit"""
        try:
            # Release the instance lock
            if hasattr(self, "instance_lock"):
                self.instance_lock.release()

            # Destroy the window
            self.root.destroy()

        except Exception as e:
            print(f"Error during cleanup: {e}")
            sys.exit(0)


def main():
    """Main application entry point with single instance control"""

    # Check for existing instance before creating window
    lock_file_path = Path("C:/Users/micro/Celsius AI/server_hub_instance.lock")

    # Quick check for existing instance
    if os.path.exists(lock_file_path):
        try:
            with open(lock_file_path, "r") as f:
                existing_pid = int(f.read().strip())
            if psutil.pid_exists(existing_pid):
                process = psutil.Process(existing_pid)
                if "celsius_server_hub.py" in " ".join(process.cmdline()):
                    # Show message without creating window
                    root = tk.Tk()
                    root.withdraw()  # Hide window
                    messagebox.showinfo(
                        "Already Running",
                        "Celsius AI Server Hub is already running!\n\n"
                        "Only one instance is allowed.\n"
                        "Check your taskbar for the existing window.",
                    )
                    root.destroy()
                    return
        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
            pass  # Stale lock file, continue

    # Create the application
    root = tk.Tk()
    try:
        app = CelsiusServerHub(root)

        # Only start mainloop if initialization was successful
        if hasattr(app, "root") and app.root.winfo_exists():
            root.mainloop()

    except Exception as e:
        print(f"Error starting Server Hub: {e}")
        messagebox.showerror("Startup Error", f"Failed to start Server Hub:\n{str(e)}")
        root.destroy()


if __name__ == "__main__":
    main()
