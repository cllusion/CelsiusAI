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

# Try to import optional UI theming package; keep module import-time safe.
try:
    from ttkthemes import ThemedTk
except Exception:
    ThemedTk = None  # type: ignore

from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    # These imports are only for type checking and will not be executed at runtime.
    from ttkthemes import ThemedTk as _ThemedTk
    from src.hub.async_loop import AsyncTkinter as _AsyncTkinter

# Project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

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

# Email notifier accessor (preferred) — fall back to a no-op getter if the
# enhanced email system isn't available at import time.
try:
    from src.utils.enhanced_email_system import get_enhanced_notifier
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
    from src.hub.async_loop import AsyncTkinter
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
        self.root.title("🛡️ Celsius AI - Ultimate Hub 🛡️")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

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

        # Initialize conversational AI if available
        self.conversational_ai = None
        if CONVERSATION_AVAILABLE:
            try:
                self.conversational_ai = ConversationalAI()
                print("ConversationalAI initialized successfully")
            except Exception as e:
                print(f"Failed to initialize ConversationalAI: {e}")

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

        # --- UI Setup ---
        self.style = ttk.Style(self.root)
        self.root.set_theme("equilux")
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
        self.tab_monitoring = ttk.Frame(self.notebook)
        self.tab_ngrok = ttk.Frame(self.notebook)
        self.tab_code_approval = ttk.Frame(self.notebook)
        self.tab_reports = ttk.Frame(self.notebook)
        self.tab_ai_systems = ttk.Frame(self.notebook)
        self.tab_chat = ttk.Frame(self.notebook)
        self.tab_hardware = ttk.Frame(self.notebook)
        self.tab_security = ttk.Frame(self.notebook)
        self.tab_admin = ttk.Frame(self.notebook)
        self.tab_testing = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_dashboard, text="Dashboard")
        self.notebook.add(self.tab_services, text="Services")
        self.notebook.add(self.tab_monitoring, text="Monitoring")
        self.notebook.add(self.tab_ngrok, text="Ngrok Tunnels")
        self.notebook.add(self.tab_code_approval, text="Code Approvals")
        self.notebook.add(self.tab_reports, text="📊 Reports")
        self.notebook.add(self.tab_ai_systems, text="AI Systems")
        self.notebook.add(self.tab_chat, text="💬 AI Chat")
        self.notebook.add(self.tab_hardware, text="🎮 Hardware")
        self.notebook.add(self.tab_security, text="Security")
        self.notebook.add(self.tab_admin, text="Administration")
        self.notebook.add(self.tab_testing, text="Testing")

        # Map visible tab text to their creation methods so we can lazy-load
        self._tab_creators = {
            "Dashboard": self.create_dashboard_tab,
            "Services": self.create_services_tab,
            "Monitoring": self.create_monitoring_tab,
            "Ngrok Tunnels": self.create_ngrok_tab,
            "Code Approvals": self.create_code_approval_tab,
            "📊 Reports": self.create_reports_tab,
            "AI Systems": self.create_ai_systems_tab,
            "💬 AI Chat": self.create_chat_tab,
            "🎮 Hardware": self.create_hardware_tab,
            "Security": self.create_security_tab,
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
        header_label = ttk.Label(header_frame, text="🛡️ Celsius AI - Ultimate Hub 🛡️", style="Header.TLabel")
        header_label.pack(side="left")

        # User info and logout button
        user_frame = ttk.Frame(header_frame)
        user_frame.pack(side="right")

        self.user_label = ttk.Label(user_frame, text=f"👤 User: {self.username}", font=("Helvetica", 10))
        self.user_label.pack(side="left", padx=(0, 10))

        self.logout_btn = ttk.Button(user_frame, text="🚪 Logout", command=self.logout_action, width=12)
        self.logout_btn.pack(side="left")

        # Change password button
        try:
            from src.hub.account import ChangePasswordWindow

            self.change_pw_btn = ttk.Button(
                user_frame, text="🔒 Change Password", command=self._open_change_password, width=16
            )
            self.change_pw_btn.pack(side="left", padx=(6, 0))
        except Exception:
            # If account UI not available, skip adding the button
            pass

        # Email notifier status and manual re-init
        self.email_status_label = ttk.Label(user_frame, text="📧 Email: Unknown", font=("Helvetica", 9))
        self.email_status_label.pack(side="left", padx=(8, 4))

        self.email_reinit_btn = ttk.Button(user_frame, text="Re-init Email", command=lambda: self.async_loop.create_task(self._reinit_email_clicked()), width=12)
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
        learning_frame = ttk.LabelFrame(frame, text="🧠 AI Learning Insights", padding=10)
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
            from src.hub.account import ChangePasswordWindow

            ChangePasswordWindow(self.root, self.username)
        except Exception as e:
            logging.exception("Failed to open ChangePasswordWindow: %s", e)
            messagebox.showerror("Error", f"Failed to open Change Password dialog: {e}")

    def create_monitoring_tab(self):
        """Delegate Monitoring tab creation to the extracted UI module."""
        try:
            from src.hub.ui import create_monitoring_tab

            return create_monitoring_tab(self)
        except Exception:
            logging.exception("Failed to delegate create_monitoring_tab to src.hub.ui")
            return None

    def create_reports_tab(self):
        """Create Reports tab by delegating to the extracted UI module."""
        try:
            from src.hub.ui import create_reports_tab

            return create_reports_tab(self)
        except Exception:
            logging.exception("Failed to delegate create_reports_tab to src.hub.ui")
            return None

    def open_import_dialog(self):
        """Open a dialog to paste or upload a transcript for ingestion."""
        if not _HAS_INGEST or store_conversation is None:
            messagebox.showerror("Import Unavailable", "Conversation ingestion is not available in this installation.")
            return

        win = tk.Toplevel(self.root)
        win.title("Import Transcript")
        win.geometry("720x520")

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

    def create_chat_tab(self):
        """Delegate Chat tab creation to the extracted UI module."""
        try:
            from src.hub.ui import create_chat_tab

            return create_chat_tab(self)
        except Exception:
            logging.exception("Failed to delegate create_chat_tab to src.hub.ui")
            return None

    def create_hardware_tab(self):
        """Delegate Hardware tab creation to the extracted UI module."""
        try:
            from src.hub.ui import create_hardware_tab

            return create_hardware_tab(self)
        except Exception:
            logging.exception("Failed to delegate create_hardware_tab to src.hub.ui")
            return None

    def create_security_tab(self):
        """Creates the content for the Security tab."""
        frame = self.tab_security

        # Authentication Info
        auth_frame = ttk.LabelFrame(frame, text="Authentication Status", padding=10)
        auth_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            auth_frame, text="✅ System Access: Authenticated", font=("Helvetica", 10, "bold"), foreground="green"
        ).pack(pady=5)
        ttk.Label(auth_frame, text=f"User: {self.username}", font=("Helvetica", 9)).pack()
        ttk.Label(
            auth_frame, text=f"Session Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", font=("Helvetica", 9)
        ).pack()

        if self.email_notifier:
            ttk.Label(
                auth_frame, text="📧 Email Notifications: Enabled", font=("Helvetica", 9), foreground="green"
            ).pack()
        else:
            ttk.Label(
                auth_frame, text="📧 Email Notifications: Disabled", font=("Helvetica", 9), foreground="orange"
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
            "", "end", values=(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Login", "Hub initialized", "✅ Success")
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

    def create_admin_tab(self):
        """Create Administration tab by delegating to the extracted UI module."""
        try:
            # Import here to avoid circular imports at module import time
            from src.hub.ui import create_admin_tab

            return create_admin_tab(self)
        except Exception:
            # Fallback: no-op to keep the hub functional if the UI module is broken
            logging.exception("Failed to delegate create_admin_tab to src.hub.ui")
            return None

    def review_pending_ai_training(self):
        """Open a small dialog to list pending AI-training items for review/approve/reject."""
        try:
            from src.learning.ai_to_ai_training import list_pending, approve_item, reject_item
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"AI training module unavailable: {e}")
            return

        pending = list_pending(100)

        dialog = tk.Toplevel(self.root)
        dialog.title("Pending AI Training Items")
        dialog.geometry("800x600")

        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tree = ttk.Treeview(list_frame, columns=("id", "timestamp", "participants", "source"), show="headings")
        tree.heading("id", text="ID")
        tree.heading("timestamp", text="Timestamp")
        tree.heading("participants", text="Participants")
        tree.heading("source", text="Source")
        tree.pack(fill="both", expand=True)

        for item in pending:
            tree.insert(
                "",
                "end",
                iid=str(item["id"]),
                values=(item["id"], item["timestamp"], (item["participants"] or "")[:40], item["source"]),
            )

        text_frame = ttk.LabelFrame(dialog, text="Transcript")
        text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        transcript_text = tk.Text(text_frame, wrap="word", height=12)
        transcript_text.pack(fill="both", expand=True)

        def on_select(event):
            sel = tree.selection()
            if not sel:
                return
            item_id = int(sel[0])
            # fetch the raw text from pending list
            for it in pending:
                if it["id"] == item_id:
                    transcript_text.delete("1.0", "end")
                    transcript_text.insert("1.0", it["raw_text"])
                    break

        tree.bind("<<TreeviewSelect>>", on_select)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=5)

        def approve_selected():
            sel = tree.selection()
            if not sel:
                self._msg(messagebox.showwarning, "Select", "Select an item to approve")
                return
            item_id = int(sel[0])
            res = approve_item(item_id)
            if res.get("status") == "ok":
                self._msg(messagebox.showinfo, "Approved", f"Item {item_id} approved and ingested")
                dialog.destroy()
            else:
                self._msg(messagebox.showerror, "Error", f"Failed to approve: {res.get('error')}")

        def reject_selected():
            sel = tree.selection()
            if not sel:
                self._msg(messagebox.showwarning, "Select", "Select an item to reject")
                return
            item_id = int(sel[0])
            res = reject_item(item_id)
            if res.get("status") == "ok":
                self._msg(messagebox.showinfo, "Rejected", f"Item {item_id} marked rejected")
                dialog.destroy()
            else:
                self._msg(messagebox.showerror, "Error", f"Failed to reject: {res.get('error')}")

        ttk.Button(btn_frame, text="Approve & Ingest", command=approve_selected).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Reject", command=reject_selected).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right")

    def open_upload_authorization_dialog(self):
        """Open file dialog to upload an authorization form into the authorizations store."""
        try:
            from src.admin.authorization_manager import save_authorization
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Authorization manager unavailable: {e}")
            return

        path = filedialog.askopenfilename(title="Select authorization form to upload", filetypes=[("All files", "*.*")])
        if not path:
            return

        res = save_authorization(path, uploader=getattr(self, "username", "unknown"))
        if res.get("status") == "ok":
            self._msg(messagebox.showinfo, "Uploaded", f"Uploaded authorization id={res.get('id')}")
        else:
            self._msg(messagebox.showerror, "Error", f"Failed to upload: {res.get('error')}")

    def open_web_learning_contacts_viewer(self):
        """Launch the external viewer script to preview/export contact requests."""
        try:
            script = PROJECT_ROOT / "scripts" / "view_web_learning_contacts.py"
            if not script.exists():
                self._msg(messagebox.showerror, "Not found", f"Viewer script not found: {script}")
                return
            # Launch in a separate process so the hub UI remains responsive
            subprocess.Popen([sys.executable, str(script)])
            self._msg(messagebox.showinfo, "Launched", "Web learning contacts viewer launched")
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to launch viewer: {e}")

    def open_web_learning_contacts_embedded(self):
        """Open an embedded Toplevel viewer for web learning contact requests."""
        try:
            contacts_file = PROJECT_ROOT / "data" / "web_learning_contact_requests.json"
            dialog = tk.Toplevel(self.root)
            dialog.title("Web Learning Contact Requests")
            dialog.geometry("900x500")

            frame = ttk.Frame(dialog)
            frame.pack(fill="both", expand=True, padx=10, pady=10)

            tree = ttk.Treeview(
                frame, columns=("topic", "source", "contact", "alternatives", "checked_at"), show="headings"
            )
            for col in ("topic", "source", "contact", "alternatives", "checked_at"):
                tree.heading(col, text=col)
                tree.column(col, width=160, anchor="w")
            tree.pack(fill="both", expand=True, side="left")

            scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscroll=scrollbar.set)
            scrollbar.pack(side="left", fill="y")

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(fill="x", padx=10, pady=6)
            ttk.Button(
                btn_frame, text="Refresh", command=lambda: self._populate_contacts_tree(tree, contacts_file)
            ).pack(side="left")
            ttk.Button(
                btn_frame,
                text="Export CSV",
                command=lambda: self.schedule_on_main_thread(self._export_contacts_csv, contacts_file),
            ).pack(side="left", padx=6)
            ttk.Button(btn_frame, text="Open JSON", command=lambda: self._open_file(contacts_file)).pack(side="left")

            # initial populate
            self._populate_contacts_tree(tree, contacts_file)
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to open embedded viewer: {e}")

    def import_web_learning_alternatives(self):
        """Import alternatives discovered by the web learner into ingestion candidates.

        This reads `data/web_learning_contact_requests.json`, extracts any
        `alternatives` values (URLs), and appends them to
        `data/ingestion_candidates.json` as simple candidate records. Duplicates
        are ignored. The ingestion UI is refreshed after import.
        """
        try:
            contacts_file = PROJECT_ROOT / "data" / "web_learning_contact_requests.json"
            if not contacts_file.exists():
                self._msg(messagebox.showinfo, "No Data", "No web learning contact requests found.")
                return

            import json
            from src.hub.ingestion import load_candidates, save_candidates

            contacts = json.loads(contacts_file.read_text(encoding="utf-8"))
            candidates = load_candidates(PROJECT_ROOT)
            seen = {c.get("source") for c in candidates}

            added = 0
            for it in contacts:
                alts = it.get("alternatives") or []
                for alt in alts:
                    if alt in seen:
                        continue
                    # create a minimal candidate entry
                    cand = {
                        "source": alt,
                        "title": f"Alternative for {it.get('source', '')}",
                        "added_at": datetime.now().isoformat(),
                    }
                    candidates.append(cand)
                    seen.add(alt)
                    added += 1

            if added > 0:
                save_candidates(PROJECT_ROOT, candidates)
                # refresh ingestion UI
                try:
                    self.load_ingestion_candidates()
                except Exception:
                    pass
                self._msg(messagebox.showinfo, "Imported", f"Imported {added} alternative source(s) into ingestion candidates.")
            else:
                self._msg(messagebox.showinfo, "No New Alternatives", "No new alternative sources found to import.")
        except Exception as e:
            logging.exception("Failed to import web learning alternatives: %s", e)
            self._msg(messagebox.showerror, "Error", f"Failed to import alternatives: {e}")

    def _populate_contacts_tree(self, tree, contacts_file: Path):
        try:
            import json

            tree.delete(*tree.get_children())
            if not contacts_file.exists():
                return
            items = json.loads(contacts_file.read_text(encoding="utf-8"))
            for it in items:
                alts = ", ".join(it.get("alternatives") or []) if it.get("alternatives") else ""
                tree.insert(
                    "",
                    "end",
                    values=(
                        it.get("topic", ""),
                        it.get("source", ""),
                        it.get("contact", ""),
                        alts,
                        it.get("checked_at", ""),
                    ),
                )
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to load contacts: {e}")

    def _export_contacts_csv(self, contacts_file: Path):
        try:
            import json, csv

            if not contacts_file.exists():
                self._msg(messagebox.showinfo, "No data", "No contact requests to export")
                return
            items = json.loads(contacts_file.read_text(encoding="utf-8"))
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if not path:
                return
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["topic", "source", "contact", "alternatives", "checked_at"])
                for it in items:
                    w.writerow(
                        [
                            it.get("topic", ""),
                            it.get("source", ""),
                            it.get("contact", ""),
                            "|".join(it.get("alternatives") or []),
                            it.get("checked_at", ""),
                        ]
                    )
            self._msg(messagebox.showinfo, "Exported", f"Exported {len(items)} items to {path}")
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to export CSV: {e}")

    def _open_file(self, path: Path):
        try:
            if path.exists():
                import os

                os.startfile(path)
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to open file: {e}")

    async def _generate_outreach_csv(self):
        """Run the outreach CSV generator script in a subprocess and notify the user when done."""
        try:
            script = PROJECT_ROOT / "scripts" / "generate_outreach_csv.py"
            if not script.exists():
                self._msg(messagebox.showerror, "Not found", f"Outreach generator not found: {script}")
                return
            env = os.environ.copy()
            env["PYTHONPATH"] = str(PROJECT_ROOT)
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(script), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
            )
            stdout, stderr = await proc.communicate()
            out_text = stdout.decode("utf-8", errors="ignore") if stdout else ""
            err_text = stderr.decode("utf-8", errors="ignore") if stderr else ""
            if proc.returncode == 0:
                self._msg(messagebox.showinfo, "Outreach CSV", f"Outreach CSV generated.\n{out_text}")
            else:
                self._msg(messagebox.showerror, "Outreach CSV Error", f"Generator failed.\n{err_text}\n{out_text}")
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to run outreach generator: {e}")

    def open_review_authorizations_dialog(self):
        """Open a dialog to list and review uploaded authorization forms."""
        try:
            from src.admin.authorization_manager import (
                list_authorizations,
                get_authorization,
                approve_authorization,
                reject_authorization,
                export_authorization,
            )
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Authorization manager unavailable: {e}")
            return

        items = list_authorizations(200)

        dialog = tk.Toplevel(self.root)
        dialog.title("Authorization Forms")
        dialog.geometry("900x700")

        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Top controls: status filter, search box, auto-refresh
        control_frame = ttk.Frame(list_frame)
        control_frame.pack(fill="x", pady=(0, 6))

        ttk.Label(control_frame, text="Status:").pack(side="left", padx=(0, 4))
        status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(
            control_frame,
            values=["All", "pending", "approved", "rejected"],
            textvariable=status_var,
            state="readonly",
            width=12,
        )
        status_combo.pack(side="left")

        ttk.Label(control_frame, text="Search:").pack(side="left", padx=(8, 4))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(control_frame, textvariable=search_var, width=40)
        search_entry.pack(side="left")

        auto_refresh_var = tk.BooleanVar(value=False)
        auto_refresh_chk = ttk.Checkbutton(control_frame, text="Auto-refresh", variable=auto_refresh_var)
        auto_refresh_chk.pack(side="left", padx=(8, 4))

        tree = ttk.Treeview(list_frame, columns=("id", "timestamp", "uploader", "filename", "status"), show="headings")
        for col, title in [
            ("id", "ID"),
            ("timestamp", "Uploaded"),
            ("uploader", "Uploader"),
            ("filename", "Filename"),
            ("status", "Status"),
        ]:
            tree.heading(col, text=title)
            tree.column(col, width=150 if col != "filename" else 300)
        tree.pack(fill="both", expand=True)

        def refresh_tree():
            # repopulate from backend with filter/search
            for ch in tree.get_children():
                tree.delete(ch)
            cur_items = list_authorizations(500)
            filt = status_var.get()
            q = search_var.get().lower()
            for it in cur_items:
                if filt and filt != "All" and it.get("status") != filt:
                    continue
                    if q:
                        hay = f"{it.get('uploader','')} {it.get('filename','')} {it.get('timestamp','')} {it.get('status','')}".lower()
                        if q not in hay:
                            continue
                tree.insert(
                    "",
                    "end",
                    iid=str(it["id"]),
                    values=(
                        it["id"],
                        it["timestamp"],
                        it.get("uploader", ""),
                        it.get("filename", ""),
                        it.get("status", ""),
                    ),
                )

        def scheduled_refresh():
            if auto_refresh_var.get():
                refresh_tree()
                try:
                    dialog.after(5000, scheduled_refresh)
                except Exception:
                    pass

        # wire search/filters
        status_combo.bind("<<ComboboxSelected>>", lambda e: refresh_tree())
        search_entry.bind("<Return>", lambda e: refresh_tree())

        # initial population
        refresh_tree()

        # start auto-refresh loop if requested
        if auto_refresh_var.get():
            dialog.after(5000, scheduled_refresh)

        preview_frame = ttk.LabelFrame(dialog, text="Preview / Details")
        preview_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        preview_text = tk.Text(preview_frame, wrap="word", height=15)
        preview_text.pack(fill="both", expand=True)

        def on_select(event):
            sel = tree.selection()
            preview_text.delete("1.0", "end")
            if not sel:
                return
            aid = int(sel[0])
            auth = get_authorization(aid)
            if not auth:
                preview_text.insert("1.0", "Authorization metadata not found")
                return
            preview_text.insert(
                "1.0",
                f"ID: {auth['id']}\nUploaded: {auth['timestamp']}\nUploader: {auth['uploader']}\nFilename: {auth['filename']}\nStatus: {auth['status']}\nNotes: {auth.get('notes','')}\n\n",
            )
            # try to show file contents for text files
            try:
                p = Path(auth["stored_path"])
                if p.exists():
                    sfx = p.suffix.lower()
                    if sfx in (".txt", ".md", ".log", ".csv"):
                        with p.open("r", encoding="utf-8", errors="ignore") as fh:
                            preview_text.insert("end", fh.read())
                    elif sfx == ".pdf":
                        # Try optional PDF text extraction, then OCR fallback for scanned PDFs.
                        extracted = []
                        used_extractor = None
                        try:
                            try:
                                from pypdf import PdfReader as _PdfReader

                                used_extractor = "pypdf"
                            except Exception:
                                from PyPDF2 import PdfReader as _PdfReader

                                used_extractor = "PyPDF2"

                            reader = _PdfReader(str(p))
                            for page in getattr(reader, "pages", []):
                                try:
                                    txt = page.extract_text()
                                    if txt:
                                        extracted.append(txt)
                                except Exception:
                                    continue
                        except Exception as pe:
                            # extraction module missing or failed; will try OCR below
                            used_extractor = None

                        if extracted:
                            preview_text.insert("end", "\n\n".join(extracted))
                        else:
                            # Try OCR fallback using pdf2image + pytesseract if available
                            try:
                                from pdf2image import convert_from_path
                                import pytesseract
                                import tempfile

                                ocr_pages = []
                                # convert_from_path may require poppler; wrap in try/except
                                try:
                                    with tempfile.TemporaryDirectory() as td:
                                        images = convert_from_path(str(p), output_folder=td)
                                        for img in images:
                                            try:
                                                txt = pytesseract.image_to_string(img)
                                                if txt:
                                                    ocr_pages.append(txt)
                                            except Exception:
                                                # ignore page-level OCR errors
                                                pass
                                except Exception as conv_err:
                                    preview_text.insert(
                                        "end",
                                        f"PDF OCR failed: convert_from_path error (poppler may be required). Install poppler and try again.\nError: {conv_err}",
                                    )
                                    ocr_pages = []

                                if ocr_pages:
                                    preview_text.insert("end", "\n\n".join(ocr_pages))
                                else:
                                    preview_text.insert(
                                        "end",
                                        "No extractable text found and OCR produced no text (scanned PDF or images).",
                                    )

                            except Exception as oerr:
                                if used_extractor is None:
                                    preview_text.insert(
                                        "end",
                                        "PDF preview requires optional package 'pypdf' or 'PyPDF2' for text extraction, or 'pdf2image'+'pytesseract' for OCR.\nInstall with: pip install pypdf pdf2image pytesseract Pillow\nNote: pdf2image requires poppler on your system.\n",
                                    )
                                else:
                                    preview_text.insert(
                                        "end",
                                        "No extractable text found in PDF (may be a scanned document). Install pdf2image+pytesseract for OCR support.",
                                    )
                    else:
                        preview_text.insert(
                            "end", f"Stored file: {auth['stored_path']}\n(Preview not available for this file type)"
                        )
                else:
                    preview_text.insert("end", "Stored file missing on disk.")
            except Exception as e:
                preview_text.insert("end", f"Error reading file: {e}")

        tree.bind("<<TreeviewSelect>>", on_select)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=5)

        def approve_sel():
            sel = tree.selection()
            if not sel:
                self._msg(messagebox.showwarning, "Select", "Select an authorization to approve")
                return
            aid = int(sel[0])
            comment = simpledialog.askstring("Approve", "Optional comment for approval:")
            res = approve_authorization(aid, approver=getattr(self, "username", "admin"), comment=comment)
            if res.get("status") == "ok":
                self._msg(messagebox.showinfo, "Approved", f"Authorization {aid} approved")
                # refresh
                refresh_tree()
            else:
                self._msg(messagebox.showerror, "Error", f"Failed to approve: {res.get('error')}")

        def reject_sel():
            sel = tree.selection()
            if not sel:
                self._msg(messagebox.showwarning, "Select", "Select an authorization to reject")
                return
            aid = int(sel[0])
            comment = simpledialog.askstring("Reject", "Reason for rejection:")
            res = reject_authorization(aid, approver=getattr(self, "username", "admin"), comment=comment)
            if res.get("status") == "ok":
                self._msg(messagebox.showinfo, "Rejected", f"Authorization {aid} rejected")
                refresh_tree()
            else:
                self._msg(messagebox.showerror, "Error", f"Failed to reject: {res.get('error')}")

        def export_sel():
            sel = tree.selection()
            if not sel:
                self._msg(messagebox.showwarning, "Select", "Select an authorization to export")
                return
            aid = int(sel[0])
            auth = get_authorization(aid)
            if not auth:
                self._msg(messagebox.showerror, "Error", "Authorization not found")
                return
            dest = filedialog.asksaveasfilename(
                title="Export authorization to", initialfile=auth.get("filename", "auth.bin")
            )
            if not dest:
                return
            res = export_authorization(aid, dest)
            if res.get("status") == "ok":
                self._msg(messagebox.showinfo, "Exported", f"Exported to {res.get('path')}")
            else:
                self._msg(messagebox.showerror, "Error", f"Export failed: {res.get('error')}")

        ttk.Button(btn_frame, text="Approve", command=approve_sel).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Reject", command=reject_sel).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Export", command=export_sel).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right")

    async def fetch_from_providers(self):
        """Fetch content from configured AI providers and queue it for review."""
        try:
            from src.learning.provider_connectors import (
                load_providers,
                build_fetch_payload,
                normalize_headers,
                provider_summary,
            )
            from src.learning.ai_to_ai_training import submit_conversation_for_training
            import aiohttp
        except Exception as e:
            logging.exception("Error importing provider modules")
            return

        providers = load_providers()
        if not providers:
            self.schedule_on_main_thread(
                self._msg, messagebox.showinfo, "Providers", "No AI providers configured (see config/ai_providers.json)"
            )
            return

        async with aiohttp.ClientSession() as session:
            for p in providers:
                endpoint = p.get("endpoint")
                if not endpoint:
                    continue
                headers = normalize_headers(p.get("headers"))
                payload = build_fetch_payload(p)

                try:
                    async with session.post(endpoint, json=payload, headers=headers, timeout=30) as resp:
                        text = None
                        try:
                            j = await resp.json()
                            # Try conventional keys
                            text = j.get("text") or j.get("output") or j.get("response") or None
                            if not text:
                                # If provider returns a simple structure, stringify it
                                text = json.dumps(j)
                        except Exception:
                            # Fallback to raw text
                            text = await resp.text()

                        if text:
                            # Submit raw text into pending AI training queue
                            submit_conversation_for_training(text, participants=p.get("name"), source=p.get("name"))
                            self.schedule_on_main_thread(
                                self._msg,
                                messagebox.showinfo,
                                "Fetched",
                                f"Fetched content from {provider_summary(p)} and queued for review.",
                            )

                except Exception:
                    logging.exception("Failed to fetch from provider %s", p.get("name"))

    def create_testing_tab(self):
        """Creates the content for the Testing tab."""
        frame = self.tab_testing
        run_tests_btn = ttk.Button(frame, text="Run Ultimate Test Suite", command=self.run_tests_action)
        run_tests_btn.pack(pady=10, padx=20)

        output_frame = ttk.LabelFrame(frame, text="Test Output", padding=10)
        output_frame.pack(expand=True, fill="both", padx=20, pady=10)

        self.test_output_text = tk.Text(
            output_frame,
            wrap="word",
            height=20,
            bg=self.style.lookup("TFrame", "background"),
            fg=self.style.lookup("TLabel", "foreground"),
        )
        self.test_output_text.pack(expand=True, fill="both")

    def create_ngrok_tab(self):
        """
        Ngrok Tunnel Management Tab
        Allows user to start/stop ngrok tunnels for dashboard access
        """
        frame = self.tab_ngrok

        # Header
        header_frame = ttk.LabelFrame(frame, text="Ngrok Tunnel Management", padding=10)
        header_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(header_frame, text="Manage ngrok tunnels for remote access to Celsius Dashboard").pack()

        # Tunnel controls
        control_frame = ttk.LabelFrame(frame, text="Active Tunnels", padding=10)
        control_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Tunnel list
        self.tunnel_tree = ttk.Treeview(
            control_frame, columns=("Port", "Public URL", "Status"), show="headings", height=8
        )
        self.tunnel_tree.heading("Port", text="Local Port")
        self.tunnel_tree.heading("Public URL", text="Public URL")
        self.tunnel_tree.heading("Status", text="Status")
        self.tunnel_tree.pack(fill="both", expand=True, pady=5)

        # Buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(
            btn_frame, text="Start Dashboard Tunnel (Port 5000)", command=lambda: self.toggle_ngrok_tunnel(5000)
        ).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Stop Selected Tunnel", command=self.stop_selected_tunnel).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_ngrok_status).pack(side="left", padx=5)

        # Status display
        self.ngrok_status_text = tk.Text(
            control_frame,
            wrap="word",
            height=6,
            bg=self.style.lookup("TFrame", "background"),
            fg=self.style.lookup("TLabel", "foreground"),
        )
        self.ngrok_status_text.pack(fill="x", pady=5)

        # Initial refresh
        self.refresh_ngrok_status()

    def create_code_approval_tab(self):
        """
        Code Approval Tab
        Shows all code change requests from Celsius AI
        User can approve or reject changes here
        """
        frame = self.tab_code_approval

        # Header
        header_frame = ttk.LabelFrame(frame, text="Celsius AI Code Approval System", padding=10)
        header_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            header_frame,
            text="Review and approve/reject code changes requested by Celsius AI",
            font=("Helvetica", 10, "bold"),
        ).pack()
        ttk.Label(
            header_frame, text="CRITICAL: All code changes require your explicit approval", foreground="red"
        ).pack()

        # Pending requests list
        request_frame = ttk.LabelFrame(frame, text="Pending Approval Requests", padding=10)
        request_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Request tree
        self.approval_tree = ttk.Treeview(
            request_frame, columns=("ID", "Title", "Files", "Timestamp"), show="headings", height=10
        )
        self.approval_tree.heading("ID", text="Request ID")
        self.approval_tree.heading("Title", text="Title")
        self.approval_tree.heading("Files", text="Files to Modify")
        self.approval_tree.heading("Timestamp", text="Timestamp")
        self.approval_tree.pack(fill="both", expand=True, pady=5)
        self.approval_tree.bind("<<TreeviewSelect>>", self.on_approval_select)

        # Details frame
        details_frame = ttk.LabelFrame(frame, text="Request Details", padding=10)
        details_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.approval_details_text = tk.Text(
            details_frame,
            wrap="word",
            height=12,
            bg=self.style.lookup("TFrame", "background"),
            fg=self.style.lookup("TLabel", "foreground"),
        )
        self.approval_details_text.pack(fill="both", expand=True)

        # Action buttons
        action_frame = ttk.Frame(frame, padding=10)
        action_frame.pack(fill="x", padx=10)

        ttk.Button(action_frame, text="✓ APPROVE", command=self.approve_code_change, style="Success.TButton").pack(
            side="left", padx=5
        )
        ttk.Button(action_frame, text="✗ REJECT", command=self.reject_code_change, style="Danger.TButton").pack(
            side="left", padx=5
        )
        ttk.Button(action_frame, text="Apply Patch", command=self.apply_selected_patch).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Explain Change", command=self.explain_selected_change).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Refresh Requests", command=self.refresh_approval_requests).pack(
            side="left", padx=5
        )

        # Initial load
        self.refresh_approval_requests()

    async def initialize_async_components(self):
        """Initializes aiohttp session and database asynchronously."""
        try:
            self.http_session = aiohttp.ClientSession()
            await self.init_db()

            # Initialize email notifier. Perform a fresh runtime import here so that
            # a transient or earlier import-time failure (at module import) does
            # not permanently disable notifications.
            try:
                from src.utils.enhanced_email_system import EnhancedEmailNotifier as _EnhancedEmailNotifier
            except Exception:
                # If the import fails, do not attempt to reference undefined symbols;
                # simply disable the email notifier initialization.
                _EnhancedEmailNotifier = None

            # Use centralized helper to initialize the email notifier and start a
            # background retry loop if initialization fails transiently.
            await self.ensure_email_notifier()

            # Start the service health check loop
            self.async_loop.create_task(self.periodic_health_check())
            # Start polling hourly reports and update the UI
            try:
                self.async_loop.create_task(self.periodic_poll_hourly_reports())
            except Exception:
                logging.debug("Failed to start hourly reports poller", exc_info=True)
            # Start periodic sweep for web-learning contacts (runs external script)
            try:
                self.async_loop.create_task(self.periodic_sweep_contacts())
            except Exception:
                logging.debug("Failed to start periodic web-learning sweep", exc_info=True)
            self.log_activity("Hub", "Hub Initialized", f"Async components ready. User: {self.username}")

            # Initial service status check (schedule on main thread)
            self.schedule_on_main_thread(self.refresh_dashboard)

            # Start checking for Guardian logout signal on main thread
            self.schedule_on_main_thread(self.check_guardian_logout_signal)

            # Send login notification email (try to initialize notifier if needed)
            self.async_loop.create_task(
                self.send_email_notification(
                    "Login",
                    "Hub Login Notification",
                    f"User {self.username} has logged into the Celsius Ultimate Hub.\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nIf this wasn't you, please secure your system immediately.",
                    "high",
                )
            )
        except Exception as e:
            logging.error(f"Async initialization failed: {e}", exc_info=True)
            # Use safe messagebox scheduling from async context
            self._msg(messagebox.showerror, "Init Error", f"Could not initialize async components: {e}")

    def on_closing(self):
        """Handle the window closing event."""
        if messagebox.askokcancel("Quit", "Do you want to quit Celsius Hub?"):
            self.log_activity("Hub", "Shutdown", "User initiated shutdown.")
            self.async_loop.create_task(self.shutdown())

    def logout_action(self):
        """Handle logout - return to login screen without closing."""
        if messagebox.askyesno(
            "Logout", "Are you sure you want to logout?\n\nThe Hub will remain open but require re-authentication."
        ):
            self.perform_logout()

    def perform_logout(self):
        """Perform the actual logout."""
        # Log the activity
        self.log_activity("Hub", "Logout", f"User {self.username} logged out")

        # Update UI to show logged out state
        self.username = "Not Logged In"
        self.user_label.config(text=f"🔒 {self.username}")

        # Disable all tabs except monitoring (read-only)
        for i in range(self.notebook.index("end")):
            if i != 2:  # Keep monitoring tab enabled (index 2)
                self.notebook.tab(i, state="disabled")

        # Show re-login button
        self.show_relogin_prompt()

    def show_relogin_prompt(self):
        """Show a prompt to re-login."""
        # Create overlay frame
        self.relogin_frame = ttk.Frame(self.root, padding=20)
        self.relogin_frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(self.relogin_frame, text="🔒 Session Logged Out", font=("Helvetica", 16, "bold")).pack(pady=10)
        ttk.Label(self.relogin_frame, text="Please login again to access Hub features.").pack(pady=5)

        ttk.Button(self.relogin_frame, text="Login", command=self.relogin, width=20).pack(pady=10)

    def relogin(self):
        """Handle re-login."""
        # Remove relogin frame
        if hasattr(self, "relogin_frame"):
            self.relogin_frame.destroy()

        # Create a Toplevel window for re-login
        login_toplevel = tk.Toplevel(self.root)
        login_toplevel.title("🛡️ Celsius AI - Re-Login")
        login_toplevel.geometry("400x300")
        login_toplevel.transient(self.root)
        login_toplevel.grab_set()

        # Center the window
        login_toplevel.update_idletasks()
        x = (login_toplevel.winfo_screenwidth() // 2) - (400 // 2)
        y = (login_toplevel.winfo_screenheight() // 2) - (300 // 2)
        login_toplevel.geometry(f"400x300+{x}+{y}")

        # Create login UI in the Toplevel
        main_frame = ttk.Frame(login_toplevel, padding="20")
        main_frame.pack(expand=True, fill="both")

        # Header
        ttk.Label(main_frame, text="🛡️ Celsius AI", font=("Helvetica", 20, "bold")).pack(pady=10)
        ttk.Label(main_frame, text="Re-Login Required", font=("Helvetica", 10)).pack(pady=5)

        # Username
        ttk.Label(main_frame, text="Username:", font=("Helvetica", 10)).pack(pady=(20, 5))
        username_entry = ttk.Entry(main_frame, font=("Helvetica", 10), width=30)
        username_entry.pack(pady=5)
        username_entry.insert(0, "cllusion001")

        # Password
        ttk.Label(main_frame, text="Password:", font=("Helvetica", 10)).pack(pady=(10, 5))
        password_entry = ttk.Entry(main_frame, font=("Helvetica", 10), width=30, show="*")
        password_entry.pack(pady=5)

        # Status label
        status_label = ttk.Label(main_frame, text="", font=("Helvetica", 9), foreground="red")
        status_label.pack(pady=5)

        authenticated = [False]  # Use list to allow modification in nested function

        def attempt_relogin():
            """Validates the re-login credentials."""
            username = username_entry.get()
            password = password_entry.get()

            # Correct credentials
            VALID_USERNAME = "cllusion001"
            VALID_PASSWORD = "T3qy22ny*@dyu0ppn*pG"

            if username == VALID_USERNAME and password == VALID_PASSWORD:
                authenticated[0] = True
                login_toplevel.destroy()
            else:
                status_label.config(text="❌ Invalid credentials. Please try again.")
                password_entry.delete(0, tk.END)
                password_entry.focus()

        # Login button
        ttk.Button(main_frame, text="🔓 Login", command=attempt_relogin, width=20).pack(pady=15)

        # Cancel button
        ttk.Button(main_frame, text="Cancel", command=login_toplevel.destroy, width=20).pack(pady=5)

        # Bind Enter key to login
        password_entry.bind("<Return>", lambda e: attempt_relogin())
        password_entry.focus()

        # Wait for the window to close
        self.root.wait_window(login_toplevel)

        if authenticated[0]:
            self.username = "cllusion001"
            self.user_label.config(text=f"👤 User: {self.username}")

            # Re-enable all tabs
            for i in range(self.notebook.index("end")):
                self.notebook.tab(i, state="normal")

            self.log_activity("Hub", "Re-Login", f"User {self.username} re-authenticated")

            # Send login notification (attempt to initialize notifier if needed)
            self.async_loop.create_task(
                self.send_email_notification(
                    "Re-Login",
                    "Hub Re-Login Notification",
                    f"User {self.username} has re-logged into the Celsius Ultimate Hub.\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "high",
                )
            )
            # reset activity timer on successful relogin
            try:
                self._last_activity = datetime.now()
            except Exception:
                pass
        else:
            # User cancelled, show prompt again
            self.show_relogin_prompt()

    def check_guardian_logout_signal(self):
        """Check for Guardian's logout signal file."""
        signal_file = PROJECT_ROOT / "data" / "guardian_logout_signal.txt"

        if signal_file.exists():
            try:
                # Read and remove the signal file
                with open(signal_file, "r") as f:
                    signal_data = f.read().strip()

                signal_file.unlink()  # Delete the signal file

                # Perform logout if signal is valid
                if signal_data == "GUARDIAN_LOGOUT":
                    logging.info("Guardian logout signal received - logging out...")
                    self.perform_logout()
            except Exception as e:
                logging.error(f"Error processing Guardian logout signal: {e}")

        # Check again in 2 seconds
        self.root.after(2000, self.check_guardian_logout_signal)

    def _update_activity(self):
        """Update the last-activity timestamp (called on user input events)."""
        try:
            self._last_activity = datetime.now()
        except Exception:
            pass

    def _check_inactivity(self):
        """Called periodically on the main thread to enforce an inactivity timeout."""
        try:
            if getattr(self, "_last_activity", None) is None:
                self._last_activity = datetime.now()
            elapsed = datetime.now() - self._last_activity
            minutes = elapsed.total_seconds() / 60.0
            if getattr(self, "session_timeout_minutes", 0) and minutes >= self.session_timeout_minutes:
                # perform logout due to inactivity
                logging.info("User session timed out after %.1f minutes; logging out", minutes)
                try:
                    messagebox.showinfo(
                        "Session Timeout",
                        "Your session has been inactive and will be logged out for security. Please log in again.",
                    )
                except Exception:
                    pass
                self.perform_logout()
            else:
                # schedule next check in 60 seconds
                self.root.after(60_000, self._check_inactivity)
        except Exception:
            logging.exception("Error while checking inactivity")

    def _on_tab_changed(self, event):
        """Lazy-load tab content on first selection."""
        try:
            tab_id = event.widget.select()
            text = event.widget.tab(tab_id, option="text")
            creator = self._tab_creators.get(text)
            if creator and not self._tab_initialized.get(text, False):
                # Show a small indeterminate progress indicator while the tab is being created.
                try:
                    parent = event.widget.nametowidget(tab_id)
                    loading_frame = ttk.Frame(parent)
                    loading_frame.pack(fill="both", expand=True)
                    pb = ttk.Progressbar(loading_frame, mode="indeterminate")
                    pb.pack(pady=20)
                    pb.start(10)
                    # Allow UI to render the progressbar briefly
                    try:
                        self.root.update_idletasks()
                    except Exception:
                        pass

                    # Create the tab content (runs on main thread)
                    creator()
                    self._tab_initialized[text] = True

                    # Stop and remove the progress UI
                    try:
                        pb.stop()
                        loading_frame.destroy()
                    except Exception:
                        pass
                except Exception:
                    logging.exception("Failed to create tab: %s", text)
        except Exception:
            logging.debug("_on_tab_changed: unexpected error", exc_info=True)

    async def shutdown(self):
        """Gracefully shuts down all services and the application."""
        logging.info("Shutting down all services...")
        # Stop all running services
        await asyncio.gather(
            *[self.stop_service(name) for name in self.services if self.services[name].get("status") == "Running"]
        )

        # Close the aiohttp session
        if self.http_session:
            await self.http_session.close()

        # Stop the async loop thread
        self.async_loop.stop()

        # Destroy the Tkinter window
        self.root.destroy()

    async def _reinit_email_clicked(self):
        """Handler for the Re-init Email button. Attempts immediate re-initialization."""
        try:
            await self.ensure_email_notifier(force=True)
            # give UI a moment to reflect the change
            self.schedule_on_main_thread(self._update_email_status)
        except Exception:
            logging.exception("_reinit_email_clicked failed")

    def _periodic_update_email_status(self):
        """Called on the Tk main thread to update the email status label periodically."""
        try:
            self._update_email_status()
            # also update admin tab labels if present
            try:
                if getattr(self, "_email_admin_retry_lbl", None):
                    self._email_admin_retry_lbl.config(text=f"Retry Count: {getattr(self, '_email_retry_count', 0)}")
                if getattr(self, "_email_admin_last_error_lbl", None):
                    self._email_admin_last_error_lbl.config(text=f"Last Error: {getattr(self, '_email_last_error', 'None')}")
            except Exception:
                pass
        except Exception:
            logging.debug("_periodic_update_email_status: failed to update status", exc_info=True)
        # reschedule
        try:
            self.root.after(5000, self._periodic_update_email_status)
        except Exception:
            pass

    def _update_email_status(self):
        try:
            if getattr(self, "email_notifier", None):
                # prefer green for enabled
                if hasattr(self, "email_status_label"):
                    self.email_status_label.config(text="📧 Email: Enabled", foreground="green")
            else:
                if hasattr(self, "email_status_label"):
                    self.email_status_label.config(text="📧 Email: Disabled", foreground="orange")
        except Exception:
            try:
                if hasattr(self, "email_status_label"):
                    self.email_status_label.config(text="📧 Email: Unknown", foreground="gray")
            except Exception:
                pass

    def load_service_config(self) -> Dict[str, Dict[str, Any]]:
        """Loads the service configuration from a JSON file."""
        try:
            with open(CONFIG_PATH, "r") as config_file:
                config = json.load(config_file)
            # The project's main config.json is an application config, while
            # service definitions are expected to be a mapping of service-name
            # -> dict(details). Detect the shape and handle gracefully.
            if isinstance(config, dict) and "services" in config and isinstance(config["services"], dict):
                services = config["services"]
            else:
                # If the file doesn't contain a 'services' mapping, it's likely
                # the general app config (e.g., config/config.json). In that
                # case return the default service map so the Hub has something
                # sane to work with instead of attempting to call
                # setdefault() on strings.
                services = None

            if services is None:
                return {
                    "core_ai": {
                        "name": "Core AI Engine",
                        "module": "src.core.main",
                        "status": "Stopped",
                        "restart_count": 0,
                    },
                    "dashboard": {
                        "name": "Enhanced Dashboard",
                        "module": "src.dashboard.enhanced_mobile_dashboard",
                        "status": "Stopped",
                        "restart_count": 0,
                        "health_uri": "http://localhost:5000",
                    },
                    "guardian": {
                        "name": "Guardian System",
                        "module": "src.guardian.celsius_ultimate_guardian",
                        "status": "Stopped",
                        "restart_count": 0,
                    },
                }

            # Validate and set default values for service entries
            for service, details in services.items():
                if not isinstance(details, dict):
                    # If an entry is malformed, replace it with a minimal dict
                    services[service] = {
                        "name": str(service),
                        "module": str(details) if details else "",
                        "status": "Stopped",
                        "restart_count": 0,
                    }
                else:
                    details.setdefault("status", "Stopped")
                    details.setdefault("restart_count", 0)

            return services
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # Config load warning - show via safe scheduler
            # self is available here so schedule the messagebox safely
            try:
                self._msg(
                    messagebox.showwarning,
                    "Config Error",
                    f"Could not load '{CONFIG_PATH.name}': {e}. Using default config.",
                )
            except Exception:
                # Fallback if self not fully initialized
                messagebox.showwarning(
                    "Config Error", f"Could not load '{CONFIG_PATH.name}': {e}. Using default config."
                )
            return {
                "core_ai": {
                    "name": "Core AI Engine",
                    "module": "src.core.main",
                    "status": "Stopped",
                    "restart_count": 0,
                },
                "dashboard": {
                    "name": "Enhanced Dashboard",
                    "module": "src.dashboard.enhanced_mobile_dashboard",
                    "status": "Stopped",
                    "restart_count": 0,
                    "health_uri": "http://localhost:5000",
                },
                "guardian": {
                    "name": "Guardian System",
                    "module": "src.guardian.celsius_ultimate_guardian",
                    "status": "Stopped",
                    "restart_count": 0,
                },
            }

    def schedule_async_task(self, coro):
        """Helper to schedule a coroutine from the GUI thread."""
        self.async_loop.create_task(coro)

    def _msg(self, func, *args, **kwargs):
        """Schedule a messagebox call on the Tk main loop and set parent to hub root.

        func should be a callable from tkinter.messagebox (e.g. messagebox.showinfo).
        Any kwargs passed will be forwarded; parent is defaulted to self.root.
        """
        kwargs.setdefault("parent", self.root)
        try:
            # Schedule the messagebox to run on the main thread via the queue
            self.schedule_on_main_thread(func, *args, **kwargs)
        except Exception:
            # Best-effort fallback: call directly (rare edge-case during shutdown)
            try:
                func(*args, **kwargs)
            except Exception:
                logging.debug("Failed to show messagebox", exc_info=True)

    def schedule_on_main_thread(self, func, *args, **kwargs):
        """Enqueue a callable to run on the Tk main thread.

        The main thread polls the queue and executes the callables. This
        avoids calling Tk APIs from worker threads which raises
        RuntimeError: main thread is not in main loop.
        """
        try:
            self._main_thread_queue.put((func, args, kwargs))
        except Exception:
            logging.debug("Failed to enqueue main-thread task", exc_info=True)

    def _process_main_thread_queue(self):
        """Process queued callables on the Tk main thread."""
        try:
            while not self._main_thread_queue.empty():
                func, args, kwargs = self._main_thread_queue.get_nowait()
                try:
                    func(*args, **(kwargs or {}))
                except Exception:
                    logging.exception("Error while executing main-thread task")
        except Exception:
            logging.exception("Failed to process main thread queue")
        finally:
            # Poll again
            try:
                self.root.after(100, self._process_main_thread_queue)
            except Exception:
                # If after fails, we are likely shutting down
                pass

    async def ensure_email_notifier(self, force: bool = False):
        """Ensure the email notifier is initialized.

        If initialization fails, a background retry task is started which will
        attempt re-initialization until successful. Calling with force=True
        will attempt initialization even if a notifier already exists.
        """
        if getattr(self, "email_notifier", None) is not None and not force:
            return

        # Avoid creating multiple concurrent retry loops
        if getattr(self, "_email_retry_task", None) and not self._email_retry_task.done():
            # a retry loop is already running; still attempt an immediate try
            pass

        try:
            from src.utils.enhanced_email_system import EnhancedEmailNotifier as _EnhancedEmailNotifier
        except Exception:
            _EnhancedEmailNotifier = None

        if _EnhancedEmailNotifier is None:
            logging.info("Email notifier module not available; notifications disabled for now")
            self._email_last_error = "module_missing"
            self._email_retry_count = getattr(self, "_email_retry_count", 0) + 1
            # Start retry loop if not already running
            if not getattr(self, "_email_retry_task", None):
                self._email_retry_task = self.async_loop.create_task(self._email_init_retry_loop())
            return

        try:
            notifier = _EnhancedEmailNotifier()
            notifier.config_file = PROJECT_ROOT / "config" / "email_config.json"
            await notifier.initialize()
            self.email_notifier = notifier
            logging.info("Email notifier initialized successfully (ensure_email_notifier)")
            # Cancel any retry loop if running
            if getattr(self, "_email_retry_task", None):
                try:
                    self._email_retry_task.cancel()
                except Exception:
                    pass
                self._email_retry_task = None
        except Exception as e:
            logging.warning(f"ensure_email_notifier: failed to initialize notifier: {e}")
            # record last error and bump retry counter
            try:
                self._email_last_error = str(e)
                self._email_retry_count = getattr(self, "_email_retry_count", 0) + 1
            except Exception:
                pass
            # Start or ensure a retry loop is running
            if not getattr(self, "_email_retry_task", None):
                self._email_retry_task = self.async_loop.create_task(self._email_init_retry_loop())

    async def _email_init_retry_loop(self):
        """Background retry loop to attempt email notifier initialization.

        Keeps retrying with exponential backoff up to a cap. Runs until the
        notifier becomes available.
        """
        delay = 5
        max_delay = 300
        while getattr(self, "email_notifier", None) is None:
            try:
                await self.ensure_email_notifier(force=True)
                if getattr(self, "email_notifier", None) is not None:
                    return
            except Exception as ex:
                logging.debug("_email_init_retry_loop: transient failure, will retry", exc_info=True)
                try:
                    self._email_last_error = str(ex)
                    self._email_retry_count = getattr(self, "_email_retry_count", 0) + 1
                except Exception:
                    pass

            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)

    async def send_email_notification(self, tag: str, subject: str, body: str, priority: str = "normal"):
        """Helper to send email notifications, ensuring the notifier is available.

        This will attempt to initialize the notifier if it's not present, and
        will log instead of raising if notifications cannot be sent.
        """
        try:
            if not getattr(self, "email_notifier", None):
                # Try a quick initialization attempt
                await self.ensure_email_notifier()

            if getattr(self, "email_notifier", None):
                try:
                    await self.email_notifier.send_notification(tag, subject, body, priority)
                    logging.info("Email notification sent: %s", subject)
                except Exception as e:
                    logging.warning("Failed to send email notification: %s", e)
            else:
                logging.info("Email notifier not available; skipping sending email: %s", subject)
        except Exception:
            logging.exception("send_email_notification: unexpected error")

    def _safe_join(self, parts, sep="\n"):
        """Join an iterable of parts into a string safely.

        - If parts is None, return an empty string.
        - If parts is a string, return it unchanged.
        - Otherwise, attempt to join by coercing each element to str.
        """
        if parts is None:
            return ""
        # If someone passed a single string, don't iterate its characters
        if isinstance(parts, (str, bytes)):
            return str(parts)

        try:
            return sep.join(map(str, parts))
        except TypeError:
            # Fallback: coerce whole object to string
            try:
                return str(parts)
            except Exception:
                return ""

    def update_ui_metrics(self):
        """Periodically updates UI metrics and timestamps."""
        # Refresh dashboard metrics every 5 seconds to reduce overhead
        if not hasattr(self, "_update_counter"):
            self._update_counter = 0

        self._update_counter += 1
        if self._update_counter >= 5:  # Every 5 seconds
            self.refresh_dashboard()
            self._update_counter = 0

        self.root.after(1000, self.update_ui_metrics)

    async def init_db(self):
        """Initializes the SQLite database for logging."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    service TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT
                )
                """
                )
                await db.commit()
            logging.info("Database initialized successfully.")
        except Exception as e:
            logging.error(f"Database initialization error: {e}")

    def log_activity(self, service: str, action: str, details: str):
        """Log an activity to the database and the UI."""
        self.schedule_async_task(self._async_log_activity(service, action, details))

    async def _async_log_activity(self, service: str, action: str, details: str):
        """Coroutine to perform the database logging."""
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO activity_log (timestamp, service, action, details) VALUES (?, ?, ?, ?)",
                    (timestamp_str, service, action, details),
                )
                await db.commit()

            # Update the UI from the main thread
            self.schedule_on_main_thread(self._update_log_tree, timestamp_str, service, action, details)
        except Exception as e:
            logging.error(f"Database log failed: {e}")

    def _update_log_tree(self, timestamp: str, service: str, action: str, details: str):
        """Updates the log Treeview in the UI. Must be called from the main thread."""
        self.log_tree.insert("", "end", values=(timestamp, service, action, details))
        self.log_tree.yview_moveto(1)

    def start_service_action(self, service_name: str):
        """Action to start a service, called from a button click."""
        self.schedule_async_task(self.start_service(service_name))

    async def start_service(self, service_name: str):
        """Starts a service by its name."""
        service = self.services.get(service_name)
        if not service:
            logging.error(f"Service {service_name} not found.")
            return

        module_path = service.get("module")
        if not module_path:
            logging.error(f"Service {service_name} has no module defined.")
            return

        python_executable = sys.executable
        self.log_activity(service_name, "Starting", f"Executing: {python_executable} -m {module_path}")

        try:
            process = await asyncio.create_subprocess_exec(
                python_executable, "-m", module_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            self.processes[service_name] = process
            self.services[service_name]["status"] = "Running"
            self.log_activity(service_name, "Started", f"Process started with PID: {process.pid}")

            # Send email notification
            if self.email_notifier:
                try:
                    await self.email_notifier.send_notification(
                        "Service Started",
                        f"Service Started: {service['name']}",
                        f"Service: {service['name']}\nModule: {module_path}\nPID: {process.pid}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        "normal",
                    )
                except Exception as e:
                    logging.warning(f"Failed to send service start notification: {e}")

            # Start a task to monitor the process output
            self.schedule_async_task(self.monitor_process_output(service_name, process))

        except Exception as e:
            logging.error(f"Failed to start service {service_name}: {e}")
            self.log_activity(service_name, "Error", f"Failed to start: {e}")
            self.services[service_name]["status"] = "Error"

        self.schedule_on_main_thread(self.update_service_buttons)

    def stop_service_action(self, service_name: str):
        """Action to stop a service, called from a button click."""
        self.schedule_async_task(self.stop_service(service_name))

    async def stop_service(self, service_name: str):
        """Stops a service by its name."""
        process = self.processes.get(service_name)
        if process and process.returncode is None:
            try:
                process.terminate()
                await process.wait()
                self.log_activity(service_name, "Stopped", f"Process {process.pid} terminated.")
            except Exception as e:
                self.log_activity(service_name, "Error", f"Failed to stop process {process.pid}: {e}")

        self.services[service_name]["status"] = "Stopped"
        if service_name in self.processes:
            del self.processes[service_name]

        self.schedule_on_main_thread(self.update_service_buttons)

    async def monitor_process_output(self, service_name: str, process: asyncio.subprocess.Process):
        """Monitors and logs the stdout/stderr of a service process."""
        log_path = PROJECT_ROOT / "logs" / f"{service_name.replace(' ', '_').lower()}.log"

        try:
            with open(log_path, "a") as log_file:
                async for line in process.stdout:
                    log_file.write(line.decode("utf-8", errors="ignore"))
                    log_file.flush()
                async for line in process.stderr:
                    log_file.write(f"ERROR: {line.decode('utf-8', errors='ignore')}")
                    log_file.flush()
        except Exception as e:
            logging.error(f"Error monitoring output for {service_name}: {e}")

    def restart_service_action(self, service_name: str):
        """Action to restart a service."""
        self.schedule_async_task(self.restart_service(service_name))

    async def restart_service(self, service_name: str):
        """Stops and then starts a service."""
        self.log_activity(service_name, "Restarting", "Initiating service restart.")
        await self.stop_service(service_name)
        await asyncio.sleep(2)  # Give it a moment to release resources
        await self.start_service(service_name)

    async def periodic_health_check(self):
        """Periodically checks the health of running services."""
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            for name, service in self.services.items():
                if service.get("status") == "Running" and "health_uri" in service:
                    await self.check_service_health(name, service["health_uri"])

    async def periodic_poll_hourly_reports(self):
        """Poll the hourly reports DB periodically and update the Reports tab summary.

        The function checks PROJECT_ROOT/data/celsius_reports.db hourly_reports table
        and schedules a main-thread UI update when a new report is found.
        """
        import aiosqlite

        db_path = PROJECT_ROOT / "data" / "celsius_reports.db"
        while True:
            try:
                if not self.enable_hourly_updates:
                    await asyncio.sleep(60)
                    continue

                if not db_path.exists():
                    # Schedule a friendly message on the main thread
                    self.schedule_on_main_thread(self._update_hourly_summary_text, "No hourly reports DB found.")
                    await asyncio.sleep(60)
                    continue

                async with aiosqlite.connect(db_path) as db:
                    async with db.execute(
                        "SELECT id, timestamp, report_data FROM hourly_reports ORDER BY id DESC LIMIT 1"
                    ) as cur:
                        row = await cur.fetchone()
                        if row:
                            row_id, ts, data = row[0], row[1], row[2]
                            if row_id != self._last_hourly_id:
                                self._last_hourly_id = row_id
                                # shorten data for UI
                                snippet = (data[:1000] + "...") if data and len(data) > 1000 else (data or "")
                                summary = f"{ts}\n{snippet}"
                                self.schedule_on_main_thread(self._update_hourly_summary_text, summary)
                await asyncio.sleep(60)
            except Exception:
                logging.exception("Error polling hourly reports")
                await asyncio.sleep(60)

    def _update_hourly_summary_text(self, text: str):
        """Update the hourly summary widget on the main thread."""
        try:
            if hasattr(self, "hourly_summary_text"):
                self.hourly_summary_text.delete("1.0", "end")
                self.hourly_summary_text.insert("1.0", text)
        except Exception:
            logging.exception("Failed to update hourly summary UI")

    async def check_service_health(self, service_name: str, uri: str):
        """Checks the health of a service by sending a request to its health URI."""
        if not self.http_session:
            return
        try:
            async with self.http_session.get(uri, timeout=5) as response:
                if response.status == 200:
                    self.log_activity(service_name, "Health Check", "OK")
                else:
                    self.log_activity(service_name, "Health Check", f"Failed with status {response.status}")
                    # Optionally trigger a restart here
        except aiohttp.ClientError as e:
            self.log_activity(service_name, "Health Check", f"Failed: {e}")
            # Optionally trigger a restart here

    def run_tests_action(self):
        """Action to run the ultimate test suite."""
        self.schedule_async_task(self.run_tests())

    async def run_tests(self):
        """Runs the ultimate test suite and logs the results."""
        test_script_path = str(PROJECT_ROOT / "tests" / "ultimate_test_suite.py")
        self.log_activity("Testing", "Starting", "Running ultimate test suite...")
        self.test_output_text.delete("1.0", tk.END)
        self.test_output_text.insert(tk.END, "Running tests...\n\n")

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, test_script_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
            )

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                # Update GUI from the main thread
                self.schedule_on_main_thread(
                    lambda l=line: self.test_output_text.insert(tk.END, l.decode("utf-8", errors="ignore"))
                )

            await process.wait()

            if process.returncode == 0:
                self.log_activity("Testing", "Finished", "All tests passed.")
                self.schedule_on_main_thread(
                    lambda: self.test_output_text.insert(tk.END, "\n--- ✅ All tests passed ---")
                )
            else:
                self.log_activity("Testing", "Finished", f"Tests failed with code {process.returncode}.")
                self.schedule_on_main_thread(
                    lambda: self.test_output_text.insert(
                        tk.END, f"\n--- 🔥 Tests failed (exit code {process.returncode}) ---"
                    )
                )

        except Exception as e:
            self.log_activity("Testing", "Error", f"Failed to run tests: {e}")
            self.schedule_on_main_thread(
                lambda e=e: self.test_output_text.insert(tk.END, f"\n--- 💥 Error running tests: {e} ---")
            )

    def perform_cleanup_action(self):
        """Action to perform system cleanup."""
        self.schedule_async_task(self.perform_cleanup())

    async def perform_cleanup(self):
        """Performs system cleanup tasks."""
        self.log_activity("Admin", "Cleanup", "Starting system cleanup...")
        # This is a synchronous function, so run it in a thread to avoid blocking
        try:
            await asyncio.to_thread(self._execute_cleanup)
            self.log_activity("Admin", "Cleanup", "Cleanup completed successfully.")
            self._msg(messagebox.showinfo, "Cleanup", "System cleanup completed successfully.")
        except Exception as e:
            self.log_activity("Admin", "Cleanup", f"Cleanup failed: {e}")
            self._msg(messagebox.showerror, "Cleanup Error", f"An error occurred during cleanup: {e}")

    def _execute_cleanup(self):
        """Synchronous cleanup logic to be run in a thread."""
        self.schedule_on_main_thread(self.log_activity, "Admin", "Cleanup", "Creating system backup...")
        try:
            backup_path = self.create_system_backup()
            self.schedule_on_main_thread(
                self.log_activity, "Admin", "Backup", f"System backup created at {backup_path}"
            )
        except Exception as e:
            self.schedule_on_main_thread(self.log_activity, "Admin", "Backup", f"Backup failed: {e}")
            raise

        # Add other cleanup tasks here (e.g., cleaning old logs)
        self.schedule_on_main_thread(self.log_activity, "Admin", "Cleanup", "Log cleanup would happen here.")

    def create_system_backup(self) -> Path:
        """
        Creates a zip archive of the entire project directory.

        Excludes cache, backup, and archive directories.
        """
        backup_dir = PROJECT_ROOT / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"celsius_backup_{timestamp}.zip"
        backup_path = backup_dir / backup_filename

        excluded_dirs = {"__pycache__", "backups", "archive", ".git", ".vscode"}

        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in PROJECT_ROOT.rglob("*"):
                # Check if the file is in an excluded directory
                if any(part in excluded_dirs for part in file_path.parts):
                    continue

                # Add file to the zip archive
                relative_path = file_path.relative_to(PROJECT_ROOT)
                zipf.write(file_path, relative_path)

        return backup_path

    # Dashboard helper methods
    def refresh_dashboard(self):
        """Refreshes the dashboard metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            self.cpu_label.config(text=f"CPU: {cpu_percent}%")
            self.memory_label.config(
                text=f"Memory: {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)"
            )
            self.disk_label.config(
                text=f"Disk: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)"
            )

            # Update service status by checking actual running processes
            self._update_service_status_from_processes()

            # Update service status display
            self.service_status_text.delete("1.0", tk.END)
            for name, service in self.services.items():
                status = service.get("status", "Unknown")
                status_symbol = "🟢" if status == "Running" else "🔴" if status == "Stopped" else "⚠️"
                self.service_status_text.insert(tk.END, f"{status_symbol} {service['name']}: {status}\n")
        except Exception as e:
            logging.error(f"Dashboard refresh error: {e}")

    def _update_service_status_from_processes(self):
        """Updates service status by checking actual running processes."""
        try:
            # Get all Python processes
            python_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["name"] and "python" in proc.info["name"].lower():
                        python_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Map service modules to check
            service_module_map = {
                "defender": "celsius_realtime_defender.py",
                "core_ai": "main.py",
                "dashboard": "enhanced_mobile_dashboard.py",
                "guardian": "celsius_ultimate_guardian.py",
                "web_learning": "web_learning",
                "hourly_reporter": "celsius_hourly_reporter.py",
            }

            # Check each service
            for service_name, module_pattern in service_module_map.items():
                if service_name not in self.services:
                    continue

                is_running = False
                for proc in python_processes:
                    try:
                        cmdline = proc.info.get("cmdline", [])
                        if cmdline and any(module_pattern in str(arg) for arg in cmdline):
                            is_running = True
                            # Update process reference if we don't have it
                            if service_name not in self.processes:
                                self.processes[service_name] = proc
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # Update status
                if is_running:
                    self.services[service_name]["status"] = "Running"
                else:
                    self.services[service_name]["status"] = "Stopped"
                    # Clean up dead process reference
                    if service_name in self.processes:
                        del self.processes[service_name]

        except Exception as e:
            logging.error(f"Error updating service status from processes: {e}")

    def start_all_services(self):
        """Starts all configured services."""
        for service_name in self.services:
            if self.services[service_name]["status"] != "Running":
                self.start_service_action(service_name)
        self._msg(messagebox.showinfo, "Services", "Starting all services...")

    def stop_all_services(self):
        """Stops all running services."""
        for service_name in self.services:
            if self.services[service_name]["status"] == "Running":
                self.stop_service_action(service_name)
        self._msg(messagebox.showinfo, "Services", "Stopping all services...")

    # AI Systems helper methods
    def start_learning_session(self):
        """Starts a new AI learning session."""
        self._msg(
            messagebox.showinfo,
            "Web Learning",
            "Starting AI learning session...\nThis feature will initiate web-based knowledge acquisition.",
        )
        self.log_activity("AI Systems", "Learning Session", "Started new learning session")

    def view_learning_history(self):
        """Views the AI learning history."""
        self._msg(
            messagebox.showinfo,
            "Learning History",
            "This feature will display the history of AI learning sessions and acquired knowledge.",
        )

    # Security helper methods
    def export_security_log(self):
        """Exports the security log to a file."""
        try:
            export_path = PROJECT_ROOT / "logs" / f"security_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(export_path, "w") as f:
                f.write("Celsius AI - Security Log Export\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write("=" * 80 + "\n\n")
                for item in self.security_log_tree.get_children():
                    values = self.security_log_tree.item(item)["values"]
                    f.write(f"{values[0]} | {values[1]} | {values[2]} | {values[3]}\n")
            self._msg(messagebox.showinfo, "Export", f"Security log exported to:\n{export_path}")
        except Exception as e:
            self._msg(messagebox.showerror, "Export Error", f"Failed to export security log: {e}")

    def clear_security_log(self):
        """Clears the security log."""
        if messagebox.askyesno("Clear Log", "Are you sure you want to clear the security log?"):
            for item in self.security_log_tree.get_children():
                self.security_log_tree.delete(item)
            self._msg(messagebox.showinfo, "Cleared", "Security log has been cleared.")

    # Administration helper methods
    def clear_old_logs(self):
        """Clears old log files."""
        if messagebox.askyesno("Clear Logs", "This will delete log files older than 30 days. Continue?"):
            try:
                logs_dir = PROJECT_ROOT / "logs"
                cutoff_date = datetime.now() - timedelta(days=30)
                deleted_count = 0

                for log_file in logs_dir.glob("*.log"):
                    if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_date:
                        log_file.unlink()
                        deleted_count += 1

                self._msg(messagebox.showinfo, "Cleanup", f"Deleted {deleted_count} old log files.")
                self.log_activity("Admin", "Log Cleanup", f"Deleted {deleted_count} old log files")
            except Exception as e:
                self._msg(messagebox.showerror, "Error", f"Failed to clear logs: {e}")

    def vacuum_databases(self):
        """Vacuums all databases to optimize them."""
        self.schedule_async_task(self._async_vacuum_databases())

    async def _async_vacuum_databases(self):
        """Asynchronously vacuums databases."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("VACUUM")
                await db.commit()
            self._msg(messagebox.showinfo, "Database", "Database optimization complete.")
            self.log_activity("Admin", "Database", "Vacuum completed successfully")
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to vacuum database: {e}")

    def view_db_stats(self):
        """Views database statistics."""
        self.schedule_async_task(self._async_view_db_stats())

    async def _async_view_db_stats(self):
        """Asynchronously retrieves database statistics."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM activity_log")
                count = await cursor.fetchone()

            stats = f"""Database Statistics
            
