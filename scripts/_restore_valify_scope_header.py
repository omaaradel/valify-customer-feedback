#!/usr/bin/env python3
"""One-time: restore valify_scope header to column Q after replace_feedback_rows wiped it."""
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
ws = sh.worksheet("Feedback Log")

headers = ws.row_values(1)
print(f"Current header has {len(headers)} columns. Last 3: {headers[-3:]}")

if len(headers) < 17 or headers[16] != "valify_scope":
    ws.update("Q1", [["valify_scope"]])
    print("Added valify_scope header to column Q.")
else:
    print("valify_scope header already present at column Q.")

headers = ws.row_values(1)
col_q = headers[16] if len(headers) >= 17 else "MISSING"
print(f"Header now has {len(headers)} columns. Column Q: {col_q}")
