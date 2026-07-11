#!/usr/bin/env python3
"""
Export the Feedback Log sheet to data/feedback.json, structured by client.

Run from the repo root:
    python scripts/export_json.py

Also importable as export_feedback_json(), called by main.py's run_export_json()
and by the Phase 9 GitHub Actions daily pipeline.
"""
import base64
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import gspread

from config import CLIENTS

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
_OUTPUT_PATH = os.path.join(_DATA_DIR, "feedback.json")

_REVIEW_FIELDS = [
    "source", "post_date", "language", "raw_text", "sentiment",
    "feedback_type", "product_area", "severity", "claude_summary", "valify_scope",
]


def _open_sheet():
    sa_b64 = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sa_info = json.loads(base64.b64decode(sa_b64))
    gc = gspread.service_account_from_dict(sa_info)
    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    return sh.worksheet("Feedback Log")


def export_feedback_json() -> str:
    """Export the Feedback Log to data/feedback.json, structured by client.
    Off-topic rows are excluded from each client's reviews array but counted
    in total and off_topic. Rows where valify_scope is "false" (or blank) are
    excluded entirely: not in reviews, not in on_topic, and not in total
    either, so out-of-scope feedback has zero footprint anywhere in the
    export. They still exist in the Sheet, they are just never written here.
    Per client, total always equals on_topic plus off_topic exactly.
    Returns the output file path."""
    ws = _open_sheet()
    all_values = ws.get_all_values()
    header = all_values[0] if all_values else []
    data_rows = all_values[1:] if len(all_values) > 1 else []

    def ci(name):
        return header.index(name) if name in header else None

    col = {name: ci(name) for name in (["client_name"] + _REVIEW_FIELDS)}

    def get(row, name):
        idx = col.get(name)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    display_names = [c.display_name for c in CLIENTS.values()]
    clients = {
        name: {"total": 0, "on_topic": 0, "off_topic": 0, "reviews": []}
        for name in display_names
    }

    unmatched = 0
    for row in data_rows:
        client_name = get(row, "client_name")
        bucket = clients.get(client_name)
        if bucket is None:
            # Blank or unrecognized client_name: not one of the 8 configured clients.
            unmatched += 1
            continue
        feedback_type = get(row, "feedback_type")
        if feedback_type != "off_topic":
            # valify_scope "false" (out of scope) rows are on-topic
            # feedback_type but not relevant to a Valify KYC flow: excluded
            # from the export entirely, they do not even count toward total.
            valify_scope = get(row, "valify_scope")
            if valify_scope not in ("true", "unsure"):
                continue

        bucket["total"] += 1
        if feedback_type == "off_topic":
            bucket["off_topic"] += 1
            continue
        bucket["on_topic"] += 1
        bucket["reviews"].append({field: get(row, field) for field in _REVIEW_FIELDS})

    for bucket in clients.values():
        bucket["reviews"].sort(key=lambda r: r.get("post_date", ""), reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_rows": len(data_rows),
        "clients": clients,
    }

    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    on_topic_total = sum(b["on_topic"] for b in clients.values())
    if unmatched:
        print(f"NOTE: {unmatched} rows had a client_name not in config.py, excluded from client buckets.")
    print(f"Exported {len(clients)} clients, {on_topic_total} on-topic reviews to data/feedback.json")
    return _OUTPUT_PATH


def main() -> None:
    export_feedback_json()


if __name__ == "__main__":
    main()
