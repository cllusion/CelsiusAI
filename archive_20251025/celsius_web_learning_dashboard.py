#!/usr/bin/env python3
"""
Celsius AI Web Learning Dashboard
Real-time monitoring of web learning activities
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import sqlite3
import json
from datetime import datetime, timedelta
import threading
import time
from typing import Dict, List
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates


class WebLearningDashboard:
    """Dashboard for monitoring Celsius AI web learning"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🌐 Celsius AI - Web Learning Dashboard")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1a1a2e")

        # Database path
        self.db_path = "celsius_web_learning.db"

        # Dashboard state
        self.auto_refresh = True
        self.refresh_interval = 30  # seconds

        # Colors
        self.colors = {
            "bg": "#1a1a2e",
            "panel": "#16213e",
            "accent": "#0f3460",
            "success": "#00ff88",
            "warning": "#ffaa00",
            "error": "#ff4757",
            "text": "#ffffff",
            "subtext": "#a4b0be",
        }

        self.setup_dashboard()
        self.start_auto_refresh()

    def setup_dashboard(self):
        """Setup the main dashboard interface"""
        # Main title
        title_frame = tk.Frame(self.root, bg=self.colors["bg"])
        title_frame.pack(fill=tk.X, padx=20, pady=10)

        title_label = tk.Label(
            title_frame,
            text="🌐 CELSIUS AI WEB LEARNING DASHBOARD",
            font=("Arial", 18, "bold"),
            fg=self.colors["success"],
            bg=self.colors["bg"],
        )
        title_label.pack()

        # Control panel
        control_frame = tk.Frame(self.root, bg=self.colors["bg"])
        control_frame.pack(fill=tk.X, padx=20, pady=5)

        refresh_btn = tk.Button(
            control_frame,
            text="🔄 Refresh",
            command=self.refresh_dashboard,
            bg=self.colors["accent"],
            fg=self.colors["text"],
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

        auto_refresh_var = tk.BooleanVar(value=self.auto_refresh)
        auto_checkbox = tk.Checkbutton(
            control_frame,
            text="Auto-refresh (30s)",
            variable=auto_refresh_var,
            command=lambda: setattr(self, "auto_refresh", auto_refresh_var.get()),
            bg=self.colors["bg"],
            fg=self.colors["text"],
            selectcolor=self.colors["accent"],
            font=("Arial", 10),
        )
        auto_checkbox.pack(side=tk.LEFT, padx=20)

        # Status indicator
        self.status_label = tk.Label(
            control_frame,
            text="🔄 Loading...",
            fg=self.colors["warning"],
            bg=self.colors["bg"],
            font=("Arial", 10, "bold"),
        )
        self.status_label.pack(side=tk.RIGHT)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Configure notebook style
        style = ttk.Style()
        style.configure("TNotebook.Tab", padding=[20, 10])

        self.setup_overview_tab()
        self.setup_learning_activity_tab()
        self.setup_insights_tab()
        self.setup_reports_tab()

        # Load initial data
        self.refresh_dashboard()

    def setup_overview_tab(self):
        """Setup overview tab"""
        overview_frame = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(overview_frame, text="📊 Overview")

        # Statistics panel
        stats_frame = tk.LabelFrame(
            overview_frame,
            text="📈 Learning Statistics",
            fg=self.colors["text"],
            bg=self.colors["panel"],
            font=("Arial", 12, "bold"),
        )
        stats_frame.pack(fill=tk.X, padx=10, pady=10)

        self.stats_frame = stats_frame

        # Topic distribution chart
        chart_frame = tk.LabelFrame(
            overview_frame,
            text="📊 Topic Distribution",
            fg=self.colors["text"],
            bg=self.colors["panel"],
            font=("Arial", 12, "bold"),
        )
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.chart_frame = chart_frame

    def setup_learning_activity_tab(self):
        """Setup learning activity tab"""
        activity_frame = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(activity_frame, text="🔍 Learning Activity")

        # Recent content learned
        content_frame = tk.LabelFrame(
            activity_frame,
            text="📚 Recently Learned Content",
            fg=self.colors["text"],
            bg=self.colors["panel"],
            font=("Arial", 12, "bold"),
        )
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Content list
        content_list_frame = tk.Frame(content_frame, bg=self.colors["panel"])
        content_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Columns: Title, Topic, Quality, Time
        columns = ("Title", "Topic", "Quality", "Learned")
        self.content_tree = ttk.Treeview(content_list_frame, columns=columns, show="headings", height=15)

        for col in columns:
            self.content_tree.heading(col, text=col)
            self.content_tree.column(col, width=200)

        content_scrollbar = ttk.Scrollbar(content_list_frame, orient=tk.VERTICAL, command=self.content_tree.yview)
        self.content_tree.configure(yscrollcommand=content_scrollbar.set)

        self.content_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_insights_tab(self):
        """Setup insights tab"""
        insights_frame = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(insights_frame, text="💡 Insights")

        # Insights display
        insights_display_frame = tk.LabelFrame(
            insights_frame,
            text="🧠 Generated Insights",
            fg=self.colors["text"],
            bg=self.colors["panel"],
            font=("Arial", 12, "bold"),
        )
        insights_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.insights_text = scrolledtext.ScrolledText(
            insights_display_frame,
            wrap=tk.WORD,
            width=80,
            height=25,
            bg=self.colors["accent"],
            fg=self.colors["text"],
            font=("Consolas", 10),
            insertbackground=self.colors["text"],
        )
        self.insights_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def setup_reports_tab(self):
        """Setup reports tab"""
        reports_frame = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(reports_frame, text="📋 Reports")

        # Report selection
        report_control_frame = tk.Frame(reports_frame, bg=self.colors["bg"])
        report_control_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(
            report_control_frame,
            text="Report Period:",
            fg=self.colors["text"],
            bg=self.colors["bg"],
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT)

        self.report_period_var = tk.StringVar(value="daily")
        report_combo = ttk.Combobox(
            report_control_frame,
            textvariable=self.report_period_var,
            values=["daily", "weekly", "monthly"],
            state="readonly",
            width=10,
        )
        report_combo.pack(side=tk.LEFT, padx=10)

        generate_report_btn = tk.Button(
            report_control_frame,
            text="📊 Generate Report",
            command=self.generate_report,
            bg=self.colors["accent"],
            fg=self.colors["text"],
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
        )
        generate_report_btn.pack(side=tk.LEFT, padx=10)

        # Report display
        report_display_frame = tk.LabelFrame(
            reports_frame,
            text="📈 Learning Report",
            fg=self.colors["text"],
            bg=self.colors["panel"],
            font=("Arial", 12, "bold"),
        )
        report_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.report_text = scrolledtext.ScrolledText(
            report_display_frame,
            wrap=tk.WORD,
            width=80,
            height=20,
            bg=self.colors["accent"],
            fg=self.colors["text"],
            font=("Consolas", 10),
            insertbackground=self.colors["text"],
        )
        self.report_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def get_learning_statistics(self) -> Dict:
        """Get current learning statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total content learned
            cursor.execute("SELECT COUNT(*) FROM learned_content")
            total_content = cursor.fetchone()[0]

            # Content by topic
            cursor.execute(
                """
                SELECT topic, COUNT(*) as count, AVG(quality_score) as avg_quality
                FROM learned_content 
                GROUP BY topic
                ORDER BY count DESC
            """
            )
            topic_stats = cursor.fetchall()

            # Recent activity (last 24 hours)
            yesterday = datetime.now() - timedelta(days=1)
            cursor.execute("SELECT COUNT(*) FROM learned_content WHERE timestamp > ?", (yesterday.isoformat(),))
            recent_content = cursor.fetchone()[0]

            # Total insights
            cursor.execute("SELECT COUNT(*) FROM learning_insights")
            total_insights = cursor.fetchone()[0]

            # Average quality
            cursor.execute("SELECT AVG(quality_score) FROM learned_content")
            avg_quality = cursor.fetchone()[0] or 0

            conn.close()

            return {
                "total_content": total_content,
                "topic_stats": topic_stats,
                "recent_content": recent_content,
                "total_insights": total_insights,
                "avg_quality": avg_quality,
            }

        except Exception as e:
            return {"total_content": 0, "topic_stats": [], "recent_content": 0, "total_insights": 0, "avg_quality": 0}

    def update_overview(self):
        """Update overview tab with current statistics"""
        stats = self.get_learning_statistics()

        # Clear existing stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        # Create stats grid
        stats_grid = tk.Frame(self.stats_frame, bg=self.colors["panel"])
        stats_grid.pack(fill=tk.X, padx=10, pady=10)

        # Statistics cards
        stat_items = [
            ("📚 Total Content", str(stats["total_content"]), self.colors["success"]),
            ("🔥 Recent (24h)", str(stats["recent_content"]), self.colors["warning"]),
            ("💡 Total Insights", str(stats["total_insights"]), self.colors["accent"]),
            ("⭐ Avg Quality", f"{stats['avg_quality']:.2f}", self.colors["success"]),
        ]

        for i, (label, value, color) in enumerate(stat_items):
            card_frame = tk.Frame(stats_grid, bg=self.colors["accent"], relief=tk.RAISED, bd=2)
            card_frame.grid(row=0, column=i, padx=10, pady=5, sticky="ew")
            stats_grid.columnconfigure(i, weight=1)

            tk.Label(card_frame, text=label, fg=self.colors["text"], bg=self.colors["accent"], font=("Arial", 10)).pack(
                pady=5
            )

            tk.Label(card_frame, text=value, fg=color, bg=self.colors["accent"], font=("Arial", 16, "bold")).pack(
                pady=5
            )

        # Update topic distribution chart
        self.update_topic_chart(stats["topic_stats"])

    def update_topic_chart(self, topic_stats):
        """Update topic distribution chart"""
        # Clear existing chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        if not topic_stats:
            tk.Label(
                self.chart_frame,
                text="No learning data available yet",
                fg=self.colors["subtext"],
                bg=self.colors["panel"],
                font=("Arial", 12),
            ).pack(expand=True)
            return

        # Create matplotlib figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        fig.patch.set_facecolor(self.colors["panel"])

        # Topic distribution pie chart
        topics = [stat[0] for stat in topic_stats]
        counts = [stat[1] for stat in topic_stats]

        ax1.pie(counts, labels=topics, autopct="%1.1f%%", startangle=90)
        ax1.set_title("Content by Topic", color="white")
        ax1.set_facecolor(self.colors["panel"])

        # Quality scores bar chart
        qualities = [stat[2] for stat in topic_stats]

        ax2.bar(topics, qualities, color=["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#feca57"][: len(topics)])
        ax2.set_title("Average Quality by Topic", color="white")
        ax2.set_ylabel("Quality Score", color="white")
        ax2.set_ylim(0, 1)
        ax2.set_facecolor(self.colors["panel"])
        ax2.tick_params(colors="white")

        # Rotate x-axis labels for better readability
        plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")

        plt.tight_layout()

        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def update_learning_activity(self):
        """Update learning activity tab"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get recent content
            cursor.execute(
                """
                SELECT title, topic, quality_score, timestamp
                FROM learned_content 
                ORDER BY timestamp DESC
                LIMIT 50
            """
            )

            recent_content = cursor.fetchall()
            conn.close()

            # Clear existing items
            for item in self.content_tree.get_children():
                self.content_tree.delete(item)

            # Add recent content
            for content in recent_content:
                title = content[0][:50] + "..." if len(content[0]) > 50 else content[0]
                topic = content[1].title()
                quality = f"{content[2]:.2f}" if content[2] else "N/A"
                timestamp = datetime.fromisoformat(content[3]).strftime("%Y-%m-%d %H:%M")

                self.content_tree.insert("", "end", values=(title, topic, quality, timestamp))

        except Exception as e:
            pass

    def update_insights(self):
        """Update insights tab"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT topic, insight, confidence_score, timestamp, insight_type
                FROM learning_insights 
                ORDER BY timestamp DESC
                LIMIT 20
            """
            )

            insights = cursor.fetchall()
            conn.close()

            # Clear and update insights display
            self.insights_text.delete(1.0, tk.END)

            if not insights:
                self.insights_text.insert(tk.END, "🤖 No insights generated yet.\n\n")
                self.insights_text.insert(tk.END, "Insights will appear here as Celsius learns from web sources.\n")
                return

            self.insights_text.insert(tk.END, "🧠 CELSIUS AI LEARNING INSIGHTS\n")
            self.insights_text.insert(tk.END, "=" * 50 + "\n\n")

            for insight in insights:
                topic, text, confidence, timestamp, insight_type = insight

                # Format timestamp
                time_str = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M")

                # Insert insight
                self.insights_text.insert(tk.END, f"📊 {topic.upper()} | {insight_type.replace('_', ' ').title()}\n")
                self.insights_text.insert(tk.END, f"🕒 {time_str} | Confidence: {confidence:.0%}\n")
                self.insights_text.insert(tk.END, f"💡 {text}\n")
                self.insights_text.insert(tk.END, "-" * 50 + "\n\n")

            # Scroll to top
            self.insights_text.see(1.0)

        except Exception as e:
            self.insights_text.delete(1.0, tk.END)
            self.insights_text.insert(tk.END, f"❌ Error loading insights: {str(e)}")

    def generate_report(self):
        """Generate and display learning report"""
        # Import web learner to generate report
        try:
            from celsius_web_learner import CelsiusWebLearner

            learner = CelsiusWebLearner()
            period = self.report_period_var.get()
            report = learner.generate_learning_report(period)

            # Display report
            self.report_text.delete(1.0, tk.END)

            if not report:
                self.report_text.insert(tk.END, "❌ Unable to generate report. No learning data available.\n")
                return

            # Format report
            self.report_text.insert(tk.END, f"📈 CELSIUS AI LEARNING REPORT ({period.upper()})\n")
            self.report_text.insert(tk.END, "=" * 60 + "\n\n")

            self.report_text.insert(tk.END, f"📊 SUMMARY\n")
            self.report_text.insert(
                tk.END, f"Generated: {datetime.fromisoformat(report['generated_at']).strftime('%Y-%m-%d %H:%M')}\n"
            )
            self.report_text.insert(tk.END, f"Topics Covered: {report['topics_covered']}\n")
            self.report_text.insert(tk.END, f"Content Learned: {report['total_content_learned']}\n")
            self.report_text.insert(tk.END, f"Insights Generated: {report['insights_generated']}\n\n")

            # Topic breakdown
            if report["topic_breakdown"]:
                self.report_text.insert(tk.END, "📚 TOPIC BREAKDOWN\n")
                for topic_data in report["topic_breakdown"]:
                    self.report_text.insert(
                        tk.END,
                        f"• {topic_data['topic'].title()}: "
                        f"{topic_data['content_count']} items "
                        f"(Quality: {topic_data['average_quality']:.2f})\n",
                    )
                self.report_text.insert(tk.END, "\n")

            # Learning summary
            self.report_text.insert(tk.END, "📖 LEARNING SUMMARY\n")
            self.report_text.insert(tk.END, f"{report['learning_summary']}\n\n")

            # Recommendations
            if report["recommendations"]:
                self.report_text.insert(tk.END, "💡 RECOMMENDATIONS\n")
                for i, rec in enumerate(report["recommendations"], 1):
                    self.report_text.insert(tk.END, f"{i}. {rec}\n")

        except Exception as e:
            self.report_text.delete(1.0, tk.END)
            self.report_text.insert(tk.END, f"❌ Error generating report: {str(e)}\n")
            self.report_text.insert(tk.END, "\nPlease ensure the web learner is properly initialized.")

    def refresh_dashboard(self):
        """Refresh all dashboard data"""
        self.status_label.config(text="🔄 Refreshing...", fg=self.colors["warning"])

        try:
            # Update all tabs
            self.update_overview()
            self.update_learning_activity()
            self.update_insights()

            # Update status
            current_time = datetime.now().strftime("%H:%M:%S")
            self.status_label.config(text=f"✅ Updated: {current_time}", fg=self.colors["success"])

        except Exception as e:
            self.status_label.config(text="❌ Update Failed", fg=self.colors["error"])

    def start_auto_refresh(self):
        """Start automatic dashboard refresh"""

        def auto_refresh_loop():
            while True:
                time.sleep(self.refresh_interval)
                if self.auto_refresh:
                    self.refresh_dashboard()

        refresh_thread = threading.Thread(target=auto_refresh_loop, daemon=True)
        refresh_thread.start()

    def run(self):
        """Run the dashboard"""
        self.root.mainloop()


def main():
    """Launch the web learning dashboard"""
    print("🌐 Launching Celsius AI Web Learning Dashboard...")

    try:
        dashboard = WebLearningDashboard()
        dashboard.run()
    except Exception as e:
        print(f"❌ Error launching dashboard: {str(e)}")


if __name__ == "__main__":
    main()
