"""
UI compatibility wrapper for incremental refactor.

This module provides thin forwarding wrappers for the Hub UI builder
functions while we move UI code out of `celsius_ultimate_hub.py`.

The wrappers defer attribute lookup until call time so importing this
module doesn't force a hard dependency on all symbols being present at
import time.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
import tkinter as tk
from tkinter import ttk, messagebox
import logging


def create_admin_tab(hub: Any) -> None:
    """Create the Administration tab widgets for the given hub instance.

    This function mirrors the original `UltimateHub.create_admin_tab` method
    but lives here so the UI can be moved incrementally without breaking
    callers that import the legacy module.
    """
    frame = hub.tab_admin

    # System Maintenance
    maintenance_frame = ttk.LabelFrame(frame, text="System Maintenance", padding=10)
    maintenance_frame.pack(fill="x", padx=10, pady=5)

    ttk.Button(
        maintenance_frame,
        text="Perform System Cleanup & Backup",
        command=hub.perform_cleanup_action,
    ).pack(pady=5, fill="x", padx=5)
    ttk.Button(maintenance_frame, text="Clear Old Logs", command=hub.clear_old_logs).pack(pady=5, fill="x", padx=5)
    ttk.Button(maintenance_frame, text="Vacuum Databases", command=hub.vacuum_databases).pack(pady=5, fill="x", padx=5)

    # Database Management
    db_frame = ttk.LabelFrame(frame, text="Database Management", padding=10)
    db_frame.pack(fill="x", padx=10, pady=5)

    ttk.Button(db_frame, text="View Database Stats", command=hub.view_db_stats).pack(pady=5, fill="x", padx=5)

    ttk.Button(db_frame, text="Export Activity Log", command=hub.export_activity_log).pack(pady=5, fill="x", padx=5)
    ttk.Button(db_frame, text="Initialize Databases", command=lambda: hub.schedule_async_task(hub.init_db())).pack(
        pady=5, fill="x", padx=5
    )
    ttk.Button(db_frame, text="Review Pending AI Training Items", command=hub.review_pending_ai_training).pack(
        pady=5, fill="x", padx=5
    )
    ttk.Button(
        db_frame,
        text="Fetch from AI Providers (now)",
        command=lambda: hub.schedule_async_task(hub.fetch_from_providers()),
    ).pack(pady=5, fill="x", padx=5)

    ttk.Button(db_frame, text="Upload Authorization Form", command=hub.open_upload_authorization_dialog).pack(
        pady=5, fill="x", padx=5
    )
    ttk.Button(db_frame, text="Review Authorization Forms", command=hub.open_review_authorizations_dialog).pack(
        pady=5, fill="x", padx=5
    )
    # Download blank authorization form (admin quick-action)
    ttk.Button(
        db_frame,
        text="Download Blank Authorization",
        command=hub.download_blank_authorization_form,
    ).pack(pady=5, fill="x", padx=5)

    ttk.Button(
        db_frame, text="View Web Learning Contact Requests", command=hub.open_web_learning_contacts_embedded
    ).pack(pady=5, fill="x", padx=5)
    # Import web-learner discovered alternative sources into ingestion candidates
    ttk.Button(
        db_frame,
        text="Import Web Learning Alternatives",
        command=lambda: hub.import_web_learning_alternatives(),
    ).pack(pady=5, fill="x", padx=5)
    ttk.Button(
        db_frame,
        text="Prepare Outreach CSV",
        command=lambda: hub.schedule_async_task(hub._generate_outreach_csv()),
    ).pack(pady=5, fill="x", padx=5)

    # System Information
    info_frame = ttk.LabelFrame(frame, text="System Information", padding=10)
    info_frame.pack(fill="both", expand=True, padx=10, pady=5)

    hub.system_info_text = tk.Text(
        info_frame,
        wrap="word",
        height=10,
        bg=hub.style.lookup("TFrame", "background"),
        fg=hub.style.lookup("TLabel", "foreground"),
    )
    hub.system_info_text.pack(fill="both", expand=True)

    info = f"""Celsius AI - Ultimate Hub
        
    Project Root: {Path(hub.PROJECT_ROOT) if hasattr(hub, 'PROJECT_ROOT') else Path('.')}
    Database Path: {getattr(hub, 'db_path', 'unknown')}
    Python Version: {sys.version.split()[0]}
    Platform: {sys.platform}

    Services Configured: {len(getattr(hub, 'services', []) or [])}
    Active Processes: {len(getattr(hub, 'processes', {}) or {})}
    """
    hub.system_info_text.insert("1.0", info)

    # Email Notifier Status (Admin)
    email_frame = ttk.LabelFrame(frame, text="Email Notifier Status", padding=10)
    email_frame.pack(fill="x", padx=10, pady=5)

    retry_count = getattr(hub, "_email_retry_count", 0)
    last_error = getattr(hub, "_email_last_error", "None")

    lbl = ttk.Label(email_frame, text=f"Retry Count: {retry_count}")
    lbl.pack(side="left", padx=5)

    lbl2 = ttk.Label(email_frame, text=f"Last Error: {last_error}")
    lbl2.pack(side="left", padx=10)

    # expose these labels for live updates from the hub
    try:
        hub._email_admin_retry_lbl = lbl
        hub._email_admin_last_error_lbl = lbl2
    except Exception:
        pass

    def _reinit_now():
        try:
            hub.schedule_on_main_thread(lambda: hub._msg(messagebox.showinfo, "Re-init", "Attempting email re-init..."))
            hub.async_loop.create_task(hub.ensure_email_notifier(force=True))
        except Exception:
            logging.exception("Failed to schedule email re-init")

    ttk.Button(email_frame, text="Re-init Email Now", command=_reinit_now).pack(side="right", padx=5)

    # Ingestion review section (Admin)
    ingest_frame = ttk.LabelFrame(frame, text="Ingestion Review (Admin)", padding=10)
    ingest_frame.pack(fill="both", expand=True, padx=10, pady=5)

    cols = ("#", "Source", "Title", "Added")
    hub.ingestion_tree = ttk.Treeview(ingest_frame, columns=cols, show="headings", height=6)
    for c in cols:
        hub.ingestion_tree.heading(c, text=c)
        hub.ingestion_tree.column(c, width=200)

    ingest_scroll = ttk.Scrollbar(ingest_frame, orient="vertical", command=hub.ingestion_tree.yview)
    hub.ingestion_tree.configure(yscrollcommand=ingest_scroll.set)
    ingest_scroll.pack(side="right", fill="y")
    hub.ingestion_tree.pack(fill="both", expand=True)

    # Show path and loaded count for ingestion candidates to help debugging
    try:
        cand_path = hub._ingestion_candidates_path()
    except Exception:
        cand_path = "data/ingestion_candidates.json"

    hub.ingestion_status_label = ttk.Label(ingest_frame, text=f"Candidates file: {cand_path}")
    hub.ingestion_status_label.pack(fill="x", padx=10, pady=(4, 6))

    # Immediately load any existing ingestion candidates so the admin sees them
    # without having to press Refresh.
    try:
        hub.load_ingestion_candidates()
    except Exception:
        logging.exception("Failed to auto-load ingestion candidates")

    ingest_controls = ttk.Frame(ingest_frame)
    ingest_controls.pack(fill="x", pady=5)
    ttk.Button(ingest_controls, text="Refresh", command=hub.load_ingestion_candidates).pack(side="left", padx=5)
    ttk.Button(ingest_controls, text="Approve", command=hub.approve_selected_ingestion).pack(side="left", padx=5)
    ttk.Button(ingest_controls, text="Approve All", command=hub.approve_all_ingestion).pack(side="left", padx=5)
    ttk.Button(ingest_controls, text="Reject", command=hub.reject_selected_ingestion).pack(side="left", padx=5)

    # Seed ingestion (Project Gutenberg) quick action
    seed_frame = ttk.Frame(ingest_frame)
    seed_frame.pack(fill="x", pady=5)
    ttk.Button(seed_frame, text="Seed Project Gutenberg (sample)", command=hub.seed_gutenberg_samples).pack(side="left", padx=5)


def open_web_learning_contacts_embedded(hub: Any) -> None:
    """Open an embedded contacts viewer for the given hub instance."""
    return hub.open_web_learning_contacts_embedded()


__all__ = ["create_admin_tab", "open_web_learning_contacts_embedded"]


def create_reports_tab(hub: Any) -> None:
    """Create the Reports tab widgets for the given hub instance.

    Mirrors the original `UltimateHub.create_reports_tab` but accepts the
    hub instance so the UI can be moved incrementally.
    """
    frame = hub.tab_reports

    # Create a scrollable canvas for the whole tab
    canvas_bg = hub.style.lookup("TFrame", "background") or frame.cget("bg")
    canvas = tk.Canvas(frame, highlightthickness=0, bg=canvas_bg)
    vscroll = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)

    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_canvas_config(e):
        try:
            canvas.itemconfig(window_id, width=e.width)
            canvas.configure(scrollregion=canvas.bbox("all"))
        except Exception:
            pass

    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", _on_canvas_config)

    canvas.configure(yscrollcommand=vscroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    vscroll.pack(side="right", fill="y")

    # Learning Reports Section (inside inner frame)
    learning_frame = ttk.LabelFrame(inner, text="Learning Reports", padding=10)
    learning_frame.pack(fill="x", padx=10, pady=5)

    # Learning reports controls
    controls_frame = ttk.Frame(learning_frame)
    controls_frame.pack(fill="x", pady=5)

    ttk.Button(controls_frame, text="Refresh Reports", command=hub.refresh_learning_reports).pack(side="left", padx=5)
    ttk.Button(controls_frame, text="Open Reports Folder", command=hub.open_reports_folder).pack(side="left", padx=5)
    ttk.Button(controls_frame, text="Generate New Report", command=hub.generate_learning_report).pack(
        side="left", padx=5
    )
    ttk.Button(controls_frame, text="Import Transcript", command=hub.open_import_dialog).pack(side="left", padx=5)

    # Learning reports display (text + scrollbar)
    hub.learning_reports_text = tk.Text(
        learning_frame,
        wrap="word",
        height=12,
        bg=hub.style.lookup("TFrame", "background"),
        fg=hub.style.lookup("TLabel", "foreground"),
    )
    scrollbar_lr = ttk.Scrollbar(learning_frame, orient="vertical", command=hub.learning_reports_text.yview)
    hub.learning_reports_text.configure(yscrollcommand=scrollbar_lr.set)
    scrollbar_lr.pack(side="right", fill="y")
    hub.learning_reports_text.pack(fill="both", expand=True)

    # Hourly summary small display
    hourly_frame = ttk.LabelFrame(inner, text="Latest Hourly Summary", padding=8)
    hourly_frame.pack(fill="x", padx=10, pady=5)
    hub.hourly_summary_text = tk.Text(
        hourly_frame,
        height=4,
        wrap="word",
        bg=hub.style.lookup("TFrame", "background"),
        fg=hub.style.lookup("TLabel", "foreground"),
    )
    hub.hourly_summary_text.pack(fill="both", expand=True)

    # Hourly reports file list
    hourly_files_frame = ttk.LabelFrame(inner, text="Hourly Report Files", padding=8)
    hourly_files_frame.pack(fill="both", padx=10, pady=5)

    cols_hr = ("Filename", "Generated")
    hub.hourly_reports_tree = ttk.Treeview(hourly_files_frame, columns=cols_hr, show="headings", height=6)
    for c in cols_hr:
        hub.hourly_reports_tree.heading(c, text=c)
        hub.hourly_reports_tree.column(c, width=300 if c == "Filename" else 160)

    hr_scroll = ttk.Scrollbar(hourly_files_frame, orient="vertical", command=hub.hourly_reports_tree.yview)
    hub.hourly_reports_tree.configure(yscrollcommand=hr_scroll.set)
    hr_scroll.pack(side="right", fill="y")
    hub.hourly_reports_tree.pack(fill="both", expand=True)

    hr_controls = ttk.Frame(hourly_files_frame)
    hr_controls.pack(fill="x", pady=5)
    ttk.Button(hr_controls, text="Refresh Hourly Reports", command=hub.refresh_hourly_reports_list).pack(
        side="left", padx=5
    )
    ttk.Button(hr_controls, text="Open Reports Folder", command=hub.open_reports_folder).pack(side="left", padx=5)

    # System Reports Section (inside inner frame)
    system_frame = ttk.LabelFrame(inner, text="System Reports", padding=10)
    system_frame.pack(fill="both", expand=True, padx=10, pady=5)

    # System reports controls
    sys_controls_frame = ttk.Frame(system_frame)
    sys_controls_frame.pack(fill="x", pady=5)

    ttk.Button(sys_controls_frame, text="Guardian Report", command=hub.show_guardian_report).pack(side="left", padx=5)
    ttk.Button(sys_controls_frame, text="Security Report", command=hub.show_security_report).pack(side="left", padx=5)
    ttk.Button(sys_controls_frame, text="Performance Report", command=hub.show_performance_report).pack(
        side="left", padx=5
    )

    # System reports display
    hub.system_reports_text = tk.Text(
        system_frame,
        wrap="word",
        height=12,
        bg=hub.style.lookup("TFrame", "background"),
        fg=hub.style.lookup("TLabel", "foreground"),
    )
    scrollbar_sr = ttk.Scrollbar(system_frame, orient="vertical", command=hub.system_reports_text.yview)
    hub.system_reports_text.configure(yscrollcommand=scrollbar_sr.set)
    scrollbar_sr.pack(side="right", fill="y")
    hub.system_reports_text.pack(fill="both", expand=True)

    # Auto-refresh reports on tab creation
    try:
        hub.refresh_learning_reports()
    except Exception:
        pass
    try:
        hub.show_guardian_report()
    except Exception:
        pass


def create_monitoring_tab(hub: Any) -> None:
    """Create the Monitoring tab widgets for the given hub instance.

    Mirrors the original `UltimateHub.create_monitoring_tab` implementation.
    """
    frame = hub.tab_monitoring
    log_frame = ttk.LabelFrame(frame, text="Activity Log", padding=10)
    log_frame.pack(expand=True, fill="both", padx=10, pady=10)

    cols = ("Timestamp", "Service", "Action", "Details")
    hub.log_tree = ttk.Treeview(log_frame, columns=cols, show="headings")
    for col in cols:
        hub.log_tree.heading(col, text=col)
        hub.log_tree.column(col, width=150)

    hub.log_tree.column("Details", width=400)

    scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=hub.log_tree.yview)
    hub.log_tree.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    hub.log_tree.pack(expand=True, fill="both")


__all__.extend(["create_reports_tab", "create_monitoring_tab"])


def create_security_tab(hub: Any) -> None:
    """Create the Security tab widgets for the given hub instance.

    Mirrors the original `UltimateHub.create_security_tab`.
    """
    frame = hub.tab_security

    # Authentication Info
    auth_frame = ttk.LabelFrame(frame, text="Authentication Status", padding=10)
    auth_frame.pack(fill="x", padx=10, pady=5)

    ttk.Label(
        auth_frame, text="✅ System Access: Authenticated", font=("Helvetica", 10, "bold"), foreground="green"
    ).pack(pady=5)
    ttk.Label(auth_frame, text=f"User: {hub.username}", font=("Helvetica", 9)).pack()
    ttk.Label(
        auth_frame, text=f"Session Start: {hub._last_activity.strftime('%Y-%m-%d %H:%M:%S')}", font=("Helvetica", 9)
    ).pack()

    if getattr(hub, "email_notifier", None):
        ttk.Label(auth_frame, text="📧 Email Notifications: Enabled", font=("Helvetica", 9), foreground="green").pack()
    else:
        ttk.Label(
            auth_frame, text="📧 Email Notifications: Disabled", font=("Helvetica", 9), foreground="orange"
        ).pack()

    # Security Logs
    log_frame = ttk.LabelFrame(frame, text="Security Activity Log", padding=10)
    log_frame.pack(fill="both", expand=True, padx=10, pady=5)

    cols = ("Timestamp", "Event Type", "Details", "Status")
    hub.security_log_tree = ttk.Treeview(log_frame, columns=cols, show="headings", height=10)
    for col in cols:
        hub.security_log_tree.heading(col, text=col)
        hub.security_log_tree.column(col, width=150)

    scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=hub.security_log_tree.yview)
    hub.security_log_tree.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    hub.security_log_tree.pack(fill="both", expand=True)

    # Add sample security events
    try:
        hub.security_log_tree.insert(
            "",
            "end",
            values=(
                hub._last_activity.strftime("%Y-%m-%d %H:%M:%S"),
                "Login",
                "Hub initialized",
                "✅ Success",
            ),
        )
    except Exception:
        pass

    # Security Actions
    actions_frame = ttk.LabelFrame(frame, text="Security Actions", padding=10)
    actions_frame.pack(fill="x", padx=10, pady=5)

    ttk.Button(
        actions_frame,
        text="View Failed Login Attempts",
        command=lambda: hub._msg(messagebox.showinfo, "Security", "No failed login attempts recorded."),
    ).pack(side="left", padx=5)
    ttk.Button(actions_frame, text="Export Security Log", command=hub.export_security_log).pack(side="left", padx=5)
    ttk.Button(actions_frame, text="Clear Security Log", command=hub.clear_security_log).pack(side="left", padx=5)


__all__.append("create_security_tab")


def create_chat_tab(hub: Any) -> None:
    """Create the Chat tab UI for the given hub instance."""
    frame = hub.tab_chat

    # Main chat frame
    main_chat_frame = ttk.Frame(frame)
    main_chat_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Chat history display
    chat_frame = ttk.LabelFrame(main_chat_frame, text="💬 Chat with Celsius AI", padding="10")
    chat_frame.pack(fill="both", expand=True, pady=(0, 10))

    # Create chat display
    hub.chat_display = tk.Text(
        chat_frame, wrap=tk.WORD, height=20, bg="black", fg="cyan", font=("Consolas", 10), insertbackground="cyan"
    )
    hub.chat_display.pack(fill="both", expand=True, pady=(0, 10))

    # Add initial welcome message
    welcome_msg = """🛡️ Welcome to Celsius AI Chat Interface! 🛡️
        
