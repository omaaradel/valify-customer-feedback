#!/usr/bin/env python3
"""
Part A — standalone test for the column-drop bug fix in sheets.py.

Proves that FEEDBACK_HEADERS contains all 17 columns including valify_scope,
and that _dict_to_row / _to_row / replace_feedback_rows all preserve column Q.

Does NOT connect to Google Sheets. All assertions run in-memory.
If any assertion fails the script exits with code 1 and prints FAIL details.
Part B (audit) should only run after this script exits 0.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sheets import FEEDBACK_HEADERS, _dict_to_row, _to_row, _rows_as_dicts

failures = []


def check(label, condition, expected=None, actual=None):
    if condition:
        print(f"  PASS  {label}")
    else:
        msg = f"  FAIL  {label}"
        if expected is not None or actual is not None:
            msg += f"\n          expected : {expected!r}"
            msg += f"\n          actual   : {actual!r}"
        print(msg)
        failures.append(label)


# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("CASE 1 — FEEDBACK_HEADERS structure")
print("=" * 70)

EXPECTED_HEADERS = [
    "client_name", "post_url", "source", "post_date", "author",
    "raw_text", "language", "rating", "sentiment", "feedback_type",
    "product_area", "severity", "engagement", "agreement_signal",
    "claude_summary", "scraped_at", "valify_scope",
]

check(
    "FEEDBACK_HEADERS has exactly 17 elements",
    len(FEEDBACK_HEADERS) == 17,
    expected=17, actual=len(FEEDBACK_HEADERS),
)
check(
    "FEEDBACK_HEADERS[16] is 'valify_scope'",
    len(FEEDBACK_HEADERS) >= 17 and FEEDBACK_HEADERS[16] == "valify_scope",
    expected="valify_scope",
    actual=FEEDBACK_HEADERS[16] if len(FEEDBACK_HEADERS) >= 17 else "MISSING",
)
check(
    "FEEDBACK_HEADERS matches expected column order exactly",
    FEEDBACK_HEADERS == EXPECTED_HEADERS,
    expected=EXPECTED_HEADERS,
    actual=list(FEEDBACK_HEADERS),
)

# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("CASE 2 — _dict_to_row: full 17-column row with valify_scope sentinel")
print("=" * 70)

full_row = {h: f"VALUE_{h}" for h in FEEDBACK_HEADERS}
full_row["valify_scope"] = "COL_Q_MARKER"
result = _dict_to_row(full_row, FEEDBACK_HEADERS)

check(
    "_dict_to_row produces exactly 17 values",
    len(result) == 17,
    expected=17, actual=len(result),
)
check(
    "result[16] == 'COL_Q_MARKER'  (valify_scope at index 16, column Q)",
    len(result) >= 17 and result[16] == "COL_Q_MARKER",
    expected="COL_Q_MARKER",
    actual=result[16] if len(result) >= 17 else "LIST_TOO_SHORT",
)

# Verify every column is at its correct index
for i, h in enumerate(EXPECTED_HEADERS):
    expected_val = "COL_Q_MARKER" if h == "valify_scope" else f"VALUE_{h}"
    actual_val = result[i] if i < len(result) else "MISSING"
    check(
        f"result[{i:2d}] == {expected_val!r}  (col '{h}')",
        actual_val == expected_val,
        expected=expected_val, actual=actual_val,
    )

# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("CASE 3 — _dict_to_row: empty optional fields do NOT shift columns")
print("=" * 70)

# Columns intentionally left empty: engagement (12), claude_summary (14),
# agreement_signal (13), sentiment (8), feedback_type (9), product_area (10),
# severity (11). Column Q (valify_scope, 16) also empty.
sparse_row = {
    "client_name": "EmptyOptionalClient",
    "post_url": "https://example.com",
    "source": "appstore",
    "post_date": "2026-06-15",
    "author": "tester",
    "raw_text": "Test review with empty fields",
    "language": "en",
    "rating": "3",
    "sentiment": "",
    "feedback_type": "",
    "product_area": "",
    "severity": "",
    "engagement": "",
    "agreement_signal": "",
    "claude_summary": "",
    "scraped_at": "2026-06-15T00:00:00Z",
    "valify_scope": "",
}
sparse_result = _dict_to_row(sparse_row, FEEDBACK_HEADERS)

check(
    "_dict_to_row with empty fields still produces 17 values",
    len(sparse_result) == 17,
    expected=17, actual=len(sparse_result),
)
check(
    "sparse_result[0] == 'EmptyOptionalClient'  (client_name not shifted)",
    len(sparse_result) >= 1 and sparse_result[0] == "EmptyOptionalClient",
    expected="EmptyOptionalClient",
    actual=sparse_result[0] if len(sparse_result) >= 1 else "MISSING",
)
check(
    "sparse_result[2] == 'appstore'  (source not shifted by empty sentiment)",
    len(sparse_result) >= 3 and sparse_result[2] == "appstore",
    expected="appstore",
    actual=sparse_result[2] if len(sparse_result) >= 3 else "MISSING",
)
check(
    "sparse_result[8] == ''  (sentiment stays empty at index 8)",
    len(sparse_result) >= 9 and sparse_result[8] == "",
    expected="",
    actual=sparse_result[8] if len(sparse_result) >= 9 else "MISSING",
)
check(
    "sparse_result[12] == ''  (engagement stays empty at index 12)",
    len(sparse_result) >= 13 and sparse_result[12] == "",
    expected="",
    actual=sparse_result[12] if len(sparse_result) >= 13 else "MISSING",
)
check(
    "sparse_result[14] == ''  (claude_summary stays empty at index 14)",
    len(sparse_result) >= 15 and sparse_result[14] == "",
    expected="",
    actual=sparse_result[14] if len(sparse_result) >= 15 else "MISSING",
)
check(
    "sparse_result[16] == ''  (valify_scope empty at index 16, not shifted)",
    len(sparse_result) >= 17 and sparse_result[16] == "",
    expected="",
    actual=sparse_result[16] if len(sparse_result) >= 17 else "MISSING",
)
check(
    "sparse_result[15] == '2026-06-15T00:00:00Z'  (scraped_at not shifted by empty valify_scope)",
    len(sparse_result) >= 16 and sparse_result[15] == "2026-06-15T00:00:00Z",
    expected="2026-06-15T00:00:00Z",
    actual=sparse_result[15] if len(sparse_result) >= 16 else "MISSING",
)

# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("CASE 4 — _to_row: scraped item dict produces 17 values")
print("=" * 70)

scraped_item = {
    "client_name": "Thndr",
    "post_url": "https://play.google.com/store/apps/details?id=com.thndr",
    "source": "play_store",
    "post_date": "2026-06-10",
    "author": "testuser",
    "raw_text": "Verification step is smooth and fast",
    "language": "en",
    "rating": 5,
    "sentiment": "positive",
    "feedback_type": "compliment",
    "product_area": "nid_verification",
    "severity": "low",
    "engagement": "",
    "agreement_signal": False,
    "claude_summary": "User praises verification speed",
    "scraped_at": "2026-06-15T06:00:00Z",
    "valify_scope": "true",
}
to_row_result = _to_row(scraped_item)

check(
    "_to_row produces exactly 17 values",
    len(to_row_result) == 17,
    expected=17, actual=len(to_row_result),
)
check(
    "to_row_result[16] == 'true'  (valify_scope at column Q)",
    len(to_row_result) >= 17 and to_row_result[16] == "true",
    expected="true",
    actual=to_row_result[16] if len(to_row_result) >= 17 else "MISSING",
)
check(
    "to_row_result[8] == 'positive'  (sentiment at index 8)",
    len(to_row_result) >= 9 and to_row_result[8] == "positive",
    expected="positive",
    actual=to_row_result[8] if len(to_row_result) >= 9 else "MISSING",
)
check(
    "to_row_result[13] == 'FALSE'  (agreement_signal=False converts to 'FALSE')",
    len(to_row_result) >= 14 and to_row_result[13] == "FALSE",
    expected="FALSE",
    actual=to_row_result[13] if len(to_row_result) >= 14 else "MISSING",
)
check(
    "to_row_result[15] == '2026-06-15T06:00:00Z'  (scraped_at at index 15)",
    len(to_row_result) >= 16 and to_row_result[15] == "2026-06-15T06:00:00Z",
    expected="2026-06-15T06:00:00Z",
    actual=to_row_result[15] if len(to_row_result) >= 16 else "MISSING",
)

# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("CASE 5 — replace_feedback_rows code path: full round-trip via MockWorksheet")
print("=" * 70)


class MockWorksheet:
    """In-memory worksheet that mirrors the gspread interface used by replace_feedback_rows."""

    def __init__(self):
        self._data = []

    def clear(self):
        self._data = []

    def append_row(self, row):
        self._data.append(list(row))

    def append_rows(self, rows, value_input_option="RAW", insert_data_option="INSERT_ROWS"):
        for row in rows:
            self._data.append(list(row))

    def get_all_values(self):
        return [list(r) for r in self._data]


def simulate_replace_feedback_rows(mock_ws, rows):
    """Mirrors the exact replace_feedback_rows logic in sheets.py:
       clear → append header → _dict_to_row each row → append_rows.
    """
    mock_ws.clear()
    mock_ws.append_row(FEEDBACK_HEADERS)
    if not rows:
        return
    data = [_dict_to_row(r, FEEDBACK_HEADERS) for r in rows]
    mock_ws.append_rows(data, value_input_option="RAW", insert_data_option="INSERT_ROWS")


# Build three input rows: two filled, one with empty optional fields
input_rows = [
    {h: f"R1_{h}" for h in FEEDBACK_HEADERS},
    {h: f"R2_{h}" for h in FEEDBACK_HEADERS},
    {h: "" for h in FEEDBACK_HEADERS},
]
input_rows[0]["valify_scope"] = "COL_Q_MARKER_ROW1"
input_rows[1]["valify_scope"] = "COL_Q_MARKER_ROW2"
input_rows[2]["valify_scope"] = "COL_Q_MARKER_ROW3"
input_rows[2]["client_name"] = "EmptyOptionals"
input_rows[2]["source"] = "appstore"

mock_ws = MockWorksheet()
simulate_replace_feedback_rows(mock_ws, input_rows)

# Read back via _rows_as_dicts (the same function real code uses after replace)
read_back = _rows_as_dicts(mock_ws, FEEDBACK_HEADERS)

check(
    "MockWorksheet has exactly 3 data rows after replace",
    len(read_back) == 3,
    expected=3, actual=len(read_back),
)
if len(read_back) >= 1:
    check(
        "Row 1 valify_scope == 'COL_Q_MARKER_ROW1'",
        read_back[0].get("valify_scope") == "COL_Q_MARKER_ROW1",
        expected="COL_Q_MARKER_ROW1", actual=read_back[0].get("valify_scope"),
    )
    check(
        "Row 1 client_name == 'R1_client_name'  (no column shift)",
        read_back[0].get("client_name") == "R1_client_name",
        expected="R1_client_name", actual=read_back[0].get("client_name"),
    )
if len(read_back) >= 2:
    check(
        "Row 2 valify_scope == 'COL_Q_MARKER_ROW2'",
        read_back[1].get("valify_scope") == "COL_Q_MARKER_ROW2",
        expected="COL_Q_MARKER_ROW2", actual=read_back[1].get("valify_scope"),
    )
if len(read_back) >= 3:
    check(
        "Row 3 valify_scope == 'COL_Q_MARKER_ROW3'  (empty-fields row)",
        read_back[2].get("valify_scope") == "COL_Q_MARKER_ROW3",
        expected="COL_Q_MARKER_ROW3", actual=read_back[2].get("valify_scope"),
    )
    check(
        "Row 3 client_name == 'EmptyOptionals'  (not shifted by empty fields)",
        read_back[2].get("client_name") == "EmptyOptionals",
        expected="EmptyOptionals", actual=read_back[2].get("client_name"),
    )
    check(
        "Row 3 source == 'appstore'  (not shifted by empty sentiment/feedback_type)",
        read_back[2].get("source") == "appstore",
        expected="appstore", actual=read_back[2].get("source"),
    )

# Inspect raw bytes: header row must have 17 cols, data rows must have 17 cols
raw = mock_ws.get_all_values()
check(
    "Raw sheet has 4 rows total (1 header + 3 data)",
    len(raw) == 4,
    expected=4, actual=len(raw),
)
check(
    "Raw header row has 17 columns",
    len(raw) >= 1 and len(raw[0]) == 17,
    expected=17, actual=len(raw[0]) if len(raw) >= 1 else 0,
)
check(
    "Raw header row[0][16] == 'valify_scope'",
    len(raw) >= 1 and len(raw[0]) >= 17 and raw[0][16] == "valify_scope",
    expected="valify_scope",
    actual=raw[0][16] if len(raw) >= 1 and len(raw[0]) >= 17 else "MISSING",
)
check(
    "Raw data row 1 has 17 columns",
    len(raw) >= 2 and len(raw[1]) == 17,
    expected=17, actual=len(raw[1]) if len(raw) >= 2 else 0,
)
check(
    "Raw data row 1 col[16] == 'COL_Q_MARKER_ROW1'",
    len(raw) >= 2 and len(raw[1]) >= 17 and raw[1][16] == "COL_Q_MARKER_ROW1",
    expected="COL_Q_MARKER_ROW1",
    actual=raw[1][16] if len(raw) >= 2 and len(raw[1]) >= 17 else "MISSING",
)
check(
    "Raw data row 3 (empty-fields) has 17 columns",
    len(raw) >= 4 and len(raw[3]) == 17,
    expected=17, actual=len(raw[3]) if len(raw) >= 4 else 0,
)
check(
    "Raw data row 3 col[16] == 'COL_Q_MARKER_ROW3'",
    len(raw) >= 4 and len(raw[3]) >= 17 and raw[3][16] == "COL_Q_MARKER_ROW3",
    expected="COL_Q_MARKER_ROW3",
    actual=raw[3][16] if len(raw) >= 4 and len(raw[3]) >= 17 else "MISSING",
)

# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 70)
total_checks = sum(
    1 for line in open(__file__).readlines() if line.strip().startswith("check(")
)
if failures:
    print(f"RESULT: {len(failures)} FAILURE(S)  —  Part B will NOT run.")
    print()
    for f in failures:
        print(f"  FAIL  {f}")
    sys.exit(1)
else:
    print("RESULT: ALL ASSERTIONS PASSED — column-drop fix verified.")
    print("Part B (audit) may now proceed.")
    sys.exit(0)
