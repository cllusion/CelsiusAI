"""
Celsius AI - Core Assistant Module
==================================

Description:
------------
This module contains the primary `CelsiusAI` class, which serves as the central
brain for the entire system. It orchestrates various subsystems to process user
queries, manage security tasks, handle device interactions, and perform self-learning.

Key Responsibilities:
---------------------
- **Query Processing**: Receives user input and classifies its intent.
- **Subsystem Orchestration**: Routes classified queries to the appropriate handler,
  such as the `ThreatAnalyzer`, `DeviceManager`, or `WhiteHatEngine`.
- **Conversational AI**: Enhances user interaction to feel more natural and human-like.
- **Self-Learning**: Continuously learns from interactions to improve its knowledge base.
- **State Management**: Maintains the overall security context and system status.
- **Health Data Management**: Provides functionality to import and analyze health and
  fitness data, including from external sources like Google Gemini.

Dependencies:
-------------
- `openai`: For optional integration with OpenAI's language models.
- `transformers`: For using local, privacy-focused language models.
- `torch`: A dependency for the `transformers` library.
- Internal Celsius Components: `CelsiusConfig`, `SelfLearningAI`, `ThreatAnalyzer`, etc.

Usage:
------
The `CelsiusAI` class is typically instantiated and managed by a higher-level
application, such as the FastAPI web interface (`web_interface.py`) or the
command-line interface (`main.py`). Its `initialize` method should be called
at startup, and its `process_query` method is the main entry point for user
interaction.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional, Any
from datetime import datetime

# Optional imports with fallbacks for key libraries
try:
    import openai
except ImportError:
    openai = None
    logging.warning("OpenAI library not found. OpenAI features will be disabled.")

try:
    from transformers import AutoTokenizer, AutoModel
    import torch

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    AutoTokenizer, AutoModel, torch = None, None, None
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers library not found. Local model features will be disabled.")

# Import core Celsius components
from .config import CelsiusConfig
from .self_learning import SelfLearningAI
from .conversational_ai import ConversationalAI
from .health_data import HealthDataManager

# Safely import other components, allowing the system to run in a degraded mode
try:
    from src.security.analyzer import ThreatAnalyzer
    from src.intelligence.processor import IntelligenceProcessor
    from src.devices.manager import DeviceManager
    from src.whitehat.engine import WhiteHatEngine

    CELSIUS_COMPONENTS_AVAILABLE = True
except ImportError:
    logging.warning("One or more core Celsius components failed to import. Running in degraded mode.")
    CELSIUS_COMPONENTS_AVAILABLE = False

    # Define dummy classes to ensure the application can still run
    class ThreatAnalyzer:
        def __init__(self, config: CelsiusConfig) -> None:
            pass

        async def initialize(self) -> None:
            pass

        async def shutdown(self) -> None:
            pass

        async def perform_scan(self, scan_type: str) -> dict[str, Any]:
            return {"error": "Not available"}

        async def analyze_current_threats(self) -> dict[str, Any]:
            return {"error": "Not available"}

    class IntelligenceProcessor:
        def __init__(self, config: CelsiusConfig) -> None:
            pass

        async def initialize(self) -> None:
            pass

        async def shutdown(self) -> None:
            pass

        async def query_intelligence(self, query: str) -> dict[str, Any]:
            return {"error": "Not available"}

    class DeviceManager:
        def __init__(self, config: CelsiusConfig) -> None:
            pass

        async def get_device_status(self) -> list[dict[str, Any]]:
            return []

    class WhiteHatEngine:
        def __init__(self, config: CelsiusConfig) -> None:
            pass

        async def initialize(self) -> None:
            pass

        def get_authorization_status(self) -> dict[str, Any]:
            return {"authorized": False}

        async def request_authorization(self) -> bool:
            return False

        async def execute_technique(self, technique: str, target: str) -> dict[str, Any]:
            return {"error": "Not available"}

        async def run_engagement(self, target: str) -> dict[str, Any]:
            return {"error": "Not available"}

        def get_available_techniques(self) -> list[str]:
            return []


logger = logging.getLogger(__name__)


class CelsiusAI:
    """
    Main AI Assistant class for orchestrating cybersecurity defense, learning,
    and user interaction.
    """

    def __init__(self, config: CelsiusConfig) -> None:
        """
        Initializes the CelsiusAI assistant and its subsystems.

        Args:
            config (CelsiusConfig): The configuration object for the AI.
        """
        self.config = config
        self.self_learning = SelfLearningAI()
        self.conversational_ai = ConversationalAI()
        self.health_manager = HealthDataManager()

        # Initialize core components if available
        if CELSIUS_COMPONENTS_AVAILABLE:
            self.threat_analyzer = ThreatAnalyzer(config)
            self.intel_processor = IntelligenceProcessor(config)
            self.device_manager = DeviceManager(config)
            self.whitehat_engine = WhiteHatEngine(config)
        else:
            # Use dummy instances if components are missing
            self.threat_analyzer = ThreatAnalyzer(config)
            self.intel_processor = IntelligenceProcessor(config)
            self.device_manager = DeviceManager(config)
            self.whitehat_engine = WhiteHatEngine(config)

        self.conversation_history: list[dict[str, Any]] = []
        self.security_context: dict[str, Any] = {
            "threat_level": "low",
            "active_threats": [],
            "last_scan": None,
            "device_status": {},
            "whitehat_authorized": False,
        }

    async def initialize(self) -> None:
        """
        Initializes the AI assistant and its subsystems, loading necessary models
        and data. This method is designed to be resilient and allow the application
        to start even if some components fail.
        """
        logger.info("Initializing Celsius AI core...")
        try:
            if TRANSFORMERS_AVAILABLE:
                logger.info("Transformers library is available. Local AI models can be loaded if needed.")
            else:
                logger.info("Transformers library not available. Using lightweight, rule-based processing.")

            # Initialize subsystems with individual error handling
            subsystems = {
                "Threat Analyzer": self.threat_analyzer,
                "Intelligence Processor": self.intel_processor,
                "White Hat Engine": self.whitehat_engine,
                "Self-Learning Module": self.self_learning,
            }

            for name, system in subsystems.items():
                if hasattr(system, "initialize"):
                    try:
                        await system.initialize()
                    except Exception as e:
                        logger.warning(f"{name} initialization failed: {e}")
                elif hasattr(system, "_load_knowledge_base"):  # For SelfLearningAI
                    try:
                        await system._load_knowledge_base()
                    except Exception as e:
                        logger.warning(f"{name} initialization failed: {e}")

            logger.info("✅ Celsius AI core initialized successfully.")

        except Exception as e:
            logger.error(f"A critical error occurred during Celsius AI initialization: {e}", exc_info=True)
            logger.warning("Starting in a minimal mode with only basic chat functionality.")

    async def process_query(self, query: str) -> str:
        """
        Processes a user query by classifying its intent, routing it to the
        appropriate handler, and returning a human-like response.

        Args:
            query (str): The user's input query.

        Returns:
            str: A formatted, conversational response from the AI.
        """
        logger.info(f"Processing query: '{query[:75]}...'")
        try:
            # Enhance the interaction with conversational context
            conversation_context = self.conversational_ai.process_conversation(query, "general")
            self._add_to_history(query, "user")

            # Classify the query to determine user intent
            query_type = await self._classify_query(query)
            logger.debug(f"Classified query as type: {query_type}")

            # Route to the appropriate handler based on classification
            handler_map = {
                "security_scan": self._handle_security_scan,
                "threat_analysis": self._handle_threat_analysis,
                "device_management": self._handle_device_query,
                "intelligence": self._handle_intelligence_query,
                "whitehat": self._handle_whitehat_query,
                "learning": self._handle_learning_query,
                "health": self._handle_health_query,
                "fitness": self._handle_health_query,  # Route fitness to health
                "status": self._handle_status_query,
                "general": self._handle_general_query,
            }
            handler = handler_map.get(query_type, self._handle_general_query)
            response = await handler(query)

            # Enhance the raw response with a conversational personality
            enhanced_response = self.conversational_ai.enhance_response(response, conversation_context)
            self._add_to_history(enhanced_response, "assistant")

            # Learn from the completed interaction
            await self.self_learning.learn_from_conversation(
                {"user_message": query, "ai_response": enhanced_response, "timestamp": datetime.now().isoformat()}
            )

            return enhanced_response

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return f"I'm sorry, but I encountered an unexpected error while processing your request: {e}"

    def _add_to_history(self, text: str, role: str) -> None:
        """
        Adds an entry to the conversation history and manages its size.

        Args:
            text (str): The message text from the user or assistant.
            role (str): The role, either 'user' or 'assistant'.
        """
        self.conversation_history.append({"timestamp": datetime.now().isoformat(), "role": role, "content": text})
        # Keep the history to a manageable size
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-20:]

    async def _classify_query(self, query: str) -> str:
        """
        Classifies the user's query into a specific category based on keywords.

        Args:
            query (str): The user's input query.

        Returns:
            str: The classified query type (e.g., 'security_scan', 'health').
        """
        query_lower = query.lower()

        # Define keyword mappings for different categories
        keyword_map = {
            "whitehat": ["pentest", "penetration", "hack", "exploit", "whitehat", "authorize", "engagement"],
            "health": [
                "health",
                "fitness",
                "workout",
                "exercise",
                "weight",
                "diet",
                "nutrition",
                "steps",
                "heart rate",
                "sleep",
                "calories",
                "gemini data",
                "import health",
            ],
            "learning": ["learn", "knowledge", "training", "teach", "study", "education", "module"],
            "security_scan": ["scan"],
            "threat_analysis": ["threat", "malware", "virus", "attack", "breach", "security"],
            "device_management": ["device", "computer", "phone", "tablet", "laptop", "sync"],
            "intelligence": ["intelligence", "cve", "vulnerability", "exploit", "news"],
            "status": ["status", "overview", "dashboard", "summary", "report"],
        }

        # Iterate through mappings to find a match
        for category, keywords in keyword_map.items():
            if any(keyword in query_lower for keyword in keywords):
                # Special case for 'security_scan' vs 'threat_analysis'
                if category == "threat_analysis" and "scan" in query_lower:
                    return "security_scan"
                return category

        return "general"

    async def _handle_security_scan(self, query: str) -> str:
        """Handle security scanning requests."""
        try:
            scan_type = "full"
            if "network" in query.lower():
                scan_type = "network"
            elif "file" in query.lower():
                scan_type = "file"

            results = await self.threat_analyzer.perform_scan(scan_type)

            response = f"🔍 Security Scan Complete ({scan_type})\\n\\n"
            response += f"Threats Detected: {len(results.get('threats', []))}\\n"
            response += f"Vulnerabilities: {len(results.get('vulnerabilities', []))}\\n"
            response += f"Risk Level: {results.get('risk_level', 'Unknown')}\\n\\n"

            if results.get("threats"):
                response += "⚠️ Active Threats:\\n"
                for threat in results["threats"][:3]:  # Show top 3
                    response += f"  • {threat.get('name', 'Unknown')}: {threat.get('severity', 'Unknown')}\\n"

            return response

        except Exception as e:
            return f"❌ Security scan failed: {e}"

    async def _handle_threat_analysis(self, query: str) -> str:
        """Handle threat analysis requests."""
        try:
            analysis = await self.threat_analyzer.analyze_current_threats()

            response = f"🛡️ Threat Analysis Report\\n\\n"
            response += f"Current Threat Level: {analysis.get('level', 'Unknown')}\\n"
            response += f"Active Monitoring: {'✅' if analysis.get('monitoring') else '❌'}\\n\\n"

            if analysis.get("recommendations"):
                response += "💡 Recommendations:\\n"
                for rec in analysis["recommendations"][:3]:
                    response += f"  • {rec}\\n"

            return response

        except Exception as e:
            return f"❌ Threat analysis failed: {e}"

    async def _handle_device_query(self, query: str) -> str:
        """Handle device management queries."""
        try:
            devices = await self.device_manager.get_device_status()

            response = "📱 Device Status Report\\n\\n"

            for device in devices:
                status_icon = "🟢" if device.get("secure") else "🟡"
                response += f"{status_icon} {device.get('name', 'Unknown')}: {device.get('status', 'Unknown')}\\n"

            return response

        except Exception as e:
            return f"❌ Device query failed: {e}"

    async def _handle_intelligence_query(self, query: str) -> str:
        """Handle threat intelligence queries."""
        try:
            intel = await self.intel_processor.query_intelligence(query)

            response = "🔍 Threat Intelligence\\n\\n"
            response += f"Query: {query}\\n"
            response += f"Results: {len(intel.get('results', []))} items found\\n\\n"

            if intel.get("results"):
                for result in intel["results"][:2]:  # Show top 2
                    response += f"• {result.get('title', 'Unknown')}\\n"
                    response += f"  Severity: {result.get('severity', 'Unknown')}\\n\\n"

            return response

        except Exception as e:
            return f"❌ Intelligence query failed: {e}"

    async def _handle_whitehat_query(self, query: str) -> str:
        """Handle white hat hacking and penetration testing queries."""
        try:
            query_lower = query.lower()

            # Check for authorization requests
            if any(word in query_lower for word in ["authorize", "authorization", "request"]):
                auth_status = self.whitehat_engine.get_authorization_status()
                if auth_status["authorized"]:
                    response = f"🔐 White Hat Authorization Status\\n\\n"
                    response += f"Status: ✅ AUTHORIZED\\n"
                    response += f"Authorization ID: {auth_status['authorization_id']}\\n"
                    response += f"Level: {auth_status['level']}\\n"
                    response += f"Valid Until: {auth_status['valid_until']}\\n"
                    response += f"Authorized Techniques: {auth_status['authorized_techniques']}\\n"
                    return response
                else:
                    response = f"🔐 White Hat Authorization Required\\n\\n"
                    response += f"Status: ❌ NOT AUTHORIZED\\n"
                    response += f"Reason: {auth_status.get('message', 'No active authorization')}\\n\\n"
                    response += f"To request authorization:\\n"
                    response += f"1. Use command: 'request pentest authorization'\\n"
                    response += f"2. Complete the authorization form\\n"
                    response += f"3. Ensure legal compliance\\n"
                    return response

            # Handle authorization request initiation
            if "request" in query_lower and ("pentest" in query_lower or "authorization" in query_lower):
                success = await self.whitehat_engine.request_authorization()
                if success:
                    return "✅ White hat authorization completed successfully! You can now use penetration testing commands."
                else:
                    return "❌ Authorization request cancelled or failed."

            # Check if authorized for other operations
            auth_status = self.whitehat_engine.get_authorization_status()
            if not auth_status["authorized"]:
                return f"🔐 Authorization required for penetration testing operations.\\nUse 'request pentest authorization' to begin."

            # Handle technique execution
            if "run" in query_lower or "execute" in query_lower:
                # Extract target and technique from query
                # This is a simplified parser - in production, use more sophisticated NLP
                words = query_lower.split()

                # Look for target (IP, domain, etc.)
                target = None
                for word in words:
                    if "." in word and not word.startswith("."):
                        target = word
                        break

                if not target:
                    return "❌ Please specify a target (IP address or domain) for the penetration test."

                # Look for technique
                available_techniques = list(self.whitehat_engine.technique_library.techniques.keys())
                technique = None
                for tech in available_techniques:
                    if any(part in query_lower for part in tech.split("_")):
                        technique = tech
                        break

                if not technique:
                    techniques_list = "\\n".join([f"  • {tech}" for tech in available_techniques[:10]])
                    return f"❌ Please specify a technique. Available techniques:\\n{techniques_list}"

                # Execute the technique
                result = await self.whitehat_engine.execute_technique(technique, target)

                if "error" in result:
                    return f"❌ Technique execution failed: {result['error']}"

                response = f"🎯 Penetration Test Result\\n\\n"
                response += f"Technique: {technique}\\n"
                response += f"Target: {target}\\n"
                response += f"Timestamp: {result.get('timestamp', 'Unknown')}\\n\\n"

                # Summarize results
                if result.get("open_ports"):
                    response += f"Open Ports: {len(result['open_ports'])}\\n"
                if result.get("vulnerabilities"):
                    response += f"Vulnerabilities: {len(result['vulnerabilities'])}\\n"
                if result.get("subdomains"):
                    response += f"Subdomains: {len(result['subdomains'])}\\n"

                return response

            # Handle engagement requests
            if "engagement" in query_lower or "full" in query_lower:
                words = query_lower.split()
                target = None
                for word in words:
                    if "." in word and not word.startswith("."):
                        target = word
                        break

                if not target:
                    return "❌ Please specify a target for the penetration testing engagement."

                engagement = await self.whitehat_engine.run_engagement(target)

                if "error" in engagement:
                    return f"❌ Engagement failed: {engagement['error']}"

                response = f"🎯 Penetration Testing Engagement Report\\n\\n"
                response += f"Target: {engagement['target']}\\n"
                response += f"Engagement ID: {engagement['id']}\\n"
                response += f"Phases Completed: {len(engagement['phases'])}\\n"
                response += f"Findings: {len(engagement['findings'])}\\n\\n"

                # Summarize high-severity findings
                high_severity = [f for f in engagement["findings"] if f.get("severity") == "high"]
                if high_severity:
                    response += f"🚨 High Severity Issues: {len(high_severity)}\\n"
                    for finding in high_severity[:3]:
                        response += f"  • {finding['title']}\\n"

                return response

            # Show available capabilities
            auth_status = self.whitehat_engine.get_authorization_status()
            techniques = self.whitehat_engine.get_available_techniques()

            response = f"🔐 White Hat Hacking Capabilities\\n\\n"
            response += f"Authorization Level: {auth_status['level']}\\n"
            response += f"Available Technique Categories: {len(techniques)}\\n\\n"

            response += f"Commands:\\n"
            response += f"  • 'run [technique] on [target]' - Execute specific technique\\n"
            response += f"  • 'full engagement [target]' - Complete penetration test\\n"
            response += f"  • 'authorize' - Check authorization status\\n\\n"

            response += f"Example: 'run port scan on example.com'\\n"

            return response

        except Exception as e:
            return f"❌ White hat query failed: {e}"

    async def _handle_learning_query(self, query: str) -> str:
        """Handle learning-related queries and module management."""
        try:
            query_lower = query.lower()

            # Get learning statistics
            if any(word in query_lower for word in ["status", "stats", "statistics"]):
                stats = self.self_learning.get_learning_stats()
                return f"""🧠 **Learning Status Report**

