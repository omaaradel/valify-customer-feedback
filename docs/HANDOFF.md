# Valify Customer Feedback Monitor. Persistent handoff.
Last updated: 2026-07-05 by Claude Code (Phase 8c-r1 closure re-verified live twice against the sheet, .env format bug recurred and was fixed both times, Phase 8 confirmed fully complete, no exceptions).

---

## How to use this document

Any new Claude Code session opened in this repo should read this file first.
It captures the current phase status, sheet state, credential requirements,
architectural decisions, and open backlog so that work can resume immediately
without a paste-in context briefing from the user.

---

## Project location

`F:\Apps\Claude\Claude Directory\Projects\Customer Feedback`

---

## What this project does

Valify Analytics' account team needs early warning of KYC friction that users
are venting about publicly, before clients escalate it as a support ticket.
This system scrapes public feedback (app store reviews and web results) for each
of Valify's 8 priority clients, enriches
each item with a multi-field classification, writes results to a
shared Google Sheet, and delivers a weekly email digest. Enrichment is
automated via Gemini (with Groq fallback) as part of the Phase 9 daily
GitHub Actions pipeline. A legacy manual mode, pasting
`docs/enrich_prompt.md` into a Claude Code session, is retained for ad-hoc runs.

---

## Active clients

App Store IDs are sourced from `config.py` (source of truth). Trustpilot status confirmed 2026-06-14.

| Client | BigQuery key | Play Store package | App Store ID | Trustpilot | Use case | Valify products |
|---|---|---|---|---|---|---|
| Amazon | Amazon_live_bundle | com.amazon.mShop.android.shopping | 297606951 | amazon.eg, deferred | Return-item and seller verification (Egypt) | NID OCR |
| Thndr | thndr | com.axismarkets.thndr | 1494883259 | not on Trustpilot | Trading account opening | NID OCR, Facematch, Phone Validation (NTRA + CSO) |
| Klivvr | Klivvr | com.klivvr.consumer | 1586109111 | not on Trustpilot | Digital wallet account opening | NID OCR, Passport OCR, NID Transliteration |
| Rabbit | Rabbit_live_bundle | com.Rabbit.rabbitApp | 1468767626 | not on Trustpilot | Rider onboarding, first scooter or e-bike rental | NID OCR, Liveness Detection, Facematch |
| ADIB | ADIB | com.ADIBEgyptPhone | 1263042975 | not on Trustpilot | Digital bank account opening | NID OCR, Liveness Detection, Facematch, Sanctions |
| Midbank | Midbank | com.midbankcf.midtakseet | 1639315081 | not on Trustpilot | Bank account opening via Mogo BNPL app | NID OCR |
| Raya | Raya | com.rayaelite.B2E | 6738885879 | not on Trustpilot | Consumer finance onboarding for corporate employees (3-step, KYC at step 3) | NID OCR, Liveness Detection, Facematch |
| Khazna | Khazna | com.project.imperialcreation.khaznaproject | 1614641229 | not on Trustpilot | Digital financial app signup | NID OCR |

Notes on disambiguation:
- Rabbit: `com.Rabbit.rabbitApp` is Rabbit Mobility (e-scooter/e-bike). `com.rabbit.mart` is Rabbit Mart (grocery). These are unrelated companies.
- Midbank: `com.midbankcf.midtakseet` is the Mogo app published by Mid Bank for Consumer Finance.
- Raya: `com.rayaelite.B2E` is Raya Elite (B2E consumer finance). `com.rayawealth.rayawealth` is an unrelated Indian wealth management firm. App Store ID 6738885879 confirmed 2026-06-14 via apps.apple.com/eg/app/raya-elite/id6738885879.

---

## Architecture (current state)

**Storage:** Google Sheets (gspread library). One spreadsheet with four tabs: Feedback Log (append-only, one row per feedback item), Admin (one row per client, auto-maintained), seen_hashes (SHA-256 dedup registry), Archive (off-topic rows older than 30 days moved here by housekeeping).

**Scrapers (active sources):**
- Play Store: `google-play-scraper`, per-app ID, AR then EN. Fully operational.
- App Store: iTunes RSS endpoint (direct HTTP), per-app ID, Egypt storefront. Tier A. 93 rows written in Phase 8c (30-day window, 2026-06-15).

**Scrapers (disabled sources):**
- web_ddg: `duckduckgo-search`. Disabled in Phase 8c. Returns search snippets, not user reviews. 73 rows quarantined to Quarantine tab. Re-enable: `_DDG_ENABLED = True` in scrapers/web.py.
- web_trustpilot: Trustpilot page scraping. Disabled in Phase 7. AWS WAF blocks at TLS-fingerprint level. Re-enable: `_TRUSTPILOT_ENABLED = True` in scrapers/web.py (also add cloudscraper/curl_cffi).

**Enrichment:** Enrichment has two modes: (1) legacy manual, via `docs/enrich_prompt.md` in Claude Code, retained for ad-hoc runs, (2) automated, via `scripts/enrich_phase8.py` called from the GitHub Actions daily pipeline (Phase 9). Requires GEMINI_API_KEY in .env. Model: gemini-3.5-flash (gemini-1.5-flash no longer exists; gemini-2.0-flash has quota 0 on free tier keys; gemini-3.5-flash is the correct Flash model for this key).