Available Commands:
• RGB Control: "red", "blue", "green", "purple", "yellow", "orange", "white", "lights off"
• Fan Control: "fan high", "fan low", "fan max", "fan auto"
• System Status: "status", "temperature", "hardware status"
• Help: "help", "commands"

Examples:
> red                    # Turn motherboard RGB red
> lights off            # Turn off all RGB lights  
> fan high              # Set fans to high speed
> rgb purple motherboard # Set motherboard to purple
> status                # Show system status

Type your command below and press Enter to chat with Celsius AI!
========================================================================

"""
    hub.chat_display.insert(tk.END, welcome_msg)
    hub.chat_display.see(tk.END)

    # Input frame
    input_frame = ttk.Frame(main_chat_frame)
    input_frame.pack(fill="x")

    # Chat input
    ttk.Label(input_frame, text="Message:").pack(side="left", padx=(0, 5))
    hub.chat_input = ttk.Entry(input_frame, font=("Consolas", 10))
    hub.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 10))

    # Per-message opt-in checkbox to save this message to learning (only if global enabled)
    hub.save_to_learning_var = tk.BooleanVar(value=False)
    hub.save_to_learning_cb = ttk.Checkbutton(input_frame, text="Save to Learning", variable=hub.save_to_learning_var)
    hub.save_to_learning_cb.pack(side="right", padx=(0, 8))

    # Send button
    send_button = ttk.Button(input_frame, text="Send", command=hub.send_chat_message)
    send_button.pack(side="right")

    # Bind Enter key to send message
    hub.chat_input.bind("<Return>", lambda e: hub.send_chat_message())

    # Quick action buttons
    quick_actions_frame = ttk.LabelFrame(main_chat_frame, text="Quick Actions", padding="10")
    quick_actions_frame.pack(fill="x", pady=(10, 0))

    # RGB quick buttons
    rgb_quick_frame = ttk.Frame(quick_actions_frame)
    rgb_quick_frame.pack(fill="x", pady=(0, 5))
    ttk.Label(rgb_quick_frame, text="RGB:").pack(side="left", padx=(0, 10))

    for color in ["Red", "Blue", "Green", "Purple", "Orange", "White", "Off"]:
        command = color.lower() if color != "Off" else "lights off"
        ttk.Button(rgb_quick_frame, text=color, command=lambda c=command: hub.quick_chat_command(c)).pack(
            side="left", padx=2
        )

    # Fan quick buttons
    fan_quick_frame = ttk.Frame(quick_actions_frame)
    fan_quick_frame.pack(fill="x")
    ttk.Label(fan_quick_frame, text="Fans:").pack(side="left", padx=(0, 10))

    for fan_mode in ["High", "Low", "Max", "Auto"]:
        command = f"fan {fan_mode.lower()}"
        ttk.Button(fan_quick_frame, text=fan_mode, command=lambda c=command: hub.quick_chat_command(c)).pack(
            side="left", padx=2
        )

    # Conversation training opt-in (global)
    training_frame = ttk.Frame(main_chat_frame)
    training_frame.pack(fill="x", pady=(8, 0))
    hub.enable_conversation_training_var = tk.BooleanVar(value=False)

    def _on_toggle_training():
        hub.enable_conversation_training = bool(hub.enable_conversation_training_var.get())

    hub.enable_training_cb = ttk.Checkbutton(
        training_frame,
        text="Enable Conversation Training (opt-in)",
        variable=hub.enable_conversation_training_var,
        command=_on_toggle_training,
    )
    hub.enable_training_cb.pack(side="left", padx=5)


__all__.append("create_chat_tab")


def create_hardware_tab(hub: Any) -> None:
    """Create the Hardware tab UI for the given hub instance."""
    frame = hub.tab_hardware

    # Create scrollable frame
    canvas_bg = hub.style.lookup("TFrame", "background") or frame.cget("bg")
    hardware_canvas = tk.Canvas(frame, highlightthickness=0, bg=canvas_bg)
    hardware_scrollbar = ttk.Scrollbar(frame, orient="vertical", command=hardware_canvas.yview)
    hardware_scrollable_frame = ttk.Frame(hardware_canvas)

    hw_window_id = hardware_canvas.create_window((0, 0), window=hardware_scrollable_frame, anchor="nw")

    def _on_hw_canvas_config(e):
        try:
            hardware_canvas.itemconfig(hw_window_id, width=e.width)
            hardware_canvas.configure(scrollregion=hardware_canvas.bbox("all"))
        except Exception:
            pass

    hardware_scrollable_frame.bind(
        "<Configure>", lambda e: hardware_canvas.configure(scrollregion=hardware_canvas.bbox("all"))
    )
    hardware_canvas.bind("<Configure>", _on_hw_canvas_config)

    hardware_canvas.configure(yscrollcommand=hardware_scrollbar.set)

    # Title
    title_frame = ttk.LabelFrame(hardware_scrollable_frame, text="🎮 Hardware Control Center", padding="10")
    title_frame.pack(fill="x", padx=10, pady=5)

    # Status section
    status_frame = ttk.LabelFrame(hardware_scrollable_frame, text="System Status", padding="10")
    status_frame.pack(fill="x", padx=10, pady=5)

    hub.hardware_status_text = tk.Text(status_frame, height=6, wrap=tk.WORD)
    hub.hardware_status_text.pack(fill="x", pady=5)

    status_button_frame = ttk.Frame(status_frame)
    status_button_frame.pack(fill="x", pady=5)

    ttk.Button(status_button_frame, text="🔄 Refresh Status", command=hub.refresh_hardware_status).pack(
        side="left", padx=5
    )
    ttk.Button(status_button_frame, text="🌐 Open Web Interface", command=hub.open_hardware_web).pack(
        side="left", padx=5
    )

    # Fan Control section
    fan_frame = ttk.LabelFrame(hardware_scrollable_frame, text="🌀 Fan Control", padding="10")
    fan_frame.pack(fill="x", padx=10, pady=5)

    # Fan speed controls
    fan_control_frame = ttk.Frame(fan_frame)
    fan_control_frame.pack(fill="x", pady=5)

    ttk.Label(fan_control_frame, text="Fan Speed:").pack(side="left", padx=5)
    hub.fan_speed_var = tk.StringVar(value="50")
    fan_speed_scale = ttk.Scale(
        fan_control_frame, from_=0, to=100, variable=hub.fan_speed_var, orient="horizontal", length=200
    )
    fan_speed_scale.pack(side="left", padx=10)

    hub.fan_speed_label = ttk.Label(fan_control_frame, text="50%")
    hub.fan_speed_label.pack(side="left", padx=5)

    # Update label when scale changes
    def update_fan_label(*args):
        try:
            speed = int(float(hub.fan_speed_var.get()))
        except Exception:
            speed = 0
        hub.fan_speed_label.config(text=f"{speed}%")

    hub.fan_speed_var.trace("w", update_fan_label)

    # Fan preset buttons
    fan_preset_frame = ttk.Frame(fan_frame)
    fan_preset_frame.pack(fill="x", pady=5)

    ttk.Button(fan_preset_frame, text="Silent (30%)", command=lambda: hub.set_fan_preset(30)).pack(side="left", padx=5)
    ttk.Button(fan_preset_frame, text="Balanced (50%)", command=lambda: hub.set_fan_preset(50)).pack(
        side="left", padx=5
    )
    ttk.Button(fan_preset_frame, text="Performance (80%)", command=lambda: hub.set_fan_preset(80)).pack(
        side="left", padx=5
    )
    ttk.Button(fan_preset_frame, text="Max (100%)", command=lambda: hub.set_fan_preset(100)).pack(side="left", padx=5)

    # Apply fan settings button
    ttk.Button(fan_frame, text="🌀 Apply Fan Settings", command=hub.apply_fan_settings).pack(pady=10)

    # RGB Control section
    rgb_frame = ttk.LabelFrame(hardware_scrollable_frame, text="🌈 RGB Lighting Control", padding="10")
    rgb_frame.pack(fill="x", padx=10, pady=5)

    # Color selection
    color_frame = ttk.Frame(rgb_frame)
    color_frame.pack(fill="x", pady=5)

    ttk.Label(color_frame, text="RGB Color:").pack(side="left", padx=5)

    # Color sliders
    color_controls = ttk.Frame(color_frame)
    color_controls.pack(side="left", padx=10)

    # Red
    red_frame = ttk.Frame(color_controls)
    red_frame.pack(fill="x", pady=2)
    ttk.Label(red_frame, text="R:", width=2).pack(side="left")
    hub.red_var = tk.StringVar(value="255")
    ttk.Scale(red_frame, from_=0, to=255, variable=hub.red_var, orient="horizontal", length=100).pack(
        side="left", padx=5
    )
    hub.red_label = ttk.Label(red_frame, text="255", width=3)
    hub.red_label.pack(side="left")

    # Green
    green_frame = ttk.Frame(color_controls)
    green_frame.pack(fill="x", pady=2)
    ttk.Label(green_frame, text="G:", width=2).pack(side="left")
    hub.green_var = tk.StringVar(value="0")
    ttk.Scale(green_frame, from_=0, to=255, variable=hub.green_var, orient="horizontal", length=100).pack(
        side="left", padx=5
    )
    hub.green_label = ttk.Label(green_frame, text="0", width=3)
    hub.green_label.pack(side="left")

    # Blue
    blue_frame = ttk.Frame(color_controls)
    blue_frame.pack(fill="x", pady=2)
    ttk.Label(blue_frame, text="B:", width=2).pack(side="left")
    hub.blue_var = tk.StringVar(value="0")
    ttk.Scale(blue_frame, from_=0, to=255, variable=hub.blue_var, orient="horizontal", length=100).pack(
        side="left", padx=5
    )
    hub.blue_label = ttk.Label(blue_frame, text="0", width=3)
    hub.blue_label.pack(side="left")

    # Color preview
    hub.color_preview = tk.Frame(color_frame, width=50, height=50, bg="#FF0000")
    hub.color_preview.pack(side="left", padx=10)

    # Update color preview and labels
    def update_color(*args):
        try:
            r = int(float(hub.red_var.get()))
            g = int(float(hub.green_var.get()))
            b = int(float(hub.blue_var.get()))
        except Exception:
            r = g = b = 0
        color = f"#{r:02x}{g:02x}{b:02x}"
        try:
            hub.color_preview.config(bg=color)
        except Exception:
            pass
        try:
            hub.red_label.config(text=str(r))
            hub.green_label.config(text=str(g))
            hub.blue_label.config(text=str(b))
        except Exception:
            pass

    hub.red_var.trace("w", update_color)
    hub.green_var.trace("w", update_color)
    hub.blue_var.trace("w", update_color)

    # RGB preset buttons
    rgb_preset_frame = ttk.Frame(rgb_frame)
    rgb_preset_frame.pack(fill="x", pady=5)

    rgb_presets = [
        ("🔴 Red", (255, 0, 0)),
        ("🟢 Green", (0, 255, 0)),
        ("🔵 Blue", (0, 0, 255)),
        ("🟣 Purple", (128, 0, 128)),
        ("🟡 Yellow", (255, 255, 0)),
        ("🟠 Orange", (255, 165, 0)),
        ("⚪ White", (255, 255, 255)),
    ]

    for i, (name, (r, g, b)) in enumerate(rgb_presets):
        ttk.Button(rgb_preset_frame, text=name, command=lambda r=r, g=g, b=b: hub.set_rgb_preset(r, g, b)).pack(
            side="left", padx=2
        )

    # RGB effects
    effects_frame = ttk.Frame(rgb_frame)
    effects_frame.pack(fill="x", pady=5)

    ttk.Label(effects_frame, text="Effects:").pack(side="left", padx=5)
    ttk.Button(effects_frame, text="🌊 Wave", command=lambda: hub.apply_rgb_effect("wave")).pack(side="left", padx=5)
    ttk.Button(effects_frame, text="💫 Breathing", command=lambda: hub.apply_rgb_effect("breathing")).pack(
        side="left", padx=5
    )
    ttk.Button(effects_frame, text="🌈 Rainbow", command=lambda: hub.apply_rgb_effect("rainbow")).pack(
        side="left", padx=5
    )
    ttk.Button(effects_frame, text="⚡ Static", command=hub.apply_rgb_settings).pack(side="left", padx=5)

    # Performance Profiles section
    profile_frame = ttk.LabelFrame(hardware_scrollable_frame, text="⚡ Performance Profiles", padding="10")
    profile_frame.pack(fill="x", padx=10, pady=5)

    profile_button_frame = ttk.Frame(profile_frame)
    profile_button_frame.pack(fill="x", pady=5)

    ttk.Button(profile_button_frame, text="🔇 Silent Mode", command=lambda: hub.apply_profile("silent")).pack(
        side="left", padx=5
    )
    ttk.Button(profile_button_frame, text="⚖️ Balanced Mode", command=lambda: hub.apply_profile("balanced")).pack(
        side="left", padx=5
    )
    ttk.Button(profile_button_frame, text="🚀 Performance Mode", command=lambda: hub.apply_profile("performance")).pack(
        side="left", padx=5
    )
    ttk.Button(profile_button_frame, text="🎮 Gaming Mode", command=lambda: hub.apply_profile("gaming")).pack(
        side="left", padx=5
    )

    # Temperature monitoring
    temp_frame = ttk.LabelFrame(hardware_scrollable_frame, text="🌡️ Temperature Monitoring", padding="10")
    temp_frame.pack(fill="x", padx=10, pady=5)

    hub.temp_text = tk.Text(temp_frame, height=4, wrap=tk.WORD)
    hub.temp_text.pack(fill="x", pady=5)

    temp_controls = ttk.Frame(temp_frame)
    temp_controls.pack(fill="x", pady=5)

    ttk.Button(temp_controls, text="🌡️ Check Temperatures", command=hub.check_temperatures).pack(side="left", padx=5)

    hub.auto_temp_var = tk.BooleanVar()
    ttk.Checkbutton(
        temp_controls, text="Auto Fan Control", variable=hub.auto_temp_var, command=hub.toggle_auto_fan
    ).pack(side="left", padx=5)

    # Pack scrollable components
    hardware_canvas.pack(side="left", fill="both", expand=True)
    hardware_scrollbar.pack(side="right", fill="y")

    # Initialize hardware status
    try:
        hub.refresh_hardware_status()
    except Exception:
        pass


__all__.append("create_hardware_tab")
