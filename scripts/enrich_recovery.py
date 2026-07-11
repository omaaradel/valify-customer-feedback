#!/usr/bin/env python3
"""
Post-Phase-8c recovery enrichment.

Step 1  --step parse-error
  Full re-enrichment for 33 appstore rows that received parse_error during Phase 8c
  due to Gemini quota exhaustion. All 7 fields (sentiment, feedback_type, product_area,
  severity, agreement_signal, claude_summary, valify_scope) are re-enriched.

Step 2  --step valify-scope
  Adds valify_scope to rows that already have correct sentiment + feedback_type values
  but are missing valify_scope (column Q was wiped by the Phase 8c column-drop bug).
  Writes ONLY column Q (valify_scope). No other field is touched.

  Targets rows where:
    - sentiment is set and not parse_error
    - feedback_type is set, not off_topic, not parse_error
    - valify_scope is empty

Run in order:
  python scripts/enrich_recovery.py --step parse-error
  python scripts/enrich_recovery.py --step valify-scope

Dry-run (classify, do not write):
  python scripts/enrich_recovery.py --step parse-error --dry-run
  python scripts/enrich_recovery.py --step valify-scope --dry-run
"""
import argparse
import base64
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import gspread

from enrichment.gemini_classifier import build_system_instruction
from enrichment.provider_chain import ProviderChain, build_default_providers


def _build_chain() -> tuple:
    """Build a ProviderChain using the standard provider order (Gemini, then
    Groq and OpenRouter if their keys are set). See
    enrichment.provider_chain.build_default_providers."""
    providers = build_default_providers()
    return ProviderChain(providers), build_system_instruction()

# Column positions (1-indexed) in Feedback Log
_COL_SENTIMENT       = 9
_COL_FEEDBACK_TYPE   = 10
_COL_PRODUCT_AREA    = 11
_COL_SEVERITY        = 12
_COL_AGREEMENT       = 14
_COL_SUMMARY         = 15
_COL_VALIFY_SCOPE    = 17

_FULL_COLS = {
    "sentiment":        _COL_SENTIMENT,
    "feedback_type":    _COL_FEEDBACK_TYPE,
    "product_area":     _COL_PRODUCT_AREA,
    "severity":         _COL_SEVERITY,
    "agreement_signal": _COL_AGREEMENT,
    "claude_summary":   _COL_SUMMARY,
    "valify_scope":     _COL_VALIFY_SCOPE,
}


def _col_letter(n: int) -> str:
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def _open_sheet():
    sa_b64 = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sa_info = json.loads(base64.b64decode(sa_b64))
    gc = gspread.service_account_from_dict(sa_info)
    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    return sh.worksheet("Feedback Log")


def _get(row, col_0idx):
    if col_0idx is None or col_0idx >= len(row):
        return ""
    return row[col_0idx].strip()


def _pull_parse_error_appstore(ws) -> list:
    """Appstore rows where sentiment == 'parse_error'."""
    all_values = ws.get_all_values()
    if len(all_values) < 2:
        return []
    header = all_values[0]

    def ci(name):
        return header.index(name) if name in header else None

    c_src  = ci("source")
    c_sent = ci("sentiment")
    c_cli  = ci("client_name")
    c_raw  = ci("raw_text")

    rows = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        row = row + [""] * max(0, _COL_VALIFY_SCOPE - len(row))
        if _get(row, c_src) == "appstore" and _get(row, c_sent) == "parse_error":
            rows.append({
                "row_id":    str(row_idx),
                "row_number": row_idx,
                "client":    _get(row, c_cli),
                "source":    "appstore",
                "review_text": _get(row, c_raw),
            })
    return rows


