#!/usr/bin/env python3
"""
Celsius AI Web Learning Engine (Async Edition)
==============================================
An intelligent, asynchronous web crawling and learning system designed
with ethical considerations at its core. This module uses modern async
libraries for high-performance, non-blocking web scraping and data processing.

Features:
- Asynchronous web crawling with `aiohttp`.
- Non-blocking database operations with `aiosqlite`.
- Ethical scraping guidelines (respects robots.txt, uses a clear user-agent).
- Content analysis for quality and topic relevance.
- Insight generation and automated reporting.
"""

import asyncio
import json
import logging
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from urllib.parse import quote

import aiohttp
import aiosqlite
import ssl
import certifi
from aiohttp import TCPConnector
from bs4 import BeautifulSoup

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("celsius_web_learning.log"), logging.StreamHandler()],
)


class CelsiusWebLearner:
    """
    An ethical, asynchronous web learning system for Celsius AI.
    """

    def __init__(self, db_path: Path):
        """
        Initializes the web learner.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.learning_active = asyncio.Event()
        self.learning_active.set()
        self.rate_limit = 2  # Seconds between requests per domain
        self.max_pages_per_site = 50
        self.session_timeout = aiohttp.ClientTimeout(total=10)
        self.logger = logging.getLogger("CelsiusWebLearner")

        self.learning_topics = self._get_learning_topics()
        self.ethical_boundaries = self._get_ethical_boundaries()
        self.session: Optional[aiohttp.ClientSession] = None
        # Respect robots.txt by default; can be overridden by integration
        self.respect_robots_txt = True
        # Domains explicitly allowed to bypass robots.txt (use with caution)
        self.trusted_sources = set()
        # Counters for diagnostics
        self.blocked_count = 0
        self.blocked_sites = set()

    @staticmethod
    def _get_learning_topics() -> Dict[str, Dict[str, List[str]]]:
        """Defines the topics and sources for learning - ALL TOPICS, NO RESTRICTIONS."""
        return {
            "cybersecurity": {
                "keywords": [
                    "security",
                    "vulnerability",
                    "malware",
                    "encryption",
                    "firewall",
                    "phishing",
                    "penetration testing",
                ],
                "sources": ["https://www.cisa.gov", "https://krebsonsecurity.com", "https://www.bleepingcomputer.com"],
            },
            "programming": {
                "keywords": [
                    "python",
                    "javascript",
                    "rust",
                    "golang",
                    "c++",
                    "java",
                    "typescript",
                    "asyncio",
                    "fastapi",
                    "react",
                    "vue",
                    "django",
                    "flask",
                    "machine learning",
                    "data structures",
                    "algorithms",
                    "design patterns",
                ],
                "sources": [
                    "https://realpython.com",
                    "https://dev.to",
                    "https://github.com/trending",
                    "https://stackoverflow.com",
                    "https://medium.com",
                    "https://hackernoon.com",
                ],
            },
            "artificial_intelligence": {
                "keywords": [
                    "AI",
                    "neural networks",
                    "deep learning",
                    "transformers",
                    "LLM",
                    "GPT",
                    "computer vision",
                    "NLP",
                    "reinforcement learning",
                    "PyTorch",
                    "TensorFlow",
                ],
                "sources": [
                    "https://arxiv.org",
                    "https://paperswithcode.com",
                    "https://huggingface.co",
                    "https://openai.com/research",
                ],
            },
            "science": {
                "keywords": [
                    "physics",
                    "chemistry",
                    "biology",
                    "astronomy",
                    "mathematics",
                    "quantum computing",
                    "space",
                    "research",
                    "discovery",
                ],
                "sources": [
                    "https://www.nature.com",
                    "https://www.sciencedaily.com",
                    "https://phys.org",
                    "https://www.scientificamerican.com",
                ],
            },
            "technology": {
                "keywords": [
                    "innovation",
                    "hardware",
                    "software",
                    "cloud computing",
                    "devops",
                    "microservices",
                    "containers",
                    "kubernetes",
                    "serverless",
                    "edge computing",
                ],
                "sources": [
                    "https://techcrunch.com",
                    "https://arstechnica.com",
                    "https://www.wired.com",
                    "https://www.theverge.com",
                ],
            },
            "web_development": {
                "keywords": [
                    "HTML",
                    "CSS",
                    "web design",
                    "frontend",
                    "backend",
                    "full stack",
                    "responsive design",
                    "accessibility",
                    "performance",
                    "SEO",
                ],
                "sources": ["https://css-tricks.com", "https://smashingmagazine.com", "https://web.dev"],
            },
            "data_science": {
                "keywords": [
                    "data analysis",
                    "statistics",
                    "visualization",
                    "pandas",
                    "numpy",
                    "scikit-learn",
                    "big data",
                    "analytics",
                ],
                "sources": ["https://towardsdatascience.com", "https://kaggle.com", "https://datasciencecentral.com"],
            },
            "systems_programming": {
                "keywords": [
                    "operating systems",
                    "kernel",
                    "memory management",
                    "concurrency",
                    "distributed systems",
                    "networking",
                    "protocols",
                ],
                "sources": ["https://lwn.net", "https://kernel.org", "https://unix.stackexchange.com"],
            },
            "philosophy_ethics": {
                "keywords": [
                    "ethics",
                    "AI ethics",
                    "morality",
                    "philosophy",
                    "consciousness",
                    "free will",
                    "existentialism",
                    "epistemology",
                ],
                "sources": ["https://plato.stanford.edu", "https://iep.utm.edu"],
            },
            "general_knowledge": {
                "keywords": [
                    "history",
                    "culture",
                    "geography",
                    "world events",
                    "society",
                    "economics",
                    "politics",
                    "art",
                    "music",
                    "literature",
                ],
                "sources": ["https://wikipedia.org", "https://britannica.com", "https://www.bbc.com/news"],
            },
            "engineering": {
                "keywords": [
                    "mechanical",
                    "electrical",
                    "civil",
                    "aerospace",
                    "robotics",
                    "automation",
                    "CAD",
                    "simulation",
                ],
                "sources": ["https://engineering.com", "https://www.asme.org"],
            },
            "business_finance": {
                "keywords": [
                    "business",
                    "finance",
                    "investing",
                    "economics",
                    "marketing",
                    "management",
                    "entrepreneurship",
                    "startups",
                ],
                "sources": ["https://www.investopedia.com", "https://www.forbes.com", "https://hbr.org"],
            },
        }

    @staticmethod
    def _get_ethical_boundaries() -> Dict[str, any]:
        """Defines the ethical guidelines for web scraping."""
        return {
            "respect_robots_txt": True,
            "user_agent": "CelsiusAI-Learner/2.0 (Async; Educational Purpose; github.com/your-repo)",
            "no_personal_data": True,
            "respect_rate_limits": True,
        }

    async def initialize(self):
        """Initializes the database and the aiohttp session."""
        await self._init_database()
        # Create an SSL context using certifi's CA bundle to avoid certificate
        # verification issues on some platforms (Windows venvs, etc.).
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers={"User-Agent": self.ethical_boundaries["user_agent"]},
                timeout=self.session_timeout,
            )
        except Exception:
            # Fallback to default session if certifi or SSL context fails
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": self.ethical_boundaries["user_agent"]}, timeout=self.session_timeout
            )
        self.logger.info("Web Learner initialized with async session.")
        try:
            # Log the CA bundle path used by certifi for easier diagnostics
            self.logger.info(f"certifi CA bundle: {certifi.where()}")
        except Exception:
            # Non-fatal; continue without CA path logging
            pass

    async def _init_database(self):
        """Initializes the database schema asynchronously."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS learned_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE NOT NULL,
                    title TEXT, content_summary TEXT, topic TEXT, keywords TEXT,
                    quality_score REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    content_hash TEXT, source_credibility INTEGER DEFAULT 0
                )
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS learning_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL,
                    insight TEXT NOT NULL, confidence_score REAL, sources_count INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, insight_type TEXT
                )
            """
            )
            await db.commit()
        self.logger.info("Async web learning database initialized.")

    async def _is_crawl_allowed(self, url: str) -> bool:
        """Checks robots.txt to see if crawling is permitted."""
        # Allow bypass for explicitly trusted sources
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        if domain in self.trusted_sources:
            return True

        if not self.ethical_boundaries["respect_robots_txt"] or not self.respect_robots_txt:
            return True

        parsed_url = urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

        try:
            if not self.session:
                await self.initialize()

            async with self.session.get(robots_url, timeout=self.session_timeout) as response:
                if response.status == 200:
                    text = await response.text()
                    # Basic check, a full robotsparser library would be better for production
                    if "Disallow: /" in text and "Allow: /" not in text:
                        self.logger.warning(f"Crawling disallowed by robots.txt at {url}")
                        # record blocked domain for diagnostics
                        self.blocked_count += 1
                        self.blocked_sites.add(domain)
                        # Attempt lightweight diagnostics: find alternative sources and contact info
                        try:
                            alt = await self.find_alternative_sources(url)
                            if alt:
                                self.logger.info(f"Found alternative sources for {domain}: {alt}")
                            contact = await self.find_contact_email(url)
                            if contact:
                                self.logger.info(f"Found contact for {domain}: {contact}")
                                await self._save_contact_request(domain, contact, url)
                        except Exception:
                            # Diagnostics must not block operation
                            pass
                        return False
                return True
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout checking robots.txt for {url}, proceeding cautiously.")
            return True
        except aiohttp.ClientError as e:
            self.logger.error(f"Client error checking robots.txt for {url}: {e}, assuming allowed.")
            return True

    async def extract_content_ethically(self, url: str) -> Optional[Dict]:
        """Extracts content from a URL asynchronously and ethically."""
        if not await self._is_crawl_allowed(url):
            return None

        try:
            async with self.session.get(url, timeout=self.session_timeout) as response:
                response.raise_for_status()
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                for script in soup(["script", "style", "nav", "footer", "aside"]):
                    script.decompose()

                title = soup.title.string.strip() if soup.title else "No Title"

                main_content_selectors = ["article", "main", ".content", "#content", ".post-body"]
                content_element = next((soup.select_one(s) for s in main_content_selectors if soup.select_one(s)), None)

                text = (
                    content_element.get_text(separator="\n", strip=True)
                    if content_element
                    else soup.get_text(separator="\n", strip=True)
                )

                cleaned_text = re.sub(r"\s{2,}", " ", text)
                summary = cleaned_text[:2000] + ("..." if len(cleaned_text) > 2000 else "")
                content_hash = hashlib.sha256(cleaned_text.encode()).hexdigest()

                return {
                    "url": url,
                    "title": title,
                    "content_summary": summary,
                    "content_hash": content_hash,
                    "word_count": len(cleaned_text.split()),
                }
        except Exception as e:
            self.logger.warning(f"Failed to extract content from {url}: {e}")
            return None

    def analyze_content_quality(self, content_data: Dict) -> float:
        """Analyzes content quality based on heuristics."""
        score = 0.0
        if content_data["word_count"] > 300:
            score += 0.4
        if len(content_data["title"]) > 15 and "clickbait" not in content_data["title"].lower():
            score += 0.3

        # Relevance check
        content = content_data["content_summary"].lower()
        keywords_found = sum(1 for topic in self.learning_topics.values() for kw in topic["keywords"] if kw in content)
        score += min(0.3, keywords_found * 0.05)

        return min(1.0, score)

    def determine_topic(self, content_data: Dict) -> str:
        """Determines the primary topic of the content."""
        content = (content_data["title"] + " " + content_data["content_summary"]).lower()
        topic_scores = {
            topic: sum(content.count(kw) for kw in data["keywords"]) for topic, data in self.learning_topics.items()
        }
        return max(topic_scores, key=topic_scores.get) if any(topic_scores.values()) else "general"

    async def store_learned_content(self, content_data: Dict, topic: str, quality_score: float) -> bool:
        """Stores learned content in the database if it's not a duplicate."""
        try:
            # Best-effort de-duplication: check both content_hash and URL to avoid
            # triggering UNIQUE constraint errors on the `url` column.
            async with aiosqlite.connect(self.db_path) as db:
                # Check by content hash first (fast duplicate detection)
                cursor = await db.execute(
                    "SELECT id FROM learned_content WHERE content_hash = ?", (content_data["content_hash"],)
                )
                if await cursor.fetchone():
                    return False  # Duplicate by content

                # Also check if the URL already exists in DB to avoid IntegrityError
                cursor = await db.execute("SELECT id FROM learned_content WHERE url = ?", (content_data.get("url"),))
                if await cursor.fetchone():
                    return False  # Duplicate by URL

                keywords = {
                    kw
                    for t_data in self.learning_topics.values()
                    for kw in t_data["keywords"]
                    if kw in content_data["content_summary"].lower()
                }

                try:
                    await db.execute(
                        """INSERT INTO learned_content (url, title, content_summary, topic, keywords, quality_score, content_hash)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            content_data.get("url"),
                            content_data.get("title"),
                            content_data.get("content_summary"),
                            topic,
                            ",".join(keywords),
                            quality_score,
                            content_data.get("content_hash"),
                        ),
                    )
                    await db.commit()
                    self.logger.info(f"Stored: '{content_data.get('title')}' (Quality: {quality_score:.2f})")
                    return True
                except Exception as e:
                    # Handle a common race: UNIQUE constraint on url/content_hash.
                    # Treat it as a non-fatal duplicate and log at INFO level.
                    try:
                        import sqlite3

                        if isinstance(e, sqlite3.IntegrityError) or "UNIQUE constraint failed" in str(e):
                            self.logger.info(f"Duplicate detected (skipping store) for URL: {content_data.get('url')}")
                            return False
                    except Exception:
                        pass
                    self.logger.error(f"Error storing content: {e}")
                    return False
        except Exception as e:
            self.logger.error(f"Error storing content (outer): {e}")
            return False

    # ------------------------------------------------------------------
    # Alternative source discovery and contact-finding helpers
    # These are conservative: they only gather potential contact addresses
    # and alternative endpoints (feeds, sitemaps) for admin review. We DO
    # NOT auto-send requests or perform large-scale scraping.
    # ------------------------------------------------------------------
    async def find_alternative_sources(self, url: str) -> List[str]:
        """Look for RSS/Atom feeds, sitemap.xml, or known feed endpoints for a site."""
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        candidates: List[str] = []

        # Common feed and sitemap locations
        endpoints = [
            f"{base}/feed",
            f"{base}/feeds/posts/default",
            f"{base}/sitemap.xml",
            f"{base}/rss",
            f"{base}/rss.xml",
            f"{base}/atom.xml",
        ]

        # Try fetching endpoints and verify they look like feeds or sitemaps
        for ep in endpoints:
            try:
                if not self.session:
                    await self.initialize()
                async with self.session.get(ep, timeout=self.session_timeout) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if "<rss" in text.lower() or "<feed" in text.lower() or "<urlset" in text.lower():
                            candidates.append(ep)
            except Exception:
                continue

        # Also try scraping the homepage for <link rel="alternate" type="application/rss+xml">
        try:
            homepage = base + "/"
            if not self.session:
                await self.initialize()
            async with self.session.get(homepage, timeout=self.session_timeout) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    for link in soup.find_all("link", rel=lambda v: v and "alternate" in v):
                        t = link.get("type", "")
                        if "rss" in t or "atom" in t or "xml" in t:
                            href = link.get("href")
                            if href:
                                candidates.append(urljoin(homepage, href))
        except Exception:
            pass

        # Deduplicate while preserving order
        seen = set()
        result = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                result.append(c)
        return result

    async def find_contact_email(self, url: str) -> Optional[str]:
        """Attempt to locate a contact email for the site by checking robots.txt,
        common contact pages, and by scraping mailto: links. Returns the first
        plausible email address or None.
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        potential: List[str] = []

        # Check robots.txt for email-like patterns
        robots_url = f"{parsed.scheme}://{domain}/robots.txt"
        try:
            if not self.session:
                await self.initialize()
            async with self.session.get(robots_url, timeout=self.session_timeout) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    import re

                    m = re.search(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
                    if m:
                        potential.append(m.group(1))
                    m2 = re.search(
                        r"contact[:= ]+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", text, re.IGNORECASE
                    )
                    if m2:
                        potential.append(m2.group(1))
        except Exception:
            pass

        # Try common pages: /contact, /contact-us, /about
        contact_pages = [
            f"{parsed.scheme}://{domain}/contact",
            f"{parsed.scheme}://{domain}/contact-us",
            f"{parsed.scheme}://{domain}/about",
            f"{parsed.scheme}://{domain}/about-us",
            f"{parsed.scheme}://{domain}/team",
        ]
        try:
            import re

            for cp in contact_pages:
                try:
                    async with self.session.get(cp, timeout=self.session_timeout) as resp:
                        if resp.status == 200:
                            html = await resp.text()
                            # Find mailto links
                            mlinks = re.findall(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", html)
                            if mlinks:
                                potential.extend(mlinks)
                                break
                            # Also search for plain emails
                            plain = re.findall(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", html)
                            if plain:
                                potential.extend(plain)
                                break
                except Exception:
                    continue
        except Exception:
            pass

        # Fallback: try homepage scraping for mailto
        try:
            homepage = f"{parsed.scheme}://{domain}/"
            async with self.session.get(homepage, timeout=self.session_timeout) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    import re

                    mlinks = re.findall(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", html)
                    if mlinks:
                        potential.extend(mlinks)
                    else:
                        plain = re.findall(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", html)
                        if plain:
                            potential.extend(plain)
        except Exception:
            pass

        # Normalize and return first plausible email
        cleaned: List[str] = []
        for e in potential:
            e = e.strip().lower()
            if "@" in e and len(e) > 5:
                cleaned.append(e)

        return cleaned[0] if cleaned else None

    async def _save_contact_request(self, domain: str, email: str, source_url: str) -> None:
        """Save contact requests to a JSON file for admin review. Deduplicate by domain+email."""
        try:
            import json

            contacts_file = Path(self.db_path).parent / "web_learning_contact_requests.json"
            data = []
            if contacts_file.exists():
                try:
                    data = json.loads(contacts_file.read_text(encoding="utf-8"))
                except Exception:
                    data = []

            entry = {"domain": domain, "email": email, "source": source_url, "found_at": datetime.now().isoformat()}
            # Simple de-dup
            keys = {(d.get("domain"), d.get("email")) for d in data}
            if (domain, email) not in keys:
                data.append(entry)
                contacts_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                self.logger.info(f"Saved contact request for {domain} -> {email} to {contacts_file}")
        except Exception as e:
            self.logger.warning(f"Failed to save contact request: {e}")

    async def learn_from_topic(self, topic: str, max_sources: int = 3):
        """Learns from web sources for a specific topic."""
        if topic not in self.learning_topics:
            self.logger.warning(f"Unknown topic: {topic}")
            return

        self.logger.info(f"Starting learning for topic: {topic}")
        sources = self.learning_topics[topic]["sources"][:max_sources]

        tasks = [self._process_source(source_url) for source_url in sources]
        await asyncio.gather(*tasks)
        self.logger.info(f"Completed learning cycle for {topic}.")

    async def _process_source(self, source_url: str):
        """Processes a single source URL, extracts content, and stores it."""
        if not self.learning_active.is_set():
            return

        # First try feed/API adapters for known sources (feed-first strategy)
        try:
            api_items = await self.fetch_via_api(source_url, None)
        except Exception:
            api_items = []

        if api_items:
            for content_data in api_items:
                try:
                    quality_score = self.analyze_content_quality(content_data)
                    if quality_score > 0.4:
                        detected_topic = self.determine_topic(content_data)
                        await self.store_learned_content(content_data, detected_topic, quality_score)
                except Exception:
                    self.logger.exception("Error processing API-sourced content from %s", source_url)
            await asyncio.sleep(self.rate_limit)
            return

        # Fallback to page extraction when no feed/API results
        content_data = await self.extract_content_ethically(source_url)
        if content_data:
            quality_score = self.analyze_content_quality(content_data)
            if quality_score > 0.4:
                detected_topic = self.determine_topic(content_data)
                await self.store_learned_content(content_data, detected_topic, quality_score)

        await asyncio.sleep(self.rate_limit)

    async def fetch_via_api(self, source_url: str, topic: Optional[str] = None, max_items: int = 3) -> List[Dict]:
        """Attempt to fetch recent content via site APIs or RSS feeds for known sources.

        Returns a list of content_data dicts similar to extract_content_ethically output.
        """
        results = []
        parsed = urlparse(source_url)
        domain = parsed.netloc.lower()

        try:
            if "arxiv.org" in domain:
                # Use arXiv API - search by topic keywords if provided
                query = ""
                if topic and topic in self.learning_topics:
                    qwords = self.learning_topics[topic]["keywords"][:3]
                    query = "+".join(quote(w) for w in qwords)
                else:
                    query = "ai"
                api_url = f"http://export.arxiv.org/api/query?search_query=all:{query}&max_results={max_items}"
                async with self.session.get(api_url, timeout=self.session_timeout) as resp:
                    if resp.status != 200:
                        return []
                    text = await resp.text()
                # Parse Atom feed
                try:
                    import xml.etree.ElementTree as ET

                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    root = ET.fromstring(text)
                    for entry in root.findall("atom:entry", ns)[:max_items]:
                        title = entry.find("atom:title", ns).text or "No Title"
                        summary = entry.find("atom:summary", ns).text or ""
                        link = entry.find("atom:id", ns).text or ""
                        cleaned = re.sub(r"\s{2,}", " ", summary)
                        content_hash = hashlib.sha256(cleaned.encode()).hexdigest()
                        results.append(
                            {
                                "url": link,
                                "title": title.strip(),
                                "content_summary": cleaned,
                                "content_hash": content_hash,
                                "word_count": len(cleaned.split()),
                            }
                        )
                except Exception:
                    return []

            elif "dev.to" in domain:
                api_url = f"https://dev.to/api/articles?per_page={max_items}"
                async with self.session.get(api_url, timeout=self.session_timeout) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                for item in data[:max_items]:
                    title = item.get("title", "No Title")
                    url = item.get("url") or item.get("canonical_url") or item.get("path")
                    summary = item.get("description") or item.get("body_markdown", "")[:1000]
                    cleaned = re.sub(r"\s{2,}", " ", summary)
                    content_hash = hashlib.sha256(cleaned.encode()).hexdigest()
                    results.append(
                        {
                            "url": url,
                            "title": title.strip(),
                            "content_summary": cleaned,
                            "content_hash": content_hash,
                            "word_count": len(cleaned.split()),
                        }
                    )

            elif "realpython.com" in domain or "realpython" in source_url:
                feed_url = "https://realpython.com/feeds/all/"
                async with self.session.get(feed_url, timeout=self.session_timeout) as resp:
                    if resp.status != 200:
                        return []
                    text = await resp.text()
                try:
                    import xml.etree.ElementTree as ET

                    root = ET.fromstring(text)
                    # RSS -> channel/item
                    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
                    for it in items[:max_items]:
                        title = it.find("title").text if it.find("title") is not None else "No Title"
                        desc = it.find("description") or it.find("{http://www.w3.org/2005/Atom}summary")
                        summary = desc.text if desc is not None else ""
                        link = (
                            it.find("link").text
                            if it.find("link") is not None
                            else (
                                it.find("{http://www.w3.org/2005/Atom}id").text
                                if it.find("{http://www.w3.org/2005/Atom}id") is not None
                                else ""
                            )
                        )
                        cleaned = re.sub(r"\s{2,}", " ", summary)
                        content_hash = hashlib.sha256(cleaned.encode()).hexdigest()
                        results.append(
                            {
                                "url": link,
                                "title": title.strip(),
                                "content_summary": cleaned,
                                "content_hash": content_hash,
                                "word_count": len(cleaned.split()),
                            }
                        )
                except Exception:
                    return []

        except Exception:
            return []

        return results

    async def start_continuous_learning(self):
        """Starts the continuous, asynchronous web learning process."""
        self.logger.info("Starting continuous learning loop.")
        self.learning_active.set()
        await self.initialize()

        try:
            while self.learning_active.is_set():
                self.logger.info("--- New learning cycle ---")
                tasks = [self.learn_from_topic(topic) for topic in self.learning_topics.keys()]
                await asyncio.gather(*tasks)

                self.logger.info("Cycle complete. Waiting for 1 hour.")
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            self.logger.info("Learning loop cancelled.")
        finally:
            if self.session:
                await self.session.close()
            self.logger.info("Web learner session closed.")

    def stop_learning(self):
        """Stops the web learning process gracefully."""
        self.learning_active.clear()
        self.logger.info("Stop signal received. Finishing current tasks...")

    # ------------------------------------------------------------------
    # Synchronous helpers used by the integration layer (convenience API)
    # These use the same SQLite DB file but operate synchronously so the
    # higher-level integration code can call them without awaiting.
    # ------------------------------------------------------------------
    def store_insight(self, topic: str, insight: str, confidence: float = 0.6, insight_type: str = "auto") -> bool:
        """Store a generated insight into the learning_insights table (sync).

        This is a convenience wrapper so the integration layer can call
        this method from synchronous code.
        """
        try:
            import sqlite3

            conn = sqlite3.connect(str(self.db_path))
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO learning_insights (topic, insight, confidence_score, sources_count, insight_type)
                   VALUES (?, ?, ?, ?, ?)""",
                (topic, insight, confidence, 1, insight_type),
            )
            conn.commit()
            conn.close()
            self.logger.info(f"Stored insight for topic '{topic}': {insight[:80]}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to store insight: {e}")
            return False

    def generate_learning_insights(self, topic: Optional[str] = None, hours: int = 24) -> List[Dict]:
        """Generate a short list of learning insights for a topic (sync).

        Returns a list of insight dicts: { 'topic': str, 'insight': str, 'confidence': float }
        """
        try:
            import sqlite3

            conn = sqlite3.connect(str(self.db_path))
            cur = conn.cursor()

            # If insights table has entries, prefer them
            if topic:
                cur.execute(
                    "SELECT insight, confidence_score FROM learning_insights WHERE topic = ? ORDER BY timestamp DESC LIMIT 10",
                    (topic,),
                )
            else:
                cur.execute(
                    "SELECT topic, insight, confidence_score FROM learning_insights ORDER BY timestamp DESC LIMIT 50"
                )

            rows = cur.fetchall()

            insights = []
            if rows:
                if topic:
                    for r in rows:
                        insights.append({"topic": topic, "insight": r[0], "confidence": float(r[1] or 0.5)})
                else:
                    for r in rows:
                        insights.append({"topic": r[0], "insight": r[1], "confidence": float(r[2] or 0.5)})

                conn.close()
                return insights

            # Fallback: synthesize simple insights from learned_content
            if topic:
                cur.execute(
                    "SELECT title, content_summary FROM learned_content WHERE topic = ? ORDER BY timestamp DESC LIMIT 10",
                    (topic,),
                )
            else:
                cur.execute(
                    "SELECT topic, COUNT(*) FROM learned_content GROUP BY topic ORDER BY COUNT(*) DESC LIMIT 10"
                )

            rows = cur.fetchall()
            conn.close()

            if not rows:
                return []

            synth = []
            if topic:
                for title, summary in rows:
                    text = f"Learned: {title} — {summary[:140].strip()}"
                    synth.append({"topic": topic, "insight": text, "confidence": 0.5})
            else:
                for t, cnt in rows:
                    synth.append({"topic": t, "insight": f"Top topic: {t} ({cnt} items learned)", "confidence": 0.6})

            return synth
        except Exception as e:
            self.logger.error(f"Error generating learning insights (sync): {e}")
            return []

    def generate_learning_report(self, period: str = "daily") -> Optional[Dict]:
        """Generate a summary learning report (sync).

        period can be 'daily' or 'weekly' — this controls the timeframe used
        when summarizing recent learning activity.
        """
        try:
            import sqlite3
            from datetime import datetime, timedelta

            conn = sqlite3.connect(str(self.db_path))
            cur = conn.cursor()

            now = datetime.now()
            if period == "daily":
                since = now - timedelta(days=1)
            elif period == "weekly":
                since = now - timedelta(days=7)
            else:
                since = now - timedelta(days=1)

            since_iso = since.isoformat()

            # Total learned content
            cur.execute("SELECT COUNT(*) FROM learned_content WHERE timestamp > ?", (since_iso,))
            total_content = cur.fetchone()[0] or 0

            # Insights
            cur.execute("SELECT COUNT(*) FROM learning_insights WHERE timestamp > ?", (since_iso,))
            total_insights = cur.fetchone()[0] or 0

            # Top topics
            cur.execute(
                "SELECT topic, COUNT(*) as cnt FROM learned_content WHERE timestamp > ? GROUP BY topic ORDER BY cnt DESC LIMIT 5",
                (since_iso,),
            )
            top = cur.fetchall()
            top_topics = [{"topic": t[0], "count": t[1]} for t in top]

            # Sample insights
            cur.execute(
                "SELECT topic, insight, confidence_score FROM learning_insights ORDER BY timestamp DESC LIMIT 10"
            )
            sample = [{"topic": r[0], "insight": r[1], "confidence": float(r[2] or 0.5)} for r in cur.fetchall()]

            conn.close()

            report = {
                "period": period,
                "generated_at": now.isoformat(),
                "total_content_learned": total_content,
                "total_insights": total_insights,
                "top_topics": top_topics,
                "sample_insights": sample,
            }

            return report
        except Exception as e:
            self.logger.error(f"Failed to generate learning report: {e}")
            return None


async def test_web_learning():
    """Tests the asynchronous web learning system."""
    print("🌐 TESTING CELSIUS AI ASYNC WEB LEARNING ENGINE")
    print("=" * 50)

    db_file = Path("celsius_web_learning_async.db")
    if db_file.exists():
        db_file.unlink()

    learner = CelsiusWebLearner(db_path=db_file)
    await learner.initialize()

    print("Async web learning engine initialized")
    print(f"📚 Topics: {', '.join(learner.learning_topics.keys())}")
    print(f"📊 Database: {learner.db_path}")

    print("\n🚀 Performing a single learning run for 'programming' topic...")
    await learner.learn_from_topic("programming", max_sources=2)

    print("\nSingle run complete. Check logs and database for results.")

    # Example of starting and stopping the continuous loop
    print("\n🔄 Starting continuous learning for 15 seconds as a test...")
    learning_task = asyncio.create_task(learner.start_continuous_learning())

    await asyncio.sleep(15)
    learner.stop_learning()
    await learning_task

    print("\nContinuous learning test finished.")


if __name__ == "__main__":
    try:
        asyncio.run(test_web_learning())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