**Automation:** `main.py` orchestrates scrape, dedup, write, housekeeping, enrichment, JSON export, backup, and digest as callable functions. Phase 9 delivers full automation via a GitHub Actions cron workflow (`.github/workflows/daily_pipeline.yml`) that runs Gemini auto-enrichment with Groq fallback daily.

**Dedup:** SHA-256 of `source + post_url + raw_text[:200]` stored in `seen_hashes` tab. Stateless and idempotent.

**Backup:** `scripts/backup_to_git.py` dumps all Sheet tabs to `/backups/` as CSV. Git commit of `/backups/` deferred to Phase 9.

**Housekeeping:** `housekeeping.py` runs at the end of every scrape. Off-topic rows older than 30 days are moved to Archive tab. Hard ceiling at 45k rows triggers a new sibling archive spreadsheet.

---

## Credentials required in .env

| Variable | Purpose |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Base64-encoded GCP service account JSON (Sheets + Drive API enabled) |
| `GOOGLE_SHEET_ID` | String between `/d/` and `/edit` in the Sheet URL |
| `GEMINI_API_KEY` | Gemini API key for Phase 8+ automated enrichment via `enrichment/gemini_classifier.py`. Free tier key from https://aistudio.google.com/app/apikey. The key value is never logged or committed. |
| `GROQ_API_KEY` | Groq free tier API key for fallback enrichment via `enrichment/providers/groq.py`. Free account at console.groq.com. Geo-blocked from Egyptian IPs. Works on GitHub Actions. Never logged or committed. |

---

## Decisions log (chronological, oldest first)

