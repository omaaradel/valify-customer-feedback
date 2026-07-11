#!/usr/bin/env python3
"""
Phase 8 enrichment runner.

Two modes:
  --mode scope-only   Re-enrich already-classified rows with valify_scope + sentiment.
                      Targets rows where sentiment is set and feedback_type is not off_topic.
                      Expected count: ~27 rows from Phases 4-6.

  --mode full         Full enrichment for any row with no sentiment yet (any source).
                      Originally targeted unenriched web_ddg rows only (Phase 7, ~73 rows);
                      broadened in Phase 9 so it also covers newly-scraped play_store and
                      appstore rows from the daily automation pipeline. web_ddg is retired
                      and disabled, so this now effectively targets same-day new rows.

Run from the repo root:
  python scripts/enrich_phase8.py --mode scope-only
  python scripts/enrich_phase8.py --mode full
  python scripts/enrich_phase8.py --mode scope-only --dry-run
"""
import argparse
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import gspread

from enrichment.gemini_classifier import build_system_instruction
from enrichment.provider_chain import ProviderChain, build_default_providers


def _col_letter(n: int) -> str:
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


# Column positions (1-indexed) in Feedback Log
_COL_SENTIMENT = 9
_COL_FEEDBACK_TYPE = 10
_COL_PRODUCT_AREA = 11
_COL_SEVERITY = 12
_COL_AGREEMENT_SIGNAL = 14
_COL_CLAUDE_SUMMARY = 15
_COL_VALIFY_SCOPE = 17

_SCOPE_COLS = {
    "sentiment": _COL_SENTIMENT,
    "valify_scope": _COL_VALIFY_SCOPE,
}

_FULL_COLS = {
    "sentiment": _COL_SENTIMENT,
    "feedback_type": _COL_FEEDBACK_TYPE,
    "product_area": _COL_PRODUCT_AREA,
    "severity": _COL_SEVERITY,
    "agreement_signal": _COL_AGREEMENT_SIGNAL,
    "claude_summary": _COL_CLAUDE_SUMMARY,
    "valify_scope": _COL_VALIFY_SCOPE,
}


def _build_chain() -> tuple:
    """Build a ProviderChain using the standard provider order (Gemini, then
    Groq and OpenRouter if their keys are set). See
    enrichment.provider_chain.build_default_providers."""
    providers = build_default_providers()
    return ProviderChain(providers), build_system_instruction()


def _ensure_valify_scope_header(ws) -> None:
    headers = ws.row_values(1)
    if len(headers) < _COL_VALIFY_SCOPE or headers[_COL_VALIFY_SCOPE - 1] != "valify_scope":
        ws.update(f"{_col_letter(_COL_VALIFY_SCOPE)}1", [["valify_scope"]])
        print("[enrich_phase8] Added 'valify_scope' header to column Q.")


def _open_sheet():
    sa_b64 = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sa_info = json.loads(base64.b64decode(sa_b64))
    gc = gspread.service_account_from_dict(sa_info)
    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    return sh.worksheet("Feedback Log")


def _pull_scope_only_rows(ws) -> list:
    """Rows that are enriched (sentiment set) and not off_topic."""
    all_values = ws.get_all_values()
    if len(all_values) < 2:
        return []
    header = all_values[0]
    col_sentiment = header.index("sentiment") if "sentiment" in header else None
    col_feedback_type = header.index("feedback_type") if "feedback_type" in header else None
    col_client = header.index("client_name") if "client_name" in header else None
    col_source = header.index("source") if "source" in header else None
    col_raw_text = header.index("raw_text") if "raw_text" in header else None

    rows = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        row = row + [""] * (max(len(header), _COL_VALIFY_SCOPE) - len(row))
        sentiment = row[col_sentiment] if col_sentiment is not None else ""
        feedback_type = row[col_feedback_type] if col_feedback_type is not None else ""
        valify_scope_val = row[_COL_VALIFY_SCOPE - 1] if len(row) >= _COL_VALIFY_SCOPE else ""

        # Backfill only: skip rows that already carry a real valify_scope value.
        # "parse_error" is a leftover failed-classification marker, not a real value.
        is_missing = (not valify_scope_val) or (valify_scope_val == "parse_error")
        if sentiment and feedback_type != "off_topic" and is_missing:
            rows.append({
                "row_id": str(row_idx),
                "row_number": row_idx,
                "client": row[col_client] if col_client is not None else "",
                "source": row[col_source] if col_source is not None else "",
                "review_text": row[col_raw_text] if col_raw_text is not None else "",
                "existing_valify_scope": valify_scope_val,
            })
    return rows


