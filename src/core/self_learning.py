"""
Celsius AI - Enhanced Self-Learning Core
========================================

Description:
------------
This module provides the core self-learning capabilities for the Celsius AI,
allowing it to learn from conversations, external documents, and other data
sources across a wide range of domains. It is designed to be extensible,
with a modular architecture for adding new learning domains.

Key Features:
-------------
- **Multi-Domain Learning**: Organizes knowledge into distinct `LearningModule`s,
  such as cybersecurity, programming, finance, and health.
- **Knowledge Extraction**: Uses rule-based patterns (regex) to extract salient
  pieces of information from unstructured text.
- **Persistent Knowledge Base**: Stores learned `KnowledgeEntry` objects in
  domain-specific JSON files for long-term memory.
- **Confidence Scoring**: Assigns a confidence level to each piece of knowledge,
  differentiating between verified sources and conversational learning.
- **Duplicate Prevention**: Uses hashing to prevent storing the exact same
  piece of knowledge multiple times.
- **Asynchronous File I/O**: Uses `aiofiles` for non-blocking file operations to
  avoid stalling the application's event loop.
- **Dynamic Module Management**: Learning modules can be enabled or disabled at
  runtime.
- **Insight and Suggestions**: Provides statistics on learning progress and can
  suggest new topics to explore based on knowledge gaps.

Usage:
------
The `SelfLearningAI` class is the main entry point for this module. It is
typically instantiated once and used by the main AI assistant to process
and learn from new information.

    from core.self_learning import SelfLearningAI

    async def main():
        learning_ai = SelfLearningAI()

        # Learn from a piece of text
        text_content = "A new vulnerability in the Log4j library allows for remote code execution."
        await learning_ai.learn_from_external_source(
            content=text_content,
            source="Internal Security Bulletin",
            domain="cybersecurity"
        )

        # Retrieve learned knowledge
        knowledge = await learning_ai.get_knowledge(domain="cybersecurity", query="vulnerability")
        for entry in knowledge:
            print(f"Learned: {entry.content} (Confidence: {entry.confidence})")

"""

import asyncio
import json
import logging
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Type
from dataclasses import dataclass, field, asdict

# Asynchronous file operations are preferred.
# If aiofiles is not installed, a synchronous fallback is used for compatibility.
try:
    import aiofiles
except ImportError:
    aiofiles = None
    print("Warning: 'aiofiles' not found. Using synchronous file operations for self-learning module.")

logger = logging.getLogger(__name__)

# Define the root of the project to resolve paths correctly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "data" / "knowledge_base"


@dataclass
class LearningModule:
    """
    Represents a specific learning domain for the AI, defining its scope,
    keywords, and learned patterns.
    """

    name: str
    domain: str
    description: str
    keywords: Set[str] = field(default_factory=set)
    learned_patterns: List[Dict[str, Any]] = field(default_factory=list)
    confidence_threshold: float = 0.7
    last_updated: Optional[str] = None
    enabled: bool = True


@dataclass
class KnowledgeEntry:
    """
    Represents a single, atomic piece of learned knowledge, complete with
    metadata about its source, confidence, and verification status.
    """

    content: str
    domain: str
    source: str
    confidence: float
    timestamp: str
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    verified: bool = False


