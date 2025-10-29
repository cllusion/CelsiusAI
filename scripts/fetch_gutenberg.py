#!/usr/bin/env python3
"""Download public-domain books from Project Gutenberg and ingest them.

Usage:
  python scripts/fetch_gutenberg.py --id 1342 --chunk-size 5000 --ingest

This script only downloads public-domain works available on Project Gutenberg.
Be sure you have the right to ingest any text you download.
"""
from pathlib import Path
import argparse
import requests
import re
import sys
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.learning import conversation_ingest


def try_gutenberg_text_url(book_id: int) -> Optional[str]:
    """Try a few common Gutenberg text URL patterns and return the text if found."""
    patterns = [
        f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt",
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
        f"https://www.gutenberg.org/ebooks/{book_id}.txt.utf-8",
        f"https://www.gutenberg.org/ebooks/{book_id}.txt",
    ]

    headers = {"User-Agent": "CelsiusAI-BookFetcher/1.0 (+https://example.local)"}
    for url in patterns:
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200 and r.text and len(r.text) > 1000:
                return r.text
        except Exception:
            continue
    return None


def strip_gutenberg_header_footer(text: str) -> str:
    """Remove the Project Gutenberg header and footer from the text if present."""
    # Look for the standard START/END markers (case-insensitive)
    start_re = re.compile(r"\*\*\*\s*START OF (THIS|THE) PROJECT GUTENBERG EBOOK.*\*\*\*", re.IGNORECASE)
    end_re = re.compile(r"\*\*\*\s*END OF (THIS|THE) PROJECT GUTENBERG EBOOK.*\*\*\*", re.IGNORECASE)

    start_m = start_re.search(text)
    if start_m:
        text = text[start_m.end() :]

    end_m = end_re.search(text)
    if end_m:
        text = text[: end_m.start()]

    # Trim leading/trailing whitespace
    return text.strip()


def chunk_text(text: str, chunk_size: int = 5000):
    """Yield text chunks of approximately chunk_size characters, breaking at paragraph boundaries when possible."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    cur = []
    cur_len = 0
    for p in paragraphs:
        if cur_len + len(p) + 2 <= chunk_size:
            cur.append(p)
            cur_len += len(p) + 2
        else:
            if cur:
                yield "\n\n".join(cur)
            # If single paragraph is larger than chunk, split it
            if len(p) > chunk_size:
                for i in range(0, len(p), chunk_size):
                    yield p[i : i + chunk_size]
                cur = []
                cur_len = 0
            else:
                cur = [p]
                cur_len = len(p) + 2

    if cur:
        yield "\n\n".join(cur)


def ingest_gutenberg(book_id: int, chunk_size: int = 5000, ingest_chunks: bool = True):
    print(f"Fetching Gutenberg book id={book_id}...")
    txt = try_gutenberg_text_url(book_id)
    if not txt:
        print("Could not download book text from Project Gutenberg. Check the id or network.")
        return

    body = strip_gutenberg_header_footer(txt)
    if not body or len(body) < 200:
        print("Downloaded text appears too short after header stripping; aborting.")
        return

    # Try to detect a title from the first non-empty line
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    title = lines[0] if lines else f"gutenberg-{book_id}"
    source = f"gutenberg:{book_id}"

    print(f"Ingesting '{title[:80]}' (approx {len(body)} chars) in chunks of {chunk_size}...")

    if ingest_chunks:
        count = 0
        for chunk in chunk_text(body, chunk_size=chunk_size):
            meta_source = f"{source}:chunk:{count}"
            res = conversation_ingest.store_conversation(chunk, participants=title, source=meta_source)
            print(f"  chunk {count} -> {res}")
            count += 1
        print(f"Ingested {count} chunks from Gutenberg id={book_id}.")
    else:
        res = conversation_ingest.store_conversation(body, participants=title, source=source)
        print(f"Ingested whole book -> {res}")


def main():
    parser = argparse.ArgumentParser(description="Fetch and ingest public-domain books from Project Gutenberg.")
    parser.add_argument("--id", type=int, help="Project Gutenberg numeric id (e.g. 1342)")
    parser.add_argument("--chunk-size", type=int, default=5000)
    parser.add_argument(
        "--no-chunk", dest="ingest_chunks", action="store_false", help="Ingest whole book as single conversation"
    )
    args = parser.parse_args()

    if not args.id:
        parser.error("Please provide --id for the Gutenberg book id to fetch")

    ingest_gutenberg(args.id, chunk_size=args.chunk_size, ingest_chunks=args.ingest_chunks)


if __name__ == "__main__":
    main()
