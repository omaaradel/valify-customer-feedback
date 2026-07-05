# Valify Analytics — Customer Feedback Monitor

## Project Goal

This system automatically monitors public user feedback about Valify Analytics' clients'
KYC and onboarding flows. Every day it scrapes app-store reviews, Reddit, and public
Facebook pages for complaints and praise related to each client's identity-verification
experience, enriches each item via the Claude API, writes results to a shared Google Sheet,
and delivers a daily email digest. The goal is to give Valify's account team early warning
of KYC friction that users are venting about publicly — before clients escalate it as a
support ticket.

---

## Priority Clients

Data source: `Clients Transactional Volume.xlsx` (BigQuery pull, 2026 YTD as of 2026-05-24).
Amazon is priority #1 by product directive; Thndr–Khazna ranked by total_transactions desc.

| # | Display Name | Internal Key        | Flow                                       | Valify Products Active                            | First Tx   | Run Cadence    |
|---|--------------|---------------------|--------------------------------------------|---------------------------------------------------|------------|----------------|
| 1 | Amazon       | Amazon_live_bundle  | Return-item / seller verification (Egypt)  | NID OCR                                           | 2026-03-24 | Daily          |
| 2 | Thndr        | thndr               | Investment/trading account opening         | NID OCR, Facematch, NTRA/CSO Phone Validation     | 2026-01-01 | Daily          |
| 3 | Klivvr       | Klivvr              | Digital wallet account opening             | NID OCR, Passport OCR, NID Transliteration        | 2026-01-01 | Daily          |
| 4 | Rabbit       | Rabbit_live_bundle  | Rider onboarding (e-scooter/e-bike rental) | NID OCR, Liveness Detection, Facematch            | 2026-01-01 | Every 2-3 days |
| 5 | ADIB         | ADIB                | Digital bank account opening               | NID OCR, Liveness Detection, Facematch, Sanctions | 2026-01-01 | Every 2-3 days |
| 6 | Midbank      | Midbank             | Bank account opening (Mogo/BNPL app)       | NID OCR                                           | 2026-01-01 | Every 2-3 days |
| 7 | Raya         | Raya                | Raya Wealth investment account opening     | NID OCR, Liveness Detection, Facematch            | 2026-01-01 | Every 2-3 days |
| 8 | Khazna       | Khazna              | Digital financial app signup               | NID OCR                                           | 2026-01-01 | Every 2-3 days |

### Valify Core Products (user-facing names used throughout this codebase)
| Product | Internal service names |
|---------|----------------------|
| NID Verification | `ocr`, `ocr_conf`, `passport_ocr`, `egy_nid_transliteration`, `transliteration`, `cropper` |
| Liveness Detection | `liveness_detection` |
| Facematch | `facial_recognition` |
| Other (contextual) | `ntra_validation`, `cso_validation`, `sanction_shield` |

A client that does not use `liveness_detection` will have no liveness-complaint keywords
in its active keyword set. See `docs/keywords.md` for per-client keyword lists.

---

## Output Schema

### Tab 1 — "Feedback Log" (one row per feedback item)
```
client_name | post_url | source | post_date | author | raw_text | language |
rating | sentiment | feedback_type | product_area | severity | engagement |
agreement_signal | claude_summary | scraped_at
```

### Tab 2 — "Admin" (maintained automatically)
```
client_name | playstore_url | appstore_url | active_keywords_en |
active_keywords_ar | dead_keywords | last_run_status | last_run_at
```

Full column definitions and allowed enum values: `docs/sheet_schema.md`.

---

## Tech Stack Decisions

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language | Python 3.11 | Best ecosystem for all chosen scraping libs |
| Play Store | `google-play-scraper` (pip) | Mature, free, no API key, supports Arabic locale |
| App Store | `app-store-scraper` (pip) | Mirrors Play API surface, free, supports Egypt locale |
| Reddit | `praw` (pip) | Official Reddit API, free 60 req/min |
| Facebook | `facebook-scraper` (pip) | Best-effort only; no auth needed for public content |
| X/Twitter | **Dropped from v1** | snscrape unreliable since early 2024; twscrape needs paid credentials |
| Web fallback | `duckduckgo-search` (pip) | Free, no API key, catches review sites/blogs/forums |
| Sheets | `gspread` (pip) | Well-supported, free, service-account auth |
| AI enrichment | Manual via Claude Code (paste `docs/enrich_prompt.md`) | Zero ongoing cost; classification is human-triggered |
| Scheduler | GitHub Actions cron | Free, zero infra, secrets management built-in |
| Digest | Gmail SMTP (email) | Free, no external service, App Password auth |
| Dedup | SHA-256 of `source + post_url + raw_text[:200]` | Stateless, cheap; stored in `seen_hashes` tab |