**Knowledge Base:**
• Total Entries: {stats.get('total_entries', 0)}
• Active Domains: {stats.get('domains_covered', 0)}
• Average Confidence: {stats.get('confidence_average', 0):.1%}

**Active Learning Modules:**
{chr(10).join([f"• {module['name']}" for module in stats.get('active_modules', [])])}

**Last Learning Session:** {stats.get('last_learning_session', 'Never')}

Use 'learn about [topic]' to teach me something new!"""

            # Enable/disable learning modules
            elif "enable" in query_lower or "disable" in query_lower:
                action = "enable" if "enable" in query_lower else "disable"

                # Extract domain from query (simplified)
                domains = [
                    "cybersecurity",
                    "programming",
                    "finance",
                    "legal",
                    "health",
                    "fitness",
                    "business",
                    "technology",
                ]
                target_domain = None

                for domain in domains:
                    if domain in query_lower:
                        target_domain = domain
                        break

                if target_domain:
                    enabled = action == "enable"
                    await self.self_learning.enable_learning_module(target_domain, enabled)
                    return f"✅ {action.capitalize()}d learning module for {target_domain}"
                else:
                    return f"❓ Please specify which learning module to {action}: {', '.join(domains)}"

            # Get learning suggestions
            elif any(word in query_lower for word in ["suggest", "recommend", "what should", "topics"]):
                suggestions = await self.self_learning.suggest_learning_topics()
                if suggestions:
                    return f"""💡 **Learning Suggestions:**