def _pull_missing_valify_scope(ws) -> list:
    """Rows with real enrichment (non-empty, non-parse_error sentiment and
    feedback_type != off_topic) that are missing valify_scope."""
    all_values = ws.get_all_values()
    if len(all_values) < 2:
        return []
    header = all_values[0]

    def ci(name):
        return header.index(name) if name in header else None

    c_src  = ci("source")
    c_sent = ci("sentiment")
    c_ft   = ci("feedback_type")
    c_cli  = ci("client_name")
    c_raw  = ci("raw_text")

    rows = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        row = row + [""] * max(0, _COL_VALIFY_SCOPE - len(row))
        sentiment     = _get(row, c_sent)
        feedback_type = _get(row, c_ft)
        scope_val     = row[_COL_VALIFY_SCOPE - 1] if len(row) >= _COL_VALIFY_SCOPE else ""

        # scope_val == "parse_error" is a leftover failed-classification marker from a prior
        # run (pre-write-guard). It is not a real value, so it is treated as missing, same as blank.
        if (sentiment
                and sentiment != "parse_error"
                and feedback_type
                and feedback_type not in ("off_topic", "parse_error")
                and (not scope_val or scope_val == "parse_error")):
            rows.append({
                "row_id":    str(row_idx),
                "row_number": row_idx,
                "client":    _get(row, c_cli),
                "source":    _get(row, c_src),
                "review_text": _get(row, c_raw),
            })
    return rows


def _merge_row_numbers(api_results: list, source_rows: list) -> list:
    id_to_num = {str(r["row_number"]): r["row_number"] for r in source_rows}
    merged = []
    for item in api_results:
        num = id_to_num.get(str(item.get("row_id", "")))
        if num is not None:
            item["row_number"] = num
            merged.append(item)
    return merged