Full platform-by-platform rationale: `docs/scrapers.md`.

---

## Architecture

```
GitHub Actions cron — 06:00 UTC daily (08:00 Cairo winter / 09:00 DST)
          │
          ▼
     main.py  (orchestrator)
          │
          ├─► config.py          client registry, date bounds, run cadence
          │
          ├─► keywords.py        per-client keyword sets (gated by services used)
          │
          ├─► scrapers/
          │    ├── playstore.py  google-play-scraper
          │    ├── appstore.py   app-store-scraper         [Phase 3]
          │    ├── reddit.py     PRAW                      [Phase 3]
          │    ├── facebook.py   facebook-scraper          [Phase 3]
          │    └── web.py        duckduckgo-search         [Phase 3]
          │
          ├─► utils/
          │    ├── dedup.py      SHA-256 content-hash dedup
          │    └── dates.py      date bounding, UTC handling
          │
          ├─► enrichment.py      Language detection (Arabic/Latin heuristic)
          │
          ├─► sheets.py          gspread read/write to Google Sheet
          │
          └─► digest.py          HTML email via Gmail SMTP  [Phase 3]
```

**Two run modes:**
- `--mode historical` (first run): sweeps back to `first_tx` date, capped at 12 months.
  Amazon: back to 2026-03-24. All others: 2026-01-01.
- `--mode daily` (subsequent): fetches last 48 hours. Dedup prevents duplicates.

---

## File Index

```
.
├── CLAUDE.md                      This file
├── README.md                      Quick-start for new contributors
├── main.py                        CLI orchestrator: scrape → enrich → write → digest
├── config.py                      Client definitions (app IDs, services, dates, cadence)
├── keywords.py                    Keyword sets per client, gated by services used
├── enrichment.py                  Language detection (Arabic/Latin heuristic)
├── sheets.py                      gspread wrapper (Feedback Log, Admin, seen_hashes)
├── requirements.txt               Pinned Python dependencies
├── .env.example                   Template for local .env file
├── .gitignore
│
├── scrapers/
│   ├── __init__.py
│   ├── playstore.py               Google Play Store via google-play-scraper
│   ├── appstore.py                Apple App Store via app-store-scraper  [Phase 3]
│   ├── reddit.py                  Reddit via PRAW                        [Phase 3]
│   ├── facebook.py                Public Facebook (best-effort)          [Phase 3]
│   └── web.py                     DuckDuckGo web fallback                [Phase 3]
│
├── utils/
│   ├── __init__.py
│   ├── dedup.py                   SHA-256 hash deduplication
│   └── dates.py                   Date bounding per client, UTC handling
│
├── scripts/
│   ├── export_pending.py          Export unenriched Sheet rows to pending.json
│   └── import_enriched.py         Write enriched.json classifications back to Sheet
│
└── docs/
    ├── scrapers.md                Per-platform approach + verified app IDs
    ├── keywords.md                Keyword sets EN + AR per client + rotation logic
    ├── enrichment.md              Enrichment overview, per-client use cases, rules
    ├── enrichment_taxonomy.md     Field definitions and allowed enum values
    ├── enrichment_hints.md        Per-client signal phrases and edge-case guidance
    ├── enrichment_examples.md     Labelled input/output examples for tricky cases
    ├── enrich_prompt.md           Paste into Claude Code to run manual enrichment
    ├── sheet_schema.md            Exact Google Sheet column structure
    └── runbook.md                 Incident response for broken scrapers
```

---

## How to Run

### Install dependencies
```bash
pip install -r requirements.txt
```

### Required environment variables
Copy `.env.example` to `.env` and fill in:
```
GOOGLE_SERVICE_ACCOUNT_JSON  Base64-encoded service account JSON
GOOGLE_SHEET_ID              Spreadsheet ID from Sheet URL
```

### Amazon historical sweep (Phase 2 target)
```bash
python main.py --client amazon --mode historical
```

### Dry run (no Sheet writes)
```bash
python main.py --client amazon --mode historical --dry-run
```

### Daily delta
```bash
python main.py --client amazon --mode daily
```

---

## Cost Estimates

Model: `claude-haiku-4-5-20251001` — ~$0.80/M input tokens, ~$4/M output tokens.

