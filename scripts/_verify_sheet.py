#!/usr/bin/env python3
"""Final verification: sheet totals, source breakdown, quarantine tab."""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import gspread

sa_info = json.loads(base64.b64decode(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]))
gc = gspread.service_account_from_dict(sa_info)
sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])

ws_fl = sh.worksheet("Feedback Log")
fl_rows = ws_fl.get_all_values()
header = fl_rows[0]
data_rows = fl_rows[1:]

print(f"Feedback Log header columns: {len(header)}")
col_q = header[16] if len(header) >= 17 else "MISSING"
print(f"Column Q: {col_q}")
print(f"Feedback Log data rows: {len(data_rows)}")

col_source = header.index("source")
col_sentiment = header.index("sentiment")

sources = {}
for r in data_rows:
    s = r[col_source] if len(r) > col_source else ""
    sources[s] = sources.get(s, 0) + 1

print("Source breakdown:")
for k, v in sorted(sources.items()):
    print(f"  {repr(k)}: {v}")

appstore = [r for r in data_rows if len(r) > col_source and r[col_source] == "appstore"]
sentiment_counts = {}
for r in appstore:
    s = r[col_sentiment] if len(r) > col_sentiment else ""
    sentiment_counts[s] = sentiment_counts.get(s, 0) + 1
print(f"Appstore row sentiment breakdown ({len(appstore)} rows):")
for k, v in sorted(sentiment_counts.items()):
    print(f"  {repr(k)}: {v}")

tabs = [ws.title for ws in sh.worksheets()]
print(f"Tabs in spreadsheet: {tabs}")

if "Quarantine" in tabs:
    ws_q = sh.worksheet("Quarantine")
    q_rows = ws_q.get_all_values()
    print(f"Quarantine data rows: {len(q_rows) - 1}")
    if len(q_rows) > 0:
        q_header = q_rows[0]
        print(f"Quarantine header columns: {len(q_header)}, last column: {q_header[-1] if q_header else 'empty'}")
    if len(q_rows) > 1:
        q_source_col = q_header.index("source") if "source" in q_header else None
        if q_source_col is not None:
            q_sources = {}
            for r in q_rows[1:]:
                s = r[q_source_col] if len(r) > q_source_col else ""
                q_sources[s] = q_sources.get(s, 0) + 1
            print(f"Quarantine source breakdown: {q_sources}")
else:
    print("Quarantine tab not found.")