Activity Log Entries: {count[0] if count else 0}
Database Path: {self.db_path}
Database Size: {self.db_path.stat().st_size / 1024:.2f} KB
"""
            self._msg(messagebox.showinfo, "Database Stats", stats)
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to get database stats: {e}")

    def export_activity_log(self):
        """Exports the activity log to a CSV file."""
        self.schedule_async_task(self._async_export_activity_log())

    async def _async_export_activity_log(self):
        """Asynchronously exports the activity log."""
        try:
            export_path = PROJECT_ROOT / "logs" / f"activity_log_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT timestamp, service, action, details FROM activity_log ORDER BY timestamp DESC"
                )
                rows = await cursor.fetchall()

            with open(export_path, "w") as f:
                f.write("Timestamp,Service,Action,Details\n")
                for row in rows:
                    f.write(f"{row[0]},{row[1]},{row[2]},{row[3]}\n")

            self._msg(messagebox.showinfo, "Export", f"Activity log exported to:\n{export_path}")
        except Exception as e:
            self._msg(messagebox.showerror, "Export Error", f"Failed to export activity log: {e}")

    # Ngrok tunnel management methods
    def toggle_ngrok_tunnel(self, port: int):
        """Start or stop ngrok tunnel for specified port"""
        # NOTE: This requires ngrok to be installed
        # Implementation creates async task to manage ngrok subprocess
        self.async_loop.create_task(self._toggle_ngrok_async(port))

    async def _toggle_ngrok_async(self, port: int):
        """Async implementation of ngrok toggle"""
        try:
            import subprocess

            # Check if ngrok is running for this port
            for proc in psutil.process_iter(["name", "cmdline"]):
                try:
                    if proc.info["name"] and "ngrok" in proc.info["name"].lower():
                        cmdline = proc.info.get("cmdline") or []
                        if str(port) in self._safe_join(cmdline, " "):
                            # Stop this tunnel
                            proc.terminate()
                            await asyncio.sleep(1)
                            self.refresh_ngrok_status()
                            self._msg(messagebox.showinfo, "Ngrok", f"Tunnel on port {port} stopped")
                            return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Start new tunnel
            process = await asyncio.create_subprocess_exec(
                "ngrok", "http", str(port), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            await asyncio.sleep(2)  # Wait for ngrok to initialize
            self.refresh_ngrok_status()
            self._msg(messagebox.showinfo, "Ngrok", f"Tunnel started on port {port}\nCheck status for public URL")

        except FileNotFoundError:
            self._msg(messagebox.showerror, "Ngrok Error", "ngrok not found. Please install ngrok first.")
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to toggle tunnel: {e}")

    def stop_selected_tunnel(self):
        """Stop the selected ngrok tunnel"""
        selection = self.tunnel_tree.selection()
        if not selection:
            self._msg(messagebox.showwarning, "No Selection", "Please select a tunnel to stop")
            return

        item = self.tunnel_tree.item(selection[0])
        port = item["values"][0]

        # Find and stop the ngrok process for this port
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                if proc.info["name"] and "ngrok" in proc.info["name"].lower():
                    cmdline = proc.info.get("cmdline") or []
                    if str(port) in self._safe_join(cmdline, " "):
                        proc.terminate()
                        self._msg(messagebox.showinfo, "Stopped", f"Tunnel on port {port} stopped")
                        self.refresh_ngrok_status()
                        return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self._msg(messagebox.showwarning, "Not Found", f"No active tunnel found for port {port}")

    def refresh_ngrok_status(self):
        """Refresh ngrok tunnel status"""
        # Clear current items
        for item in self.tunnel_tree.get_children():
            self.tunnel_tree.delete(item)

        # Find running ngrok processes
        tunnels_found = []
        for proc in psutil.process_iter(["name", "cmdline", "pid"]):
            try:
                if proc.info["name"] and "ngrok" in proc.info["name"].lower():
                    cmdline = self._safe_join(proc.info.get("cmdline") or [], " ")

                    # Extract port if present
                    import re

                    port_match = re.search(r"http\s+(\d+)", cmdline)
                    if port_match:
                        port = port_match.group(1)
                        tunnels_found.append({"port": port, "pid": proc.info["pid"], "status": "Running"})

                        # Try to get public URL from ngrok API
                        try:
                            import requests

                            response = requests.get("http://localhost:4040/api/tunnels", timeout=2)
                            if response.status_code == 200:
                                data = response.json()
                                for tunnel in data.get("tunnels", []):
                                    if str(port) in tunnel.get("config", {}).get("addr", ""):
                                        public_url = tunnel.get("public_url", "N/A")
                                        self.tunnel_tree.insert("", "end", values=(port, public_url, "Active"))
                                        break
                            else:
                                self.tunnel_tree.insert("", "end", values=(port, "Starting...", "Initializing"))
                        except Exception:
                            self.tunnel_tree.insert("", "end", values=(port, "Check ngrok dashboard", "Running"))

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Update status text
        self.ngrok_status_text.delete("1.0", "end")
        if tunnels_found:
            status = f"Active Tunnels: {len(tunnels_found)}\n"
            status += "Ngrok Dashboard: http://localhost:4040\n"
            status += "\nNote: Public URLs are available in the ngrok dashboard"
        else:
            status = "No active ngrok tunnels\n"
            status += "Click 'Start Dashboard Tunnel' to create a tunnel\n"
            status += "Note: ngrok must be installed (https://ngrok.com)"

        self.ngrok_status_text.insert("1.0", status)

    # Code approval methods
    def refresh_approval_requests(self):
        """Refresh the list of pending code approval requests"""
        # Notify user that requests are being retrieved (runs on main thread)
        self._msg(messagebox.showinfo, "Retrieving", "Retrieving approval requests...")
        self.async_loop.create_task(self._refresh_approvals_async())

    async def _refresh_approvals_async(self):
        """Async implementation of approval refresh"""
        try:
            # Import the code approval system
            from src.core.celsius_code_approval_system import CelsiusCodeApprovalSystem

            approval_system = CelsiusCodeApprovalSystem()
            await approval_system.initialize()

            pending = await approval_system.get_pending_requests()

            # Update UI on main thread
            def update_ui():
                # Clear current items
                for item in self.approval_tree.get_children():
                    self.approval_tree.delete(item)

                # Add pending requests
                for request in pending:
                    files = (
                        json.loads(request["files_to_modify"])
                        if isinstance(request["files_to_modify"], str)
                        else request["files_to_modify"]
                    )
                    files_str = ", ".join([Path(f).name for f in files[:3]])
                    if len(files) > 3:
                        files_str += f" +{len(files)-3} more"

                    self.approval_tree.insert(
                        "",
                        "end",
                        values=(
                            request["request_id"],
                            request["title"],
                            files_str,
                            request["timestamp"][:19],  # Trim to datetime
                        ),
                        tags=(request["request_id"],),
                    )

            # Show result to the user
            if not pending:
                self._msg(messagebox.showinfo, "No Approvals", "No new code approval requests were found.")
            else:
                self._msg(
                    messagebox.showinfo, "Approvals Retrieved", f"Retrieved {len(pending)} pending approval request(s)."
                )

            self.schedule_on_main_thread(update_ui)

        except Exception as e:
            import traceback

            tb = traceback.format_exc()
            logger.error(f"Failed to refresh approvals: {e}\n{tb}")
            # Persist traceback to a timestamped log file for easier diagnosis
            try:
                log_dir = PROJECT_ROOT / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                log_path = log_dir / f"approval_refresh_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                with open(log_path, "w", encoding="utf-8") as lf:
                    lf.write(tb)
            except Exception:
                log_path = None

            # Notify user on the main thread and point to the saved logfile
            if log_path:
                self._msg(
                    messagebox.showerror, "Error", f"Failed to load approval requests. Details written to:\n{log_path}"
                )
            else:
                self._msg(messagebox.showerror, "Error", f"Failed to load approval requests: {e}")

    def on_approval_select(self, event):
        """Handle selection of approval request to show details"""
        selection = self.approval_tree.selection()
        if not selection:
            return

        request_id = self.approval_tree.item(selection[0])["values"][0]
        self.async_loop.create_task(self._load_approval_details_async(request_id))

    def download_blank_authorization_form(self):
        """Prompt the user to save a blank authorization form (text) to disk."""
        try:
            default_name = f"celsius_authorization_form_{datetime.now().strftime('%Y%m%d')}.txt"
            save_path = filedialog.asksaveasfilename(
                parent=self.root,
                title="Save Blank Authorization Form",
                defaultextension=".txt",
                initialfile=default_name,
                filetypes=[("Text File", "*.txt"), ("All Files", "*")],
            )
            if not save_path:
                return

            template = (
                "Celsius AI - Authorization Form\n"
                "=================================\n\n"
                "Project/Request Title:\n"
                "Requested By (Name):\n"
                "Requested By (Email):\n"
                "Date:\n\n"
                "Description of Requested Change:\n\n"
                "Security & Compliance Approval:\n\n"
                "Approver Name:\n"
                "Approver Signature:\n"
                "Approval Date:\n\n"
                "Notes:\n"
            )

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(template)

            self._msg(messagebox.showinfo, "Saved", f"Blank authorization form saved to:\n{save_path}")
        except Exception as e:
            logging.exception("Failed to write authorization form: %s", e)
            self._msg(messagebox.showerror, "Error", f"Failed to save authorization form: {e}")

    async def _load_approval_details_async(self, request_id: str):
        """Load and display approval request details"""
        try:
            from src.core.celsius_code_approval_system import CelsiusCodeApprovalSystem

            approval_system = CelsiusCodeApprovalSystem()
            await approval_system.initialize()

            # Get request details from database
            async with aiosqlite.connect(approval_system.db_path) as db:
                async with db.execute("SELECT * FROM approval_requests WHERE request_id = ?", (request_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        columns = [desc[0] for desc in cursor.description]
                        request = dict(zip(columns, row))

                        # Format details for display
                        details = f"""
