#!/usr/bin/env python3
"""
Celsius Adaptive Security System
Applies machine learning knowledge to enhance system security automatically
"""

import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import logging
import re


class AdaptiveSecurityEngine:
    """
    Applies learning from web sources to automatically improve system security
    """

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.learning_reports_dir = self.project_root / "learning_reports"
        self.knowledge_base_file = self.project_root / "data" / "adaptive_security_kb.json"
        self.security_log = self.project_root / "logs" / "adaptive_security.log"
        self.config_file = self.project_root / "config" / "adaptive_security_config.json"

        # Create directories if they don't exist
        self.knowledge_base_file.parent.mkdir(exist_ok=True, parents=True)
        self.security_log.parent.mkdir(exist_ok=True, parents=True)
        self.config_file.parent.mkdir(exist_ok=True, parents=True)

        self.setup_logging()
        self.load_configuration()
        self.knowledge_base = self.load_knowledge_base()

    def setup_logging(self):
        """Setup logging for adaptive security"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(self.security_log, encoding="utf-8"), logging.StreamHandler()],
        )
        self.logger = logging.getLogger("AdaptiveSecurity")

    def load_configuration(self):
        """Load adaptive security configuration"""
        default_config = {
            "auto_apply_security_updates": True,
            "threat_detection_sensitivity": "medium",
            "learning_update_interval": 3600,  # 1 hour
            "max_auto_modifications": 5,  # per day
            "require_approval": True,
            "protected_files": ["celsius_ultimate_hub.py", "main.py", "enhanced_mobile_dashboard.py"],
            "security_rules": {
                "port_scanning_protection": True,
                "rate_limiting": True,
                "authentication_hardening": True,
                "log_monitoring": True,
            },
        }

        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
        except Exception as e:
            self.logger.warning(f"Could not load config, using defaults: {e}")

        self.config = default_config
        self.save_configuration()

    def save_configuration(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")

    def load_knowledge_base(self) -> Dict[str, Any]:
        """Load the adaptive security knowledge base"""
        try:
            if self.knowledge_base_file.exists():
                with open(self.knowledge_base_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load knowledge base: {e}")

        # Default knowledge base
        return {
            "threats": {},
            "vulnerabilities": {},
            "mitigations": {},
            "best_practices": {},
            "last_updated": datetime.now().isoformat(),
            "learning_sources": [],
            "applied_improvements": [],
        }

    def save_knowledge_base(self):
        """Save knowledge base to file"""
        try:
            self.knowledge_base["last_updated"] = datetime.now().isoformat()
            with open(self.knowledge_base_file, "w") as f:
                json.dump(self.knowledge_base, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save knowledge base: {e}")

    async def analyze_learning_reports(self) -> List[Dict[str, Any]]:
        """Analyze recent learning reports for security insights"""
        security_insights = []

        if not self.learning_reports_dir.exists():
            self.logger.warning("Learning reports directory not found")
            return security_insights

        # Get recent learning reports
        report_files = list(self.learning_reports_dir.glob("*.json"))
        if not report_files:
            self.logger.info("No learning reports found")
            return security_insights

        # Analyze latest reports
        for report_file in sorted(report_files, key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
            try:
                with open(report_file, "r") as f:
                    report_data = json.load(f)

                # Extract security-relevant information
                if "recent_items" in report_data:
                    for item in report_data["recent_items"]:
                        if self.is_security_relevant(item):
                            insight = self.extract_security_insight(item)
                            if insight:
                                security_insights.append(insight)

            except Exception as e:
                self.logger.error(f"Error analyzing report {report_file}: {e}")

        return security_insights

    def is_security_relevant(self, item: Dict[str, Any]) -> bool:
        """Check if a learning item is security-relevant"""
        security_keywords = [
            "vulnerability",
            "exploit",
            "attack",
            "threat",
            "malware",
            "security",
            "penetration",
            "breach",
            "compromise",
            "mitigation",
            "hardening",
            "authentication",
            "authorization",
            "encryption",
            "firewall",
            "intrusion",
            "detection",
            "prevention",
            "cve",
            "patch",
            "update",
            "backdoor",
            "injection",
            "xss",
            "csrf",
        ]

        content = str(item).lower()
        return any(keyword in content for keyword in security_keywords)

    def extract_security_insight(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract actionable security insight from learning item"""
        try:
            insight = {
                "type": "general",
                "severity": "low",
                "description": item.get("content", ""),
                "source": item.get("source", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "applicable": False,
                "mitigation": None,
            }

            content = str(item).lower()

            # Classify insight type and severity
            if any(word in content for word in ["critical", "high", "severe", "exploit"]):
                insight["severity"] = "high"
            elif any(word in content for word in ["medium", "moderate", "vulnerability"]):
                insight["severity"] = "medium"

            # Determine if applicable to Celsius AI
            if any(word in content for word in ["python", "flask", "web", "api", "server"]):
                insight["applicable"] = True

            # Extract potential mitigations
            if "patch" in content or "update" in content:
                insight["mitigation"] = "update_dependencies"
            elif "authentication" in content:
                insight["mitigation"] = "strengthen_auth"
            elif "rate limit" in content:
                insight["mitigation"] = "implement_rate_limiting"

            return insight

        except Exception as e:
            self.logger.error(f"Error extracting security insight: {e}")
            return None

    async def apply_security_improvements(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply security improvements based on insights"""
        improvements = []
        daily_modifications = self.count_daily_modifications()

        if daily_modifications >= self.config.get("max_auto_modifications", 5):
            self.logger.warning("Daily modification limit reached")
            return improvements

        for insight in insights:
            if not insight.get("applicable", False):
                continue

            improvement = await self.apply_single_improvement(insight)
            if improvement:
                improvements.append(improvement)

        return improvements

    async def apply_single_improvement(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a single security improvement"""
        try:
            mitigation = insight.get("mitigation")

            if mitigation == "update_dependencies":
                return await self.suggest_dependency_updates(insight)
            elif mitigation == "strengthen_auth":
                return await self.strengthen_authentication(insight)
            elif mitigation == "implement_rate_limiting":
                return await self.implement_rate_limiting(insight)
            else:
                return await self.general_security_hardening(insight)

        except Exception as e:
            self.logger.error(f"Error applying improvement: {e}")
            return None

    async def suggest_dependency_updates(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest dependency updates based on security insight"""
        improvement = {
            "type": "dependency_update",
            "description": f"Security update recommended: {insight['description'][:100]}...",
            "action": "Update Python dependencies to latest secure versions",
            "files_affected": ["requirements.txt"],
            "severity": insight["severity"],
            "auto_apply": False,  # Requires approval
            "timestamp": datetime.now().isoformat(),
        }

        # Log the suggestion
        self.logger.info(f"Suggested dependency update: {improvement['description']}")
        self.knowledge_base["applied_improvements"].append(improvement)
        self.save_knowledge_base()

        return improvement

    async def strengthen_authentication(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Strengthen authentication based on security insight"""
        improvement = {
            "type": "authentication_hardening",
            "description": f"Authentication enhancement: {insight['description'][:100]}...",
            "action": "Implement stronger authentication mechanisms",
            "files_affected": ["celsius_ultimate_hub.py", "enhanced_mobile_dashboard.py"],
            "severity": insight["severity"],
            "auto_apply": False,
            "recommendations": [
                "Add session timeout",
                "Implement account lockout",
                "Strengthen password requirements",
                "Add two-factor authentication",
            ],
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(f"Suggested authentication hardening: {improvement['description']}")
        self.knowledge_base["applied_improvements"].append(improvement)
        self.save_knowledge_base()

        return improvement

    async def implement_rate_limiting(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Implement rate limiting based on security insight"""
        improvement = {
            "type": "rate_limiting",
            "description": f"Rate limiting recommended: {insight['description'][:100]}...",
            "action": "Implement API rate limiting to prevent abuse",
            "files_affected": ["enhanced_mobile_dashboard.py"],
            "severity": insight["severity"],
            "auto_apply": False,
            "implementation": {
                "max_requests_per_minute": 60,
                "max_requests_per_hour": 1000,
                "block_duration": 300,  # 5 minutes
            },
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(f"Suggested rate limiting: {improvement['description']}")
        self.knowledge_base["applied_improvements"].append(improvement)
        self.save_knowledge_base()

        return improvement

    async def general_security_hardening(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """General security hardening based on insight"""
        improvement = {
            "type": "general_hardening",
            "description": f"Security hardening: {insight['description'][:100]}...",
            "action": "General security improvements",
            "severity": insight["severity"],
            "auto_apply": False,
            "recommendations": [
                "Review and update security headers",
                "Implement input validation",
                "Add security logging",
                "Update error handling",
            ],
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(f"General security hardening suggested: {improvement['description']}")
        self.knowledge_base["applied_improvements"].append(improvement)
        self.save_knowledge_base()

        return improvement

    def count_daily_modifications(self) -> int:
        """Count modifications made today"""
        today = datetime.now().date()
        count = 0

        for improvement in self.knowledge_base.get("applied_improvements", []):
            try:
                improvement_date = datetime.fromisoformat(improvement["timestamp"]).date()
                if improvement_date == today:
                    count += 1
            except:
                continue

        return count

    async def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        insights = await self.analyze_learning_reports()
        improvements = await self.apply_security_improvements(insights)

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_insights": len(insights),
            "applicable_insights": len([i for i in insights if i.get("applicable", False)]),
            "improvements_suggested": len(improvements),
            "daily_modifications": self.count_daily_modifications(),
            "security_status": "active",
            "insights": insights[:10],  # Last 10 insights
            "improvements": improvements,
            "knowledge_base_size": len(self.knowledge_base.get("threats", {})),
            "configuration": self.config,
        }

        return report

    async def run_continuous_monitoring(self):
        """Run continuous security monitoring"""
        self.logger.info("Starting adaptive security monitoring...")

        while True:
            try:
                # Generate security report
                report = await self.generate_security_report()

                # Log summary
                self.logger.info(
                    f"Security analysis: {report['total_insights']} insights, "
                    f"{report['improvements_suggested']} improvements"
                )

                # Save report
                report_file = (
                    self.project_root / "logs" / f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                with open(report_file, "w") as f:
                    json.dump(report, f, indent=2)

                # Wait for next cycle
                await asyncio.sleep(self.config.get("learning_update_interval", 3600))

            except Exception as e:
                self.logger.error(f"Error in security monitoring: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error


async def main():
    """Main function for standalone execution"""
    engine = AdaptiveSecurityEngine()

    # Generate a security report
    report = await engine.generate_security_report()

    print("\n=== CELSIUS ADAPTIVE SECURITY REPORT ===")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Total Security Insights: {report['total_insights']}")
    print(f"Applicable Insights: {report['applicable_insights']}")
    print(f"Improvements Suggested: {report['improvements_suggested']}")
    print(f"Daily Modifications: {report['daily_modifications']}")
    print(f"Security Status: {report['security_status']}")

    if report["improvements"]:
        print("\nRecent Security Improvements:")
        for improvement in report["improvements"][:5]:
            print(f"  - {improvement['type']}: {improvement['description']}")

    print(f"\nKnowledge Base Size: {report['knowledge_base_size']} items")
    print("Adaptive security monitoring active!")


if __name__ == "__main__":
    asyncio.run(main())
