#!/usr/bin/env python3
"""
Celsius Learning Application Launcher
Coordinates adaptive security and self-improvement systems
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Import our learning application modules
from learning.celsius_adaptive_security import AdaptiveSecurityEngine
from learning.celsius_self_improvement import SelfImprovementEngine


class LearningApplicationCoordinator:
    """
    Coordinates both adaptive security and self-improvement systems
    """

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.setup_logging()

        # Initialize engines
        self.security_engine = AdaptiveSecurityEngine()
        self.improvement_engine = SelfImprovementEngine()

        self.running = False

    def setup_logging(self):
        """Setup coordinated logging"""
        log_file = self.project_root / "logs" / "learning_application.log"
        log_file.parent.mkdir(exist_ok=True, parents=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
        )
        self.logger = logging.getLogger("LearningCoordinator")

    async def run_analysis_cycle(self):
        """Run one complete analysis cycle"""
        try:
            self.logger.info("Starting learning application analysis cycle...")

            # Run security analysis
            security_report = await self.security_engine.generate_security_report()
            self.logger.info(
                f"Security analysis: {security_report['total_insights']} insights, "
                f"{security_report['improvements_suggested']} improvements"
            )

            # Run improvement analysis
            improvement_report = await self.improvement_engine.generate_improvement_report()
            self.logger.info(
                f"Self-improvement analysis: {improvement_report['opportunities_found']} opportunities, "
                f"{improvement_report['improvements_generated']} improvements"
            )

            # Generate combined report
            combined_report = {
                "timestamp": datetime.now().isoformat(),
                "security": {
                    "insights": security_report["total_insights"],
                    "applicable_insights": security_report["applicable_insights"],
                    "improvements": security_report["improvements_suggested"],
                    "status": security_report["security_status"],
                },
                "self_improvement": {
                    "opportunities": improvement_report["opportunities_found"],
                    "improvements": improvement_report["improvements_generated"],
                    "pending": improvement_report["pending_approvals"],
                    "applied": improvement_report["total_applied"],
                },
                "overall_status": "active",
                "cycle_complete": True,
            }

            # Save combined report
            report_file = (
                self.project_root
                / "logs"
                / f"learning_application_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(report_file, "w") as f:
                json.dump(combined_report, f, indent=2)

            self.logger.info("Learning application cycle completed successfully")
            return combined_report

        except Exception as e:
            self.logger.error(f"Error in analysis cycle: {e}")
            return None

    async def run_continuous_learning(self):
        """Run continuous learning application"""
        self.logger.info("Starting continuous learning application...")
        self.running = True

        cycle_count = 0

        while self.running:
            try:
                cycle_count += 1
                self.logger.info(f"Starting learning cycle #{cycle_count}")

                # Run analysis cycle
                report = await self.run_analysis_cycle()

                if report:
                    self.logger.info(
                        f"Cycle #{cycle_count} completed - "
                        f"Security: {report['security']['improvements']} improvements, "
                        f"Self-improvement: {report['self_improvement']['improvements']} improvements"
                    )

                # Wait 2 hours between cycles (configurable)
                await asyncio.sleep(7200)

            except Exception as e:
                self.logger.error(f"Error in continuous learning: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    def stop(self):
        """Stop continuous learning"""
        self.logger.info("Stopping learning application...")
        self.running = False


async def main():
    """Main function"""
    coordinator = LearningApplicationCoordinator()

    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--once":
            # Run once and exit
            print("Running single learning application cycle...")
            report = await coordinator.run_analysis_cycle()

            if report:
                print("\n=== LEARNING APPLICATION RESULTS ===")
                print(f"Timestamp: {report['timestamp']}")
                print(f"Security Insights: {report['security']['insights']}")
                print(f"Security Improvements: {report['security']['improvements']}")
                print(f"Self-Improvement Opportunities: {report['self_improvement']['opportunities']}")
                print(f"Self-Improvement Suggestions: {report['self_improvement']['improvements']}")
                print(f"Pending Approvals: {report['self_improvement']['pending']}")
                print(f"Overall Status: {report['overall_status']}")
                print("\nLearning application analysis complete!")
            else:
                print("Learning application analysis failed!")

        elif sys.argv[1] == "--continuous":
            # Run continuously
            print("Starting continuous learning application...")
            await coordinator.run_continuous_learning()

        elif sys.argv[1] == "--status":
            # Show status
            security_report = await coordinator.security_engine.generate_security_report()
            improvement_report = await coordinator.improvement_engine.generate_improvement_report()

            print("\n=== LEARNING APPLICATION STATUS ===")
            print(f"Security Engine: {security_report['security_status']}")
            print(f"Security Knowledge Base: {security_report['knowledge_base_size']} items")
            print(f"Daily Security Modifications: {security_report['daily_modifications']}")
            print(f"Self-Improvement Engine: {improvement_report['system_status']}")
            print(f"Pending Improvements: {improvement_report['pending_approvals']}")
            print(f"Applied Improvements: {improvement_report['total_applied']}")
            print(f"Daily Changes: {improvement_report['daily_changes']}")

        else:
            print("Usage: python celsius_learning_application.py [--once|--continuous|--status]")
    else:
        # Default: run once
        print("Running single learning application cycle...")
        report = await coordinator.run_analysis_cycle()

        if report:
            print("\n=== LEARNING APPLICATION RESULTS ===")
            print(f"Security improvements: {report['security']['improvements']}")
            print(f"Self-improvement suggestions: {report['self_improvement']['improvements']}")
            print("Learning application active!")
        else:
            print("Learning application analysis failed!")


if __name__ == "__main__":
    asyncio.run(main())
