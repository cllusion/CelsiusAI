#!/usr/bin/env python3
"""Launcher script to run the web learning integration in a separate process.

Run this using the project's Python interpreter to isolate the web learner from the UI
process (prevents console popups and event-loop conflicts when launched as a subprocess).
"""
import time
import logging
from pathlib import Path

try:
    from src.learning.celsius_web_learning_integration import CelsiusWebLearningIntegration
except Exception:
    # allow running from repo root
    from celsius_web_learning_integration import CelsiusWebLearningIntegration


def main():
    logging.basicConfig(level=logging.INFO)
    ROOT = Path(__file__).resolve().parents[2]
    logging.info("Starting Celsius Web Learner subprocess")
    try:
        integration = CelsiusWebLearningIntegration()
        # Start async continuous learning in background thread inside this process
        integration.start_learning_process()
        # Keep process alive
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Web learner subprocess exiting")


if __name__ == '__main__':
    main()
