#!/usr/bin/env python3
"""
Celsius AI Web Learning Launcher
Simple interface to start and monitor web learning
"""

import os
import sys
import time
import threading
from datetime import datetime

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)


class CelsiusWebLearningLauncher:
    """Simple launcher for Celsius AI web learning"""

    def __init__(self):
        self.learning_active = False
        self.learner = None

    def display_banner(self):
        """Display startup banner"""
        print()
        print("=" * 60)
        print("         CELSIUS AI WEB LEARNING SYSTEM")
        print("=" * 60)
        print("Intelligent web learning with ethical boundaries")
        print()

    def initialize_learner(self):
        """Initialize the web learning system"""
        try:
            from celsius_web_learner import CelsiusWebLearner

            self.learner = CelsiusWebLearner()
            print("Web learning system initialized successfully!")
            return True
        except Exception as e:
            print(f"Error initializing web learner: {str(e)}")
            return False

    def show_menu(self):
        """Show main menu options"""
        print("\nAVAILABLE COMMANDS:")
        print("------------------")
        print("1. start    - Start continuous web learning")
        print("2. status   - Show learning status")
        print("3. learn    - Perform single learning session")
        print("4. report   - Generate learning report")
        print("5. search   - Search learned content")
        print("6. insights - Show recent insights")
        print("7. dashboard- Launch monitoring dashboard")
        print("8. stop     - Stop web learning")
        print("9. help     - Show this menu")
        print("0. quit     - Exit program")
        print()

    def start_continuous_learning(self):
        """Start continuous web learning"""
        if not self.learner:
            print("Error: Web learner not initialized")
            return

        if self.learning_active:
            print("Web learning is already active!")
            return

        print("Starting continuous web learning...")
        self.learning_active = True

        def learning_loop():
            session_count = 0
            while self.learning_active:
                try:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Learning Session #{session_count + 1}")

                    # Learn from each topic (limited)
                    for topic in list(self.learner.learning_topics.keys())[:2]:  # Limit to 2 topics per session
                        if not self.learning_active:
                            break

                        print(f"  Learning about: {topic.replace('_', ' ').title()}")
                        self.learner.learn_from_topic(topic, max_sources=1)

                        # Generate insights
                        insights = self.learner.generate_learning_insights(topic)
                        for insight in insights:
                            self.learner.store_insight(topic, insight)

                        time.sleep(5)  # Brief pause between topics

                    session_count += 1
                    print(f"  Session {session_count} completed")

                    # Sleep for 10 minutes between sessions (demo purposes)
                    if self.learning_active:
                        print("  Next session in 10 minutes...")
                        time.sleep(600)

                except Exception as e:
                    print(f"Error in learning session: {str(e)}")
                    time.sleep(60)  # Wait 1 minute on error

        learning_thread = threading.Thread(target=learning_loop, daemon=True)
        learning_thread.start()

        print("Continuous web learning started in background!")
        print("Use 'status' to check progress or 'stop' to halt learning")

    def show_status(self):
        """Show learning status"""
        if not self.learner:
            print("Web learner not initialized")
            return

        try:
            import sqlite3

            conn = sqlite3.connect(self.learner.db_path)
            cursor = conn.cursor()

            # Get statistics
            cursor.execute("SELECT COUNT(*) FROM learned_content")
            total_content = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM learning_insights")
            total_insights = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT topic, COUNT(*) as count, AVG(quality_score) as avg_quality
                FROM learned_content 
                GROUP BY topic
                ORDER BY count DESC
            """
            )
            topic_stats = cursor.fetchall()

            conn.close()

            print("\nLEARNING STATUS:")
            print("----------------")
            print(f"Learning Active: {'YES' if self.learning_active else 'NO'}")
            print(f"Total Content: {total_content} articles")
            print(f"Total Insights: {total_insights} insights")

            if topic_stats:
                print("\nTopic Breakdown:")
                for topic, count, quality in topic_stats:
                    print(f"  {topic.title()}: {count} articles (Quality: {quality:.2f})")

        except Exception as e:
            print(f"Error getting status: {str(e)}")

    def perform_single_learning(self):
        """Perform a single learning session"""
        if not self.learner:
            print("Web learner not initialized")
            return

        print("Starting single learning session...")
        print("This will learn from one source per topic...")

        learned_count = 0
        for topic in self.learner.learning_topics.keys():
            try:
                print(f"Learning about: {topic.replace('_', ' ').title()}")
                self.learner.learn_from_topic(topic, max_sources=1)
                learned_count += 1
            except Exception as e:
                print(f"Error learning about {topic}: {str(e)}")

        print(f"Single learning session completed! Processed {learned_count} topics")

    def generate_report(self):
        """Generate learning report"""
        if not self.learner:
            print("Web learner not initialized")
            return

        try:
            print("Generating learning report...")
            report = self.learner.generate_learning_report("daily")

            if report:
                print("\nDAILY LEARNING REPORT:")
                print("----------------------")
                print(f"Report Period: {report['report_period']}")
                print(f"Topics Covered: {report['topics_covered']}")
                print(f"Content Learned: {report['total_content_learned']}")
                print(f"Insights Generated: {report['insights_generated']}")
                print(f"\nSummary: {report['learning_summary']}")

                if report.get("recommendations"):
                    print("\nRecommendations:")
                    for i, rec in enumerate(report["recommendations"], 1):
                        print(f"  {i}. {rec}")
            else:
                print("No report data available yet")

        except Exception as e:
            print(f"Error generating report: {str(e)}")

    def search_content(self):
        """Search learned content"""
        if not self.learner:
            print("Web learner not initialized")
            return

        query = input("Enter search query: ").strip()
        if not query:
            print("No search query provided")
            return

        try:
            import sqlite3

            conn = sqlite3.connect(self.learner.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT title, topic, url, quality_score
                FROM learned_content
                WHERE title LIKE ? OR content_summary LIKE ?
                ORDER BY quality_score DESC
                LIMIT 10
            """,
                (f"%{query}%", f"%{query}%"),
            )

            results = cursor.fetchall()
            conn.close()

            if results:
                print(f"\nSearch Results for '{query}':")
                print("-" * 40)
                for i, (title, topic, url, quality) in enumerate(results, 1):
                    print(f"{i}. {title}")
                    print(f"   Topic: {topic.title()} | Quality: {quality:.2f}")
                    print(f"   URL: {url}")
                    print()
            else:
                print("No results found")

        except Exception as e:
            print(f"Error searching content: {str(e)}")

    def show_insights(self):
        """Show recent insights"""
        if not self.learner:
            print("Web learner not initialized")
            return

        try:
            import sqlite3

            conn = sqlite3.connect(self.learner.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT topic, insight, confidence_score, timestamp
                FROM learning_insights
                ORDER BY timestamp DESC
                LIMIT 5
            """
            )

            insights = cursor.fetchall()
            conn.close()

            if insights:
                print("\nRECENT INSIGHTS:")
                print("----------------")
                for topic, insight, confidence, timestamp in insights:
                    print(f"Topic: {topic.title()}")
                    print(f"Confidence: {confidence:.0%}")
                    print(f"Time: {timestamp}")
                    print(f"Insight: {insight}")
                    print("-" * 40)
            else:
                print("No insights generated yet")

        except Exception as e:
            print(f"Error getting insights: {str(e)}")

    def launch_dashboard(self):
        """Launch monitoring dashboard"""
        try:
            print("Launching web learning dashboard...")
            print("Note: Dashboard will open in a new window")

            from celsius_web_learning_dashboard import WebLearningDashboard

            dashboard = WebLearningDashboard()

            # Run dashboard in separate thread to keep launcher active
            dashboard_thread = threading.Thread(target=dashboard.run, daemon=True)
            dashboard_thread.start()

            print("Dashboard launched successfully!")
            print("You can continue using this launcher while dashboard runs")

        except Exception as e:
            print(f"Error launching dashboard: {str(e)}")

    def stop_learning(self):
        """Stop web learning"""
        if self.learning_active:
            self.learning_active = False
            if self.learner:
                self.learner.stop_learning()
            print("Web learning stopped")
        else:
            print("Web learning is not currently active")

    def run(self):
        """Run the launcher"""
        self.display_banner()

        # Initialize learner
        if not self.initialize_learner():
            print("Failed to initialize web learner. Exiting.")
            return

        self.show_menu()

        while True:
            try:
                command = input("Celsius Web Learning> ").strip().lower()

                if command in ["1", "start"]:
                    self.start_continuous_learning()
                elif command in ["2", "status"]:
                    self.show_status()
                elif command in ["3", "learn"]:
                    self.perform_single_learning()
                elif command in ["4", "report"]:
                    self.generate_report()
                elif command in ["5", "search"]:
                    self.search_content()
                elif command in ["6", "insights"]:
                    self.show_insights()
                elif command in ["7", "dashboard"]:
                    self.launch_dashboard()
                elif command in ["8", "stop"]:
                    self.stop_learning()
                elif command in ["9", "help"]:
                    self.show_menu()
                elif command in ["0", "quit", "exit"]:
                    self.stop_learning()
                    print("Goodbye!")
                    break
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' to see available commands")

            except KeyboardInterrupt:
                print("\nStopping...")
                self.stop_learning()
                break
            except EOFError:
                print("\nGoodbye!")
                self.stop_learning()
                break
            except Exception as e:
                print(f"Error: {str(e)}")


def main():
    """Main entry point"""
    launcher = CelsiusWebLearningLauncher()
    launcher.run()


if __name__ == "__main__":
    main()