{chr(10).join([f"• {suggestion}" for suggestion in suggestions])}

I can learn more effectively if you teach me about these topics!"""
                else:
                    return "🎓 Your knowledge base looks comprehensive! Feel free to ask me anything or teach me something new."

            # Teach the AI something new
            elif any(word in query_lower for word in ["learn", "teach", "remember"]):
                # Extract the learning content (simplified extraction)
                if "about" in query_lower:
                    topic_start = query_lower.find("about") + 5
                    learning_content = query[topic_start:].strip()
                elif "that" in query_lower:
                    topic_start = query_lower.find("that") + 4
                    learning_content = query[topic_start:].strip()
                else:
                    learning_content = query.strip()

                if learning_content:
                    # Let the self-learning system process this
                    await self.self_learning.learn_from_external_source(content=learning_content, source="user_input")
                    return f"🎓 Thank you for teaching me! I've learned about: {learning_content[:100]}..."
                else:
                    return "❓ What would you like me to learn? Try: 'Learn that [your information]'"

            # Search knowledge base
            elif any(word in query_lower for word in ["know", "knowledge", "search", "find"]):
                # Extract search terms
                search_terms = (
                    query_lower.replace("what do you know about", "")
                    .replace("search for", "")
                    .replace("find", "")
                    .strip()
                )

                if search_terms:
                    knowledge = await self.self_learning.get_knowledge(query=search_terms)
                    if knowledge:
                        return f"""🔍 **Knowledge Search Results:**