- 2026-05-24: Email digest (Gmail SMTP) chosen over Slack webhook. SMTP is free with no external service dependency.
- 2026-05-24: Amazon Shopping app (`com.amazon.mShop.android.shopping`) confirmed, not Seller Central. Egyptian buyers and sellers use the global app; Valify KYC surfaces inside it.
- 2026-05-24: X/Twitter dropped from v1. snscrape has been unreliable since early 2024; twscrape requires paid credentials.
- 2026-05-24: Phase 2 scoped to Amazon Play Store only. Validates the full pipeline before adding more scrapers and clients.
- 2026-05-24: No auto-cron in Phase 2. Cron enabled manually after first sweep is reviewed and approved.
- 2026-05-24: Midbank uses Mogo app (`com.midbankcf.midtakseet`). Mogo is Mid Bank for Consumer Finance's BNPL app and the one that uses Valify OCR per transaction data.
- 2026-05-24: Raya uses Raya Wealth app (`com.rayawealth.rayawealth`). NOTE: this decision was superseded; see 2026-05-26 entry.
- 2026-05-25: Enrichment is manual via Claude Code, not API. Zero ongoing cost. Scraping is automated; classification is human-triggered.
- 2026-05-25: Keywords are contextual hints, not lexical filters. A review with zero literal keyword matches can still be highly relevant.
- 2026-05-25: Sentiment captured neutrally. Positive, negative, and suggestion feedback are all valued equally.
- 2026-05-25: Per-client use case is explicit in `docs/enrichment.md`. Amazon = returns/seller registration; all others = customer onboarding.
- 2026-05-25: Storage is Google Sheet with auto-housekeeping. No BigQuery. Free, already integrated, sufficient for current volume.
- 2026-05-25: Sheet stays under 25k rows during normal operation. Off-topic rows older than 30 days are pruned to Archive tab.
- 2026-05-25: Hard ceiling at 45k rows triggers automatic archive-sheet creation.
- 2026-05-25: Phase 9 will commit /backups/ to Git on a weekly cron.
- 2026-05-26: Rabbit uses `com.Rabbit.rabbitApp` (Rabbit Mobility, e-scooter/e-bike), NOT `com.rabbit.mart` (Rabbit Mart, grocery delivery). Confirmed by developer name and transaction data alignment.
- 2026-05-26: Raya uses `com.rayaelite.B2E` (Raya Elite B2E), NOT `com.rayawealth.rayawealth` (unrelated Indian app). Raya Elite is the consumer finance app requiring full KYC (NID + liveness + facematch), consistent with Raya's Valify service list.
- 2026-06-13: Facebook scraping fragility accepted. `facebook-scraper` breaks frequently; gaps are accepted. No engineering time invested to keep it alive. All failures caught and logged; run continues.
- 2026-06-13: Web scope limited to DuckDuckGo search plus Trustpilot. No blog scraping, no news scraping, no Egyptian forums.
- 2026-06-13: HANDOFF.md established as the canonical living state document. Every phase ends with an update to this file.
- 2026-06-14: Reddit dropped from Phase 7 and from the project. Reddit's Responsible Builder Policy (June 2026) restricts the legacy Data API to moderation use cases. Our use case (commercial product analytics for an identity verification vendor) does not qualify. Devvit, Reddit's sanctioned developer platform, is for apps that run inside Reddit, not for external scraping. Reddit signal will surface incidentally via DuckDuckGo results in scrapers/web.py.
- 2026-06-14: Facebook scraping dropped from Phase 7. Smoke test of kevinzg/facebook-scraper confirmed mbasic.facebook.com now hard redirects unauthenticated requests to login, m.facebook.com serves a JS SPA that the library cannot parse, and Facebook RSS feeds return 404. Under the hard constraints (no login or cookies, no paid services), Facebook scraping is not achievable in 2026. Facebook content may surface incidentally via DuckDuckGo results in scrapers/web.py. Revisit only if a constraint is relaxed.
- 2026-06-14: Trustpilot scraping deferred past Phase 7. Amazon is the only client with a Trustpilot page (amazon.eg, approximately 85 reviews). AWS WAF blocks plain Python requests at the TLS-fingerprint level, returning a 403 "Verifying Connection" interstitial. Bypassing it requires cloudscraper or curl_cffi. ROI is low: the ~85 Trustpilot reviews are already largely covered by Play Store and App Store volume for Amazon. Deferred to a future phase. The web_trustpilot source value is preserved in scrapers/web.py; re-enabling requires only flipping `_TRUSTPILOT_ENABLED = True` and installing the bypass library.
- 2026-06-15: gemini-1.5-flash is not available in the v1beta API (404). gemini-2.0-flash and gemini-2.0-flash-lite have free-tier quota limit=0 for this key. gemini-2.5-flash works but hits the 20 RPM free-tier limit under load. gemini-3.5-flash is the working Flash-tier model; it has a separate quota. The classifier uses gemini-3.5-flash. If this key is replaced, re-test available models with ListModels before running.
- 2026-06-15: valify_scope field added at column Q. sentiment `mixed` value removed; Phase 8 definition uses positive / negative / neutral only. Reviews with both tones classify by dominant tone, or neutral if balanced.
- 2026-06-15: enrichment/gemini_classifier.py created as a package alongside root enrichment.py. The enrichment/ package shadows enrichment.py for Python imports; scrapers continue to work via enrichment/__init__.py which re-exports detect_language.
- 2026-06-15: App Store scraper fixed (Phase 8b). Three changes: (1) _SLEEP_BETWEEN_CLIENTS raised from 2.0 to 12.0 seconds and wired into the main.py client loop via a sleep_before parameter on fetch(); previously the constant was defined but never called, so multi-client runs fired with no inter-client pause, triggering Apple CDN throttling. (2) Empty page-1 feed now logged as SUSPECTED BLOCK at error level with body length, instead of silently returning 0 rows identical to a genuine empty result. (3) One 30-second retry added on suspected block; if retry also returns empty, fetch() returns ([], True) so the caller can distinguish a blocked result from a successful zero. Full 8-client sweep (30-day window) confirmed: all 8 clients returned HTTP 200 with entries, no suspected blocks. Row counts: Amazon 51, Thndr 22, Rabbit 6, ADIB 9, Klivvr 4, Midbank 4, Raya 0 (date cutoff, not block), Khazna 0 (date cutoff, not block). Total 96 rows.
- 2026-06-14: DDG web results carry no reliable post_date. The `duckduckgo-search` library returns a title, snippet, and URL but no publication date in the metadata. post_date is stored as blank for web_ddg rows. This interacts with housekeeping age-based pruning: rows without a date are never pruned by the 30-day archival rule. This is acceptable for Phase 7 because web_ddg volume is low (tens of rows per run, not thousands). A future phase may add a scraped_at fallback date for web_ddg rows so housekeeping can eventually prune them.
- 2026-06-14: Apple iTunes RSS CDN throttles sequential multi-client requests when clients fire with no inter-client pause. Fixed in Phase 8b: _SLEEP_BETWEEN_CLIENTS=12s is now wired into the client loop. See the 2026-06-15 Phase 8b entry for full details.
- 2026-06-15: App Store first write was a 30-day window only (2026-05-16 to 2026-06-15), not a full historical backfill. Decision rationale: App Store scraper is newly confirmed operational; limiting to 30 days avoids ingesting a large stale backlog whose relevance has already decayed. Full historical backfill from first_tx dates is deferred to Phase 11 along with the 7 non-Amazon Play Store clients.
- 2026-06-15: web_ddg source retired. DuckDuckGo returns search-result snippets (homepages, directory listings, wrong company, encyclopedia pages), not user reviews. All 73 web_ddg rows were classified as off_topic=72, unsure=1 by Gemini in Phase 8. These 73 rows were moved to the Quarantine tab with reason "web_ddg retired: search snippet, not a user review." The DDG scraper is disabled via `_DDG_ENABLED = False` in scrapers/web.py; re-enabling requires only flipping the flag.
- 2026-06-15: sheets.py FEEDBACK_HEADERS did not include valify_scope. When replace_feedback_rows (used in the web_ddg quarantine step) cleared and rewrote the Feedback Log, it used FEEDBACK_HEADERS as the column list, which silently dropped column Q (valify_scope) for all rows. Fixed: valify_scope added as the 17th element of FEEDBACK_HEADERS and to _to_row(). The column Q header was restored immediately. All valify_scope values in the Feedback Log require re-enrichment (see open backlog).
- 2026-06-15: Gemini free-tier quota (gemini-3.5-flash) exhausted mid-run during appstore enrichment. 33 of the 93 appstore rows received parse_error for all enrichment fields. These rows have correct raw_text, source, post_date, and language, but their sentiment, feedback_type, product_area, severity, claude_summary, and valify_scope are all set to "parse_error" or "enrichment_failed". A re-enrichment pass (--mode full, targeting source=appstore, sentiment=parse_error) should run after the daily quota resets.
- 2026-06-16: Column-drop bug fix verified. tests/test_replace_feedback_rows.py (47 assertions, all PASS) proves FEEDBACK_HEADERS has 17 elements with valify_scope at index 16, _dict_to_row always produces exactly 17 values, empty optional fields stay empty without shifting subsequent columns, and the full replace_feedback_rows code path preserves column Q through a MockWorksheet round-trip. The test is in-memory only; it does not touch the real Feedback Log.
- 2026-06-16: Pre-recovery audit run (validation/audit_pre_recovery.md, read-only). Confirmed: 3,353 rows (3,260 play_store + 93 appstore), all valify_scope values blank, 33 appstore parse_error rows, 41 play_store rows with legacy sentiment="mixed" (enriched before the Phase 8 taxonomy locked to positive/negative/neutral), 73 Quarantine rows (all web_ddg). All six checklist invariants passed.
- 2026-06-16: scripts/enrich_recovery.py created. Two targeted steps: --step parse-error runs enrich_full_batch on appstore rows where sentiment=parse_error (all 7 fields); --step valify-scope runs classify_batch on rows with real enrichment but empty valify_scope, writing only column Q. Write happens before summary print so a crash in the summary does not lose data. Summary normalizes Gemini JSON booleans (True/False) to lowercase strings to avoid sorted() TypeError on mixed types.
- 2026-06-16: enrich_recovery.py --step parse-error run (live). Found 33 rows. 20 enriched successfully (false=19, true=1; sentiment=negative for all 20; feedback_type=off_topic=19, ux_friction=1). 13 rows still parse_error: batches 2 (rows 11-20) and 4 (rows 31-33) exhausted all 5 Gemini retries on 429. Root cause: 4s inter-batch sleep is exactly the 15 RPM free-tier ceiling; 503 retries within each batch consume burst capacity and push the effective rate over the limit. The 20 successful rows are written to the sheet including their valify_scope values. The 13 remaining rows need a re-run after quota resets. enrich_recovery.py --step valify-scope not yet run.
- 2026-06-16: Fallback provider architecture built as Phase 9 pre-work. Provider chain implemented: Gemini Flash free tier (primary) then Groq free tier (fallback) then clean exit with no write (last resort). Ollama deferred unless Groq Arabic quality fails during Phase 9 testing.
- 2026-06-16: Circuit breaker implemented with two distinct failure modes. ProviderQuotaError (daily limit exhausted, HTTP 429 with no recovery) keeps the circuit OPEN for the entire run, no cooldown. ProviderUnavailableError (503, transient network failure) uses a 5-minute cooldown before HALF-OPEN retry. These are handled separately because a daily quota does not recover in 5 minutes.
- 2026-06-16: Write guard added to enrich_recovery.py and enrich_phase8.py. When all providers fail or all circuits are open, the script skips the batch and writes nothing to the sheet. Rows stay blank. parse_error is never written as a result of provider failure. Blank means not yet enriched. parse_error means the API returned a malformed response.
- 2026-06-16: Checkpoint file added at scripts/enrichment_checkpoint.json. Written after every batch, not at end of run. Records completed row IDs, skipped row IDs, and which provider handled each row. Eliminates the need for manual recovery passes after mid-run crashes.
- 2026-06-16: Groq free tier is geo-blocked for Egyptian IP addresses (Cloudflare geo-filter). Groq works correctly on GitHub Actions (US servers) but will not work when running scripts locally from Cairo. This is expected and acceptable. Local runs rely on Gemini only. Production cron on GitHub Actions uses the full fallback chain.
- 2026-06-16: Phase 9 automation confirmed to run on GitHub Actions cron. Free tier, no credit card, US servers. GEMINI_API_KEY and GROQ_API_KEY both required as GitHub Actions secrets before Phase 9 cron is enabled.
- 2026-06-16: Groq Arabic quality (Egyptian dialect) is untested. Decision: test during Phase 9 on a 20-row Arabic sample before trusting Groq as a production fallback for valify_scope classification. If quality is poor on dialect, Ollama with Qwen2.5 or Aya-23 is the next option.
- 2026-07-05: Bug found: 29 rows (27 play_store on-topic + 2 appstore) and 13 appstore rows had the literal string "parse_error" written into valify_scope (and, for the 13, into all 7 enrichment fields), left over from a run between 2026-06-16 and 2026-07-05 that predates or bypassed the write-guard architecture. This directly contradicts the write-guard rule ("parse_error is never written; blank means not yet enriched"). Neither `enrich_recovery.py` nor `enrich_phase8.py` treated `"parse_error"` as a value needing retry: `_pull_missing_valify_scope` (enrich_recovery.py) and `_pull_scope_only_rows` (enrich_phase8.py) only checked for blank cells, so all 42 affected rows were silently skipped on the first pass of Phase 8c-r1 recovery. Fixed both predicates to treat `valify_scope == "parse_error"` the same as blank (missing, eligible for retry). Also added a blank/parse_error valify_scope filter to `enrich_phase8.py --mode scope-only`, which previously had no such filter at all and would have unconditionally reprocessed every on-topic row (including rows Step 1 had just written) on every run.
- 2026-07-05: Phase 8c-r1 recovery completed. Step 1 (valify-scope, 29 rows: 27 play_store + 2 appstore): all 29 processed via Gemini in 3 batches, no skips. valify_scope: true=10, false=13, unsure=6. Sanity check passed (true count 10 is within the 3-10 expected range). Step 2 (parse-error, 13 remaining appstore rows): all 13 processed via Gemini in 2 batches, no skips. sentiment: negative=10, positive=3. feedback_type: off_topic=13 for all 13. valify_scope: false=13 (off_topic rule forces false). No rows remain parse_error anywhere in the sheet (sentiment, feedback_type, or valify_scope). Step 3 (scope-only backfill, `enrich_phase8.py --mode scope-only`): 0 rows found needing backfill, because the fixed Step 1 predicate had already resolved every row that step 3 would have targeted. This is the correct outcome, not a failure. Provider used for all three steps: Gemini only (Groq fallback was available but never invoked; no batches failed).
- 2026-07-05: Inter-batch sleep raised from 4s to 6s. The value actually governing `enrich_recovery.py` and `enrich_phase8.py` runs is `_BATCH_DELAY` in `enrichment/provider_chain.py` (used by `ProviderChain._run_batches`), not a literal inside `enrich_recovery.py` itself. Raised `_BATCH_DELAY` from 4.0 to 6.0. Also raised the two legacy, currently-unused `time.sleep(4)` calls in `enrichment/gemini_classifier.py`'s standalone `classify_batch`/`enrich_full_batch` functions to 6s for consistency, closing the HANDOFF backlog item recorded on 2026-06-16.
- 2026-07-05: Local environment note (not a code issue): during this session, `gspread`/`requests` intermittently raised `MemoryError` while decoding Sheets API responses, and even a plain `import requests` once failed with `MemoryError` during regex compilation. Root cause: this machine has no pagefile configured (`SizeStoredInPagingFiles` = 0) and periodically runs with only ~4GB free RAM against 16GB total (Brave browser + Windows Memory Compression are the largest consumers). This caused transient allocation failures unrelated to sheet size (3,353 rows is trivial). Retrying after a short pause resolved it every time. Not expected to affect Phase 9 GitHub Actions cron runs (separate, swap-backed environment). If local recovery runs become unreliable again, configure a Windows pagefile or close memory-heavy applications before running.
- 2026-07-05: `.env.example` (committed in the initial commit) contained a real-looking base64-encoded Google service account key, pushed to GitHub before anyone noticed. Purged from full git history with `git-filter-repo --path .env.example --invert-paths --force` and force-pushed to `origin master`. `.env.example` also added to `.gitignore` so it cannot be recommitted. The rewritten history no longer contains the file, but anyone who already cloned or forked before the force push still has the old commit locally; the key must be treated as compromised regardless of the history purge.
- 2026-07-05: Local `.env` `GOOGLE_SERVICE_ACCOUNT_JSON` was stored as raw, multi-line, pretty-printed JSON instead of the single-line base64 string the code expects (`base64.b64decode(...)` then `json.loads(...)` in `_open_sheet()`). `python-dotenv` silently dropped the unparseable continuation lines, leaving the env var as just `{`, which made `scripts/enrich_recovery.py --step valify-scope` fail immediately with `JSONDecodeError` on this session's first attempt. Fixed by reconstructing the JSON block from `.env`, validating it parses, re-encoding it to base64, and collapsing it back to a single `.env` line. Local-only fix, `.env` is gitignored and was never committed; no application code changed.
- 2026-07-05: While diagnosing the `.env` formatting bug above, a naive split-on-`=` debug script matched an `=` character embedded inside the base64 private-key material and printed most of the key's value into a terminal/tool output during this session. Combined with the separate `.env.example` git-history exposure the same day, the service account key must be treated as compromised. Action needed, not yet done: rotate the key in Google Cloud Console (IAM, Service Accounts, Keys), update local `.env`, and update the `GOOGLE_SERVICE_ACCOUNT_JSON` GitHub Actions secret when Phase 9 configures it.
- 2026-07-05: Phase 8c-r1 closure re-verified live, after the `.env` fix above. Ran all three recovery steps in order against the live sheet: `enrich_recovery.py --step valify-scope` found 0 rows missing valify_scope (expected ~29 per the earlier closure, already resolved), `enrich_recovery.py --step parse-error` found 0 appstore rows with `sentiment == parse_error` (expected 13, already resolved), `enrich_phase8.py --mode scope-only` found 0 on-topic rows with real enrichment but blank valify_scope (expected 0, confirming the earlier closure). No provider calls were made in any step since no rows matched; no batches were skipped. A separate read-only query of the full Feedback Log confirms zero rows with `parse_error` in sentiment, feedback_type, or valify_scope anywhere in the sheet, and zero on-topic rows missing valify_scope. Totals match the closure numbers exactly: 3,353 rows total (play_store 3,260, appstore 93); sentiment negative=1,711, positive=1,491, neutral=110, mixed=41 (legacy); feedback_type off_topic=3,323, ux_friction=16, bug=12, compliment=2; valify_scope true=11, false=45, unsure=6, blank=3,291. Inter-batch sleep confirmed at 6s (`_BATCH_DELAY` in `enrichment/provider_chain.py:28`, not a literal in `enrich_recovery.py`). Phase 8 is confirmed fully complete with no unresolved rows and no exceptions.
- 2026-07-05: Second re-verification pass, same session, same three steps re-run in order on request. Before Step 1 could connect to the sheet, `.env`'s `GOOGLE_SERVICE_ACCOUNT_JSON` was found back in the same raw multi-line format described above (same `python-dotenv` parse warnings on lines 3 to 13, same `JSONDecodeError` on `_open_sheet()`), even though it had already been fixed once earlier in this session. Cause not established (not investigated further; possibly a reset of the working environment between turns rather than anything in this repo). Fixed the same way as before: reconstructed the JSON block, validated it parses, re-encoded to base64, collapsed to one line, no field values printed at any point (see the no-secrets-in-output rule now in effect for this project). After the fix, all three steps were re-run live and again found 0 rows to process, identical to the first re-verification pass. No sheet data changed. If a future session hits the same `JSONDecodeError` at `_open_sheet()`, check whether `GOOGLE_SERVICE_ACCOUNT_JSON` in `.env` is single-line base64 before assuming a code or credentials problem.
- 2026-07-06: Phase 9 Step 4, Groq Arabic quality test run (`scripts/groq_arabic_test.py`, new). Selected 20 Arabic rows (23 on-topic Arabic rows available; none needed from off-topic). Groq failed with `HTTP 403 Forbidden` on every batch across 4 independent attempts this session, consistent with the known Egyptian-IP geo-block, not flakiness: Groq is confirmed unreachable from this local environment. Result recorded as deferred to the first GitHub Actions `workflow_dispatch` run (US servers, not geo-blocked), per plan; Groq is not yet confirmed or rejected as a production fallback. Separately and unrelated to Groq: repeated retries across this session's multiple attempts exhausted the `gemini-3.5-flash` free-tier daily quota (`429`, `limit: 20`), so the final run also recorded 0 Gemini results; this is a one-day quota exhaustion caused by this test's own retries, not a structural problem, and is expected to clear on its own. Full row-level detail in `validation/groq_arabic_test.md`. Action needed: re-run `python scripts/groq_arabic_test.py` from a GitHub Actions `workflow_dispatch` run once the workflow exists, to get a real Gemini-vs-Groq comparison before trusting Groq as the production fallback.

