#!/usr/bin/env python3
"""
Phase 9 Groq Arabic quality test.

Selects up to 20 Arabic rows from the Feedback Log (on-topic preferred, filled
out with off-topic rows if fewer than 20 on-topic Arabic rows exist), runs each
through GeminiProvider and GroqProvider independently via classify_one_batch,
compares valify_scope and sentiment, and writes validation/groq_arabic_test.md.

Groq's free tier is geo-blocked from Egyptian IPs. If run locally from Cairo,
the Groq calls are expected to fail; this script records that, keeps the
Gemini-only results, and marks the comparison deferred to the first GitHub
Actions run (US servers, not geo-blocked). It never blocks on this.

Run from the repo root:
    python scripts/groq_arabic_test.py
"""
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
from enrichment.providers.base import ProviderQuotaError, ProviderUnavailableError
from enrichment.providers.gemini import GeminiProvider
from enrichment.providers.groq import GroqProvider

_SAMPLE_SIZE = 20
_MAX_RETRIES = 3
_RETRY_WAIT = 20.0
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VALIDATION_PATH = os.path.join(_PROJECT_ROOT, "validation", "groq_arabic_test.md")
_MATCH_THRESHOLD = 0.75


def _open_sheet():
    sa_b64 = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sa_info = json.loads(base64.b64decode(sa_b64))
    gc = gspread.service_account_from_dict(sa_info)
    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    return sh.worksheet("Feedback Log")


def _select_sample(ws) -> list:
    """Up to 20 Arabic rows: on-topic first, off-topic to fill the rest."""
    all_values = ws.get_all_values()
    header = all_values[0]

    def ci(name):
        return header.index(name) if name in header else None

    c_lang, c_ft, c_cli, c_src, c_raw = (
        ci("language"), ci("feedback_type"), ci("client_name"), ci("source"), ci("raw_text"),
    )

    def get(row, idx):
        return row[idx].strip() if idx is not None and idx < len(row) else ""

    on_topic_ar, off_topic_ar = [], []
    for row_idx, row in enumerate(all_values[1:], start=2):
        if get(row, c_lang) != "ar":
            continue
        item = {
            "row_id": str(row_idx),
            "client": get(row, c_cli),
            "source": get(row, c_src),
            "review_text": get(row, c_raw),
        }
        (off_topic_ar if get(row, c_ft) == "off_topic" else on_topic_ar).append(item)

    sample = on_topic_ar[:_SAMPLE_SIZE]
    if len(sample) < _SAMPLE_SIZE:
        sample += off_topic_ar[: _SAMPLE_SIZE - len(sample)]
    return sample, len(on_topic_ar)


def _classify_batch_with_retry(provider, batch, system_instruction) -> list:
    """Retries on transient ProviderUnavailableError (e.g. 503 high demand).
    Gives up immediately on ProviderQuotaError (won't recover soon). Returns
    [] if all attempts fail, never raises."""
    for attempt in range(_MAX_RETRIES):
        try:
            return provider.classify_one_batch(batch, system_instruction)
        except ProviderQuotaError as exc:
            print(f"  [{provider.name}] quota exhausted, giving up on this batch: {exc}")
            return []
        except ProviderUnavailableError as exc:
            if attempt < _MAX_RETRIES - 1:
                print(f"  [{provider.name}] transient error (attempt {attempt + 1}/{_MAX_RETRIES}), retrying in {_RETRY_WAIT:.0f}s: {exc}")
                time.sleep(_RETRY_WAIT)
            else:
                print(f"  [{provider.name}] still unavailable after {_MAX_RETRIES} attempts, giving up on this batch: {exc}")
                return []
        except Exception as exc:
            print(f"  [{provider.name}] unexpected error, giving up on this batch: {exc}")
            return []
    return []


def _classify_all(provider, sample, system_instruction) -> dict:
    """Returns {row_id: {"valify_scope": ..., "sentiment": ...}}, batches of 10.
    A batch that fails after retries is simply absent from the result."""
    results = {}
    for start in range(0, len(sample), 10):
        batch = sample[start : start + 10]
        parsed = _classify_batch_with_retry(provider, batch, system_instruction)
        for item in parsed:
            rid = str(item.get("row_id", ""))
            results[rid] = {
                "valify_scope": str(item.get("valify_scope", "")).lower(),
                "sentiment": str(item.get("sentiment", "")).lower(),
            }
    return results


