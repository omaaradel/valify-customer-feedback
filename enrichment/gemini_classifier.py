"""
Gemini Flash classifier for Phase 8 enrichment.

Two entry points:
  classify_batch(rows, api_key)  -- valify_scope + sentiment only (for re-enriching existing rows)
  enrich_full_batch(rows, api_key) -- all 7 enrichment fields (for new unenriched rows)

The system instruction is built at runtime from docs/enrichment.md, docs/enrichment_hints.md,
and docs/enrichment_taxonomy.md so the docs remain the single source of truth.
"""
import json
import os
import random
import time
import urllib.request
import urllib.error

from dotenv import load_dotenv

_MODEL = "gemini-3.5-flash"
_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + _MODEL
    + ":generateContent"
)
_BATCH_SIZE = 10
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_doc(relative_path: str) -> str:
    full_path = os.path.join(_PROJECT_ROOT, relative_path)
    with open(full_path, encoding="utf-8") as f:
        return f.read()


def get_api_key() -> str:
    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not found in .env. Add it before running Phase 8 enrichment."
        )
    return key


def build_system_instruction() -> str:
    enrichment_md = _read_doc("docs/enrichment.md")
    hints_md = _read_doc("docs/enrichment_hints.md")
    taxonomy_md = _read_doc("docs/enrichment_taxonomy.md")
    return (
        "You are a classification assistant for Valify Analytics, an identity verification vendor "
        "operating in Egypt.\n\n"
        "Your job is to read app store and web reviews about Valify's clients and classify each review "
        "according to the rules and field definitions below.\n\n"
        "--- PROJECT CONTEXT AND RULES ---\n\n"
        + enrichment_md
        + "\n\n--- SIGNAL HINTS AND DETECTION EXAMPLES ---\n\n"
        + hints_md
        + "\n\n--- FIELD TAXONOMY AND ALLOWED VALUES ---\n\n"
        + taxonomy_md
    )


def _parse_retry_after(body: str) -> float:
    """Extract suggested retry seconds from a 429 error body."""
    import re
    m = re.search(r"retry in (\d+\.?\d*)\s*s", body, re.IGNORECASE)
    if m:
        return float(m.group(1)) + 2.0  # add 2s buffer
    return 65.0  # default: 65s if we cannot parse


def _call_api(system_instruction: str, user_content: str, api_key: str) -> str:
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": user_content}]}],
        "generationConfig": {"temperature": 0.0},
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url = _API_URL + "?key=" + api_key
    last_exc = None
    max_attempts = 5
    for attempt in range(max_attempts):
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503, 500):
                body = exc.read().decode("utf-8", errors="replace")
                last_exc = exc
                if attempt < max_attempts - 1:
                    wait = _parse_retry_after(body) if exc.code == 429 else (15 * (attempt + 1))
                    print(f"[gemini_classifier] HTTP {exc.code}, retry {attempt+1}/{max_attempts-1} after {wait:.0f}s...")
                    time.sleep(wait)
                continue
            raise
    raise last_exc


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(inner).strip()
    return text


def _scope_error_rows(row_ids: list) -> list:
    # sentiment is intentionally omitted so the caller does not overwrite existing values
    return [
        {"row_id": rid, "valify_scope": "parse_error"}
        for rid in row_ids
    ]


def _full_error_rows(row_ids: list) -> list:
    return [
        {
            "row_id": rid,
            "sentiment": "parse_error",
            "feedback_type": "parse_error",
            "product_area": "parse_error",
            "severity": "parse_error",
            "agreement_signal": False,
            "claude_summary": "enrichment_failed",
            "valify_scope": "parse_error",
        }
        for rid in row_ids
    ]


