#!/usr/bin/env python3
"""List and export authorization records from data/authorizations.db

Usage:
  python scripts/list_authorizations.py --list [--limit N]
  python scripts/list_authorizations.py --export ID --dest /path/to/out

This is a lightweight admin helper to inspect authorization uploads.
"""
import argparse
import sys
from pathlib import Path

try:
    from src.admin.authorization_manager import list_authorizations, get_authorization, export_authorization
except Exception as e:
    print(f"Failed to import authorization manager: {e}")
    sys.exit(2)


def cmd_list(limit: int = 100):
    rows = list_authorizations(limit)
    if not rows:
        print("No authorizations found.")
        return
    print(f"Showing up to {limit} authorizations:\n")
    for r in rows:
        print(
            f"ID: {r['id']}  Uploaded: {r['timestamp']}  Uploader: {r.get('uploader','')}  File: {r.get('filename','')}  Status: {r.get('status','')}"
        )


def cmd_export(aid: int, dest: str):
    res = export_authorization(aid, dest)
    if res.get("status") == "ok":
        print(f"Exported authorization {aid} to {res.get('path')}")
    else:
        print(f"Export failed: {res.get('error')}")


def main():
    p = argparse.ArgumentParser(description="List or export stored authorization files")
    p.add_argument("--list", action="store_true", help="List authorizations")
    p.add_argument("--limit", type=int, default=100, help="List limit")
    p.add_argument("--export", type=int, help="Authorization ID to export")
    p.add_argument("--dest", type=str, help="Destination path for export")
    args = p.parse_args()

    if args.list:
        cmd_list(args.limit)
        return

    if args.export:
        if not args.dest:
            print("Please provide --dest when using --export")
            sys.exit(2)
        cmd_export(args.export, args.dest)
        return

    p.print_help()


if __name__ == "__main__":
    main()
