"""
Small Tkinter viewer to preview and export `data/web_learning_contact_requests.json`.

Usage:
    python scripts/view_web_learning_contacts.py
"""

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

DATA = Path("data") / "web_learning_contact_requests.json"


class Viewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Web Learning Contact Requests")
        self.geometry("900x500")
        self.create_widgets()
        self.load()

    def create_widgets(self):
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            frm, columns=("topic", "source", "contact", "alternatives", "checked_at"), show="headings"
        )
        for col in ("topic", "source", "contact", "alternatives", "checked_at"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        btn_frm = ttk.Frame(self)
        btn_frm.pack(fill=tk.X)
        ttk.Button(btn_frm, text="Refresh", command=self.load).pack(side=tk.LEFT, padx=4, pady=4)
        ttk.Button(btn_frm, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frm, text="Open File", command=self.open_file).pack(side=tk.LEFT, padx=4)

    def load(self):
        self.tree.delete(*self.tree.get_children())
        if not DATA.exists():
            messagebox.showinfo("No data", f"{DATA} not found.")
            return
        try:
            items = json.loads(DATA.read_text(encoding="utf-8"))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {e}")
            return
        for it in items:
            alts = ", ".join(it.get("alternatives") or [])
            self.tree.insert(
                "", "end", values=(it.get("topic"), it.get("source"), it.get("contact"), alts, it.get("checked_at"))
            )

    def export_csv(self):
        items = []
        if DATA.exists():
            items = json.loads(DATA.read_text(encoding="utf-8"))
        if not items:
            messagebox.showinfo("No data", "No items to export")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        import csv

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
        messagebox.showinfo("Exported", f"Exported {len(items)} items to {path}")

    def open_file(self):
        if DATA.exists():
            import os

            os.startfile(DATA)


if __name__ == "__main__":
    Viewer().mainloop()
