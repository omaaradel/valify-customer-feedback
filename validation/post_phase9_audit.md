# Post Phase 9 audit

Read-only audit of the Feedback Log after Module 4 (process unenriched rows), run 2026-07-11
against workflow_dispatch run 29157839249. This audit was taken after the local repo was
fast-forwarded to the workflow's own commit (5af4b58), so backups and data/feedback.json in
this repo match the sheet state at audit time.

## Enrichment run that closed the backlog

Found 15 unenriched rows (down from 153 reported when the Phase 9 follow-up modules started,
most of the earlier backlog was already cleared by an intermediate run during Module 2 and 3
testing). All 15 processed successfully via Gemini in 2 batches, no fallback needed, so Groq
and OpenRouter were not exercised by this particular run. The workflow's "Enrich retry (if
needed)" step (Module 3) then found 0 unenriched rows, confirming nothing was left.

## Sheet totals

Total rows in Feedback Log: 3,515 (up from 3,353 at the last full audit, 2026-07-05, from
several days of live daily scraping since Phase 9 went live).

Source breakdown:
| Source | Count |
|---|---|
| play_store | 3,422 |
| appstore | 93 |

Sentiment breakdown (whole sheet):
| Value | Count |
|---|---|
| negative | 1,809 |
| positive | 1,547 |
| neutral | 118 |
| mixed | 41 (legacy, pre-Phase-8 taxonomy, unchanged, not re-classified) |

Feedback type breakdown (whole sheet):
| Value | Count |
|---|---|
| off_topic | 3,482 |
| ux_friction | 19 |
| bug | 12 |
| compliment | 2 |

## Required checks

| Check | Result |
|---|---|
| Rows with blank sentiment | 0 |
| Rows with "parse_error" in any enrichment field (sentiment, feedback_type, or valify_scope) | 0 |
| On-topic rows (feedback_type not off_topic) missing valify_scope | 0 |

No unenriched rows remain. No row IDs to list.

## valify_scope breakdown

On-topic rows only (feedback_type not off_topic, 33 rows total):
| Value | Count |
|---|---|
| true | 14 |
| false | 13 |
| unsure | 6 |

Whole-sheet valify_scope column (for reference): true=14, false=204, unsure=6, blank=3,291.
The 204 false values include both the 13 on-topic false rows above and 191 off-topic rows:
full-mode enrichment (`scripts/enrich_phase8.py` `run_full`, used for all rows scraped since
Phase 9) writes all 7 fields for every row it processes, including off-topic ones, and the
classification rule forces valify_scope=false for off_topic rows. This is expected, not a bug,
it is a different rule path than the old scope-only backfill that only ever touched on-topic
rows. The 3,291 blank valify_scope rows are the pre-Phase-9 historical backlog (play_store rows
scraped before daily full-mode enrichment covered every new row), unchanged from the 2026-07-05
audit, they were off_topic and never targeted for column-Q backfill by design; this is the
intended end state, not a gap.

## Conclusion

The sheet is clean as of this audit. No unenriched rows, no parse_error rows, no on-topic rows
missing valify_scope. OpenRouter's real-world behavior as a fallback is still unconfirmed by
live evidence, this run never needed to fall through past Gemini.
