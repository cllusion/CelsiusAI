from pathlib import Path
import sys

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.learning.celsius_web_learning_integration import CelsiusWebLearningIntegration

if __name__ == "__main__":
    wli = CelsiusWebLearningIntegration()
    report = wli.generate_daily_report()
    print("REPORT_CREATED:", bool(report))
    if report:
        print("Report keys:", list(report.keys())[:10])
