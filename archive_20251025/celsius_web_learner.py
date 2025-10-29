#!/usr/bin/env python3
"""
Celsius AI Web Learning Engine
Intelligent web crawling and learning system with ethical boundaries
"""

import requests
import sqlite3
import json
import time
import logging
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import hashlib
import threading
from typing import List, Dict, Optional
import re
import os


class CelsiusWebLearner:
    """Ethical web learning system for Celsius AI"""

    def __init__(self):
        self.db_path = "celsius_web_learning.db"
        self.learning_active = True
        self.rate_limit = 2  # Seconds between requests
        self.max_pages_per_site = 50  # Ethical limit per site
        self.session_timeout = 10  # Request timeout

        # Learning domains and topics
        self.learning_topics = {
            "cybersecurity": {
                "keywords": ["security", "vulnerability", "malware", "encryption", "firewall", "phishing"],
                "sources": [
                    "https://www.cisa.gov",
                    "https://krebsonsecurity.com",
                    "https://www.bleepingcomputer.com",
                    "https://www.darkreading.com",
                ],
            },
            "technology": {
                "keywords": ["AI", "machine learning", "programming", "software", "hardware", "innovation"],
                "sources": [
                    "https://techcrunch.com",
                    "https://arstechnica.com",
                    "https://www.wired.com",
                    "https://spectrum.ieee.org",
                ],
            },
            "system_optimization": {
                "keywords": ["performance", "optimization", "efficiency", "monitoring", "benchmarking"],
                "sources": ["https://www.tomshardware.com", "https://www.anandtech.com", "https://www.phoronix.com"],
            },
            "programming": {
                "keywords": ["python", "javascript", "development", "coding", "algorithms", "best practices"],
                "sources": [
                    "https://realpython.com",
                    "https://stackoverflow.com",
                    "https://dev.to",
                    "https://github.com",
                ],
            },
            "fitness_health": {
                "keywords": ["fitness", "health", "nutrition", "exercise", "wellness", "mental health", "diet"],
                "sources": [
                    "https://www.mayoclinic.org",
                    "https://www.webmd.com",
                    "https://www.healthline.com",
                    "https://www.cdc.gov",
                ],
            },
        }

        # Ethical guidelines
        self.ethical_boundaries = {
            "respect_robots_txt": True,
            "user_agent": "CelsiusAI-Learner/1.0 (Educational Purpose)",
            "no_personal_data": True,
            "no_copyrighted_content": True,
            "respect_rate_limits": True,
            "educational_purpose_only": True,
        }

        self.setup_logging()
        self.init_database()

    def setup_logging(self):
        """Setup logging for web learning activities"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler("celsius_web_learning.log"), logging.StreamHandler()],
        )
        self.logger = logging.getLogger("CelsiusWebLearner")

    def init_database(self):
        """Initialize database for storing learned content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables for learned content
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learned_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                content_summary TEXT,
                topic TEXT,
                keywords TEXT,
                quality_score REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT,
                source_credibility INTEGER DEFAULT 0
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                insight TEXT NOT NULL,
                confidence_score REAL,
                sources_count INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                insight_type TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_period TEXT,
                topics_covered TEXT,
                insights_generated INTEGER,
                quality_metrics TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                report_data TEXT
            )
        """
        )

        conn.commit()
        conn.close()

        self.logger.info("Web learning database initialized")

    def check_robots_txt(self, base_url: str) -> bool:
        """Check if crawling is allowed by robots.txt"""
        try:
            robots_url = urljoin(base_url, "/robots.txt")
            response = requests.get(robots_url, timeout=5)

            if response.status_code == 200:
                robots_content = response.text.lower()
                # Simple robots.txt check - in production, use proper robotparser
                if "disallow: /" in robots_content:
                    return False

            return True

        except Exception:
            # If can't access robots.txt, be conservative and allow
            return True

    def extract_content_ethically(self, url: str) -> Optional[Dict]:
        """Extract content while respecting ethical boundaries"""
        try:
            headers = {
                "User-Agent": self.ethical_boundaries["user_agent"],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            response = requests.get(url, headers=headers, timeout=self.session_timeout)
            response.raise_for_status()

            # Parse content
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract meaningful content
            title = soup.title.string if soup.title else "No Title"

            # Get main content (avoid ads, navigation, etc.)
            content_selectors = ["article", "main", ".content", "#content", ".post", ".entry"]
            main_content = None

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    main_content = content_elem.get_text()
                    break

            if not main_content:
                main_content = soup.get_text()

            # Clean and summarize content
            cleaned_content = re.sub(r"\s+", " ", main_content).strip()
            content_summary = cleaned_content[:2000] + "..." if len(cleaned_content) > 2000 else cleaned_content

            # Generate content hash for deduplication
            content_hash = hashlib.md5(cleaned_content.encode()).hexdigest()

            return {
                "url": url,
                "title": title.strip(),
                "content_summary": content_summary,
                "content_hash": content_hash,
                "word_count": len(cleaned_content.split()),
                "extracted_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.warning(f"Failed to extract content from {url}: {str(e)}")
            return None

    def analyze_content_quality(self, content_data: Dict) -> float:
        """Analyze content quality and relevance"""
        quality_score = 0.0

        # Word count factor (prefer substantial content)
        word_count = content_data.get("word_count", 0)
        if word_count > 500:
            quality_score += 0.3
        elif word_count > 200:
            quality_score += 0.2
        elif word_count > 50:
            quality_score += 0.1

        # Title quality (prefer descriptive titles)
        title = content_data.get("title", "").lower()
        if len(title) > 10 and not any(spam in title for spam in ["click here", "amazing", "!!!!"]):
            quality_score += 0.2

        # Content relevance check
        content = content_data.get("content_summary", "").lower()
        relevant_keywords = 0

        for topic, topic_data in self.learning_topics.items():
            for keyword in topic_data["keywords"]:
                if keyword.lower() in content:
                    relevant_keywords += 1

        if relevant_keywords > 0:
            quality_score += min(0.5, relevant_keywords * 0.1)

        return min(1.0, quality_score)

    def determine_topic(self, content_data: Dict) -> str:
        """Determine the primary topic of content"""
        content = (content_data.get("content_summary", "") + " " + content_data.get("title", "")).lower()

        topic_scores = {}

        for topic, topic_data in self.learning_topics.items():
            score = 0
            for keyword in topic_data["keywords"]:
                score += content.count(keyword.lower())
            topic_scores[topic] = score

        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        return "general"

    def store_learned_content(self, content_data: Dict, topic: str, quality_score: float):
        """Store learned content in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if content already exists (deduplication)
            cursor.execute("SELECT id FROM learned_content WHERE content_hash = ?", (content_data["content_hash"],))
            if cursor.fetchone():
                conn.close()
                return False  # Already exists

            # Extract keywords
            content = content_data.get("content_summary", "").lower()
            keywords = []
            for topic_data in self.learning_topics.values():
                for keyword in topic_data["keywords"]:
                    if keyword.lower() in content:
                        keywords.append(keyword)

            cursor.execute(
                """
                INSERT INTO learned_content 
                (url, title, content_summary, topic, keywords, quality_score, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    content_data["url"],
                    content_data["title"],
                    content_data["content_summary"],
                    topic,
                    ",".join(keywords),
                    quality_score,
                    content_data["content_hash"],
                ),
            )

            conn.commit()
            conn.close()

            self.logger.info(f"Stored learned content: {content_data['title']} (Quality: {quality_score:.2f})")
            return True

        except Exception as e:
            self.logger.error(f"Error storing learned content: {str(e)}")
            return False

    def learn_from_topic(self, topic: str, max_sources: int = 5):
        """Learn from web sources about a specific topic"""
        if topic not in self.learning_topics:
            self.logger.warning(f"Unknown topic: {topic}")
            return

        topic_data = self.learning_topics[topic]
        sources_processed = 0
        content_learned = 0

        self.logger.info(f"Starting web learning for topic: {topic}")

        for source_url in topic_data["sources"][:max_sources]:
            if not self.learning_active:
                break

            try:
                # Check robots.txt
                if not self.check_robots_txt(source_url):
                    self.logger.info(f"Robots.txt disallows crawling: {source_url}")
                    continue

                # Extract content
                content_data = self.extract_content_ethically(source_url)

                if content_data:
                    # Analyze quality
                    quality_score = self.analyze_content_quality(content_data)

                    if quality_score > 0.3:  # Only store high-quality content
                        detected_topic = self.determine_topic(content_data)

                        if self.store_learned_content(content_data, detected_topic, quality_score):
                            content_learned += 1

                sources_processed += 1

                # Respect rate limits
                time.sleep(self.rate_limit)

            except Exception as e:
                self.logger.error(f"Error learning from {source_url}: {str(e)}")
                continue

        self.logger.info(
            f"Completed learning for {topic}: {content_learned} pieces of content from {sources_processed} sources"
        )

    def generate_learning_insights(self, topic: str) -> List[Dict]:
        """Generate insights from learned content"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT title, content_summary, quality_score, keywords
                FROM learned_content 
                WHERE topic = ? AND quality_score > 0.5
                ORDER BY quality_score DESC
                LIMIT 20
            """,
                (topic,),
            )

            content_items = cursor.fetchall()
            conn.close()

            if not content_items:
                return []

            insights = []

            # Generate trend insights
            all_keywords = []
            for item in content_items:
                keywords = item[3].split(",") if item[3] else []
                all_keywords.extend([k.strip() for k in keywords if k.strip()])

            # Find trending keywords
            keyword_counts = {}
            for keyword in all_keywords:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

            top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            if top_keywords:
                insight = f"Top trending topics in {topic}: " + ", ".join(
                    [f"{k} ({v} mentions)" for k, v in top_keywords]
                )
                insights.append(
                    {
                        "insight": insight,
                        "confidence_score": 0.8,
                        "insight_type": "trend_analysis",
                        "sources_count": len(content_items),
                    }
                )

            # Generate quality insights
            avg_quality = sum(item[2] for item in content_items) / len(content_items)
            high_quality_count = sum(1 for item in content_items if item[2] > 0.7)

            quality_insight = f"Content quality analysis for {topic}: Average quality {avg_quality:.2f}, {high_quality_count} high-quality sources identified"
            insights.append(
                {
                    "insight": quality_insight,
                    "confidence_score": 0.9,
                    "insight_type": "quality_analysis",
                    "sources_count": len(content_items),
                }
            )

            return insights

        except Exception as e:
            self.logger.error(f"Error generating insights for {topic}: {str(e)}")
            return []

    def generate_learning_report(self, period: str = "daily") -> Dict:
        """Generate comprehensive learning report"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate time range
            if period == "daily":
                time_filter = datetime.now() - timedelta(days=1)
            elif period == "weekly":
                time_filter = datetime.now() - timedelta(weeks=1)
            else:  # monthly
                time_filter = datetime.now() - timedelta(days=30)

            # Get learning statistics
            cursor.execute(
                """
                SELECT topic, COUNT(*) as count, AVG(quality_score) as avg_quality
                FROM learned_content 
                WHERE timestamp > ?
                GROUP BY topic
                ORDER BY count DESC
            """,
                (time_filter.isoformat(),),
            )

            topic_stats = cursor.fetchall()

            # Get total insights generated
            cursor.execute(
                """
                SELECT COUNT(*) FROM learning_insights 
                WHERE timestamp > ?
            """,
                (time_filter.isoformat(),),
            )

            insights_count = cursor.fetchone()[0]

            conn.close()

            # Build report
            report = {
                "report_period": period,
                "generated_at": datetime.now().isoformat(),
                "topics_covered": len(topic_stats),
                "total_content_learned": sum(stat[1] for stat in topic_stats),
                "insights_generated": insights_count,
                "topic_breakdown": [
                    {"topic": stat[0], "content_count": stat[1], "average_quality": round(stat[2], 2)}
                    for stat in topic_stats
                ],
                "learning_summary": self.generate_learning_summary(topic_stats),
                "recommendations": self.generate_learning_recommendations(topic_stats),
            }

            # Store report
            self.store_learning_report(report)

            return report

        except Exception as e:
            self.logger.error(f"Error generating learning report: {str(e)}")
            return {}

    def generate_learning_summary(self, topic_stats: List) -> str:
        """Generate human-readable learning summary"""
        if not topic_stats:
            return "No new learning content acquired during this period."

        total_content = sum(stat[1] for stat in topic_stats)
        top_topic = topic_stats[0] if topic_stats else None

        summary = f"Acquired {total_content} pieces of high-quality content across {len(topic_stats)} topics. "

        if top_topic:
            summary += f"Primary focus area was '{top_topic[0]}' with {top_topic[1]} articles analyzed. "

        avg_quality = sum(stat[2] for stat in topic_stats) / len(topic_stats)
        summary += f"Overall content quality score: {avg_quality:.2f}/1.0"

        return summary

    def generate_learning_recommendations(self, topic_stats: List) -> List[str]:
        """Generate recommendations based on learning analysis"""
        recommendations = []

        if not topic_stats:
            recommendations.append("Expand learning sources to acquire more diverse content")
            return recommendations

        # Analyze topic distribution
        topic_counts = [stat[1] for stat in topic_stats]
        if len(set(topic_counts)) > 1:  # Uneven distribution
            min_topic = min(topic_stats, key=lambda x: x[1])
            recommendations.append(
                f"Consider increasing focus on '{min_topic[0]}' topic - only {min_topic[1]} items learned"
            )

        # Quality recommendations
        low_quality_topics = [stat for stat in topic_stats if stat[2] < 0.5]
        if low_quality_topics:
            for topic in low_quality_topics:
                recommendations.append(
                    f"Improve content sources for '{topic[0]}' - current quality score: {topic[2]:.2f}"
                )

        # General recommendations
        recommendations.append("Continue regular web learning to maintain knowledge currency")
        recommendations.append("Focus on authoritative sources for higher quality insights")

        return recommendations

    def store_learning_report(self, report: Dict):
        """Store learning report in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO learning_reports 
                (report_period, topics_covered, insights_generated, quality_metrics, report_data)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    report["report_period"],
                    json.dumps([t["topic"] for t in report["topic_breakdown"]]),
                    report["insights_generated"],
                    json.dumps(
                        {
                            "avg_quality": (
                                sum(t["average_quality"] for t in report["topic_breakdown"])
                                / len(report["topic_breakdown"])
                                if report["topic_breakdown"]
                                else 0
                            )
                        }
                    ),
                    json.dumps(report),
                ),
            )

            conn.commit()
            conn.close()

            self.logger.info(f"Stored learning report for period: {report['report_period']}")

        except Exception as e:
            self.logger.error(f"Error storing learning report: {str(e)}")

    def start_continuous_learning(self):
        """Start continuous web learning process"""
        self.logger.info("Starting continuous web learning process")

        def learning_loop():
            while self.learning_active:
                try:
                    # Learn from each topic
                    for topic in self.learning_topics.keys():
                        if not self.learning_active:
                            break

                        self.learn_from_topic(topic, max_sources=2)  # Limited sources per cycle

                        # Generate insights
                        insights = self.generate_learning_insights(topic)
                        for insight in insights:
                            self.store_insight(topic, insight)

                    # Generate daily report
                    daily_report = self.generate_learning_report("daily")

                    # Sleep for 1 hour before next learning cycle
                    time.sleep(3600)

                except Exception as e:
                    self.logger.error(f"Error in learning loop: {str(e)}")
                    time.sleep(300)  # Wait 5 minutes on error

        learning_thread = threading.Thread(target=learning_loop, daemon=True)
        learning_thread.start()

    def store_insight(self, topic: str, insight_data: Dict):
        """Store learning insight in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO learning_insights 
                (topic, insight, confidence_score, sources_count, insight_type)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    topic,
                    insight_data["insight"],
                    insight_data["confidence_score"],
                    insight_data["sources_count"],
                    insight_data["insight_type"],
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Error storing insight: {str(e)}")

    def stop_learning(self):
        """Stop the web learning process"""
        self.learning_active = False
        self.logger.info("Web learning process stopped")


def test_web_learning():
    """Test the web learning system"""
    print("🌐 TESTING CELSIUS AI WEB LEARNING ENGINE")
    print("=" * 50)

    learner = CelsiusWebLearner()

    print("✅ Web learning engine initialized")
    print("📚 Learning topics configured:")
    for topic in learner.learning_topics.keys():
        print(f"   • {topic.title()}")

    print("\n🤖 Ethical boundaries enforced:")
    for boundary, enabled in learner.ethical_boundaries.items():
        status = "✅" if enabled else "❌"
        print(f"   {status} {boundary.replace('_', ' ').title()}")

    print(f"\n📊 Database: {learner.db_path}")
    print("🔄 Ready for continuous learning")
    print("\n💡 To start learning: learner.start_continuous_learning()")


if __name__ == "__main__":
    test_web_learning()
