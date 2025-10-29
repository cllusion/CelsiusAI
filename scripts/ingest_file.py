#!/usr/bin/env python3
"""CLI to ingest a local file (TXT/EPUB/PDF) into the Celsius ingestion pipeline.

Usage:
    python scripts/ingest_file.py /path/to/file --source manual --author "Admin"

Behavior:
- Extracts text using `src.utils.text_extract.extract_text` (safe optional deps)
- Chunks the text into ~1000-character segments and writes them to
  `data/pending_ingest/<filename>_chunks.json` with metadata for admin review.
- Optionally calls `conversation_ingest.store_conversation()` if `--auto-commit` is set.

This script is intentionally conservative: by default it writes chunks for
admin review instead of auto-committing into the learning DB.
"""
from pathlib import Path
import argparse
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger("ingest_file")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from src.utils.text_extract import extract_text


def chunk_text(text: str, max_chars: int = 1000):
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        # try to break at newline or sentence boundary
        seg = text[start:end]
        if end < n:
            # extend to next newline or space up to +200 chars
            extra_end = min(n, end + 200)
            snippet = text[end:extra_end]
            # find first newline
            nl = snippet.find("\n")
            if nl != -1:
                end += nl
            else:
                sp = snippet.find(" ")
                if sp != -1:
                    end += sp
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]


def write_pending_chunks(dest_dir: Path, base_name: str, chunks, metadata):
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "source_file": base_name,
        "chunks_count": len(chunks),
        "metadata": metadata,
        "chunks": chunks,
    }
    out_path = dest_dir / (base_name + "_chunks.json")
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    return out_path


def try_auto_commit(chunks, metadata, source, author):
    # Attempt to import the ingestion entrypoint if available
    # prefer the package under src.learning
    try:
        from src.learning.conversation_ingest import store_conversation
    except Exception:
        try:
            from conversation_ingest import store_conversation
        except Exception:
            try:
                from src.conversation_ingest import store_conversation
            except Exception:
                logger.warning("No ingestion entrypoint available; skipping auto-commit.")
                return False

    # prepare a simple conversation payload per chunk
    success = True
    for i, c in enumerate(chunks):
        payload = {
            "text": c,
            "source": source,
            "author": author,
            "chunk_index": i,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        try:
            store_conversation(payload)
        except Exception:
            logger.exception("Failed to store chunk %s", i)
            success = False
    return success


def main():
    p = argparse.ArgumentParser(description="Ingest a local file for admin review or auto-commit")
    p.add_argument("file", help="Path to the input file")
    p.add_argument("--source", default="manual", help="Source label for metadata")
    p.add_argument("--author", default="unknown", help="Author/uploader name")
    p.add_argument("--auto-commit", action="store_true", help="Attempt to auto-commit to ingestion pipeline")
    p.add_argument("--chunk-size", type=int, default=1000, help="Maximum characters per chunk")
    args = p.parse_args()

    path = Path(args.file)
    if not path.exists():
        logger.error("File not found: %s", path)
        raise SystemExit(2)

    text, meta = extract_text(str(path))
    if not text:
        logger.warning("No text extracted; metadata=%s", meta)

    chunks = []
    if text:
        chunks = chunk_text(text, max_chars=args.chunk_size)

    dest = Path("data") / "pending_ingest"
    base = path.stem
    out_path = write_pending_chunks(dest, base, chunks, meta)
    logger.info("Wrote %d chunks to %s", len(chunks), out_path)

    if args.auto_commit:
        ok = try_auto_commit(chunks, meta, args.source, args.author)
        if ok:
            logger.info("Auto-commit succeeded (best-effort)")
        else:
            logger.warning("Auto-commit failed or skipped; chunks remain in %s", out_path)


if __name__ == "__main__":
    main()
