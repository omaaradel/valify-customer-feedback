#!/usr/bin/env python3
"""
Export unenriched Feedback Log rows to pending.json.

Run from the repo root:
    python scripts/export_pending.py
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import gspread


def main() -> None:
    sa_b64 = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sa_info = json.loads(base64.b64decode(sa_b64))
    gc = gspread.service_account_from_dict(sa_info)

    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    ws = sh.worksheet("Feedback Log")

    all_values = ws.get_all_values()
    if len(all_values) < 2:
        print("Feedback Log is empty or header-only.")
        return

    header = all_values[0]
    pending = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        row = row + [""] * (len(header) - len(row))
        row_dict = dict(zip(header, row))
        if not row_dict.get("sentiment"):
            pending.append({
                "row_number": row_idx,
                "client_name": row_dict.get("client_name", ""),
                "source": row_dict.get("source", ""),
                "post_date": row_dict.get("post_date", ""),
                "raw_text": row_dict.get("raw_text", ""),
                "rating": row_dict.get("rating", ""),
                "language": row_dict.get("language", ""),
            })

    with open("pending.json", "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(pending)} unenriched rows to pending.json")


if __name__ == "__main__":
    main()
