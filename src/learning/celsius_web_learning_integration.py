#!/usr/bin/env python3
"""
Celsius AI Web Learning Integration
Integrates web learning capabilities into the main Celsius AI system
"""

import os
import sys
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
# Resolve project root (two levels up from src/learning)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

try:
    from celsius_web_learner import CelsiusWebLearner
except ImportError:
    print("❌ Error: celsius_web_learner.py not found")
    CelsiusWebLearner = None


class CelsiusWebLearningIntegration:
    """Integration layer for web learning with main Celsius system"""

    def __init__(self):
        self.web_learner = None
        self.learning_active = False
        self.integration_status = "initializing"
        self.last_learning_report = None
        self.learning_thread = None

        # Integration settings
        self.settings = {
            "auto_start_learning": True,
            "learning_interval_hours": 6,  # Learn every 6 hours
            "report_generation_hours": 24,  # Generate reports daily
            "max_learning_sessions_per_day": 4,
            "ethical_mode": True,
            "trusted_sources": [],
            "save_learning_logs": True,
        }

        self.initialize_integration()

    def initialize_integration(self):
        """Initialize the web learning integration"""
        try:
            if CelsiusWebLearner is None:
                self.integration_status = "error_missing_learner"
                return

            # Initialize web learner with a local DB path used by the async learner
            db_path = PROJECT_ROOT / "data" / "web_learning.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.web_learner = CelsiusWebLearner(db_path)
            # Load any admin-approved ingestion sources and add them as trusted
            # sources and as an "approved_sources" learning topic so the
            # learner will consider them during learning cycles.
            try:
                approved_file = PROJECT_ROOT / "data" / "ingestion_approved.json"
                if approved_file.exists():
                    with open(approved_file, "r", encoding="utf-8") as f:
                        approved = json.load(f) or []
                    approved_sources = []
                    for entry in approved:
                        src = entry.get("source") or entry.get("url") or entry.get("feed")
                        if not src:
                            continue
                        try:
                            from urllib.parse import urlparse

                            net = urlparse(src).netloc or src
                            net = net.lower()
                            # Add to trusted_sources set on the web_learner
                            try:
                                self.web_learner.trusted_sources.add(net)
                            except Exception:
                                pass
                        except Exception:
                            pass
                        approved_sources.append(src)

                    # Create or extend an "approved_sources" topic so the
                    # learner will actively fetch these URLs (feed-first).
                    if approved_sources:
                        try:
                            topic_name = "approved_sources"
                            if topic_name not in self.web_learner.learning_topics:
                                self.web_learner.learning_topics[topic_name] = {"keywords": [], "sources": []}
                            # extend while avoiding duplicates
                            existing = set(self.web_learner.learning_topics[topic_name]["sources"])
                            for s in approved_sources:
                                if s not in existing:
                                    self.web_learner.learning_topics[topic_name]["sources"].append(s)
                                    existing.add(s)
                        except Exception:
                            pass
            except Exception:
                # Non-fatal: integration still initializes even if approved list can't be read
                pass
            # Mirror integration settings to the learner for robots and trusted sources
            try:
                # Use ethical_mode to decide whether to respect robots.txt by default
                self.web_learner.respect_robots_txt = bool(self.settings.get("ethical_mode", True))
                trusted = self.settings.get("trusted_sources") or []
                # Normalize and store netlocs
                for d in trusted:
                    try:
                        from urllib.parse import urlparse

                        net = urlparse(d).netloc or d
                        self.web_learner.trusted_sources.add(net.lower())
                    except Exception:
                        self.web_learner.trusted_sources.add(d.lower())
            except Exception:
                pass
            self.integration_status = "ready"

            print("Celsius AI Web Learning Integration initialized")

            if self.settings["auto_start_learning"]:
                self.start_learning_process()

            # After initialization, ensure any admin-approved sources are
            # pushed into the learner so they are considered immediately.
            try:
                # Use the same refresh helper that can be invoked later
                self.refresh_approved_sources()
            except Exception:
                # Non-fatal: continue even if refresh fails
                pass

        except Exception as e:
            self.integration_status = f"error: {str(e)}"
            print(f"❌ Error initializing web learning: {str(e)}")

    def start_learning_process(self):
        """Start the continuous learning process"""
        if not self.web_learner:
            print("❌ Web learner not initialized")
            return False

        if self.learning_active:
            print("ℹ️ Learning process already active")
            return True

        self.learning_active = True

        def run_async_learner():
            """Run the learner's async continuous loop in a dedicated event loop."""
            try:
                print("🚀 Starting Celsius AI web learning (async) in background thread...")
                import asyncio

                asyncio.run(self.web_learner.start_continuous_learning())
            except Exception as e:
                print(f"❌ Web learning async runner exited with error: {e}")

        # Start the async learner loop in a background thread
        self.learning_thread = threading.Thread(target=run_async_learner, daemon=True)
        self.learning_thread.start()

        # Indicate background start
        print("Web learning process started in background")
        return True

    def perform_learning_session(self):
        """Perform a single learning session"""
        if not self.web_learner:
            return
        print(f"Starting learning session at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Learn from each topic (limited sources per session)
        topics_learned = 0
        total_content = 0

        for topic in self.web_learner.learning_topics.keys():
            try:
                print(f"Learning about: {topic.replace('_', ' ').title()}")

                # Learn from topic (limited to 2 sources per session)
                # `learn_from_topic` is async in the learner; execute it synchronously
                try:
                    import asyncio

                    asyncio.run(self.web_learner.learn_from_topic(topic, max_sources=2))
                except Exception as e:
                    print(f"Error running async learn_from_topic for {topic}: {e}")

                # Generate and store insights
                insights = self.web_learner.generate_learning_insights(topic)
                for insight in insights:
                    self.web_learner.store_insight(topic, insight)

                topics_learned += 1

                # Small delay between topics
                time.sleep(5)

            except Exception as e:
                print(f"Error learning about {topic}: {str(e)}")
                continue

        # Summary of session
        print(f"Learning session completed: {topics_learned} topics processed")

    def generate_daily_report(self):
        """Generate and store daily learning report"""
        if not self.web_learner:
            return None

        try:
            print("📊 Generating daily learning report...")

            report = self.web_learner.generate_learning_report("daily")

            if report:
                self.last_learning_report = report

                # Save report to file
                if self.settings["save_learning_logs"]:
                    self.save_learning_report(report)

                print("Daily learning report generated")
                return report

        except Exception as e:
            print(f"❌ Error generating daily report: {str(e)}")
            return None

    def save_learning_report(self, report: Dict):
        """Save learning report to file"""
        try:
            # Save to the top-level learning_reports directory so the Hub can find it
            reports_dir = PROJECT_ROOT / "learning_reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            # Per requirements: only save .txt files using MMDDYY HHMM timestamp
            timestamp = datetime.now().strftime("%m%d%y %H%M")
            filename = f"celsius_learning_report_{timestamp}.txt"
            filepath = reports_dir / filename

            enriched = {
                "report_period": report.get("period") or report.get("report_period") or "daily",
                "generated_at": report.get("generated_at") or datetime.now().isoformat(),
                "total_content_learned": report.get("total_content_learned") or report.get("total_content") or 0,
                "insights_generated": report.get("total_insights") or report.get("insights_generated") or 0,
                "top_topics": report.get("top_topics") or report.get("topics") or [],
                "sample_insights": report.get("sample_insights") or report.get("insights") or [],
                "learning_summary": report.get("learning_summary")
                or f"Learned {report.get('total_content_learned', 0)} items with {report.get('total_insights', 0)} insights.",
                "recommendations": report.get("recommendations") or [],
            }

            try:
                from src.utils.report_formatters import format_learning_report_text

                text = format_learning_report_text(enriched)
            except Exception:
                text = f"Celsius Learning Report\nGenerated: {enriched.get('generated_at')}\n\nSummary:\n{enriched.get('learning_summary')}"

            with open(filepath, "w", encoding="utf-8") as ftxt:
                ftxt.write(text)

            print(f"Learning report saved: {filename}")

        except Exception as e:
            print(f"❌ Error saving learning report: {str(e)}")

    def get_learning_status(self) -> Dict:
        """Get current learning status"""
        status = {
            "integration_status": self.integration_status,
            "learning_active": self.learning_active,
            "learner_available": self.web_learner is not None,
            "settings": self.settings.copy(),
            "last_report_time": None,
            "total_content_learned": 0,
            "total_insights": 0,
        }

        if self.last_learning_report:
            status["last_report_time"] = self.last_learning_report.get("generated_at")
            status["total_content_learned"] = self.last_learning_report.get("total_content_learned", 0)
            status["total_insights"] = self.last_learning_report.get("insights_generated", 0)

        # Get database stats if available
        if self.web_learner:
            try:
                import sqlite3

                conn = sqlite3.connect(self.web_learner.db_path)
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM learned_content")
                status["total_content_learned"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM learning_insights")
                status["total_insights"] = cursor.fetchone()[0]

                conn.close()

            except Exception:
                pass

        return status

    def get_recent_insights(self, limit: int = 5) -> List[Dict]:
        """Get recent learning insights"""
        if not self.web_learner:
            return []

        try:
            import sqlite3

            conn = sqlite3.connect(self.web_learner.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT topic, insight, confidence_score, timestamp, insight_type
                FROM learning_insights 
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (limit,),
            )

            insights = cursor.fetchall()
            conn.close()

            return [
                {
                    "topic": insight[0],
                    "insight": insight[1],
                    "confidence": insight[2],
                    "timestamp": insight[3],
                    "type": insight[4],
                }
                for insight in insights
            ]

        except Exception as e:
            print(f"❌ Error getting recent insights: {str(e)}")
            return []

    def search_learned_content(self, query: str, topic: Optional[str] = None) -> List[Dict]:
        """Search through learned content"""
        if not self.web_learner:
            return []

        try:
            import sqlite3

            conn = sqlite3.connect(self.web_learner.db_path)
            cursor = conn.cursor()

            # Build search query
            sql = """
                SELECT url, title, content_summary, topic, quality_score, timestamp
                FROM learned_content
                WHERE (title LIKE ? OR content_summary LIKE ? OR keywords LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%", f"%{query}%"]

            if topic:
                sql += " AND topic = ?"
                params.append(topic)

            sql += " ORDER BY quality_score DESC, timestamp DESC LIMIT 10"

            cursor.execute(sql, params)
            results = cursor.fetchall()
            conn.close()

            return [
                {
                    "url": result[0],
                    "title": result[1],
                    "summary": result[2][:200] + "..." if len(result[2]) > 200 else result[2],
                    "topic": result[3],
                    "quality": result[4],
                    "timestamp": result[5],
                }
                for result in results
            ]

        except Exception as e:
            print(f"❌ Error searching learned content: {str(e)}")
            return []

    def stop_learning(self):
        """Stop the learning process"""
        self.learning_active = False
        print("🛑 Stopping web learning process...")

        if self.web_learner:
            self.web_learner.stop_learning()

    print("Web learning process stopped")

    def restart_learning(self):
        """Restart the learning process"""
        self.stop_learning()
        time.sleep(2)
        self.start_learning_process()

    def update_settings(self, new_settings: Dict):
        """Update learning settings"""
        for key, value in new_settings.items():
            if key in self.settings:
                self.settings[key] = value

        print(f"⚙️ Learning settings updated: {list(new_settings.keys())}")

    def get_learning_summary(self) -> str:
        """Get a human-readable learning summary"""
        status = self.get_learning_status()

        if not status["learner_available"]:
            return "❌ Web learning not available - learner not initialized"

        if not status["learning_active"]:
            return "⏸️ Web learning is paused"

        summary_parts = [
            f"🌐 Web Learning Status: {'Active' if status['learning_active'] else 'Inactive'}",
            f"📚 Content Learned: {status['total_content_learned']} articles",
            f"💡 Insights Generated: {status['total_insights']} insights",
            f"⏰ Learning Interval: {status['settings']['learning_interval_hours']} hours",
            f"🎯 Daily Session Limit: {status['settings']['max_learning_sessions_per_day']}",
            f"🛡️ Ethical Mode: {'Enabled' if status['settings']['ethical_mode'] else 'Disabled'}",
        ]

        if status["last_report_time"]:
            last_report = datetime.fromisoformat(status["last_report_time"])
            summary_parts.append(f"📊 Last Report: {last_report.strftime('%Y-%m-%d %H:%M')}")

        return "\n".join(summary_parts)

    def refresh_approved_sources(self) -> int:
        """Reload `data/ingestion_approved.json` and push approved
        sources into the running learner.

        Returns the number of sources added (best-effort).
        """
        try:
            approved_file = PROJECT_ROOT / "data" / "ingestion_approved.json"
            if not approved_file.exists():
                return 0

            try:
                with open(approved_file, "r", encoding="utf-8") as f:
                    approved = json.load(f) or []
            except Exception:
                approved = []

            approved_sources = []
            # local import to avoid relying on outer imports
            try:
                from urllib.parse import urlparse
            except Exception:
                urlparse = None
            for entry in approved:
                src = entry.get("source") or entry.get("url") or entry.get("feed")
                if not src:
                    continue
                approved_sources.append(src)
                # add netloc to trusted_sources for robots checks
                try:
                    if urlparse:
                        net = urlparse(src).netloc or src
                    else:
                        net = src
                    if hasattr(self, "web_learner") and self.web_learner:
                        try:
                            self.web_learner.trusted_sources.add(net.lower())
                        except Exception:
                            pass
                except Exception:
                    pass

            if approved_sources and hasattr(self, "web_learner") and self.web_learner:
                try:
                    topic_name = "approved_sources"
                    if topic_name not in self.web_learner.learning_topics:
                        self.web_learner.learning_topics[topic_name] = {"keywords": [], "sources": []}
                    existing = set(self.web_learner.learning_topics[topic_name]["sources"])
                    added = 0
                    for s in approved_sources:
                        if s not in existing:
                            self.web_learner.learning_topics[topic_name]["sources"].append(s)
                            existing.add(s)
                            added += 1
                    return added
                except Exception:
                    return 0

            return 0
        except Exception as e:
            # Record internal status briefly for diagnostics
            try:
                self.integration_status = f"error_refresh_approved:{e}"
            except Exception:
                pass
            return 0


# Global instance for integration
web_learning_integration = None


def initialize_web_learning():
    """Initialize the global web learning integration"""
    global web_learning_integration

    if web_learning_integration is None:
        web_learning_integration = CelsiusWebLearningIntegration()

    return web_learning_integration


def refresh_web_learning_approved_sources() -> int:
    """Convenience helper: ensure the global integration exists and
    refresh its approved sources. Returns number of sources added.
    """
    try:
        integration = initialize_web_learning()
        if integration:
            return integration.refresh_approved_sources()
    except Exception:
        pass
    return 0


async def get_web_learning_integration():
    """Get or create web learning integration instance (async version)"""
    return initialize_web_learning()


def get_web_learning_status():
    """Get web learning status"""
    if web_learning_integration:
        return web_learning_integration.get_learning_status()
    return {"integration_status": "not_initialized"}


def test_web_learning_integration():
    """Test the web learning integration"""
    print("TESTING CELSIUS AI WEB LEARNING INTEGRATION")
    print("=" * 60)

    # Initialize integration
    integration = initialize_web_learning()

    # Show status
    status = integration.get_learning_status()
    print(f"Integration Status: {status['integration_status']}")
    print(f"Learning Active: {status['learning_active']}")
    print(f"Learner Available: {status['learner_available']}")

    # Show settings
    print("\nSettings:")
    for key, value in status["settings"].items():
        print(f"  {key}: {value}")

    # Show summary
    print("\n" + "=" * 40)
    print("LEARNING SUMMARY")
    print("=" * 40)
    print(integration.get_learning_summary())

    # Test search functionality
    print("\n" + "=" * 40)
    print("TESTING SEARCH")
    print("=" * 40)

    # This will return empty results initially as no content is learned yet
    search_results = integration.search_learned_content("security")
    print(f"Search results for 'security': {len(search_results)} items")

    recent_insights = integration.get_recent_insights()
    print(f"Recent insights: {len(recent_insights)} items")

    print("\nWeb learning integration test completed!")


if __name__ == "__main__":
    test_web_learning_integration()
