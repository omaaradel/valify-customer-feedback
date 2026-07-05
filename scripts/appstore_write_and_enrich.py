#!/usr/bin/env python3
"""
App Store write-and-enrich runner.

Step 1: Scrape App Store for all 8 clients (30-day window).
Step 2: Run sanity checks before any write.
Step 3: Write clean App Store rows to Feedback Log (source=appstore).
Step 4: Enrich the new rows via Gemini (full enrichment).
Step 5: Retire web_ddg: quarantine 73 rows to Quarantine tab, disable DDG source.

Run from repo root:
  python scripts/appstore_write_and_enrich.py
  python scripts/appstore_write_and_enrich.py --dry-run
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import CLIENTS
from scrapers.appstore import fetch as fetch_appstore
from sheets import SheetsClient, FEEDBACK_HEADERS
from utils.dedup import make_hash
from enrichment.gemini_classifier import get_api_key, enrich_full_batch


_DAYS = 30
_TEMP_FILE = "appstore_scraped_temp.json"
_ENRICH_CHUNK = 50          # rows per enrich_full_batch call (internal _BATCH_SIZE=10 handles API batching)
_INTER_CHUNK_SLEEP = 5.0    # seconds between enrichment chunks
_DROP_FLAG_THRESHOLD = 0.20 # flag and stop if more than 20% of scraped rows are dropped
_SCOPE_FLAG_THRESHOLD = 0.40  # flag if valify_scope=true exceeds 40% of enriched rows

# Column positions (1-indexed) in Feedback Log, matching enrich_phase8.py.
_COL_SENTIMENT = 9
_COL_FEEDBACK_TYPE = 10
_COL_PRODUCT_AREA = 11
_COL_SEVERITY = 12
_COL_AGREEMENT_SIGNAL = 14
_COL_CLAUDE_SUMMARY = 15
_COL_VALIFY_SCOPE = 17

_FULL_COLS = {
    "sentiment": _COL_SENTIMENT,
    "feedback_type": _COL_FEEDBACK_TYPE,
    "product_area": _COL_PRODUCT_AREA,
    "severity": _COL_SEVERITY,
    "agreement_signal": _COL_AGREEMENT_SIGNAL,
    "claude_summary": _COL_CLAUDE_SUMMARY,
    "valify_scope": _COL_VALIFY_SCOPE,
}

QUARANTINE_HEADERS = FEEDBACK_HEADERS + ["quarantine_reason"]
_QUARANTINE_REASON = "web_ddg retired: search snippet, not a user review."

_WRITE_BATCH = 100
_WRITE_SLEEP = 1.0


def _col_letter(n: int) -> str:
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


# ---- Step 1 ----------------------------------------------------------------

def step1_scrape(since: datetime) -> Tuple[List[Dict], List[Tuple]]:
    """Scrape App Store for all 8 clients. Returns (all_rows, client_table).

    client_table entries: (display_name, row_count, suspected_block, status_note)
    Rows from suspected-block clients are excluded from all_rows.
    """
    all_rows: List[Dict] = []
    client_table: List[Tuple] = []
    appstore_call_n = 0

    for key, client in CLIENTS.items():
        if not client.appstore_id:
            client_table.append((client.display_name, 0, False, "no_app_id"))
            continue

        print(f"Scraping App Store: {client.display_name} ...")
        rows, suspected_block = fetch_appstore(
            app_id=client.appstore_id,
            display_name=client.display_name,
            since=since,
            sleep_before=(appstore_call_n > 0),
        )
        appstore_call_n += 1

        if suspected_block:
            status = "SUSPECTED_BLOCK"
            print(f"  WARNING: {client.display_name} suspected block -- 0 rows included.")
        else:
            status = "ok"
            all_rows.extend(rows)

        client_table.append((client.display_name, len(rows), suspected_block, status))

    return all_rows, client_table


# ---- Step 2 ----------------------------------------------------------------

def step2_sanity_checks(
    scraped_rows: List[Dict],
    client_table: List[Tuple],
    seen_hashes: Set[str],
    since: datetime,
) -> Tuple[List[Dict], Dict]:
    """Run sanity checks. Returns (clean_rows, report)."""
    now = datetime.now(timezone.utc)
    total = len(scraped_rows)

    blocked_clients = [name for name, count, blocked, _ in client_table if blocked]

    # 1. Dedup within the scraped batch (same client + same raw_text).
    seen_text_keys: Set[str] = set()
    dup_count = 0
    deduped: List[Dict] = []
    for row in scraped_rows:
        key = f"{row['client_name']}|{row['raw_text']}"
        if key in seen_text_keys:
            dup_count += 1
        else:
            seen_text_keys.add(key)
            deduped.append(row)

    # 2. Short or empty review_text (under 3 words).
    short_count = 0
    text_ok: List[Dict] = []
    for row in deduped:
        if len(row.get("raw_text", "").split()) < 3:
            short_count += 1
        else:
            text_ok.append(row)

    # 3. Date sanity: future or older than the 30-day window.
    date_bad_count = 0
    date_ok: List[Dict] = []
    for row in text_ok:
        pd = row.get("post_date", "")
        if not pd:
            date_ok.append(row)
            continue
        try:
            dt = datetime.fromisoformat(pd)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(timezone.utc)
            if dt > now or dt < since:
                date_bad_count += 1
            else:
                date_ok.append(row)
        except ValueError:
            date_ok.append(row)

    # 4. SHA-256 dedup against rows already in the sheet.
    already_seen_count = 0
    new_rows: List[Dict] = []
    for row in date_ok:
        h = make_hash(row["source"], row["post_url"], row["raw_text"])
        if h in seen_hashes:
            already_seen_count += 1
        else:
            row["_hash"] = h
            new_rows.append(row)

    dropped_total = dup_count + short_count + date_bad_count + already_seen_count
    drop_rate = dropped_total / total if total > 0 else 0.0

    report = {
        "total_scraped": total,
        "blocked_clients": blocked_clients,
        "duplicates_within_scrape": dup_count,
        "short_text_quarantined": short_count,
        "date_out_of_range": date_bad_count,
        "already_in_sheet": already_seen_count,
        "dropped_total": dropped_total,
        "drop_rate": drop_rate,
        "will_proceed": len(new_rows),
    }

    return new_rows, report


# ---- Step 3 ----------------------------------------------------------------

def step3_write(sheet: SheetsClient, clean_rows: List[Dict], dry_run: bool) -> int:
    """Write clean rows to Feedback Log. Returns data-row count before writing."""
    before_count = sheet.count_feedback_rows()
    print(f"Feedback Log has {before_count} data rows before write.")

    if dry_run:
        print(f"[DRY RUN] Would write {len(clean_rows)} App Store rows.")
        return before_count

    sheet.append_feedback(clean_rows)
    new_hashes = [row["_hash"] for row in clean_rows if "_hash" in row]
    sheet.append_hashes(new_hashes)

    after_count = sheet.count_feedback_rows()
    print(f"Wrote {len(clean_rows)} rows. Feedback Log now has {after_count} data rows.")
    return before_count


# ---- Helpers ---------------------------------------------------------------

def _batch_update_with_retry(ws, updates: List[Dict], max_attempts: int = 3) -> None:
    """Write cell updates with simple exponential-backoff retry on network/quota errors."""
    for attempt in range(max_attempts):
        try:
            ws.batch_update(updates)
            print(f"    Wrote {len(updates)} cell updates to Feedback Log.")
            return
        except Exception as exc:
            if attempt < max_attempts - 1:
                wait = 20 * (attempt + 1)
                print(f"    batch_update error (attempt {attempt + 1}/{max_attempts}): {exc}")
                print(f"    Retrying in {wait}s ...")
                time.sleep(wait)
            else:
                print(f"    batch_update failed after {max_attempts} attempts: {exc}")
                raise


def _pull_unenriched_appstore_rows(ws) -> List[Dict]:
    """Return Feedback Log rows where source=appstore and sentiment is empty.

    Each returned dict has row_id, row_number, client, source, review_text.
    """
    all_values = ws.get_all_values()
    if len(all_values) < 2:
        return []
    header = all_values[0]

    def _col(name: str) -> Optional[int]:
        return header.index(name) if name in header else None

    col_source = _col("source")
    col_sentiment = _col("sentiment")
    col_client = _col("client_name")
    col_raw_text = _col("raw_text")

    rows = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        row = row + [""] * (max(len(header), _COL_VALIFY_SCOPE) - len(row))
        source = row[col_source] if col_source is not None else ""
        sentiment = row[col_sentiment] if col_sentiment is not None else ""
        if source == "appstore" and not sentiment:
            rows.append({
                "row_id": str(row_idx),
                "row_number": row_idx,
                "client": row[col_client] if col_client is not None else "",
                "source": source,
                "review_text": row[col_raw_text] if col_raw_text is not None else "",
            })
    return rows


# ---- Step 4 ----------------------------------------------------------------

def step4_enrich(
    sheet: SheetsClient,
    clean_rows: List[Dict],
    before_count: int,
    dry_run: bool,
) -> None:
    """Enrich newly written App Store rows using Gemini full enrichment."""
    api_key = get_api_key()

    # Assign sheet row numbers. New rows follow header (row 1) and existing rows
    # (rows 2 .. before_count+1), so new row i (0-indexed) is at sheet row
    # before_count + 2 + i.
    gemini_rows = []
    for i, row in enumerate(clean_rows):
        sheet_row = before_count + 2 + i
        gemini_rows.append({
            "row_id": str(sheet_row),
            "row_number": sheet_row,
            "client": row["client_name"],
            "source": row["source"],
            "review_text": row["raw_text"],
        })

    print(f"Enriching {len(gemini_rows)} App Store rows via Gemini...")

    # Reuse the SheetsClient's underlying spreadsheet to avoid a second auth round-trip.
    ws = sheet.spreadsheet.worksheet("Feedback Log")

    headers = ws.row_values(1)
    if len(headers) < _COL_VALIFY_SCOPE or headers[_COL_VALIFY_SCOPE - 1] != "valify_scope":
        ws.update(f"{_col_letter(_COL_VALIFY_SCOPE)}1", [["valify_scope"]])
        print("Added 'valify_scope' header to column Q.")

    all_results: List[Dict] = []

    for chunk_start in range(0, len(gemini_rows), _ENRICH_CHUNK):
        chunk = gemini_rows[chunk_start: chunk_start + _ENRICH_CHUNK]
        print(
            f"  Enriching rows {chunk_start + 1} to {chunk_start + len(chunk)}"
            f" of {len(gemini_rows)} ..."
        )

        results = enrich_full_batch(chunk, api_key)

        # Map row_number from chunk back to results by row_id.
        id_to_num = {str(r["row_number"]): r["row_number"] for r in chunk}
        for item in results:
            if item.get("row_number") is None:
                item["row_number"] = id_to_num.get(str(item.get("row_id", "")))

        valid_results = [r for r in results if r.get("row_number") is not None]

        if not dry_run and valid_results:
            updates = []
            for item in valid_results:
                row_num = item["row_number"]
                for field, col in _FULL_COLS.items():
                    val = item.get(field, "")
                    if isinstance(val, bool):
                        val = str(val).lower()
                    updates.append({"range": f"{_col_letter(col)}{row_num}", "values": [[val]]})
            if updates:
                _batch_update_with_retry(ws, updates)

        all_results.extend(valid_results)

        if chunk_start + _ENRICH_CHUNK < len(gemini_rows):
            print(f"  Pausing {_INTER_CHUNK_SLEEP:.0f}s between chunks...")
            time.sleep(_INTER_CHUNK_SLEEP)

    _print_enrichment_summary(all_results)


def _print_enrichment_summary(results: List[Dict]) -> None:
    total = len(results)
    scope_counts: Dict[str, int] = {}
    sentiment_counts: Dict[str, int] = {}
    for r in results:
        vs = r.get("valify_scope", "")
        s = r.get("sentiment", "")
        scope_counts[vs] = scope_counts.get(vs, 0) + 1
        sentiment_counts[s] = sentiment_counts.get(s, 0) + 1

    print(f"\nEnrichment summary: {total} rows processed.")
    print("  valify_scope breakdown:")
    for k in ("true", "false", "unsure", "parse_error"):
        if k in scope_counts:
            print(f"    {k}: {scope_counts[k]}")
    print("  sentiment breakdown:")
    for k in ("positive", "negative", "neutral", "parse_error"):
        if k in sentiment_counts:
            print(f"    {k}: {sentiment_counts[k]}")

    true_count = scope_counts.get("true", 0)
    if total > 0:
        true_rate = true_count / total
        if true_rate > _SCOPE_FLAG_THRESHOLD:
            print(
                f"\nFLAG: valify_scope=true is {true_count}/{total} ({true_rate:.0%})."
                f" App reviews skew toward general complaints;"
                f" a rate above 40% suggests scope rule drift. Investigate before accepting."
            )
        else:
            print(
                f"\nSanity check passed: valify_scope=true is {true_count}/{total}"
                f" ({true_rate:.0%}), within expected range."
            )


# ---- Step 5 ----------------------------------------------------------------

def step5_retire_web_ddg(sheet: SheetsClient, dry_run: bool) -> None:
    """Move web_ddg rows to Quarantine tab and confirm Feedback Log is clean."""
    print("\n--- Step 5: Retire web_ddg source ---")

    all_rows = sheet.get_all_feedback_rows()
    web_ddg_rows = [r for r in all_rows if r.get("source") == "web_ddg"]
    keep_rows = [r for r in all_rows if r.get("source") != "web_ddg"]

    print(f"Found {len(web_ddg_rows)} web_ddg rows in Feedback Log.")

    if not web_ddg_rows:
        print("No web_ddg rows found. Quarantine step skipped.")
        return

    # Ensure Quarantine tab exists.
    existing_tabs = {ws.title for ws in sheet.spreadsheet.worksheets()}
    if "Quarantine" not in existing_tabs:
        q_ws = sheet.spreadsheet.add_worksheet(title="Quarantine", rows=5000, cols=20)
        q_ws.append_row(QUARANTINE_HEADERS)
        print("Created Quarantine tab.")
    else:
        q_ws = sheet.spreadsheet.worksheet("Quarantine")
        if not q_ws.row_values(1):
            q_ws.append_row(QUARANTINE_HEADERS)
            print("Added header row to existing Quarantine tab.")

    if dry_run:
        print(
            f"[DRY RUN] Would quarantine {len(web_ddg_rows)} rows to Quarantine tab"
            f" and rewrite Feedback Log with {len(keep_rows)} rows."
        )
        return

    # Write web_ddg rows to Quarantine.
    q_data = []
    for row in web_ddg_rows:
        r_list = [str(row.get(h, "")) for h in FEEDBACK_HEADERS]
        r_list.append(_QUARANTINE_REASON)
        q_data.append(r_list)

    for start in range(0, len(q_data), _WRITE_BATCH):
        chunk = q_data[start: start + _WRITE_BATCH]
        q_ws.append_rows(chunk, value_input_option="RAW", insert_data_option="INSERT_ROWS")
        if start + _WRITE_BATCH < len(q_data):
            time.sleep(_WRITE_SLEEP)

    print(f"Wrote {len(web_ddg_rows)} rows to Quarantine tab.")

    # Rewrite Feedback Log without web_ddg rows.
    sheet.replace_feedback_rows(keep_rows)

    # Verify.
    final_count = sheet.count_feedback_rows()
    print(f"Feedback Log rewritten. Now has {final_count} data rows.")

    # Spot-check: confirm no web_ddg rows remain.
    remaining = sum(
        1 for r in sheet.get_all_feedback_rows()
        if r.get("source") == "web_ddg"
    )
    if remaining == 0:
        print("Confirmed: Feedback Log contains 0 web_ddg rows.")
    else:
        print(f"WARNING: {remaining} web_ddg rows still remain in Feedback Log. Investigate.")


# ---- Resume (step 4+5 only) ------------------------------------------------

def run_resume() -> None:
    """Enrich any unenriched appstore rows in the sheet, then retire web_ddg.

    Use this when step 4 failed mid-run and 93 rows are already in the sheet
    but some have empty sentiment. Reads the sheet, finds those rows, enriches
    them, and then runs step 5.
    """
    print("Resume mode: enriching unenriched App Store rows + retiring web_ddg.")
    api_key = get_api_key()
    sheet = SheetsClient()
    ws = sheet.spreadsheet.worksheet("Feedback Log")

    headers = ws.row_values(1)
    if len(headers) < _COL_VALIFY_SCOPE or headers[_COL_VALIFY_SCOPE - 1] != "valify_scope":
        ws.update(f"{_col_letter(_COL_VALIFY_SCOPE)}1", [["valify_scope"]])
        print("Added 'valify_scope' header to column Q.")

    print("Reading sheet to find unenriched App Store rows ...")
    gemini_rows = _pull_unenriched_appstore_rows(ws)
    print(f"Found {len(gemini_rows)} unenriched App Store rows (source=appstore, sentiment empty).")

    if not gemini_rows:
        print("No unenriched rows found. Proceeding to Step 5.")
    else:
        all_results: List[Dict] = []
        for chunk_start in range(0, len(gemini_rows), _ENRICH_CHUNK):
            chunk = gemini_rows[chunk_start: chunk_start + _ENRICH_CHUNK]
            print(
                f"  Enriching rows {chunk_start + 1} to {chunk_start + len(chunk)}"
                f" of {len(gemini_rows)} ..."
            )
            results = enrich_full_batch(chunk, api_key)

            id_to_num = {str(r["row_number"]): r["row_number"] for r in chunk}
            for item in results:
                if item.get("row_number") is None:
                    item["row_number"] = id_to_num.get(str(item.get("row_id", "")))

            valid_results = [r for r in results if r.get("row_number") is not None]

            if valid_results:
                updates = []
                for item in valid_results:
                    row_num = item["row_number"]
                    for field, col in _FULL_COLS.items():
                        val = item.get(field, "")
                        if isinstance(val, bool):
                            val = str(val).lower()
                        updates.append({"range": f"{_col_letter(col)}{row_num}", "values": [[val]]})
                if updates:
                    _batch_update_with_retry(ws, updates)

            all_results.extend(valid_results)

            if chunk_start + _ENRICH_CHUNK < len(gemini_rows):
                print(f"  Pausing {_INTER_CHUNK_SLEEP:.0f}s between chunks...")
                time.sleep(_INTER_CHUNK_SLEEP)

        _print_enrichment_summary(all_results)

    step5_retire_web_ddg(sheet, dry_run=False)
    print("\nResume complete.")


# ---- Main ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="App Store write-and-enrich + web_ddg retirement"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and check without writing to the sheet or calling Gemini.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Skip scrape/write. Enrich any unenriched appstore rows already in the sheet,"
            " then retire web_ddg. Use after a mid-run failure in step 4."
        ),
    )
    args = parser.parse_args()

    if args.resume:
        run_resume()
        return

    since = datetime.now(timezone.utc) - timedelta(days=_DAYS)
    print(f"App Store 30-day window: since {since.date()} UTC.")

    # ---- Step 1: Scrape ------------------------------------------------
    print("\n--- Step 1: Scrape App Store (30-day window) ---")
    scraped_rows, client_table = step1_scrape(since)

    serialisable = [
        {k: v.isoformat() if isinstance(v, datetime) else v for k, v in row.items()}
        for row in scraped_rows
    ]
    with open(_TEMP_FILE, "w", encoding="utf-8") as f:
        json.dump(serialisable, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(scraped_rows)} scraped rows to {_TEMP_FILE}.")

    print("\nPer-client App Store results:")
    print(f"  {'Client':<15} {'Rows':>6}  Suspected Block")
    print("  " + "-" * 40)
    for name, count, blocked, status in client_table:
        flag = "YES" if blocked else "no"
        print(f"  {name:<15} {count:>6}  {flag}")
    blocked_count = sum(1 for _, _, b, _ in client_table if b)
    total_non_blocked = sum(c for _, c, b, _ in client_table if not b)
    print(f"\n  Total rows (non-blocked clients): {total_non_blocked}")
    if blocked_count:
        print(f"  Blocked clients: {blocked_count}")

    # ---- Step 2: Sanity checks ----------------------------------------
    print("\n--- Step 2: Sanity Checks ---")
    print("Connecting to sheet ...")
    sheet = SheetsClient()
    seen_hashes = sheet.get_seen_hashes()
    print(f"Loaded {len(seen_hashes)} existing hashes from sheet.")

    clean_rows, report = step2_sanity_checks(scraped_rows, client_table, seen_hashes, since)

    print("\nSanity check report:")
    print(f"  Total scraped (non-blocked clients): {report['total_scraped']}")
    if report["blocked_clients"]:
        print(f"  FLAG: Suspected-block clients (rows excluded): {', '.join(report['blocked_clients'])}")
    print(f"  Duplicates within scrape (dropped): {report['duplicates_within_scrape']}")
    print(f"  Short text under 3 words (quarantined): {report['short_text_quarantined']}")
    print(f"  Date out of 30-day window (dropped): {report['date_out_of_range']}")
    print(f"  Already in sheet via SHA-256 dedup (skipped): {report['already_in_sheet']}")
    print(f"  Total dropped or excluded: {report['dropped_total']}")
    print(f"  Drop rate: {report['drop_rate']:.1%}")
    print(f"  Rows proceeding to write: {report['will_proceed']}")

    if report["drop_rate"] > _DROP_FLAG_THRESHOLD:
        print(
            f"\nSTOP: Drop rate {report['drop_rate']:.1%} exceeds"
            f" {_DROP_FLAG_THRESHOLD:.0%} threshold."
            " Review the report above before proceeding."
        )
        return

    if report["will_proceed"] == 0:
        print("\nNothing new to write. All App Store rows are already in the sheet.")
    else:
        # ---- Step 3: Write --------------------------------------------
        print("\n--- Step 3: Write Clean App Store Rows ---")
        before_count = step3_write(sheet, clean_rows, args.dry_run)

        # ---- Step 4: Enrich ------------------------------------------
        print("\n--- Step 4: Enrich New App Store Rows ---")
        if args.dry_run:
            print("[DRY RUN] Skipping Gemini enrichment.")
        else:
            step4_enrich(sheet, clean_rows, before_count, args.dry_run)

    # ---- Step 5: Retire web_ddg --------------------------------------
    step5_retire_web_ddg(sheet, args.dry_run)

    print("\nDone.")


if __name__ == "__main__":
    main()