def _pull_unenriched_rows(ws) -> list:
    """Rows where sentiment is empty or parse_error, any source. Used both for the
    one-time Phase 7 web_ddg backlog and for newly-scraped rows in the Phase 9
    daily automation pipeline."""
    all_values = ws.get_all_values()
    if len(all_values) < 2:
        return []
    header = all_values[0]
    col_sentiment = header.index("sentiment") if "sentiment" in header else None
    col_source = header.index("source") if "source" in header else None
    col_client = header.index("client_name") if "client_name" in header else None
    col_raw_text = header.index("raw_text") if "raw_text" in header else None

    rows = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        row = row + [""] * (max(len(header), _COL_VALIFY_SCOPE) - len(row))
        sentiment = row[col_sentiment] if col_sentiment is not None else ""
        source = row[col_source] if col_source is not None else ""

        if not sentiment or sentiment == "parse_error":
            rows.append({
                "row_id": str(row_idx),
                "row_number": row_idx,
                "client": row[col_client] if col_client is not None else "",
                "source": source,
                "review_text": row[col_raw_text] if col_raw_text is not None else "",
            })
    return rows


def _write_scope_results(ws, results: list, dry_run: bool) -> None:
    updates = []
    for item in results:
        row = item["row_number"]
        for field, col in _SCOPE_COLS.items():
            val = item.get(field)
            if val is None:
                continue  # parse_error path: do not overwrite existing value
            updates.append({"range": f"{_col_letter(col)}{row}", "values": [[val]]})
    if dry_run:
        print(f"[DRY RUN] Would write {len(updates)} cell updates.")
        for u in updates[:10]:
            print(f"  {u['range']}: {u['values'][0][0]}")
        if len(updates) > 10:
            print(f"  ... and {len(updates) - 10} more")
    else:
        if updates:
            ws.batch_update(updates)


def _write_full_results(ws, results: list, dry_run: bool) -> None:
    updates = []
    for item in results:
        row = item["row_number"]
        for field, col in _FULL_COLS.items():
            val = item.get(field, "")
            if isinstance(val, bool):
                val = str(val).lower()
            updates.append({"range": f"{_col_letter(col)}{row}", "values": [[val]]})
    if dry_run:
        print(f"[DRY RUN] Would write {len(updates)} cell updates.")
        for u in updates[:10]:
            print(f"  {u['range']}: {u['values'][0][0]}")
        if len(updates) > 10:
            print(f"  ... and {len(updates) - 10} more")
    else:
        if updates:
            ws.batch_update(updates)


def _tally_counts(results: list) -> tuple:
    scope_counts = {}
    sentiment_counts = {}
    for r in results:
        vs = r.get("valify_scope", "")
        s = r.get("sentiment", "")
        scope_counts[vs] = scope_counts.get(vs, 0) + 1
        sentiment_counts[s] = sentiment_counts.get(s, 0) + 1
    return scope_counts, sentiment_counts