---

## Repo structure (current)

```
.
+-- CLAUDE.md                       Full project context and decisions log
+-- README.md                       Quick-start for new contributors
+-- HANDOFF.md                      (see docs/HANDOFF.md -- this file)
+-- main.py                         CLI orchestrator: scrape, dedup, write, housekeeping
+-- config.py                       Client registry (app IDs, services, first_tx, cadence)
+-- keywords.py                     Keyword sets per client, gated by Valify services used
+-- enrichment.py                   Language detection (dead file, shadowed by enrichment/ package)
+-- housekeeping.py                 Row count checks, off-topic archival, ceiling guard
+-- sheets.py                       gspread wrapper for all Sheet operations
+-- requirements.txt                Pinned Python dependencies
+-- .env.example                    Template for local .env (GEMINI_API_KEY added Phase 8)
+-- .gitignore
+-- scrapers/
|   +-- __init__.py
|   +-- playstore.py                Google Play Store (google-play-scraper)
|   +-- appstore.py                 Apple App Store (app-store-scraper) [Phase 7]
|   +-- web.py                      DuckDuckGo + Trustpilot [Phase 7]
+-- enrichment/
|   +-- __init__.py                 detect_language() -- imported by all scrapers [Phase 8]
|   +-- gemini_classifier.py        Gemini Flash classifier: classify_batch, enrich_full_batch [Phase 8]
|   +-- circuit_breaker.py          Circuit breaker state machine. CLOSED, OPEN, HALF-OPEN per provider.
|   +-- provider_chain.py           ProviderChain. Tries providers in order. Checkpoint written per batch.
|   +-- providers/
|       +-- __init__.py
|       +-- base.py                 BaseProvider ABC. Shared prompt builders. ProviderQuotaError, ProviderUnavailableError, ProviderParseError.
|       +-- gemini.py               GeminiProvider. Raises exceptions instead of returning parse_error values.
|       +-- groq.py                 GroqProvider. OpenAI-compatible Groq REST API. Default model llama-3.3-70b-versatile.
+-- utils/
|   +-- __init__.py
|   +-- dedup.py                    SHA-256 hash deduplication
|   +-- dates.py                    Date bounding, UTC handling
+-- scripts/
|   +-- export_pending.py           Export unenriched Sheet rows to pending.json
|   +-- import_enriched.py          Write enriched.json classifications back to Sheet
|   +-- enrich_phase8.py            Phase 8 Gemini enrichment runner (scope-only, full) [Phase 8]
|   +-- appstore_write_and_enrich.py  App Store scrape, sanity check, write, enrich, web_ddg retire [Phase 8c]
|   +-- _restore_valify_scope_header.py  One-time: restore column Q header after FEEDBACK_HEADERS bug [Phase 8c]
|   +-- backup_to_git.py            Dump all Sheet tabs to /backups/ as CSV
|   +-- audit_pre_recovery.py       Read-only audit: valify_scope/parse_error/sentiment breakdown per source [2026-06-16]
|   +-- enrich_recovery.py          Post-8c recovery: --step parse-error (33 rows) / --step valify-scope (29 rows) [2026-06-16]
|   +-- enrichment_checkpoint.json  Runtime checkpoint. Tracks completed and skipped row IDs per run.
+-- tests/
|   +-- test_replace_feedback_rows.py  47-assertion in-memory test for replace_feedback_rows column-drop fix [2026-06-16]
+-- validation/
|   +-- audit_pre_recovery.md       Pre-recovery audit report, all invariants confirmed [2026-06-16]
+-- docs/
|   +-- HANDOFF.md                  This file
|   +-- scrapers.md                 Platform approach and verified app IDs
|   +-- keywords.md                 Keyword sets EN + AR per client
|   +-- enrichment.md               Enrichment overview and per-client use cases
|   +-- enrichment_taxonomy.md      Field definitions and allowed enum values
|   +-- enrichment_hints.md         Per-client signal phrases and edge-case guidance
|   +-- enrichment_examples.md      Labelled input/output examples for tricky cases
|   +-- enrich_prompt.md            Paste into Claude Code to run manual enrichment
|   +-- sheet_schema.md             Google Sheet column structure
|   +-- runbook.md                  Incident response for broken scrapers
+-- backups/                        CSV snapshots of all Sheet tabs (date-stamped)
```