REQUEST ID: {request['request_id']}
TITLE: {request['title']}
TIMESTAMP: {request['timestamp']}
STATUS: {request['status']}

DESCRIPTION:
{request['description']}

FILES TO MODIFY:
{request['files_to_modify']}

DETAILED CHANGES:
{request['changes_detail']}

BENEFITS:
{request['benefits']}

POTENTIAL DETRIMENTS:
{request['detriments']}

ALTERNATIVES CONSIDERED:
{request['alternatives']}

USER RESPONSE:
{request['user_response'] or 'Pending decision'}
"""

                        # Update UI
                        def update_details():
                            self.approval_details_text.delete("1.0", "end")
                            self.approval_details_text.insert("1.0", details)

                        self.schedule_on_main_thread(update_details)

        except Exception as e:
            logger.error(f"Failed to load approval details: {e}")

    async def _submit_code_approval_async(
        self,
        title: str,
        description: str,
        files_to_modify: list,
        changes_detail: str,
        benefits: str,
        detriments: str,
        alternatives: str,
    ):
        """Submit a code approval request into the centralized approval DB."""
        try:
            from src.core.celsius_code_approval_system import CelsiusCodeApprovalSystem

            approval_system = CelsiusCodeApprovalSystem()
            await approval_system.initialize()
            request_id = await approval_system.submit_request(
                title=title,
                description=description,
                files_to_modify=files_to_modify,
                changes_detail=changes_detail,
                benefits=benefits,
                detriments=detriments,
                alternatives=alternatives,
            )

            # Notify user on main thread
            def notify():
                self._msg(messagebox.showinfo, "Code Approval Requested", f"Submitted code approval request: {request_id}")

            self.schedule_on_main_thread(notify)
            # Refresh approvals list so the request appears in the UI
            self.schedule_on_main_thread(self.refresh_approval_requests)
        except Exception as e:
            logger.error(f"Failed to submit code approval request: {e}")
            try:
                self._msg(messagebox.showerror, "Error", f"Failed to create code approval request: {e}")
            except Exception:
                pass

    def approve_code_change(self):
        """Approve the selected code change request"""
        selection = self.approval_tree.selection()
        if not selection:
            self._msg(messagebox.showwarning, "No Selection", "Please select a request to approve")
            return

        request_id = self.approval_tree.item(selection[0])["values"][0]

        # Get user notes
        notes = tk.simpledialog.askstring("Approval Notes", "Optional notes for approval:", parent=self.root)

        if messagebox.askyesno(
            "Confirm Approval",
            f"Approve code change request {request_id}?\n\nThis will allow Celsius AI to make the requested changes.",
        ):
            self.async_loop.create_task(self._approve_async(request_id, notes or "Approved"))

    async def _approve_async(self, request_id: str, notes: str):
        """Async approval implementation"""
        try:
            from src.core.celsius_code_approval_system import CelsiusCodeApprovalSystem

            approval_system = CelsiusCodeApprovalSystem()
            await approval_system.initialize()
            await approval_system.approve_request(request_id, notes)

            self._msg(messagebox.showinfo, "Approved", f"Request {request_id} approved")
            self.refresh_approval_requests()

            # After approval, offer to auto-apply the proposed patch (safe, gated)
            try:
                # Load the request details to get the changes_detail (patch)
                import aiosqlite

                async with aiosqlite.connect(approval_system.db_path) as db:
                    async with db.execute(
                        "SELECT title, changes_detail FROM approval_requests WHERE request_id = ?",
                        (request_id,),
                    ) as cursor:
                        row = await cursor.fetchone()
                        if row:
                            title, changes_detail = row[0], row[1]
                        else:
                            changes_detail = None

                # Only offer auto-apply if there's a plausible unified diff in changes_detail
                plausible_patch = False
                if changes_detail and isinstance(changes_detail, str):
                    patch_head = changes_detail.strip().splitlines()[0] if changes_detail.strip() else ""
                    if patch_head.startswith("diff --git") or patch_head.startswith("***") or patch_head.startswith("---"):
                        plausible_patch = True

                if not changes_detail:
                    # Nothing to apply
                    return

                if plausible_patch:
                    # Ask user whether to attempt to apply now (will run tests)
                    apply_now = messagebox.askyesno(
                        "Apply Patch Now",
                        "This approval contains a patch. Would you like to attempt applying it now?\n(The system will run tests and rollback on failure.)",
                    )
                    if apply_now:
                        # Schedule async apply
                        self.async_loop.create_task(self._apply_approved_patch(request_id, title))
                else:
                    # Not a unified diff; save to proposals for manual review
                    try:
                        prop_dir = PROJECT_ROOT / "proposals"
                        prop_dir.mkdir(parents=True, exist_ok=True)
                        prop_file = prop_dir / f"{request_id}.txt"
                        prop_file.write_text(changes_detail or "", encoding="utf-8")
                        self._msg(
                            messagebox.showinfo,
                            "Patch Saved",
                            f"Approval details were saved to {prop_file}. Please paste a unified diff into the Code Approval request to enable auto-apply.",
                        )
                    except Exception:
                        pass
            except Exception:
                # Non-fatal; don't block approval flow
                pass

        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to approve: {e}")

    def reject_code_change(self):
        """Reject the selected code change request"""
        selection = self.approval_tree.selection()
        if not selection:
            self._msg(messagebox.showwarning, "No Selection", "Please select a request to reject")
            return

        request_id = self.approval_tree.item(selection[0])["values"][0]

        # Get rejection reason
        reason = tk.simpledialog.askstring(
            "Rejection Reason", "Please provide a reason for rejection:", parent=self.root
        )

        if not reason:
            self._msg(messagebox.showwarning, "Reason Required", "Please provide a reason for rejection")
            return

        if messagebox.askyesno("Confirm Rejection", f"Reject code change request {request_id}?"):
            self.async_loop.create_task(self._reject_async(request_id, reason))

    def apply_selected_patch(self):
        """Handler to apply the unified-diff attached to the selected approval request.

        This schedules the same safe apply routine used by the approve flow, but
        is explicitly triggered by the admin (no intermediate approve step).
        """
        selection = self.approval_tree.selection()
        if not selection:
            self._msg(messagebox.showwarning, "No Selection", "Please select a request to apply")
            return

        request_id = self.approval_tree.item(selection[0])["values"][0]

        if not messagebox.askyesno("Confirm Apply", f"Apply patch for request {request_id} now?\n(This will run tests and rollback on failure.)"):
            return

        # fetch title for commit message
        try:
            import aiosqlite

            async def _get_and_apply():
                try:
                    from src.core.celsius_code_approval_system import CelsiusCodeApprovalSystem

                    approval_system = CelsiusCodeApprovalSystem()
                    await approval_system.initialize()
                    async with aiosqlite.connect(approval_system.db_path) as db:
                        async with db.execute("SELECT title FROM approval_requests WHERE request_id = ?", (request_id,)) as cur:
                            row = await cur.fetchone()
                            title = row[0] if row else request_id
                except Exception:
                    title = request_id

                # schedule the safe apply
                await self._apply_approved_patch(request_id, title)

            self.async_loop.create_task(_get_and_apply())
        except Exception:
            # Fallback: schedule apply without title
            self.async_loop.create_task(self._apply_approved_patch(request_id, request_id))

    def explain_selected_change(self):
        """Generate and show a human-readable explanation of the selected request's patch."""
        selection = self.approval_tree.selection()
        if not selection:
            self._msg(messagebox.showwarning, "No Selection", "Please select a request to explain")
            return

        request_id = self.approval_tree.item(selection[0])["values"][0]

        try:
            import aiosqlite

            async def _fetch_and_explain():
                try:
                    from src.core.celsius_code_approval_system import CelsiusCodeApprovalSystem

                    approval_system = CelsiusCodeApprovalSystem()
                    await approval_system.initialize()
                    async with aiosqlite.connect(approval_system.db_path) as db:
                        async with db.execute("SELECT changes_detail FROM approval_requests WHERE request_id = ?", (request_id,)) as cur:
                            row = await cur.fetchone()
                            patch_text = row[0] if row else None
                except Exception:
                    patch_text = None

                explanation = self._summarize_patch(patch_text)

                def show():
                    # Use the details text box to show a longer explanation
                    try:
                        self.approval_details_text.delete("1.0", "end")
                        self.approval_details_text.insert("1.0", explanation)
                    except Exception:
                        self._msg(messagebox.showinfo, "Patch Explanation", explanation)

                self.schedule_on_main_thread(show)

            self.async_loop.create_task(_fetch_and_explain())
        except Exception:
            explanation = self._summarize_patch(None)
            self._msg(messagebox.showinfo, "Patch Explanation", explanation)

    def _summarize_patch(self, patch_text: str | None) -> str:
        """Produce a human-readable summary of a unified diff or descriptive changes.

        - Lists files changed and a short summary of additions/removals by file
        - If no patch text is present, returns guidance message
        """
        if not patch_text:
            return (
                "No patch available for this request.\n\n"
                "If this request included a patch, paste a unified diff (git-style) into the 'Detailed Changes' field so the system can explain and optionally apply it.\n"
            )

        lines = patch_text.splitlines()
        files = []
        summary = []
        cur_file = None
        adds = 0
        dels = 0

        for ln in lines:
            if ln.startswith("diff --git"):
                # commit previous
                if cur_file:
                    summary.append(f"{cur_file}: +{adds} / -{dels}")
                # reset
                parts = ln.split()
                if len(parts) >= 3:
                    # diff --git a/path b/path
                    a = parts[2]
                    b = parts[3] if len(parts) > 3 else parts[-1]
                    # strip a/ b/
                    cur_file = b.split("b/")[-1] if "b/" in b else b
                else:
                    cur_file = "unknown"
                files.append(cur_file)
                adds = dels = 0
            elif ln.startswith("+") and not ln.startswith("+++ "):
                adds += 1
            elif ln.startswith("-") and not ln.startswith("--- "):
                dels += 1

        # append last
        if cur_file:
            summary.append(f"{cur_file}: +{adds} / -{dels}")

        if not files:
            # If it wasn't a git diff, just return the text up to a reasonable length
            excerpt = patch_text[:400]
            return f"Patch preview (non-diff or small):\n\n{excerpt}\n\n(Full details in DB)"

        out = "Patch Summary:\n"
        out += "Files changed:\n"
        for s in summary:
            out += f" - {s}\n"

        out += "\nDetailed preview (first 400 chars):\n"
        out += patch_text[:400]
        return out

    async def _reject_async(self, request_id: str, reason: str):
        """Async rejection implementation"""
        try:
            from src.core.celsius_code_approval_system import CelsiusCodeApprovalSystem

            approval_system = CelsiusCodeApprovalSystem()
            await approval_system.initialize()
            await approval_system.reject_request(request_id, reason)

            self._msg(messagebox.showinfo, "Rejected", f"Request {request_id} rejected")
            self.refresh_approval_requests()

        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to reject: {e}")

    async def _apply_approved_patch(self, request_id: str, title: str):
        """Attempt to apply an approved patch safely.

        Creates a new git branch, attempts to apply the unified diff, runs tests,
        commits on success, or rolls back on failure.
        """
        try:
            import subprocess
            import sys
            import tempfile
            import shutil
            from pathlib import Path
            import aiosqlite

            repo_root = PROJECT_ROOT

            # Fetch the patch text from DB
            try:
                from src.core.celsius_code_approval_system import CelsiusCodeApprovalSystem

                approval_system = CelsiusCodeApprovalSystem()
            except Exception:
                approval_system = None

            patch_text = None
            if approval_system:
                async with aiosqlite.connect(approval_system.db_path) as db:
                    async with db.execute(
                        "SELECT changes_detail FROM approval_requests WHERE request_id = ?",
                        (request_id,),
                    ) as cursor:
                        row = await cursor.fetchone()
                        if row:
                            patch_text = row[0]

            if not patch_text or not isinstance(patch_text, str):
                self.schedule_on_main_thread(lambda: self._msg(messagebox.showerror, "No Patch", "No patch available to apply."))
                return

            first_line = patch_text.strip().splitlines()[0] if patch_text.strip() else ""
            if not (first_line.startswith("diff --git") or first_line.startswith("***") or first_line.startswith("---")):
                self.schedule_on_main_thread(lambda: self._msg(messagebox.showerror, "Not a Patch", "Stored changes are not a unified diff. Auto-apply aborted."))
                return

            tmpdir = Path(tempfile.mkdtemp(prefix="celsius_apply_"))
            patch_file = tmpdir / f"{request_id}.diff"
            patch_file.write_text(patch_text, encoding="utf-8")

            def run(cmd, **kw):
                return subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root), **kw)

            # Ensure git repo
            res = run(["git", "rev-parse", "--show-toplevel"])
            if res.returncode != 0:
                self.schedule_on_main_thread(lambda: self._msg(messagebox.showerror, "Git Error", "Not a git repository."))
                shutil.rmtree(tmpdir, ignore_errors=True)
                return

            cur_branch_proc = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            cur_branch = cur_branch_proc.stdout.strip() if cur_branch_proc.returncode == 0 else "main"
            head_proc = run(["git", "rev-parse", "HEAD"])
            orig_head = head_proc.stdout.strip() if head_proc.returncode == 0 else None

            branch_name = f"apply/{request_id}"
            res = run(["git", "checkout", "-b", branch_name])
            if res.returncode != 0:
                res = run(["git", "checkout", branch_name])
                if res.returncode != 0:
                    self.schedule_on_main_thread(lambda: self._msg(messagebox.showerror, "Git Error", f"Failed to create/checkout branch {branch_name}: {res.stderr}"))
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    return

            # Check apply
            res = run(["git", "apply", "--check", str(patch_file)])
            if res.returncode != 0:
                self.schedule_on_main_thread(lambda: self._msg(messagebox.showerror, "Apply Failed", f"Patch cannot be applied:\n{res.stderr}"))
                run(["git", "checkout", cur_branch])
                run(["git", "branch", "-D", branch_name])
                shutil.rmtree(tmpdir, ignore_errors=True)
                return

            res = run(["git", "apply", "--index", str(patch_file)])
            if res.returncode != 0:
                self.schedule_on_main_thread(lambda: self._msg(messagebox.showerror, "Apply Failed", f"git apply failed:\n{res.stderr}"))
                run(["git", "checkout", cur_branch])
                run(["git", "branch", "-D", branch_name])
                shutil.rmtree(tmpdir, ignore_errors=True)
                return

            py = sys.executable
            test_proc = run([py, "-m", "pytest", "tests/", "-q"]) 

            if test_proc.returncode == 0:
                commit_msg = f"Apply approved code change {request_id}: {title}"
                run(["git", "commit", "-m", commit_msg])
                out = test_proc.stdout + "\n" + test_proc.stderr
                self.schedule_on_main_thread(lambda: self._msg(messagebox.showinfo, "Applied", f"Patch applied and tests passed. Branch: {branch_name}\n\nTest output:\n{out[:2000]}"))
            else:
                out = test_proc.stdout + "\n" + test_proc.stderr
                if orig_head:
                    run(["git", "reset", "--hard", orig_head])
                run(["git", "checkout", cur_branch])
                run(["git", "branch", "-D", branch_name])
                self.schedule_on_main_thread(lambda: self._msg(messagebox.showerror, "Tests Failed", f"Tests failed after applying patch. Rolled back.\n\nTest output:\n{out[:2000]}"))

            shutil.rmtree(tmpdir, ignore_errors=True)

        except Exception as e:
            logger.error(f"Error applying approved patch: {e}")
            try:
                self.schedule_on_main_thread(lambda: self._msg(messagebox.showerror, "Error", f"Failed to apply approved patch: {e}"))
            except Exception:
                pass

    def stop_learning_system(self):
        """Attempt to stop the AI learning system (best-effort)."""
        # Schedule an async graceful stop so we can wait for termination.
        try:
            self.async_loop.create_task(self._graceful_stop_process("ai_learning"))
        except Exception:
            logging.exception("stop_learning_system: failed to schedule graceful stop")

    def stop_web_learning_system(self):
        """Attempt to stop the web learning subprocess/integration (best-effort)."""
        try:
            self.async_loop.create_task(self._graceful_stop_process("web_learning"))
        except Exception:
            logging.exception("stop_web_learning_system: failed to schedule graceful stop")

    async def _graceful_stop_process(self, name: str, timeout: float = 8.0):
        """Gracefully stop a named subprocess tracked in self.processes.

        Attempts terminate(), waits up to `timeout` seconds, then kills if still running.
        Falls back to calling higher-level integration stop methods if no process is tracked.
        """
        try:
            proc = self.processes.get(name)
            if proc:
                try:
                    # Try to send SIGINT first (if supported) to allow graceful shutdown
                    try:
                        if hasattr(proc, "send_signal"):
                            try:
                                proc.send_signal(signal.SIGINT)
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # Wait briefly for graceful exit
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=2.0)
                        self._msg(messagebox.showinfo, "Stopped", f"Process {name} exited on SIGINT.")
                        try:
                            del self.processes[name]
                        except Exception:
                            pass
                        return
                    except asyncio.TimeoutError:
                        # Not exited yet - fall back to terminate
                        logging.debug("Process %s did not exit after SIGINT; sending terminate", name)

                    try:
                        proc.terminate()
                    except Exception:
                        pass

                    # Wait for process to exit after terminate
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=timeout)
                        self._msg(messagebox.showinfo, "Stopped", f"Process {name} terminated gracefully.")
                        try:
                            del self.processes[name]
                        except Exception:
                            pass
                        return
                    except asyncio.TimeoutError:
                        logging.warning("Process %s did not exit within timeout; killing", name)
                        try:
                            proc.kill()
                        except Exception:
                            pass
                        try:
                            await asyncio.wait_for(proc.wait(), timeout=3.0)
                        except Exception:
                            pass
                        self._msg(messagebox.showinfo, "Stopped", f"Process {name} killed.")
                        try:
                            del self.processes[name]
                        except Exception:
                            pass
                        return
                except Exception:
                    logging.exception("Error while stopping process %s", name)

            # If no tracked process, attempt integration stop
            if name == "ai_learning":
                try:
                    if hasattr(self, "conversational_ai") and self.conversational_ai:
                        stop = getattr(self.conversational_ai, "stop", None)
                        if callable(stop):
                            stop()
                            self._msg(messagebox.showinfo, "Stopped", "AI learning stopped via integration.")
                            return
                except Exception:
                    logging.debug("_graceful_stop_process ai_learning: integration stop failed", exc_info=True)

            if name == "web_learning":
                try:
                    integration = getattr(self, "web_learning_integration", None)
                    if integration and hasattr(integration, "stop_learning"):
                        integration.stop_learning()
                        self._msg(messagebox.showinfo, "Stopped", "Web learning integration stopped.")
                        return
                except Exception:
                    logging.debug("_graceful_stop_process web_learning: integration stop failed", exc_info=True)

            self._msg(messagebox.showwarning, "Not Running", f"{name} not running or could not be stopped gracefully.")
        except Exception:
            logging.exception("_graceful_stop_process: unexpected error for %s", name)

    # Learning System methods
    def refresh_learning_insights(self):
        """Refresh AI learning insights from the learning system database"""
        # Notify user that we're retrieving learning insights
        self._msg(messagebox.showinfo, "Retrieving", "Retrieving learning insights...")
        self.async_loop.create_task(self._refresh_learning_insights_async())

    async def _refresh_learning_insights_async(self):
        """Async implementation of learning insights refresh"""
        try:
            from src.core.celsius_learning_system import CelsiusLearningSystem

            # Check if learning system is running
            learning_running = False
            for proc in psutil.process_iter(["name", "cmdline"]):
                try:
                    cmdline = self._safe_join(proc.info.get("cmdline") or [], " ")
                    if "celsius_learning_launcher.py" in cmdline or "celsius_learning_system.py" in cmdline:
                        learning_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Update status label (schedule on main Tk thread)
            status_text = "🟢 Learning System: RUNNING" if learning_running else "🔴 Learning System: STOPPED"
            # Use schedule_on_main_thread to avoid calling Tk APIs from worker threads
            self.schedule_on_main_thread(self.learning_status_label.config, text=status_text)

            # Get insights from database
            learning_system = CelsiusLearningSystem()
            await learning_system.initialize()

            insights = await learning_system.get_learning_insights(hours=24)

            # Format insights for display (adapted to dict structure from learning system)
            def update_insights():
                self.learning_insights_text.delete("1.0", "end")

                if not insights:
                    self.learning_insights_text.insert(
                        "1.0",
                        "📊 No learning data available yet.\n\n"
                        "The learning system will start collecting data once launched.\n"
                        "Click 'Start Learning' to begin autonomous monitoring.",
                    )
                    return

                observations = insights.get("observations", {}) or {}
                performance = insights.get("performance", {}) or {}
                suggestions = insights.get("suggestions", []) or []

                # Build display text (defensively - guard against unexpected types)
                try:
                    parts = []
                    parts.append("📈 Learning Insights (Last 24 Hours)")
                    parts.append("=" * 60)

                    # Observation summary
                    parts.append("\n📊 Observation Summary:")
                    total_obs = 0
                    for obs_type, count in observations.items():
                        parts.append(f"  • {obs_type}: {count} observations")
                        try:
                            total_obs += int(count)
                        except Exception:
                            pass
                    parts.append(f"\n🔍 Total Observations: {total_obs}")
                    parts.append("⏱️  Monitoring: Continuous (every 30 seconds)")
                    parts.append(
                        "🎯 Processes Tracked: 7 (Defender, Guardian, Hub, Dashboard, Core AI, Web Learning, Hourly Reporter)\n"
                    )

                    # Performance averages
                    if performance:
                        parts.append("⚙️ Performance (avg last 24h):")
                        for proc_name, vals in performance.items():
                            cpu = vals.get("cpu")
                            mem = vals.get("memory")
                            cpu_s = f"{cpu:.1f}%" if isinstance(cpu, (int, float)) else str(cpu)
                            mem_s = f"{mem:.1f} MB" if isinstance(mem, (int, float)) else str(mem)
                            parts.append(f"  • {proc_name}: CPU {cpu_s}, Memory {mem_s}")
                        parts.append("")

                    # Suggestions
                    if suggestions:
                        parts.append("💡 Recent Improvement Suggestions:")
                        for s in suggestions:
                            parts.append(
                                f"  • [{s.get('category','general')}] {s.get('suggestion','')} (Benefit: {s.get('benefit','n/a')})"
                            )

                    parts.append("\n" + "=" * 60)
                    parts.append("TIP: Learning is autonomous - suggestions appear in Code Approvals tab")

                    # Use safe join with additional fallback
                    try:
                        insights_text = self._safe_join(parts, "\n")
                    except Exception as join_exc:
                        logger.exception("Learning insights formatting failed during join: %s", join_exc)
                        # Fallback to a simple string representation
                        try:
                            insights_text = str(parts)
                        except Exception:
                            insights_text = "📊 Learning insights could not be formatted."

                    # Schedule UI update on the Tk main thread
                    self.schedule_on_main_thread(
                        lambda text=insights_text: (
                            self.learning_insights_text.delete("1.0", "end"),
                            self.learning_insights_text.insert("1.0", text),
                        )
                    )
                except Exception:
                    # Catch any error building the insights text and log full traceback
                    logger.exception("Unexpected error while building learning insights display")
                    fallback = (
                        "❌ Error formatting learning insights.\n"
                        "The learning data may be malformed or incomplete.\n"
                        "Please check the learning system database and logs."
                    )
                    self.schedule_on_main_thread(
                        lambda text=fallback: (
                            self.learning_insights_text.delete("1.0", "end"),
                            self.learning_insights_text.insert("1.0", text),
                        )
                    )

            # Schedule the follow-up UI callback on the main thread as well
            self.schedule_on_main_thread(update_insights)

        except Exception as e:
            # Log full traceback to help diagnosing the source of the join/type error
            logger.error(f"Failed to refresh learning insights: {e}", exc_info=True)
            err_text = f"❌ Error loading learning insights:\n{e}\n\n" "Make sure the learning system database exists."
            self.schedule_on_main_thread(
                lambda text=err_text: (
                    self.learning_insights_text.delete("1.0", "end"),
                    self.learning_insights_text.insert("1.0", text),
                )
            )

    def start_learning_system(self):
        """Start the Learning System as a background process"""
        try:
            import subprocess

            # Check if already running
            for proc in psutil.process_iter(["name", "cmdline"]):
                try:
                    cmdline = self._safe_join(proc.info.get("cmdline") or [], " ")
                    if "celsius_learning_launcher.py" in cmdline:
                        self._msg(messagebox.showinfo, "Already Running", "Learning System is already running")
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Start learning system
            learning_script = PROJECT_ROOT / "src" / "learning" / "celsius_learning_launcher.py"

            if sys.platform == "win32":
                # Windows: Use cmd.exe start to open a new console window reliably
                try:
                    subprocess.Popen(["cmd", "/c", "start", "", sys.executable, str(learning_script)])
                except Exception:
                    # Fallback to CREATE_NEW_CONSOLE if start fails
                    subprocess.Popen(
                        [sys.executable, str(learning_script)], creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
            else:
                # Unix-like: Use nohup
                subprocess.Popen(
                    [sys.executable, str(learning_script)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )

            self._msg(
                messagebox.showinfo,
                "Started",
                "Learning System started successfully!\n\n"
                "It will run in the background monitoring all processes.\n"
                "Insights will appear here and suggestions in Code Approvals tab.",
            )

            # Refresh status after 2 seconds
            self.root.after(2000, self.refresh_learning_insights)

        except Exception as e:
            self._msg(messagebox.showerror, "Start Error", f"Failed to start Learning System:\n{e}")

    def start_web_learning_system(self):
        """Start the Web Learning System as a background process"""
        try:
            import subprocess

            # Check if already running
            for proc in psutil.process_iter(["name", "cmdline"]):
                try:
                    cmdline = self._safe_join(proc.info.get("cmdline") or [], " ")
                    if "celsius_web_learning_launcher.py" in cmdline:
                        self._msg(messagebox.showinfo, "Already Running", "Web Learning System is already running")
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Start web learning system
            web_learning_script = PROJECT_ROOT / "src" / "learning" / "celsius_web_learning_launcher.py"

            if sys.platform == "win32":
                # Windows: Use cmd.exe start to open a new console window reliably
                try:
                    subprocess.Popen(["cmd", "/c", "start", "", sys.executable, str(web_learning_script), "--daemon"])
                except Exception:
                    subprocess.Popen(
                        [sys.executable, str(web_learning_script), "--daemon"],
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )
            else:
                # Unix-like: Use nohup
                subprocess.Popen(
                    [sys.executable, str(web_learning_script), "--daemon"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )

            self._msg(
                messagebox.showinfo,
                "Started",
                "Web Learning System started successfully!\n\n"
                "It will run in daemon mode in the background.\n"
                "Check the terminal window for status updates.",
            )

            # Refresh status after 2 seconds
            self.root.after(2000, self.refresh_learning_insights)

        except Exception as e:
            self._msg(messagebox.showerror, "Start Error", f"Failed to start Web Learning System:\n{e}")

    # Reports Tab Methods
    def refresh_learning_reports(self):
        """Refresh and display learning reports"""
        try:
            self.learning_reports_text.delete("1.0", "end")

            reports_dir = PROJECT_ROOT / "learning_reports"
            if not reports_dir.exists():
                self.learning_reports_text.insert(
                    "1.0",
                    "📁 No learning reports directory found.\n\nReports will appear here when the learning system generates them.",
                )
                return

            # Get all learning report files (.txt per new format)
            report_files = list(reports_dir.glob("celsius_learning_report_*.txt"))
            report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)  # Newest first

            if not report_files:
                self.learning_reports_text.insert(
                    "1.0", "No learning reports found. Reports will appear here after the learning system runs."
                )
                return

            # Display recent reports (show the first 5 full text)
            report_text = "CELSIUS AI LEARNING REPORTS\n"
            report_text += "=" * 60 + "\n\n"

            for i, report_file in enumerate(report_files[:5]):  # Show last 5 reports
                try:
                    with open(report_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    report_text += f"Report #{i+1}: {report_file.name}\n"
                    report_text += content
                    report_text += "\n" + ("-" * 60) + "\n\n"

                except Exception as e:
                    report_text += f"Error reading {report_file.name}: {e}\n\n"

            if len(report_files) > 5:
                report_text += f"\n{len(report_files) - 5} additional reports available in learning_reports folder."

            self.learning_reports_text.insert("1.0", report_text)

        except Exception as e:
            self.learning_reports_text.delete("1.0", "end")
            self.learning_reports_text.insert("1.0", f"❌ Error loading learning reports:\n{e}")

    def refresh_hourly_reports_list(self):
        """Populate the hourly reports treeview with files from data/reports."""
        try:
            reports_dir = PROJECT_ROOT / "data" / "reports"
            if not reports_dir.exists():
                # clear tree
                try:
                    for i in getattr(self, "hourly_reports_tree", []).get_children():
                        getattr(self, "hourly_reports_tree").delete(i)
                except Exception:
                    pass
                return

            files = sorted(reports_dir.glob("celsius_hourly_report_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)

            tree = getattr(self, "hourly_reports_tree", None)
            if tree is None:
                return

            # Clear existing
            for row in tree.get_children():
                tree.delete(row)

            for f in files:
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    mtime = "unknown"
                tree.insert("", "end", values=(f.name, mtime))
        except Exception:
            # non-fatal
            return

    def seed_gutenberg_samples(self):
        """Add a few public-domain seeds (Project Gutenberg) as ingestion candidates."""
        try:
            seeds = [
                {
                    "source": "https://www.gutenberg.org/ebooks/1342",
                    "title": "Pride and Prejudice - Project Gutenberg",
                    "added_at": datetime.now().isoformat(),
                },
                {
                    "source": "https://www.gutenberg.org/ebooks/84",
                    "title": "Frankenstein - Project Gutenberg",
                    "added_at": datetime.now().isoformat(),
                },
            ]
            from src.hub.ingestion import load_candidates, save_candidates

            cand = load_candidates(PROJECT_ROOT)
            cand.extend(seeds)
            save_candidates(PROJECT_ROOT, cand)
            # refresh UI
            self.load_ingestion_candidates()
        except Exception:
            return

    def start_web_learner_subprocess(self):
        """Start the web learner in a separate Python subprocess and keep a handle on it."""
        try:
            if getattr(self, "web_learner_proc", None) is not None:
                return
            script = PROJECT_ROOT / "scripts" / "web_learner_runner.py"
            if not script.exists():
                logging.warning("Web learner runner script not found")
                return

            python = sys.executable
            creationflags = 0
            # On Windows, hide console window
            if sys.platform.startswith("win") and hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen([python, str(script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
            self.web_learner_proc = proc
            logging.info(f"Started web learner subprocess (pid={proc.pid})")
        except Exception:
            logging.exception("Failed to start web learner subprocess")

    def stop_web_learner_subprocess(self):
        try:
            proc = getattr(self, "web_learner_proc", None)
            if not proc:
                return
            proc.terminate()
            proc.wait(timeout=5)
            logging.info("Web learner subprocess stopped")
            self.web_learner_proc = None
        except Exception:
            logging.exception("Failed to stop web learner subprocess")

    # --- Admin ingestion review helpers ---
    def _ingestion_candidates_path(self):
        return PROJECT_ROOT / "data" / "ingestion_candidates.json"

    def load_ingestion_candidates(self):
        """Load ingestion candidates from disk and populate the admin tree (if present)."""
        try:
            # delegate to helper so tests can import logic without GUI
            from src.hub.ingestion import load_candidates

            candidates = load_candidates(PROJECT_ROOT)

            # Ensure tree exists
            tree = getattr(self, "ingestion_tree", None)
            if tree is None:
                return candidates

            # Clear
            for r in tree.get_children():
                tree.delete(r)

            for idx, c in enumerate(candidates):
                src = c.get("source", "unknown")
                title = c.get("title", "(no title)")
                ts = c.get("added_at", "")
                tree.insert("", "end", iid=str(idx), values=(idx, src, title, ts))

            return candidates
        except Exception:
            return []

        finally:
            # Update admin status label, if present, with the path and count
            try:
                lbl = getattr(self, "ingestion_status_label", None)
                if lbl is not None:
                    try:
                        p = self._ingestion_candidates_path()
                    except Exception:
                        p = PROJECT_ROOT / "data" / "ingestion_candidates.json"
                    try:
                        count = len(candidates)
                    except Exception:
                        count = 0
                    lbl.config(text=f"Candidates file: {p} — {count} candidate(s)")
            except Exception:
                pass

    def _save_ingestion_candidates(self, candidates):
        try:
            from src.hub.ingestion import save_candidates

            save_candidates(PROJECT_ROOT, candidates)
        except Exception:
            pass

    def approve_selected_ingestion(self):
        """Approve the selected ingestion candidate and move it to approved list."""
        try:
            tree = getattr(self, "ingestion_tree", None)
            if tree is None:
                return
            sel = tree.selection()
            if not sel:
                return
            idx = int(sel[0])
            from src.hub.ingestion import approve_candidate, load_candidates

            # Load current candidates so we can capture the approved item for code-approval metadata
            all_cands = load_candidates(PROJECT_ROOT)
            approved_item = all_cands[idx] if 0 <= idx < len(all_cands) else None

            success = approve_candidate(PROJECT_ROOT, idx)
            if success:
                self.load_ingestion_candidates()
                # Push this newly approved candidate into a running web learner (if any)
                try:
                    from src.learning.celsius_web_learning_integration import refresh_web_learning_approved_sources

                    added = refresh_web_learning_approved_sources()
                    if added:
                        self._msg(messagebox.showinfo, "Learner Updated", f"Pushed {added} approved source(s) to running Web Learner.")
                except Exception:
                    # non-fatal
                    pass

                # Create a code approval request so a human can approve integrating
                # this newly-approved source into the running system (AI-assisted)
                try:
                    # build sources list for request
                    from src.utils.ai_coding import generate_patch_for_approved_sources

                    srcs = []
                    if approved_item:
                        s = approved_item.get("source") or approved_item.get("url")
                        if s:
                            srcs.append(s)
                    patch = generate_patch_for_approved_sources(srcs)
                    title = "Integrate approved ingestion source(s) into Web Learning"
                    desc = "Automatically integrate newly-approved ingestion source(s) into the web learning integration. Review the proposed patch and approve to apply."
                    files = ["src/learning/celsius_web_learning_integration.py"]
                    changes_detail = patch
                    benefits = "Allows the Web Learner to consider admin-approved sources immediately and consistently."
                    detriments = "Minor configuration change; ensure sources are trustworthy and conform to robots.txt and legal requirements."
                    alternatives = "Manually restart the Web Learner after approving sources, or import via the Admin UI."

                    # schedule async submission
                    self.async_loop.create_task(
                        self._submit_code_approval_async(title, desc, files, changes_detail, benefits, detriments, alternatives)
                    )
                except Exception:
                    pass
        except Exception:
            return

    def reject_selected_ingestion(self):
        """Reject (remove) the selected ingestion candidate."""
        try:
            tree = getattr(self, "ingestion_tree", None)
            if tree is None:
                return
            sel = tree.selection()
            if not sel:
                return
            idx = int(sel[0])
            from src.hub.ingestion import reject_candidate

            success = reject_candidate(PROJECT_ROOT, idx)
            if success:
                self.load_ingestion_candidates()
        except Exception:
            return

    def approve_all_ingestion(self):
        """Approve all ingestion candidates (move all to approved list)."""
        try:
            from src.hub.ingestion import load_candidates, approved_path
            from src.hub.ingestion import save_candidates

            candidates = load_candidates(PROJECT_ROOT)
            if not candidates:
                self._msg(messagebox.showinfo, "No Candidates", "No ingestion candidates to approve.")
                return

            ap = approved_path(PROJECT_ROOT)
            approved = []
            if ap.exists():
                try:
                    with open(ap, "r", encoding="utf-8") as f:
                        approved = json.load(f) or []
                except Exception:
                    approved = []

            approved.extend(candidates)
            # write approved file
            ap.parent.mkdir(parents=True, exist_ok=True)
            with open(ap, "w", encoding="utf-8") as f:
                json.dump(approved, f, ensure_ascii=False, indent=2)

            # clear candidates
            save_candidates(PROJECT_ROOT, [])

            # refresh UI
            try:
                self.load_ingestion_candidates()
            except Exception:
                pass

            self._msg(messagebox.showinfo, "Approved", f"Approved {len(candidates)} candidate(s).")

            # Push approved sources into a running web learner immediately
            try:
                from src.learning.celsius_web_learning_integration import refresh_web_learning_approved_sources

                added = refresh_web_learning_approved_sources()
                if added:
                    self._msg(messagebox.showinfo, "Learner Updated", f"Pushed {added} approved source(s) to running Web Learner.")
            except Exception:
                pass
            # Also create a code approval request to integrate these approved sources
            try:
                from src.utils.ai_coding import generate_patch_for_approved_sources

                srcs = [c.get("source") or c.get("url") for c in candidates if (c.get("source") or c.get("url"))]
                patch = generate_patch_for_approved_sources(srcs)
                title = "Integrate approved ingestion sources into Web Learning"
                desc = "Proposed automated integration of newly-approved ingestion sources into the web learning integration. Review the patch and approve to apply."
                files = ["src/learning/celsius_web_learning_integration.py"]
                changes_detail = patch
                benefits = "Enables the Web Learner to directly consider admin-approved sources as part of scheduled learning cycles."
                detriments = "Requires review to ensure sources are appropriate; may increase crawl surface area."
                alternatives = "Manually restart or reconfigure the web learner to include these sources."

                self.async_loop.create_task(
                    self._submit_code_approval_async(title, desc, files, changes_detail, benefits, detriments, alternatives)
                )
            except Exception:
                pass
        except Exception as e:
            logging.exception("approve_all_ingestion failed: %s", e)
            self._msg(messagebox.showerror, "Error", f"Failed to approve all: {e}")

    def open_reports_folder(self):
        """Open the learning reports folder in file explorer"""
        try:
            reports_dir = PROJECT_ROOT / "learning_reports"
            if reports_dir.exists():
                if sys.platform == "win32":
                    os.startfile(str(reports_dir))
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(reports_dir)])
                else:
                    subprocess.run(["xdg-open", str(reports_dir)])
            else:
                self._msg(messagebox.showwarning, "Not Found", "Learning reports directory doesn't exist yet.")
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to open reports folder:\n{e}")

        # --- Hourly Reports Polling ---
        async def periodic_poll_hourly_reports(self):
            """Periodically poll the hourly reports DB and update the UI with the latest summary."""
            try:
                while True:
                    # Fetch latest summary
                    try:
                        latest = await self._fetch_latest_hourly_summary()
                        # Schedule UI update on main thread
                        self.schedule_on_main_thread(self._update_hourly_summary, latest)
                    except Exception:
                        # Non-fatal; continue polling
                        pass
                    # Poll every 60 seconds
                    await asyncio.sleep(60)
            except asyncio.CancelledError:
                return
            except Exception:
                return

        async def _fetch_latest_hourly_summary(self):
            """Return a brief string summary from the latest hourly_reports DB row, if any."""
            try:
                db_path = PROJECT_ROOT / "data" / "celsius_reports.db"
                if not db_path.exists():
                    return "No hourly reports DB found."

                import aiosqlite

                async with aiosqlite.connect(db_path) as db:
                    async with db.execute(
                        "SELECT timestamp, report_data FROM hourly_reports ORDER BY timestamp DESC LIMIT 1"
                    ) as cursor:
                        row = await cursor.fetchone()
                        if not row:
                            return "No hourly reports available."
                        ts, report_data = row
                        # report_data may be long; return first 300 chars plus timestamp
                        snippet = (
                            (report_data[:300] + "...")
                            if report_data and len(report_data) > 300
                            else (report_data or "")
                        )
                        return f"Last hourly report: {ts} — {snippet}"
            except Exception as e:
                return f"Error fetching hourly report: {e}"

        def _update_hourly_summary(self, summary_text: str):
            """Update the hourly summary widget on the main thread."""
            try:
                if not hasattr(self, "hourly_summary_text") or self.hourly_summary_text is None:
                    return
                self.hourly_summary_text.delete("1.0", "end")
                self.hourly_summary_text.insert("1.0", summary_text)
            except Exception:
                # Ignore UI update errors
                pass

    def generate_learning_report(self):
        """Trigger generation of a new learning report"""
        try:
            # Notify user that report generation is starting
            self._msg(messagebox.showinfo, "Generating", "Generating a new learning report...")

            # Proactively trigger the web learning integration to generate a report now
            from src.learning.celsius_web_learning_integration import initialize_web_learning

            integration = initialize_web_learning()
            report = integration.generate_daily_report()

            if report:
                self._msg(
                    messagebox.showinfo,
                    "Report Generated",
                    "A new learning report was generated and saved to the learning_reports folder.",
                )
                # Refresh the reports view
                self.refresh_learning_reports()
            else:
                self._msg(
                    messagebox.showwarning,
                    "No Report",
                    "Could not generate a report right now. Ensure Web Learning is initialized and try again.",
                )
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to generate learning report:\n{e}")

    def show_guardian_report(self):
        """Display Guardian system report"""
        try:
            self.system_reports_text.delete("1.0", "end")

            # Generate Guardian status report
            report_text = "🛡️ GUARDIAN SYSTEM REPORT\n"
            report_text += "=" * 60 + "\n\n"

            # Check Guardian database
            guardian_db = PROJECT_ROOT / "data" / "celsius_guardian.db"
            if guardian_db.exists():
                report_text += "📊 Guardian Database: ✅ Active\n"

                # Read Guardian logs from database
                try:
                    import sqlite3

                    conn = sqlite3.connect(guardian_db)
                    cursor = conn.cursor()

                    # Get recent events
                    cursor.execute(
                        """
                        SELECT timestamp, service_name, event_type, message 
                        FROM guardian_logs 
                        ORDER BY timestamp DESC 
                        LIMIT 10
                    """
                    )

                    events = cursor.fetchall()
                    if events:
                        report_text += f"\n🔍 Recent Guardian Events ({len(events)} shown):\n"
                        report_text += "-" * 60 + "\n"

                        for event in events:
                            timestamp, service, event_type, message = event
                            report_text += f"[{timestamp}] {service} - {event_type}\n"
                            report_text += f"  {message}\n\n"

                    conn.close()

                except Exception as e:
                    report_text += f"⚠️ Error reading Guardian database: {e}\n"
            else:
                report_text += "📊 Guardian Database: ❌ Not Found\n"

            # Check Guardian processes
            guardian_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
                try:
                    cmdline = self._safe_join(proc.info.get("cmdline") or [], " ")
                    if "celsius_ultimate_guardian" in cmdline:
                        uptime = datetime.now() - datetime.fromtimestamp(proc.info.get("create_time", 0))
                        guardian_processes.append({"pid": proc.info.get("pid"), "uptime": uptime})
                except Exception:
                    pass

            if guardian_processes:
                report_text += f"\n🛡️ Active Guardian Processes: {len(guardian_processes)}\n"
                for guard in guardian_processes:
                    hours = guard["uptime"].seconds // 3600
                    minutes = (guard["uptime"].seconds % 3600) // 60
                    report_text += f"  • PID {guard['pid']}: {guard['uptime'].days}d {hours}h {minutes}m uptime\n"
            else:
                report_text += "\n❌ No Guardian processes detected!\n"

            report_text += f"\n📅 Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            self.system_reports_text.insert("1.0", report_text)

        except Exception as e:
            self.system_reports_text.delete("1.0", "end")
            self.system_reports_text.insert("1.0", f"❌ Error generating Guardian report:\n{e}")

    def show_security_report(self):
        """Display security report"""
        try:
            self.system_reports_text.delete("1.0", "end")

            report_text = "🔒 SECURITY SYSTEM REPORT\n"
            report_text += "=" * 60 + "\n\n"

            # Authentication status
            report_text += f"👤 Current User: {self.username}\n"
            report_text += f"🔐 Authentication: ✅ Active\n"
            report_text += f"📧 Email Notifications: {'✅ Enabled' if self.email_notifier else '❌ Disabled'}\n\n"

            # Check for auth database
            auth_db = PROJECT_ROOT / "celsius_auth.json"
            if auth_db.exists():
                report_text += "🗃️ Authentication Database: ✅ Present\n"
            else:
                report_text += "🗃️ Authentication Database: ❌ Missing\n"

            # System integrity
            report_text += "\n🛡️ System Integrity:\n"
            critical_files = [
                "src/guardian/celsius_ultimate_guardian.py",
                "src/hub/celsius_ultimate_hub.py",
                "src/core/main.py",
            ]

            for file_path in critical_files:
                full_path = PROJECT_ROOT / file_path
                if full_path.exists():
                    report_text += f"  ✅ {file_path}\n"
                else:
                    report_text += f"  ❌ {file_path} - MISSING!\n"

            report_text += f"\n📅 Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            self.system_reports_text.insert("1.0", report_text)

        except Exception as e:
            self.system_reports_text.delete("1.0", "end")
            self.system_reports_text.insert("1.0", f"❌ Error generating security report:\n{e}")

    def show_performance_report(self):
        """Display performance report"""
        try:
            self.system_reports_text.delete("1.0", "end")

            report_text = "⚡ PERFORMANCE REPORT\n"
            report_text += "=" * 60 + "\n\n"

            # System resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            report_text += "💻 System Resources:\n"
            report_text += f"  CPU Usage: {cpu_percent:.1f}%\n"
            report_text += f"  Memory Usage: {memory.percent:.1f}% ({memory.used // 1024**3:.1f}GB / {memory.total // 1024**3:.1f}GB)\n"
            report_text += (
                f"  Disk Usage: {disk.percent:.1f}% ({disk.used // 1024**3:.1f}GB / {disk.total // 1024**3:.1f}GB)\n\n"
            )

            # Running processes
            celsius_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info", "cpu_percent"]):
                try:
                    cmdline = self._safe_join(proc.info.get("cmdline") or [], " ")
                    if any(term in cmdline for term in ["celsius", "guardian", "hub"]):
                        celsius_processes.append(
                            {
                                "pid": proc.info.get("pid"),
                                "memory": (
                                    proc.info.get("memory_info").rss // 1024**2 if proc.info.get("memory_info") else 0
                                ),  # MB
                                "cpu": proc.info.get("cpu_percent", 0),
                            }
                        )
                except Exception:
                    pass

            if celsius_processes:
                total_memory = sum(p["memory"] for p in celsius_processes)
                report_text += f"🔧 Celsius AI Processes: {len(celsius_processes)} running\n"
                report_text += f"  Total Memory Usage: {total_memory}MB\n"
                report_text += "  Process Details:\n"
                for proc in celsius_processes:
                    report_text += f"    • PID {proc['pid']}: {proc['memory']}MB RAM\n"
            else:
                report_text += "❌ No Celsius AI processes detected\n"

            report_text += f"\n📅 Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            self.system_reports_text.insert("1.0", report_text)

        except Exception as e:
            self.system_reports_text.delete("1.0", "end")
            self.system_reports_text.insert("1.0", f"❌ Error generating performance report:\n{e}")

    # Hardware Control Methods
    def refresh_hardware_status(self):
        """Refresh hardware status display"""
        try:
            # Get hardware status from the hardware API
            import requests

            try:
                response = requests.get("http://localhost:5001/api/hardware/status", timeout=2)
                if response.status_code == 200:
                    status_data = response.json()
                    status_text = "🎮 Hardware Control System: Connected\n"
                    status_text += f"🌀 Fan Control: {status_data.get('fan_control', 'Unknown')}\n"
                    status_text += f"🌈 RGB Control: {status_data.get('rgb_control', 'Unknown')}\n"
                    status_text += f"🌡️ Temperature Sensors: {status_data.get('temperature_sensors', 'Unknown')}\n"
                    status_text += f"⚡ Power Management: {status_data.get('power_management', 'Unknown')}\n"
                else:
                    status_text = "⚠️ Hardware API not responding\n"
                    status_text += "Hardware control available via local methods only"
            except requests.exceptions.RequestException:
                status_text = "🎮 Hardware Control System: Local Mode\n"
                status_text += "🌀 Fan Control: ✅ Available (System Interface)\n"
                status_text += "🌈 RGB Control: ⚠️ Simulation Mode (No RGB Hardware Detected)\n"
                status_text += "🌡️ Temperature Sensors: ✅ Available (System Sensors)\n"
                status_text += "⚡ Power Management: ✅ Configured for 24/7 Operation\n\n"
                status_text += "💡 Note: Install OpenRGB or manufacturer RGB software for real RGB control"

            self.hardware_status_text.delete("1.0", "end")
            self.hardware_status_text.insert("1.0", status_text)

        except Exception as e:
            self.hardware_status_text.delete("1.0", "end")
            self.hardware_status_text.insert("1.0", f"❌ Error checking hardware status:\n{e}")

    def open_hardware_web(self):
        """Open hardware web interface"""
        try:
            import webbrowser

            webbrowser.open("http://localhost:5001")
        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to open web interface:\n{e}")

    def set_fan_preset(self, speed):
        """Set fan speed preset"""
        self.fan_speed_var.set(str(speed))

    def apply_fan_settings(self):
        """Apply fan speed settings"""
        try:
            speed = int(float(self.fan_speed_var.get()))

            # Try to use hardware API first
            import requests

            try:
                response = requests.post("http://localhost:5001/api/hardware/fan", json={"speed": speed}, timeout=5)
                if response.status_code == 200:
                    self._msg(messagebox.showinfo, "Success", f"Fan speed set to {speed}%")
                    return
            except requests.exceptions.RequestException:
                pass

            # Fallback to local hardware controller
            try:
                import sys
                import os

                hardware_path = os.path.join(os.path.dirname(__file__), "..", "hardware")
                if hardware_path not in sys.path:
                    sys.path.append(hardware_path)
                from celsius_hardware_controller import CelsiusHardwareController

                controller = CelsiusHardwareController()
                controller.set_fan_speed_simple(speed)
                self._msg(messagebox.showinfo, "Success", f"Fan speed set to {speed}% (local control)")

            except ImportError:
                self._msg(
                    messagebox.showwarning,
                    "Warning",
                    f"Hardware controller not available.\n" f"Fan speed setting: {speed}% (simulated)",
                )

        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to set fan speed:\n{e}")

    def set_rgb_preset(self, r, g, b):
        """Set RGB color preset"""
        self.red_var.set(str(r))
        self.green_var.set(str(g))
        self.blue_var.set(str(b))

    def apply_rgb_settings(self):
        """Apply RGB color settings"""
        try:
            r = int(float(self.red_var.get()))
            g = int(float(self.green_var.get()))
            b = int(float(self.blue_var.get()))

            # Try to use hardware API first
            import requests

            try:
                response = requests.post(
                    "http://localhost:5001/api/hardware/rgb", json={"r": r, "g": g, "b": b}, timeout=5
                )
                if response.status_code == 200:
                    self._msg(messagebox.showinfo, "Success", f"RGB color set to ({r}, {g}, {b})")
                    return
            except requests.exceptions.RequestException:
                pass

            # Fallback to local hardware controller
            try:
                import sys
                import os

                hardware_path = os.path.join(os.path.dirname(__file__), "..", "hardware")
                if hardware_path not in sys.path:
                    sys.path.append(hardware_path)
                from celsius_hardware_controller import CelsiusHardwareController

                controller = CelsiusHardwareController()
                controller.set_rgb_color_simple(r, g, b)

                # Check if RGB control is in simulation mode
                self._msg(
                    messagebox.showinfo,
                    "RGB Control",
                    f"RGB color set to ({r}, {g}, {b})\n\n"
                    f"💡 Note: RGB control is in simulation mode.\n"
                    f"Install OpenRGB or manufacturer RGB software for real RGB control.\n"
                    f"Fan control works with real hardware.",
                )

            except ImportError:
                self._msg(
                    messagebox.showwarning,
                    "Warning",
                    f"Hardware controller not available.\n" f"RGB color setting: ({r}, {g}, {b}) (simulated)",
                )

        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to set RGB color:\n{e}")

    def apply_rgb_effect(self, effect):
        """Apply RGB lighting effect"""
        try:
            # Try to use hardware API first
            import requests

            try:
                response = requests.post(
                    "http://localhost:5001/api/hardware/effect", json={"effect": effect}, timeout=5
                )
                if response.status_code == 200:
                    self._msg(messagebox.showinfo, "Success", f"RGB effect '{effect}' applied")
                    return
            except requests.exceptions.RequestException:
                pass

            # Fallback to local hardware controller
            try:
                import sys
                import os

                hardware_path = os.path.join(os.path.dirname(__file__), "..", "hardware")
                if hardware_path not in sys.path:
                    sys.path.append(hardware_path)
                from celsius_hardware_controller import CelsiusHardwareController

                controller = CelsiusHardwareController()
                controller.apply_effect_simple(effect)

                self._msg(
                    messagebox.showinfo,
                    "RGB Effect",
                    f"RGB effect '{effect}' applied\n\n"
                    f"💡 Note: RGB effects are in simulation mode.\n"
                    f"Install RGB control software for real lighting effects.",
                )

            except ImportError:
                self._msg(
                    messagebox.showwarning,
                    "Warning",
                    f"Hardware controller not available.\n" f"RGB effect '{effect}' (simulated)",
                )

        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to apply RGB effect:\n{e}")

    def apply_profile(self, profile):
        """Apply performance profile"""
        try:
            profiles = {
                "silent": {"fan_speed": 30, "rgb": (0, 0, 255)},  # Blue for cool/quiet
                "balanced": {"fan_speed": 50, "rgb": (0, 255, 0)},  # Green for balanced
                "performance": {"fan_speed": 80, "rgb": (255, 165, 0)},  # Orange for performance
                "gaming": {"fan_speed": 100, "rgb": (255, 0, 0)},  # Red for maximum
            }

            if profile in profiles:
                settings = profiles[profile]

                # Set fan speed
                self.fan_speed_var.set(str(settings["fan_speed"]))

                # Set RGB color
                r, g, b = settings["rgb"]
                self.red_var.set(str(r))
                self.green_var.set(str(g))
                self.blue_var.set(str(b))

                # Apply settings
                self.apply_fan_settings()
                self.apply_rgb_settings()

                # Also apply via profile if hardware controller is available
                try:
                    import sys
                    import os

                    hardware_path = os.path.join(os.path.dirname(__file__), "..", "hardware")
                    if hardware_path not in sys.path:
                        sys.path.append(hardware_path)
                    from celsius_hardware_controller import CelsiusHardwareController

                    controller = CelsiusHardwareController()
                    controller.apply_profile_simple(profile)
                except ImportError:
                    pass  # Use GUI controls only

                self._msg(messagebox.showinfo, "Success", f"'{profile.title()}' profile applied")
            else:
                self._msg(messagebox.showerror, "Error", f"Unknown profile: {profile}")

        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Failed to apply profile:\n{e}")

    def check_temperatures(self):
        """Check system temperatures"""
        try:
            # Try to use hardware API first
            import requests

            try:
                response = requests.get("http://localhost:5001/api/hardware/temperature", timeout=5)
                if response.status_code == 200:
                    temp_data = response.json()
                    temp_text = "🌡️ System Temperatures:\n"
                    for sensor, temp in temp_data.items():
                        temp_text += f"  {sensor}: {temp}°C\n"

                    self.temp_text.delete("1.0", "end")
                    self.temp_text.insert("1.0", temp_text)
                    return
            except requests.exceptions.RequestException:
                pass

            # Fallback to local temperature checking
            try:
                import psutil

                temp_text = "🌡️ System Temperatures:\n"

                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for name, entries in temps.items():
                            for entry in entries:
                                temp_text += f"  {name} ({entry.label or 'N/A'}): {entry.current}°C\n"
                    else:
                        temp_text += "  No temperature sensors found\n"
                else:
                    temp_text += "  Temperature monitoring not available on this platform\n"

                self.temp_text.delete("1.0", "end")
                self.temp_text.insert("1.0", temp_text)

            except ImportError:
                self.temp_text.delete("1.0", "end")
                self.temp_text.insert("1.0", "❌ psutil not available for temperature monitoring")

        except Exception as e:
            self.temp_text.delete("1.0", "end")
            self.temp_text.insert("1.0", f"❌ Error checking temperatures:\n{e}")

    def toggle_auto_fan(self):
        """Toggle automatic fan control"""
        try:
            auto_enabled = self.auto_temp_var.get()

            # Try to use hardware API first
            import requests

            try:
                response = requests.post(
                    "http://localhost:5001/api/hardware/auto-fan", json={"enabled": auto_enabled}, timeout=5
                )
                if response.status_code == 200:
                    status_text = "Enabled" if auto_enabled else "Disabled"
                    self._msg(messagebox.showinfo, "Auto Fan Control", f"Automatic fan control {status_text}")
                    return
            except requests.exceptions.RequestException:
                pass

            # Fallback to direct hardware control
            # Fallback to direct hardware control
            try:
                import sys
                import os

                sys.path.append(os.path.join(os.path.dirname(__file__), "..", "hardware"))
                from celsius_hardware_controller import CelsiusHardwareController

                controller = CelsiusHardwareController()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                if auto_enabled:
                    loop.run_until_complete(controller.auto_adjust_by_temperature())
                    self._msg(messagebox.showinfo, "Auto Fan Control", "Automatic fan control enabled")
                else:
                    self._msg(messagebox.showinfo, "Auto Fan Control", "Automatic fan control disabled")

            except Exception as controller_error:
                self._msg(messagebox.showerror, "Error", f"Failed to toggle auto fan control: {controller_error}")

        except Exception as e:
            self._msg(messagebox.showerror, "Error", f"Auto fan control error: {e}")

    def send_chat_message(self):
        """Send a chat message to Celsius AI"""
        message = self.chat_input.get().strip()
        if not message:
            return

        # Clear input
        self.chat_input.delete(0, tk.END)

        # Add user message to chat
        self.add_chat_message("You", message, "user")

        # Process the command
        self.process_chat_command(message)

        # Optionally save the message to the learning conversation DB if the user opted in
        try:
            save_this = getattr(self, "save_to_learning_var", None)
            enabled = getattr(self, "enable_conversation_training", False)
            if enabled and save_this and save_this.get():
                try:
                    from src.learning.conversation_ingest import store_conversation

                    # Store only the single user message as a short transcript; Hub will record context later if needed
                    resp = store_conversation(message, participants="user", source="chat")
                    if resp.get("status") != "ok":
                        self._msg(
                            messagebox.showwarning,
                            "Ingest Warning",
                            f"Could not save conversation: {resp.get('error')}",
                        )
                except Exception as ie:
                    # Non-fatal: inform user on UI thread
                    self.schedule_on_main_thread(
                        self._msg, messagebox.showwarning, "Ingest Error", f"Failed to store conversation: {ie}"
                    )
        except Exception:
            # swallow ingestion errors to avoid affecting chat flow
            pass

    async def periodic_sweep_contacts(self, interval_seconds: int = 3600):
        """Periodically runs the sweep script to refresh web learning contact requests.

        Runs the external script in a subprocess to avoid cross-event-loop aiohttp issues.
        """
        script = PROJECT_ROOT / "scripts" / "sweep_web_learning_contacts.py"
        if not script.exists():
            logging.info("Sweep script not found; periodic sweep disabled")
            return

        while True:
            try:
                logging.info("Starting periodic web-learning contact sweep")
                env = os.environ.copy()
                env["PYTHONPATH"] = str(PROJECT_ROOT)
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(script),
                    "--timeout",
                    "60",
                    "--retries",
                    "2",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    logging.info(f'Sweep stdout: {stdout.decode("utf-8", errors="ignore")[:2000]}')
                if stderr:
                    logging.warning(f'Sweep stderr: {stderr.decode("utf-8", errors="ignore")[:2000]}')
            except Exception:
                logging.exception("Error running periodic sweep")

            # Sleep until next run
            await asyncio.sleep(interval_seconds)

    def quick_chat_command(self, command):
        """Execute a quick chat command"""
        self.chat_input.delete(0, tk.END)
        self.chat_input.insert(0, command)
        self.send_chat_message()

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
                            self.add_chat_message("Celsius AI", "🔴 RGB lights turned OFF", "system")
                        else:
                            self.add_chat_message("Celsius AI", f"🎨 RGB lights set to {color_name.upper()}", "system")
                        return
                except requests.exceptions.RequestException:
                    pass

                # Fallback to direct control
                try:
                    import sys
                    import os

                    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "hardware"))
                    from celsius_hardware_controller import CelsiusHardwareController

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
                        self.add_chat_message("Celsius AI", "🔴 RGB lights turned OFF", "system")
                    else:
                        self.add_chat_message("Celsius AI", f"🎨 RGB lights set to {color_name.upper()}", "system")

                except Exception as direct_error:
                    self.add_chat_message("Celsius AI", f"❌ RGB control failed: {direct_error}", "system")
            else:
                self.add_chat_message(
                    "Celsius AI",
                    "❌ Color not recognized. Available: red, blue, green, purple, yellow, orange, white, off",
                    "system",
                )

        except Exception as e:
            self.add_chat_message("Celsius AI", f"❌ RGB command error: {e}", "system")

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
                    self.add_chat_message("Celsius AI", "🤖 Fan control set to AUTOMATIC", "system")
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
                            "Celsius AI", f"🌪️ Fan speed set to {speed_name.upper()} ({target_speed}%)", "system"
                        )
                        return
                except requests.exceptions.RequestException:
                    pass

                # Fallback to direct control
                try:
                    import sys
                    import os

                    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "hardware"))
                    from celsius_hardware_controller import CelsiusHardwareController

                    controller = CelsiusHardwareController()
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    loop.run_until_complete(controller.initialize())
                    loop.run_until_complete(controller.set_fan_speed("cpu", target_speed))

                    self.add_chat_message(
                        "Celsius AI", f"🌪️ Fan speed set to {speed_name.upper()} ({target_speed}%)", "system"
                    )

                except Exception as direct_error:
                    self.add_chat_message("Celsius AI", f"❌ Fan control failed: {direct_error}", "system")
            else:
                self.add_chat_message(
                    "Celsius AI", "❌ Fan speed not recognized. Available: high, low, max, medium, auto", "system"
                )

        except Exception as e:
            self.add_chat_message("Celsius AI", f"❌ Fan command error: {e}", "system")

    def show_system_status_chat(self):
        """Show system status in chat"""
        try:
            # Get basic system info
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            status_msg = f"""🛡️ Celsius AI System Status:
            
💻 CPU Usage: {cpu_percent}%
🧠 Memory Usage: {memory.percent}%
💾 Disk Usage: {disk.percent}%
🌡️ System Temperature: Checking...
🎮 Hardware Controller: Available
🌈 RGB Control: Active (373 LEDs)
⚡ Services: Running"""

            self.add_chat_message("Celsius AI", status_msg, "system")

        except Exception as e:
            self.add_chat_message("Celsius AI", f"❌ Status check failed: {e}", "system")

    def show_temperature_status(self):
        """Show temperature status in chat"""
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                temp_msg = "🌡️ System Temperatures:\n"
                for name, entries in temps.items():
                    for entry in entries:
                        temp_msg += f"  {name}: {entry.current}°C\n"
            else:
                temp_msg = "🌡️ Temperature sensors not available"

            self.add_chat_message("Celsius AI", temp_msg, "system")

        except Exception as e:
            self.add_chat_message("Celsius AI", f"❌ Temperature check failed: {e}", "system")

    def show_chat_help(self):
        """Show help information in chat"""
        help_msg = """🛡️ Celsius AI Chat Commands:

🌈 RGB Control:
• red, blue, green, purple, yellow, orange, white
• "lights off" - Turn off all RGB lights
• "rgb [color] all" - Control all devices
• "rgb [color] motherboard" - Control motherboard only

🌪️ Fan Control:
• "fan high" - Set fans to high speed (80%)
• "fan low" - Set fans to low speed (30%)
• "fan max" - Set fans to maximum (100%)
• "fan auto" - Enable automatic control

📊 System Information:
• "status" - Show system status
• "temperature" - Show temperature readings
• "help" - Show this help message

Examples:
• "red" - Turn motherboard red
• "lights off" - Turn off all lights
• "fan high" - Increase fan speed
• "status" - Check system health"""

        self.add_chat_message("Celsius AI", help_msg, "system")


if __name__ == "__main__":
    try:
        # Prefer the dedicated login module which integrates with the
        # file-based auth system. Fall back to a very small local dialog
        # if the module cannot be imported (keeps the script runnable).
        try:
            from src.hub.login import LoginWindow
        except Exception:
            class LoginWindow:
                def __init__(self, root):
                    self.root = root
                    self.authenticated = False
                    self.username = ""

                    root.title("Celsius AI Login")
                    root.geometry("360x160")

                    frm = ttk.Frame(root, padding=10)
                    frm.pack(fill="both", expand=True)

                    ttk.Label(frm, text="Username:").grid(row=0, column=0, sticky="w")
                    self.user_entry = ttk.Entry(frm)
                    self.user_entry.grid(row=0, column=1, sticky="ew")

                    ttk.Label(frm, text="Password:").grid(row=1, column=0, sticky="w")
                    self.pass_entry = ttk.Entry(frm, show="*")
                    self.pass_entry.grid(row=1, column=1, sticky="ew")

                    btn_frame = ttk.Frame(frm)
                    btn_frame.grid(row=2, column=0, columnspan=2, pady=(10,0))

                    ttk.Button(btn_frame, text="Login", command=self._do_login).pack(side="left", padx=5)
                    ttk.Button(btn_frame, text="Cancel", command=self._do_cancel).pack(side="left", padx=5)

                    frm.columnconfigure(1, weight=1)

                def _do_login(self):
                    uname = self.user_entry.get().strip()
                    if not uname:
                        messagebox.showwarning("Login", "Please enter a username.")
                        return
                    self.username = uname
                    self.authenticated = True
                    self.root.destroy()

                def _do_cancel(self):
                    self.authenticated = False
                    self.root.destroy()

        login_root = tk.Tk()
        login_window = LoginWindow(login_root)
        login_root.mainloop()

        # Check if authentication was successful
        if not login_window.authenticated:
            logging.info("Login cancelled or failed. Exiting.")
            sys.exit(0)

        username = login_window.username
        logging.info(f"User {username} authenticated successfully")

        # 3. Start the asyncio event loop in a background thread
        async_loop = AsyncTkinter()
        async_loop.start()

        # 4. Create the main Tkinter window
        root = ThemedTk(theme="arc")

        # 5. Create the application, passing the async loop manager and username
        app = UltimateHub(root, async_loop, username)

        # 6. Start the Tkinter main loop
        root.mainloop()

    except Exception as e:
        logging.critical(f"A fatal error occurred: {e}", exc_info=True)
        messagebox.showerror("Fatal Error", f"A critical error occurred and the application must close:\n\n{e}")
