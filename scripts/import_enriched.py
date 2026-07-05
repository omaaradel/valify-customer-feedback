#!/usr/bin/env python3
"""
Write enriched.json classifications back into the Feedback Log sheet.

Run from the repo root after enrichment:
    python scripts/import_enriched.py
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import gspread

# Feedback Log column positions (1-indexed)
# A=client_name B=post_url C=source D=post_date E=author F=raw_text
# G=language H=rating I=sentiment J=feedback_type K=product_area L=severity
# M=engagement N=agreement_signal O=claude_summary P=scraped_at Q=valify_scope
_ENRICH_COLS = {
    "sentiment": 9,
    "feedback_type": 10,
    "product_area": 11,
    "severity": 12,
    "agreement_signal": 14,
    "claude_summary": 15,
    "valify_scope": 17,
}


def _col_letter(n: int) -> str:
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def main() -> None:
    with open("enriched.json", encoding="utf-8") as f:
        enriched = json.load(f)

    sa_b64 = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sa_info = json.loads(base64.b64decode(sa_b64))
    gc = gspread.service_account_from_dict(sa_info)

    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    ws = sh.worksheet("Feedback Log")

    updates = []
    for item in enriched:
        row = item["row_number"]
        for field, col in _ENRICH_COLS.items():
            val = item.get(field, "")
            if isinstance(val, bool):
                val = str(val).lower()
            updates.append({"range": f"{_col_letter(col)}{row}", "values": [[val]]})

    if updates:
        ws.batch_update(updates)

    n = len(enriched)
    off_topic = sum(1 for i in enriched if i.get("feedback_type") == "off_topic")
    critical = sum(1 for i in enriched if i.get("severity") == "critical")
    high = sum(1 for i in enriched if i.get("severity") == "high")
    print(f"Enriched {n} rows. {off_topic} off-topic. {critical} critical. {high} high.")


if __name__ == "__main__":
    main()
