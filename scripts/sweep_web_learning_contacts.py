#!/usr/bin/env python3
"""
Improved sweep for web learning contact discovery and alternative sources.

Features:
 - Uses configurable timeout and retries
 - Uses a more permissive User-Agent header to discover alternate feeds/contact pages
 - Merges and deduplicates results into data/web_learning_contact_requests.json

Usage:
    python scripts/sweep_web_learning_contacts.py [--relaxed] [--timeout SECS] [--retries N]
"""
import asyncio
import json
import argparse
from pathlib import Path
from datetime import datetime

from src.learning.celsius_web_learner import CelsiusWebLearner

OUTPUT = Path("data") / "web_learning_contact_requests.json"


async def check_source(learner, topic, src, timeout=10, retries=1, ua=None):
    """Run contact and alternative discovery for a single source with retries."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            # The learner's methods accept the URL and use its aiohttp session.
            # We call them directly; they already respect robots.txt.
            contact = await learner.find_contact_email(src)
            alts = await learner.find_alternative_sources(src)
            return {
                "topic": topic,
                "source": src,
                "contact": contact,
                "alternatives": alts,
                "checked_at": datetime.now().isoformat(),
            }
        except Exception as e:
            last_exc = e
            # small backoff
            await asyncio.sleep(0.5 * attempt)
    # all retries failed
    return {
        "topic": topic,
        "source": src,
        "contact": None,
        "alternatives": [],
        "checked_at": datetime.now().isoformat(),
        "error": str(last_exc),
    }


async def sweep_all(timeout=10, retries=1, relaxed=False):
    # Create a local learner instance and initialize its async resources in this loop
    db_path = Path(__file__).resolve().parents[2] / "data" / "web_learning.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    learner = CelsiusWebLearner(db_path)
    # ensure the learner's async DB and session are initialized on our event loop
    try:
        await learner.initialize()
    except Exception as e:
        print(f"Failed to initialize learner: {e}")
        return

    tasks = []
    for topic, meta in learner.learning_topics.items():
        sources = meta.get("sources", [])
        for src in sources:
            print(f"Checking {src} for alternatives/contact...")
            tasks.append(check_source(learner, topic, src, timeout=timeout, retries=retries))

    results = []
    # Run sequentially to reduce stress on remote hosts; change to gather for parallelism if desired.
    for t in tasks:
        res = await t
        # Only include if we found anything useful or there was an error
        if res.get("contact") or (res.get("alternatives") and len(res.get("alternatives")) > 0) or res.get("error"):
            results.append(res)

    # Merge with existing file
    existing = []
    if OUTPUT.exists():
        try:
            existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    # Build set of keys to dedup: (topic, source, contact)
    keys = {(e.get("topic"), e.get("source"), e.get("contact")) for e in existing}
    merged = list(existing)
    for e in results:
        key = (e.get("topic"), e.get("source"), e.get("contact"))
        if key not in keys:
            merged.append(e)
            keys.add(key)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Wrote {len(merged)} contact request entries to {OUTPUT}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--relaxed", action="store_true", help="Use more permissive discovery parameters")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds")
    parser.add_argument("--retries", type=int, default=2, help="Number of retries per source")
    args = parser.parse_args()

    # Run the sweep on the event loop
    asyncio.run(sweep_all(timeout=args.timeout, retries=args.retries, relaxed=args.relaxed))


if __name__ == "__main__":
    main()