---

## Phase status

| Phase | Status | Description |
|---|---|---|
| 1 | done | Architecture design, documentation, repo scaffold |
| 2 | done | Amazon Play Store historical sweep, full pipeline validation |
| 3 | done | All 8 clients Play Store sweep |
| 4 | done | Housekeeping module (archival, row ceiling) |
| 5 | done | Rabbit and Raya app disambiguation, config.py corrections |
| 6 | done | Enrichment scripts (export_pending.py, import_enriched.py), first enrichment run |
| 7 | done | App Store and Web (DDG) scrapers; --source flag on main.py; 73 new rows written |
| 8 | done | Enrichment hardening: valify_scope + sentiment fields, Gemini classifier, re-enriched 27+73 rows |
| 8b | done | App Store scraper fix: inter-client sleep wired up (12s), suspected-block detection, one retry |
| 8c | done | App Store first write (30-day window, 93 rows), Gemini enrichment, web_ddg retirement (73 rows quarantined), sheets.py FEEDBACK_HEADERS fix. Phase 8 fully complete. |
| 8c-r1 | done | Post-8c recovery, closed 2026-07-05. Column-drop fix verified (47/47 test assertions). Found and fixed a second bug: 42 rows (29 + 13) had literal "parse_error" written to valify_scope/enrichment fields instead of being left blank; both recovery scripts' row-selection predicates now treat "parse_error" as missing. Step 1 (valify-scope, 29 rows): done, true=10/false=13/unsure=6, sanity check passed. Step 2 (parse-error, 13 rows): done, all real values, none remain parse_error. Step 3 (scope-only backfill): 0 rows needed, confirming Steps 1-2 fully closed the gap. Inter-batch sleep raised 4s to 6s. No unresolved rows. |
| 8-fallback | done | Fallback provider architecture: circuit breaker, provider chain (Gemini then Groq), write guard, checkpoint file. |
| 9 | next | Full automation. GitHub Actions cron at 06:00 UTC. Gemini auto-enrichment with Groq fallback. Git backup commit weekly. Email digest via Gmail SMTP. Groq Arabic quality test on 20-row sample before enabling fallback in production. GEMINI_API_KEY and GROQ_API_KEY required as GitHub Actions secrets. |
| 10 | pending | Read-only dashboard. Reads data/feedback.json via raw GitHub URL. Visible to full Valify team. Hosted on a free public platform. |
| 11 | pending | Tiered scaling (priority field per client, tier-based scrape frequency) |
| 12 | pending | Historical backfill for all 8 clients (App Store full, and the 7 non-Amazon Play Store clients) |
| 13 | pending | Extension runbooks (ADD_CLIENT.md, ADD_PLATFORM.md) |

