# Enrichment Prompt — Paste into a fresh Claude Code session

> **How to use:** Copy everything below the horizontal rule into a new Claude Code
> conversation opened in the project folder. Claude will load context, classify all
> unenriched rows, write them back to the Sheet, and report a summary.

---

You are classifying user feedback for **Valify Analytics**, an Egyptian
identity-verification company.

## Step 0 — Load context (do this before anything else)

Read the following three files now and keep their contents in context for the
entire session:

1. Read `docs/enrichment.md` — per-client use cases, keyword guidance, sentiment rules
2. Read `docs/enrichment_taxonomy.md` — all field definitions and allowed values
3. Read `docs/enrichment_hints.md` — per-client signal phrases and edge-case guidance

For any item you find ambiguous during classification, also read
`docs/enrichment_examples.md` — it has six labelled examples covering implicit
relevance, positive feedback, suggestions, off-topic, liveness, and mixed sentiment.

## Two rules to apply throughout

**Keywords are contextual hints, not filters.** The keyword sets in `keywords.py`
tell you what kind of language to watch for, but a review can be highly relevant with
zero literal keyword matches. Classify based on meaning, not string overlap.

**Sentiment is neutral on direction.** Capture positive, negative, neutral, and
suggestion feedback with equal fidelity. Do not bias toward complaints. A user
saying *"التحقق كان سهل وسريع"* is signal — it tells product what is working.

---

## Step 1 — Export unenriched rows

```bash
python scripts/export_pending.py
```

If the output says "0 unenriched rows", stop here.

---

## Step 2 — Read pending.json

Read `pending.json`. Each entry:

```json
{
  "row_number": 2,
  "client_name": "Amazon",
  "source": "play_store",
  "post_date": "2026-04-15T09:22:00+00:00",
  "raw_text": "...",
  "rating": 1,
  "language": "en"
}
```

---

## Step 3 — Classify every item

Using the field definitions from `docs/enrichment_taxonomy.md` and the per-client
context from `docs/enrichment_hints.md`, classify each item:

```json
{
  "row_number": <same integer from input — do not change>,
  "sentiment": "positive" | "negative" | "neutral" | "mixed",
  "feedback_type": "bug" | "ux_friction" | "feature_request" | "compliment" | "off_topic",
  "product_area": "nid_verification" | "liveness_detection" | "facematch" | "onboarding_general" | "other",
  "severity": "critical" | "high" | "medium" | "low" | "none",
  "agreement_signal": true | false,
  "claude_summary": "<one English sentence, max 200 chars>"
}
```

`agreement_signal` is `false` for all `play_store` and `app_store` rows (no comments
available). Set to `true` only for `reddit` or `facebook` source rows where replies
explicitly confirm the same problem ("same here", "me too", "نفس المشكلة").

For any item that seems ambiguous, read `docs/enrichment_examples.md` before deciding.

---

## Step 4 — Write enriched.json

Write a JSON array to `enriched.json` in the repo root. One object per item from
`pending.json`. Preserve `row_number` exactly — it is the sheet row to update.

```json
[
  {
    "row_number": 2,
    "sentiment": "negative",
    "feedback_type": "bug",
    "product_area": "nid_verification",
    "severity": "critical",
    "agreement_signal": false,
    "claude_summary": "ID scan repeatedly fails after multiple attempts during account opening."
  }
]
```

---

## Step 5 — Write back to the Sheet

```bash
python scripts/import_enriched.py
```

---

## Step 6 — Report summary

```
Enriched N rows. M off-topic. K critical. J high.
```

Then list every `critical` item: `row_number`, `client_name`, `claude_summary`.
These need immediate attention from the account team.
