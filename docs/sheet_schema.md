# Google Sheet Schema

## Sheet structure

One Google Sheet with **three tabs:**
- **Feedback Log** — one row per feedback item (append-only)
- **Admin** — one row per client (Claude Code maintains)
- **seen_hashes** — deduplication registry (one hash per row, no headers)

Share the sheet with the Google service account email address
(found in the service account JSON) with **Editor** access.

---

## Tab 1 — "Feedback Log"

### Column Definitions

| Col | Name | Type | Allowed Values / Notes |
|-----|------|------|------------------------|
| A | `client_name` | string | Display name: `Amazon`, `Thndr`, `Klivvr`, `Rabbit`, `ADIB`, `Midbank`, `Raya`, `Khazna` |
| B | `post_url` | string | Full URL to the review/post. For Play Store reviews, constructed as `https://play.google.com/store/apps/details?id={app_id}&reviewId={review_id}`. For App Store, iTunes link. |
| C | `source` | string | `play_store` \| `app_store` \| `reddit` \| `facebook` \| `twitter` \| `web` |
| D | `post_date` | datetime | ISO 8601, UTC: `2026-05-23T14:30:00Z`. Display formatted as `YYYY-MM-DD HH:MM` in the sheet. |
| E | `author` | string | Username or display name of the poster. Anonymized for Play Store (as returned by scraper). |
| F | `raw_text` | string | Full verbatim text of the review/post. No truncation. Newlines replaced with `\n`. |
| G | `language` | string | `ar` \| `en` \| `ar-en` |
| H | `rating` | integer or null | 1–5 for app store reviews. `null` for Reddit/Facebook/Twitter/Web. |
| I | `sentiment` | string | `positive` \| `negative` \| `neutral` |
| J | `feedback_type` | string | `bug` \| `ux_friction` \| `feature_request` \| `compliment` \| `off_topic` |
| K | `product_area` | string | `nid_verification` \| `liveness_detection` \| `facematch` \| `onboarding_general` \| `other` |
| L | `severity` | string | `critical` \| `high` \| `medium` \| `low` \| `none` |
| M | `engagement` | string | Structured string: `"likes:12, comments:5, upvotes:34"`. Fields omitted if N/A for the platform. |
| N | `agreement_signal` | boolean | `TRUE` \| `FALSE`. `TRUE` means reply/comment thread confirms the complaint is widespread. |
| O | `claude_summary` | string | One sentence in English from Claude. Max 200 characters. |
| P | `scraped_at` | datetime | ISO 8601 UTC timestamp of when this row was written. `2026-05-24T06:03:21Z`. |
| Q | `valify_scope` | string | `true` \| `false` \| `unsure`. Whether the review describes the identity verification step (ID capture, selfie, liveness, facematch, or phone verification during onboarding). |

### Row 1
Header row with column names exactly as listed above (case-sensitive).
Freeze Row 1 in the sheet.

### Sorting / Filtering notes
- The sheet is append-only. Newest rows are at the bottom.
- To analyze: filter by `client_name`, sort by `post_date` desc, filter `severity IN (critical, high)`.
- For a Valify-wide view: remove the `client_name` filter, sort by `severity`, then `post_date`.

### Engagement format examples
| Source | Engagement string |
|--------|------------------|
| Play Store | `"likes:23, comments:0"` |
| App Store | `"likes:N/A, comments:0"` |
| Reddit | `"upvotes:47, comments:12"` |
| Facebook | `"likes:18, comments:7"` |
| Twitter/X | `"likes:5, retweets:2, replies:3"` |
| Web | `"likes:N/A, comments:N/A"` |

---

## Tab 2 — "Admin"

One row per client. Written/updated by `sheets.py` at the end of each run.

| Col | Name | Type | Notes |
|-----|------|------|-------|
| A | `client_name` | string | Same display names as Feedback Log |
| B | `playstore_url` | string | Full Play Store app URL |
| C | `appstore_url` | string | Full App Store app URL |
| D | `active_keywords_en` | string | JSON array of active English keywords + hit stats. Example: `[{"kw": "thndr verification", "hits": 12, "zeros": 0}]` |
| E | `active_keywords_ar` | string | Same structure for Arabic keywords |
| F | `dead_keywords` | string | Comma-separated list of keywords retired due to 3 consecutive zero runs, with swap date. Example: `"thndr signup problem (swapped 2026-05-25 → thndr onboarding stuck)"` |
| G | `last_run_status` | string | `success` \| `partial` \| `failed` \| `facebook_blocked` \| `twitter_blocked` |
| H | `last_run_at` | datetime | ISO 8601 UTC |

### Admin tab initialization
On first run (`--mode historical`), `sheets.py` writes one row per client with:
- Play Store and App Store URLs from `config.py`
- Starting keyword sets from `keywords.py`
- `last_run_status = "pending"`
- `last_run_at = "never"`

### Row 1
Header row with column names as listed. No freeze needed (only 8 data rows).

---

## Tab 3 — "seen_hashes"

Single column, no header. Each row is a SHA-256 hex digest string (64 chars).
Used by `utils/dedup.py` to avoid writing duplicate items.

### Hash construction
```python
import hashlib
def make_hash(source: str, post_url: str, raw_text: str) -> str:
    key = f"{source}|{post_url}|{raw_text[:200]}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
```

### Dedup flow
1. Before writing a batch to Feedback Log, compute hashes for all new items.
2. Read all existing hashes from `seen_hashes` tab (single read, cached in memory for the run).
3. Filter out items whose hash already exists.
4. Append new hashes to `seen_hashes` tab.
5. Append remaining (new) items to Feedback Log.

### Maintenance
This tab will grow ~50–200 rows per day. After 90 days (~9,000–18,000 rows),
consider archiving or truncating hashes older than 90 days using the `post_date`
stored in Feedback Log. A helper script `scripts/prune_hashes.py` will be provided.

---

## Google Sheets API Notes

### Authentication
Uses a Google Cloud service account with the Sheets API and Drive API enabled.
The service account JSON is base64-encoded and stored as the `GOOGLE_SERVICE_ACCOUNT_JSON`
environment variable / GitHub Actions secret.

### Write strategy
`sheets.py` uses `gspread`'s `append_rows()` for bulk appends (one API call per batch
of up to 100 rows), and `update()` for Admin tab row updates.
This stays well within the free quota of 300 requests/minute.

### Sheet ID
The Google Sheet ID (`GOOGLE_SHEET_ID` env var) is the string between `/d/` and `/edit`
in the sheet URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`.
