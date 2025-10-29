#!/usr/bin/env python3
"""
Celsius AI Web Learning Dashboard (Async Edition)
=================================================
A real-time, asynchronous dashboard for monitoring the activities of the
Celsius AI Web Learning Engine.

Features:
- Built with modern, themed UI elements (`ttkthemes`).
- Fully asynchronous operations using `asyncio` and `aiosqlite`.
- Real-time data fetching and UI updates without blocking.
- Interactive charts for data visualization with `matplotlib`.
"""

import asyncio
import tkinter as tk
from tkinter import ttk, scrolledtext
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
from pathlib import Path

import aiosqlite
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ttkthemes import ThemedTk

# --- Project Imports ---
try:
    from learning.celsius_web_learner import CelsiusWebLearner
except ImportError:
    # This might happen if run standalone, provide a dummy class
    class CelsiusWebLearner:
        def __init__(self, *args, **kwargs):
            pass

        async def generate_learning_report(self, *args, **kwargs):
            return {}


# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


class WebLearningDashboard:
    """
    An asynchronous dashboard for monitoring Celsius AI web learning.
    """

    def __init__(self, root: ThemedTk, loop: asyncio.AbstractEventLoop):
        """
        Initializes the dashboard.

        Args:
            root: The root ThemedTk window.
            loop: The asyncio event loop.
        """
        self.root = root
        self.loop = loop
        self.root.title("🌐 Celsius AI - Web Learning Dashboard (Async)")
        self.root.geometry("1400x900")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- State ---
        self.db_path = Path("celsius_web_learning_async.db")
        self.auto_refresh = asyncio.Event()
        self.auto_refresh.set()
        self.refresh_interval = 30  # seconds
        self.logger = logging.getLogger("WebLearningDashboard")

        # --- UI & Theming ---
        self.style = ttk.Style(self.root)
        self.root.set_theme("equilux")  # A nice dark theme
        self.configure_styles()

        # --- Initialization ---
        self.tasks = []
        self.setup_dashboard()
        self.tasks.append(self.loop.create_task(self.auto_refresh_loop()))

    def configure_styles(self):
        """Configures custom styles for the dashboard."""
        bg = self.style.lookup("TFrame", "background")
        panel_bg = "#2a2a2a"
        accent = "#00aaff"
        text_color = "white"

        self.style.configure("TFrame", background=bg)
        self.style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground=accent, background=bg)
        self.style.configure("Card.TFrame", background=panel_bg, relief="raised", borderwidth=1)
        self.style.configure("Card.TLabel", font=("Segoe UI", 10), foreground=text_color, background=panel_bg)
        self.style.configure("CardValue.TLabel", font=("Segoe UI", 16, "bold"), foreground=accent, background=panel_bg)
        self.style.configure("TNotebook.Tab", padding=[20, 10], font=("Segoe UI", 10, "bold"))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def setup_dashboard(self):
        """Sets up the main dashboard interface."""
        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(header_frame, text="🌐 Web Learning Dashboard", style="Header.TLabel").pack(side=tk.LEFT)
        self.status_label = ttk.Label(header_frame, text="Initializing...", font=("Segoe UI", 10))
        self.status_label.pack(side=tk.RIGHT)

        # Controls
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Button(
            control_frame, text="🔄 Refresh", command=lambda: self.loop.create_task(self.refresh_dashboard())
        ).pack(side=tk.LEFT)

        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.setup_tabs()
        self.loop.create_task(self.refresh_dashboard())

    def setup_tabs(self):
        """Creates all the tabs in the notebook."""
        self.overview_frame = ttk.Frame(self.notebook)
        self.activity_frame = ttk.Frame(self.notebook)
        self.insights_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.overview_frame, text="📊 Overview")
        self.notebook.add(self.activity_frame, text="🔍 Learning Activity")
        self.notebook.add(self.insights_frame, text="💡 Insights")

        # Populate tabs
        self.setup_overview_tab()
        self.setup_learning_activity_tab()
        self.setup_insights_tab()

    def setup_overview_tab(self):
        """Sets up the content of the Overview tab."""
        # Statistics Cards
        self.stats_frame = ttk.Frame(self.overview_frame)
        self.stats_frame.pack(fill=tk.X, padx=10, pady=10)

        # Chart
        self.chart_frame = ttk.LabelFrame(self.overview_frame, text="📊 Topic Distribution")
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def setup_learning_activity_tab(self):
        """Sets up the content of the Learning Activity tab."""
        content_frame = ttk.LabelFrame(self.activity_frame, text="📚 Recently Learned Content")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("Title", "Topic", "Quality", "Learned")
        self.content_tree = ttk.Treeview(content_frame, columns=columns, show="headings", height=15)
        for col in columns:
            self.content_tree.heading(col, text=col)
        self.content_tree.column("Title", width=400)
        self.content_tree.pack(fill=tk.BOTH, expand=True)

    def setup_insights_tab(self):
        """Sets up the content of the Insights tab."""
        insights_display_frame = ttk.LabelFrame(self.insights_frame, text="🧠 Generated Insights")
        insights_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.insights_text = scrolledtext.ScrolledText(insights_display_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.insights_text.pack(fill=tk.BOTH, expand=True)

    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Fetches learning statistics from the database asynchronously."""
        if not self.db_path.exists():
            self.logger.warning(f"Database file not found at {self.db_path}. Returning empty stats.")
            return {"total_content": 0, "topic_stats": [], "recent_content": 0, "total_insights": 0, "avg_quality": 0}
        try:
            async with aiosqlite.connect(self.db_path) as db:
                total_content_cur = await db.execute("SELECT COUNT(*) FROM learned_content")
                total_content = (await total_content_cur.fetchone() or [0])[0]

                topic_stats_cur = await db.execute(
                    """
                    SELECT topic, COUNT(*), AVG(quality_score) FROM learned_content
                    GROUP BY topic ORDER BY COUNT(*) DESC
                """
                )
                topic_stats = await topic_stats_cur.fetchall()

                yesterday = (datetime.now() - timedelta(days=1)).isoformat()
                recent_cur = await db.execute("SELECT COUNT(*) FROM learned_content WHERE timestamp > ?", (yesterday,))
                recent_content = (await recent_cur.fetchone() or [0])[0]

                insights_cur = await db.execute("SELECT COUNT(*) FROM learning_insights")
                total_insights = (await insights_cur.fetchone() or [0])[0]

                avg_quality_cur = await db.execute("SELECT AVG(quality_score) FROM learned_content")
                avg_quality = (await avg_quality_cur.fetchone() or [0])[0]

            return {
                "total_content": total_content,
                "topic_stats": topic_stats,
                "recent_content": recent_content,
                "total_insights": total_insights,
                "avg_quality": avg_quality or 0,
            }
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"total_content": 0, "topic_stats": [], "recent_content": 0, "total_insights": 0, "avg_quality": 0}

    async def refresh_dashboard(self):
        """Refreshes all dashboard data asynchronously."""
        self.status_label.config(text="🔄 Refreshing...")
        try:
            stats = await self.get_learning_statistics()
            self.update_overview(stats)
            await self.update_learning_activity()
            await self.update_insights()
            self.status_label.config(text=f"✅ Updated: {datetime.now():%H:%M:%S}")
        except Exception as e:
            self.logger.error(f"Dashboard refresh failed: {e}")
            self.status_label.config(text="❌ Update Failed")

    def update_overview(self, stats: Dict[str, Any]):
        """Updates the Overview tab with new statistics."""
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        stat_items = [
            ("📚 Total Content", stats["total_content"]),
            ("🔥 Recent (24h)", stats["recent_content"]),
            ("💡 Total Insights", stats["total_insights"]),
            ("⭐ Avg Quality", f"{stats['avg_quality']:.2f}"),
        ]

        for i, (label, value) in enumerate(stat_items):
            card = ttk.Frame(self.stats_frame, style="Card.TFrame")
            card.grid(row=0, column=i, padx=10, pady=5, sticky="ew")
            self.stats_frame.columnconfigure(i, weight=1)
            ttk.Label(card, text=label, style="Card.TLabel").pack(pady=(10, 0))
            ttk.Label(card, text=str(value), style="CardValue.TLabel").pack(pady=(0, 10))

        self.update_topic_chart(stats["topic_stats"])

    def update_topic_chart(self, topic_stats: List[tuple]):
        """Updates the topic distribution chart."""
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        if not topic_stats:
            ttk.Label(self.chart_frame, text="No data to display.").pack()
            return

        fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
        fig.patch.set_facecolor(self.style.lookup("TFrame", "background"))

        topics = [stat[0] for stat in topic_stats]
        counts = [stat[1] for stat in topic_stats]

        ax.pie(counts, labels=topics, autopct="%1.1f%%", startangle=90, textprops={"color": "white"})
        ax.set_title("Content by Topic", color="white")

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    async def update_learning_activity(self):
        """Updates the learning activity treeview."""
        if not self.db_path.exists():
            return
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT title, topic, quality_score, timestamp FROM learned_content
                    ORDER BY timestamp DESC LIMIT 50
                """
                )
                recent_content = await cursor.fetchall()

            self.content_tree.delete(*self.content_tree.get_children())
            for title, topic, quality, ts in recent_content:
                self.content_tree.insert(
                    "",
                    "end",
                    values=(
                        title[:60] + "..." if len(title) > 60 else title,
                        topic.title(),
                        f"{quality:.2f}" if quality else "N/A",
                        datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M"),
                    ),
                )
        except Exception as e:
            self.logger.error(f"Failed to update activity: {e}")

    async def update_insights(self):
        """Updates the insights text view."""
        if not self.db_path.exists():
            return
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT topic, insight, confidence_score, timestamp FROM learning_insights
                    ORDER BY timestamp DESC LIMIT 20
                """
                )
                insights = await cursor.fetchall()

            self.insights_text.config(state=tk.NORMAL)
            self.insights_text.delete(1.0, tk.END)
            if not insights:
                self.insights_text.insert(tk.END, "No insights generated yet.")
            else:
                for topic, insight, confidence, ts in insights:
                    self.insights_text.insert(
                        tk.END,
                        f"[{datetime.fromisoformat(ts):%Y-%m-%d %H:%M}] [{topic.upper()}] (Conf: {confidence:.0%})\n",
                    )
                    self.insights_text.insert(tk.END, f"💡 {insight}\n\n")
            self.insights_text.config(state=tk.DISABLED)
        except Exception as e:
            self.logger.error(f"Failed to update insights: {e}")

    async def auto_refresh_loop(self):
        """The main loop for auto-refreshing the dashboard."""
        while True:
            try:
                await self.auto_refresh.wait()
                await self.refresh_dashboard()
                await asyncio.sleep(self.refresh_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Auto-refresh loop error: {e}")
                await asyncio.sleep(self.refresh_interval)

    def on_closing(self):
        """Handles the window closing event."""
        for task in self.tasks:
            task.cancel()
        self.root.destroy()


async def main():
    """The main entry point for the dashboard application."""
    loop = asyncio.get_event_loop()
    root = ThemedTk()
    app = WebLearningDashboard(root, loop)

    while True:
        try:
            root.update()
            root.update_idletasks()
            await asyncio.sleep(0.01)
        except tk.TclError:
            break  # Window was closed


if __name__ == "__main__":
    logging.info("Launching Celsius AI Web Learning Dashboard...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Dashboard closed by user.")