class SelfLearningAI:
    """
    An AI agent capable of self-learning across multiple domains by processing
    conversations and external data sources.
    """

    def __init__(self, knowledge_base_path: Path = KNOWLEDGE_BASE_DIR):
        """
        Initializes the SelfLearningAI.

        Args:
            knowledge_base_path (Path): The directory to store the knowledge base files.
        """
        self.knowledge_base_path: Path = knowledge_base_path
        self.knowledge_base_path.mkdir(parents=True, exist_ok=True)

        self.learning_modules: Dict[str, LearningModule] = self._initialize_learning_modules()
        self.knowledge_entries: List[KnowledgeEntry] = []

        self.learning_stats: Dict[str, Any] = {
            "total_entries": 0,
            "domains_covered": 0,
            "last_learning_session": None,
            "confidence_average": 0.0,
        }

        logger.info("Self-Learning AI initialized with multi-domain capabilities.")

    def _initialize_learning_modules(self) -> Dict[str, LearningModule]:
        """
        Initializes all predefined learning modules for the AI.

        Returns:
            Dict[str, LearningModule]: A dictionary of learning modules keyed by domain.
        """
        return {
            "cybersecurity": LearningModule(
                name="Cybersecurity Intelligence",
                domain="cybersecurity",
                description="Learns about threats, vulnerabilities, and defense strategies.",
                keywords={"malware", "phishing", "vulnerability", "firewall", "encryption", "zero-day"},
            ),
            "programming": LearningModule(
                name="Programming & Development",
                domain="programming",
                description="Learns programming languages, frameworks, and best practices.",
                keywords={"python", "javascript", "api", "database", "algorithm", "debugging", "git"},
            ),
            "finance": LearningModule(
                name="Financial Intelligence",
                domain="finance",
                description="Learns about personal finance, investments, and markets.",
                keywords={"investment", "stocks", "bonds", "cryptocurrency", "budget", "inflation"},
            ),
            "legal": LearningModule(
                name="Legal Frameworks",
                domain="legal",
                description="Learns about laws, regulations, and compliance.",
                keywords={"privacy", "gdpr", "compliance", "contract", "liability", "data protection"},
            ),
            "health": LearningModule(
                name="Health & Wellness",
                domain="health",
                description="Learns about health, medical knowledge, and wellness.",
                keywords={"nutrition", "exercise", "mental health", "medicine", "diagnosis", "wellness"},
            ),
            "fitness": LearningModule(
                name="Fitness & Training",
                domain="fitness",
                description="Learns about exercise, training methods, and performance.",
                keywords={"workout", "strength training", "cardio", "endurance", "recovery", "technique"},
            ),
            "business": LearningModule(
                name="Business Intelligence",
                domain="business",
                description="Learns about business strategy, management, and entrepreneurship.",
                keywords={"strategy", "management", "marketing", "startup", "operations", "leadership"},
            ),
            "technology": LearningModule(
                name="Technology Trends",
                domain="technology",
                description="Learns about emerging technologies and digital transformation.",
                keywords={"ai", "machine learning", "blockchain", "iot", "automation", "cloud computing"},
            ),
        }

    async def learn_from_conversation(self, conversation: Dict[str, Any]):
        """
        Analyzes a user conversation and extracts knowledge if applicable.

        Args:
            conversation (Dict[str, Any]): A dictionary containing 'user_message',
                                           'ai_response', and 'timestamp'.
        """
        try:
            user_query = conversation.get("user_message", "")
            ai_response = conversation.get("ai_response", "")
            timestamp = conversation.get("timestamp", datetime.now().isoformat())

            domain = self._classify_domain(user_query + " " + ai_response)
            if not domain:
                return

            knowledge = await self._extract_knowledge(user_query, ai_response, domain)
            if not knowledge:
                return

            entry = KnowledgeEntry(
                content=knowledge,
                domain=domain,
                source="conversation",
                confidence=0.6,  # Lower confidence for conversational learning
                timestamp=timestamp,
                tags=self._extract_tags(user_query + " " + ai_response),
                verified=False,
            )

            await self._store_knowledge_entry(entry)
            logger.info(f"Learned new knowledge in {domain}: {knowledge[:100]}...")

        except Exception as e:
            logger.error(f"Error in learning from conversation: {e}", exc_info=True)

    async def learn_from_external_source(self, content: str, source: str, domain: Optional[str] = None):
        """
        Learns from external content like documents, websites, or API responses.

        Args:
            content (str): The text content to learn from.
            source (str): A descriptor for the source of the content (e.g., URL, filename).
            domain (Optional[str]): The domain of the content. If None, it will be classified.
        """
        try:
            if not domain:
                domain = self._classify_domain(content)

            if domain and domain in self.learning_modules:
                knowledge_pieces = await self._extract_knowledge_pieces(content, domain)

                for piece in knowledge_pieces:
                    entry = KnowledgeEntry(
                        content=piece["content"],
                        domain=domain,
                        source=source,
                        confidence=piece.get("confidence", 0.8),  # Higher confidence for external sources
                        timestamp=datetime.now().isoformat(),
                        tags=piece.get("tags", []),
                        references=[source],
                        verified=False,
                    )
                    await self._store_knowledge_entry(entry)

                logger.info(f"Learned {len(knowledge_pieces)} new pieces from {source} in domain {domain}.")
        except Exception as e:
            logger.error(f"Error learning from external source '{source}': {e}", exc_info=True)

    def _classify_domain(self, text: str) -> Optional[str]:
        """
        Classifies a piece of text into a learning domain based on keyword scoring.

        Args:
            text (str): The text to classify.

        Returns:
            Optional[str]: The name of the domain with the highest score, or None.
        """
        text_lower = text.lower()
        domain_scores = {
            name: sum(len(kw.split()) for kw in module.keywords if kw.lower() in text_lower)
            for name, module in self.learning_modules.items()
            if module.enabled
        }

        # Filter out zero scores
        domain_scores = {k: v for k, v in domain_scores.items() if v > 0}

        return max(domain_scores, key=domain_scores.get) if domain_scores else None

    async def _extract_knowledge(self, query: str, response: str, domain: str) -> Optional[str]:
        """
        Extracts a single, actionable piece of knowledge from a query-response pair.

        Args:
            query (str): The user's query.
            response (str): The AI's response.
            domain (str): The classified domain of the text.

        Returns:
            Optional[str]: The extracted knowledge statement, or None.
        """
        combined_text = f"{query}. {response}"

        # Simple regex patterns to find factual statements.
        # More sophisticated NLP techniques could be used here.
        patterns_by_domain: Dict[str, List[str]] = {
            "cybersecurity": [r"vulnerability in ([\w\s]+) allows for (.+?)\."],
            "programming": [r"(\w+) function is used to (.+?)\."],
            "finance": [r"investment strategy of (.+?) involves (.+?)\."],
            "legal": [r"(\w+) law requires (.+?)\."],
            "health": [r"(\w+) is a symptom of (.+?)\."],
            "fitness": [r"exercise ([\w\s]+) targets the ([\w\s]+) muscles\."],
            "business": [r"business model known as ([\w\s]+) works by (.+?)\."],
            "technology": [r"(\w+) is a technology that enables (.+?)\."],
        }

        patterns = patterns_by_domain.get(domain, [r"([\w\s]+) is ([\w\s]+?)\."])

        for pattern in patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    async def _extract_knowledge_pieces(self, content: str, domain: str) -> List[Dict[str, Any]]:
        """
        Extracts multiple knowledge pieces from a larger block of content.

        Args:
            content (str): The content to parse.
            domain (str): The domain of the content.

        Returns:
            List[Dict[str, Any]]: A list of extracted knowledge pieces.
        """
        knowledge_pieces = []
        sentences = re.split(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s", content)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 25:  # Filter for meaningful sentences
                knowledge = await self._extract_knowledge("", sentence, domain)
                if knowledge:
                    knowledge_pieces.append(
                        {"content": knowledge, "confidence": 0.75, "tags": self._extract_tags(sentence)}
                    )
        return knowledge_pieces

    def _extract_tags(self, text: str) -> List[str]:
        """
        Extracts relevant tags from text based on module keywords.

        Args:
            text (str): The text to extract tags from.

        Returns:
            List[str]: A list of unique tags.
        """
        text_lower = text.lower()
        tags = {
            keyword
            for module in self.learning_modules.values()
            for keyword in module.keywords
            if keyword.lower() in text_lower
        }
        return list(tags)

    async def _store_knowledge_entry(self, entry: KnowledgeEntry):
        """
        Stores a knowledge entry in the appropriate domain file.

        Args:
            entry (KnowledgeEntry): The knowledge entry to store.
        """
        domain_file = self.knowledge_base_path / f"{entry.domain}_knowledge.json"
        content_hash = hashlib.md5(entry.content.encode()).hexdigest()

        try:
            entries = []
            if domain_file.exists():
                if aiofiles:
                    async with aiofiles.open(domain_file, "r", encoding="utf-8") as f:
                        content = await f.read()
                        if content:
                            entries = json.loads(content)
                else:
                    with open(domain_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content:
                            entries = json.loads(content)

            if content_hash not in {e.get("hash") for e in entries}:
                entry_dict = asdict(entry)
                entry_dict["hash"] = content_hash
                entries.append(entry_dict)

                if aiofiles:
                    async with aiofiles.open(domain_file, "w", encoding="utf-8") as f:
                        await f.write(json.dumps(entries, indent=4))
                else:
                    with open(domain_file, "w", encoding="utf-8") as f:
                        f.write(json.dumps(entries, indent=4))

                self.knowledge_entries.append(entry)
                self._update_learning_stats()
                logger.info(f"Stored new knowledge entry in {entry.domain}.")

        except Exception as e:
            logger.error(f"Error storing knowledge entry to {domain_file}: {e}", exc_info=True)

    def _update_learning_stats(self):
        """Updates internal statistics about the learning process."""
        total_entries = len(self.knowledge_entries)
        self.learning_stats.update(
            {
                "total_entries": total_entries,
                "domains_covered": len({entry.domain for entry in self.knowledge_entries}),
                "last_learning_session": datetime.now().isoformat(),
                "confidence_average": (
                    sum(entry.confidence for entry in self.knowledge_entries) / total_entries
                    if total_entries > 0
                    else 0.0
                ),
            }
        )

    async def get_knowledge(self, domain: Optional[str] = None, query: Optional[str] = None) -> List[KnowledgeEntry]:
        """
        Retrieves knowledge from the knowledge base, with optional filters.

        Args:
            domain (Optional[str]): Filter by a specific domain.
            query (Optional[str]): Filter by a search query in content or tags.

        Returns:
            List[KnowledgeEntry]: A list of matching knowledge entries, sorted by confidence.
        """
        try:
            if not self.knowledge_entries:
                await self._load_knowledge_base()

            results = self.knowledge_entries
            if domain:
                results = [entry for entry in results if entry.domain == domain]
            if query:
                q_lower = query.lower()
                results = [
                    entry
                    for entry in results
                    if q_lower in entry.content.lower() or any(q_lower in tag.lower() for tag in entry.tags)
                ]

            results.sort(key=lambda x: (x.confidence, x.timestamp), reverse=True)
            return results[:50]  # Return top 50 matches

        except Exception as e:
            logger.error(f"Error retrieving knowledge: {e}", exc_info=True)
            return []

    async def _load_knowledge_base(self):
        """Loads all knowledge entries from their respective files into memory."""
        logger.info("Loading knowledge base from files...")
        self.knowledge_entries = []
        for domain_file in self.knowledge_base_path.glob("*_knowledge.json"):
            try:
                if aiofiles:
                    async with aiofiles.open(domain_file, "r", encoding="utf-8") as f:
                        content = await f.read()
                else:
                    with open(domain_file, "r", encoding="utf-8") as f:
                        content = f.read()

                if content:
                    entries_data = json.loads(content)
                    for data in entries_data:
                        # Pop hash as it's not part of the dataclass
                        data.pop("hash", None)
                        self.knowledge_entries.append(KnowledgeEntry(**data))
            except Exception as e:
                logger.error(f"Error loading domain file {domain_file}: {e}", exc_info=True)

        self._update_learning_stats()
        logger.info(f"Loaded {len(self.knowledge_entries)} knowledge entries across all domains.")

    def get_learning_stats(self) -> Dict[str, Any]:
        """Returns a dictionary of current learning statistics."""
        return {
            **self.learning_stats,
            "active_modules": [
                {
                    "name": module.name,
                    "domain": module.domain,
                    "enabled": module.enabled,
                    "keywords_count": len(module.keywords),
                }
                for module in self.learning_modules.values()
                if module.enabled
            ],
        }

    async def toggle_learning_module(self, domain: str, enabled: bool):
        """
        Enables or disables a specific learning module.

        Args:
            domain (str): The domain of the module to toggle.
            enabled (bool): The new enabled state.
        """
        if domain in self.learning_modules:
            self.learning_modules[domain].enabled = enabled
            status = "enabled" if enabled else "disabled"
            logger.info(f"Learning module '{domain}' has been {status}.")
        else:
            logger.warning(f"Attempted to toggle non-existent learning module: {domain}")

    async def suggest_learning_topics(self, domain: Optional[str] = None) -> List[str]:
        """
        Suggests topics for further learning based on knowledge gaps.

        Args:
            domain (Optional[str]): If provided, suggests topics within that domain.

        Returns:
            List[str]: A list of suggested learning topics.
        """
        if not self.knowledge_entries:
            await self._load_knowledge_base()

        if domain:
            # Suggest based on under-represented keywords in a specific domain
            if domain in self.learning_modules:
                all_keywords = self.learning_modules[domain].keywords
                known_tags = {
                    tag.lower() for entry in self.knowledge_entries if entry.domain == domain for tag in entry.tags
                }
                missing_keywords = [kw for kw in all_keywords if kw.lower() not in known_tags]
                return [f"Expand on: {kw}" for kw in missing_keywords[:5]]
            return []
        else:
            # Suggest based on least-covered domains
            domain_counts = {name: 0 for name in self.learning_modules}
            for entry in self.knowledge_entries:
                if entry.domain in domain_counts:
                    domain_counts[entry.domain] += 1

            # Sort domains by the number of entries
            sorted_domains = sorted(domain_counts.items(), key=lambda item: item[1])
            return [f"Expand knowledge in the '{d[0]}' domain" for d in sorted_domains[:3]]
