#!/usr/bin/env python3
"""
Part B — read-only audit of current sheet state.
Writes a summary to validation/audit_pre_recovery.md.

No writes to Feedback Log. No Gemini/enrichment calls.
"""
import base64
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import gspread

from sheets import FEEDBACK_HEADERS

# ── Connect ───────────────────────────────────────────────────────────────────

sa_info = json.loads(base64.b64decode(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]))
gc = gspread.service_account_from_dict(sa_info)
sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])

# ── Feedback Log ──────────────────────────────────────────────────────────────

ws_fl = sh.worksheet("Feedback Log")
fl_all = ws_fl.get_all_values()

sheet_header = fl_all[0] if fl_all else []
data_rows = fl_all[1:] if len(fl_all) > 1 else []

def col(name):
    try:
        return sheet_header.index(name)
    except ValueError:
        return None

c_source        = col("source")
c_sentiment     = col("sentiment")
c_feedback_type = col("feedback_type")
c_product_area  = col("product_area")
c_severity      = col("severity")
c_scope         = col("valify_scope")
c_client        = col("client_name")

def get(row, idx):
    if idx is None or idx >= len(row):
        return ""
    return row[idx].strip()

# ── Collect per-row data ───────────────────────────────────────────────────────

total_rows = len(data_rows)
source_counts = Counter()
scope_by_source = defaultdict(Counter)    # source -> scope_value -> count
sentiment_by_source = defaultdict(Counter)
parse_error_rows = []   # rows where any enrichment field == "parse_error"
client_by_source = defaultdict(Counter)

ENRICH_COLS = [c_sentiment, c_feedback_type, c_product_area, c_severity]

for r in data_rows:
    src  = get(r, c_source)
    scop = get(r, c_scope)
    sent = get(r, c_sentiment)

    source_counts[src] += 1
    scope_by_source[src][scop if scop else "(empty)"] += 1
    sentiment_by_source[src][sent if sent else "(empty)"] += 1
    client_by_source[src][get(r, c_client)] += 1

    # Mark as parse_error if any enrichment field contains "parse_error"
    is_pe = any(get(r, c) == "parse_error" for c in ENRICH_COLS if c is not None)
    if is_pe:
        parse_error_rows.append(r)

# ── Play Store on-topic (valify_scope == "true") ──────────────────────────────

ps_on_topic = [
    r for r in data_rows
    if get(r, c_source) == "play_store" and get(r, c_scope) == "true"
]
ps_scope_state = Counter(get(r, c_scope) if get(r, c_scope) else "(empty)"
                         for r in data_rows if get(r, c_source) == "play_store")

# ── Legacy mixed-sentiment rows ───────────────────────────────────────────────
# "mixed" is a non-canonical sentiment value from before the taxonomy was locked.
# Also catch comma-joined variants like "positive,negative" or "positive, negative".
CANONICAL_SENTIMENTS = {"positive", "negative", "neutral", "mixed", "parse_error", "(empty)", ""}

def is_legacy_mixed(sent_value):
    """True if sentiment looks like the old compound/mixed format."""
    v = sent_value.lower().strip()
    return (
        "," in v
        or "/" in v
        or v == "mixed"
        or ("positive" in v and "negative" in v)
    )

legacy_mixed = [
    r for r in data_rows
    if is_legacy_mixed(get(r, c_sentiment))
]
legacy_by_source = Counter(get(r, c_source) for r in legacy_mixed)

# ── Quarantine tab ────────────────────────────────────────────────────────────

tabs = {ws.title for ws in sh.worksheets()}
quarantine_rows = 0
quarantine_source_counts = Counter()
if "Quarantine" in tabs:
    ws_q = sh.worksheet("Quarantine")
    q_all = ws_q.get_all_values()
    if len(q_all) > 1:
        q_header = q_all[0]
        q_data   = q_all[1:]
        quarantine_rows = len(q_data)
        try:
            q_src_col = q_header.index("source")
            for row in q_data:
                s = row[q_src_col].strip() if q_src_col < len(row) else ""
                quarantine_source_counts[s] += 1
        except ValueError:
            pass

# ── Header sanity ─────────────────────────────────────────────────────────────

header_cols     = len(sheet_header)
col_q_value     = sheet_header[16] if header_cols >= 17 else "MISSING"
header_matches  = sheet_header == FEEDBACK_HEADERS

# ── Parse error by source ─────────────────────────────────────────────────────

pe_by_source = Counter(get(r, c_source) for r in parse_error_rows)

# ── Build report ──────────────────────────────────────────────────────────────

now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

lines = []
def L(s=""):
    lines.append(s)

L("# Pre-Recovery Audit — Feedback Log")
L()
L(f"**Generated:** {now_utc}  ")
L(f"**Session:** Part B, no enrichment calls, no sheet writes.")
L()

L("---")
L()
L("## 1. Sheet Header Sanity")
L()
L(f"| Field | Value |")
L(f"|-------|-------|")
L(f"| Header column count | {header_cols} |")
L(f"| Column Q (index 16) | `{col_q_value}` |")
L(f"| Header matches FEEDBACK_HEADERS | {'YES' if header_matches else 'NO — MISMATCH'} |")
L()

if not header_matches:
    L("> **WARNING:** Sheet header does not match FEEDBACK_HEADERS.")
    L(f"> Sheet: {sheet_header}")
    L(f"> Expected: {FEEDBACK_HEADERS}")
    L()

