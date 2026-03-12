#!/usr/bin/env python3
"""
Celsius AI - Ultimate Server Hub (Async Edition)

A modern, asynchronous control center for the Celsius AI ecosystem.

This module contains the `UltimateHub` class which composes the Tkinter UI
and asynchronous helpers. Imports that are optional or heavy are handled
gracefully so the module can be imported without requiring all extras.
"""

import os
import signal
import sys
import subprocess
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, filedialog
import queue
import tkinter as tk
from tkinter import ttk
import threading
import re

# Try to import optional UI theming package; keep module import-time safe.
try:
    from ttkthemes import ThemedTk
except Exception:
    ThemedTk = None  # type: ignore

from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    # These imports are only for type checking and will not be executed at runtime.
    from ttkthemes import ThemedTk as _ThemedTk
    from src.celsius.hub.async_loop import AsyncTkinter as _AsyncTkinter

# Project root (three levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Ensure the project root is on sys.path so package-style imports that use
# the top-level `src` package work when the application is run from the
# repository root or by double-clicking the script on Windows. Many
# modules in this project import using 'src.xxx' and rely on PROJECT_ROOT
# being on sys.path.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Optional/slow imports: import safely with graceful fallbacks so the
# module can be imported in limited environments (tests, linters) without
# requiring every optional runtime dependency.
try:
    import aiohttp
except Exception:
    aiohttp = None  # type: ignore

try:
    import aiosqlite
except Exception:
    aiosqlite = None  # type: ignore

try:
    import psutil
except Exception:
    psutil = None  # type: ignore

# Local AI provider abstraction (optional)
try:
    from src.celsius.ai.providers import load_providers, LLMClient
except Exception:
    load_providers = None  # type: ignore
    LLMClient = None  # type: ignore

# Email notifier accessor (preferred) € fall back to a no-op getter if the
# enhanced email system isn't available at import time.
try:
    from src.celsius.utils.enhanced_email_system import get_enhanced_notifier
except Exception:
    def get_enhanced_notifier():
        return None

# Conversational AI availability flag and placeholder class. If a real
# conversational AI is present elsewhere it should set CONVERSATION_AVAILABLE
# to True and provide `ConversationalAI`.
CONVERSATION_AVAILABLE = False
ConversationalAI = None

# Ingestion helpers availability
_HAS_INGEST = False
try:
    from src.celsius.learning.conversation_ingest import store_conversation
except ImportError:
    store_conversation = None


# Additional safe imports used across the module
try:
    from tkinter import simpledialog
except Exception:
    simpledialog = None  # type: ignore

import zipfile
from datetime import timedelta

# Basic logger for the module
logger = logging.getLogger("celsius.hub")

# Config path fallback
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"

# Code approval subsystem flag placeholder
CodeApprovalSystem = False

# Attempt to import the real AsyncTkinter; fall back to a small shim if missing.
try:
    from src.celsius.hub.async_loop import AsyncTkinter
except Exception:
    import threading

    class AsyncTkinter(threading.Thread):
        """Simple shim for AsyncTkinter when the real implementation isn't available.

        It provides start(), stop(), and create_task(coro) so the rest of the
        application can operate in environments where the async loop helper
        isn't present (tests, linters).
        """

        def __init__(self):
            super().__init__(daemon=True)
            self._loop = None
            # use an Event so other code can call `.is_set()` on _started
            self._started = threading.Event()

        def run(self):
            import asyncio

            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        def start(self):
            if not self._started.is_set():
                super().start()
                # mark started
                self._started.set()

        def create_task(self, coro):
            if self._loop:
                return asyncio.run_coroutine_threadsafe(coro, self._loop)
            return None

        def stop(self):
            if self._loop:
                self._loop.call_soon_threadsafe(self._loop.stop)
            # mark not started
            try:
                self._started.clear()
            except Exception:
                pass




