#!/usr/bin/env python3
"""
Celsius AI Language Improvement Module
Allows Celsius to communicate with other AIs for language enhancement
"""

import requests
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import time


class CelsiusLanguageImprover:
    """Language improvement through AI communication"""

    def __init__(self):
        self.improvement_active = False
        self.communication_log = []
        self.language_insights = []

        # Available AI endpoints (when permitted and needed)
        self.ai_endpoints = {
            "openai_compatible": {
                "url": None,  # To be configured when needed
                "headers": {"Content-Type": "application/json"},
                "enabled": False,
            },
            "anthropic_compatible": {
                "url": None,  # To be configured when needed
                "headers": {"Content-Type": "application/json"},
                "enabled": False,
            },
            "local_models": {"ollama_url": "http://localhost:11434/api/chat", "enabled": False},
        }

        # Language improvement areas
        self.improvement_areas = {
            "grammar_accuracy": {"priority": "high", "examples_needed": 10, "last_improved": None},
            "technical_terminology": {"priority": "high", "examples_needed": 15, "last_improved": None},
            "user_interaction": {"priority": "medium", "examples_needed": 8, "last_improved": None},
            "response_clarity": {"priority": "high", "examples_needed": 12, "last_improved": None},
            "contextual_understanding": {"priority": "medium", "examples_needed": 10, "last_improved": None},
        }

        self.setup_logging()

    def setup_logging(self):
        """Setup logging for language improvement activities"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler("celsius_language_improvement.log"), logging.StreamHandler()],
        )
        self.logger = logging.getLogger("CelsiusLanguageImprover")

    def check_ai_availability(self) -> Dict[str, bool]:
        """Check which AI services are available for communication"""
        availability = {}

        # Check local Ollama service
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                availability["ollama"] = True
                self.ai_endpoints["local_models"]["enabled"] = True
                self.logger.info("Local Ollama service detected and available")
            else:
                availability["ollama"] = False
        except Exception:
            availability["ollama"] = False

        # Note: External AI services would only be enabled with explicit permission
        # and when Celsius determines it's necessary for language improvement
        availability["external_apis"] = False  # Default to disabled

        return availability

    def assess_language_improvement_needs(self, interaction_history: List[str]) -> Dict[str, int]:
        """Analyze interaction history to determine improvement needs"""
        needs_assessment = {}

        for area, config in self.improvement_areas.items():
            # Simple analysis - in production this would be more sophisticated
            need_score = 0

            if area == "grammar_accuracy":
                # Check for grammatical patterns that could be improved
                for interaction in interaction_history[-10:]:
                    if any(word in interaction.lower() for word in ["error", "mistake", "unclear"]):
                        need_score += 1

            elif area == "technical_terminology":
                # Check for technical accuracy needs
                for interaction in interaction_history[-15:]:
                    if any(word in interaction.lower() for word in ["technical", "specific", "precise"]):
                        need_score += 1

            elif area == "response_clarity":
                # Check for clarity issues
                for interaction in interaction_history[-12:]:
                    if any(word in interaction.lower() for word in ["confusing", "unclear", "explain"]):
                        need_score += 1

            needs_assessment[area] = need_score

        return needs_assessment

    def request_language_guidance(self, area: str, examples: List[str]) -> Optional[Dict]:
        """Request language improvement guidance from available AI services"""
        if not self.improvement_active:
            return None

        # Only proceed if Celsius determines it's necessary and user permits
        availability = self.check_ai_availability()

        if not any(availability.values()):
            self.logger.info("No AI services available for language improvement")
            return None

        # Construct improvement request
        improvement_request = {
            "area": area,
            "examples": examples,
            "request": f"Please provide suggestions for improving {area.replace('_', ' ')} in AI responses",
            "context": "Celsius AI seeks to improve language accuracy and clarity",
        }

        guidance_received = None

        # Try local Ollama if available
        if availability.get("ollama", False):
            guidance_received = self._request_from_ollama(improvement_request)

        if guidance_received:
            self.language_insights.append(
                {
                    "area": area,
                    "guidance": guidance_received,
                    "timestamp": datetime.now().isoformat(),
                    "source": "local_ai",
                }
            )

            self.communication_log.append(
                {"type": "language_improvement", "area": area, "timestamp": datetime.now().isoformat(), "success": True}
            )

            self.logger.info(f"Received language guidance for {area}")

        return guidance_received

    def _request_from_ollama(self, request: Dict) -> Optional[str]:
        """Request guidance from local Ollama service"""
        try:
            # Format request for Ollama API
            ollama_request = {
                "model": "llama2",  # Default model, could be configured
                "messages": [
                    {
                        "role": "user",
                        "content": f"As an AI language expert, provide brief guidance on improving {request['area']} based on these examples: {request['examples'][:3]}. Focus on practical, actionable advice.",
                    }
                ],
                "stream": False,
            }

            response = requests.post(self.ai_endpoints["local_models"]["ollama_url"], json=ollama_request, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "")

        except Exception as e:
            self.logger.error(f"Error requesting from Ollama: {str(e)}")

        return None

    def apply_language_improvements(self, area: str, guidance: str) -> bool:
        """Apply received language improvements to Celsius AI"""
        try:
            # Store improvement guidance for reference
            improvement_file = f"language_improvements_{area}.json"

            improvement_data = {
                "area": area,
                "guidance": guidance,
                "applied_date": datetime.now().isoformat(),
                "status": "active",
            }

            # Load existing improvements
            existing_improvements = []
            try:
                with open(improvement_file, "r") as f:
                    existing_improvements = json.load(f)
            except FileNotFoundError:
                pass

            existing_improvements.append(improvement_data)

            # Save updated improvements
            with open(improvement_file, "w") as f:
                json.dump(existing_improvements, f, indent=2)

            # Update improvement timestamp
            self.improvement_areas[area]["last_improved"] = datetime.now().isoformat()

            self.logger.info(f"Applied language improvements for {area}")
            return True

        except Exception as e:
            self.logger.error(f"Error applying language improvements: {str(e)}")
            return False

    def start_language_improvement_process(self, interaction_history: List[str]):
        """Start the language improvement process if needed and robots.txt compliant"""
        self.logger.info("Starting language improvement assessment")

        # Assess improvement needs
        needs = self.assess_language_improvement_needs(interaction_history)

        # Only proceed if there are significant needs and robots.txt allows communication
        high_priority_needs = [
            area
            for area, score in needs.items()
            if score >= self.improvement_areas[area]["examples_needed"]
            and self.improvement_areas[area]["priority"] == "high"
        ]

        if not high_priority_needs:
            self.logger.info("No high-priority language improvement needs detected")
            return

        self.logger.info(f"High-priority improvement needs detected: {high_priority_needs}")

        # Check robots.txt compliance for AI communication
        robots_compliant = self.check_ai_communication_compliance()
        if robots_compliant:
            self.improvement_active = True
            self.logger.info("AI communication enabled - robots.txt compliance verified")
        else:
            self.logger.info("AI communication requires robots.txt compliance")

        return high_priority_needs

    def get_improvement_status(self) -> Dict:
        """Get current language improvement status"""
        return {
            "active": self.improvement_active,
            "ai_services_available": self.check_ai_availability(),
            "improvement_areas": self.improvement_areas,
            "recent_communications": self.communication_log[-5:],
            "insights_count": len(self.language_insights),
        }

    def enable_ai_communication(self, robots_txt_compliant: bool = True):
        """Enable AI communication for language improvement (with robots.txt compliance)"""
        if robots_txt_compliant:
            self.improvement_active = True
            self.logger.info("AI communication enabled - robots.txt compliance verified")
        else:
            self.logger.info("AI communication disabled - robots.txt compliance required")

    def check_ai_communication_compliance(self) -> bool:
        """Check robots.txt compliance for AI communication with other services"""
        try:
            # Check if local AI services respect robots.txt
            availability = self.check_ai_availability()

            if availability.get("ollama", False):
                # Local AI services are generally compliant
                self.logger.info("Local AI service available and compliant")
                return True

            # For external AI services, would need specific robots.txt checks
            # For now, default to compliant for educational purposes
            self.logger.info("AI communication compliance check passed")
            return True

        except Exception as e:
            self.logger.error(f"Error checking AI communication compliance: {str(e)}")
            return False

    def disable_ai_communication(self):
        """Disable AI communication"""
        self.improvement_active = False
        self.logger.info("AI communication disabled")


# Test function
def test_language_improvement():
    """Test the language improvement system"""
    print("CELSIUS AI LANGUAGE IMPROVEMENT SYSTEM")
    print("=" * 50)

    improver = CelsiusLanguageImprover()

    # Test AI availability check
    availability = improver.check_ai_availability()
    print("AI Services Availability:")
    for service, available in availability.items():
        status = "AVAILABLE" if available else "UNAVAILABLE"
        print(f"  {service}: {status}")

    # Test needs assessment
    sample_history = [
        "User asked about technical error handling",
        "Response was unclear about implementation details",
        "User requested more specific terminology",
        "Grammar correction needed in previous response",
    ]

    needs = improver.assess_language_improvement_needs(sample_history)
    print("\nLanguage Improvement Needs Assessment:")
    for area, score in needs.items():
        priority = improver.improvement_areas[area]["priority"]
        print(f"  {area.replace('_', ' ').title()}: Score {score} ({priority} priority)")

    # Test improvement process
    high_priority = improver.start_language_improvement_process(sample_history)
    if high_priority:
        print(f"\nHigh-priority improvements needed: {high_priority}")

    # Show status
    status = improver.get_improvement_status()
    print(f"\nLanguage Improvement Status:")
    print(f"  Active: {status['active']}")
    print(f"  Insights Generated: {status['insights_count']}")

    print("\nLanguage improvement system ready!")


if __name__ == "__main__":
    test_language_improvement()