L("---")
L()
L("## 2. Overall Feedback Log Totals")
L()
L(f"**Total data rows:** {total_rows}")
L()
L("### Per-source breakdown")
L()
L("| Source | Rows |")
L("|--------|------|")
for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
    L(f"| `{src}` | {cnt} |")
L()

L("---")
L()
L("## 3. valify_scope State by Source")
L()
for src in sorted(scope_by_source):
    L(f"### `{src}` ({source_counts[src]} rows)")
    L()
    L("| valify_scope | Count |")
    L("|-------------|-------|")
    sc = scope_by_source[src]
    for val in ["true", "false", "unsure", "parse_error", "(empty)"]:
        if sc[val]:
            L(f"| `{val}` | {sc[val]} |")
    # Catch any unexpected values
    for val, cnt in sc.items():
        if val not in ["true", "false", "unsure", "parse_error", "(empty)"]:
            L(f"| `{val}` (unexpected) | {cnt} |")
    L()

L("---")
L()
L("## 4. parse_error Rows")
L()
L(f"**Total parse_error rows:** {len(parse_error_rows)}  ")
L("(A row is counted if any of sentiment / feedback_type / product_area / severity equals `parse_error`)")
L()
L("| Source | parse_error rows |")
L("|--------|-----------------|")
for src, cnt in sorted(pe_by_source.items(), key=lambda x: -x[1]):
    L(f"| `{src}` | {cnt} |")
expected_appstore_pe = 33
actual_appstore_pe = pe_by_source.get("appstore", 0)
L()
if actual_appstore_pe == expected_appstore_pe:
    L(f"> **CONFIRMED:** appstore parse_error count = {actual_appstore_pe} (expected {expected_appstore_pe}).")
else:
    L(f"> **NOTE:** appstore parse_error count = {actual_appstore_pe} (expected {expected_appstore_pe}).")
L()

L("---")
L()
L("## 5. Play Store On-Topic Rows (valify_scope = true)")
L()
L(f"**Count:** {len(ps_on_topic)}")
L()
L("### play_store valify_scope distribution")
L()
L("| valify_scope | Count |")
L("|-------------|-------|")
for val in ["true", "false", "unsure", "parse_error", "(empty)"]:
    if ps_scope_state[val]:
        L(f"| `{val}` | {ps_scope_state[val]} |")
for val, cnt in ps_scope_state.items():
    if val not in ["true", "false", "unsure", "parse_error", "(empty)"]:
        L(f"| `{val}` (unexpected) | {cnt} |")
L()
L("> All play_store valify_scope values were wiped to blank during the Phase 8c")
L("> column-drop bug. Re-enrichment of valify_scope is queued for the next Gemini session.")
L()

L("---")
L()
L("## 6. Sentiment Distribution by Source")
L()
for src in sorted(sentiment_by_source):
    L(f"### `{src}`")
    L()
    L("| Sentiment | Count |")
    L("|-----------|-------|")
    for val, cnt in sorted(sentiment_by_source[src].items(), key=lambda x: -x[1]):
        L(f"| `{val}` | {cnt} |")
    L()

L("---")
L()
L("## 7. Legacy Mixed-Sentiment Rows")
L()
L(f"**Total rows flagged as legacy mixed-sentiment:** {len(legacy_mixed)}")
L()
if legacy_mixed:
    L("| Source | Count |")
    L("|--------|-------|")
    for src, cnt in sorted(legacy_by_source.items(), key=lambda x: -x[1]):
        L(f"| `{src}` | {cnt} |")
    L()
    L("Sample sentiment values found:")
    L()
    sample_vals = sorted(set(get(r, c_sentiment) for r in legacy_mixed))[:10]
    for v in sample_vals:
        L(f"- `{v}`")
else:
    L("No legacy mixed-sentiment rows found.")
L()

L("---")
L()
L("## 8. Quarantine Tab")
L()
L(f"**Quarantine row count:** {quarantine_rows}")
if quarantine_source_counts:
    L()
    L("| Source | Count |")
    L("|--------|-------|")
    for src, cnt in sorted(quarantine_source_counts.items(), key=lambda x: -x[1]):
        L(f"| `{src}` | {cnt} |")
L()

L("---")
L()
L("## 9. Summary Checklist")
L()

items = [
    ("Header has 17 columns with valify_scope at Q",
     header_cols == 17 and col_q_value == "valify_scope"),
    ("Total rows within expected range (3300–3400)",
     3300 <= total_rows <= 3400),
    ("appstore row count == 93",
     source_counts.get("appstore", 0) == 93),
    (f"appstore parse_error == {expected_appstore_pe}",
     actual_appstore_pe == expected_appstore_pe),
    ("Quarantine tab has 73 rows",
     quarantine_rows == 73),
    ("All play_store valify_scope values are empty (post-bug state)",
     ps_scope_state.get("(empty)", 0) == source_counts.get("play_store", -1)),
]
for label, ok in items:
    L(f"- [{'x' if ok else ' '}] {label}")
L()

report_text = "\n".join(lines)

# Print to stdout
print(report_text)

# Write to validation/audit_pre_recovery.md
out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "validation")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "audit_pre_recovery.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report_text)

print(f"\n[audit] Report written to {out_path}")