---

## Sheet state (current)

As of 2026-07-05 (last write: 2026-07-05 Phase 8c-r1 closure, last backup: 2026-06-14, backup is stale and should be refreshed in Phase 9).

**Feedback Log total:** 3,353 data rows (no row count change since Phase 8c)

**Source breakdown:**
| Source | Count | Notes |
|---|---|---|
| play_store | 3,260 | All 8 clients, historical + daily sweeps through Phase 7 |
| appstore | 93 | All 8 clients, 30-day window (2026-05-16 to 2026-06-15). First App Store write. |
| web_ddg | 0 | Retired. 73 rows moved to Quarantine tab. |
| web_trustpilot | 0 | Disabled in Phase 7 (AWS WAF). |

**Quarantine tab:** 73 rows (all web_ddg, reason: "web_ddg retired: search snippet, not a user review.")

**Enrichment state (Feedback Log), whole-sheet totals as of 2026-07-05:**
| Field | Breakdown |
|---|---|
| sentiment | negative=1,711, positive=1,491, neutral=110, mixed=41 (legacy, pre-Phase-8 taxonomy). Zero parse_error. |
| feedback_type | off_topic=3,323, ux_friction=16, bug=12, compliment=2. Zero parse_error. |
| valify_scope | true=11, false=45, unsure=6, blank=3,291. Zero parse_error. |