def _print_scope_summary(results: list) -> None:
    total = len(results)
    scope_counts, sentiment_counts = _tally_counts(results)

    print(f"\nTotal rows processed: {total}")
    print("valify_scope breakdown:")
    for k in ("true", "false", "unsure", "parse_error"):
        if k in scope_counts:
            print(f"  {k}: {scope_counts[k]}")
    print("sentiment breakdown:")
    for k in ("positive", "negative", "neutral", "parse_error"):
        if k in sentiment_counts:
            print(f"  {k}: {sentiment_counts[k]}")

    true_count = scope_counts.get("true", 0)
    if true_count >= 20:
        print(
            f"\nSANITY CHECK FAILED: valify_scope=true count is {true_count}, which is >= 20."
            " The system instruction may be too loose. Investigate before proceeding."
        )
    elif true_count < 8:
        print(
            f"\nNOTE: valify_scope=true count is {true_count}, below expected range of 8-14."
            " Check if the system instruction is too strict."
        )
    else:
        print(f"\nSanity check passed: valify_scope=true count {true_count} is in range 8-14.")


def _print_full_summary(results: list) -> None:
    total = len(results)
    scope_counts, sentiment_counts = _tally_counts(results)

    print(f"\nTotal rows processed: {total}")
    print("valify_scope breakdown:")
    for k in ("true", "false", "unsure", "parse_error"):
        if k in scope_counts:
            print(f"  {k}: {scope_counts[k]}")
    print("sentiment breakdown:")
    for k in ("positive", "negative", "neutral", "parse_error"):
        if k in sentiment_counts:
            print(f"  {k}: {sentiment_counts[k]}")

    unsure_count = scope_counts.get("unsure", 0)
    if total > 0 and unsure_count / total > 0.5:
        print(
            f"\nFLAG: unsure rate is {unsure_count}/{total} ({100*unsure_count//total}%),"
            " which exceeds 50%. Web results are vague by nature, but this rate is high."
            " Review a sample before accepting."
        )


def _merge_row_numbers(api_results: list, source_rows: list) -> list:
    """Map row_number from source_rows back into api_results by row_id."""
    id_to_num = {str(r["row_number"]): r["row_number"] for r in source_rows}
    for item in api_results:
        item["row_number"] = id_to_num.get(str(item.get("row_id", "")), None)
    return [r for r in api_results if r["row_number"] is not None]


def run_scope_only(dry_run: bool = False) -> dict:
    chain, system_instruction = _build_chain()
    print("Connecting to sheet...")
    ws = _open_sheet()
    _ensure_valify_scope_header(ws)

    print("Pulling on-topic enriched rows...")
    source_rows = _pull_scope_only_rows(ws)
    print(f"Found {len(source_rows)} on-topic enriched rows.")
    if len(source_rows) == 0:
        print("No rows to process.")
        return {"total": 0, "valify_scope": {}, "sentiment": {}, "skipped": 0}
    if abs(len(source_rows) - 27) > 15:
        print(
            f"NOTE: Expected ~27 rows but found {len(source_rows)}."
            " Review this count before proceeding."
        )

    print(f"Running classify_batch on {len(source_rows)} rows...")
    api_results = chain.classify_batch(source_rows, system_instruction)
    print("Provider usage:", chain.provider_summary())
    merged = _merge_row_numbers(api_results, source_rows)

    if not dry_run:
        print("Writing results to sheet...")
    _write_scope_results(ws, merged, dry_run)
    if not dry_run:
        print("Done.")

    _print_scope_summary(merged)
    scope_counts, sentiment_counts = _tally_counts(merged)
    skipped = len(source_rows) - len(merged)
    return {
        "total": len(merged),
        "valify_scope": scope_counts,
        "sentiment": sentiment_counts,
        "skipped": skipped,
    }


