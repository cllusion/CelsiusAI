#!/usr/bin/env python3
"""
Check curated alternative sources per topic (e.g., Reddit, HN, Project Gutenberg) and merge findings into contact requests.
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime

from src.learning.celsius_web_learner import CelsiusWebLearner

OUTPUT = Path("data") / "web_learning_contact_requests.json"

CURATED = {
    "cybersecurity": [
        "https://www.reddit.com/r/netsec/",
        "https://news.ycombinator.com/",
    ],
    "programming": [
        "https://www.reddit.com/r/programming/",
        "https://news.ycombinator.com/",
    ],
    "artificial_intelligence": [
        "https://www.reddit.com/r/MachineLearning/",
        "https://news.ycombinator.com/",
    ],
    "general_knowledge": [
        "https://www.gutenberg.org",
    ],
}


async def run_curated():
    db_path = Path(__file__).resolve().parents[2] / "data" / "web_learning.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    learner = CelsiusWebLearner(db_path)
    await learner.initialize()

    results = []
    for topic, sources in CURATED.items():
        for s in sources:
            try:
                contact = await learner.find_contact_email(s)
                alts = await learner.find_alternative_sources(s)
                if contact or alts:
                    results.append(
                        {
                            "topic": topic,
                            "source": s,
                            "contact": contact,
                            "alternatives": alts,
                            "checked_at": datetime.now().isoformat(),
                        }
                    )
            except Exception as e:
                print(f"Error checking {s}: {e}")

    existing = []
    if OUTPUT.exists():
        try:
            existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    keys = {(e.get("topic"), e.get("source"), e.get("contact")) for e in existing}
    merged = list(existing)
    for e in results:
        key = (e.get("topic"), e.get("source"), e.get("contact"))
        if key not in keys:
            merged.append(e)
            keys.add(key)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Wrote {len(merged)} entries to {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(run_curated())
