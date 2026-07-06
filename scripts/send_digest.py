#!/usr/bin/env python3
"""
Weekly plain-text email digest via Gmail SMTP, Mondays only.

Run from the repo root:
    python scripts/send_digest.py
    python scripts/send_digest.py --dry-run

Also importable as send_digest(dry_run=False), called by main.py's run_digest()
and the Phase 9 GitHub Actions daily pipeline (which invokes this every day;
the Monday check below decides whether it actually sends).

Reads data/feedback.json (the output of export_json.py), not the Sheet directly.
"""
import argparse
import json
import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FEEDBACK_JSON = os.path.join(_PROJECT_ROOT, "data", "feedback.json")

_RECIPIENT = "omar.farghaly@valify.me"
_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587
_WINDOW_DAYS = 7
_SUMMARY_TRUNCATE = 200

_DATE_FORMATS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def _parse_post_date(value):
    """Parse a post_date string to a date. Returns None if blank or unparseable,
    never raises."""
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    candidates = [value]
    if len(value) >= 10:
        candidates.append(value[:10])
    for candidate in candidates:
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
    return None


def _load_feedback():
    if not os.path.exists(_FEEDBACK_JSON):
        return None
    with open(_FEEDBACK_JSON, encoding="utf-8") as f:
        return json.load(f)


def _build_digest(feedback: dict, today) -> tuple:
    """Returns (subject, body) for the digest covering the past _WINDOW_DAYS
    days ending today (inclusive)."""
    start_date = today - timedelta(days=_WINDOW_DAYS - 1)
    end_date = today

    sections = []
    for client_name, bucket in feedback.get("clients", {}).items():
        in_window = []
        for review in bucket.get("reviews", []):
            post_date = _parse_post_date(review.get("post_date", ""))
            if post_date is None or not (start_date <= post_date <= end_date):
                continue
            in_window.append(review)
        if not in_window:
            continue

        lines = [f"{client_name}: {len(in_window)} on-topic review(s) this week."]
        for review in in_window:
            summary = (review.get("claude_summary") or "").strip()
            if not summary:
                summary = (review.get("raw_text") or "")[:_SUMMARY_TRUNCATE]
            lines.append(f"  - {summary}")
        sections.append("\n".join(lines))

    body = "\n\n".join(sections) if sections else "No on-topic reviews in the past 7 days."
    subject = f"Valify Feedback Digest: {start_date.isoformat()} to {end_date.isoformat()}"
    return subject, body


def _send_email(subject: str, body: str) -> None:
    sender = os.environ["GMAIL_SENDER"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = _RECIPIENT

    with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, [_RECIPIENT], msg.as_string())


def send_digest(dry_run: bool = False) -> bool:
    """Build and send (or print) the weekly digest. Returns True only if an
    email was actually sent. Returns False, and prints why, for: not Monday
    (unless dry_run), data/feedback.json missing, or an SMTP send failure.
    Never raises: all failures are caught, printed, and returned as False.
    """
    today = datetime.now(timezone.utc).date()

    if today.weekday() != 0 and not dry_run:
        print("Not Monday, skipping digest.")
        return False

    feedback = _load_feedback()
    if feedback is None:
        print("data/feedback.json not found. Run export_json.py first.")
        return False

    subject, body = _build_digest(feedback, today)

    if dry_run:
        print(f"Subject: {subject}")
        print()
        print(body)
        return False

    try:
        _send_email(subject, body)
    except Exception as exc:
        print(f"SMTP send failed: {exc}")
        return False

    print(f"Digest sent to {_RECIPIENT}.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send the weekly Valify feedback digest via Gmail SMTP.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the email (subject and body) instead of sending it.",
    )
    args = parser.parse_args()

    # Cheap pre-checks, duplicated from send_digest, only to pick the right
    # process exit code. send_digest itself is fully self-contained and
    # correct when called directly (e.g. from main.py's run_digest).
    if not os.path.exists(_FEEDBACK_JSON):
        print("data/feedback.json not found. Run export_json.py first.")
        sys.exit(1)

    not_monday = datetime.now(timezone.utc).date().weekday() != 0

    sent = send_digest(dry_run=args.dry_run)

    if args.dry_run or not_monday:
        sys.exit(0)
    sys.exit(0 if sent else 1)


if __name__ == "__main__":
    main()
