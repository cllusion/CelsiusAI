import asyncio
import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from src.utils.celsius_auth import CelsiusAuth

logger = logging.getLogger(__name__)


class LoginWindow:
    """A small login dialog that authenticates against the file-based auth system.

    This dialog runs the synchronous authentication flow using ``asyncio.run``
    because the full application event loop isn't started yet when the login
    window appears.
    """

    def __init__(self, root: tk.Tk, data_dir: Path = None):
        self.root = root
        self.authenticated = False
        self.username = ""

        if data_dir is None:
            data_dir = Path.cwd() / "data"

        self._data_dir = data_dir

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
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        ttk.Button(btn_frame, text="Login", command=self._on_login).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).pack(side="left", padx=5)

        frm.columnconfigure(1, weight=1)

    def _on_cancel(self):
        self.authenticated = False
        self.root.destroy()

    def _on_login(self):
        uname = self.user_entry.get().strip()
        pwd = self.pass_entry.get()
        if not uname:
            messagebox.showwarning("Login", "Please enter a username.")
            return
        # Run authentication in a background thread so the UI stays responsive
        # and apply a timeout so the dialog doesn't hang indefinitely.
        self._set_ui_state(disabled=True)

        def worker():
            try:
                # Run the authenticate coroutine with a timeout
                coro = self._authenticate(uname, pwd)
                # 30 second timeout — allow for transient file locks (OneDrive,
                # antivirus) when upgrading or writing auth files.
                success, result = asyncio.run(asyncio.wait_for(coro, timeout=30.0))
            except asyncio.TimeoutError:
                success, result = False, {"message": "Authentication timed out"}
            except Exception as e:
                logger.exception("Authentication failed: %s", e)
                success, result = False, {"message": str(e)}

            # Post result back to the main thread
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
                    # Show the auth file path so the user can confirm which JSON file
                    # the login code is reading. This is non-sensitive and helps
                    # diagnose cases where the app runs from a different CWD.
                    msg = result.get("message", "Authentication failed")
                    auth_file = result.get("auth_file")
                    if auth_file:
                        msg = f"{msg}\n\nAuth file: {auth_file}"
                    messagebox.showerror("Login Failed", msg)

            try:
                self.root.after(0, on_done)
            except Exception:
                # Last-resort direct call
                on_done()

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _set_ui_state(self, disabled: bool):
        state = "disabled" if disabled else "normal"
        try:
            for w in (self.user_entry, self.pass_entry):
                w.config(state=state)
            # find the login button (first child of btn_frame)
            # keep it simple: iterate children and set state
            for child in self.root.winfo_children():
                for sub in child.winfo_children():
                    try:
                        sub.config(state=state)
                    except Exception:
                        pass
        except Exception:
            pass

    async def _authenticate(self, username: str, password: str):
        auth = CelsiusAuth(self._data_dir)
        await auth.initialize()
        success, result = await auth.authenticate(username, password)
        # Attach the resolved auth file path to help debugging from the UI.
        if isinstance(result, dict):
            result.setdefault("auth_file", str(auth.auth_file))
        return success, result