def _batch_update_retry(ws, updates: list, max_attempts: int = 3) -> None:
    for attempt in range(max_attempts):
        try:
            ws.batch_update(updates)
            return
        except Exception as exc:
            if attempt < max_attempts - 1:
                wait = 20 * (attempt + 1)
                print(f"  [batch_update] Attempt {attempt + 1} failed: {exc}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def _write_full_results(ws, results: list, dry_run: bool) -> None:
    updates = []
    for item in results:
        row = item["row_number"]
        for field, col in _FULL_COLS.items():
            val = item.get(field, "")
            if isinstance(val, bool):
                val = str(val).lower()
            updates.append({"range": f"{_col_letter(col)}{row}", "values": [[str(val)]]})
    if dry_run:
        print(f"[DRY RUN] Would write {len(updates)} cell updates across {len(results)} rows.")
        for u in updates[:14]:
            print(f"  {u['range']}: {u['values'][0][0]!r}")
        if len(updates) > 14:
            print(f"  ... and {len(updates) - 14} more")
    else:
        if updates:
            _batch_update_retry(ws, updates)
            print(f"Wrote {len(updates)} cell updates for {len(results)} rows.")


def _write_valify_scope_only(ws, results: list, dry_run: bool) -> None:
    updates = []
    for item in results:
        row = item["row_number"]
        val = item.get("valify_scope")
        if val is None:
            continue
        updates.append({"range": f"{_col_letter(_COL_VALIFY_SCOPE)}{row}", "values": [[str(val)]]})
    if dry_run:
        print(f"[DRY RUN] Would write {len(updates)} valify_scope values.")
        for u in updates[:10]:
            print(f"  {u['range']}: {u['values'][0][0]!r}")
        if len(updates) > 10:
            print(f"  ... and {len(updates) - 10} more")
    else:
        if updates:
            _batch_update_retry(ws, updates)
            print(f"Wrote {len(updates)} valify_scope values.")


def _norm(val) -> str:
    """Normalize a field value to a lowercase string (handles JSON booleans)."""
    if val is None:
        return ""
    return str(val).lower()


def _print_full_summary(results: list) -> None:
    scope_counts  = {}
    sent_counts   = {}
    ft_counts     = {}
    for r in results:
        vs = _norm(r.get("valify_scope", ""))
        s  = _norm(r.get("sentiment", ""))
        ft = _norm(r.get("feedback_type", ""))
        scope_counts[vs] = scope_counts.get(vs, 0) + 1
        sent_counts[s]   = sent_counts.get(s, 0) + 1
        ft_counts[ft]    = ft_counts.get(ft, 0) + 1

    print(f"\nRows processed: {len(results)}")
    print("valify_scope:  " + "  ".join(f"{k}={v}" for k, v in sorted(scope_counts.items())))
    print("sentiment:     " + "  ".join(f"{k}={v}" for k, v in sorted(sent_counts.items())))
    print("feedback_type: " + "  ".join(f"{k}={v}" for k, v in sorted(ft_counts.items())))

    pe = scope_counts.get("parse_error", 0)
    if pe:
        print(f"\nFLAG: {pe} rows still got parse_error for valify_scope.")
        print("  Check Gemini quota or try again after the quota window resets.")
    else:
        print(f"\nAll {len(results)} rows classified successfully.")


def _print_scope_summary(results: list) -> None:
    scope_counts = {}
    for r in results:
        vs = _norm(r.get("valify_scope", ""))
        scope_counts[vs] = scope_counts.get(vs, 0) + 1

    print(f"\nRows processed: {len(results)}")
    print("valify_scope: " + "  ".join(f"{k}={v}" for k, v in sorted(scope_counts.items())))

    pe = scope_counts.get("parse_error", 0)
    if pe:
        print(f"\nFLAG: {pe} rows got parse_error for valify_scope.")
        print("  Check Gemini quota or try again after the quota window resets.")
    else:
        print(f"\nAll {len(results)} rows got a real valify_scope value.")


def run_parse_error_step(dry_run: bool) -> None:
    chain, system_instruction = _build_chain()
    print("Connecting to sheet...")
    ws = _open_sheet()

    print("Pulling appstore parse_error rows...")
    source_rows = _pull_parse_error_appstore(ws)
    print(f"Found {len(source_rows)} rows. (Expected 33)")

    if len(source_rows) == 0:
        print("No parse_error appstore rows found — nothing to do.")
        return

    if abs(len(source_rows) - 33) > 10:
        print(
            f"NOTE: expected ~33 but found {len(source_rows)}."
            " Review before proceeding. Continuing..."
        )

    print(f"\nRunning enrich_full_batch on {len(source_rows)} rows...")
    api_results = chain.enrich_full_batch(source_rows, system_instruction)
    print("Provider usage:", chain.provider_summary())
    merged = _merge_row_numbers(api_results, source_rows)

    _write_full_results(ws, merged, dry_run)
    print()
    _print_full_summary(merged)


def run_valify_scope_step(dry_run: bool) -> None:
    chain, system_instruction = _build_chain()
    print("Connecting to sheet...")
    ws = _open_sheet()

    print("Pulling rows with missing valify_scope...")
    source_rows = _pull_missing_valify_scope(ws)
    print(f"Found {len(source_rows)} rows missing valify_scope.")
    print(f"  (Expected ~87: ~60 appstore non-parse_error + ~27 play_store on-topic)")

    if len(source_rows) == 0:
        print("No rows need valify_scope — nothing to do.")
        return

    from collections import Counter
    by_source = Counter(r["source"] for r in source_rows)
    for src, cnt in sorted(by_source.items()):
        print(f"  {src}: {cnt}")

    print(f"\nRunning classify_batch on {len(source_rows)} rows...")
    api_results = chain.classify_batch(source_rows, system_instruction)
    print("Provider usage:", chain.provider_summary())
    merged = _merge_row_numbers(api_results, source_rows)

    _write_valify_scope_only(ws, merged, dry_run)
    print()
    _print_scope_summary(merged)


def main() -> None:
    parser = argparse.ArgumentParser(description="Post-Phase-8c recovery enrichment")
    parser.add_argument(
        "--step",
        choices=["parse-error", "valify-scope"],
        required=True,
        help=(
            "parse-error: full re-enrichment for 33 appstore parse_error rows. "
            "valify-scope: add valify_scope to rows with real enrichment but empty column Q."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify but do not write to sheet.",
    )
    args = parser.parse_args()

    if args.step == "parse-error":
        run_parse_error_step(dry_run=args.dry_run)
    elif args.step == "valify-scope":
        run_valify_scope_step(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