def _write_report(sample, on_topic_count, gemini_results, groq_results, groq_error) -> dict:
    deferred = groq_error is not None
    rows_out = []
    scope_matches = 0
    sentiment_matches = 0
    compared = 0

    for item in sample:
        rid = item["row_id"]
        g = gemini_results.get(rid, {})
        q = groq_results.get(rid, {})
        row = {
            "row_id": rid,
            "preview": item["review_text"][:80].replace("|", "/"),
            "gemini_valify_scope": g.get("valify_scope", ""),
            "gemini_sentiment": g.get("sentiment", ""),
        }
        if deferred:
            row["groq_valify_scope"] = "n/a (deferred)"
            row["groq_sentiment"] = "n/a (deferred)"
            row["match"] = "n/a"
        else:
            row["groq_valify_scope"] = q.get("valify_scope", "")
            row["groq_sentiment"] = q.get("sentiment", "")
            scope_match = bool(g) and bool(q) and g.get("valify_scope") == q.get("valify_scope")
            sentiment_match = bool(g) and bool(q) and g.get("sentiment") == q.get("sentiment")
            if g and q:
                compared += 1
                if scope_match:
                    scope_matches += 1
                if sentiment_match:
                    sentiment_matches += 1
            row["match"] = "yes" if (scope_match and sentiment_match) else "no"
        rows_out.append(row)

    scope_rate = (scope_matches / compared) if compared else 0.0
    sentiment_rate = (sentiment_matches / compared) if compared else 0.0
    confirmed = (not deferred) and compared > 0 and scope_rate > _MATCH_THRESHOLD and sentiment_rate > _MATCH_THRESHOLD

    lines = [
        "# Groq Arabic quality test",
        "",
        f"Sample size: {len(sample)} Arabic rows ({on_topic_count} on-topic Arabic rows available, "
        f"{max(0, len(sample) - on_topic_count)} off-topic rows used to fill the sample).",
        "",
    ]

    if deferred:
        lines += [
            f"Groq unreachable: {groq_error}",
            "",
            "Result: deferred to the first GitHub Actions run. Groq's free tier is geo-blocked from "
            "Egyptian IPs, so this local run recorded Gemini results only. Groq is not yet confirmed "
            "or rejected as a production fallback; re-run this script from GitHub Actions (workflow_dispatch) "
            "to get a real comparison before relying on Groq in production.",
            "",
        ]
        gemini_missing = len(sample) - len(gemini_results)
        if gemini_missing:
            lines += [
                f"Note: Gemini also did not return a result for {gemini_missing}/{len(sample)} rows this run "
                "(see console output for per-batch errors; typically transient 503 high-demand responses or, "
                "after enough retries, a daily free-tier quota limit). This is separate from the Groq "
                "geo-block above and usually resolves on its own or after the daily quota resets.",
                "",
            ]
    else:
        lines += [
            f"Rows compared (both providers returned a result): {compared}/{len(sample)}",
            f"valify_scope match: {scope_matches}/{compared} ({scope_rate:.0%})",
            f"sentiment match: {sentiment_matches}/{compared} ({sentiment_rate:.0%})",
            "",
            f"Result: {'CONFIRMED' if confirmed else 'NOT CONFIRMED'} as production fallback "
            f"(threshold: over {_MATCH_THRESHOLD:.0%} on both fields).",
            "",
        ]
        if not confirmed:
            lines += [
                "Groq did not meet the match-rate threshold. Next step: evaluate Ollama with "
                "Qwen2.5 or Aya-23 as the fallback provider instead of Groq.",
                "",
            ]

    lines += [
        "| row_id | preview | gemini_valify_scope | groq_valify_scope | gemini_sentiment | groq_sentiment | match |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows_out:
        lines.append(
            f"| {row['row_id']} | {row['preview']} | {row['gemini_valify_scope']} | "
            f"{row['groq_valify_scope']} | {row['gemini_sentiment']} | {row['groq_sentiment']} | {row['match']} |"
        )

    os.makedirs(os.path.dirname(_VALIDATION_PATH), exist_ok=True)
    with open(_VALIDATION_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return {
        "deferred": deferred,
        "compared": compared,
        "scope_matches": scope_matches,
        "sentiment_matches": sentiment_matches,
        "scope_rate": scope_rate,
        "sentiment_rate": sentiment_rate,
        "confirmed": confirmed,
    }


def main() -> None:
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not gemini_key:
        print("GEMINI_API_KEY not set. Cannot run test.")
        sys.exit(1)

    system_instruction = build_system_instruction()
    print("Connecting to sheet...")
    ws = _open_sheet()

    print("Selecting Arabic sample...")
    sample, on_topic_count = _select_sample(ws)
    print(f"Selected {len(sample)} Arabic rows ({on_topic_count} on-topic Arabic rows available).")
    if not sample:
        print("No Arabic rows found. Cannot run test.")
        sys.exit(1)

    print(f"Running GeminiProvider.classify_one_batch on {len(sample)} rows...")
    gemini_results = _classify_all(GeminiProvider(gemini_key), sample, system_instruction)
    print(f"Gemini returned {len(gemini_results)} results.")

    groq_results = {}
    groq_error = None
    if not groq_key:
        groq_error = "GROQ_API_KEY not set"
        print("GROQ_API_KEY not set, skipping Groq.")
    else:
        try:
            print(f"Running GroqProvider.classify_one_batch on {len(sample)} rows...")
            groq_results = _classify_all(GroqProvider(groq_key), sample, system_instruction)
            print(f"Groq returned {len(groq_results)} results.")
        except Exception as exc:
            groq_error = str(exc)
            print(f"Groq unreachable or failed: {groq_error}")

        # _classify_all catches per-batch errors internally (retries, then gives
        # up) rather than raising, so a fully failed run surfaces as an empty
        # dict, not an exception. Treat that the same as an explicit failure:
        # there is nothing to compare, so this must be reported as deferred,
        # not as "Groq ran and scored 0%".
        if not groq_error and not groq_results:
            groq_error = (
                "Groq returned 0 results across all batches (see per-batch errors "
                "printed above; likely geo-blocked from this environment, consistent "
                "with the Groq geo-blocking note in docs/HANDOFF.md)"
            )

    summary = _write_report(sample, on_topic_count, gemini_results, groq_results, groq_error)
    print()
    print(f"Report written to validation/groq_arabic_test.md")
    if summary["deferred"]:
        print("Groq comparison deferred (Groq unreachable from this environment).")
    else:
        print(
            f"valify_scope match: {summary['scope_matches']}/{summary['compared']} "
            f"({summary['scope_rate']:.0%}), sentiment match: {summary['sentiment_matches']}/{summary['compared']} "
            f"({summary['sentiment_rate']:.0%})"
        )
        print(f"Confirmed as production fallback: {summary['confirmed']}")


if __name__ == "__main__":
    main()
