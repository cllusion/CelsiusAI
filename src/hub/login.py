import asyncio
import logging
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from src.utils.celsius_auth import CelsiusAuth

try:
    from src.hub.theme import PALETTE as _C, FONT, FONT_BOLD, FONT_SM, FONT_HERO
except ImportError:
    _C = {
        "bg": "#0d0d14", "surface": "#13131e", "card": "#1a1a2e",
        "border": "#252540", "primary": "#7c3aed", "pri_light": "#a78bfa",
        "pri_dark": "#6d28d9", "text": "#e2e8f0", "text_muted": "#64748b",
    }
    FONT = FONT_SM = ("Segoe UI", 10)
    FONT_BOLD = ("Segoe UI", 10, "bold")
    FONT_HERO = ("Segoe UI", 22, "bold")

logger = logging.getLogger(__name__)


class LoginWindow:
    """Branded login dialog that authenticates against the file-based auth system."""

    def __init__(self, root: tk.Tk, data_dir: Path = None):
        self.root = root
        self.authenticated = False
        self.username = ""

        if data_dir is None:
            data_dir = Path.cwd() / "data"
        self._data_dir = data_dir

        # ── Window setup ─────────────────────────────────────────────────────
        root.title("Celsius AI")
        root.geometry("420x340")
        root.resizable(False, False)
        root.configure(bg=_C["bg"])

        # Centre on screen
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - 420) // 2
        y = (sh - 340) // 2
        root.geometry(f"420x340+{x}+{y}")

        # ── Outer padding ────────────────────────────────────────────────────
        outer = tk.Frame(root, bg=_C["bg"])
        outer.pack(fill="both", expand=True, padx=36, pady=24)

        # ── Brand header ─────────────────────────────────────────────────────
        brand = tk.Frame(outer, bg=_C["bg"])
        brand.pack(fill="x")

        tk.Label(
            brand, text="Celsius AI",
            font=FONT_HERO, fg=_C["text"], bg=_C["bg"],
        ).pack()
        tk.Label(
            brand, text="Personal AI Hub",
            font=FONT_SM, fg=_C["text_muted"], bg=_C["bg"],
        ).pack()

        # Accent divider
        tk.Frame(outer, height=2, bg=_C["primary"]).pack(fill="x", pady=(14, 18))

        # ── Form ─────────────────────────────────────────────────────────────
        form = tk.Frame(outer, bg=_C["bg"])
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)

        _lbl_cfg = dict(font=FONT_SM, fg=_C["text_muted"], bg=_C["bg"], anchor="w")
        _ent_cfg = dict(
            font=FONT, bg=_C["card"], fg=_C["text"],
            insertbackground=_C["text"], relief="flat",
            highlightthickness=1,
            highlightbackground=_C["border"],
            highlightcolor=_C["primary"],
        )

        tk.Label(form, text="Username", **_lbl_cfg).grid(
            row=0, column=0, sticky="w")
        self.user_entry = tk.Entry(form, **_ent_cfg)
        self.user_entry.grid(row=1, column=0, sticky="ew", ipady=6, pady=(2, 12))

        tk.Label(form, text="Password", **_lbl_cfg).grid(
            row=2, column=0, sticky="w")
        self.pass_entry = tk.Entry(form, show="*", **_ent_cfg)
        self.pass_entry.grid(row=3, column=0, sticky="ew", ipady=6, pady=(2, 20))

        # ── Buttons ──────────────────────────────────────────────────────────
        btn_row = tk.Frame(outer, bg=_C["bg"])
        btn_row.pack(fill="x")

        _btn_base = dict(relief="flat", cursor="hand2", padx=20, pady=8, bd=0)

        self.login_btn = tk.Button(
            btn_row, text="Sign In",
            font=FONT_BOLD,
            bg=_C["primary"], fg="#ffffff",
            activebackground=_C["pri_light"], activeforeground="#ffffff",
            command=self._on_login,
            **_btn_base,
        )
        self.login_btn.pack(side="left")

        tk.Button(
            btn_row, text="Cancel",
            font=FONT,
            bg=_C["card"], fg=_C["text_muted"],
            activebackground=_C["border"], activeforeground=_C["text"],
            command=self._on_cancel,
            **_btn_base,
        ).pack(side="left", padx=(10, 0))

        # ── Key bindings ─────────────────────────────────────────────────────
        self.user_entry.focus_set()
        self.user_entry.bind("<Return>", lambda _e: self.pass_entry.focus_set())
        self.pass_entry.bind("<Return>", lambda _e: self._on_login())

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _on_cancel(self):
        self.authenticated = False
        self.root.destroy()

    def _on_login(self):
        uname = self.user_entry.get().strip()
        pwd = self.pass_entry.get()
        if not uname:
            messagebox.showwarning("Login", "Please enter a username.")
            return

        self._set_ui_state(disabled=True)

        def worker():
            try:
                coro = self._authenticate(uname, pwd)
                success, result = asyncio.run(asyncio.wait_for(coro, timeout=30.0))
            except asyncio.TimeoutError:
                success, result = False, {"message": "Authentication timed out"}
            except Exception as exc:
                logger.exception("Authentication failed: %s", exc)
                success, result = False, {"message": str(exc)}

            def on_done():
                self._set_ui_state(disabled=False)
                if success:
                    self.username = uname
                    self.authenticated = True
                    try:
                        self.root.destroy()
                    except Exception:
                        pass
                else:
                    msg = result.get("message", "Authentication failed")
                    auth_file = result.get("auth_file")
                    if auth_file:
                        msg = f"{msg}\n\nAuth file: {auth_file}"
                    messagebox.showerror("Login Failed", msg)

            try:
                self.root.after(0, on_done)
            except Exception:
                on_done()

        threading.Thread(target=worker, daemon=True).start()

    def _set_ui_state(self, disabled: bool):
        state = "disabled" if disabled else "normal"
        try:
            self.user_entry.config(state=state)
            self.pass_entry.config(state=state)
            self.login_btn.config(state=state)
        except Exception:
            pass

    async def _authenticate(self, username: str, password: str):
        auth = CelsiusAuth(self._data_dir)
        await auth.initialize()
        success, result = await auth.authenticate(username, password)
        if isinstance(result, dict):
            result.setdefault("auth_file", str(auth.auth_file))
        return success, result