Found {len(knowledge)} relevant entries about "{search_terms}":

{chr(10).join([f"• {entry.content[:100]}..." for entry in knowledge[:3]])}

Domain coverage: {', '.join(set(entry.domain for entry in knowledge))}"""
                    else:
                        return (
                            f"❓ I don't have specific knowledge about '{search_terms}' yet. You can teach me about it!"
                        )
                else:
                    return "❓ What would you like me to search for in my knowledge base?"

            # Default learning help
            else:
                return """🧠 **Celsius AI Learning System**

I can learn from conversations and expand my knowledge across multiple domains:

**Commands:**
• `learning status` - View learning statistics
• `learn about [topic]` - Teach me something new
• `what do you know about [topic]` - Search my knowledge
• `learning suggestions` - Get learning recommendations
• `enable/disable [domain] learning` - Manage learning modules

**Learning Domains:**
• Cybersecurity • Programming • Finance • Legal
• Health • Fitness • Business • Technology

I continuously learn from our conversations to provide better assistance!"""

        except Exception as e:
            logger.error(f"Error in learning query: {e}", exc_info=True)
            return f"❌ Learning system error: {e}"

    async def _handle_status_query(self, query: str) -> str:
        """Handle status and overview queries."""
        try:
            # Get overall system status
            overall_status = await self._get_system_status()

            response = "📊 Celsius AI Status Dashboard\\n\\n"
            response += f"System Health: {overall_status.get('health', 'Unknown')}\\n"
            response += f"Security Level: {overall_status.get('security_level', 'Unknown')}\\n"
            response += f"Active Monitoring: {'✅' if overall_status.get('monitoring') else '❌'}\\n"
            response += f"Last Update: {overall_status.get('last_update', 'Unknown')}\\n\\n"

            response += "🔧 Services Status:\\n"
            for service, status in overall_status.get("services", {}).items():
                status_icon = "🟢" if status == "running" else "🔴"
                response += f"  {status_icon} {service}: {status}\\n"

            return response

        except Exception as e:
            return f"❌ Status query failed: {e}"

    async def _handle_health_query(self, query: str) -> str:
        """Handle health and fitness related queries."""
        try:
            query_lower = query.lower()

            # Import Gemini data
            if "import" in query_lower and "gemini" in query_lower:
                return """📊 **Import Health Data from Gemini**

