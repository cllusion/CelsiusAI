"""
Celsius AI - Threat Intelligence Processing Module
==================================================

Description:
------------
This module is responsible for collecting, processing, caching, and querying
threat intelligence from various sources. It serves as the central hub for
all threat-related data within the Celsius AI ecosystem, providing other
modules with actionable intelligence on indicators of compromise (IOCs) such
as malicious IPs, domains, file hashes, and CVEs.

Key Features:
-------------
- **Multi-Source Aggregation**: Designed to pull data from multiple sources,
  including VirusTotal, MISP (Malware Information Sharing Platform), and local
  JSON-based threat feeds.
- **Intelligent Querying**: Classifies queries to identify the type of indicator
  (e.g., IP address, file hash, domain) and directs the query appropriately.
- **Caching System**: Maintains a local cache of intelligence data to reduce
  API usage, improve response times, and ensure availability. The cache has a
  configurable Time-To-Live (TTL) and a maximum size.
- **Asynchronous Operations**: Uses `aiohttp` for non-blocking external API calls
  and `asyncio` for managing background tasks like cache cleanup and feed updates.
- **Rate Limiting Awareness**: Includes placeholder logic for respecting API rate
  limits of external services like VirusTotal.
- **Extensible**: New intelligence sources can be added by extending the
  `_query_external_sources` method and adding a configuration entry.

Usage:
------
The `IntelligenceProcessor` is typically initialized once by the main assistant.
Other modules can then use it to query for threat intelligence.

    from core.config import load_config
    from intelligence.processor import IntelligenceProcessor

    async def main():
        config = load_config()
        intel_processor = IntelligenceProcessor(config)
        await intel_processor.initialize()

        # Query for a known malicious hash
        query_hash = "e4d909c290d0fb1ca068ffaddf22cbd0"
        results = await intel_processor.query_intelligence(query_hash)

        if results.get('results'):
            print(f"Found intelligence for {query_hash}:")
            for result in results['results']:
                print(f"- Source: {result['source']}, Severity: {result['severity']}")
        else:
            print(f"No intelligence found for {query_hash}.")

        await intel_processor.shutdown()

"""

import asyncio
import json
import logging
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import aiohttp

# Assuming a config object with attributes for API keys and settings
from src.core.config import CelsiusConfig

logger = logging.getLogger(__name__)

# Define the root of the project to resolve paths correctly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
THREAT_FEEDS_DIR = DATA_DIR / "threat_feeds"
CACHE_FILE = DATA_DIR / "intelligence_cache.json"