**Per enrichment batch** (20 items, ~3,000 input + 1,500 output tokens):
- Input: $0.0024 | Output: $0.006 | Total: **~$0.008/batch**
- System-prompt caching (500-token system prompt cached after first call) saves ~$0.0004/batch.

**Historical sweep — Amazon only** (est. 500–2,000 reviews since 2026-03-24):
- 25–100 batches × $0.008 = **$0.20–$0.80 one-time**

**Daily steady-state — Amazon only:**
- ~20–50 new reviews/day = 1–3 batches = **~$0.01–$0.03/day**

**Daily steady-state — all 8 clients (Phase 3+):**
- ~100–300 new items/day = 5–15 batches = ~$0.05–$0.15/day
- Monthly: **~$1.50–$4.50/month**

These are upper-bound estimates; many reviews will be non-English/non-Arabic and
filtered before enrichment, reducing actual batch count.

---

## Decisions Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-05-24 | Email digest (Gmail SMTP) over Slack webhook | SMTP is free with zero external service dependencies; a Slack workspace integration adds ops overhead |
| 2026-05-24 | Amazon Shopping app (`com.amazon.mShop.android.shopping`) not Seller Central | Egyptian sellers/buyers use the global app; Seller Central is for inventory management, not the Valify KYC flow |
| 2026-05-24 | X/Twitter dropped from v1 | snscrape has been unreliable since early 2024; twscrape requires account credentials we won't budget for |
| 2026-05-24 | Phase 2 = Amazon Play Store sweep only | Validate the full pipeline end-to-end before adding more scrapers and clients |
| 2026-05-24 | No auto-cron in Phase 2 | Cron enabled manually after first sweep is reviewed and approved |
| 2026-05-24 | Midbank → Mogo app (`com.midbankcf.midtakseet`) | Mogo is Mid Bank for Consumer Finance's BNPL app — the one that uses Valify OCR per transaction data |
| 2026-05-24 | Raya → Raya Wealth (`com.rayawealth.rayawealth`) | Investment account opening requires full KYC (NID + liveness + facematch), matching Raya's Valify service list |
| 2026-05-25 | Rabbit → Rabbit Mobility (`com.Rabbit.rabbitApp`), NOT Rabbit Mart (`com.rabbit.mart`) | Rabbit_live_bundle is the e-scooter/e-bike rental company; Rabbit Mart is an unrelated grocery delivery app. Rider onboarding uses all three Valify products (NID + liveness + facematch), consistent with the `_live_bundle` key. |
| 2026-05-25 | Enrichment is manual via Claude Code, not API | Zero ongoing cost. Scraping is automated; classification is human-triggered. Paste `docs/enrich_prompt.md` into a Claude Code session after each scrape run. No `ANTHROPIC_API_KEY` needed. |
| 2026-05-25 | Keywords are contextual hints, not lexical filters | A review with zero literal keyword matches can still be highly relevant (e.g., Amazon return flow in Arabic). Keyword sets in `keywords.py` guide what language to watch for, not what to include or exclude. |
| 2026-05-25 | Sentiment captured neutrally — positive, negative, suggestions all valued equally | Do not bias classification toward complaints. Positive and neutral feedback (fast verification, gallery-upload requests) is equally actionable signal for the product team. |
| 2026-05-25 | Per-client use case is explicit in `docs/enrichment.md` | Amazon = returns/seller registration; all others = customer onboarding. Feedback meaning depends on the flow. "Verification" in an Amazon review refers to the return or seller-signup step, not account KYC. |
| 2026-05-25 | Storage = Google Sheet with auto-housekeeping. No BigQuery. | Sheet is free, already integrated, and sufficient for current data volume. `housekeeping.py` runs at the end of every scrape to keep it sustainable. |
| 2026-05-25 | Sheet stays under 25k rows during normal operation. Off-topic rows older than 30 days are pruned to Archive tab automatically. | Off-topic rows (99%+ of Amazon volume) are low-value after 30 days. Archiving them keeps the Feedback Log fast and the working set relevant. |
| 2026-05-25 | Hard ceiling at 45k rows triggers automatic archive-sheet creation. Archive sheet IDs are logged in this decisions log. | Prevents Sheet API degradation at extreme row counts. New sibling sheets are created via `gc.create()` and their IDs are appended below for discoverability. |
| 2026-05-25 | Phase 9 will commit /backups/ to Git on a weekly cron. | `scripts/backup_to_git.py` (triggered by `--backup` flag) writes all tabs as CSV to `/backups/`. Git commit is deferred to Phase 9 to keep Phase 3 scope tight. |