def classify_batch(rows: list, api_key: str) -> list:
    """
    Classify valify_scope and sentiment for a list of row dicts.
    Each row must have: row_id, client, source, review_text.
    Returns list of {row_id, valify_scope, sentiment}.
    At most _BATCH_SIZE rows per API call.
    """
    system_instruction = build_system_instruction()
    results = []

    for i in range(0, len(rows), _BATCH_SIZE):
        if i > 0:
            time.sleep(6)  # raised from 4s: stay clear of the 15 RPM free-tier ceiling
        batch = rows[i: i + _BATCH_SIZE]
        row_ids = [r["row_id"] for r in batch]

        prompt = (
            "Classify the following reviews. For each review, determine two fields:\n"
            "  valify_scope: true / false / unsure\n"
            "  sentiment: positive / negative / neutral\n\n"
            "Rules:\n"
            "- Base valify_scope on the ACTION described, not on whether Valify is named.\n"
            "- Users never mention Valify by name. Detect by what the user did or was asked to do.\n"
            "- Understand Egyptian Arabic dialect, Modern Standard Arabic, and English natively.\n"
            "  Do not translate. Classify in the language the review is written in.\n"
            "- Sentiment applies to any review regardless of valify_scope value.\n"
            "- Return ONLY a valid JSON array. No preamble. No explanation. No markdown fences.\n"
            "- Each element: {\"row_id\": \"...\", \"valify_scope\": \"...\", \"sentiment\": \"...\"}\n\n"
            "Reviews to classify:\n"
            + json.dumps(batch, ensure_ascii=False)
        )

        try:
            raw = _call_api(system_instruction, prompt, api_key)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"[gemini_classifier] HTTP {exc.code}: {body[:500]}")
            results.extend(_scope_error_rows(row_ids))
            continue
        except Exception as exc:
            print(f"[gemini_classifier] API error: {exc}")
            results.extend(_scope_error_rows(row_ids))
            continue

        try:
            outer = json.loads(raw)
            text = _strip_fences(outer["candidates"][0]["content"]["parts"][0]["text"])
            batch_results = json.loads(text)
        except Exception as exc:
            print(f"[gemini_classifier] Parse error: {exc}")
            print(f"[gemini_classifier] Raw response (first 2000 chars): {raw[:2000]}")
            batch_results = _scope_error_rows(row_ids)

        results.extend(batch_results)

    return results


def enrich_full_batch(rows: list, api_key: str) -> list:
    """
    Full enrichment: all 7 enrichment fields for unenriched rows.
    Each row must have: row_id, client, source, review_text.
    Returns list of dicts with all enrichment fields.
    """
    system_instruction = build_system_instruction()
    results = []

    for i in range(0, len(rows), _BATCH_SIZE):
        if i > 0:
            time.sleep(6)  # raised from 4s: stay clear of the 15 RPM free-tier ceiling
        batch = rows[i: i + _BATCH_SIZE]
        row_ids = [r["row_id"] for r in batch]

        prompt = (
            "Classify the following reviews. For each review, return all 7 enrichment fields.\n\n"
            "Fields to return for each review:\n"
            "  sentiment: positive / negative / neutral\n"
            "  feedback_type: bug / ux_friction / feature_request / compliment / off_topic\n"
            "  product_area: nid_verification / liveness_detection / facematch / onboarding_general / other\n"
            "  severity: critical / high / medium / low / none\n"
            "  agreement_signal: true / false\n"
            "  claude_summary: one sentence in English, max 200 characters\n"
            "  valify_scope: true / false / unsure\n\n"
            "Rules:\n"
            "- Base valify_scope on the ACTION described, not on whether Valify is named.\n"
            "- Users never mention Valify by name. Detect by what the user did or was asked to do.\n"
            "- Understand Egyptian Arabic dialect, Modern Standard Arabic, and English natively.\n"
            "  Do not translate. Classify in the language the review is written in.\n"
            "- For off_topic rows: severity = none, product_area = other, valify_scope = false.\n"
            "- agreement_signal is true only if the review text itself contains phrases like\n"
            "  'same here', 'me too', 'نفس المشكلة', 'أنا كمان' or explicit third-party confirmation.\n"
            "- For web_ddg source rows: these are web search snippets, often vague. Use 'unsure' for\n"
            "  valify_scope when the snippet does not clearly describe the ID capture step.\n"
            "- Return ONLY a valid JSON array. No preamble. No explanation. No markdown fences.\n"
            "- Each element must have all 7 fields plus row_id.\n\n"
            "Reviews to classify:\n"
            + json.dumps(batch, ensure_ascii=False)
        )

        try:
            raw = _call_api(system_instruction, prompt, api_key)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"[gemini_classifier] HTTP {exc.code}: {body[:500]}")
            results.extend(_full_error_rows(row_ids))
            continue
        except Exception as exc:
            print(f"[gemini_classifier] API error: {exc}")
            results.extend(_full_error_rows(row_ids))
            continue

        try:
            outer = json.loads(raw)
            text = _strip_fences(outer["candidates"][0]["content"]["parts"][0]["text"])
            batch_results = json.loads(text)
        except Exception as exc:
            print(f"[gemini_classifier] Parse error (full): {exc}")
            print(f"[gemini_classifier] Raw response (first 2000 chars): {raw[:2000]}")
            batch_results = _full_error_rows(row_ids)

        results.extend(batch_results)

    return results
