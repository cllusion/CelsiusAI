import asyncio
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional

from src.utils.celsius_auth import CelsiusAuth


class ChangePasswordWindow:
    """Dialog to change the current user's password.

    Usage: ChangePasswordWindow(parent, username)
    """

    def __init__(self, parent: tk.Widget, username: str, data_dir: Optional[Path] = None):
        self.parent = parent
        self.username = username
        if data_dir is None:
            data_dir = Path.cwd() / "data"

        self._data_dir = data_dir

        self.win = tk.Toplevel(parent)
        self.win.title("Change Password")
        self.win.geometry("420x220")
        self.win.transient(parent)
        self.win.grab_set()

        frm = ttk.Frame(self.win, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=f"User: {self.username}").grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(frm, text="Current password:").grid(row=1, column=0, sticky="w", pady=(8, 2))
        self.current_entry = ttk.Entry(frm, show="*")
        self.current_entry.grid(row=1, column=1, sticky="ew", pady=(8, 2))

        ttk.Label(frm, text="New password:").grid(row=2, column=0, sticky="w", pady=2)
        self.new_entry = ttk.Entry(frm, show="*")
        self.new_entry.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(frm, text="Confirm new:").grid(row=3, column=0, sticky="w", pady=2)
        self.confirm_entry = ttk.Entry(frm, show="*")
        self.confirm_entry.grid(row=3, column=1, sticky="ew", pady=2)

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btns, text="Change", command=self._on_change).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancel", command=self._on_cancel).pack(side="left", padx=6)

        frm.columnconfigure(1, weight=1)

    def _on_cancel(self):
        self.win.destroy()

    def _on_change(self):
        current = self.current_entry.get()
        new = self.new_entry.get()
        confirm = self.confirm_entry.get()

        if not current or not new:
            messagebox.showwarning("Change Password", "Please fill all password fields.")
            return
        if new != confirm:
            messagebox.showwarning("Change Password", "New passwords do not match.")
            return

        # Run verification and change synchronously (safe pre-mainloop usage)
        try:
            ok, res = asyncio.run(self._verify_and_change(current, new))
        except Exception as e:
            messagebox.showerror("Change Password", f"Internal error: {e}")
            return

        if ok:
            messagebox.showinfo("Change Password", "Password changed successfully.")
            self.win.destroy()
        else:
            messagebox.showerror("Change Password", res.get("message", str(res)))

    async def _verify_and_change(self, current: str, new: str):
        auth = CelsiusAuth(self._data_dir)
        await auth.initialize()

        # verify current credentials
        success, result = await auth.authenticate(self.username, current)
        if not success:
            return False, {"message": "Current password incorrect."}

        # perform change
        ok, msg = await auth.change_password(self.username, new)
        if ok:
            return True, {"message": msg}
        return False, {"message": msg}
