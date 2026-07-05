#!/usr/bin/env python3
"""
Dump all Google Sheet tabs to CSV files in /backups/.

Run from the repo root:
    python scripts/backup_to_git.py

Overwrites same-day files safely. Does not commit to git (that is Phase 9).
Each tab becomes: backups/{Tab_Name}_{YYYY-MM-DD}.csv
"""
import base64
import csv
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import gspread

BACKUPS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backups",
)


def main() -> None:
    sa_b64 = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sa_info = json.loads(base64.b64decode(sa_b64))
    gc = gspread.service_account_from_dict(sa_info)
    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])

    os.makedirs(BACKUPS_DIR, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for ws in sh.worksheets():
        # Safe filename: replace spaces and slashes
        tab_safe = ws.title.replace(" ", "_").replace("/", "_")
        filename = f"{tab_safe}_{date_str}.csv"
        filepath = os.path.join(BACKUPS_DIR, filename)

        data = ws.get_all_values()
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        print(f"Wrote {len(data):>6} rows  ->  backups/{filename}")

    print(f"Backup complete. {len(sh.worksheets())} tabs written to backups/")


if __name__ == "__main__":
    main()