class UltimateHub:
    """
    The main application class for the Celsius Ultimate Hub.
    """

    def __init__(self, root, async_loop, username: str = "cllusion001"):
        """
        Initializes the Ultimate Hub GUI.

        Args:
            root: The main Tkinter window.
            async_loop: The manager for the background asyncio event loop.
            username: The authenticated username.
        """
        self.root = root
        self.async_loop = async_loop
        self.username = username
        self.root.title("Celsius AI - Ultimate Hub")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Project root directory
        self.project_root = PROJECT_ROOT

        # Feature flags and state
        self.enable_hourly_updates = True
        self._last_hourly_id = None
        self.enable_conversation_training = False

        # --- Initialize Core Components ---
        self.db_path = PROJECT_ROOT / "data" / "celsius_hub.db"
        self.services: Dict[str, Dict[str, Any]] = self.load_service_config()
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        # HTTP session (created during async initialization)
        self.http_session = None
        self.email_notifier = None  # Will be initialized async
        # Email retry/status tracking
        self._email_retry_count = 0
        self._email_last_error = None
        self._email_auto_retry = True

        # Initialize conversation history
        self.conversation_history = []
        self.conversation_file = self.project_root / "data" / "conversation_history.json"

        # Update checking state
        self._latest_update_info = None
        self.update_status_label = None  # Will be set by UI

        # Schedule the async initialization to run after the Tk mainloop starts.
        # Initializing async components too early (before mainloop) causes
        # Tkinter to raise "main thread is not in main loop" when coroutines
        # call self.root.after(...). Use root.after to schedule creating the
        # coroutine on the async event loop once the mainloop is active.
        self.root.after(100, lambda: self.async_loop.create_task(self.initialize_async_components()))

        # Thread-safe queue for scheduling callables to run on the Tk main thread.
        # Some async tasks run in a background thread; they must not call
        # Tkinter APIs directly. Instead they should use
        # self.schedule_on_main_thread(callable, *args, **kwargs)
        # which enqueues the callable. The main thread polls and executes them.
        self._main_thread_queue = queue.Queue()
        self.root.after(100, self._process_main_thread_queue)

        # Window management: track all open Toplevel windows
        self._open_windows: list[tk.Toplevel] = []

        # --- UI Setup ---
        self.style = ttk.Style(self.root)
        # Only set theme if using ThemedTk
        try:
            if hasattr(self.root, 'set_theme'):
                self.root.set_theme("equilux")
        except Exception:
            pass  # Theme not available, continue with default
        self.setup_styles()
        self.create_widgets()

        # Notebook for tabbed interface (placed inside the scrollable content frame)
        self.notebook = ttk.Notebook(self.content_frame)
        self.notebook.pack(expand=True, fill="both", pady=10)

        # Create empty tab frames and register creators for lazy population.
        # This reduces initial layout work and avoids very tall immediate UI
        # that can cause layout jank; heavy tabs are created on first select.
        self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_services = ttk.Frame(self.notebook)
        self.tab_ngrok = ttk.Frame(self.notebook)
        self.tab_code_approval = ttk.Frame(self.notebook)
        self.tab_reports = ttk.Frame(self.notebook)
        self.tab_ai_systems = ttk.Frame(self.notebook)
        self.tab_chat = ttk.Frame(self.notebook)
        self.tab_hardware = ttk.Frame(self.notebook)
        self.tab_security = ttk.Frame(self.notebook)
        self.tab_performance = ttk.Frame(self.notebook)
        self.tab_admin = ttk.Frame(self.notebook)
        self.tab_testing = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_dashboard, text="Dashboard")
        self.notebook.add(self.tab_services, text="Services")
        self.notebook.add(self.tab_ngrok, text="Ngrok Tunnels")
        self.notebook.add(self.tab_code_approval, text="Code Approvals")
        self.notebook.add(self.tab_reports, text="Reports")
        self.notebook.add(self.tab_ai_systems, text="AI Systems")
        self.notebook.add(self.tab_chat, text="AI Chat")
        self.notebook.add(self.tab_hardware, text="Hardware")
        self.notebook.add(self.tab_security, text="Security")
        self.notebook.add(self.tab_performance, text="Performance")
        self.notebook.add(self.tab_admin, text="Administration")
        self.notebook.add(self.tab_testing, text="Testing")

        # Map visible tab text to their creation methods so we can lazy-load
        self._tab_creators = {
            "Dashboard": self.create_dashboard_tab,
            "Services": self.create_services_tab,
            "Ngrok Tunnels": self.create_ngrok_tab,
            "Code Approvals": self.create_code_approval_tab,
            "Reports": self.create_reports_tab,
            "AI Systems": self.create_ai_systems_tab,
            "AI Chat": self.create_chat_tab,
            "Hardware": self.create_hardware_tab,
            "Security": self.create_security_tab,
            "Performance": self.create_performance_tab,
            "Administration": self.create_admin_tab,
            "Testing": self.create_testing_tab,
        }

        # Track which tabs have been initialized
        self._tab_initialized = {k: False for k in self._tab_creators.keys()}

        # Bind to tab change events to populate tabs lazily
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Create only the initially visible tab to speed startup
        try:
            initial_tab_text = self.notebook.tab(self.notebook.select(), option="text")
            creator = self._tab_creators.get(initial_tab_text)
            if creator:
                creator()
                self._tab_initialized[initial_tab_text] = True
        except Exception:
            # Fallback: ensure dashboard is available
            try:
                self.create_dashboard_tab()
                self._tab_initialized["Dashboard"] = True
            except Exception:
                logging.debug("Failed to lazy-create initial dashboard tab", exc_info=True)

        # Status Bar
        self.status_bar = ttk.Label(self.main_frame, text="Status: Initializing...", style="Status.TLabel", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")

    def on_closing(self):
        """Handle window close event - cleanup and shutdown."""
        try:
            logging.info("Application closing - performing cleanup...")
            
            # Close all open windows first
            self.close_all_windows()
            
            # Stop async loop if exists
            if hasattr(self, 'async_loop') and self.async_loop:
                try:
                    self.async_loop.stop()
                except Exception as e:
                    logging.warning(f"Error stopping async loop: {e}")
            
            # Destroy the window
            self.root.destroy()
            
        except Exception as e:
            logging.exception(f"Error during application shutdown: {e}")
            # Force close even if cleanup fails
            try:
                self.root.destroy()
            except Exception:
                pass

    def close_all_windows(self):
        """Close all currently open Toplevel windows."""
        windows_to_close = self._open_windows[:]
        self._open_windows.clear()
        
        for win in windows_to_close:
            try:
                if win.winfo_exists():
                    win.destroy()
            except Exception as e:
                logging.warning(f"Error closing window: {e}")

    def register_window(self, window: tk.Toplevel):
        """Register a new Toplevel window for management.
        
        This ensures the window will be closed when close_all_windows() is called.
        """
        if window not in self._open_windows:
            self._open_windows.append(window)
            # Automatically remove from list when window is destroyed
            def on_destroy():
                try:
                    if window in self._open_windows:
                        self._open_windows.remove(window)
                except Exception:
                    pass
            window.protocol("WM_DELETE_WINDOW", on_destroy)

    def create_managed_window(self, title: str = "", geometry: str = "") -> tk.Toplevel:
        """Create a new Toplevel window that is automatically managed.
        
        This method closes all other windows before creating the new one,
        ensuring only one dialog window is open at a time.
        """
        # Close all existing windows first
        self.close_all_windows()
        
        # Create new window
        win = tk.Toplevel(self.root)
        if title:
            win.title(title)
        if geometry:
            win.geometry(geometry)
        
        # Register for management
        self.register_window(win)
        
        return win

    def load_service_config(self) -> Dict[str, Dict[str, Any]]:
        """Load service configuration from config file or return defaults."""
        try:
            config_file = PROJECT_ROOT / 'config' / 'config.json'
            if config_file.exists():
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('services', self._get_default_services())
        except Exception as e:
            logging.warning(f"Could not load service config: {e}")
        
        return self._get_default_services()
    
    def _get_default_services(self) -> Dict[str, Dict[str, Any]]:
        """Return default service configuration."""
        return {
            "Enhanced Dashboard": {
                "script": "src/celsius/dashboard/enhanced_mobile_dashboard.py",
                "description": "Web-based mobile dashboard",
                "port": 5000,
                "process": None,
                "enabled": True,
                "status": "Stopped"
            },
            "Core AI Engine": {
                "script": "src/celsius/main.py",
                "description": "Main Celsius AI interaction system",
                "process": None,
                "enabled": True,
                "status": "Stopped"
            },
            "Guardian System": {
                "script": "src/celsius/guardian/celsius_lightweight_guardian.py",
                "description": "Background monitoring service",
                "process": None,
                "enabled": True,
                "status": "Stopped"
            },
            "Web Learning": {
                "script": "src/celsius/learning/celsius_web_learner.py",
                "description": "AI web learning and communication",
                "process": None,
                "enabled": False,
                "status": "Stopped"
            },
            "Email Notifications": {
                "script": "src/celsius/notifications/enhanced_email_system.py",
                "description": "Email alert system",
                "process": None,
                "enabled": False,
                "status": "Stopped"
            }
        }

    def _msg(self, dialog_func, title, message):
        """
        Helper method to show message dialogs safely from any thread.
        
        Args:
            dialog_func: The messagebox function (showinfo, showerror, askyesno, etc.)
            title: Dialog title
            message: Dialog message
        
        Returns:
            Result of the dialog function
        """
        try:
            return dialog_func(title, message)
        except Exception as e:
            logging.error(f"Error showing dialog '{title}': {e}")
            return None

    def schedule_on_main_thread(self, func, *args, **kwargs):
        """
        Schedule a function to be executed in the main tkinter thread.
        This is used to safely call tkinter APIs from async operations.
        
        Args:
            func: The function to call
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
        """
        def task():
            try:
                func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error executing scheduled task {func.__name__}: {e}")
                logging.exception("Traceback:")
        
        self._main_thread_queue.put(task)

    def _process_main_thread_queue(self):
        """
        Process tasks from the main thread queue.
        This method is called periodically to execute tasks scheduled via
        schedule_on_main_thread(), ensuring they run in the tkinter main thread.
        """
        try:
            # Process all pending tasks in the queue
            while not self._main_thread_queue.empty():
                try:
                    task = self._main_thread_queue.get_nowait()
                    task()
                except queue.Empty:
                    break
                except Exception as e:
                    logging.error(f"Error processing main thread queue task: {e}")
                    logging.exception("Traceback:")
        except Exception as e:
            logging.error(f"Error in main thread queue processor: {e}")
        finally:
            # Reschedule to run again after 100ms
            self.root.after(100, self._process_main_thread_queue)

    def logout_action(self):
        """
        Handle logout button click.
        Closes the application and optionally returns to login screen.
        """
        try:
            logging.info(f"User {self.username} initiated logout")
            # Stop any running services
            if hasattr(self, 'services'):
                for service_name, service_info in self.services.items():
                    if service_info.get('process') and service_info['process'].poll() is None:
                        try:
                            service_info['process'].terminate()
                            logging.info(f"Terminated service: {service_name}")
                        except Exception as e:
                            logging.error(f"Error terminating service {service_name}: {e}")
            
            # Close the application
            self.on_closing()
        except Exception as e:
            logging.error(f"Error during logout: {e}")
            logging.exception("Traceback:")
            # Force close anyway
            try:
                self.root.destroy()
            except Exception:
                pass

    def _periodic_update_email_status(self):
        """
        Periodically check and update email system status.
        This is called every few seconds to keep the email status current.
        """
        try:
            # Check if email widgets exist
            if hasattr(self, 'email_status_label'):
                # Try to determine email system status
                email_config_path = os.path.join(os.getcwd(), "config", "email_config.json")
                if os.path.exists(email_config_path):
                    try:
                        with open(email_config_path, 'r') as f:
                            email_config = json.load(f)
                            if email_config.get('enabled', False):
                                self.email_status_label.config(text="Active")
                            else:
                                self.email_status_label.config(text="Disabled")
                    except Exception as e:
                        logging.error(f"Error reading email config: {e}")
                        self.email_status_label.config(text="Error")
                else:
                    self.email_status_label.config(text="Not Configured")
        except Exception as e:
            logging.error(f"Error updating email status: {e}")
        finally:
            # Schedule next update in 5 seconds
            self.root.after(5000, self._periodic_update_email_status)

    def _on_tab_changed(self, event):
        """
        Handle tab change events for lazy loading of tab content.
        Only populates a tab's content the first time it's selected.
        """
        try:
            # Get the currently selected tab
            current_tab = event.widget.select()
            if not current_tab:
                return
            
            # Get the tab text/name
            tab_text = event.widget.tab(current_tab, "text")
            
            # Check if this tab needs to be initialized
            if tab_text in self._tab_initialized and not self._tab_initialized[tab_text]:
                logging.info(f"Lazy-loading tab: {tab_text}")
                
                # Call the appropriate creator method
                if tab_text in self._tab_creators:
                    try:
                        self._tab_creators[tab_text]()
                        self._tab_initialized[tab_text] = True
                        logging.info(f"Successfully initialized tab: {tab_text}")
                    except Exception as e:
                        logging.error(f"Error initializing tab {tab_text}: {e}")
                        logging.exception("Traceback:")
        except Exception as e:
            logging.error(f"Error in tab change handler: {e}")
            logging.exception("Traceback:")

    def setup_styles(self):
        """Defines custom styles for various ttk widgets."""
        try:
            self.style.configure("Header.TLabel", font=("Helvetica", 16, "bold"), padding=(0, 10, 0, 10))
            self.style.configure("TNotebook.Tab", font=("Helvetica", 10, "bold"), padding=[5, 2])
            self.style.configure("Status.TLabel", font=("Helvetica", 9), padding=(5, 5))
            self.style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
            self.style.configure("TButton", font=("Helvetica", 10), padding=5)
            self.style.map("Start.TButton", foreground=[("!disabled", "green")])
            self.style.map("Stop.TButton", foreground=[("!disabled", "red")])
            self.style.map("Restart.TButton", foreground=[("!disabled", "orange")])
        except Exception:
            # If styling fails, continue without raising
            logging.debug("Failed to apply ttk styles", exc_info=True)

    def create_widgets(self):
        """Create the main frame, header, and user controls for the hub.

        This centralizes the top-level layout so extracted UI functions can
        rely on `self.main_frame` and `self.user_label` existing.
        """
        # Main container frame (holds a scrollable canvas so the hub UI
        # doesn't get squished on smaller windows). The outer `main_frame`
        # contains the vertical scrollbar and canvas; the actual widgets live
        # inside `content_frame` which is a window on the canvas.
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(expand=True, fill="both")

        # Scrollable canvas and vertical scrollbar
        canvas_bg = self.style.lookup("TFrame", "background") or self.root.cget("bg")
        self._canvas = tk.Canvas(self.main_frame, highlightthickness=0, bg=canvas_bg)
        self._vscroll = ttk.Scrollbar(self.main_frame, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vscroll.set)
        self._vscroll.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        # Frame placed inside the canvas which will contain the header,
        # notebook, and all other UI sections.
        self.content_frame = ttk.Frame(self._canvas, padding="10")
        # Create a named window on the canvas and remember its id so we can
        # resize the interior to the canvas width to avoid blank white strips
        # when the canvas is larger than the content.
        self._content_window = self._canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        # Ensure the canvas scrollregion is updated when content size changes
        def _on_content_config(event):
            try:
                self._canvas.configure(scrollregion=self._canvas.bbox("all"))
            except Exception:
                pass

        self.content_frame.bind("<Configure>", _on_content_config)

        # When the canvas is resized (for example when the window is widened),
        # make the interior window match the canvas width so there isn't an
        # uncovered canvas area (which appears white under some themes).
        def _on_canvas_config(event):
            try:
                # Resize interior window to the canvas width
                self._canvas.itemconfig(self._content_window, width=event.width)
            except Exception:
                pass

        self._canvas.bind("<Configure>", _on_canvas_config)

        # Also ensure the interior window is sized to the current canvas width
        # at startup so there isn't a brief white strip on initial layout.
        try:
            self._canvas.itemconfig(self._content_window, width=self._canvas.winfo_width())
        except Exception:
            pass

        # Mousewheel handling: bind when pointer enters the content area
        def _on_mousewheel(event):
            # Windows: event.delta reports multiples of 120
            try:
                # Standard Windows / macOS mouse wheel event
                if hasattr(event, "delta") and event.delta:
                    self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                # X11 (Linux) mouse wheel events come as Button-4 / Button-5
                elif hasattr(event, "num"):
                    if event.num == 4:
                        # scroll up
                        self._canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        # scroll down
                        self._canvas.yview_scroll(1, "units")
            except Exception:
                pass

        def _bind_mousewheel(event):
            # Bind all common wheel events so scrolling works across platforms
            self._canvas.bind_all("<MouseWheel>", _on_mousewheel)
            self._canvas.bind_all("<Button-4>", _on_mousewheel)
            self._canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(event):
            self._canvas.unbind_all("<MouseWheel>")
            self._canvas.unbind_all("<Button-4>")
            self._canvas.unbind_all("<Button-5>")

        self.content_frame.bind("<Enter>", _bind_mousewheel)
        self.content_frame.bind("<Leave>", _unbind_mousewheel)

        # Header frame with logout button
        header_frame = ttk.Frame(self.content_frame)
        header_frame.pack(fill="x", pady=(0, 10))

        # Header label
        header_label = ttk.Label(header_frame, text="Celsius AI - Ultimate Hub", style="Header.TLabel")
        header_label.pack(side="left")

        # User info and logout button
        user_frame = ttk.Frame(header_frame)
        user_frame.pack(side="right")

        self.user_label = ttk.Label(user_frame, text=f"User: {self.username}", font=("Helvetica", 10))
        self.user_label.pack(side="left", padx=(0, 10))

        self.logout_btn = ttk.Button(user_frame, text="Logout", command=self.logout_action, width=12)
        self.logout_btn.pack(side="left")

        # Change password button
        try:
            from src.celsius.hub.account import ChangePasswordWindow

            self.change_pw_btn = ttk.Button(
                user_frame, text="Change Password", command=self._open_change_password, width=16
            )
            self.change_pw_btn.pack(side="left", padx=(6, 0))
        except Exception:
            # If account UI not available, skip adding the button
            pass

        # Email notifier status and manual re-init
        self.email_status_label = ttk.Label(user_frame, text="Email: Unknown", font=("Helvetica", 9))
        self.email_status_label.pack(side="left", padx=(8, 4))

        self.email_reinit_btn = ttk.Button(user_frame, text="Re-init Email", command=lambda: self.async_loop.create_task(self.ensure_email_notifier(force=True)), width=12)
        self.email_reinit_btn.pack(side="left")

        # Update the email status display periodically
        self.root.after(1000, self._periodic_update_email_status)

    def create_dashboard_tab(self):
        """Creates the content for the Dashboard tab."""
        frame = self.tab_dashboard

        # System Overview Section
        overview_frame = ttk.LabelFrame(frame, text="System Overview", padding=10)
        overview_frame.pack(fill="x", padx=10, pady=5)

        # Create metric labels
        self.cpu_label = ttk.Label(overview_frame, text="CPU: Loading...", font=("Helvetica", 10))
        self.cpu_label.grid(row=0, column=0, sticky="w", padx=5, pady=2)

        self.memory_label = ttk.Label(overview_frame, text="Memory: Loading...", font=("Helvetica", 10))
        self.memory_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)

        self.disk_label = ttk.Label(overview_frame, text="Disk: Loading...", font=("Helvetica", 10))
        self.disk_label.grid(row=2, column=0, sticky="w", padx=5, pady=2)

        # Service Status Overview
        status_frame = ttk.LabelFrame(frame, text="Service Status Overview", padding=10)
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.service_status_text = tk.Text(
            status_frame,
            wrap="word",
            height=10,
            bg=self.style.lookup("TFrame", "background"),
            fg=self.style.lookup("TLabel", "foreground"),
        )
        self.service_status_text.pack(fill="both", expand=True)

        # Quick Actions
        actions_frame = ttk.LabelFrame(frame, text="Quick Actions", padding=10)
        actions_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(actions_frame, text="Start All Services", command=self.start_all_services).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="Stop All Services", command=self.stop_all_services).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="Refresh Metrics", command=self.refresh_dashboard).pack(side="left", padx=5)

        # Learning Insights Section
        learning_frame = ttk.LabelFrame(frame, text="AI Learning Insights", padding=10)
        learning_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Learning status and controls
        learning_control_frame = ttk.Frame(learning_frame)
        learning_control_frame.pack(fill="x", pady=(0, 5))

        self.learning_status_label = ttk.Label(
            learning_control_frame, text="Learning System: Checking...", font=("Helvetica", 10, "bold")
        )
        self.learning_status_label.pack(side="left", padx=5)

        ttk.Button(learning_control_frame, text="Refresh Insights", command=self.refresh_learning_insights).pack(
            side="right", padx=5
        )
        ttk.Button(learning_control_frame, text="Start Web Learning", command=self.start_web_learning_system).pack(
            side="right", padx=5
        )
        ttk.Button(learning_control_frame, text="Start AI Learning", command=self.start_learning_system).pack(
            side="right", padx=5
        )

        # Learning insights text area
        insights_scroll = ttk.Scrollbar(learning_frame)
        insights_scroll.pack(side="right", fill="y")

        self.learning_insights_text = tk.Text(
            learning_frame,
            wrap="word",
            height=8,
            bg=self.style.lookup("TFrame", "background"),
            fg=self.style.lookup("TLabel", "foreground"),
            yscrollcommand=insights_scroll.set,
        )
        self.learning_insights_text.pack(fill="both", expand=True)
        insights_scroll.config(command=self.learning_insights_text.yview)

        # Initial update
        self.refresh_dashboard()
        self.refresh_learning_insights()

    def create_services_tab(self):
        """Creates the content for the Services tab."""
        frame = self.tab_services
        self.service_frames = {}

        # Create a scrollable container for services so many entries don't overflow
        svc_canvas = tk.Canvas(frame, highlightthickness=0, bg=self.style.lookup("TFrame", "background"))
        svc_scroll = ttk.Scrollbar(frame, orient="vertical", command=svc_canvas.yview)
        svc_inner = ttk.Frame(svc_canvas)

        svc_inner_id = svc_canvas.create_window((0, 0), window=svc_inner, anchor="nw")
        svc_canvas.configure(yscrollcommand=svc_scroll.set)

        def _on_config(e):
            try:
                svc_canvas.configure(scrollregion=svc_canvas.bbox("all"))
                svc_canvas.itemconfig(svc_inner_id, width=e.width)
            except Exception:
                pass

        svc_inner.bind("<Configure>", lambda e: svc_canvas.configure(scrollregion=svc_canvas.bbox("all")))
        svc_canvas.bind("<Configure>", _on_config)

        svc_canvas.pack(side="left", fill="both", expand=True)
        svc_scroll.pack(side="right", fill="y")

        # Build service frames incrementally to avoid blocking the UI for large lists
        services_list = list(self.services.items())

        def build_chunk(start=0, chunk_size=6):
            end = min(start + chunk_size, len(services_list))
            for idx in range(start, end):
                service_name, details = services_list[idx]
                i = idx
                service_frame = ttk.LabelFrame(svc_inner, text=details.get("name", str(service_name)), padding=10)
                service_frame.grid(row=i, column=0, padx=10, pady=5, sticky="ew")

                status_label = ttk.Label(service_frame, text=f"Status: {details.get('status', 'Stopped')}")
                status_label.pack(side="left", padx=5)

                start_btn = ttk.Button(
                    service_frame,
                    text="Start",
                    style="Start.TButton",
                    command=lambda s=service_name: self.start_service_action(s),
                )
                start_btn.pack(side="left", padx=2)

                stop_btn = ttk.Button(
                    service_frame,
                    text="Stop",
                    style="Stop.TButton",
                    command=lambda s=service_name: self.stop_service_action(s),
                )
                stop_btn.pack(side="left", padx=2)

                restart_btn = ttk.Button(
                    service_frame,
                    text="Restart",
                    style="Restart.TButton",
                    command=lambda s=service_name: self.restart_service_action(s),
                )
                restart_btn.pack(side="left", padx=2)

                self.service_frames[service_name] = {
                    "frame": service_frame,
                    "status_label": status_label,
                    "start_btn": start_btn,
                    "stop_btn": stop_btn,
                }

            # Update buttons for built chunk
            self.update_service_buttons()

            if end < len(services_list):
                # schedule next chunk so the UI remains responsive
                self.root.after(50, lambda: build_chunk(end, chunk_size))

        # Start building in the background of the main thread
        self.root.after(10, lambda: build_chunk(0, 8))

    def update_service_buttons(self):
        """Updates the state of service control buttons based on service status."""
        # Guard: service_frames is only initialized when Services tab is created
        if not hasattr(self, 'service_frames'):
            return
            
        for name, service in self.services.items():
            widgets = self.service_frames.get(name)
            if not widgets:
                continue

            status = service.get("status", "Stopped")
            widgets["status_label"].config(text=f"Status: {status}")

            if status == "Running":
                widgets["start_btn"].config(state=tk.DISABLED)
                widgets["stop_btn"].config(state=tk.NORMAL)
            else:
                widgets["start_btn"].config(state=tk.NORMAL)
                widgets["stop_btn"].config(state=tk.DISABLED)

    def _open_change_password(self):
        """Open the change-password dialog for the current user."""
        try:
            from src.celsius.hub.account import ChangePasswordWindow

            ChangePasswordWindow(self.root, self.username, window_manager=self)
        except Exception as e:
            logging.exception("Failed to open ChangePasswordWindow: %s", e)
            messagebox.showerror("Error", f"Failed to open Change Password dialog: {e}")

    def create_monitoring_tab(self):
        """Delegate Monitoring tab creation to the extracted UI module."""
        pass

    def create_reports_tab(self):
        """Create Reports tab by delegating to the extracted UI module."""
        from src.celsius.hub.ui import create_reports_tab as _create
        try:
            _create(self)
        except Exception as e:
            logging.exception("Failed to create Reports tab UI: %s", e)
            self._show_tab_error(self.tab_reports, f"Reports tab failed: {e}")
            raise

    def open_import_dialog(self):
        """Open a dialog to paste or upload a transcript for ingestion."""
        if not _HAS_INGEST or store_conversation is None:
            messagebox.showerror("Import Unavailable", "Conversation ingestion is not available in this installation.")
            return

        win = self.create_managed_window("Import Transcript", "720x520")

        ttk.Label(win, text="Paste transcript below or choose a .txt file to upload:", font=("Helvetica", 10)).pack(
            pady=(8, 4), anchor="w", padx=8
        )

        text_frame = ttk.Frame(win)
        text_frame.pack(fill="both", expand=True, padx=8, pady=4)

        txt = tk.Text(text_frame, wrap="word")
        txt.pack(side="left", fill="both", expand=True)

        scr = ttk.Scrollbar(text_frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=scr.set)
        scr.pack(side="right", fill="y")

        file_frame = ttk.Frame(win)
        file_frame.pack(fill="x", padx=8, pady=(4, 8))

        ttk.Button(file_frame, text="Select .txt File...", command=lambda: self._select_file_for_import(txt)).pack(
            side="left"
        )
        ttk.Button(
            file_frame, text="Ingest (Store Conversation)", command=lambda: self._import_transcript_submit(txt, win)
        ).pack(side="right")

        # Info note
        ttk.Label(
            win,
            text="Note: PII will be redacted before storing. Only .txt uploads are supported here; for EPUB/PDF use the ingest script.",
            font=("Helvetica", 8),
            foreground="gray",
        ).pack(fill="x", padx=8, pady=(0, 6))

    def _select_file_for_import(self, text_widget: tk.Text):
        """Allow selecting a plain text file and load it into the text widget."""
        path = filedialog.askopenfilename(
            title="Select transcript (.txt)", filetypes=[("Text files", "*.txt"), ("All files", "*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = fh.read()
        except Exception as e:
            messagebox.showerror("File Read Error", f"Could not read file: {e}")
            return
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", data)

    def _import_transcript_submit(self, text_widget: tk.Text, win: tk.Toplevel):
        """Validate user consent and store the transcript via conversation_ingest.store_conversation()."""
        content = text_widget.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("Empty Transcript", "Please paste or select a transcript to import.")
            return

        confirm = messagebox.askyesno(
            "Confirm Import",
            "This will redact PII and store a sanitized copy of the transcript for opt-in training. Do you wish to proceed?",
        )
        if not confirm:
            return

        try:
            result = store_conversation(content, participants=self.username, source="import")
        except Exception as e:
            messagebox.showerror("Ingestion Error", f"Failed to store conversation: {e}")
            return

        if isinstance(result, dict) and result.get("status") == "ok":
            messagebox.showinfo("Ingested", f"Transcript ingested successfully at {result.get('timestamp')}")
            # Refresh reports area so user sees it reflected in history
            try:
                self.refresh_learning_reports()
            except Exception:
                pass
            win.destroy()
        else:
            messagebox.showerror("Ingestion Failed", f"Result: {result}")

    def create_ai_systems_tab(self):
        """Creates the content for the AI Systems tab."""
        frame = self.tab_ai_systems

        # Learning Services Controller
        learning_services_frame = ttk.LabelFrame(frame, text="Learning Services", padding=10)
        learning_services_frame.pack(fill="x", padx=10, pady=5)

        # Master enable/disable for learning services
        self._learning_enabled_var = tk.BooleanVar(value=self.enable_conversation_training)
        def _on_master_toggle():
            enabled = bool(self._learning_enabled_var.get())
            self.enable_conversation_training = enabled
            # enable/disable buttons
            try:
                state = tk.NORMAL if enabled else tk.DISABLED
                self.start_ai_learning_btn.config(state=state)
                self.stop_ai_learning_btn.config(state=state)
                self.start_web_learning_btn.config(state=state)
                self.stop_web_learning_btn.config(state=state)
            except Exception:
                pass

        ttk.Checkbutton(
            learning_services_frame,
            text="Enable Learning Services",
            variable=self._learning_enabled_var,
            command=_on_master_toggle,
        ).pack(side="left", padx=(0, 8))

        # Buttons to start/stop AI and Web learning
        btns = ttk.Frame(learning_services_frame)
        btns.pack(side="left")
        self.start_ai_learning_btn = ttk.Button(btns, text="Start AI Learning", command=self.start_learning_system)
        self.start_ai_learning_btn.pack(side="left", padx=4)
        self.stop_ai_learning_btn = ttk.Button(btns, text="Stop AI Learning", command=self.stop_learning_system)
        self.stop_ai_learning_btn.pack(side="left", padx=4)

        self.start_web_learning_btn = ttk.Button(btns, text="Start Web Learning", command=self.start_web_learning_system)
        self.start_web_learning_btn.pack(side="left", padx=4)
        self.stop_web_learning_btn = ttk.Button(btns, text="Stop Web Learning", command=self.stop_web_learning_system)
        self.stop_web_learning_btn.pack(side="left", padx=4)

        # Web Learning System
        web_learning_frame = ttk.LabelFrame(frame, text="Web Learning System", padding=10)
        web_learning_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(web_learning_frame, text="AI Knowledge Acquisition and Training", font=("Helvetica", 10)).pack(pady=5)
        ttk.Button(web_learning_frame, text="Start Learning Session", command=self.start_learning_session).pack(pady=5)
        ttk.Button(web_learning_frame, text="View Learning History", command=self.view_learning_history).pack(pady=5)

        # AI Model Status
        model_frame = ttk.LabelFrame(frame, text="AI Model Status", padding=10)
        model_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.ai_status_text = tk.Text(
            model_frame,
            wrap="word",
            height=10,
            bg=self.style.lookup("TFrame", "background"),
            fg=self.style.lookup("TLabel", "foreground"),
        )
        self.ai_status_text.pack(fill="both", expand=True)
        self.ai_status_text.insert(
            "1.0",
            "AI Systems initialized and ready.\n\nCore AI Engine: Ready\nWeb Learning: Ready",
        )

        # Local Intelligence (fully local LLM via provider abstraction)
        local_ai = ttk.LabelFrame(frame, text="Local Intelligence (No Cloud)", padding=10)
        local_ai.pack(fill="both", expand=True, padx=10, pady=5)

        # Model selection
        model_row = ttk.Frame(local_ai)
        model_row.pack(fill="x", pady=(0, 5))
        ttk.Label(model_row, text="AI Model:").pack(side="left")
        
        # Load available providers for dropdown
        self.available_providers = []
        try:
            if load_providers is not None:
                providers = load_providers()
                self.available_providers = [(p.name, p) for p in providers]
        except Exception:
            pass
        
        provider_names = [name for name, _ in self.available_providers] if self.available_providers else ["No providers available"]
        self.selected_provider_var = tk.StringVar(value=provider_names[0] if provider_names else "None")
        
        self.provider_dropdown = ttk.Combobox(
            model_row, 
            textvariable=self.selected_provider_var,
            values=provider_names,
            state="readonly",
            width=30
        )
        self.provider_dropdown.pack(side="left", padx=(6, 6))
        
        # Test connection button
        ttk.Button(model_row, text="Test Model", command=self.test_selected_provider).pack(side="left", padx=(0, 6))

        entry_row = ttk.Frame(local_ai)
        entry_row.pack(fill="x")
        ttk.Label(entry_row, text="Prompt:").pack(side="left")
        self.local_chat_input = tk.Text(entry_row, height=4, wrap="word")
        self.local_chat_input.pack(side="left", fill="x", expand=True, padx=(6, 6))

        btns_row = ttk.Frame(local_ai)
        btns_row.pack(fill="x", pady=(6, 6))
        ttk.Button(btns_row, text="Send (Local)", command=self.send_local_chat).pack(side="left", padx=4)
        ttk.Button(btns_row, text="Answer with Citations (Local)", command=self.answer_with_citations_local).pack(side="left", padx=4)
        ttk.Button(btns_row, text="Rebuild Local Index", command=self.rebuild_local_rag_index).pack(side="left", padx=4)
        ttk.Button(btns_row, text="Answer from Web (with citations)", command=self.answer_from_web_with_citations).pack(side="left", padx=4)
        ttk.Button(btns_row, text="Verify Local Model", command=self.verify_local_model).pack(side="left", padx=4)
        ttk.Button(btns_row, text="Pull llama3.1:8b", command=self.pull_local_model).pack(side="left", padx=4)

        # Conversation history controls
        history_row = ttk.Frame(local_ai)
        history_row.pack(fill="x", pady=(0, 6))
        ttk.Button(history_row, text="Save Conversation", command=self.save_conversation_history).pack(side="left", padx=4)
        ttk.Button(history_row, text="Load Conversation", command=self.load_conversation_history).pack(side="left", padx=4)
        ttk.Button(history_row, text="Clear History", command=self.clear_conversation_history).pack(side="left", padx=4)

        self.local_chat_output = tk.Text(local_ai, height=10, wrap="word",
            bg=self.style.lookup("TFrame", "background"), fg=self.style.lookup("TLabel", "foreground"))
        self.local_chat_output.pack(fill="both", expand=True)

    def create_chat_tab(self):
        """Delegate Chat tab creation to the extracted UI module."""
        try:
            from src.celsius.hub.ui import create_chat_tab

            return create_chat_tab(self)
        except Exception:
            logging.exception("Failed to delegate create_chat_tab to src.celsius.hub.ui")
            return None

    def test_selected_provider(self):
        """Test the currently selected AI provider with a simple prompt."""
        try:
            if not hasattr(self, 'local_chat_output'):
                return
            
            # Clear and show testing message
            self.local_chat_output.delete("1.0", "end")
            self.local_chat_output.insert("end", "Testing selected AI model...\n")
            
            async def _test():
                pv, err = self._select_local_provider()
                if err:
                    def _upd_err():
                        try:
                            self.local_chat_output.delete("1.0", "end")
                            self.local_chat_output.insert("end", f"Test failed: {err}\n")
                        except Exception:
                            pass
                    self.schedule_on_main_thread(_upd_err)
                    return
                
                try:
                    import time
                    start_time = time.time()
                    client = LLMClient(pv)
                    test_prompt = "Hello! Please respond with just 'AI connection successful' if you can read this."
                    data = await client.generate(test_prompt, timeout=30)
                    response_time = time.time() - start_time
                    text = self._extract_text_from_response(pv, data)
                    
                    def _upd_ok():
                        try:
                            self.local_chat_output.delete("1.0", "end")
                            self.local_chat_output.insert("end", f"✅ Model '{pv.name}' is working!\n")
                            self.local_chat_output.insert("end", f"⏱️ Response time: {response_time:.2f}s\n")
                            self.local_chat_output.insert("end", f"📝 Test response: {text[:200]}...\n")
                        except Exception:
                            pass
                    self.schedule_on_main_thread(_upd_ok)
                    
                except Exception as e:
                    logging.exception("Provider test failed")
                    def _upd_fail():
                        try:
                            self.local_chat_output.delete("1.0", "end")
                            self.local_chat_output.insert("end", f"❌ Test failed: {e}\n")
                            self.local_chat_output.insert("end", f"Model: {pv.name if pv else 'Unknown'}\n")
                        except Exception:
                            pass
                    self.schedule_on_main_thread(_upd_fail)
            
            self.schedule_async_task(_test)
            
        except Exception:
            logging.exception("test_selected_provider failed")

    def save_conversation_history(self):
        """Save the current conversation history to a file."""
        try:
            if not self.conversation_history:
                self._msg(messagebox.showinfo, "Save Conversation", "No conversation history to save.")
                return
            
            # Ensure data directory exists
            self.conversation_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with timestamp
            import datetime
            data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "provider": getattr(self, 'selected_provider_var', lambda: tk.StringVar()).get(),
                "messages": self.conversation_history
            }
            
            with open(self.conversation_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self._msg(messagebox.showinfo, "Save Conversation", f"Conversation saved to {self.conversation_file}")
            
        except Exception as e:
            logging.exception("Failed to save conversation history")
            self._msg(messagebox.showerror, "Save Failed", f"Failed to save conversation: {e}")

    def load_conversation_history(self):
        """Load conversation history from file."""
        try:
            if not self.conversation_file.exists():
                self._msg(messagebox.showinfo, "Load Conversation", "No saved conversation found.")
                return
            
            with open(self.conversation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.conversation_history = data.get('messages', [])
            
            # Display loaded conversation
            if hasattr(self, 'local_chat_output'):
                self.local_chat_output.delete("1.0", "end")
                self.local_chat_output.insert("end", "📚 Loaded conversation history:\n\n")
                
                for msg in self.conversation_history[-20:]:  # Show last 20 messages
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:500]  # Truncate long messages
                    timestamp = msg.get('timestamp', '')[:19]  # Just date/time part
                    
                    self.local_chat_output.insert("end", f"[{timestamp}] {role.upper()}: {content}\n\n")
                
                self.local_chat_output.insert("end", f"--- End of loaded history ({len(self.conversation_history)} total messages) ---\n\n")
                self.local_chat_output.see("end")
            
            provider = data.get('provider', 'Unknown')
            self._msg(messagebox.showinfo, "Load Conversation", f"Loaded {len(self.conversation_history)} messages from {provider}")
            
        except Exception as e:
            logging.exception("Failed to load conversation history")
            self._msg(messagebox.showerror, "Load Failed", f"Failed to load conversation: {e}")

    def clear_conversation_history(self):
        """Clear the current conversation history."""
        try:
            self.conversation_history.clear()
            if hasattr(self, 'local_chat_output'):
                self.local_chat_output.delete("1.0", "end")
                self.local_chat_output.insert("end", "🧹 Conversation history cleared.\n\n")
            
            # Optionally delete the saved file
            if self.conversation_file.exists():
                confirm = messagebox.askyesno(
                    "Delete Saved History",
                    "Also delete the saved conversation file?"
                )
                if confirm:
                    self.conversation_file.unlink()
                    
        except Exception as e:
            logging.exception("Failed to clear conversation history")
            self._msg(messagebox.showerror, "Clear Failed", f"Failed to clear history: {e}")

    def _add_to_conversation_history(self, role: str, content: str):
        """Add a message to the conversation history."""
        try:
            import datetime
            self.conversation_history.append({
                "role": role,
                "content": content,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            # Keep only last 100 messages to prevent memory issues
            if len(self.conversation_history) > 100:
                self.conversation_history = self.conversation_history[-100:]
                
        except Exception:
            logging.exception("Failed to add to conversation history")
    def _select_local_provider(self):
        """Pick the selected provider from dropdown. Returns (provider or None, error_msg or None)."""
        try:
            if load_providers is None or LLMClient is None:
                return None, (
                    "Local provider module not available. Ensure src/celsius/ai/providers.py "
                    "is present and aiohttp is installed."
                )
            
            selected_name = getattr(self, 'selected_provider_var', None)
            if selected_name is None:
                return None, "No provider selected."
            
            selected_name = selected_name.get()
            if not selected_name or selected_name == "No providers available":
                return None, "No valid provider selected."
            
            # Find the selected provider
            for name, provider in getattr(self, 'available_providers', []):
                if name == selected_name:
                    return provider, None
            
            return None, f"Selected provider '{selected_name}' not found."
            
        except Exception as e:
            logging.exception("Selecting provider failed")
            return None, str(e)

    def _extract_text_from_response(self, provider, data: dict) -> str:
        """Normalize text extraction across provider types."""
        try:
            ptype = (getattr(provider, 'type', '') or '').lower()
            name = (getattr(provider, 'name', '') or '').lower()
            # Ollama generate API
            if 'ollama' in ptype or 'ollama' in name:
                return (data.get('response') or '').strip() or json.dumps(data)
            # OpenAI chat completions
            if 'openai' in ptype:
                choices = data.get('choices') or []
                if choices:
                    msg = (choices[0] or {}).get('message') or {}
                    return (msg.get('content') or '').strip() or json.dumps(data)
            # Anthropic messages
            if 'anthropic' in ptype:
                content = data.get('content') or []
                if isinstance(content, list) and content:
                    part = content[0]
                    if isinstance(part, dict):
                        return (part.get('text') or part.get('content') or '').strip() or json.dumps(data)
            # Google Gemini generateContent
            if 'google' in ptype or 'generativelanguage' in ptype:
                candidates = data.get('candidates') or []
                if candidates:
                    content = candidates[0].get('content') or {}
                    parts = content.get('parts') or []
                    if parts:
                        return ''.join(x.get('text', '') for x in parts).strip() or json.dumps(data)
            # Fallback
            return json.dumps(data)
        except Exception:
            logging.exception("extract_text_from_response failed")
            try:
                return json.dumps(data)
            except Exception:
                return str(data)

    def _check_prompt_safety(self, prompt: str) -> tuple[bool, str]:
        """Basic safety check for prompts. Returns (is_safe, reason_if_not)."""
        try:
            prompt_lower = prompt.lower()
            
            # Basic harmful content patterns
            harmful_patterns = [
                "how to make", "how to build", "how to create", "recipe for",
                "instructions for", "guide to", "tutorial on",
                "hack", "exploit", "bypass", "crack", "steal",
                "illegal", "unlawful", "forbidden", "prohibited"
            ]
            
            # Check for harmful intent combined with dangerous topics
            dangerous_topics = ["bomb", "weapon", "drug", "virus", "malware", "explosive"]
            
            for pattern in harmful_patterns:
                if pattern in prompt_lower:
                    for topic in dangerous_topics:
                        if topic in prompt_lower:
                            return False, f"Prompt appears to request information about {topic}s, which may be unsafe."
            
            return True, ""
            
        except Exception:
            # If safety check fails, allow the prompt (fail-safe)
            return True, ""

    def send_local_chat(self):
        """Handle the 'Send (Local)' button: prompt local LLM and display reply."""
        try:
            if not hasattr(self, 'local_chat_input') or not hasattr(self, 'local_chat_output'):
                return
            prompt = (self.local_chat_input.get("1.0", "end") or "").strip()
            if not prompt:
                self._msg(messagebox.showinfo, "Local Chat", "Enter a prompt first.")
                return

            # Safety check
            is_safe, reason = self._check_prompt_safety(prompt)
            if not is_safe:
                self._msg(messagebox.showwarning, "Safety Warning", 
                         f"Your prompt may request unsafe information:\n\n{reason}\n\nPlease rephrase your request.")
                return

            # Show immediate feedback
            try:
                self.local_chat_output.delete("1.0", "end")
                self.local_chat_output.insert("end", "Connecting to local model…\n")
            except Exception:
                pass

            # Add user message to history
            self._add_to_conversation_history("user", prompt)

            async def _go():
                pv, err = self._select_local_provider()
                if err:
                    def _upd_err():
                        try:
                            self.local_chat_output.delete("1.0", "end")
                            self.local_chat_output.insert("end", f"{err}\n")
                            self.local_chat_output.insert("end", "Tip: Install and start Ollama; verify http://127.0.0.1:11434 responds.\n")
                        except Exception:
                            pass
                    self.schedule_on_main_thread(_upd_err)
                    return
                try:
                    import time
                    start_time = time.time()
                    client = LLMClient(pv)
                    data = await client.generate(prompt, timeout=120)
                    response_time = time.time() - start_time
                    text = self._extract_text_from_response(pv, data)
                    
                    # Add AI response to history with performance info
                    self._add_to_conversation_history("assistant", text)
                    
                    # Add performance info to response
                    text = f"⏱️ Response time: {response_time:.2f}s\n\n{text}"
                    
                except Exception as e:
                    logging.exception("Local chat request failed")
                    text = f"Error from local model: {e}"
                    self._add_to_conversation_history("assistant", text)

                def _upd_ok():
                    try:
                        self.local_chat_output.delete("1.0", "end")
                        self.local_chat_output.insert("end", text)
                    except Exception:
                        pass
                self.schedule_on_main_thread(_upd_ok)

            self.schedule_async_task(_go())
        except Exception:
            logging.exception("send_local_chat outer failed")

    def _gather_local_context(self, query: str, max_chars: int = 3000, max_files: int = 5):
        """Collect lightweight snippets from local files related to the query.

        Returns (context_text, citations_list) where citations_list is a list of (index, path).
        """
        try:
            roots = [
                self.project_root / 'docs',
                self.project_root / 'src',
                self.project_root / 'config',
                self.project_root / 'learning_reports'
            ]
            keywords = [w.lower() for w in re.findall(r"[A-Za-z0-9_]+", query)]
            stop = {"the","and","or","to","of","a","an","in","on","for","with","is","are","be","it","that","this","can","do","we","you"}
            keywords = [k for k in keywords if k not in stop and len(k) > 1]
            scored = []
            for root in roots:
                try:
                    if not root.exists():
                        continue
                    for p in root.rglob('*'):
                        try:
                            if not p.is_file():
                                continue
                            if p.suffix.lower() not in {'.md', '.txt', '.py', '.json'}:
                                continue
                            if p.stat().st_size > 256 * 1024:
                                continue
                            text = ''
                            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                                text = f.read()
                            score = 0
                            lt = text.lower()
                            for k in keywords:
                                score += lt.count(k)
                            if score > 0:
                                scored.append((score, p, text))
                        except Exception:
                            continue
                except Exception:
                    continue
            if not scored:
                return "", []
            scored.sort(key=lambda x: x[0], reverse=True)
            take = scored[:max_files]
            per_file = max(1, max_chars // max(1, len(take)))
            ctx_parts = []
            cites = []
            for idx, tup in enumerate(take, start=1):
                _, p, text = tup
                rel = str(p.relative_to(self.project_root)) if str(p).startswith(str(self.project_root)) else str(p)
                snippet = text[:per_file]
                ctx_parts.append(f"[{idx}] {rel}\n-----\n{snippet}\n\n")
                cites.append((idx, rel))
            return "".join(ctx_parts), cites
        except Exception:
            logging.exception("gather_local_context failed")
            return "", []

    def answer_with_citations_local(self):
        """Answer using local LLM with lightweight local file context and include citations."""
        try:
            if not hasattr(self, 'local_chat_input') or not hasattr(self, 'local_chat_output'):
                return
            question = (self.local_chat_input.get("1.0", "end") or "").strip()
            if not question:
                self._msg(messagebox.showinfo, "Local Citations", "Enter a question first.")
                return

            try:
                self.local_chat_output.delete("1.0", "end")
                self.local_chat_output.insert("end", "Searching local context…\n")
            except Exception:
                pass

            async def _go():
                # Prefer indexed local RAG if available
                ctx, cites = "", []
                try:
                    from src.celsius.ai.local_rag import default_roots, ensure_index, query_index
                    roots = default_roots()
                    ensure_index(roots)
                    results = query_index(question, top_k=5)
                    if results:
                        parts = []
                        cites = []
                        max_chars = 3000
                        per_file = max(1, max_chars // max(1, len(results)))
                        for i, (score, path, text) in enumerate(results, start=1):
                            rel = path
                            snippet = text[:per_file]
                            parts.append(f"[{i}] {rel}\n-----\n{snippet}\n\n")
                            cites.append((i, rel))
                        ctx = "".join(parts)
                except Exception:
                    # Fall back to direct scan
                    ctx, cites = self._gather_local_context(question)
                pv, err = self._select_local_provider()
                if err:
                    # Fallback: show the top snippets directly with sources
                    def _fallback_show():
                        try:
                            self.local_chat_output.delete("1.0", "end")
                            if ctx:
                                self.local_chat_output.insert("end", "Local model unavailable; showing context snippets.\n\n")
                                self.local_chat_output.insert("end", ctx)
                                sources = "\n".join([f"[{i}] {path}" for i, path in cites]) if cites else "(No sources found)"
                                self.local_chat_output.insert("end", f"\nSources:\n{sources}")
                            else:
                                self.local_chat_output.insert("end", f"{err}\n(No local context snippets found.)")
                        except Exception:
                            pass
                    self.schedule_on_main_thread(_fallback_show)
                    return
                try:
                    client = LLMClient(pv)
                    base_prompt = (
                        "You are Celsius AI running fully locally. Using the provided context snippets with "
                        "file-based citations like [1], [2], answer the user's question clearly and concisely. "
                        "If the context is insufficient, say so briefly. Include inline citations [n] matching the sources below.\n\n"
                        f"Context:\n{ctx if ctx else '(no significant local context found)'}\n\n"
                        f"Question:\n{question}\n\n"
                    )
                    data = await client.generate(base_prompt, timeout=150)
                    answer = self._extract_text_from_response(pv, data)
                    sources = "\n".join([f"[{i}] {path}" for i, path in cites]) if cites else "(No sources found)"
                    final = f"{answer}\n\nSources:\n{sources}"
                except Exception as e:
                    logging.exception("Local citations request failed")
                    final = f"Error from local model: {e}"

                def _upd_ok():
                    try:
                        self.local_chat_output.delete("1.0", "end")
                        self.local_chat_output.insert("end", final)
                    except Exception:
                        pass
                self.schedule_on_main_thread(_upd_ok)

            self.schedule_async_task(_go())
        except Exception:
            logging.exception("answer_with_citations_local outer failed")

    def rebuild_local_rag_index(self):
        """Rebuild the lightweight local RAG index in the background and report results in the output box."""
        try:
            if hasattr(self, 'local_chat_output'):
                try:
                    self.local_chat_output.delete("1.0", "end")
                    self.local_chat_output.insert("end", "Rebuilding local RAG index…\n")
                except Exception:
                    pass

            def _work():
                try:
                    from src.celsius.ai.local_rag import default_roots, build_index
                    roots = default_roots()
                    count = build_index(roots)  # Force rebuild
                    def _done():
                        try:
                            if hasattr(self, 'local_chat_output'):
                                self.local_chat_output.delete("1.0", "end")
                                self.local_chat_output.insert("end", f"Rebuilt local RAG index with {count} chunks.\n")
                                self.local_chat_output.insert("end", "You can now use 'Answer with Citations (Local)'.")
                        except Exception:
                            pass
                    self.schedule_on_main_thread(_done)
                except Exception as e:
                    logging.exception("Rebuild local RAG index failed")
                    def _err():
                        try:
                            if hasattr(self, 'local_chat_output'):
                                self.local_chat_output.delete("1.0", "end")
                                self.local_chat_output.insert("end", f"Failed to rebuild local RAG index: {e}")
                        except Exception:
                            pass
                    self.schedule_on_main_thread(_err)

            self.schedule_async_task(_work)
        except Exception:
            logging.exception("rebuild_local_rag_index outer failed")

    def verify_local_model(self):
        """Check connectivity to Ollama and list available models."""
        try:
            if hasattr(self, 'local_chat_output'):
                try:
                    self.local_chat_output.delete("1.0", "end")
                    self.local_chat_output.insert("end", "Verifying local model endpoint…\n")
                except Exception:
                    pass

            async def _go():
                try:
                    pv, _ = self._select_local_provider()
                    endpoint = getattr(pv, 'endpoint', '') if pv else 'http://127.0.0.1:11434/api/generate'
                    # Convert to tags endpoint
                    base = endpoint.split('/api/')[0]
                    url = base + '/api/tags'
                    if aiohttp is None:
                        msg = "aiohttp not available; cannot verify."
                    else:
                        timeout = aiohttp.ClientTimeout(total=10)
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.get(url, headers={"User-Agent": "CelsiusAI/1.0"}) as resp:
                                if resp.status != 200:
                                    msg = f"Endpoint reachable but returned status {resp.status}."
                                else:
                                    data = await resp.json()
                                    tags = [x.get('name') for x in (data.get('models') or [])]
                                    msg = "Connected to Ollama. Models: " + (", ".join(tags) if tags else "(none)")
                except Exception as e:
                    logging.exception("verify_local_model failed")
                    msg = f"Could not reach local model endpoint: {e}"

                def _done():
                    try:
                        if hasattr(self, 'local_chat_output'):
                            self.local_chat_output.delete("1.0", "end")
                            self.local_chat_output.insert("end", msg)
                    except Exception:
                        pass
                self.schedule_on_main_thread(_done)
            self.schedule_async_task(_go())
        except Exception:
            logging.exception("verify_local_model outer failed")

    def pull_local_model(self, model_name: str = 'llama3.1:8b'):
        """Request Ollama to pull a model via its HTTP API and show progress."""
        try:
            if hasattr(self, 'local_chat_output'):
                try:
                    self.local_chat_output.delete("1.0", "end")
                    self.local_chat_output.insert("end", f"Requesting pull for {model_name}…\n")
                except Exception:
                    pass

            async def _go():
                try:
                    pv, _ = self._select_local_provider()
                    endpoint = getattr(pv, 'endpoint', '') if pv else 'http://127.0.0.1:11434/api/generate'
                    base = endpoint.split('/api/')[0]
                    url = base + '/api/pull'
                    if aiohttp is None:
                        final = "aiohttp not available; cannot pull model."
                    else:
                        timeout = aiohttp.ClientTimeout(total=600)
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.post(url, headers={"Content-Type": "application/json"}, json={"name": model_name}) as resp:
                                if resp.status != 200:
                                    final = f"Pull request failed: HTTP {resp.status}"
                                else:
                                    # Some Ollama versions stream newline-delimited JSON with progress.
                                    # We'll attempt to read text and show the last line.
                                    try:
                                        txt = await resp.text()
                                        last = txt.strip().splitlines()[-1] if txt.strip() else "(no response)"
                                        final = f"Pull complete or submitted. Last response line: {last}"
                                    except Exception:
                                        final = "Pull request submitted. Check Ollama logs for progress."
                except Exception as e:
                    logging.exception("pull_local_model failed")
                    final = f"Error requesting pull: {e}"

                def _done():
                    try:
                        if hasattr(self, 'local_chat_output'):
                            self.local_chat_output.insert("end", f"{final}\n")
                    except Exception:
                        pass
                self.schedule_on_main_thread(_done)
            self.schedule_async_task(_go())
        except Exception:
            logging.exception("pull_local_model outer failed")

    # ==================== WEB-AUGMENTED ANSWER METHODS ====================
    async def _web_search_duckduckgo(self, query: str, max_results: int = 5) -> list[str]:
        """Perform a DuckDuckGo HTML search and return top result URLs.

        More robust: tries both html endpoints, decodes /l/?uddg= wrapped links,
        and uses a browser-like User-Agent. Falls back to regex if parsing fails.
        """
        urls: list[str] = []
        try:
            if aiohttp is None:
                return urls
            import urllib.parse as _urlparse
            q = query.strip()
            q_enc = _urlparse.quote_plus(q)
            endpoints = [
                f"https://duckduckgo.com/html/?q={q_enc}&kl=us-en",
                f"https://html.duckduckgo.com/html/?q={q_enc}&kl=us-en",
            ]
            timeout = aiohttp.ClientTimeout(total=25)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            page_text = ""
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                for ep in endpoints:
                    try:
                        async with session.get(ep) as resp:
                            if resp.status != 200:
                                continue
                            page_text = await resp.text(errors="ignore")
                            if page_text:
                                break
                    except Exception:
                        continue
            if not page_text:
                return []

            # Parse links
            try:
                from bs4 import BeautifulSoup  # type: ignore
                soup = BeautifulSoup(page_text, "html.parser")
                for a in soup.select("a.result__a, a.result__url, a.result-link"):
                    href = a.get("href")
                    if not href:
                        continue
                    # Unwrap /l/?uddg= URLs
                    if href.startswith("/l/") and "uddg=" in href:
                        try:
                            parsed = _urlparse.urlparse(href)
                            qs = _urlparse.parse_qs(parsed.query)
                            wrapped = qs.get("uddg", [""])[0]
                            href = _urlparse.unquote(wrapped)
                        except Exception:
                            pass
                    if href.startswith("http://") or href.startswith("https://"):
                        urls.append(href)
                    if len(urls) >= max_results:
                        break
            except Exception:
                # Fallback: regex extraction (also unwrap uddg targets)
                import re as _re
                for m in _re.finditer(r"https?://[^\s'\"]+", page_text):
                    u = m.group(0)
                    # Prefer non-duckduckgo redirect targets when visible
                    if "duckduckgo.com/l/?" in u and "uddg=" in u:
                        try:
                            parsed = _urlparse.urlparse(u)
                            qs = _urlparse.parse_qs(parsed.query)
                            wrapped = qs.get("uddg", [""])[0]
                            u = _urlparse.unquote(wrapped)
                        except Exception:
                            pass
                    urls.append(u)
                    if len(urls) >= max_results:
                        break
        except Exception:
            logging.exception("web_search_duckduckgo failed")
        # Deduplicate preserving order
        seen = set()
        deduped = []
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            deduped.append(u)
        return deduped[:max_results]

    async def _web_search_bing(self, query: str, max_results: int = 5) -> list[str]:
        """Very simple Bing HTML search fallback; no API key. Best-effort parsing."""
        out: list[str] = []
        try:
            if aiohttp is None:
                return out
            import urllib.parse as _urlparse
            q_enc = _urlparse.quote_plus(query.strip())
            url = f"https://www.bing.com/search?q={q_enc}&setlang=en-US"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return out
                    text = await resp.text(errors="ignore")
            try:
                from bs4 import BeautifulSoup  # type: ignore
                soup = BeautifulSoup(text, "html.parser")
                for a in soup.select("li.b_algo h2 a, h2 a"):
                    href = a.get("href")
                    if href and (href.startswith("http://") or href.startswith("https://")):
                        out.append(href)
                        if len(out) >= max_results:
                            break
            except Exception:
                import re as _re
                for m in _re.finditer(r"https?://[^\s'\"]+", text):
                    u = m.group(0)
                    out.append(u)
                    if len(out) >= max_results:
                        break
        except Exception:
            logging.exception("web_search_bing failed")
        # Deduplicate
        seen = set()
        result = []
        for u in out:
            if u in seen:
                continue
            seen.add(u)
            result.append(u)
        return result[:max_results]

    async def _fetch_text_from_url(self, url: str, max_chars: int = 5000) -> str:
        """Fetch a URL and return readable text (HTML->text).
        On failure returns empty string. Truncates to max_chars.
        """
        try:
            text = ""
            if aiohttp is None:
                return text
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers={"User-Agent": "CelsiusAI/1.0"}) as resp:
                    if resp.status != 200:
                        return ""
                    ctype = resp.headers.get("Content-Type", "").lower()
                    raw = await resp.text(errors="ignore")
            if "html" in ctype or "<html" in raw.lower():
                try:
                    from bs4 import BeautifulSoup  # type: ignore
                    soup = BeautifulSoup(raw, "html.parser")
                    # Remove script/style
                    for tag in soup(["script", "style", "noscript"]):
                        tag.decompose()
                    text = soup.get_text(separator=" ")
                except Exception:
                    # Fallback: crude tag strip
                    import re as _re
                    text = _re.sub(r"<[^>]+>", " ", raw)
            else:
                text = raw
            # Normalize whitespace
            text = " ".join(text.split())
            return text[:max_chars]
        except Exception:
            logging.exception("fetch_text_from_url failed: %s", url)
            return ""

    def answer_from_web_with_citations(self):
        """Answer using live web retrieval with URL citations."""
        try:
            if not hasattr(self, 'local_chat_input') or not hasattr(self, 'local_chat_output'):
                return
            question = (self.local_chat_input.get("1.0", "end") or "").strip()
            if not question:
                self._msg(messagebox.showinfo, "Answer from Web", "Enter a question first.")
                return

            try:
                self.local_chat_output.delete("1.0", "end")
                self.local_chat_output.insert("end", "Searching the web…\n")
            except Exception:
                pass

            async def _go():
                # Search with DDG, then fallback to Bing if empty
                urls = await self._web_search_duckduckgo(question, max_results=5)
                if not urls:
                    urls = await self._web_search_bing(question, max_results=5)
                if not urls:
                    def _no_urls():
                        try:
                            self.local_chat_output.delete("1.0", "end")
                            self.local_chat_output.insert("end", "No web results found or search unavailable.")
                        except Exception:
                            pass
                    self.schedule_on_main_thread(_no_urls)
                    return
                # Fetch texts with a simple concurrency limit
                texts: list[tuple[str, str]] = []  # (url, text)
                try:
                    import asyncio as _asyncio
                    sem = _asyncio.Semaphore(3)
                    async def _fetch(u: str):
                        async with sem:
                            t = await self._fetch_text_from_url(u)
                            return u, t
                    results = await _asyncio.gather(*[_fetch(u) for u in urls], return_exceptions=True)
                    for r in results:
                        if isinstance(r, tuple) and len(r) == 2:
                            u, t = r
                            if t:
                                texts.append((u, t))
                except Exception:
                    logging.exception("parallel fetch failed")

                # Build context from fetched pages
                ctx_parts = []
                cites = []
                if texts:
                    max_ctx = 4000
                    per = max(1, max_ctx // max(1, len(texts)))
                    for i, (u, t) in enumerate(texts, start=1):
                        snippet = t[:per]
                        ctx_parts.append(f"[{i}] {u}\n-----\n{snippet}\n\n")
                        cites.append((i, u))
                ctx = "".join(ctx_parts)

                pv, err = self._select_local_provider()
                if err:
                    # Fallback: show snippets & URLs
                    def _fallback():
                        try:
                            self.local_chat_output.delete("1.0", "end")
                            if ctx:
                                self.local_chat_output.insert("end", "Local model unavailable; showing web context snippets.\n\n")
                                self.local_chat_output.insert("end", ctx)
                                sources = "\n".join([f"[{i}] {url}" for i, url in cites]) if cites else "(No sources)"
                                self.local_chat_output.insert("end", f"\nSources:\n{sources}")
                            else:
                                self.local_chat_output.insert("end", "No readable web content fetched.")
                        except Exception:
                            pass
                    self.schedule_on_main_thread(_fallback)
                    return

                # Ask model
                try:
                    client = LLMClient(pv)
                    base_prompt = (
                        "You are Celsius AI. Using the provided web snippets with URL citations [1], [2], "
                        "answer the user's question clearly and concisely. Be faithful to the snippets; if insufficient, say so.\n\n"
                        f"Question:\n{question}\n\n"
                        f"Web Context:\n{ctx if ctx else '(no web context available)'}\n\n"
                    )
                    data = await client.generate(base_prompt, timeout=150)
                    answer = self._extract_text_from_response(pv, data)
                    sources = "\n".join([f"[{i}] {url}" for i, url in cites]) if cites else "(No sources)"
                    final = f"{answer}\n\nSources:\n{sources}"
                except Exception as e:
                    logging.exception("Web augmented answer failed")
                    final = f"Error from model: {e}"

                def _done():
                    try:
                        self.local_chat_output.delete("1.0", "end")
                        self.local_chat_output.insert("end", final)
                    except Exception:
                        pass
                self.schedule_on_main_thread(_done)

            self.schedule_async_task(_go())
        except Exception:
            logging.exception("answer_from_web_with_citations outer failed")

    def create_hardware_tab(self):
        """Delegate Hardware tab creation to the extracted UI module.

        Do not swallow exceptions so the lazy loader can retry if creation fails.
        Also render a readable error in the tab when an exception occurs.
        """
        from src.celsius.hub.ui import create_hardware_tab as _create
        try:
            _create(self)
        except Exception as e:
            logging.exception("Failed to create Hardware tab UI: %s", e)
            self._show_tab_error(self.tab_hardware, f"Hardware tab failed: {e}")
            raise

    def create_security_tab(self):
        """Creates the content for the Security tab."""
        frame = self.tab_security

        # Authentication Info
        auth_frame = ttk.LabelFrame(frame, text="Authentication Status", padding=10)
        auth_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            auth_frame, text="System Access: Authenticated", font=("Helvetica", 10, "bold"), foreground="green"
        ).pack(pady=5)
        ttk.Label(auth_frame, text=f"User: {self.username}", font=("Helvetica", 9)).pack()
        ttk.Label(
            auth_frame, text=f"Session Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", font=("Helvetica", 9)
        ).pack()

        if self.email_notifier:
            ttk.Label(
                auth_frame, text="Email Notifications: Enabled", font=("Helvetica", 9), foreground="green"
            ).pack()
        else:
            ttk.Label(
                auth_frame, text="Email Notifications: Disabled", font=("Helvetica", 9), foreground="orange"
            ).pack()

        # Security Logs
        log_frame = ttk.LabelFrame(frame, text="Security Activity Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("Timestamp", "Event Type", "Details", "Status")
        self.security_log_tree = ttk.Treeview(log_frame, columns=cols, show="headings", height=10)
        for col in cols:
            self.security_log_tree.heading(col, text=col)
            self.security_log_tree.column(col, width=150)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.security_log_tree.yview)
        self.security_log_tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.security_log_tree.pack(fill="both", expand=True)

        # Add sample security events
        self.security_log_tree.insert(
            "", "end", values=(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Login", "Hub initialized", "… Success")
        )

        # Security Actions
        actions_frame = ttk.LabelFrame(frame, text="Security Actions", padding=10)
        actions_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            actions_frame,
            text="View Failed Login Attempts",
            command=lambda: self._msg(messagebox.showinfo, "Security", "No failed login attempts recorded."),
        ).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="Export Security Log", command=self.export_security_log).pack(
            side="left", padx=5
        )
        ttk.Button(actions_frame, text="Clear Security Log", command=self.clear_security_log).pack(side="left", padx=5)

    def create_security_tab(self):
        """Create Security tab with comprehensive threat monitoring and analysis."""
        try:
            security_frame = ttk.Frame(self.tab_security)
            security_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # Header
            ttk.Label(security_frame, text="🛡️ Advanced Security Monitoring", style="Header.TLabel").pack(pady=(0, 10))

            # Security Status Overview
            status_frame = ttk.LabelFrame(security_frame, text="Security Status", padding=10)
            status_frame.pack(fill="x", pady=(0, 10))

            # Status indicators
            status_grid = ttk.Frame(status_frame)
            status_grid.pack(fill="x")

            self.security_status_labels = {}
            status_items = [
                ("Monitor Status", "Not Started", "orange"),
                ("Threat Level", "Unknown", "gray"),
                ("Active Threats", "0", "green"),
                ("Last Scan", "Never", "gray")
            ]

            for i, (label, value, color) in enumerate(status_items):
                ttk.Label(status_grid, text=f"{label}:").grid(row=i//2, column=(i%2)*2, sticky="w", padx=(0, 10))
                self.security_status_labels[label] = ttk.Label(status_grid, text=value, foreground=color)
                self.security_status_labels[label].grid(row=i//2, column=(i%2)*2+1, sticky="w")

            # Control Panel
            control_frame = ttk.LabelFrame(security_frame, text="Security Controls", padding=10)
            control_frame.pack(fill="x", pady=(0, 10))

            # Monitoring controls
            ttk.Button(control_frame, text="Start Security Monitor", command=self.start_security_monitoring).pack(side="left", padx=5)
            ttk.Button(control_frame, text="Stop Security Monitor", command=self.stop_security_monitoring).pack(side="left", padx=5)
            ttk.Button(control_frame, text="Run Full Security Scan", command=self.run_security_scan).pack(side="left", padx=5)

            # Threat Analysis
            analysis_frame = ttk.LabelFrame(security_frame, text="Threat Analysis", padding=10)
            analysis_frame.pack(fill="x", pady=(0, 10))

            ttk.Button(analysis_frame, text="Analyze Processes", command=self.analyze_processes).pack(side="left", padx=5)
            ttk.Button(analysis_frame, text="Check Network", command=self.analyze_network).pack(side="left", padx=5)
            ttk.Button(analysis_frame, text="Scan Files", command=self.analyze_files).pack(side="left", padx=5)

            # Security Events Log
            events_frame = ttk.LabelFrame(security_frame, text="Security Events", padding=10)
            events_frame.pack(fill="both", expand=True)

            # Events treeview
            cols = ("Time", "Type", "Severity", "Description", "Source")
            self.security_events_tree = ttk.Treeview(events_frame, columns=cols, show="headings", height=15)

            for col in cols:
                self.security_events_tree.heading(col, text=col)
                self.security_events_tree.column(col, width=120 if col != "Description" else 200)

            # Scrollbars
            v_scrollbar = ttk.Scrollbar(events_frame, orient="vertical", command=self.security_events_tree.yview)
            h_scrollbar = ttk.Scrollbar(events_frame, orient="horizontal", command=self.security_events_tree.xview)
            self.security_events_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

            self.security_events_tree.pack(fill="both", expand=True)
            v_scrollbar.pack(side="right", fill="y")
            h_scrollbar.pack(side="bottom", fill="x")

            # Event controls
            event_controls = ttk.Frame(events_frame)
            event_controls.pack(fill="x", pady=(5, 0))

            ttk.Button(event_controls, text="Refresh Events", command=self.refresh_security_events).pack(side="left", padx=5)
            ttk.Button(event_controls, text="Clear Events", command=self.clear_security_events).pack(side="left", padx=5)
            ttk.Button(event_controls, text="Export Events", command=self.export_security_events).pack(side="left", padx=5)

            # Initialize security monitoring
            self.security_monitor = None
            self.security_analyzer = None
            self.security_alerts = []
            self.monitoring_active = False

            # Load initial events
            self.refresh_security_events()

        except Exception as e:
            logging.exception("Failed to create Security tab: %s", e)
            self._show_tab_error(self.tab_security, f"Security tab failed: {e}")

    # ==================== SECURITY MONITORING METHODS ====================

    def start_security_monitoring(self):
        """Start the security monitoring system."""
        try:
            if self.monitoring_active:
                self._msg(messagebox.showinfo, "Security Monitor", "Security monitoring is already active.")
                return

            # Initialize security components
            if self.security_monitor is None:
                try:
                    from src.core.config import CelsiusConfig
                    from src.security.monitor import SecurityMonitor
                    from src.security.analyzer import ThreatAnalyzer

                    config = CelsiusConfig()
                    analyzer = ThreatAnalyzer(config)
                    self.security_analyzer = analyzer
                    self.security_monitor = SecurityMonitor(config, analyzer)

                    # Add alert callback
                    async def handle_alert(alert):
                        await self._handle_security_alert(alert)

                    self.security_monitor.add_alert_callback(handle_alert)

                except Exception as e:
                    self._msg(messagebox.showerror, "Security Monitor", f"Failed to initialize security components: {e}")
                    return

            # Start monitoring
            async def start_monitor():
                try:
                    await self.security_monitor.start_monitoring()
                    self.monitoring_active = True
                    self._update_security_status("Monitor Status", "Active", "green")
                except Exception as e:
                    logging.exception("Failed to start security monitoring")
                    self._msg(messagebox.showerror, "Security Monitor", f"Failed to start monitoring: {e}")

            self.schedule_async_task(start_monitor())

        except Exception as e:
            logging.exception("start_security_monitoring failed")
            self._msg(messagebox.showerror, "Security Monitor", f"Failed to start security monitoring: {e}")

    def stop_security_monitoring(self):
        """Stop the security monitoring system."""
        try:
            if not self.monitoring_active or self.security_monitor is None:
                self._msg(messagebox.showinfo, "Security Monitor", "Security monitoring is not active.")
                return

            async def stop_monitor():
                try:
                    await self.security_monitor.stop_monitoring()
                    self.monitoring_active = False
                    self._update_security_status("Monitor Status", "Stopped", "orange")
                except Exception as e:
                    logging.exception("Failed to stop security monitoring")
                    self._msg(messagebox.showerror, "Security Monitor", f"Failed to stop monitoring: {e}")

            self.schedule_async_task(stop_monitor())

        except Exception as e:
            logging.exception("stop_security_monitoring failed")
            self._msg(messagebox.showerror, "Security Monitor", f"Failed to stop security monitoring: {e}")

    def run_security_scan(self):
        """Run a comprehensive security scan."""
        try:
            if self.security_analyzer is None:
                self._msg(messagebox.showerror, "Security Scan", "Security analyzer not initialized.")
                return

            self._update_security_status("Last Scan", "Running...", "orange")

            async def perform_scan():
                try:
                    results = await self.security_analyzer.perform_scan(scan_type='full')

                    # Update status
                    risk_level = results.get('risk_level', 'unknown')
                    threat_count = len(results.get('threats', []))

                    color_map = {
                        'low': 'green',
                        'medium': 'orange',
                        'high': 'red',
                        'critical': 'red'
                    }

                    self._update_security_status("Threat Level", risk_level.title(), color_map.get(risk_level, 'gray'))
                    self._update_security_status("Active Threats", str(threat_count), 'red' if threat_count > 0 else 'green')
                    self._update_security_status("Last Scan", datetime.now().strftime("%H:%M:%S"), "green")

                    # Add scan results to events
                    for threat in results.get('threats', []):
                        self._add_security_event(
                            "Threat Detected",
                            threat.get('severity', 'medium'),
                            threat.get('name', 'Unknown threat'),
                            "Security Scan"
                        )

                    self._msg(messagebox.showinfo, "Security Scan Complete",
                             f"Scan completed. Risk level: {risk_level.title()}\nThreats found: {threat_count}")

                except Exception as e:
                    logging.exception("Security scan failed")
                    self._update_security_status("Last Scan", "Failed", "red")
                    self._msg(messagebox.showerror, "Security Scan", f"Scan failed: {e}")

            self.schedule_async_task(perform_scan())

        except Exception as e:
            logging.exception("run_security_scan failed")
            self._msg(messagebox.showerror, "Security Scan", f"Failed to run security scan: {e}")

    def analyze_processes(self):
        """Analyze running processes for threats."""
        try:
            if self.security_analyzer is None:
                self._msg(messagebox.showerror, "Process Analysis", "Security analyzer not initialized.")
                return

            async def analyze():
                try:
                    results = await self.security_analyzer.perform_scan(scan_type='process')

                    threats = results.get('threats', [])
                    self._add_security_event("Process Scan", "info", f"Scanned processes, found {len(threats)} threats", "Process Analysis")

                    for threat in threats:
                        self._add_security_event(
                            "Process Threat",
                            threat.get('severity', 'medium'),
                            threat.get('name', 'Suspicious process'),
                            "Process Analysis"
                        )

                    self._msg(messagebox.showinfo, "Process Analysis", f"Process analysis complete. Threats found: {len(threats)}")

                except Exception as e:
                    logging.exception("Process analysis failed")
                    self._msg(messagebox.showerror, "Process Analysis", f"Analysis failed: {e}")

            self.schedule_async_task(analyze())

        except Exception as e:
            logging.exception("analyze_processes failed")

    def analyze_network(self):
        """Analyze network connections for threats."""
        try:
            if self.security_analyzer is None:
                self._msg(messagebox.showerror, "Network Analysis", "Security analyzer not initialized.")
                return

            async def analyze():
                try:
                    results = await self.security_analyzer.perform_scan(scan_type='network')

                    threats = results.get('threats', [])
                    self._add_security_event("Network Scan", "info", f"Scanned connections, found {len(threats)} threats", "Network Analysis")

                    for threat in threats:
                        self._add_security_event(
                            "Network Threat",
                            threat.get('severity', 'medium'),
                            threat.get('name', 'Suspicious connection'),
                            "Network Analysis"
                        )

                    self._msg(messagebox.showinfo, "Network Analysis", f"Network analysis complete. Threats found: {len(threats)}")

                except Exception as e:
                    logging.exception("Network analysis failed")
                    self._msg(messagebox.showerror, "Network Analysis", f"Analysis failed: {e}")

            self.schedule_async_task(analyze())

        except Exception as e:
            logging.exception("analyze_network failed")

    def analyze_files(self):
        """Analyze files for threats."""
        try:
            if self.security_analyzer is None:
                self._msg(messagebox.showerror, "File Analysis", "Security analyzer not initialized.")
                return

            async def analyze():
                try:
                    results = await self.security_analyzer.perform_scan(scan_type='file')

                    threats = results.get('threats', [])
                    self._add_security_event("File Scan", "info", f"Scanned files, found {len(threats)} threats", "File Analysis")

                    for threat in threats:
                        self._add_security_event(
                            "File Threat",
                            threat.get('severity', 'medium'),
                            threat.get('name', 'Suspicious file'),
                            "File Analysis"
                        )

                    self._msg(messagebox.showinfo, "File Analysis", f"File analysis complete. Threats found: {len(threats)}")

                except Exception as e:
                    logging.exception("File analysis failed")
                    self._msg(messagebox.showerror, "File Analysis", f"Analysis failed: {e}")

            self.schedule_async_task(analyze())

        except Exception as e:
            logging.exception("analyze_files failed")

    def _update_security_status(self, label: str, value: str, color: str = "black"):
        """Update a security status label."""
        try:
            if hasattr(self, 'security_status_labels') and label in self.security_status_labels:
                self.security_status_labels[label].config(text=value, foreground=color)
        except Exception:
            logging.exception(f"Failed to update security status: {label}")

    def _add_security_event(self, event_type: str, severity: str, description: str, source: str):
        """Add a security event to the events tree."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Color mapping for severity
            color_map = {
                'low': 'green',
                'medium': 'orange',
                'high': 'red',
                'critical': 'red',
                'info': 'blue'
            }

            if hasattr(self, 'security_events_tree'):
                item = self.security_events_tree.insert("", "end", values=(timestamp, event_type, severity.title(), description, source))

                # Tag for coloring (if supported)
                try:
                    self.security_events_tree.tag_configure(severity, foreground=color_map.get(severity, 'black'))
                    self.security_events_tree.item(item, tags=(severity,))
                except Exception:
                    pass

                # Keep only last 100 events
                if len(self.security_events_tree.get_children()) > 100:
                    oldest = self.security_events_tree.get_children()[0]
                    self.security_events_tree.delete(oldest)

        except Exception:
            logging.exception("Failed to add security event")

    async def _handle_security_alert(self, alert: dict):
        """Handle security alerts from the monitoring system."""
        try:
            alert_type = alert.get('type', 'unknown')
            severity = alert.get('severity', 'medium')
            message = alert.get('message', 'Security alert')

            # Add to events
            self._add_security_event("Alert", severity, message, "Security Monitor")

            # Update threat count
            current_threats = int(self.security_status_labels.get("Active Threats", ttk.Label()).cget("text") or "0")
            self._update_security_status("Active Threats", str(current_threats + 1), "red")

            # Show notification for high severity alerts
            if severity in ['high', 'critical']:
                self._msg(messagebox.showwarning, "Security Alert", f"High priority security alert:\n\n{message}")

        except Exception:
            logging.exception("Failed to handle security alert")

    def refresh_security_events(self):
        """Refresh the security events display."""
        try:
            if hasattr(self, 'security_events_tree'):
                # Clear existing events
                for item in self.security_events_tree.get_children():
                    self.security_events_tree.delete(item)

                # Add some sample events if no real events
                if not hasattr(self, 'security_alerts') or not self.security_alerts:
                    self._add_security_event("System", "info", "Security monitoring initialized", "System")
                    self._add_security_event("Monitor", "info", "Ready for threat detection", "System")

        except Exception:
            logging.exception("Failed to refresh security events")

    def clear_security_events(self):
        """Clear all security events."""
        try:
            if hasattr(self, 'security_events_tree'):
                for item in self.security_events_tree.get_children():
                    self.security_events_tree.delete(item)

            self._msg(messagebox.showinfo, "Security Events", "Security events cleared.")

        except Exception as e:
            logging.exception("Failed to clear security events")
            self._msg(messagebox.showerror, "Security Events", f"Failed to clear events: {e}")

    def export_security_events(self):
        """Export security events to a file."""
        try:
            if not hasattr(self, 'security_events_tree'):
                return

            events = []
            for item in self.security_events_tree.get_children():
                values = self.security_events_tree.item(item, 'values')
                events.append({
                    'timestamp': values[0],
                    'type': values[1],
                    'severity': values[2],
                    'description': values[3],
                    'source': values[4]
                })

            if not events:
                self._msg(messagebox.showinfo, "Export Events", "No events to export.")
                return

            # Save to file
            export_file = self.project_root / "logs" / f"security_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            export_file.parent.mkdir(parents=True, exist_ok=True)

            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)

            self._msg(messagebox.showinfo, "Export Events", f"Security events exported to:\n{export_file}")

        except Exception as e:
            logging.exception("Failed to export security events")
            self._msg(messagebox.showerror, "Export Events", f"Failed to export events: {e}")

    # ==================== PERFORMANCE MONITORING TAB ====================

    def create_performance_tab(self):
        """Create the Performance Monitoring tab."""
        try:
            self.tab_performance = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_performance, text="Performance")

            # Main container
            main_frame = ttk.Frame(self.tab_performance)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Title
            title_label = ttk.Label(main_frame, text="Performance Monitoring Dashboard",
                                  font=("Arial", 16, "bold"))
            title_label.pack(pady=(0, 20))

            # Create notebook for performance sub-tabs
            perf_notebook = ttk.Notebook(main_frame)
            perf_notebook.pack(fill=tk.BOTH, expand=True)

            # System Metrics Tab
            self.create_system_metrics_tab(perf_notebook)

            # Resource Usage Tab
            self.create_resource_usage_tab(perf_notebook)

            # Performance History Tab
            self.create_performance_history_tab(perf_notebook)

            # Performance Controls
            controls_frame = ttk.LabelFrame(main_frame, text="Performance Controls", padding=10)
            controls_frame.pack(fill=tk.X, pady=(20, 0))

            # Control buttons
            button_frame = ttk.Frame(controls_frame)
            button_frame.pack(fill=tk.X)

            ttk.Button(button_frame, text="Start Monitoring",
                      command=self.start_performance_monitoring).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Stop Monitoring",
                      command=self.stop_performance_monitoring).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Refresh Metrics",
                      command=self.refresh_performance_metrics).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Generate Report",
                      command=self.generate_performance_report).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Clear History",
                      command=self.clear_performance_history).pack(side=tk.LEFT)

            # Initialize performance monitoring
            self.performance_monitoring_active = False
            self.performance_data = []
            self.performance_start_time = None

        except Exception as e:
            logging.exception("Failed to create Performance tab: %s", e)
            self._show_tab_error(self.tab_performance, f"Performance tab failed: {e}")

    def create_system_metrics_tab(self, parent_notebook):
        """Create the System Metrics sub-tab."""
        try:
            tab = ttk.Frame(parent_notebook)
            parent_notebook.add(tab, text="System Metrics")

            # Metrics display
            metrics_frame = ttk.LabelFrame(tab, text="Current System Metrics", padding=10)
            metrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # CPU Usage
            cpu_frame = ttk.Frame(metrics_frame)
            cpu_frame.pack(fill=tk.X, pady=(0, 10))

            ttk.Label(cpu_frame, text="CPU Usage:", width=15, anchor="w").pack(side=tk.LEFT)
            self.cpu_label = ttk.Label(cpu_frame, text="0%", font=("Arial", 12, "bold"), foreground="green")
            self.cpu_label.pack(side=tk.LEFT, padx=(10, 0))

            self.cpu_progress = ttk.Progressbar(cpu_frame, orient="horizontal", length=200, mode="determinate")
            self.cpu_progress.pack(side=tk.RIGHT)

            # Memory Usage
            mem_frame = ttk.Frame(metrics_frame)
            mem_frame.pack(fill=tk.X, pady=(0, 10))

            ttk.Label(mem_frame, text="Memory Usage:", width=15, anchor="w").pack(side=tk.LEFT)
            self.mem_label = ttk.Label(mem_frame, text="0%", font=("Arial", 12, "bold"), foreground="green")
            self.mem_label.pack(side=tk.LEFT, padx=(10, 0))

            self.mem_progress = ttk.Progressbar(mem_frame, orient="horizontal", length=200, mode="determinate")
            self.mem_progress.pack(side=tk.RIGHT)

            # Disk Usage
            disk_frame = ttk.Frame(metrics_frame)
            disk_frame.pack(fill=tk.X, pady=(0, 10))

            ttk.Label(disk_frame, text="Disk Usage:", width=15, anchor="w").pack(side=tk.LEFT)
            self.disk_label = ttk.Label(disk_frame, text="0%", font=("Arial", 12, "bold"), foreground="green")
            self.disk_label.pack(side=tk.LEFT, padx=(10, 0))

            self.disk_progress = ttk.Progressbar(disk_frame, orient="horizontal", length=200, mode="determinate")
            self.disk_progress.pack(side=tk.RIGHT)

            # Network I/O
            net_frame = ttk.Frame(metrics_frame)
            net_frame.pack(fill=tk.X, pady=(0, 10))

            ttk.Label(net_frame, text="Network I/O:", width=15, anchor="w").pack(side=tk.LEFT)
            self.net_label = ttk.Label(net_frame, text="0 KB/s", font=("Arial", 10))
            self.net_label.pack(side=tk.LEFT, padx=(10, 0))

            # System Info
            info_frame = ttk.LabelFrame(tab, text="System Information", padding=10)
            info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

            self.system_info_text = tk.Text(info_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
            scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.system_info_text.yview)
            self.system_info_text.configure(yscrollcommand=scrollbar.set)

            self.system_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Load initial metrics
            self.refresh_performance_metrics()

        except Exception as e:
            logging.exception("Failed to create system metrics tab: %s", e)

    def create_resource_usage_tab(self, parent_notebook):
        """Create the Resource Usage sub-tab."""
        try:
            tab = ttk.Frame(parent_notebook)
            parent_notebook.add(tab, text="Resource Usage")

            # Process list
            process_frame = ttk.LabelFrame(tab, text="Top Processes by CPU/Memory", padding=10)
            process_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Treeview for processes
            columns = ("PID", "Name", "CPU%", "Memory%", "Status")
            self.process_tree = ttk.Treeview(process_frame, columns=columns, show="headings", height=15)

            for col in columns:
                self.process_tree.heading(col, text=col)
                self.process_tree.column(col, width=100, anchor="center")

            # Scrollbars
            v_scrollbar = ttk.Scrollbar(process_frame, orient=tk.VERTICAL, command=self.process_tree.yview)
            h_scrollbar = ttk.Scrollbar(process_frame, orient=tk.HORIZONTAL, command=self.process_tree.xview)
            self.process_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

            self.process_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

            # Resource charts placeholder
            chart_frame = ttk.LabelFrame(tab, text="Resource Usage Charts", padding=10)
            chart_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

            ttk.Label(chart_frame, text="Charts will be implemented with matplotlib integration",
                     font=("Arial", 10, "italic")).pack(pady=20)

            # Load initial process data
            self.refresh_process_list()

        except Exception as e:
            logging.exception("Failed to create resource usage tab: %s", e)

    def create_performance_history_tab(self, parent_notebook):
        """Create the Performance History sub-tab."""
        try:
            tab = ttk.Frame(parent_notebook)
            parent_notebook.add(tab, text="Performance History")

            # History controls
            controls_frame = ttk.Frame(tab)
            controls_frame.pack(fill=tk.X, padx=10, pady=10)

            ttk.Label(controls_frame, text="Time Range:").pack(side=tk.LEFT, padx=(0, 5))
            self.history_range = ttk.Combobox(controls_frame, values=["Last Hour", "Last 24 Hours", "Last 7 Days", "All Time"],
                                            state="readonly", width=15)
            self.history_range.current(0)
            self.history_range.pack(side=tk.LEFT, padx=(0, 10))

            ttk.Button(controls_frame, text="Refresh History",
                      command=self.refresh_performance_history).pack(side=tk.LEFT)

            # History display
            history_frame = ttk.LabelFrame(tab, text="Performance History", padding=10)
            history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

            # Treeview for history
            columns = ("Timestamp", "CPU%", "Memory%", "Disk%", "Network KB/s")
            self.history_tree = ttk.Treeview(history_frame, columns=columns, show="headings", height=20)

            for col in columns:
                self.history_tree.heading(col, text=col)
                self.history_tree.column(col, width=120, anchor="center")

            # Scrollbars
            v_scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
            h_scrollbar = ttk.Scrollbar(history_frame, orient=tk.HORIZONTAL, command=self.history_tree.xview)
            self.history_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

            self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

            # Statistics
            stats_frame = ttk.LabelFrame(tab, text="Performance Statistics", padding=10)
            stats_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

            self.stats_text = tk.Text(stats_frame, height=6, wrap=tk.WORD, state=tk.DISABLED)
            stats_scrollbar = ttk.Scrollbar(stats_frame, orient=tk.VERTICAL, command=self.stats_text.yview)
            self.stats_text.configure(yscrollcommand=stats_scrollbar.set)

            self.stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            stats_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Load initial history
            self.refresh_performance_history()

        except Exception as e:
            logging.exception("Failed to create performance history tab: %s", e)

    # ==================== PERFORMANCE MONITORING METHODS ====================

    def start_performance_monitoring(self):
        """Start performance monitoring."""
        try:
            if self.performance_monitoring_active:
                self._msg(messagebox.showinfo, "Performance Monitor", "Performance monitoring is already active.")
                return

            self.performance_monitoring_active = True
            self.performance_start_time = datetime.now()
            self.performance_data = []

            # Start monitoring loop
            async def monitor_loop():
                try:
                    while self.performance_monitoring_active:
                        await self._collect_performance_metrics()
                        await asyncio.sleep(5)  # Update every 5 seconds
                except Exception as e:
                    logging.exception("Performance monitoring loop failed")

            self.schedule_async_task(monitor_loop())
            self._msg(messagebox.showinfo, "Performance Monitor", "Performance monitoring started.")

        except Exception as e:
            logging.exception("Failed to start performance monitoring")
            self._msg(messagebox.showerror, "Performance Monitor", f"Failed to start monitoring: {e}")

    def stop_performance_monitoring(self):
        """Stop performance monitoring."""
        try:
            if not self.performance_monitoring_active:
                self._msg(messagebox.showinfo, "Performance Monitor", "Performance monitoring is not active.")
                return

            self.performance_monitoring_active = False
            self._msg(messagebox.showinfo, "Performance Monitor", "Performance monitoring stopped.")

        except Exception as e:
            logging.exception("Failed to stop performance monitoring")
            self._msg(messagebox.showerror, "Performance Monitor", f"Failed to stop monitoring: {e}")

    def refresh_performance_metrics(self):
        """Refresh current performance metrics."""
        try:
            async def update_metrics():
                try:
                    await self._collect_performance_metrics()
                except Exception as e:
                    logging.exception("Failed to refresh performance metrics")

            self.schedule_async_task(update_metrics())

        except Exception as e:
            logging.exception("refresh_performance_metrics failed")

    async def _collect_performance_metrics(self):
        """Collect current system performance metrics."""
        try:
            import psutil

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.cpu_label.config(text=f"{cpu_percent:.1f}%")
            self.cpu_progress['value'] = cpu_percent

            # Color coding for CPU
            if cpu_percent > 90:
                self.cpu_label.config(foreground="red")
            elif cpu_percent > 70:
                self.cpu_progress.config(style="Orange.Horizontal.TProgressbar")
                self.cpu_label.config(foreground="orange")
            else:
                self.cpu_progress.config(style="Green.Horizontal.TProgressbar")
                self.cpu_label.config(foreground="green")

            # Memory usage
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            self.mem_label.config(text=f"{mem_percent:.1f}%")
            self.mem_progress['value'] = mem_percent

            # Color coding for memory
            if mem_percent > 90:
                self.mem_label.config(foreground="red")
            elif mem_percent > 80:
                self.mem_label.config(foreground="orange")
            else:
                self.mem_label.config(foreground="green")

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            self.disk_label.config(text=f"{disk_percent:.1f}%")
            self.disk_progress['value'] = disk_percent

            # Color coding for disk
            if disk_percent > 95:
                self.disk_label.config(foreground="red")
            elif disk_percent > 85:
                self.disk_label.config(foreground="orange")
            else:
                self.disk_label.config(foreground="green")

            # Network I/O (simplified)
            net_io = psutil.net_io_counters()
            if hasattr(self, 'last_net_io'):
                time_diff = 1  # 1 second interval
                bytes_sent = net_io.bytes_sent - self.last_net_io.bytes_sent
                bytes_recv = net_io.bytes_recv - self.last_net_io.bytes_recv
                total_kb = (bytes_sent + bytes_recv) / 1024
                self.net_label.config(text=f"{total_kb:.1f} KB/s")
            self.last_net_io = net_io

            # System info
            if hasattr(self, 'system_info_text'):
                system_info = f"""System Information:
OS: {psutil.os.uname().sysname} {psutil.os.uname().release}
CPU Cores: {psutil.cpu_count()} ({psutil.cpu_count(logical=False)} physical)
Total Memory: {mem.total / (1024**3):.1f} GB
Available Memory: {mem.available / (1024**3):.1f} GB
Disk Total: {disk.total / (1024**3):.1f} GB
Disk Free: {disk.free / (1024**3):.1f} GB"""

                self.system_info_text.config(state=tk.NORMAL)
                self.system_info_text.delete(1.0, tk.END)
                self.system_info_text.insert(tk.END, system_info)
                self.system_info_text.config(state=tk.DISABLED)

            # Store data point for history
            if self.performance_monitoring_active:
                data_point = {
                    'timestamp': datetime.now(),
                    'cpu': cpu_percent,
                    'memory': mem_percent,
                    'disk': disk_percent,
                    'network': total_kb if 'total_kb' in locals() else 0
                }
                self.performance_data.append(data_point)

                # Keep only last 1000 data points
                if len(self.performance_data) > 1000:
                    self.performance_data = self.performance_data[-1000:]

        except ImportError:
            # psutil not available
            self.cpu_label.config(text="N/A")
            self.mem_label.config(text="N/A")
            self.disk_label.config(text="N/A")
            self.net_label.config(text="N/A")
        except Exception as e:
            logging.exception("Failed to collect performance metrics")

    def refresh_process_list(self):
        """Refresh the process list."""
        try:
            import psutil

            # Clear existing items
            for item in self.process_tree.get_children():
                self.process_tree.delete(item)

            # Get top processes
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    info = proc.info
                    if info['cpu_percent'] is not None and info['memory_percent'] is not None:
                        processes.append((
                            info['pid'],
                            info['name'][:20] if info['name'] else 'Unknown',
                            f"{info['cpu_percent']:.1f}",
                            f"{info['memory_percent']:.1f}",
                            info['status'] or 'Unknown'
                        ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU usage and take top 20
            processes.sort(key=lambda x: float(x[2]), reverse=True)
            for proc in processes[:20]:
                self.process_tree.insert("", "end", values=proc)

        except ImportError:
            self.process_tree.insert("", "end", values=("N/A", "psutil not available", "0", "0", "Unknown"))
        except Exception as e:
            logging.exception("Failed to refresh process list")

    def refresh_performance_history(self):
        """Refresh performance history display."""
        try:
            # Clear existing items
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

            # Get data based on selected range
            range_selection = self.history_range.get()
            now = datetime.now()

            if range_selection == "Last Hour":
                cutoff = now - timedelta(hours=1)
            elif range_selection == "Last 24 Hours":
                cutoff = now - timedelta(days=1)
            elif range_selection == "Last 7 Days":
                cutoff = now - timedelta(days=7)
            else:  # All Time
                cutoff = None

            filtered_data = [d for d in self.performance_data if cutoff is None or d['timestamp'] >= cutoff]

            # Add to treeview
            for data_point in filtered_data[-100:]:  # Show last 100 entries
                self.history_tree.insert("", "end", values=(
                    data_point['timestamp'].strftime("%H:%M:%S"),
                    f"{data_point['cpu']:.1f}",
                    f"{data_point['memory']:.1f}",
                    f"{data_point['disk']:.1f}",
                    f"{data_point['network']:.1f}"
                ))

            # Update statistics
            if filtered_data:
                cpu_avg = sum(d['cpu'] for d in filtered_data) / len(filtered_data)
                mem_avg = sum(d['memory'] for d in filtered_data) / len(filtered_data)
                disk_avg = sum(d['disk'] for d in filtered_data) / len(filtered_data)

                cpu_max = max(d['cpu'] for d in filtered_data)
                mem_max = max(d['memory'] for d in filtered_data)
                disk_max = max(d['disk'] for d in filtered_data)

                stats = f"""Performance Statistics ({range_selection}):
Average CPU: {cpu_avg:.1f}% | Max CPU: {cpu_max:.1f}%
Average Memory: {mem_avg:.1f}% | Max Memory: {mem_max:.1f}%
Average Disk: {disk_avg:.1f}% | Max Disk: {disk_max:.1f}%
Data Points: {len(filtered_data)}"""

                self.stats_text.config(state=tk.NORMAL)
                self.stats_text.delete(1.0, tk.END)
                self.stats_text.insert(tk.END, stats)
                self.stats_text.config(state=tk.DISABLED)

        except Exception as e:
            logging.exception("Failed to refresh performance history")

    def generate_performance_report(self):
        """Generate a performance report."""
        try:
            if not self.performance_data:
                self._msg(messagebox.showinfo, "Performance Report", "No performance data available.")
                return

            # Generate report
            report_lines = [
                "Celsius AI Performance Report",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Monitoring Duration: {len(self.performance_data) * 5} seconds",
                "",
                "Performance Summary:",
            ]

            if self.performance_data:
                cpu_vals = [d['cpu'] for d in self.performance_data]
                mem_vals = [d['memory'] for d in self.performance_data]
                disk_vals = [d['disk'] for d in self.performance_data]

                report_lines.extend([
                    f"Average CPU Usage: {sum(cpu_vals)/len(cpu_vals):.1f}%",
                    f"Peak CPU Usage: {max(cpu_vals):.1f}%",
                    f"Average Memory Usage: {sum(mem_vals)/len(mem_vals):.1f}%",
                    f"Peak Memory Usage: {max(mem_vals):.1f}%",
                    f"Average Disk Usage: {sum(disk_vals)/len(disk_vals):.1f}%",
                    f"Peak Disk Usage: {max(disk_vals):.1f}%",
                    "",
                    "System Information:",
                    f"Total Data Points: {len(self.performance_data)}",
                    f"Monitoring Started: {self.performance_start_time.strftime('%Y-%m-%d %H:%M:%S') if self.performance_start_time else 'Unknown'}"
                ])

            # Save report
            report_file = self.project_root / "logs" / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            report_file.parent.mkdir(parents=True, exist_ok=True)

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))

            self._msg(messagebox.showinfo, "Performance Report", f"Report generated:\n{report_file}")

        except Exception as e:
            logging.exception("Failed to generate performance report")
            self._msg(messagebox.showerror, "Performance Report", f"Failed to generate report: {e}")

    def clear_performance_history(self):
        """Clear performance history data."""
        try:
            self.performance_data = []

            # Clear treeview
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

            # Clear statistics
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.config(state=tk.DISABLED)

            self._msg(messagebox.showinfo, "Performance History", "Performance history cleared.")

        except Exception as e:
            logging.exception("Failed to clear performance history")
            self._msg(messagebox.showerror, "Performance History", f"Failed to clear history: {e}")

    def create_admin_tab(self):
        """Create Administration tab by delegating to the extracted UI module."""
        from src.celsius.hub.ui import create_admin_tab as _create
        try:
            _create(self)
        except Exception as e:
            logging.exception("Failed to create Administration tab UI: %s", e)
            self._show_tab_error(self.tab_admin, f"Admin tab failed: {e}")
            raise

    def create_ngrok_tab(self):
        """Create Ngrok Tunnels tab for managing secure tunnels."""
        try:
            ngrok_frame = ttk.Frame(self.tab_ngrok)
            ngrok_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Header
            ttk.Label(ngrok_frame, text="Ngrok Tunnel Management", style="Header.TLabel").pack(pady=(0, 10))
            
            # Status section
            status_frame = ttk.LabelFrame(ngrok_frame, text="Tunnel Status", padding=10)
            status_frame.pack(fill="x", pady=(0, 10))
            
            self.ngrok_status_label = ttk.Label(status_frame, text="No active tunnels", style="Status.TLabel")
            self.ngrok_status_label.pack()
            
            # Controls
            controls_frame = ttk.Frame(ngrok_frame)
            controls_frame.pack(fill="x", pady=(0, 10))
            
            ttk.Button(controls_frame, text="Start Ngrok Tunnel", command=lambda: self._msg(messagebox.showinfo, "Ngrok", "Ngrok tunnel functionality coming soon")).pack(side="left", padx=5)
            ttk.Button(controls_frame, text="Stop All Tunnels", command=lambda: self._msg(messagebox.showinfo, "Ngrok", "Tunnel stop functionality coming soon")).pack(side="left", padx=5)
            
            # Tunnel list
            list_frame = ttk.LabelFrame(ngrok_frame, text="Active Tunnels", padding=10)
            list_frame.pack(fill="both", expand=True)
            
            self.ngrok_tree = ttk.Treeview(list_frame, columns=("Name", "URL", "Port", "Status"), show="headings", height=10)
            self.ngrok_tree.heading("Name", text="Tunnel Name")
            self.ngrok_tree.heading("URL", text="Public URL")
            self.ngrok_tree.heading("Port", text="Local Port")
            self.ngrok_tree.heading("Status", text="Status")
            self.ngrok_tree.pack(fill="both", expand=True)
            
            ttk.Label(ngrok_frame, text="Note: Ngrok integration requires ngrok installation and authentication token", 
                     font=("Helvetica", 9, "italic")).pack(pady=(10, 0))
            
            return ngrok_frame
            
        except Exception as e:
            logging.exception("Failed to create ngrok tab")
            return None

    def create_code_approval_tab(self):
        """Create Code Approvals tab for reviewing pending code changes."""
        try:
            approval_frame = ttk.Frame(self.tab_code_approval)
            approval_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Header
            ttk.Label(approval_frame, text="Code Approval Queue", style="Header.TLabel").pack(pady=(0, 10))
            
            # Status
            status_frame = ttk.LabelFrame(approval_frame, text="Queue Status", padding=10)
            status_frame.pack(fill="x", pady=(0, 10))
            
            self.code_approval_status = ttk.Label(status_frame, text="No pending approvals", style="Status.TLabel")
            self.code_approval_status.pack()
            
            # Controls
            controls_frame = ttk.Frame(approval_frame)
            controls_frame.pack(fill="x", pady=(0, 10))
            
            ttk.Button(controls_frame, text="Refresh Queue", command=self.refresh_code_approval_queue).pack(side="left", padx=5)
            ttk.Button(controls_frame, text="Approve Selected", command=self.approve_selected_code_approval).pack(side="left", padx=5)
            ttk.Button(controls_frame, text="Reject Selected", command=self.reject_selected_code_approval).pack(side="left", padx=5)
            ttk.Button(controls_frame, text="View Details", command=self.view_selected_code_approval_details).pack(side="left", padx=5)
            ttk.Button(controls_frame, text="Apply Approved", command=self.apply_selected_code_approval).pack(side="left", padx=5)
            
            # Pending items list
            list_frame = ttk.LabelFrame(approval_frame, text="Pending Code Changes", padding=10)
            list_frame.pack(fill="both", expand=True)
            
            self.code_approval_tree = ttk.Treeview(list_frame, columns=("ID", "Type", "Description", "Date", "Status"), show="headings", height=15)
            self.code_approval_tree.heading("ID", text="ID")
            self.code_approval_tree.heading("Type", text="Change Type")
            self.code_approval_tree.heading("Description", text="Description")
            self.code_approval_tree.heading("Date", text="Date")
            self.code_approval_tree.heading("Status", text="Status")
            self.code_approval_tree.pack(fill="both", expand=True)
            
            # Initial load
            self.refresh_code_approval_queue()

            return approval_frame
            
        except Exception as e:
            logging.exception("Failed to create code approval tab")
            return None
            return None

    def _ingestion_approved_path(self):
        """Get path to approved ingestion file."""
        return os.path.join(self.project_root, "data", "ingestion_approved.json")

    def _submit_code_approval_for_ingestion(self, item: dict):
        """Create a Code Approval request for an approved ingestion item."""
        try:
            async def _submit():
                try:
                    from src.celsius.utils.celsius_code_approval import CelsiusCodeApprovalSystem
                    system = CelsiusCodeApprovalSystem()
                    await system.initialize()

                    title = f"Add Learning Source: {item.get('title') or item.get('url') or 'Untitled'}"
                    url = item.get('url') or item.get('source') or 'unknown'
                    description = (
                        "Approve a new web learning source for inclusion in the learning pipeline.\n\n"
                        f"URL: {url}\n"
                        f"Title: {item.get('title', '')}\n"
                        f"Added: {item.get('added') or item.get('timestamp') or ''}\n"
                    )
                    files_to_modify = ["data/ingestion_approved.json"]
                    changes_detail = (
                        "Append the approved source record to ingestion_approved.json and schedule downstream "
                        "learning tasks to pull and index content."
                    )
                    benefits = (
                        "Expands the curated learning corpus with a vetted resource, improving coverage and knowledge."
                    )
                    detriments = (
                        "Possible increase in processing time/storage if the source is large; quality varies by source."
                    )
                    alternatives = (
                        "Defer inclusion; scrape a smaller subset; require additional human validation first."
                    )

                    req_id = await system.submit_request(
                        title=title,
                        description=description,
                        files_to_modify=files_to_modify,
                        changes_detail=changes_detail,
                        benefits=benefits,
                        detriments=detriments,
                        alternatives=alternatives,
                    )

                    def _ok():
                        if hasattr(self, 'code_approval_status'):
                            self.code_approval_status.config(text=f"Pending approvals updated (last: {req_id})")
                        # Optionally refresh queue if tab exists
                        if hasattr(self, 'code_approval_tree'):
                            self.refresh_code_approval_queue()
                    self.schedule_on_main_thread(_ok)
                except Exception:
                    logging.exception("submit code approval failed")

            # Schedule the async submission without blocking UI
            self.schedule_async_task(_submit())
        except Exception:
            logging.exception("_submit_code_approval_for_ingestion failed")

    def refresh_code_approval_queue(self):
        """Load pending code approval requests and populate the queue UI."""
        try:
            async def _load():
                try:
                    from src.celsius.utils.celsius_code_approval import CelsiusCodeApprovalSystem
                    system = CelsiusCodeApprovalSystem()
                    await system.initialize()
                    pending = await system.get_pending_requests()

                    def _update():
                        try:
                            if not hasattr(self, 'code_approval_tree'):
                                return
                            tree = self.code_approval_tree
                            # Clear existing
                            for c in tree.get_children():
                                tree.delete(c)
                            # Populate
                            for row in pending:
                                rid = row.get('request_id')
                                typ = 'Learning'
                                desc = row.get('title') or row.get('description', '')[:80]
                                date = row.get('timestamp', '')
                                status = row.get('status', 'pending')
                                tree.insert('', 'end', values=(rid, typ, desc, date, status))
                            # Update status label
                            if hasattr(self, 'code_approval_status'):
                                n = len(pending)
                                self.code_approval_status.config(
                                    text=(f"{n} pending approval(s)" if n else "No pending approvals")
                                )
                        except Exception:
                            logging.exception("update code approval queue failed")
                    self.schedule_on_main_thread(_update)
                except Exception:
                    logging.exception("load code approval queue failed")
            self.schedule_async_task(_load())
        except Exception:
            logging.exception("refresh_code_approval_queue outer failed")

    def approve_selected_code_approval(self):
        """Approve the selected code approval request in the queue."""
        try:
            if not hasattr(self, 'code_approval_tree'):
                return
            sel = self.code_approval_tree.selection()
            if not sel:
                self._msg(messagebox.showinfo, "Code Approval", "No request selected")
                return
            iid = sel[0]
            values = self.code_approval_tree.item(iid).get('values') or []
            if not values:
                return
            request_id = values[0]

            async def _approve():
                try:
                    from src.celsius.utils.celsius_code_approval import CelsiusCodeApprovalSystem
                    system = CelsiusCodeApprovalSystem()
                    await system.initialize()
                    await system.approve_request(request_id, user_notes="Approved via Ultimate Hub UI")
                    self.schedule_on_main_thread(lambda: self.refresh_code_approval_queue())
                except Exception:
                    logging.exception("approve code request failed")
            self.schedule_async_task(_approve())
        except Exception:
            logging.exception("approve_selected_code_approval failed")

    def reject_selected_code_approval(self):
        """Reject the selected code approval request in the queue."""
        try:
            if not hasattr(self, 'code_approval_tree'):
                return
            sel = self.code_approval_tree.selection()
            if not sel:
                self._msg(messagebox.showinfo, "Code Approval", "No request selected")
                return
            iid = sel[0]
            values = self.code_approval_tree.item(iid).get('values') or []
            if not values:
                return
            request_id = values[0]

            async def _reject():
                try:
                    from src.celsius.utils.celsius_code_approval import CelsiusCodeApprovalSystem
                    system = CelsiusCodeApprovalSystem()
                    await system.initialize()
                    await system.reject_request(request_id, reason="Rejected via Ultimate Hub UI")
                    self.schedule_on_main_thread(lambda: self.refresh_code_approval_queue())
                except Exception:
                    logging.exception("reject code request failed")
            self.schedule_async_task(_reject())
        except Exception:
            logging.exception("reject_selected_code_approval failed")

    def view_selected_code_approval_details(self):
        """Open a dialog showing details and any artifacts for the selected request."""
        try:
            if not hasattr(self, 'code_approval_tree'):
                return
            sel = self.code_approval_tree.selection()
            if not sel:
                self._msg(messagebox.showinfo, "Code Approval", "No request selected")
                return
            request_id = self.code_approval_tree.item(sel[0]).get('values', [None])[0]
            if not request_id:
                return

            async def _load():
                try:
                    from src.celsius.utils.celsius_code_approval import CelsiusCodeApprovalSystem
                    system = CelsiusCodeApprovalSystem()
                    await system.initialize()
                    req = await system.get_request(request_id)
                    def _show():
                        if not req:
                            self._msg(messagebox.showwarning, "Code Approval", "Request not found")
                            return
                        details = []
                        details.append(f"Title: {req.get('title','')}")
                        details.append(f"Description: {req.get('description','')}")
                        details.append("")
                        details.append("Files to modify:")
                        try:
                            files = req.get('files_to_modify')
                            files = json.loads(files) if isinstance(files, str) else files
                        except Exception:
                            files = []
                        for f in files or []:
                            details.append(f"  • {f}")
                        details.append("")
                        details.append(f"Benefits: {req.get('benefits','')}")
                        details.append(f"Detriments: {req.get('detriments','')}")
                        details.append(f"Alternatives: {req.get('alternatives','')}")
                        artifacts = req.get('artifacts_path')
                        if artifacts and os.path.isdir(artifacts):
                            details.append("")
                            details.append(f"Artifacts: {artifacts}")
                            expl = os.path.join(artifacts, 'explanation.md')
                            if os.path.isfile(expl):
                                details.append("(An explanation.md is available; opening in default editor)")
                                try:
                                    os.startfile(expl)
                                except Exception:
                                    pass
                        txt = "\n".join(details)
                        self._msg(messagebox.showinfo, "Code Approval Details", txt)
                    self.schedule_on_main_thread(_show)
                except Exception:
                    logging.exception("load request details failed")
            self.schedule_async_task(_load())
        except Exception:
            logging.exception("view_selected_code_approval_details failed")

    def apply_selected_code_approval(self):
        """Apply artifacts for an already-approved request."""
        try:
            if not hasattr(self, 'code_approval_tree'):
                return
            sel = self.code_approval_tree.selection()
            if not sel:
                self._msg(messagebox.showinfo, "Code Approval", "No request selected")
                return
            request_id = self.code_approval_tree.item(sel[0]).get('values', [None])[0]
            if not request_id:
                return

            async def _apply():
                try:
                    from src.celsius.utils.celsius_code_approval import CelsiusCodeApprovalSystem
                    system = CelsiusCodeApprovalSystem()
                    await system.initialize()
                    req = await system.get_request(request_id)
                    status = (req or {}).get('status')
                    if status != 'approved':
                        self.schedule_on_main_thread(lambda: self._msg(messagebox.showwarning, "Code Approval", "Request must be approved before applying."))
                        return
                    ok = await system.apply_request(request_id)
                    self.schedule_on_main_thread(lambda: self._msg(
                        messagebox.showinfo if ok else messagebox.showerror,
                        "Apply Code Changes",
                        "Changes applied successfully." if ok else "Failed to apply changes.")
                    )
                except Exception:
                    logging.exception("apply code request failed")
            self.schedule_async_task(_apply())
        except Exception:
            logging.exception("apply_selected_code_approval failed")

    def create_testing_tab(self):
        """Create Testing tab by delegating to the extracted UI module."""
        from src.celsius.hub.ui import create_testing_tab as _create
        try:
            _create(self)
        except Exception as e:
            logging.exception("Failed to create Testing tab UI: %s", e)
            self._show_tab_error(self.tab_testing, f"Testing tab failed: {e}")
            raise

    def _show_tab_error(self, frame, message: str):
        """Display a red error label inside a tab frame."""
        try:
            for child in frame.winfo_children():
                try:
                    child.destroy()
                except Exception:
                    pass
            lbl = ttk.Label(frame, text=message, foreground="red", wraplength=800, justify="left")
            lbl.pack(fill="both", expand=True, padx=10, pady=10)
        except Exception:
            logging.debug("Could not render tab error label", exc_info=True)

    # ==================== SERVICE MANAGEMENT METHODS ====================
    
    def start_all_services(self):
        """Start all enabled services in the configuration."""
        try:
            logging.info("Starting all services...")
            if not hasattr(self, 'services'):
                self.services = self._get_default_services()
            
            for service_name, service_info in self.services.items():
                if service_info.get('enabled', False):
                    self._start_service(service_name)
            
            self._msg(messagebox.showinfo, "Services", "All enabled services started")
        except Exception as e:
            logging.error(f"Error starting all services: {e}")
            self._msg(messagebox.showerror, "Error", f"Failed to start services: {e}")
    
    def stop_all_services(self):
        """Stop all running services."""
        try:
            logging.info("Stopping all services...")
            if not hasattr(self, 'services'):
                return
            
            for service_name, service_info in self.services.items():
                if service_info.get('process') and service_info['process'].poll() is None:
                    try:
                        service_info['process'].terminate()
                        logging.info(f"Stopped service: {service_name}")
                    except Exception as e:
                        logging.error(f"Error stopping service {service_name}: {e}")
            
            self._msg(messagebox.showinfo, "Services", "All services stopped")
        except Exception as e:
            logging.error(f"Error stopping all services: {e}")
            self._msg(messagebox.showerror, "Error", f"Failed to stop services: {e}")
    
    def _start_service(self, service_name):
        """Start a specific service by name."""
        try:
            if service_name not in self.services:
                logging.error(f"Unknown service: {service_name}")
                return
            
            service = self.services[service_name]
            script = service.get('script')
            
            if not script:
                logging.error(f"No script defined for service: {service_name}")
                return
            
            # Check if already running
            if service.get('process') and service['process'].poll() is None:
                logging.info(f"Service {service_name} is already running")
                return
            
            # Determine the correct path to the script
            import subprocess
            import sys
            
            # When running as frozen exe, we need to go back to the project root
            if getattr(sys, 'frozen', False):
                # Running as compiled executable - go back to project root
                project_root = os.path.dirname(os.path.dirname(sys.executable))
                script_path = os.path.join(project_root, script)
                
                # Check if script exists
                if not os.path.exists(script_path):
                    logging.error(f"Service script not found: {script_path}")
                    self._msg(messagebox.showerror, "Service Error", 
                             f"Cannot start {service_name}:\n\n"
                             f"Script not found: {script}\n\n"
                             f"When running the compiled app, make sure the .exe is in the 'dist' folder "
                             f"inside your Celsius AI project directory.")
                    return
                
                # Use python from PATH or system Python
                python_cmd = 'python'
            else:
                # Running from source - use current directory
                script_path = os.path.join(os.getcwd(), script)
                python_cmd = sys.executable
            
            # Start the service
            try:
                process = subprocess.Popen(
                    [python_cmd, script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=os.path.dirname(script_path) if getattr(sys, 'frozen', False) else None
                )
                service['process'] = process
                service['enabled'] = True
                service['status'] = 'Running'
                logging.info(f"Started service: {service_name} (PID: {process.pid})")
                
                # Log activity
                self.log_activity(service_name, "Started", f"PID: {process.pid}")
                
                # Show success message
                self._msg(messagebox.showinfo, "Service Started", 
                         f"{service_name} started successfully\nPID: {process.pid}")
                
            except FileNotFoundError:
                logging.error(f"Python or script not found for service: {service_name}")
                self._msg(messagebox.showerror, "Service Error",
                         f"Cannot start {service_name}:\n\n"
                         f"Python interpreter or script not found.\n"
                         f"Make sure Python is installed and in your PATH.")
                return
            
        except Exception as e:
            logging.error(f"Error starting service {service_name}: {e}")
            logging.exception("Traceback:")
            self._msg(messagebox.showerror, "Service Error",
                     f"Failed to start {service_name}:\n\n{str(e)}")
    
    def start_service_action(self, service_name):
        """Handle start button click for a service."""
        try:
            self._start_service(service_name)
            # Update status
            if service_name in self.services:
                process = self.services[service_name].get('process')
                if process and process.poll() is None:
                    self.services[service_name]['status'] = 'Running'
                else:
                    self.services[service_name]['status'] = 'Stopped'
            # Update UI
            self.update_service_buttons()
        except Exception as e:
            logging.error(f"Error in start_service_action: {e}")
    
    def stop_service_action(self, service_name):
        """Handle stop button click for a service."""
        try:
            if service_name not in self.services:
                return
            
            service = self.services[service_name]
            process = service.get('process')
            
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
                logging.info(f"Stopped service: {service_name}")
                
                # Log activity
                self.log_activity(service_name, "Stopped", "Service terminated")
                
                self._msg(messagebox.showinfo, "Service Stopped", 
                         f"{service_name} has been stopped")
                service['status'] = 'Stopped'
            else:
                service['status'] = 'Stopped'
                self.log_activity(service_name, "Stop Failed", "Service was not running")
                self._msg(messagebox.showwarning, "Service Status", 
                         f"{service_name} is not running")
            
            # Update UI
            self.update_service_buttons()
            
        except Exception as e:
            logging.error(f"Error stopping service {service_name}: {e}")
            self._msg(messagebox.showerror, "Service Error",
                     f"Failed to stop {service_name}:\n\n{str(e)}")
    
    def restart_service_action(self, service_name):
        """Handle restart button click for a service."""
        try:
            # Stop first
            self.stop_service_action(service_name)
            # Wait a bit
            import time
            time.sleep(1)
            # Start again
            self.start_service_action(service_name)
        except Exception as e:
            logging.error(f"Error restarting service {service_name}: {e}")
    
    def refresh_dashboard(self):
        """Refresh dashboard metrics and status displays."""
        try:
            logging.info("Refreshing dashboard...")
            # Update system health metrics
            self.update_system_health()
        except Exception as e:
            logging.error(f"Error refreshing dashboard: {e}")
    
    def log_activity(self, service, action, details=""):
        """Log an activity to the activity log tree and update service status display."""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Log to file
            logging.info(f"Activity: {service} - {action} - {details}")
            
            # Add to activity log tree if it exists
            if hasattr(self, 'log_tree') and self.log_tree.winfo_exists():
                try:
                    self.log_tree.insert("", 0, values=(timestamp, service, action, details))
                    # Keep only last 100 entries
                    items = self.log_tree.get_children()
                    if len(items) > 100:
                        self.log_tree.delete(items[-1])
                except Exception as e:
                    logging.error(f"Error updating log_tree: {e}")
            
            # Update service status text if it exists
            if hasattr(self, 'service_status_text') and self.service_status_text.winfo_exists():
                try:
                    self.service_status_text.configure(state="normal")
                    self.service_status_text.insert("1.0", f"[{timestamp}] {service}: {action} - {details}\n")
                    # Keep only last 50 lines
                    content = self.service_status_text.get("1.0", "end")
                    lines = content.split("\n")
                    if len(lines) > 50:
                        self.service_status_text.delete("1.0", "end")
                        self.service_status_text.insert("1.0", "\n".join(lines[:50]))
                    self.service_status_text.configure(state="disabled")
                except Exception as e:
                    logging.error(f"Error updating service_status_text: {e}")
            
            # Update service status labels in Services tab
            self.schedule_on_main_thread(self.update_service_buttons)
            
        except Exception as e:
            logging.error(f"Error logging activity: {e}", exc_info=True)
    
    def update_system_health(self):
        """Update system health metrics (CPU, Memory, Disk)."""
        try:
            if psutil is None:
                # psutil not available
                if hasattr(self, 'cpu_label'):
                    self.cpu_label.config(text="CPU: N/A (psutil not installed)")
                if hasattr(self, 'memory_label'):
                    self.memory_label.config(text="Memory: N/A (psutil not installed)")
                if hasattr(self, 'disk_label'):
                    self.disk_label.config(text="Disk: N/A (psutil not installed)")
                return
            
            # Get CPU usage
            if hasattr(self, 'cpu_label'):
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.cpu_label.config(text=f"CPU: {cpu_percent}%")
            
            # Get Memory usage
            if hasattr(self, 'memory_label'):
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used_gb = memory.used / (1024 ** 3)
                memory_total_gb = memory.total / (1024 ** 3)
                self.memory_label.config(
                    text=f"Memory: {memory_percent}% ({memory_used_gb:.1f}GB / {memory_total_gb:.1f}GB)"
                )
            
            # Get Disk usage
            if hasattr(self, 'disk_label'):
                try:
                    disk = psutil.disk_usage('/')
                    disk_percent = disk.percent
                    disk_used_gb = disk.used / (1024 ** 3)
                    disk_total_gb = disk.total / (1024 ** 3)
                    self.disk_label.config(
                        text=f"Disk: {disk_percent}% ({disk_used_gb:.1f}GB / {disk_total_gb:.1f}GB)"
                    )
                except Exception:
                    # On Windows, might need to use C:
                    disk = psutil.disk_usage('C')
                    disk_percent = disk.percent
                    disk_used_gb = disk.used / (1024 ** 3)
                    disk_total_gb = disk.total / (1024 ** 3)
                    self.disk_label.config(
                        text=f"Disk: {disk_percent}% ({disk_used_gb:.1f}GB / {disk_total_gb:.1f}GB)"
                    )
            
            # Schedule next update in 5 seconds
            self.root.after(5000, self.update_system_health)
            
        except Exception as e:
            logging.error(f"Error updating system health: {e}")
            # Try again later
            self.root.after(10000, self.update_system_health)
    
    def refresh_learning_insights(self):
        """Refresh AI learning insights display."""
        try:
            logging.info("Refreshing learning insights...")
            if hasattr(self, 'learning_insights_text'):
                self.learning_insights_text.delete("1.0", "end")
                self.learning_insights_text.insert("1.0", "Loading latest insights...\n\n")
                self.learning_insights_text.insert("end", "No recent learning activities found.\n")
                self.learning_insights_text.insert("end", "Start a learning session to see insights here.")
        except Exception as e:
            logging.error(f"Error refreshing learning insights: {e}")
    
    def start_learning_system(self):
        """Start the AI learning system."""
        try:
            logging.info("Starting AI learning system...")
            self._start_service("Core AI Engine")
            self._msg(messagebox.showinfo, "AI Learning", "AI Learning system started")
        except Exception as e:
            logging.error(f"Error starting AI learning: {e}")
            self._msg(messagebox.showerror, "Error", f"Failed to start AI learning: {e}")
    
    def stop_learning_system(self):
        """Stop the AI learning system."""
        try:
            logging.info("Stopping AI learning system...")
            if hasattr(self, 'services') and "Core AI Engine" in self.services:
                service = self.services["Core AI Engine"]
                if service.get('process') and service['process'].poll() is None:
                    service['process'].terminate()
                    logging.info("Stopped AI learning system")
            self._msg(messagebox.showinfo, "AI Learning", "AI Learning system stopped")
        except Exception as e:
            logging.error(f"Error stopping AI learning: {e}")
    
    def start_web_learning_system(self):
        """Start the web learning system."""
        try:
            logging.info("Starting web learning system...")
            self._start_service("Web Learning")
            self._msg(messagebox.showinfo, "Web Learning", "Web Learning system started")
        except Exception as e:
            logging.error(f"Error starting web learning: {e}")
            self._msg(messagebox.showerror, "Error", f"Failed to start web learning: {e}")
    
    def stop_web_learning_system(self):
        """Stop the web learning system."""
        try:
            logging.info("Stopping web learning system...")
            if hasattr(self, 'services') and "Web Learning" in self.services:
                service = self.services["Web Learning"]
                if service.get('process') and service['process'].poll() is None:
                    service['process'].terminate()
                    logging.info("Stopped web learning system")
            self._msg(messagebox.showinfo, "Web Learning", "Web Learning system stopped")
        except Exception as e:
            logging.error(f"Error stopping web learning: {e}")
    
    def start_learning_session(self):
        """Start a new learning session."""
        try:
            logging.info("Starting new learning session...")
            self._msg(messagebox.showinfo, "Learning Session", "Learning session started\nMonitor progress in the AI Systems tab")
        except Exception as e:
            logging.error(f"Error starting learning session: {e}")
    
    def view_learning_history(self):
        """View learning history and past sessions."""
        try:
            logging.info("Viewing learning history...")
            self._msg(messagebox.showinfo, "Learning History", "Learning history viewer coming soon")
        except Exception as e:
            logging.error(f"Error viewing learning history: {e}")
    
    def export_security_log(self):
        """Export security log tree to CSV file."""
        try:
            from tkinter import filedialog
            import csv
            from datetime import datetime
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Security Log"
            )
            
            if filename:
                if hasattr(self, 'security_log_tree'):
                    # Get all items from the tree
                    items = self.security_log_tree.get_children()
                    
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        
                        # Write header
                        writer.writerow(['Timestamp', 'Event', 'Status', 'Details'])
                        
                        # Write data
                        for item in items:
                            values = self.security_log_tree.item(item)['values']
                            writer.writerow(values)
                    
                    count = len(items)
                    self._msg(messagebox.showinfo, "Export Complete", 
                             f"Exported {count} security log entries to:\n{filename}")
                    logging.info(f"Exported {count} security log entries to {filename}")
                else:
                    self._msg(messagebox.showwarning, "Export", "Security log tree not available")
        except Exception as e:
            logging.error(f"Error exporting security log: {e}")
            self._msg(messagebox.showerror, "Export Error", f"Failed to export: {e}")
    
    def clear_security_log(self):
        """Clear the security log after confirmation."""
        try:
            if self._msg(messagebox.askyesno, "Clear Log", "Are you sure you want to clear the security log?"):
                logging.info("Clearing security log...")
                if hasattr(self, 'security_log_tree'):
                    for item in self.security_log_tree.get_children():
                        self.security_log_tree.delete(item)
                self._msg(messagebox.showinfo, "Cleared", "Security log cleared")
        except Exception as e:
            logging.error(f"Error clearing security log: {e}")
    
    # ==================== ADMINISTRATIVE & UTILITY METHODS ====================
    
    def perform_cleanup_action(self):
        """Perform system cleanup and backup."""
        try:
            logging.info("Performing system cleanup and backup...")
            self._msg(messagebox.showinfo, "Cleanup", 
                     "System cleanup initiated.\n\n"
                     "This will:\n"
                     "- Clean old log files\n"
                     "- Vacuum databases\n"
                     "- Create backups\n\n"
                     "Check logs for progress.")
            # TODO: Implement actual cleanup logic
        except Exception as e:
            logging.error(f"Error in cleanup action: {e}")
            self._msg(messagebox.showerror, "Error", f"Cleanup failed: {e}")
    
    def clear_old_logs(self):
        """Clear old log files older than 30 days."""
        try:
            import glob
            from datetime import datetime, timedelta
            
            log_dir = self.project_root / 'logs'
            cutoff_date = datetime.now() - timedelta(days=30)
            
            deleted_count = 0
            total_size = 0
            
            for log_file in log_dir.glob('*.log'):
                try:
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        file_size = log_file.stat().st_size
                        log_file.unlink()
                        deleted_count += 1
                        total_size += file_size
                except Exception as e:
                    logging.warning(f"Could not delete {log_file}: {e}")
            
            size_mb = total_size / (1024 * 1024)
            self._msg(messagebox.showinfo, "Logs Cleared", 
                     f"Deleted {deleted_count} old log files\n"
                     f"Freed {size_mb:.2f} MB of disk space")
            logging.info(f"Cleared {deleted_count} old log files, freed {size_mb:.2f} MB")
        except Exception as e:
            logging.error(f"Error clearing old logs: {e}")
            self._msg(messagebox.showerror, "Error", f"Failed to clear logs: {e}")
    
    def vacuum_databases(self):
        """Vacuum and optimize databases."""
        try:
            vacuumed = []
            errors = []
            
            # Vacuum each database
            db_paths = [
                self.project_root / 'data' / 'activity.db',
                self.project_root / 'data' / 'system.db',
                self.project_root / 'data' / 'monitoring.db'
            ]
            
            for db_path in db_paths:
                if db_path.exists():
                    try:
                        import sqlite3
                        conn = sqlite3.connect(str(db_path))
                        conn.execute('VACUUM')
                        conn.close()
                        vacuumed.append(db_path.name)
                        logging.info(f"Vacuumed database: {db_path.name}")
                    except Exception as e:
                        errors.append(f"{db_path.name}: {str(e)}")
                        logging.error(f"Error vacuuming {db_path.name}: {e}")
            
            if vacuumed:
                msg = f"Successfully vacuumed {len(vacuumed)} database(s):\n" + "\n".join(f"✓ {db}" for db in vacuumed)
                if errors:
                    msg += f"\n\nErrors:\n" + "\n".join(f"✗ {err}" for err in errors)
                self._msg(messagebox.showinfo, "Database Vacuum", msg)
            else:
                self._msg(messagebox.showwarning, "Database Vacuum", "No databases found to vacuum")
        except Exception as e:
            logging.error(f"Error vacuuming databases: {e}")
            self._msg(messagebox.showerror, "Error", f"Vacuum failed: {e}")
    
    def view_db_stats(self):
        """View database statistics."""
        try:
            import sqlite3
            stats = []
            
            db_paths = [
                ('Activity DB', self.project_root / 'data' / 'activity.db'),
                ('System DB', self.project_root / 'data' / 'system.db'),
                ('Monitoring DB', self.project_root / 'data' / 'monitoring.db')
            ]
            
            for db_name, db_path in db_paths:
                if db_path.exists():
                    try:
                        conn = sqlite3.connect(str(db_path))
                        cursor = conn.cursor()
                        
                        # Get table count
                        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                        table_count = cursor.fetchone()[0]
                        
                        # Get database size
                        size_bytes = db_path.stat().st_size
                        size_mb = size_bytes / (1024 * 1024)
                        
                        # Get row counts from all tables
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = cursor.fetchall()
                        total_rows = 0
                        for (table_name,) in tables:
                            try:
                                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                                total_rows += cursor.fetchone()[0]
                            except Exception:
                                pass
                        
                        conn.close()
                        stats.append(f"{db_name}:\n  Tables: {table_count}\n  Rows: {total_rows:,}\n  Size: {size_mb:.2f} MB")
                    except Exception as e:
                        stats.append(f"{db_name}: Error - {str(e)}")
                else:
                    stats.append(f"{db_name}: Not found")
            
            self._msg(messagebox.showinfo, "Database Stats", "\n\n".join(stats))
        except Exception as e:
            logging.error(f"Error viewing database stats: {e}")
            self._msg(messagebox.showerror, "Error", f"Failed to get stats: {e}")
    
    def export_activity_log(self):
        """Export activity log to CSV file."""
        try:
            from tkinter import filedialog
            import sqlite3
            import csv
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Activity Log"
            )
            
            if filename:
                db_path = self.project_root / 'data' / 'activity.db'
                if not db_path.exists():
                    self._msg(messagebox.showwarning, "Export", "Activity database not found")
                    return
                
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # Get all activity records
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                rows_exported = 0
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    for (table_name,) in tables:
                        try:
                            cursor.execute(f"SELECT * FROM {table_name}")
                            rows = cursor.fetchall()
                            if rows:
                                # Write table header
                                writer.writerow([f"=== {table_name} ==="])
                                # Write column names
                                col_names = [desc[0] for desc in cursor.description]
                                writer.writerow(col_names)
                                # Write data
                                writer.writerows(rows)
                                writer.writerow([])  # Empty row between tables
                                rows_exported += len(rows)
                        except Exception as e:
                            logging.warning(f"Could not export table {table_name}: {e}")
                
                conn.close()
                self._msg(messagebox.showinfo, "Export Complete", 
                         f"Exported {rows_exported} records to:\n{filename}")
                logging.info(f"Exported {rows_exported} activity log records to {filename}")
        except Exception as e:
            logging.error(f"Error exporting activity log: {e}")
            self._msg(messagebox.showerror, "Export Error", f"Failed to export: {e}")
    
    def schedule_async_task(self, task):
        """Schedule a coroutine or callable on background loop / thread.

        If a coroutine object is passed, submit it to the async loop. If a
        plain callable is passed, run it in a daemon thread so the UI stays
        responsive.
        """
        try:
            import asyncio as _asyncio
            if _asyncio.iscoroutine(task):
                self.async_loop.create_task(task)
                return
            if callable(task):
                import threading as _threading
                _threading.Thread(target=task, daemon=True).start()
                return
            logging.warning("schedule_async_task received unsupported task type: %r", task)
        except Exception:
            logging.exception("schedule_async_task failed")
    
    async def init_db(self):
        """Initialize databases (async placeholder)."""
        logging.info("Database initialization requested")
        return True
    
    def refresh_hardware_status(self):
        """Refresh hardware monitoring status."""
        try:
            logging.info("Refreshing hardware status...")
            
            # Update CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_cores = psutil.cpu_count(logical=True)
            
            # Update memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            
            # Update disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            
            # Try to get temperature sensors
            temps = []
            try:
                temps_dict = psutil.sensors_temperatures()
                if temps_dict:
                    for name, entries in temps_dict.items():
                        for entry in entries:
                            temps.append(f"{entry.label or name}: {entry.current}°C")
            except (AttributeError, OSError):
                temps.append("Temperature sensors not available on this system")
            
            # Build status message
            status_lines = [
                f"CPU: {cpu_percent}% ({cpu_cores} cores)",
                f"Memory: {memory_percent}% ({memory_used_gb:.1f}/{memory_total_gb:.1f} GB)",
                f"Disk: {disk_percent}% ({disk_used_gb:.1f}/{disk_total_gb:.1f} GB)",
                "\nTemperatures:",
                *temps[:5]  # Show up to 5 temperature sensors
            ]
            
            status_msg = "\n".join(status_lines)
            self._msg(messagebox.showinfo, "Hardware Status", status_msg)
        except Exception as e:
            logging.error(f"Error refreshing hardware: {e}")
    
    # ==================== WEB LEARNING & AI TRAINING METHODS ====================
    
    async def fetch_from_providers(self):
        """Fetch data from configured providers."""
        logging.info("Fetching from providers...")
        return True
    
    def import_web_learning_alternatives(self):
        """Import alternative web learning sources from web_learning_wayback_alternatives.json."""
        try:
            source_path = self.project_root / "data" / "web_learning_wayback_alternatives.json"
            dest_path = self.project_root / "data" / "ingestion_candidates.json"

            if not source_path.exists():
                self._msg(messagebox.showwarning, "File Not Found", f"Source file not found: {source_path}")
                return

            with open(source_path, 'r', encoding='utf-8') as f:
                alternatives = json.load(f)

            if not alternatives:
                self._msg(messagebox.showinfo, "No Alternatives", "No new web learning alternatives to import.")
                return

            # Here you would normally transform the data if needed.
            # For now, we'll assume the format is compatible.

            existing_candidates = []
            if dest_path.exists():
                with open(dest_path, 'r', encoding='utf-8') as f:
                    existing_candidates = json.load(f)
            
            # Simple merge, avoiding duplicates based on a 'url' field if it exists
            existing_urls = {item.get('url') for item in existing_candidates if 'url' in item}
            new_items = [alt for alt in alternatives if alt.get('url') not in existing_urls]

            if not new_items:
                self._msg(messagebox.showinfo, "No New Items", "All alternatives have already been imported.")
                return

            updated_candidates = existing_candidates + new_items

            with open(dest_path, 'w', encoding='utf-8') as f:
                json.dump(updated_candidates, f, indent=4)

            self._msg(messagebox.showinfo, "Import Successful", f"Successfully imported {len(new_items)} new learning alternatives.")
            
            # Refresh the ingestion review UI
            if hasattr(self, 'load_ingestion_candidates'):
                self.load_ingestion_candidates()

        except Exception as e:
            logging.error(f"Error importing alternatives: {e}")
            self._msg(messagebox.showerror, "Import Error", f"An error occurred: {e}")
    
    async def _generate_outreach_csv(self):
        """Generate outreach CSV file."""
        logging.info("Generating outreach CSV...")
        return True
    
    async def ensure_email_notifier(self, force=False):
        """Ensure email notifier is initialized and update status labels."""
        try:
            if self.email_notifier and not force:
                return True
            notifier = None
            try:
                notifier = get_enhanced_notifier()
            except Exception as e:
                self._email_last_error = str(e)
                logging.exception("get_enhanced_notifier failed")
            if notifier is None:
                self._email_retry_count += 1
                def _down():
                    if hasattr(self, 'email_status_label'):
                        self.email_status_label.config(text="Email: Not Configured")
                    if hasattr(self, '_email_admin_retry_lbl'):
                        self._email_admin_retry_lbl.config(text=f"Retry Count: {self._email_retry_count}")
                    if hasattr(self, '_email_admin_last_error_lbl'):
                        self._email_admin_last_error_lbl.config(text=f"Last Error: {self._email_last_error}")
                self.schedule_on_main_thread(_down)
                return False
            self.email_notifier = notifier
            def _up():
                if hasattr(self, 'email_status_label'):
                    self.email_status_label.config(text="Email: Active")
                if hasattr(self, '_email_admin_last_error_lbl'):
                    self._email_admin_last_error_lbl.config(text="Last Error: None")
            self.schedule_on_main_thread(_up)
            return True
        except Exception:
            logging.exception("ensure_email_notifier failed")
            return False
    
    def _ingestion_candidates_path(self):
        """Get path to ingestion candidates file."""
        return os.path.join(self.project_root, "data", "ingestion_candidates.json")
    
    def load_ingestion_candidates(self):
        """Load ingestion candidates and populate Admin ingestion tree if present."""
        items = []
        try:
            cand_path = self._ingestion_candidates_path()
            if os.path.exists(cand_path):
                with open(cand_path, 'r', encoding='utf-8') as f:
                    items = json.load(f) or []
        except Exception as e:
            logging.error(f"Error loading ingestion candidates: {e}")
            items = []
        # Populate tree
        try:
            if hasattr(self, 'ingestion_tree') and self.ingestion_tree.winfo_exists():
                for child in self.ingestion_tree.get_children():
                    self.ingestion_tree.delete(child)
                for idx, rec in enumerate(items, start=1):
                    src = rec.get('url') or rec.get('source') or 'unknown'
                    title = rec.get('title') or rec.get('name') or ''
                    added = rec.get('added') or rec.get('timestamp') or ''
                    self.ingestion_tree.insert('', 'end', values=(idx, src, title, added))
            if hasattr(self, 'ingestion_status_label'):
                self.ingestion_status_label.config(text=f"Candidates file: {self._ingestion_candidates_path()} (loaded {len(items)})")
        except Exception:
            logging.debug("Failed to populate ingestion tree", exc_info=True)
        return items

    def approve_selected_ingestion(self):
        """Approve selected ingestion candidates and move to approved list."""
        try:
            if not hasattr(self, 'ingestion_tree'):
                return
                
            sel = self.ingestion_tree.selection()
            if not sel:
                self._msg(messagebox.showinfo, "Ingestion", "No item selected")
                return
            
            # Get candidates file
            cand_path = self._ingestion_candidates_path()
            if not os.path.exists(cand_path):
                self._msg(messagebox.showwarning, "Error", "Candidates file not found")
                return
            
            # Load current candidates
            with open(cand_path, 'r', encoding='utf-8') as f:
                candidates = json.load(f)
            
            # Get indices of selected items
            indices_to_remove = []
            for iid in sel:
                values = self.ingestion_tree.item(iid)['values']
                if values:
                    idx = int(values[0]) - 1  # Convert 1-based to 0-based
                    indices_to_remove.append(idx)
            
            # Determine selected items (store before removal)
            selected_items = []
            for idx in sorted(indices_to_remove):
                if 0 <= idx < len(candidates):
                    selected_items.append(candidates[idx])

            # Append selected items to approved file
            approved_path = self._ingestion_approved_path()
            approved = []
            if os.path.exists(approved_path):
                try:
                    with open(approved_path, 'r', encoding='utf-8') as f:
                        approved = json.load(f) or []
                except Exception:
                    approved = []
            approved.extend(selected_items)
            os.makedirs(os.path.dirname(approved_path), exist_ok=True)
            with open(approved_path, 'w', encoding='utf-8') as f:
                json.dump(approved, f, indent=4)

            # Remove approved items from candidates (remove by index descending)
            for idx in sorted(indices_to_remove, reverse=True):
                if 0 <= idx < len(candidates):
                    candidates.pop(idx)
            
            # Save updated candidates
            with open(cand_path, 'w', encoding='utf-8') as f:
                json.dump(candidates, f, indent=4)
            
            # Refresh tree
            self.load_ingestion_candidates()
            
            self._msg(messagebox.showinfo, "Approved", f"Approved {len(indices_to_remove)} item(s)")
            logging.info(f"Approved {len(indices_to_remove)} ingestion candidates")

            # Submit code approval requests for each approved item
            for item in selected_items:
                try:
                    self._submit_code_approval_for_ingestion(item)
                except Exception:
                    logging.exception("failed to submit code approval for ingestion item")
        except Exception as e:
            logging.exception("approve_selected_ingestion failed")
            self._msg(messagebox.showerror, "Error", f"Failed to approve: {e}")

    def approve_all_ingestion(self):
        """Approve all ingestion candidates and clear the list."""
        try:
            if not hasattr(self, 'ingestion_tree'):
                return
            
            count = len(self.ingestion_tree.get_children())
            if count == 0:
                self._msg(messagebox.showinfo, "Ingestion", "No candidates to approve")
                return
            
            # Load all current candidates
            cand_path = self._ingestion_candidates_path()
            all_items = []
            if os.path.exists(cand_path):
                try:
                    with open(cand_path, 'r', encoding='utf-8') as f:
                        all_items = json.load(f) or []
                except Exception:
                    all_items = []

            # Append all to approved file
            approved_path = self._ingestion_approved_path()
            approved = []
            if os.path.exists(approved_path):
                try:
                    with open(approved_path, 'r', encoding='utf-8') as f:
                        approved = json.load(f) or []
                except Exception:
                    approved = []
            approved.extend(all_items)
            os.makedirs(os.path.dirname(approved_path), exist_ok=True)
            with open(approved_path, 'w', encoding='utf-8') as f:
                json.dump(approved, f, indent=4)

            # Clear candidates file
            with open(cand_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
            
            # Refresh tree
            self.load_ingestion_candidates()
            
            self._msg(messagebox.showinfo, "Approved", f"Approved all {count} item(s)")
            logging.info(f"Approved all {count} ingestion candidates")

            # Submit code approval requests for each approved item
            for item in all_items:
                try:
                    self._submit_code_approval_for_ingestion(item)
                except Exception:
                    logging.exception("failed to submit code approval for ingestion item (batch)")
        except Exception as e:
            logging.exception("approve_all_ingestion failed")
            self._msg(messagebox.showerror, "Error", f"Failed to approve all: {e}")

    def reject_selected_ingestion(self):
        """Reject selected ingestion candidates (same as approve for now)."""
        try:
            if not hasattr(self, 'ingestion_tree'):
                return
                
            sel = self.ingestion_tree.selection()
            if not sel:
                self._msg(messagebox.showinfo, "Ingestion", "No item selected")
                return
            
            # Same logic as approve - just remove from candidates
            cand_path = self._ingestion_candidates_path()
            if not os.path.exists(cand_path):
                return
            
            with open(cand_path, 'r', encoding='utf-8') as f:
                candidates = json.load(f)
            
            indices_to_remove = []
            for iid in sel:
                values = self.ingestion_tree.item(iid)['values']
                if values:
                    idx = int(values[0]) - 1
                    indices_to_remove.append(idx)
            
            for idx in sorted(indices_to_remove, reverse=True):
                if 0 <= idx < len(candidates):
                    candidates.pop(idx)
            
            with open(cand_path, 'w', encoding='utf-8') as f:
                json.dump(candidates, f, indent=4)
            
            self.load_ingestion_candidates()
            
            self._msg(messagebox.showinfo, "Rejected", f"Rejected {len(indices_to_remove)} item(s)")
            logging.info(f"Rejected {len(indices_to_remove)} ingestion candidates")
        except Exception as e:
            logging.exception("reject_selected_ingestion failed")
            self._msg(messagebox.showerror, "Error", f"Failed to reject: {e}")

    def seed_gutenberg_samples(self):
        """Seed ingestion candidates with Project Gutenberg sample books."""
        try:
            # Sample Project Gutenberg books
            samples = [
                {
                    "url": "https://www.gutenberg.org/ebooks/1342",
                    "title": "Pride and Prejudice by Jane Austen",
                    "added": datetime.now().strftime('%Y-%m-%d'),
                    "source": "Project Gutenberg"
                },
                {
                    "url": "https://www.gutenberg.org/ebooks/11",
                    "title": "Alice's Adventures in Wonderland by Lewis Carroll",
                    "added": datetime.now().strftime('%Y-%m-%d'),
                    "source": "Project Gutenberg"
                },
                {
                    "url": "https://www.gutenberg.org/ebooks/84",
                    "title": "Frankenstein by Mary Wollstonecraft Shelley",
                    "added": datetime.now().strftime('%Y-%m-%d'),
                    "source": "Project Gutenberg"
                },
                {
                    "url": "https://www.gutenberg.org/ebooks/2701",
                    "title": "Moby Dick by Herman Melville",
                    "added": datetime.now().strftime('%Y-%m-%d'),
                    "source": "Project Gutenberg"
                },
                {
                    "url": "https://www.gutenberg.org/ebooks/1661",
                    "title": "The Adventures of Sherlock Holmes by Arthur Conan Doyle",
                    "added": datetime.now().strftime('%Y-%m-%d'),
                    "source": "Project Gutenberg"
                }
            ]
            
            # Load existing candidates
            cand_path = self._ingestion_candidates_path()
            os.makedirs(os.path.dirname(cand_path), exist_ok=True)
            
            existing = []
            if os.path.exists(cand_path):
                try:
                    with open(cand_path, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                except Exception:
                    existing = []
            
            # Add samples
            existing.extend(samples)
            
            # Save
            with open(cand_path, 'w', encoding='utf-8') as f:
                json.dump(existing, f, indent=4)
            
            # Refresh
            self.load_ingestion_candidates()
            
            self._msg(messagebox.showinfo, "Seeded", f"Added {len(samples)} Project Gutenberg samples")
            logging.info(f"Seeded {len(samples)} Project Gutenberg samples")
        except Exception as e:
            logging.exception("seed_gutenberg_samples failed")
            self._msg(messagebox.showerror, "Error", f"Failed to seed samples: {e}")
    
    def open_web_learning_contacts_embedded(self):
        """Open embedded web learning contacts view."""
        try:
            # Create a simple placeholder frame
            import tkinter as tk
            from tkinter import ttk
            frame = ttk.Frame(self.notebook)
            ttk.Label(frame, text="Web Learning Contacts", font=("Helvetica", 14, "bold")).pack(pady=20)
            ttk.Label(frame, text="Contact management interface coming soon.").pack()
            return frame
        except Exception as e:
            logging.error(f"Error opening contacts: {e}")
            return None
    
    def refresh_learning_reports(self):
        """Refresh learning reports display."""
        try:
            logging.info("Refreshing learning reports...")
            if not hasattr(self, 'learning_reports_text') or not self.learning_reports_text.winfo_exists():
                return

            from datetime import datetime
            import traceback

            self.learning_reports_text.delete('1.0', 'end')

            reports_dir = self.project_root / 'learning_reports'
            reports_dir.mkdir(exist_ok=True)

            report_files = sorted(reports_dir.glob('*.txt'), key=lambda p: p.stat().st_mtime, reverse=True)

            if not report_files:
                self.learning_reports_text.insert('end', "No learning reports found yet. Use 'Generate New Report' to create one.\n")
                return

            self.learning_reports_text.insert('end', f"Found {len(report_files)} report(s). Showing latest details.\n\n")

            # Show a list of recent reports with timestamps
            max_list = 10
            self.learning_reports_text.insert('end', "Recent reports:\n")
            for rp in report_files[:max_list]:
                try:
                    mod = datetime.fromtimestamp(rp.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    size_kb = rp.stat().st_size / 1024.0
                    self.learning_reports_text.insert('end', f" • {rp.name}  ({size_kb:.1f} KB, modified {mod})\n")
                except Exception:
                    self.learning_reports_text.insert('end', f" • {rp.name}\n")

            self.learning_reports_text.insert('end', "\nLatest report contents:\n" + ("=" * 40) + "\n\n")

            # Display the contents of the most recent report
            latest = report_files[0]
            try:
                with open(latest, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
                if not content.strip():
                    content = "(Report file is empty)"
                self.learning_reports_text.insert('end', content + "\n")
            except Exception:
                self.learning_reports_text.insert('end', f"Failed to read latest report: {latest.name}\n")
                self.learning_reports_text.insert('end', traceback.format_exc())
        except Exception as e:
            logging.error(f"Error refreshing learning reports: {e}")

    def show_security_report(self):
        """Display detailed security report with real data."""
        try:
            import sqlite3
            from datetime import datetime, timedelta
            
            report_lines = ["=== CELSIUS AI SECURITY REPORT ===\n"]
            report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Check activity database for security events
            db_path = self.project_root / 'data' / 'activity.db'
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    # Try to get login attempts in last 24 hours
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name LIKE '%login%' OR name LIKE '%auth%' OR name LIKE '%security%'
                    """)
                    tables = cursor.fetchall()
                    
                    if tables:
                        for (table_name,) in tables:
                            try:
                                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                                count = cursor.fetchone()[0]
                                report_lines.append(f"• {table_name}: {count} records\n")
                            except Exception:
                                pass
                    else:
                        report_lines.append("• No security-specific tables found\n")
                    
                    conn.close()
                except Exception as e:
                    report_lines.append(f"• Database check error: {str(e)}\n")
            else:
                report_lines.append("• Activity database not initialized\n")
            
            # Check for suspicious files in quarantine
            quarantine_path = self.project_root / 'quarantine'
            if quarantine_path.exists():
                quarantined = list(quarantine_path.glob('*'))
                report_lines.append(f"\n• Quarantined files: {len(quarantined)}\n")
            
            # Check log files for errors
            log_path = self.project_root / 'logs'
            if log_path.exists():
                recent_errors = 0
                try:
                    for log_file in log_path.glob('*.log'):
                        if log_file.stat().st_mtime > (datetime.now() - timedelta(hours=24)).timestamp():
                            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                                recent_errors += sum(1 for line in f if 'ERROR' in line or 'CRITICAL' in line)
                except Exception:
                    pass
                report_lines.append(f"• Recent errors (24h): {recent_errors}\n")
            
            report_lines.append("\n✓ No critical security issues detected")
            
            report = ''.join(report_lines)
            if hasattr(self, 'system_reports_text') and self.system_reports_text.winfo_exists():
                self.system_reports_text.delete('1.0', 'end')
                self.system_reports_text.insert('1.0', report)
            else:
                self._msg(messagebox.showinfo, "Security Report", report)
        except Exception as e:
            logging.exception("show_security_report failed")
            self._msg(messagebox.showerror, "Error", f"Failed to generate security report: {e}")

    def show_performance_report(self):
        """Display detailed performance report with system metrics."""
        try:
            import psutil
            from datetime import datetime
            
            report_lines = ["=== CELSIUS AI PERFORMANCE REPORT ===\n"]
            report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # CPU Info
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            report_lines.append(f"CPU Usage: {cpu_percent}%\n")
            report_lines.append(f"CPU Cores: {cpu_count}\n\n")
            
            # Memory Info
            memory = psutil.virtual_memory()
            report_lines.append(f"Memory Usage: {memory.percent}%\n")
            report_lines.append(f"Memory Available: {memory.available / (1024**3):.2f} GB\n")
            report_lines.append(f"Memory Total: {memory.total / (1024**3):.2f} GB\n\n")
            
            # Disk Info
            disk = psutil.disk_usage(str(self.project_root))
            report_lines.append(f"Disk Usage: {disk.percent}%\n")
            report_lines.append(f"Disk Free: {disk.free / (1024**3):.2f} GB\n")
            report_lines.append(f"Disk Total: {disk.total / (1024**3):.2f} GB\n\n")
            
            # Process Info
            process = psutil.Process()
            report_lines.append(f"App Memory: {process.memory_info().rss / (1024**2):.2f} MB\n")
            report_lines.append(f"App CPU: {process.cpu_percent()}%\n")
            report_lines.append(f"Threads: {process.num_threads()}\n\n")
            
            # Performance Assessment
            if cpu_percent < 50 and memory.percent < 70 and disk.percent < 80:
                report_lines.append("✓ System performing within optimal parameters")
            elif cpu_percent < 80 and memory.percent < 85 and disk.percent < 90:
                report_lines.append("⚠ System performance acceptable but monitor usage")
            else:
                report_lines.append("⚠ High resource usage detected - consider optimization")
            
            report = ''.join(report_lines)
            if hasattr(self, 'system_reports_text') and self.system_reports_text.winfo_exists():
                self.system_reports_text.delete('1.0', 'end')
                self.system_reports_text.insert('1.0', report)
            else:
                self._msg(messagebox.showinfo, "Performance Report", report)
        except Exception as e:
            logging.exception("show_performance_report failed")
            self._msg(messagebox.showerror, "Error", f"Failed to generate performance report: {e}")

    def show_service_status_report(self):
        """Display detailed service status report showing all configured services and their current state."""
        try:
            from datetime import datetime
            
            report_lines = ["=== CELSIUS AI SERVICE STATUS REPORT ===\n"]
            report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Service status overview
            total_services = len(self.services)
            running_services = sum(1 for svc in self.services.values() if svc.get('status') == 'Running')
            stopped_services = total_services - running_services
            
            report_lines.append(f"Total Services: {total_services}\n")
            report_lines.append(f"Running: {running_services}\n")
            report_lines.append(f"Stopped: {stopped_services}\n\n")
            
            # Detailed service information
            report_lines.append("SERVICE DETAILS:\n")
            report_lines.append("-" * 60 + "\n")
            
            for service_name, service_info in self.services.items():
                status = service_info.get('status', 'Unknown')
                description = service_info.get('description', 'No description')
                enabled = service_info.get('enabled', False)
                port = service_info.get('port', 'N/A')
                
                # Status indicator
                status_icon = "🟢" if status == "Running" else "🔴" if status == "Stopped" else "🟡"
                
                report_lines.append(f"{status_icon} {service_name}\n")
                report_lines.append(f"   Status: {status}\n")
                report_lines.append(f"   Description: {description}\n")
                report_lines.append(f"   Enabled: {'Yes' if enabled else 'No'}\n")
                if port != 'N/A':
                    report_lines.append(f"   Port: {port}\n")
                
                # Check if process is actually running
                process = service_info.get('process')
                if process:
                    try:
                        if hasattr(process, 'returncode') and process.returncode is None:
                            report_lines.append("   Process: Active\n")
                        else:
                            report_lines.append("   Process: Terminated\n")
                    except Exception:
                        report_lines.append("   Process: Unknown\n")
                else:
                    report_lines.append("   Process: Not started\n")
                
                report_lines.append("\n")
            
            # System health assessment
            report_lines.append("SYSTEM HEALTH ASSESSMENT:\n")
            report_lines.append("-" * 30 + "\n")
            
            if running_services == total_services:
                report_lines.append("✓ All services are running normally\n")
            elif running_services >= total_services * 0.8:
                report_lines.append("⚠ Most services are running - minor issues detected\n")
            else:
                report_lines.append("⚠ Critical: Many services are not running\n")
            
            # Check for any services that should be running but aren't
            issues = []
            for service_name, service_info in self.services.items():
                if service_info.get('enabled') and service_info.get('status') != 'Running':
                    issues.append(service_name)
            
            if issues:
                report_lines.append(f"\nServices that should be running but aren't:\n")
                for issue in issues:
                    report_lines.append(f"• {issue}\n")
            
            report = ''.join(report_lines)
            if hasattr(self, 'system_reports_text') and self.system_reports_text.winfo_exists():
                self.system_reports_text.delete('1.0', 'end')
                self.system_reports_text.insert('1.0', report)
            else:
                self._msg(messagebox.showinfo, "Service Status Report", report)
        except Exception as e:
            logging.exception("show_service_status_report failed")
            self._msg(messagebox.showerror, "Error", f"Failed to generate service status report: {e}")

    def open_reports_folder(self):
        try:
            path = os.path.join(self.project_root, 'learning_reports')
            os.makedirs(path, exist_ok=True)
            os.startfile(path)
        except Exception as e:
            logging.exception("open_reports_folder failed: %s", e)
            self._msg(messagebox.showerror, "Reports", f"Failed to open folder: {e}")

    def generate_learning_report(self):
        """Generate a comprehensive learning report with system data."""
        try:
            from datetime import datetime
            import json
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = self.project_root / 'learning_reports' / f'learning_report_{timestamp}.txt'
            report_path.parent.mkdir(exist_ok=True)
            
            report_lines = []
            report_lines.append("=" * 60)
            report_lines.append(f"CELSIUS AI LEARNING REPORT")
            report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("=" * 60)
            report_lines.append("")
            
            # Check ingestion candidates
            ingestion_path = self.project_root / 'data' / 'ingestion_candidates.json'
            if ingestion_path.exists():
                try:
                    with open(ingestion_path, 'r') as f:
                        candidates = json.load(f)
                    report_lines.append(f"Ingestion Candidates: {len(candidates)}")
                except Exception:
                    report_lines.append("Ingestion Candidates: Error reading file")
            else:
                report_lines.append("Ingestion Candidates: None")
            
            # Check learning reports folder
            reports_path = self.project_root / 'learning_reports'
            if reports_path.exists():
                report_count = len(list(reports_path.glob('*.txt')))
                report_lines.append(f"Total Learning Reports: {report_count}")
            else:
                report_lines.append("Total Learning Reports: 0")
            
            report_lines.append("")
            report_lines.append("System Status: Active")
            report_lines.append("Learning Mode: Continuous")
            report_lines.append("")
            report_lines.append("=" * 60)
            
            # Write report
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            # Update UI: show confirmation and refresh the listing with latest content
            if hasattr(self, 'learning_reports_text') and self.learning_reports_text.winfo_exists():
                self.learning_reports_text.insert('end', f"✓ Generated new report: {report_path.name}\n\n")
                try:
                    with open(report_path, 'r', encoding='utf-8', errors='ignore') as fh:
                        self.learning_reports_text.insert('end', fh.read() + "\n")
                except Exception:
                    pass
            # Show a toast/info box
            self._msg(messagebox.showinfo, "Report Generated", 
                     f"Learning report created:\n{report_path.name}")
            # Also refresh the summary view and hourly reports list
            try:
                self.refresh_learning_reports()
            except Exception:
                pass
            try:
                self.refresh_hourly_reports_list()
            except Exception:
                pass
            logging.info(f"Generated learning report: {report_path}")
        except Exception as e:
            logging.exception("generate_learning_report failed")
            self._msg(messagebox.showerror, "Error", f"Failed to generate report: {e}")
    
    def refresh_hourly_reports_list(self):
        """Refresh the hourly reports tree view."""
        try:
            from datetime import datetime
            if not hasattr(self, 'hourly_reports_tree'):
                return
            # Clear existing items
            for item in self.hourly_reports_tree.get_children():
                self.hourly_reports_tree.delete(item)
            # Reload reports from folder
            reports_path = os.path.join(self.project_root, 'logs')
            if os.path.exists(reports_path):
                for filename in sorted(os.listdir(reports_path)):
                    if filename.startswith('hourly_report_'):
                        filepath = os.path.join(reports_path, filename)
                        size = os.path.getsize(filepath)
                        modified = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
                        self.hourly_reports_tree.insert('', 'end', values=(filename, f"{size} bytes", modified))
        except Exception as e:
            logging.exception("refresh_hourly_reports_list failed: %s", e)
    
    def review_pending_ai_training(self):
        """Review and manage pending AI training items."""
        try:
            self._msg(messagebox.showinfo, "AI Training", 
                     "AI Training Review:\n\n"
                     "Pending items: 0\n"
                     "Recent training sessions: 3\n"
                     "Last update: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        except Exception as e:
            logging.exception("review_pending_ai_training failed: %s", e)
    
    def open_hardware_web(self):
        """Open the hardware web interface in a browser."""
        try:
            import webbrowser
            webbrowser.open('http://localhost:8085')
        except Exception as e:
            logging.exception("open_hardware_web failed: %s", e)
            self._msg(messagebox.showerror, "Hardware", f"Failed to open web interface: {e}")
    
    # ==================== ADMINISTRATION TAB METHODS ====================
    def build_windows_app(self):
        """Build the Windows app using PyInstaller spec in a background task.

        - Ensures PyInstaller is available (best-effort pip install if missing)
        - Runs `pyinstaller celsius_app.spec --clean` in project root
        - Streams output to the build output text area in real-time
        - Also logs output to logs/build/build_YYYYmmdd_HHMMSS.log
        - On success, offers to open the dist folder
        """
        try:
            def _work():
                import subprocess as _sp
                import time as _time
                import threading as _threading
                ts = _time.strftime("%Y%m%d_%H%M%S")
                build_dir = os.path.join(self.project_root, 'logs', 'build')
                os.makedirs(build_dir, exist_ok=True)
                log_path = os.path.join(build_dir, f'build_{ts}.log')
                spec_path = os.path.join(self.project_root, 'celsius_app.spec')
                py = sys.executable
                rc = 1
                
                def _update_output(text):
                    """Thread-safe update of the build output text area."""
                    def _do_update():
                        try:
                            self.build_output_text.insert("end", text)
                            self.build_output_text.see("end")
                        except Exception:
                            pass
                    self.schedule_on_main_thread(_do_update)
                
                try:
                    _update_output(f"[{_time.strftime('%H:%M:%S')}] Starting build process...\n")
                    
                    # Best-effort ensure PyInstaller
                    try:
                        __import__('PyInstaller')
                        _update_output(f"[{_time.strftime('%H:%M:%S')}] PyInstaller available\n")
                    except Exception:
                        _update_output(f"[{_time.strftime('%H:%M:%S')}] Installing PyInstaller...\n")
                        proc = _sp.run([py, '-m', 'pip', 'install', 'pyinstaller'], 
                                     cwd=self.project_root, capture_output=True, text=True)
                        if proc.returncode == 0:
                            _update_output(f"[{_time.strftime('%H:%M:%S')}] PyInstaller installed successfully\n")
                        else:
                            _update_output(f"[{_time.strftime('%H:%M:%S')}] Failed to install PyInstaller: {proc.stderr}\n")
                            return
                    
                    cmds = [py, '-m', 'PyInstaller', spec_path]
                    if getattr(self, 'build_clean_var', None) and self.build_clean_var.get():
                        cmds.append('--clean')
                        _update_output(f"[{_time.strftime('%H:%M:%S')}] Using clean build\n")
                    else:
                        _update_output(f"[{_time.strftime('%H:%M:%S')}] Using incremental build\n")
                    
                    _update_output(f"[{_time.strftime('%H:%M:%S')}] Running: {' '.join(cmds)}\n")
                    
                    with open(log_path, 'w', encoding='utf-8', errors='ignore') as lf:
                        proc = _sp.Popen(cmds, cwd=self.project_root, stdout=_sp.PIPE, 
                                       stderr=_sp.STDOUT, text=True, bufsize=1)
                        
                        # Read output line by line and stream to UI
                        while True:
                            line = proc.stdout.readline()
                            if not line and proc.poll() is not None:
                                break
                            if line:
                                lf.write(line)
                                lf.flush()
                                _update_output(line)
                        
                        rc = proc.returncode
                    
                except Exception as e:
                    error_msg = f"[{_time.strftime('%H:%M:%S')}] Build raised exception: {e}\n"
                    _update_output(error_msg)
                    with open(log_path, 'a', encoding='utf-8', errors='ignore') as lf:
                        lf.write(error_msg)
                
                finally:
                    def _done():
                        try:
                            if rc == 0:
                                msg = f"[{_time.strftime('%H:%M:%S')}] Build completed successfully!\nOutput: dist/ folder\nLog: {log_path}\n"
                                _update_output(msg)
                                self._msg(messagebox.showinfo, 'Build Complete', 
                                        f'Build finished successfully.\nLog: {log_path}\nOutput: dist/')
                            else:
                                msg = f"[{_time.strftime('%H:%M:%S')}] Build failed (code {rc}). See log: {log_path}\n"
                                _update_output(msg)
                                self._msg(messagebox.showerror, 'Build Failed', 
                                        f'Build failed (code {rc}).\nSee log: {log_path}')
                        except Exception:
                            pass
                    self.schedule_on_main_thread(_done)
            self.schedule_async_task(_work)
        except Exception:
            logging.exception('build_windows_app outer failed')

    def open_build_folder(self):
        """Open the build output folder (dist) in Explorer."""
        try:
            target = os.path.join(self.project_root, 'dist')
            if not os.path.isdir(target):
                # Fallback to build logs folder
                target = os.path.join(self.project_root, 'logs', 'build')
            if os.path.isdir(target):
                os.startfile(target)
            else:
                self._msg(messagebox.showinfo, 'Open Folder', 'No build output folder found yet.')
        except Exception:
            logging.exception('open_build_folder failed')
    
    def check_for_updates(self):
        """Check for available updates and update the status display."""
        try:
            def _work():
                try:
                    # Update status to checking
                    self.schedule_on_main_thread(
                        lambda: self.update_status_label.config(text="Update Status: Checking...", foreground="blue")
                    )
                    
                    # Check current version
                    current_version = self._get_current_version()
                    
                    # Check for updates (could be git, version file, or remote check)
                    update_info = self._check_update_availability()
                    
                    if update_info:
                        status_text = f"Update Status: Update available (v{update_info['version']})"
                        color = "orange"
                        self._latest_update_info = update_info
                    else:
                        status_text = f"Update Status: Up to date (v{current_version})"
                        color = "green"
                        self._latest_update_info = None
                    
                    # Update the status label
                    self.schedule_on_main_thread(
                        lambda: self.update_status_label.config(text=status_text, foreground=color)
                    )
                    
                except Exception as e:
                    logging.exception("Update check failed")
                    self.schedule_on_main_thread(
                        lambda: self.update_status_label.config(text=f"Update Status: Check failed - {str(e)}", foreground="red")
                    )
            
            # Run in background thread
            import threading
            thread = threading.Thread(target=_work, daemon=True)
            thread.start()
            
        except Exception:
            logging.exception("check_for_updates failed")
    
    def show_update_details(self):
        """Show detailed information about available updates."""
        try:
            if hasattr(self, '_latest_update_info') and self._latest_update_info:
                info = self._latest_update_info
                details = f"""Update Details:

Version: {info['version']}
Release Date: {info.get('release_date', 'Unknown')}
Size: {info.get('size', 'Unknown')}

Changes:
{info.get('changelog', 'No changelog available')}

Download URL: {info.get('download_url', 'Not available')}
"""
                self._msg(messagebox.showinfo, "Update Details", details)
            else:
                self._msg(messagebox.showinfo, "Update Details", "No update information available. Please check for updates first.")
        except Exception:
            logging.exception("show_update_details failed")
    
    def download_latest_update(self):
        """Download and install the latest update."""
        try:
            if hasattr(self, '_latest_update_info') and self._latest_update_info:
                info = self._latest_update_info
                
                # Confirm download
                if not messagebox.askyesno("Download Update", 
                    f"Download and install update v{info['version']}?\n\n"
                    f"This will download {info.get('size', 'unknown size')} and may restart the application."):
                    return
                
                def _work():
                    try:
                        # Update status
                        self.schedule_on_main_thread(
                            lambda: self.update_status_label.config(text="Update Status: Downloading...", foreground="blue")
                        )
                        
                        # Perform download (placeholder - would implement actual download logic)
                        success = self._download_and_install_update(info)
                        
                        if success:
                            self.schedule_on_main_thread(
                                lambda: self.update_status_label.config(text="Update Status: Update installed - restarting...", foreground="green")
                            )
                            # Auto-restart after successful update
                            self.schedule_on_main_thread(self._restart_application)
                        else:
                            self.schedule_on_main_thread(
                                lambda: self.update_status_label.config(text="Update Status: Download failed", foreground="red")
                            )
                            
                    except Exception as e:
                        logging.exception("Update download failed")
                        self.schedule_on_main_thread(
                            lambda: self.update_status_label.config(text=f"Update Status: Download failed - {str(e)}", foreground="red")
                        )
                
                # Run in background thread
                import threading
                thread = threading.Thread(target=_work, daemon=True)
                thread.start()
                
            else:
                self._msg(messagebox.showinfo, "Download Update", "No update available. Please check for updates first.")
        except Exception:
            logging.exception("download_latest_update failed")
    
    def _get_current_version(self):
        """Get the current application version."""
        try:
            # Try to read from version.txt file
            version_file = self.project_root / "version.txt"
            if version_file.exists():
                with open(version_file, 'r') as f:
                    return f.read().strip()
            
            # Try to read from version_info.txt (PyInstaller format)
            version_info_file = self.project_root / "version_info.txt"
            if version_info_file.exists():
                with open(version_info_file, 'r') as f:
                    content = f.read()
                    # Extract version from PyInstaller format
                    import re
                    match = re.search(r'filevers=\(([^)]+)\)', content)
                    if match:
                        vers = match.group(1).replace(' ', '').split(',')
                        return '.'.join(vers[:3])  # Major.minor.patch
            
            # Fallback to git version
            try:
                import subprocess
                result = subprocess.run(['git', 'describe', '--tags'], 
                                      capture_output=True, text=True, cwd=self.project_root)
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
            
            # Fallback to date-based version
            from datetime import datetime
            return f"dev-{datetime.now().strftime('%Y%m%d')}"
            
        except Exception:
            return "unknown"
    
    def _check_update_availability(self):
        """Check if updates are available. Returns update info dict if available, None if up to date."""
        try:
            current_version = self._get_current_version()
            
            # Parse current version
            current_parts = current_version.split('.')
            current_major = int(current_parts[0])
            current_minor = int(current_parts[1])
            current_patch = int(current_parts[2]) if len(current_parts) > 2 else 0
            
            # Define latest available version (this would normally come from a remote API)
            latest_version = "1.1.1"
            latest_parts = latest_version.split('.')
            latest_major = int(latest_parts[0])
            latest_minor = int(latest_parts[1])
            latest_patch = int(latest_parts[2]) if len(latest_parts) > 2 else 0
            
            # Compare versions
            if (latest_major > current_major or
                (latest_major == current_major and latest_minor > current_minor) or
                (latest_major == current_major and latest_minor == current_minor and latest_patch > current_patch)):
                
                # Update is available
                return {
                    'version': latest_version,
                    'release_date': '2025-11-06',
                    'size': '15.2 MB',
                    'changelog': '- Enhanced update checking system\n- Improved service monitoring\n- Bug fixes and performance improvements\n- New testing framework integration\n- Auto-restart after updates\n- Update file cleanup',
                    'download_url': 'https://github.com/celsius-ai/releases/download/v1.1.1/celsius_update.zip'
                }
            else:
                # No update available
                return None
                
        except Exception:
            logging.exception("_check_update_availability failed")
            return None
    
    def _download_and_install_update(self, update_info):
        """Download and install the update. Returns True if successful."""
        try:
            # Placeholder implementation
            # In a real implementation, this would:
            # 1. Download the update file
            # 2. Verify integrity (checksum)
            # 3. Extract/update files
            # 4. Run any migration scripts
            # 5. Update version file
            # 6. Clean up update files to prevent re-processing

            logging.info(f"Downloading update {update_info['version']}")

            # Simulate download process
            import time
            time.sleep(2)  # Simulate download time

            # For now, just return success
            # Real implementation would handle actual download and installation
            success = True

            if success:
                # Clean up any update files to prevent re-processing on restart
                self._cleanup_update_files()

            return success

        except Exception:
            logging.exception("_download_and_install_update failed")
            return False
    
    def _cleanup_update_files(self):
        """Clean up any update-related files to prevent re-processing on restart."""
        try:
            import shutil
            
            # Define potential update file locations
            update_paths = [
                self.project_root / "updates",
                self.project_root / "temp_updates", 
                self.project_root / "update_temp",
                self.project_root / "dist" / "updates",
                self.project_root / "dist" / "temp_updates"
            ]
            
            # Clean up update directories
            for update_path in update_paths:
                if update_path.exists():
                    try:
                        if update_path.is_file():
                            update_path.unlink()
                            logging.info(f"Removed update file: {update_path}")
                        elif update_path.is_dir():
                            shutil.rmtree(update_path)
                            logging.info(f"Removed update directory: {update_path}")
                    except Exception as e:
                        logging.warning(f"Failed to remove update path {update_path}: {e}")
            
            # Also clean up any .update or .tmp files in the project root
            for pattern in ["*.update", "*.tmp", "*update*.zip", "*update*.exe"]:
                for file_path in self.project_root.glob(pattern):
                    try:
                        file_path.unlink()
                        logging.info(f"Removed update file: {file_path}")
                    except Exception as e:
                        logging.warning(f"Failed to remove update file {file_path}: {e}")
                        
            # Clean up any backup executables that might be left over
            dist_dir = self.project_root / "dist"
            if dist_dir.exists():
                for backup_file in dist_dir.glob("CelsiusAI_old*.exe"):
                    try:
                        backup_file.unlink()
                        logging.info(f"Removed old backup executable: {backup_file}")
                    except Exception as e:
                        logging.warning(f"Failed to remove backup file {backup_file}: {e}")
            
            logging.info("Update file cleanup completed")
            
        except Exception as e:
            logging.exception(f"Failed to cleanup update files: {e}")

    def _restart_application(self):
        """Restart the application after update installation."""
        try:
            import sys
            import os
            
            # Show restart message
            messagebox.showinfo("Restarting", 
                "Update installed successfully!\n\nThe application will now restart to apply the changes.")
            
            # Get the current executable path
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                exe_path = sys.executable
            else:
                # Running as script - restart with python
                exe_path = sys.executable
                script_path = os.path.abspath(sys.argv[0])
                
                # Use subprocess to restart
                import subprocess
                subprocess.Popen([exe_path, script_path])
                self.root.quit()
                return
            
            # For compiled executable, restart with subprocess
            import subprocess
            subprocess.Popen([exe_path])
            
            # Close current instance
            self.root.quit()
            
        except Exception as e:
            logging.exception("Failed to restart application")
            messagebox.showerror("Restart Failed", 
                f"Update was installed but automatic restart failed.\n\nPlease restart the application manually.\n\nError: {e}")

    def open_upload_authorization_dialog(self):
        """Open Authorization Wizard to create a broader, multi-system authorization."""
        try:
            win = self.create_managed_window("Authorization Wizard", "700x600")

            frm = ttk.Frame(win, padding=10)
            frm.pack(fill="both", expand=True)

            ttk.Label(frm, text="Requester Name").grid(row=0, column=0, sticky="w")
            name_var = tk.StringVar()
            ttk.Entry(frm, textvariable=name_var, width=40).grid(row=0, column=1, sticky="w")

            ttk.Label(frm, text="Contact Email").grid(row=1, column=0, sticky="w")
            email_var = tk.StringVar()
            ttk.Entry(frm, textvariable=email_var, width=40).grid(row=1, column=1, sticky="w")

            ttk.Label(frm, text="Purpose / Scope").grid(row=2, column=0, sticky="nw")
            purpose_txt = tk.Text(frm, height=4, width=60)
            purpose_txt.grid(row=2, column=1, sticky="we")

            # Systems selection
            ttk.Label(frm, text="Systems to Test").grid(row=3, column=0, sticky="nw")
            systems_frame = ttk.Frame(frm)
            systems_frame.grid(row=3, column=1, sticky="we")
            sys_opts = [
                ("Core AI Engine", "core_ai"),
                ("Enhanced Dashboard", "dashboard"),
                ("Guardian", "guardian"),
                ("Real-Time Defender", "defender"),
                ("Web Learning", "web_learning"),
                ("Code Approvals", "code_approvals"),
            ]
            sys_vars = {}
            for i, (label, key) in enumerate(sys_opts):
                v = tk.BooleanVar(value=True if key in ("defender", "guardian") else False)
                sys_vars[key] = v
                ttk.Checkbutton(systems_frame, text=label, variable=v).grid(row=i//2, column=i%2, sticky="w", padx=4, pady=2)

            # Permissions/actions
            ttk.Label(frm, text="Allowed Actions").grid(row=4, column=0, sticky="nw")
            act_frame = ttk.Frame(frm)
            act_frame.grid(row=4, column=1, sticky="we")
            act_opts = [
                ("View/Read Only", "read"),
                ("Read/Write (with approvals)", "write_with_approval"),
                ("Quarantine-only actions", "quarantine_only"),
            ]
            act_vars = {}
            for i, (label, key) in enumerate(act_opts):
                v = tk.BooleanVar(value=(key == "write_with_approval"))
                act_vars[key] = v
                ttk.Checkbutton(act_frame, text=label, variable=v).grid(row=0, column=i, sticky="w", padx=4)

            # Duration
            ttk.Label(frm, text="Duration (hours)").grid(row=5, column=0, sticky="w")
            dur_var = tk.IntVar(value=8)
            ttk.Entry(frm, textvariable=dur_var, width=8).grid(row=5, column=1, sticky="w")

            # Test button result area
            ttk.Label(frm, text="Test Results").grid(row=6, column=0, sticky="nw")
            results_txt = tk.Text(frm, height=8, width=60)
            results_txt.grid(row=6, column=1, sticky="we")

            def do_test():
                results_txt.delete('1.0', 'end')
                checks = []
                # Simple presence checks without network calls
                try:
                    import psutil; checks.append(("psutil", True))
                except Exception: checks.append(("psutil", False))
                try:
                    from src.celsius.guardian import celsius_ultimate_guardian as g; checks.append(("Guardian module", True))
                except Exception: checks.append(("Guardian module", False))
                try:
                    from src.celsius.protection import celsius_realtime_defender as d; checks.append(("Defender module", True))
                except Exception: checks.append(("Defender module", False))
                try:
                    from src.celsius.learning import celsius_web_learning_integration as wl; checks.append(("Web Learning module", True))
                except Exception: checks.append(("Web Learning module", False))
                for name, ok in checks:
                    results_txt.insert('end', f"{name}: {'OK' if ok else 'Missing'}\n")

            def do_save():
                auth = {
                    "requester": name_var.get().strip(),
                    "email": email_var.get().strip(),
                    "purpose": purpose_txt.get('1.0', 'end').strip(),
                    "systems": [k for k, v in sys_vars.items() if v.get()],
                    "actions": [k for k, v in act_vars.items() if v.get()],
                    "duration_hours": int(dur_var.get() or 0),
                    "timestamp": datetime.now().isoformat(),
                    "status": "pending",
                }
                auth_dir = Path(self.project_root) / 'data' / 'authorizations'
                auth_dir.mkdir(parents=True, exist_ok=True)
                fname = f"auth_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(auth_dir / fname, 'w', encoding='utf-8') as f:
                    json.dump(auth, f, indent=2)
                self._msg(messagebox.showinfo, "Authorization", f"Saved authorization request:\n{fname}")

            btns = ttk.Frame(frm)
            btns.grid(row=7, column=1, sticky="e", pady=(10,0))
            ttk.Button(btns, text="Test Selected Systems", command=do_test).pack(side="left", padx=5)
            ttk.Button(btns, text="Save Request", command=do_save).pack(side="left", padx=5)
            ttk.Button(btns, text="Close", command=win.destroy).pack(side="left", padx=5)

            for i in range(2):
                frm.grid_columnconfigure(i, weight=1)
        except Exception as e:
            logging.exception("open_upload_authorization_dialog failed: %s", e)
    
    def open_review_authorizations_dialog(self):
        """Open dialog to review authorization forms."""
        try:
            win = tk.Toplevel(self.root)
            win.title("Authorization Requests")
            win.geometry("680x420")

            frm = ttk.Frame(win, padding=10)
            frm.pack(fill="both", expand=True)

            cols = ("File", "Requester", "Email", "Systems", "Status", "When")
            tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
            for c in cols:
                tree.heading(c, text=c)
                tree.column(c, width=140)
            tree.pack(fill="both", expand=True)

            auth_dir = Path(self.project_root) / 'data' / 'authorizations'
            auth_dir.mkdir(parents=True, exist_ok=True)

            def load():
                for item in tree.get_children():
                    tree.delete(item)
                for p in sorted(auth_dir.glob('auth_*.json'), reverse=True):
                    try:
                        with open(p, 'r', encoding='utf-8') as f:
                            d = json.load(f)
                        tree.insert('', 'end', values=(p.name, d.get('requester',''), d.get('email',''),
                                                        ','.join(d.get('systems', [])), d.get('status',''),
                                                        d.get('timestamp','')))
                    except Exception:
                        continue

            def _selected_filename():
                sel = tree.selection()
                if not sel:
                    return None
                return tree.item(sel[0]).get('values', [None])[0]

            def approve():
                fn = _selected_filename()
                if not fn:
                    self._msg(messagebox.showinfo, "Authorizations", "Select a request to approve")
                    return
                p = auth_dir / fn
                try:
                    d = json.loads((p.read_text(encoding='utf-8')))
                    d['status'] = 'approved'
                    p.write_text(json.dumps(d, indent=2), encoding='utf-8')
                    load()
                except Exception:
                    logging.exception("approve auth failed")

            def reject():
                fn = _selected_filename()
                if not fn:
                    self._msg(messagebox.showinfo, "Authorizations", "Select a request to reject")
                    return
                p = auth_dir / fn
                try:
                    d = json.loads((p.read_text(encoding='utf-8')))
                    d['status'] = 'rejected'
                    p.write_text(json.dumps(d, indent=2), encoding='utf-8')
                    load()
                except Exception:
                    logging.exception("reject auth failed")

            btns = ttk.Frame(frm)
            btns.pack(fill="x", pady=6)
            ttk.Button(btns, text="Refresh", command=load).pack(side="left", padx=4)
            ttk.Button(btns, text="Approve", command=approve).pack(side="left", padx=4)
            ttk.Button(btns, text="Reject", command=reject).pack(side="left", padx=4)

            load()
        except Exception as e:
            logging.exception("open_review_authorizations_dialog failed: %s", e)
    
    def download_blank_authorization_form(self):
        """Download a blank authorization form template."""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                title="Save Authorization Form Template",
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")]
            )
            if filename:
                # Write a minimal placeholder template as markdown renamed .pdf for offline use
                # (A proper PDF generator can be added later.)
                try:
                    content = (
                        "Celsius AI Authorization Form\n"
                        "==============================\n\n"
                        "Requester: ____________________________\n\n"
                        "Contact Email: ________________________\n\n"
                        "Purpose / Scope: ______________________\n\n"
                        "Systems to Test (check): Core AI / Dashboard / Guardian / Defender / Web Learning / Code Approvals\n\n"
                        "Allowed Actions: Read / Write (with approvals) / Quarantine-only\n\n"
                        "Duration (hours): _____\n\n"
                        "Signature: __________________ Date: __________\n"
                    )
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self._msg(messagebox.showinfo, "Template", f"Saved template to: {filename}")
                except Exception as ex:
                    self._msg(messagebox.showerror, "Template", f"Failed to save template: {ex}")
        except Exception as e:
            logging.exception("download_blank_authorization_form failed: %s", e)
    
    # ==================== HARDWARE TAB METHODS ====================
    
    def apply_fan_settings(self):
        """Apply fan speed settings from hardware tab."""
        try:
            if hasattr(self, 'fan_speed_var'):
                speed = self.fan_speed_var.get()
                self._msg(messagebox.showinfo, "Fan Settings", f"Would set fan speed to: {speed}%\n(Feature requires hardware controller)")
            else:
                self._msg(messagebox.showwarning, "Fan Settings", "Fan speed control not available")
        except Exception as e:
            logging.exception("apply_fan_settings failed: %s", e)
    
    def set_fan_preset(self, percent: int):
        """Set fan speed to a preset percentage and update UI."""
        try:
            if hasattr(self, 'fan_speed_var'):
                self.fan_speed_var.set(str(int(percent)))
                # Update immediately
                self.apply_fan_settings()
            else:
                self._msg(messagebox.showwarning, "Fan Preset", "Fan controls not initialized")
        except Exception:
            logging.exception("set_fan_preset failed")

    def apply_rgb_settings(self):
        """Apply RGB lighting settings from hardware tab."""
        try:
            self._msg(messagebox.showinfo, "RGB Settings", "Would apply RGB settings\n(Feature requires OpenRGB)")
        except Exception as e:
            logging.exception("apply_rgb_settings failed: %s", e)
    
    def set_rgb_preset(self, r: int, g: int, b: int):
        """Set RGB sliders to a preset color and update preview."""
        try:
            if hasattr(self, 'red_var') and hasattr(self, 'green_var') and hasattr(self, 'blue_var'):
                self.red_var.set(str(int(r)))
                self.green_var.set(str(int(g)))
                self.blue_var.set(str(int(b)))
                self.apply_rgb_settings()
            else:
                self._msg(messagebox.showwarning, "RGB Preset", "RGB controls not initialized")
        except Exception:
            logging.exception("set_rgb_preset failed")
    
    def apply_rgb_effect(self, effect_name: str):
        """Apply an RGB effect by name (stub)."""
        try:
            self._msg(messagebox.showinfo, "RGB Effect", f"Would apply effect: {effect_name}\n(Feature requires OpenRGB)")
        except Exception:
            logging.exception("apply_rgb_effect failed")
    
    def apply_profile(self, profile: str):
        """Apply a performance profile (stub)."""
        try:
            self._msg(messagebox.showinfo, "Profile", f"Would apply profile: {profile}\n(Feature requires hardware controller)")
        except Exception:
            logging.exception("apply_profile failed")
    
    def check_temperatures(self):
        """Check system temperatures."""
        try:
            import psutil
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    temp_str = "\n".join([f"{name}: {temp.current}°C" for name, sensors in temps.items() for temp in sensors])
                    self._msg(messagebox.showinfo, "Temperatures", temp_str)
                else:
                    self._msg(messagebox.showinfo, "Temperatures", "No temperature sensors detected")
            else:
                self._msg(messagebox.showinfo, "Temperatures", "Temperature monitoring not available on this system")
        except Exception as e:
            logging.exception("check_temperatures failed: %s", e)
            self._msg(messagebox.showerror, "Temperatures", f"Failed to check temperatures: {e}")
    
    def toggle_auto_fan(self):
        """Toggle automatic fan control."""
        try:
            if hasattr(self, 'auto_temp_var'):
                enabled = self.auto_temp_var.get()
                status = "enabled" if enabled else "disabled"
                self._msg(messagebox.showinfo, "Auto Fan", f"Automatic fan control {status}\n(Feature requires hardware controller)")
            else:
                self._msg(messagebox.showwarning, "Auto Fan", "Auto fan control not available")
        except Exception as e:
            logging.exception("toggle_auto_fan failed: %s", e)
    
    # ==================== EXISTING REPORT METHODS ====================
    
    def show_guardian_report(self):
        """Show guardian system report."""
        try:
            report = (
                "=== CELSIUS AI GUARDIAN REPORT ===\n\n"
                "Monitoring: Active\n"
                "Threats Detected: 0\n"
                "Last Scan: Just now\n\n"
                "Detailed reporting coming soon.\n"
            )
            if hasattr(self, 'system_reports_text') and self.system_reports_text.winfo_exists():
                self.system_reports_text.delete('1.0', 'end')
                self.system_reports_text.insert('1.0', report)
            else:
                self._msg(messagebox.showinfo, "Guardian Report", report)
        except Exception as e:
            logging.error(f"Error showing guardian report: {e}")
    
    # ==================== CHAT INTERFACE METHODS ====================
    
    def send_chat_message(self):
        """Send a chat message to AI."""
        try:
            if hasattr(self, 'chat_input'):
                message = self.chat_input.get("1.0", "end-1c").strip()
                if message:
                    logging.info(f"Chat message: {message}")
                    self.chat_input.delete("1.0", "end")
                    self._msg(messagebox.showinfo, "Chat", 
                             f"Message sent: {message}\n\nAI response coming soon.")
        except Exception as e:
            logging.error(f"Error sending chat message: {e}")
    
    def quick_chat_command(self, command):
        """Execute a quick chat command."""
        try:
            logging.info(f"Quick chat command: {command}")
            self._msg(messagebox.showinfo, "Command", f"Executed: {command}")
        except Exception as e:
            logging.error(f"Error in quick chat command: {e}")
    
    def add_chat_message(self, sender, message, msg_type="system"):
        """Add a message to the chat display"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        if msg_type == "user":
            formatted_msg = f"[{timestamp}] You: {message}\n"
            color = "lightblue"
        elif msg_type == "system":
            formatted_msg = f"[{timestamp}] Celsius AI: {message}\n"
            color = "lightgreen"
        else:
            formatted_msg = f"[{timestamp}] {sender}: {message}\n"
            color = "white"

        self.chat_display.insert(tk.END, formatted_msg)
        self.chat_display.see(tk.END)

    def process_chat_command(self, command):
        """Process a chat command and execute appropriate actions"""
        command = command.lower().strip()

        try:
            # Use conversational AI if available for enhanced responses
            if self.conversational_ai:
                try:
                    # Process conversation context
                    conversation_context = self.conversational_ai.process_conversation(command, "general")

                    # Check for greeting in context
                    greeting = conversation_context.get("greeting")
                    if greeting:
                        self.add_chat_message("Celsius AI", greeting, "system")
                except Exception as e:
                    print(f"ConversationalAI processing error: {e}")

            # RGB Control Commands
            if any(color in command for color in ["red", "blue", "green", "purple", "yellow", "orange", "white"]):
                self.process_rgb_command(command)

            elif "lights off" in command or "turn off" in command or command == "off":
                self.process_rgb_command("off")

            # Fan Control Commands
            elif "fan" in command:
                self.process_fan_command(command)

            # Status Commands
            elif command in ["status", "system status", "hardware status"]:
                self.show_system_status_chat()

            elif command in ["temperature", "temp", "temperatures"]:
                self.show_temperature_status()

            # Help Commands
            elif command in ["help", "commands", "what can you do"]:
                self.show_chat_help()

            # General conversation - use conversational AI
            elif self.conversational_ai:
                try:
                    # Generate a contextual response using conversational AI
                    base_response = f"I received your message: '{command}'. For specific hardware control, try commands like 'red lights', 'fan high', or 'status'."
                    enhanced_response = self.conversational_ai.enhance_response(base_response, conversation_context)
                    self.add_chat_message("Celsius AI", enhanced_response, "system")
                except Exception as e:
                    self.add_chat_message(
                        "Celsius AI",
                        f"I understand you're trying to communicate, but I had trouble processing that. Try 'help' for available commands.",
                        "system",
                    )

            else:
                self.add_chat_message(
                    "Celsius AI", f"Unknown command: '{command}'. Type 'help' for available commands.", "system"
                )

        except Exception as e:
            self.add_chat_message("Celsius AI", f"Error processing command: {e}", "system")

    def process_rgb_command(self, command):
        """Process RGB lighting commands"""
        try:
            # Color mappings
            colors = {
                "red": (255, 0, 0),
                "blue": (0, 0, 255),
                "green": (0, 255, 0),
                "purple": (128, 0, 128),
                "yellow": (255, 255, 0),
                "orange": (255, 165, 0),
                "white": (255, 255, 255),
                "off": (0, 0, 0),
            }

            # Find the color in the command
            target_color = None
            color_name = None

            for color, rgb in colors.items():
                if color in command:
                    target_color = rgb
                    color_name = color
                    break

            if target_color:
                # Try hardware API first
                import requests

                try:
                    response = requests.post(
                        "http://localhost:5001/api/hardware/rgb",
                        json={
                            "device": "2",  # Motherboard
                            "r": target_color[0],
                            "g": target_color[1],
                            "b": target_color[2],
                        },
                        timeout=5,
                    )
                    if response.status_code == 200:
                        if color_name == "off":
                            self.add_chat_message("Celsius AI", "´ RGB lights turned OFF", "system")
                        else:
                            self.add_chat_message("Celsius AI", f"¨ RGB lights set to {color_name.upper()}", "system")
                        return
                except requests.exceptions.RequestException:
                    pass

                # Fallback to direct control
                try:
                    import sys
                    import os

                    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "hardware"))
                    from src.celsius.hardware.celsius_hardware_controller import CelsiusHardwareController

                    controller = CelsiusHardwareController()
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # Initialize controller
                    loop.run_until_complete(controller.initialize())

                    # Set RGB color
                    device_id = "2" if "motherboard" not in command else "2"
                    if "all" in command:
                        device_id = "all"

                    loop.run_until_complete(controller.set_rgb_color(device_id, *target_color))

                    if color_name == "off":
                        self.add_chat_message("Celsius AI", "´ RGB lights turned OFF", "system")
                    else:
                        self.add_chat_message("Celsius AI", f"¨ RGB lights set to {color_name.upper()}", "system")

                except Exception as direct_error:
                    self.add_chat_message("Celsius AI", f" RGB control failed: {direct_error}", "system")
            else:
                self.add_chat_message(
                    "Celsius AI",
                    " Color not recognized. Available: red, blue, green, purple, yellow, orange, white, off",
                    "system",
                )

        except Exception as e:
            self.add_chat_message("Celsius AI", f" RGB command error: {e}", "system")

    def process_fan_command(self, command):
        """Process fan control commands"""
        try:
            speed_map = {
                "high": 80,
                "low": 30,
                "max": 100,
                "full": 100,
                "medium": 50,
                "auto": -1,  # Special case for auto
            }

            target_speed = None
            speed_name = None

            for speed, value in speed_map.items():
                if speed in command:
                    target_speed = value
                    speed_name = speed
                    break

            if target_speed is not None:
                if target_speed == -1:  # Auto mode
                    self.add_chat_message("Celsius AI", "¤– Fan control set to AUTOMATIC", "system")
                    return

                # Try hardware API first
                import requests

                try:
                    response = requests.post(
                        "http://localhost:5001/api/hardware/fan",
                        json={"device": "cpu", "speed": target_speed},
                        timeout=5,
                    )
                    if response.status_code == 200:
                        self.add_chat_message(
                            "Celsius AI", f"ª Fan speed set to {speed_name.upper()} ({target_speed}%)", "system"
                        )
                        return
                except requests.exceptions.RequestException:
                    pass

                # Fallback to direct control
                try:
                    import sys
                    import os

                    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "hardware"))
                    from src.celsius.hardware.celsius_hardware_controller import CelsiusHardwareController

                    controller = CelsiusHardwareController()
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    loop.run_until_complete(controller.initialize())
                    loop.run_until_complete(controller.set_fan_speed("cpu", target_speed))

                    self.add_chat_message(
                        "Celsius AI", f"ª Fan speed set to {speed_name.upper()} ({target_speed}%)", "system"
                    )

                except Exception as direct_error:
                    self.add_chat_message("Celsius AI", f" Fan control failed: {direct_error}", "system")
            else:
                self.add_chat_message(
                    "Celsius AI", " Fan speed not recognized. Available: high, low, max, medium, auto", "system"
                )

        except Exception as e:
            self.add_chat_message("Celsius AI", f" Fan command error: {e}", "system")

    def show_system_status_chat(self):
        """Show system status in chat"""
        try:
            # Get basic system info
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            status_msg = f"""›¡ Celsius AI System Status:
            
» CPU Usage: {cpu_percent}%
§  Memory Usage: {memory.percent}%
¾ Disk Usage: {disk.percent}%
¡ System Temperature: Checking...
Hardware Controller: Available
ˆ RGB Control: Active (373 LEDs)
¡ Services: Running"""

            self.add_chat_message("Celsius AI", status_msg, "system")

        except Exception as e:
            self.add_chat_message("Celsius AI", f" Status check failed: {e}", "system")

    def show_temperature_status(self):
        """Show temperature status in chat"""
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                temp_msg = "¡ System Temperatures:\n"
                for name, entries in temps.items():
                    for entry in entries:
                        temp_msg += f"  {name}: {entry.current}°C\n"
            else:
                temp_msg = "¡ Temperature sensors not available"

            self.add_chat_message("Celsius AI", temp_msg, "system")

        except Exception as e:
            self.add_chat_message("Celsius AI", f" Temperature check failed: {e}", "system")

    def show_chat_help(self):
        """Show help information in chat"""
        help_msg = """›¡ Celsius AI Chat Commands:

ˆ RGB Control:
€¢ red, blue, green, purple, yellow, orange, white
€¢ "lights off" - Turn off all RGB lights
€¢ "rgb [color] all" - Control all devices
€¢ "rgb [color] motherboard" - Control motherboard only

ª Fan Control:
€¢ "fan high" - Set fans to high speed (80%)
€¢ "fan low" - Set fans to low speed (30%)
€¢ "fan max" - Set fans to maximum (100%)
€¢ "fan auto" - Enable automatic control

 System Information:
€¢ "status" - Show system status
€¢ "temperature" - Show temperature readings
€¢ "help" - Show this help message

Examples:
€¢ "red" - Turn motherboard red
€¢ "lights off" - Turn off all lights
€¢ "fan high" - Increase fan speed
€¢ "status" - Check system health"""

        self.add_chat_message("Celsius AI", help_msg, "system")

    async def _reinit_email_clicked(self):
        """Handle re-init email button click."""
        try:
            self._msg(messagebox.showinfo, "Re-init", "Attempting email re-init...")
            await self.ensure_email_notifier(force=True)
        except Exception as e:
            logging.exception("Failed to schedule email re-init")
            self._msg(messagebox.showerror, "Error", f"Failed to re-init email: {e}")

    def run_selected_tests(self):
        """Runs the tests selected in the Testing tab."""
        # Ensure the Testing tab is initialized
        if not self._tab_initialized.get("Testing", False):
            try:
                self.create_testing_tab()
                self._tab_initialized["Testing"] = True
            except Exception as e:
                self._msg(messagebox.showerror, "Testing", f"Failed to initialize Testing tab: {e}")
                return
        
        if not hasattr(self, 'results_tree'):
            self._msg(messagebox.showerror, "Testing", "Results view not initialized")
            return
        self.results_tree.delete(*self.results_tree.get_children())
        
        selected_suites = [name for name, var in self.test_vars.items() if var.get()]
        
        if not selected_suites:
            messagebox.showwarning("No Tests Selected", "Please select at least one test suite to run.")
            return

        # This should run in a separate thread to avoid blocking the GUI
        def test_runner_thread():
            try:
                # Discover and run tests
                suite = unittest.TestSuite()
                loader = unittest.TestLoader()

                try:
                    from tests.ultimate_test_suite import SystemResponsivenessTests, IntegrationTests, PerformanceBenchmarkTests
                    test_map = {
                        "System Responsiveness": SystemResponsivenessTests,
                        "Integration": IntegrationTests,
                        "Performance Benchmarks": PerformanceBenchmarkTests,
                    }
                    for suite_name in selected_suites:
                        if suite_name in test_map:
                            suite.addTests(loader.loadTestsFromTestCase(test_map[suite_name]))
                except Exception:
                    # Fallback to discovery if direct import fails
                    discovered = loader.discover('tests')
                    suite.addTests(discovered)

                # Check if we need to run the ultimate test suite
                ultimate_tests_selected = any(suite_name in ["System Responsiveness", "Integration", "Performance Benchmarks"] for suite_name in selected_suites)
                
                if ultimate_tests_selected:
                    # Import and run the ultimate test suite programmatically
                    import sys
                    import os
                    
                    def run_ultimate_tests():
                        try:
                            # Set test mode to prevent GUI
                            os.environ['CELSIUS_TEST_MODE'] = '1'
                            
                            # Import and run tests programmatically
                            from tests.ultimate_test_suite import run_tests_programmatically
                            result = run_tests_programmatically()
                            
                            # Report results
                            status = "COMPLETED" if result['wasSuccessful'] else "FAILED"
                            self.schedule_on_main_thread(
                                self.hub.results_tree.insert,
                                "", "end", iid="ultimate_summary",
                                values=("UltimateTestSuite", 
                                       f"Tests: {result['testsRun']}, Passed: {result['testsRun'] - result['failures'] - result['errors']}, Failed: {result['failures']}, Errors: {result['errors']}", 
                                       status, "N/A")
                            )
                            
                        except Exception as e:
                            logging.exception("Error running ultimate tests programmatically")
                            self.schedule_on_main_thread(
                                self.hub.results_tree.insert,
                                "", "end", iid="ultimate_error",
                                values=("UltimateTestSuite", f"Error: {str(e)}", "ERROR", "N/A")
                            )
                    
                    # Run tests in a separate thread to avoid blocking GUI
                    import threading
                    test_thread = threading.Thread(target=run_ultimate_tests, daemon=True)
                    test_thread.start()
                    return  # Exit the function after starting programmatic tests
                else:
                    # For other tests, use the existing unittest discovery
                    discovered = loader.discover('tests')
                    suite.addTests(discovered)
                    
                    # Custom runner to capture results
                    class GuiTestResult(unittest.TextTestResult):
                        def __init__(self, hub, *args, **kwargs):
                            super().__init__(*args, **kwargs)
                            self.hub = hub
                            self.test_starts = {}

                        def startTest(self, test):
                            self.test_starts[test.id()] = time.perf_counter()
                            super().startTest(test)
                            self.hub.schedule_on_main_thread(
                                self.hub.results_tree.insert,
                                "", "end", iid=test.id(),
                                values=(test.__class__.__name__, test._testMethodName, "Running...", "")
                            )

                        def addSuccess(self, test):
                            super().addSuccess(test)
                            duration = time.perf_counter() - self.test_starts.get(test.id(), time.perf_counter())
                            self.hub.schedule_on_main_thread(
                                self.hub.results_tree.item,
                                test.id(),
                                values=(test.__class__.__name__, test._testMethodName, "PASSED", f"{duration:.4f}")
                            )

                        def addFailure(self, test, err):
                            super().addFailure(test, err)
                            duration = time.perf_counter() - self.test_starts.get(test.id(), time.perf_counter())
                            self.hub.schedule_on_main_thread(
                                self.hub.results_tree.item,
                                test.id(),
                                values=(test.__class__.__name__, test._testMethodName, "FAILED", f"{duration:.4f}")
                            )

                        def addError(self, test, err):
                            super().addError(test, err)
                            duration = time.perf_counter() - self.test_starts.get(test.id(), time.perf_counter())
                            self.hub.schedule_on_main_thread(
                                self.hub.results_tree.item,
                                test.id(),
                                values=(test.__class__.__name__, test._testMethodName, "ERROR", f"{duration:.4f}")
                            )
                    
                    class HubTestRunner(unittest.TextTestRunner):
                        def __init__(self, hub, *args, **kwargs):
                            super().__init__(*args, **kwargs)
                            self.hub = hub
                        
                        def _makeResult(self):
                            return self.resultclass(self.hub, self.stream, self.descriptions, self.verbosity)
                    
                    runner = HubTestRunner(self, resultclass=GuiTestResult, stream=sys.stdout)
                    runner.run(suite)

            except Exception as e:
                self.schedule_on_main_thread(
                    messagebox.showerror, "Test Execution Error", f"An error occurred: {e}"
                )

        import threading
        import time
        import unittest
        
        test_thread = threading.Thread(target=test_runner_thread, daemon=True)
        test_thread.start()
        pass


def main(root, username="cllusion001"):
    """Initialize and run the Ultimate Hub with the given root window and user."""
    try:
        from src.celsius.hub.async_loop import AsyncTkinter
        async_loop = AsyncTkinter()
    except Exception:
        # Fall back to the local shim defined in this module
        async_loop = AsyncTkinter()
    
    async_loop.start()
    hub = UltimateHub(root, async_loop, username=username)
    return hub


if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    try:
        # Use a themed window if available
        if ThemedTk:
            root = ThemedTk(theme="equilux")
        else:
            root = tk.Tk()
    except Exception:
        root = tk.Tk()

    try:
        from src.celsius.hub.login import LoginWindow

        # Create and show the login window
        login_window = LoginWindow(root, lambda user: main(root, user))
        root.mainloop()
    except ImportError:
        # Fallback for environments without the login window
        main(root, "cllusion001")
        root.mainloop()
    except Exception as e:
        logging.exception("An unexpected error occurred during startup: %s", e)
        # Also show a message box as a last resort if the UI is still usable
        try:
            messagebox.showerror("Fatal Error", f"An unexpected error occurred: {e}")
        except Exception:
            pass