Blank valify_scope (3,291 rows) is all off_topic rows (3,233 play_store + 58 appstore) that were never targeted for column-Q enrichment by design; off-topic rows are excluded from the daily digest regardless of valify_scope, so backfilling them has no product value. This is not a gap; it is the intended end state.

**On-topic rows (feedback_type not off_topic, 30 rows total) all have real valify_scope values:**
- 27 play_store + 2 appstore rows from the 2026-07-05 Step 1 recovery: true=10, false=13, unsure=6.
- 1 appstore row (row 3253) already had valify_scope=true from a prior run.

**appstore rows: 93 total, 0 parse_error.** 80 have real full enrichment from Phase 8c plus the 2026-06-16 recovery; 13 were re-enriched 2026-07-05 (all classified off_topic, valify_scope=false).

**Archive tab:** 0 data rows (housekeeping has not yet triggered archival)

**Last backup:** 2026-06-14 (scripts/backup_to_git.py, all 5 tabs written to /backups/). Stale by 3 weeks; refresh before or during Phase 9.

---

## Open backlog

**Phase 8c-r1: closed 2026-07-05.** No immediate next steps remain for enrichment recovery. See decisions log for the parse_error-in-column-Q bug found and fixed during closure.

**Infrastructure:**
- Phase 9: Full automation. Enable GitHub Actions cron at 06:00 UTC, integrate Gemini auto-enrichment via scripts/enrich_phase8.py, commit /backups/ to Git on a weekly schedule, and activate the email digest via Gmail SMTP. Requires GEMINI_API_KEY as a GitHub Actions secret.
- Trustpilot for Amazon (amazon.eg): approximately 85 reviews. Blocked in Phase 7 by AWS WAF at TLS-fingerprint level. Requires cloudscraper or curl_cffi to bypass. Low ROI vs Play Store volume. Re-enable by setting `_TRUSTPILOT_ENABLED = True` in scrapers/web.py after adding a bypass library.
- Service account key rotation completed 2026-07-05. Three keys existed for feedback-scraper, the first two are deleted. The third (current) key is active and has not been exposed. No further rotation action needed.

