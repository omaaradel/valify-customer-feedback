"""
Google Sheets client — wraps gspread for three tabs:
  Feedback Log  append-only feedback rows
  Admin         one row per client, updated each run
  seen_hashes   SHA-256 hashes for deduplication
"""
import base64
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import gspread

from config import ClientConfig

log = logging.getLogger(__name__)

FEEDBACK_HEADERS = [
    "client_name", "post_url", "source", "post_date", "author",
    "raw_text", "language", "rating", "sentiment", "feedback_type",
    "product_area", "severity", "engagement", "agreement_signal",
    "claude_summary", "scraped_at", "valify_scope",
]

ADMIN_HEADERS = [
    "client_name", "playstore_url", "appstore_url",
    "active_keywords_en", "active_keywords_ar", "dead_keywords",
    "last_run_status", "last_run_at",
]

_WRITE_BATCH = 100   # rows per append_rows call
_WRITE_SLEEP = 1.0   # seconds between batches to stay under quota


class SheetsClient:
    def __init__(self) -> None:
        self._gc = _make_client()
        self.spreadsheet = self._gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
        self._ensure_tabs()

    # ── Setup ────────────────────────────────────────────────────────────────

    def _ensure_tabs(self) -> None:
        existing = {ws.title for ws in self.spreadsheet.worksheets()}
        for title in ("Feedback Log", "Admin", "seen_hashes", "Archive"):
            if title not in existing:
                self.spreadsheet.add_worksheet(title=title, rows=10000, cols=20)
                log.info("Created sheet tab: %s", title)

        fb_ws = self.spreadsheet.worksheet("Feedback Log")
        if not fb_ws.row_values(1):
            fb_ws.append_row(FEEDBACK_HEADERS)

        admin_ws = self.spreadsheet.worksheet("Admin")
        if not admin_ws.row_values(1):
            admin_ws.append_row(ADMIN_HEADERS)

        archive_ws = self.spreadsheet.worksheet("Archive")
        if not archive_ws.row_values(1):
            archive_ws.append_row(FEEDBACK_HEADERS)

    # ── Dedup hashes ─────────────────────────────────────────────────────────

    def get_seen_hashes(self) -> Set[str]:
        ws = self.spreadsheet.worksheet("seen_hashes")
        values = ws.col_values(1)
        return {v for v in values if v.strip()}

    def append_hashes(self, hashes: List[str]) -> None:
        if not hashes:
            return
        ws = self.spreadsheet.worksheet("seen_hashes")
        ws.append_rows([[h] for h in hashes])
        log.info("Stored %d new hashes", len(hashes))

    # ── Feedback Log ─────────────────────────────────────────────────────────

    def append_feedback(self, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        ws = self.spreadsheet.worksheet("Feedback Log")
        rows = [_to_row(item) for item in items]
        for start in range(0, len(rows), _WRITE_BATCH):
            chunk = rows[start : start + _WRITE_BATCH]
            ws.append_rows(chunk, value_input_option="RAW", insert_data_option="INSERT_ROWS")
            log.info(
                "Wrote rows %d–%d to Feedback Log",
                start + 1,
                start + len(chunk),
            )
            if start + _WRITE_BATCH < len(rows):
                time.sleep(_WRITE_SLEEP)

    # ── Admin tab ────────────────────────────────────────────────────────────

    def upsert_admin(
        self,
        client_config: ClientConfig,
        status: str,
        keywords_en: List[str],
        keywords_ar: List[str],
    ) -> None:
        ws = self.spreadsheet.worksheet("Admin")
        all_values = ws.get_all_values()

        client_row_idx: Optional[int] = None
        for i, row in enumerate(all_values[1:], start=2):
            if row and row[0] == client_config.display_name:
                client_row_idx = i
                break

        playstore_url = (
            f"https://play.google.com/store/apps/details?id={client_config.playstore_id}"
            if client_config.playstore_id
            else ""
        )
        appstore_url = (
            f"https://apps.apple.com/eg/app/id{client_config.appstore_id}"
            if client_config.appstore_id
            else ""
        )

        new_row = [
            client_config.display_name,
            playstore_url,
            appstore_url,
            json.dumps(keywords_en, ensure_ascii=False),
            json.dumps(keywords_ar, ensure_ascii=False),
            "",  # dead_keywords — populated in Phase 3 rotation logic
            status,
            datetime.now(timezone.utc).isoformat(),
        ]

        if client_row_idx:
            ws.update(f"A{client_row_idx}:H{client_row_idx}", [new_row])
            log.info("Updated Admin row for %s — status=%s", client_config.display_name, status)
        else:
            ws.append_row(new_row)
            log.info("Created Admin row for %s — status=%s", client_config.display_name, status)


    # ── Housekeeping — row counts ─────────────────────────────────────────────

    def count_feedback_rows(self) -> int:
        """Data rows in Feedback Log (excludes header)."""
        # Use an open-ended range to avoid the cached row_count issue:
        # ws.col_values() uses ws.row_count which is frozen at init time and
        # does not update after append_rows(). values_get with A:A is unbounded.
        result = self.spreadsheet.values_get("'Feedback Log'!A:A")
        return max(0, len(result.get("values", [])) - 1)

    def count_archive_rows(self) -> int:
        """Data rows in Archive tab (excludes header)."""
        result = self.spreadsheet.values_get("'Archive'!A:A")
        return max(0, len(result.get("values", [])) - 1)

    # ── Housekeeping — read all rows ─────────────────────────────────────────

    def get_all_feedback_rows(self) -> List[Dict[str, Any]]:
        """All Feedback Log data rows as list of dicts (header excluded)."""
        ws = self.spreadsheet.worksheet("Feedback Log")
        return _rows_as_dicts(ws, FEEDBACK_HEADERS)

    def get_all_archive_rows(self) -> List[Dict[str, Any]]:
        """All Archive tab data rows as list of dicts (header excluded)."""
        ws = self.spreadsheet.worksheet("Archive")
        return _rows_as_dicts(ws, FEEDBACK_HEADERS)

    # ── Housekeeping — write to Archive tab ──────────────────────────────────

    def append_to_archive(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        ws = self.spreadsheet.worksheet("Archive")
        data = [_dict_to_row(r, FEEDBACK_HEADERS) for r in rows]
        for start in range(0, len(data), _WRITE_BATCH):
            chunk = data[start : start + _WRITE_BATCH]
            ws.append_rows(chunk, value_input_option="RAW", insert_data_option="INSERT_ROWS")
            if start + _WRITE_BATCH < len(data):
                time.sleep(_WRITE_SLEEP)
        log.info("Archived %d rows to Archive tab", len(rows))

    def clear_archive_tab(self) -> None:
        ws = self.spreadsheet.worksheet("Archive")
        ws.clear()
        ws.append_row(FEEDBACK_HEADERS)
        log.info("Archive tab cleared and re-headered")

    # ── Housekeeping — rewrite Feedback Log ──────────────────────────────────

    def replace_feedback_rows(self, rows: List[Dict[str, Any]]) -> None:
        """Clear Feedback Log (keep header) and rewrite with given rows."""
        ws = self.spreadsheet.worksheet("Feedback Log")
        ws.clear()
        ws.append_row(FEEDBACK_HEADERS)
        if not rows:
            return
        data = [_dict_to_row(r, FEEDBACK_HEADERS) for r in rows]
        for start in range(0, len(data), _WRITE_BATCH):
            chunk = data[start : start + _WRITE_BATCH]
            ws.append_rows(chunk, value_input_option="RAW", insert_data_option="INSERT_ROWS")
            if start + _WRITE_BATCH < len(data):
                time.sleep(_WRITE_SLEEP)
        log.info("Rewrote Feedback Log with %d rows", len(rows))

    # ── Housekeeping — create archive spreadsheet ─────────────────────────────

    def create_archive_spreadsheet(
        self,
        title: str,
        rows: List[Dict[str, Any]],
    ) -> str:
        """
        Create a new Google Spreadsheet named `title`, write `rows` into its
        first sheet, return the new spreadsheet's ID.
        """
        new_ss = self._gc.create(title)
        new_ws = new_ss.sheet1
        new_ws.update_title("Feedback Log")
        new_ws.append_row(FEEDBACK_HEADERS)

        if rows:
            data = [_dict_to_row(r, FEEDBACK_HEADERS) for r in rows]
            for start in range(0, len(data), _WRITE_BATCH):
                chunk = data[start : start + _WRITE_BATCH]
                new_ws.append_rows(chunk, value_input_option="RAW", insert_data_option="INSERT_ROWS")
                if start + _WRITE_BATCH < len(data):
                    time.sleep(_WRITE_SLEEP)

        log.info(
            "Created archive spreadsheet '%s' with %d rows (ID: %s)",
            title, len(rows), new_ss.id,
        )
        return new_ss.id


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client() -> gspread.Client:
    sa_b64 = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sa_info = json.loads(base64.b64decode(sa_b64))
    return gspread.service_account_from_dict(sa_info)


def _to_row(item: Dict[str, Any]) -> List[Any]:
    return [
        item.get("client_name", ""),
        item.get("post_url", ""),
        item.get("source", ""),
        item.get("post_date", ""),
        item.get("author", ""),
        item.get("raw_text", ""),
        item.get("language", ""),
        item.get("rating", ""),
        item.get("sentiment", ""),
        item.get("feedback_type", ""),
        item.get("product_area", ""),
        item.get("severity", ""),
        item.get("engagement", ""),
        "TRUE" if item.get("agreement_signal") else "FALSE",
        item.get("claude_summary", ""),
        item.get("scraped_at", ""),
        item.get("valify_scope", ""),
    ]


def _dict_to_row(d: Dict[str, Any], headers: List[str]) -> List[Any]:
    """Serialize a dict back to a list in header column order."""
    return [str(d.get(h, "")) for h in headers]


def _rows_as_dicts(ws, headers: List[str]) -> List[Dict[str, Any]]:
    """Read all data rows from a worksheet and return as list of dicts."""
    all_values = ws.get_all_values()
    if len(all_values) < 2:
        return []
    # Use sheet headers if present, fall back to provided headers
    sheet_headers = all_values[0] if all_values[0] else headers
    result = []
    for row in all_values[1:]:
        padded = row + [""] * max(0, len(sheet_headers) - len(row))
        result.append(dict(zip(sheet_headers, padded)))
    return result
