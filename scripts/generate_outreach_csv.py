#!/usr/bin/env python3
"""
Generate a CSV of contacts with a draft outreach subject and body for admin review.
Writes to data/outreach_drafts.csv by default.

Usage:
    python scripts/generate_outreach_csv.py [--out PATH]
"""
import json
import csv
import argparse
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_OUT = Path("data") / "outreach_drafts.csv"
TEMPLATE_SUBJECT = "Request: Permission to use content from {domain} for educational, non-commercial training"
TEMPLATE_BODY = (
    "Hello {contact_name},\n\n"
    "I'm writing on behalf of the Celsius AI project to request permission to use publicly available content from {domain} for educational, non-commercial model training. \n\n"
    "We will only ingest content after explicit admin review and the data will be stored securely for internal research. If you prefer we limit to particular sections or provide attribution, please let us know.\n\n"
    "Proposed use: internal, non-commercial training and research\n"
    "If you have a preferred contact or policy for such requests, please reply and we'll follow it.\n\n"
    "Thanks for your time,\n"
    "Celsius AI - Admin Team\n"
)


def make_contact_name(email_or_text: str) -> str:
    # Try to extract a readable name from an email or text if possible
    if not email_or_text:
        return ""
    if "@" in email_or_text:
        return email_or_text.split("@")[0].replace(".", " ").replace("_", " ").title()
    # fallback: strip and truncate
    return email_or_text.strip()[:40]


def generate(out_path: Path):
    contacts_file = Path("data") / "web_learning_contact_requests.json"
    if not contacts_file.exists():
        print(f"Contact requests file not found: {contacts_file}")
        return 1

    try:
        items = json.loads(contacts_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to read JSON: {e}")
        return 1

    rows = []
    for it in items:
        contact = it.get("contact")
        if not contact:
            continue
        domain = it.get("source")
        topic = it.get("topic", "")
        checked_at = it.get("checked_at", "")
        contact_name = make_contact_name(contact)
        # Extract a readable host/domain from the source. The incoming
        # `domain` value may be a URL, a plain hostname, or a filesystem
        # path. Use urlparse to safely extract the netloc when present,
        # otherwise fall back to the path or the original string.
        def _extract_host(val):
            if not val:
                return ""
            try:
                s = str(val)
                p = urlparse(s)
                host = p.netloc or p.path
                # Remove any userinfo if present (user:pass@host)
                if "@" in host:
                    host = host.split("@")[-1]
                return host
            except Exception:
                return str(val)

        host = _extract_host(domain)
        subject = TEMPLATE_SUBJECT.format(domain=host if host else domain)
        body = TEMPLATE_BODY.format(contact_name=contact_name, domain=domain)
        rows.append(
            {
                "topic": topic,
                "source": domain,
                "contact": contact,
                "contact_name": contact_name,
                "subject": subject,
                "body": body,
                "checked_at": checked_at,
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["topic", "source", "contact", "contact_name", "subject", "body", "checked_at"]
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote {len(rows)} outreach drafts to {out_path}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", "-o", help="Output CSV path", default=str(DEFAULT_OUT))
    args = p.parse_args()
    exit(generate(Path(args.out)))