**Scale:**
- Phase 11: Tiered scaling. Add a priority field per client and implement tier-based scrape frequency (daily vs. alternate-day).
- Phase 12: Historical backfill for all 8 clients App Store + the 7 non-Amazon Play Store clients. Run `--mode historical` for all from their respective first_tx dates. App Store 30-day window was deliberate for Phase 8c; full backfill is Phase 12.
- Phase 13: Extension runbooks. ADD_CLIENT.md and ADD_PLATFORM.md step-by-step guides.

**Minor:**
- scripts/enrich_phase8.py summary print shows valify_scope counts only for the last batch, not cumulative. The actual sheet data is correct. The display inconsistency is cosmetic; fix in a future cleanup pass.
- scripts/appstore_write_and_enrich.py and scripts/_restore_valify_scope_header.py are one-time scripts. Consider removing them after Phase 11 to reduce clutter.
- 41 play_store rows have sentiment="mixed" from pre-Phase-8 manual enrichment. The Phase 8 taxonomy does not include "mixed". These rows are harmless as-is; they will be re-classified if a future scope-only pass targets them. No immediate action needed.
- Inter-batch sleep raised to 6s on 2026-07-05 (see decisions log). Closed.
- Local machine has no pagefile configured, which caused intermittent MemoryError failures during this session's Sheets API calls (unrelated to sheet size). See 2026-07-05 decisions log entry. Consider configuring a pagefile if local enrichment runs become unreliable again.

**Phase 9 pre-work confirmed:**
- Groq Arabic quality test: run (2026-07-06, `scripts/groq_arabic_test.py`). Groq confirmed unreachable from this local environment (403 Forbidden, geo-blocked, 4/4 attempts). Deferred, not failed: re-run via GitHub Actions `workflow_dispatch` once the workflow exists, to get a real Gemini-vs-Groq comparison before trusting Groq as the production fallback. See the 2026-07-06 decisions log entry and `validation/groq_arabic_test.md` for detail.
- GitHub Actions secrets: add GEMINI_API_KEY and GROQ_API_KEY as repository secrets before enabling the cron. Never commit either key to the repo.
- Ollama deferred: only revisit if the GitHub-Actions Groq Arabic quality test (still pending) comes back below the 75% match threshold. Local model hosting adds infrastructure complexity not justified at current scale.

---

## Tone and formatting rules

These rules apply to all code, comments, log output, and documentation in this repo:
- No emojis anywhere: not in source files, Markdown, log output, or terminal output.
- No em dashes and no en dashes anywhere. Use commas, colons, or semicolons instead. This applies to code comments, docstrings, log messages, Markdown files, and terminal output.
- One short comment per file or function when the why is non-obvious. Never multi-line comment blocks.
- Tables preferred over prose for structured comparisons.
- Variable and function names are lowercase_snake_case in Python.
- Column and field names match the Sheet schema exactly (see docs/sheet_schema.md).