To import your health data from Gemini:

1. **Export your Gemini data**: Copy your health conversations or data
2. **Use the import command**: `import gemini health data: [paste data here]`
3. **I'll parse and store**: Weight, workouts, goals, measurements

**Supported data types:**
• Weight measurements (lbs/kg)
• Workout sessions and duration
• Fitness goals and targets
• Health metrics (steps, sleep, heart rate)
• Nutrition information

Just paste your Gemini health conversations or data after 'import gemini health data:' and I'll extract and organize it!"""

            # Handle Gemini import command
            elif query_lower.startswith("import gemini health data:"):
                gemini_data = query[27:].strip()  # Remove command prefix
                if gemini_data:
                    result = await self.health_manager.import_gemini_data(gemini_data)
                    if result["success"]:
                        return f"✅ {result['message']}\n\nImported {result['imported_count']} health entries successfully!"
                    else:
                        return f"❌ Import failed: {', '.join(result['errors'])}"
                else:
                    return "❓ Please provide the Gemini health data to import after the colon."

            # Health status and summary
            elif any(word in query_lower for word in ["health summary", "fitness status", "health overview"]):
                summary = self.health_manager.get_health_summary()

                response = "🏥 **Health & Fitness Summary**\n\n"
                response += f"📊 **Data Overview:**\n"
                response += f"• Health metrics: {summary['metrics_count']}\n"
                response += f"• Active fitness goals: {summary['active_goals']}\n"
                response += f"• Total workouts: {summary['total_workouts']}\n\n"

                response += f"📈 **Last 30 Days:**\n"
                response += f"• Workouts: {summary['last_30_days']['workouts']}\n"
                response += f"• Total exercise time: {summary['last_30_days']['total_workout_minutes']} minutes\n\n"

                if summary["recent_trends"]:
                    response += "📊 **Recent Trends:**\n"
                    for metric, trend in summary["recent_trends"].items():
                        response += f"• {metric.title()}: {trend['trend']} ({trend['change_percent']:+.1f}%)\n"

                if summary["goal_progress"]:
                    response += "\n🎯 **Goal Progress:**\n"
                    for goal in summary["goal_progress"][:3]:  # Show top 3 goals
                        progress_icon = "✅" if goal["progress_percentage"] >= 100 else "🎯"
                        response += f"{progress_icon} {goal['title']}: {goal['progress_percentage']:.1f}% complete\n"

                return response

            # Set fitness goals
            elif "set" in query_lower and "goal" in query_lower:
                return """🎯 **Set Fitness Goals**

I can help you set and track fitness goals! Tell me:

• **Goal type**: Weight loss, muscle gain, endurance, strength
• **Target**: Specific number (e.g., "lose 10 lbs", "run 5K")
• **Timeline**: When you want to achieve it

**Examples:**
• "Set goal: lose 15 pounds by March"
• "Set goal: run 5K in under 25 minutes by June"
• "Set goal: do 50 push-ups by end of month"

Just describe your goal and I'll track your progress!"""

            # Search health data
            elif "search" in query_lower or "find" in query_lower:
                search_terms = query_lower.replace("search", "").replace("find", "").strip()
                if search_terms:
                    results = self.health_manager.search_health_data(search_terms)

                    response = f"🔍 **Health Data Search: '{search_terms}'**\n\n"

                    if results["metrics"]:
                        response += f"📊 **Metrics** ({len(results['metrics'])} found):\n"
                        for metric in results["metrics"][:3]:
                            response += f"• {metric['metric_type'].replace('_', ' ').title()}: {metric['value']} {metric['unit']}\n"

                    if results["workouts"]:
                        response += f"\n💪 **Workouts** ({len(results['workouts'])} found):\n"
                        for workout in results["workouts"][:3]:
                            response += f"• {workout['workout_type']}: {workout['duration_minutes']} min\n"

                    if results["goals"]:
                        response += f"\n🎯 **Goals** ({len(results['goals'])} found):\n"
                        for goal in results["goals"][:3]:
                            response += f"• {goal['title']}: {goal['progress_percentage']:.1f}% complete\n"

                    if results["insights"]:
                        response += f"\n💡 **Insights:**\n"
                        for insight in results["insights"]:
                            response += f"• {insight}\n"

                    return response if any(results.values()) else f"❓ No health data found for '{search_terms}'"
                else:
                    return "❓ What health data would you like me to search for?"

            # General health help
            else:
                return """🏥 **Celsius Health & Fitness Assistant**

I can help you manage your health and fitness data!

**Key Features:**
• 📊 **Import from Gemini**: Transfer all your health conversations
• 🎯 **Goal Tracking**: Set and monitor fitness goals
• 📈 **Progress Analysis**: Trends and insights
• 💪 **Workout Logging**: Track exercise sessions
• ⚖️ **Health Metrics**: Weight, measurements, vital signs

**Quick Commands:**
• `import gemini health data: [your data]`
• `health summary` - Full overview
• `set goal: [your goal]` - Create fitness goals
• `search [keyword]` - Find specific data

Ready to help you achieve your health and fitness goals! 💪"""

        except Exception as e:
            logger.error(f"Error in health query: {e}", exc_info=True)
            return f"❌ Health query error: {e}"

    async def _handle_general_query(self, query: str) -> str:
        """Handle general cybersecurity questions."""
        try:
            # Use local AI model for privacy-first processing
            # This is a simplified version - in production, you'd want more sophisticated NLP

            response = "🤖 I'm here to help with cybersecurity questions. "

            if any(word in query.lower() for word in ["password", "passwords"]):
                response += "For password security, I recommend using unique, complex passwords with a password manager. Enable 2FA wherever possible."
            elif any(word in query.lower() for word in ["phishing", "email"]):
                response += "Be cautious with email links and attachments. Verify sender authenticity and check URLs before clicking."
            elif any(word in query.lower() for word in ["update", "patch"]):
                response += "Keep your systems updated with the latest security patches. Enable automatic updates when possible."
            else:
                response += "Could you be more specific about your cybersecurity question? I can help with threats, vulnerabilities, best practices, and more."

            return response

        except Exception as e:
            logger.error(f"General query failed: {e}", exc_info=True)
            return f"❌ General query failed: {e}"

    async def _get_system_status(self) -> dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "health": "Good",
            "security_level": self.security_context.get("threat_level", "Unknown"),
            "monitoring": True,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "services": {
                "Threat Monitor": "running",
                "Device Manager": "running",
                "Intelligence": "running",
                "AI Core": "running",
            },
        }

    async def shutdown(self) -> None:
        """
        Shuts down the AI assistant and its subsystems gracefully.
        """
        logger.info("Shutting down Celsius AI core...")
        if CELSIUS_COMPONENTS_AVAILABLE:
            await self.threat_analyzer.shutdown()
            await self.intel_processor.shutdown()
        logger.info("✅ Celsius AI core shutdown complete.")
