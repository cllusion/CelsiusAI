#!/usr/bin/env python3
"""
Check the Wayback Machine for archived snapshots of configured web learning sources.
Writes results to data/web_learning_wayback_alternatives.json
"""
import json
from pathlib import Path
from urllib.parse import urlparse, quote
import urllib.request

from src.learning.celsius_web_learner import CelsiusWebLearner

OUT = Path("data") / "web_learning_wayback_alternatives.json"


def query_wayback(domain, limit=3):
    # Query Wayback CDX API for snapshots
    q = quote(f"{domain}/*", safe="")
    url = f"https://web.archive.org/cdx/search/cdx?url={q}&output=json&fl=original,timestamp&filter=statuscode:200&limit={limit}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read()
            arr = json.loads(data)
            # arr[0] is header
            if len(arr) <= 1:
                return []
            results = []
            for row in arr[1:]:
                orig, ts = row[0], row[1]
                archived = f"https://web.archive.org/web/{ts}/{orig}"
                results.append({"original": orig, "timestamp": ts, "archived": archived})
            return results
    except Exception as e:
        return []


def main():
    db_path = Path(__file__).resolve().parents[2] / "data" / "web_learning.db"
    learner = CelsiusWebLearner(db_path)
    topics = learner._get_learning_topics()
    out = []
    for topic, meta in topics.items():
        for src in meta.get("sources", []):
            parsed = urlparse(src)
            # Use only the netloc (domain) for Wayback queries
            domain = parsed.netloc
            print(f"Querying Wayback for {domain} ...")
            snaps = query_wayback(domain, limit=5)
            if snaps:
                out.append({"topic": topic, "source": src, "snapshots": snaps})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {len(out)} domains with Wayback snapshots to {OUT}")


if __name__ == "__main__":
    main()