def run_full(dry_run: bool = False) -> dict:
    chain, system_instruction = _build_chain()
    print("Connecting to sheet...")
    ws = _open_sheet()
    _ensure_valify_scope_header(ws)

    print("Pulling unenriched rows (any source)...")
    source_rows = _pull_unenriched_rows(ws)
    print(f"Found {len(source_rows)} unenriched rows.")
    if len(source_rows) == 0:
        print("No rows to process.")
        return {"total": 0, "valify_scope": {}, "sentiment": {}, "skipped": 0}

    print(f"Running enrich_full_batch on {len(source_rows)} rows...")
    api_results = chain.enrich_full_batch(source_rows, system_instruction)
    print("Provider usage:", chain.provider_summary())
    merged = _merge_row_numbers(api_results, source_rows)

    if not dry_run:
        print("Writing results to sheet...")
    _write_full_results(ws, merged, dry_run)
    if not dry_run:
        print("Done.")

    _print_full_summary(merged)
    scope_counts, sentiment_counts = _tally_counts(merged)
    skipped = len(source_rows) - len(merged)
    return {
        "total": len(merged),
        "valify_scope": scope_counts,
        "sentiment": sentiment_counts,
        "skipped": skipped,
    }


def run_smoke_test() -> None:
    """Pull 3 rows (mix of Arabic and English), send through GeminiProvider, print raw + parsed."""
    import enrichment.gemini_classifier as _gc
    api_key = _gc.get_api_key()
    print("Connecting to sheet for smoke test...")
    ws = _open_sheet()

    all_values = ws.get_all_values()
    header = all_values[0]
    col_sentiment = header.index("sentiment") if "sentiment" in header else None
    col_source = header.index("source") if "source" in header else None
    col_client = header.index("client_name") if "client_name" in header else None
    col_raw_text = header.index("raw_text") if "raw_text" in header else None
    col_lang = header.index("language") if "language" in header else None

    ar_rows = []
    en_rows = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        row = row + [""] * (len(header) - len(row))
        lang = row[col_lang] if col_lang is not None else ""
        sentiment = row[col_sentiment] if col_sentiment is not None else ""
        if not sentiment:
            continue
        r = {
            "row_id": str(row_idx),
            "row_number": row_idx,
            "client": row[col_client] if col_client is not None else "",
            "source": row[col_source] if col_source is not None else "",
            "review_text": row[col_raw_text] if col_raw_text is not None else "",
        }
        if lang == "ar" and len(ar_rows) < 2:
            ar_rows.append(r)
        elif lang == "en" and len(en_rows) < 1:
            en_rows.append(r)
        if len(ar_rows) >= 2 and len(en_rows) >= 1:
            break

    sample = (ar_rows + en_rows)[:3]
    if not sample:
        print("Could not find suitable rows for smoke test.")
        return

    print(f"\nSmoke test: sending {len(sample)} rows to Gemini...")
    for r in sample:
        preview = r['review_text'][:80].encode("ascii", errors="replace").decode()
        print(f"  row {r['row_id']}: client={r['client']} source={r['source']} text={preview!r}")

    from enrichment.providers.gemini import GeminiProvider
    from enrichment.providers.base import classify_prompt

    provider = GeminiProvider(api_key)
    sys_instr = build_system_instruction()

    print(f"\nSmoke test: sending {len(sample)} rows to Gemini...")
    for r in sample:
        preview = r['review_text'][:80].encode("ascii", errors="replace").decode()
        print(f"  row {r['row_id']}: client={r['client']} source={r['source']} text={preview!r}")

    raw_response = provider._call_api(sys_instr, classify_prompt(sample))
    print("\n--- RAW API RESPONSE ---")
    print(raw_response[:3000])
    results = provider._parse(raw_response)
    print("\n--- PARSED RESULT ---")
    print(json.dumps(results, ensure_ascii=True, indent=2))
    print("\nSmoke test complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 8 Gemini enrichment runner")
    parser.add_argument(
        "--mode",
        choices=["scope-only", "full", "smoke-test"],
        required=True,
        help=(
            "scope-only: re-enrich existing rows with valify_scope + sentiment. "
            "full: full enrichment for unenriched web_ddg rows. "
            "smoke-test: send 3 sample rows to Gemini and print result."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run classification but do not write to sheet.",
    )
    args = parser.parse_args()

    if args.mode == "smoke-test":
        run_smoke_test()
    elif args.mode == "scope-only":
        run_scope_only(dry_run=args.dry_run)
    elif args.mode == "full":
        run_full(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
