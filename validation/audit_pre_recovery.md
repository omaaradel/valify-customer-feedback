# Pre-Recovery Audit — Feedback Log

**Generated:** 2026-06-15 22:17 UTC  
**Session:** Part B, no enrichment calls, no sheet writes.

---

## 1. Sheet Header Sanity

| Field | Value |
|-------|-------|
| Header column count | 17 |
| Column Q (index 16) | `valify_scope` |
| Header matches FEEDBACK_HEADERS | YES |

---

## 2. Overall Feedback Log Totals

**Total data rows:** 3353

### Per-source breakdown

| Source | Rows |
|--------|------|
| `play_store` | 3260 |
| `appstore` | 93 |

---

## 3. valify_scope State by Source

### `appstore` (93 rows)

| valify_scope | Count |
|-------------|-------|
| `(empty)` | 93 |

### `play_store` (3260 rows)

| valify_scope | Count |
|-------------|-------|
| `(empty)` | 3260 |

---

## 4. parse_error Rows

**Total parse_error rows:** 33  
(A row is counted if any of sentiment / feedback_type / product_area / severity equals `parse_error`)

| Source | parse_error rows |
|--------|-----------------|
| `appstore` | 33 |

> **CONFIRMED:** appstore parse_error count = 33 (expected 33).

---

## 5. Play Store On-Topic Rows (valify_scope = true)

**Count:** 0

### play_store valify_scope distribution

| valify_scope | Count |
|-------------|-------|
| `(empty)` | 3260 |

> All play_store valify_scope values were wiped to blank during the Phase 8c
> column-drop bug. Re-enrichment of valify_scope is queued for the next Gemini session.

---

## 6. Sentiment Distribution by Source

### `appstore`

| Sentiment | Count |
|-----------|-------|
| `negative` | 55 |
| `parse_error` | 33 |
| `positive` | 5 |

### `play_store`

| Sentiment | Count |
|-----------|-------|
| `negative` | 1626 |
| `positive` | 1483 |
| `neutral` | 110 |
| `mixed` | 41 |

---

## 7. Legacy Mixed-Sentiment Rows

**Total rows flagged as legacy mixed-sentiment:** 41

| Source | Count |
|--------|-------|
| `play_store` | 41 |

Sample sentiment values found:

- `mixed`

---

## 8. Quarantine Tab

**Quarantine row count:** 73

| Source | Count |
|--------|-------|
| `web_ddg` | 73 |

---

## 9. Summary Checklist

- [x] Header has 17 columns with valify_scope at Q
- [x] Total rows within expected range (3300–3400)
- [x] appstore row count == 93
- [x] appstore parse_error == 33
- [x] Quarantine tab has 73 rows
- [x] All play_store valify_scope values are empty (post-bug state)