class IntelligenceProcessor:
    """
    Processes and manages threat intelligence data from multiple sources.
    """

    def __init__(self, config: CelsiusConfig):
        """
        Initializes the IntelligenceProcessor.

        Args:
            config (CelsiusConfig): The application's configuration object.
        """
        self.config: CelsiusConfig = config
        self.intelligence_cache: Dict[str, Dict[str, Any]] = {}
        self.update_tasks: List[asyncio.Task] = []

        self.sources: Dict[str, Dict[str, Any]] = {
            "virustotal": {
                "enabled": bool(config.virustotal_api_key),
                "api_key": config.virustotal_api_key,
                "url": "https://www.virustotal.com/api/v3/",
                "rate_limit_delay": 15,  # Seconds (for 4 req/min free tier)
            },
            "misp": {
                "enabled": bool(config.misp_url and config.misp_key),
                "url": config.misp_url,
                "api_key": config.misp_key,
            },
            "local_feeds": {
                "enabled": True,
                "path": THREAT_FEEDS_DIR,
            },
        }

        self.cache_ttl: timedelta = timedelta(hours=1)
        self.max_cache_size: int = 10000
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """
        Initializes the processor: creates directories, loads cache, starts
        background tasks, and creates a sample feed if needed.
        """
        try:
            logger.info("Initializing IntelligenceProcessor...")
            THREAT_FEEDS_DIR.mkdir(parents=True, exist_ok=True)
            self.session = aiohttp.ClientSession()

            await self._load_intelligence_cache()
            await self._create_sample_feed_if_needed()
            self._start_background_tasks()

            logger.info("IntelligenceProcessor initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize IntelligenceProcessor: {e}", exc_info=True)
            if self.session:
                await self.session.close()
            raise

    async def query_intelligence(self, query: str) -> Dict[str, Any]:
        """
        Queries all available intelligence sources for a given indicator.

        Args:
            query (str): The indicator to query (e.g., IP, hash, domain).

        Returns:
            Dict[str, Any]: A dictionary containing the query results.
        """
        logger.info(f"Querying threat intelligence for: {query}")
        query_type = self._classify_query(query)

        # Search cache first
        cached_results = self._search_cache(query, query_type)
        if cached_results:
            logger.info(f"Found {len(cached_results)} results in cache for '{query}'.")
            return {"query": query, "query_type": query_type, "results": cached_results, "source": "cache"}

        # If not in cache, query external sources
        logger.info(f"No valid cache entry for '{query}'. Querying external sources.")
        external_results = await self._query_external_sources(query, query_type)

        # Cache the new results
        for result in external_results:
            self._cache_intelligence_item(result)

        return {"query": query, "query_type": query_type, "results": external_results, "source": "external"}

    def _classify_query(self, query: str) -> str:
        """
        Classifies the query string into a specific indicator type.

        Returns:
            str: The classified query type (e.g., 'ip_address', 'sha256_hash').
        """
        if re.fullmatch(r"[a-fA-F0-9]{64}", query):
            return "sha256_hash"
        if re.fullmatch(r"[a-fA-F0-9]{40}", query):
            return "sha1_hash"
        if re.fullmatch(r"[a-fA-F0-9]{32}", query):
            return "md5_hash"
        if re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", query):
            return "ip_address"
        if re.fullmatch(r"CVE-\d{4}-\d{4,7}", query, re.IGNORECASE):
            return "cve"
        if "." in query and not " " in query:
            return "domain"
        return "keyword"

    def _search_cache(self, query: str, query_type: str) -> List[Dict[str, Any]]:
        """
        Searches the local intelligence cache for a matching query.

        Returns:
            List[Dict[str, Any]]: A list of matching results from the cache.
        """
        now = datetime.now()
        results = []

        # Use a pre-computed key for direct lookup if possible
        cache_key = f"{query_type}:{query}"
        cached_item = self.intelligence_cache.get(cache_key)

        if cached_item and (now - datetime.fromisoformat(cached_item["cached_at"])) < self.cache_ttl:
            results.append(cached_item["data"])

        return results

    async def _query_external_sources(self, query: str, query_type: str) -> List[Dict[str, Any]]:
        """
        Concurrently queries all enabled external intelligence sources.

        Returns:
            List[Dict[str, Any]]: An aggregated list of results from all sources.
        """
        tasks = []
        if self.sources["virustotal"]["enabled"]:
            tasks.append(self._query_virustotal(query, query_type))
        if self.sources["misp"]["enabled"]:
            tasks.append(self._query_misp(query, query_type))
        if self.sources["local_feeds"]["enabled"]:
            tasks.append(self._query_local_feeds(query, query_type))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten list and filter out errors/empty results
        flat_results = []
        for res in results:
            if isinstance(res, list):
                flat_results.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Error querying external source: {res}", exc_info=res)

        return flat_results

    async def _query_virustotal(self, query: str, query_type: str) -> List[Dict[str, Any]]:
        """
        Queries the VirusTotal API (simulated). In a real implementation, this
        would make an HTTP request to the VT API.
        """
        if not self.session:
            return []
        logger.debug(f"Querying VirusTotal for {query_type}: {query} (simulated).")
        await asyncio.sleep(self.sources["virustotal"]["rate_limit_delay"])

        # This is a mock response. A real implementation would parse the actual API response.
        return [
            {
                "source": "virustotal",
                "indicator": query,
                "severity": "medium",
                "details": {"detection_ratio": "5/70", "scan_date": datetime.now().isoformat()},
            }
        ]

    async def _query_misp(self, query: str, query_type: str) -> List[Dict[str, Any]]:
        """
        Queries a MISP instance (simulated).
        """
        if not self.session:
            return []
        logger.debug(f"Querying MISP for {query_type}: {query} (simulated).")

        # Mock response
        return [
            {
                "source": "misp",
                "indicator": query,
                "severity": "high",
                "details": {"event_id": 1234, "tags": ["malware", "c2"]},
            }
        ]

    async def _query_local_feeds(self, query: str, query_type: str) -> List[Dict[str, Any]]:
        """Queries local threat intelligence feed files."""
        results = []
        feeds_path = self.sources["local_feeds"]["path"]
        if not feeds_path.is_dir():
            return []

        for feed_file in feeds_path.glob("*.json"):
            try:
                with open(feed_file, "r", encoding="utf-8") as f:
                    feed_data = json.load(f)
                for indicator in feed_data.get("indicators", []):
                    if indicator.get("value") == query and indicator.get("type") == query_type:
                        results.append(
                            {
                                "source": f"local_feed:{feed_file.stem}",
                                "indicator": query,
                                "severity": indicator.get("severity", "unknown"),
                                "details": indicator,
                            }
                        )
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error reading local feed {feed_file}: {e}")
        return results

    def _cache_intelligence_item(self, item: Dict[str, Any]):
        """
        Adds or updates an item in the intelligence cache.
        """
        query = item.get("indicator")
        query_type = self._classify_query(query)
        cache_key = f"{query_type}:{query}"

        self.intelligence_cache[cache_key] = {"cached_at": datetime.now().isoformat(), "data": item}
        self._enforce_cache_size()

    def _enforce_cache_size(self):
        """If the cache exceeds its max size, it removes the oldest items."""
        if len(self.intelligence_cache) > self.max_cache_size:
            num_to_remove = len(self.intelligence_cache) - self.max_cache_size
            sorted_keys = sorted(self.intelligence_cache, key=lambda k: self.intelligence_cache[k]["cached_at"])
            for i in range(num_to_remove):
                del self.intelligence_cache[sorted_keys[i]]
            logger.info(f"Cache size enforced. Removed {num_to_remove} oldest items.")

    async def _create_sample_feed_if_needed(self):
        """Creates a sample local threat feed for demonstration purposes."""
        sample_feed_file = THREAT_FEEDS_DIR / "sample_threats.json"
        if not sample_feed_file.exists():
            logger.info("Creating sample local threat feed...")
            sample_data = {
                "feed_name": "Sample Threat Feed",
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "indicators": [
                    {
                        "value": "e4d909c290d0fb1ca068ffaddf22cbd0",
                        "type": "md5_hash",
                        "description": "Known malware hash",
                        "severity": "critical",
                    },
                    {
                        "value": "malicious-domain.example.com",
                        "type": "domain",
                        "description": "Phishing domain",
                        "severity": "high",
                    },
                ],
            }
            with open(sample_feed_file, "w", encoding="utf-8") as f:
                json.dump(sample_data, f, indent=4)

    def _start_background_tasks(self):
        """Starts background tasks for cache cleanup and feed updates."""
        self.update_tasks.append(asyncio.create_task(self._cache_cleanup_loop()))
        self.update_tasks.append(asyncio.create_task(self._feed_update_loop()))

    async def _cache_cleanup_loop(self):
        """Periodically cleans expired items from the cache."""
        while True:
            await asyncio.sleep(self.cache_ttl.total_seconds() / 2)
            now = datetime.now()
            expired_keys = [
                key
                for key, item in self.intelligence_cache.items()
                if (now - datetime.fromisoformat(item["cached_at"])) > self.cache_ttl
            ]
            if expired_keys:
                for key in expired_keys:
                    del self.intelligence_cache[key]
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries.")

    async def _feed_update_loop(self):
        """Periodically triggers updates for threat intelligence feeds (simulated)."""
        while True:
            await asyncio.sleep(86400)  # Run once a day
            logger.info("Simulating daily update of threat intelligence feeds...")
            # In a real implementation, this would re-download/update feeds.

    async def _load_intelligence_cache(self):
        """Loads the intelligence cache from a file on disk."""
        if not CACHE_FILE.exists():
            return
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                self.intelligence_cache = json.load(f)
            logger.info(f"Loaded {len(self.intelligence_cache)} items from intelligence cache.")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load intelligence cache: {e}")

    async def _save_intelligence_cache(self):
        """Saves the current intelligence cache to a file on disk."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.intelligence_cache, f, indent=4)
        except IOError as e:
            logger.error(f"Failed to save intelligence cache: {e}")

    async def shutdown(self):
        """Gracefully shuts down the IntelligenceProcessor."""
        logger.info("Shutting down IntelligenceProcessor...")
        for task in self.update_tasks:
            task.cancel()
        if self.update_tasks:
            await asyncio.gather(*self.update_tasks, return_exceptions=True)

        if self.session and not self.session.closed:
            await self.session.close()

        await self._save_intelligence_cache()
        logger.info("IntelligenceProcessor shutdown complete.")
