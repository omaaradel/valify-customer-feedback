# Runbook — Incident Response for Broken Scrapers

## How to detect a problem

1. **GitHub Actions** — check the Actions tab in the repo. A red X means the run failed.
2. **Admin tab** — `last_run_status` column. Values other than `success`:
   - `partial` — some scrapers returned results, others failed
   - `failed` — all scrapers failed for a client
   - `facebook_blocked` — Facebook specifically blocked the scraper
3. **Email digest** — if no digest arrives by 06:30 UTC, the run likely crashed entirely.
4. **Google Sheet** — if no new rows appear for >48 hours, something is broken.

---

## Scraper-Specific Issues

### Play Store scraper fails

**Symptom:** `google-play-scraper` raises `NotFoundError` or `HTTPError`.

**Steps:**
1. Verify the app ID in `config.py` is still correct:
   Visit `https://play.google.com/store/apps/details?id={app_id}` — if 404, the app was removed or renamed.
2. If the app was renamed/repackaged, find the new ID on the Play Store and update `config.py`.
3. If the error is `429 Too Many Requests`, increase the sleep between requests in `scrapers/playstore.py`.
4. If the scraper library itself is broken, check https://github.com/JoMingyu/google-play-scraper/issues.

**Fallback:** Mark `playstore_url = "unavailable"` in Admin tab; continue with other sources.

---

### App Store scraper returns 0 rows (all clients)

**Symptom:** All 8 clients return 0 App Store rows in a single multi-client run, even though
individual client tests work.

**Likely cause:** Apple's iTunes RSS CDN throttles sequential requests from the same IP.
After the first 2-3 clients are fetched, the CDN begins returning empty feeds (883 bytes, 0
entries) for all subsequent requests. This is a CDN-level behavior, not a code bug.

**Steps:**
1. Confirm it is the CDN, not your app ID. Run a single client with a 7-day window:
   ```
   python main.py --client thndr --mode daily --source appstore --days 7
   ```
   If it returns results, the scraper is healthy and the issue is the sequential multi-client run.
2. To sweep all 8 clients, add a 60-second sleep between clients. Edit `scrapers/appstore.py`
   and increase `_SLEEP_BETWEEN_CLIENTS` from `2.0` to `60.0` seconds, then re-run.
3. Alternatively, run each client as a separate invocation with a 5-minute gap:
   ```
   python main.py --client amazon --mode daily --source appstore
   # wait 5 minutes
   python main.py --client thndr --mode daily --source appstore
   # etc.
   ```

**Fallback:** Skip App Store for that run; Play Store coverage is primary.

---

### App Store scraper fails for one client

**Symptom:** `requests.exceptions.HTTPError` or `JSONDecodeError` for a specific client.

**Steps:**
1. Verify the App Store ID in `config.py` is still valid:
   Visit `https://apps.apple.com/eg/app/id{app_id}` -- if the page 404s, the app was removed.
2. If the app is unavailable in the Egypt storefront (`country='eg'`), try `country='sa'`
   (Saudi Arabia) as a fallback; Egyptian users sometimes leave reviews there.
3. Update the ID in `config.py` if the app was renamed or republished.

---

### Reddit scraping

Reddit was dropped from this project on 2026-06-14. Reddit's Responsible Builder Policy
restricts the legacy Data API to moderation use cases; commercial product analytics does not
qualify. `scrapers/reddit.py` does not exist in this repo. Reddit content may surface
incidentally via DuckDuckGo results in `scrapers/web.py`.

---

### Facebook scraping

Facebook scraping was dropped from Phase 7 on 2026-06-14. `mbasic.facebook.com` hard-redirects
unauthenticated requests to login; `m.facebook.com` serves a JS SPA; Facebook RSS feeds return
404. Under the project constraints (no login or cookies, no paid services), Facebook is not
reachable. `scrapers/facebook.py` does not exist in this repo. Facebook content may surface
incidentally via DuckDuckGo results in `scrapers/web.py`.

---

### duckduckgo-search fails or returns 0 results

**Symptom:** `duckduckgo_search.exceptions.DuckDuckGoSearchException`, empty results across
all queries, or a `RuntimeWarning` saying the package was renamed to `ddgs`.

**Steps:**
1. The `duckduckgo_search` 8.x library was renamed to `ddgs`. The rename warning is harmless
   but can be silenced by installing the new package:
   ```
   pip install ddgs
   ```
   and updating the import in `scrapers/web.py` from `duckduckgo_search` to `ddgs`.
2. DuckDuckGo rate-limits aggressively if queries are run without sleeping. The scraper sleeps
   1.5 seconds between queries (`_SLEEP_BETWEEN_QUERIES`). If rate-limited, increase to 3.0s.
3. If results are consistently 0 for all queries: DDG is likely temporarily blocking the IP.
   Wait 15 minutes and retry a single query manually:
   ```python
   from duckduckgo_search import DDGS
   print(list(DDGS().text("Thndr Egypt account verification problem", max_results=5)))
   ```
4. If zero results persist, the library may be broken. Check the issue tracker at
   https://github.com/deedy5/duckduckgo_search.
5. Zero results for a specific client (e.g., Amazon, Rabbit, Midbank) may simply mean DDG does
   not surface public KYC complaints for that client. This is expected for niche apps.

**Fallback:** Zero DDG results are logged but not an error. Play Store coverage remains primary.

---

### Enrichment produces wrong classifications

**Symptom:** Classified rows have clearly wrong `sentiment`, `product_area`, or `severity`.

**Steps:**
1. Blank out the affected cells in the Feedback Log (sentiment through claude_summary columns).
2. Paste `docs/enrich_prompt.md` into a fresh Claude Code session — it will re-export
   and re-classify only rows where `sentiment` is blank.
3. Review the updated rows in the Sheet.

---

### Google Sheets write fails

**Symptom:** `gspread.exceptions.APIError` (403 or 429).

**Steps:**
1. **403 Forbidden:** The service account has lost access to the sheet. Re-share the sheet with the service account email (Editor access).
2. **429 Rate Limited:** Reduce write batch size in `sheets.py` from 100 rows to 50 rows per `append_rows()` call. Add `time.sleep(1)` between batch writes.
3. **Quota exceeded:** Free tier allows 300 requests/minute and 60 minutes of server processing per user per day. If exceeded, consider batching more aggressively or reducing scraping frequency.

---

### GitHub Actions run never starts

**Symptom:** No run in the Actions tab at the expected time.

**Steps:**
1. GitHub disables scheduled workflows after 60 days of repo inactivity. Push a small commit (or trigger the workflow manually) to re-enable.
2. Check the YAML file for syntax errors: `cat .github/workflows/daily.yml`.
3. Ensure the workflow file is on the default branch (`main`).

---

## Partial Run Recovery

If a run fails partway through (e.g., enrichment crashes after scraping 5 of 8 clients):
- Items already written to the sheet are safe (append-only).
- Hashes for written items are already in `seen_hashes`, so re-running will not duplicate them.
- Re-run with `python main.py --mode daily --client {failed_client}` to process only the missing clients.

---

## Adding a New Client

1. Add a new entry to `config.py` with all required fields.
2. Add keyword sets to `docs/keywords.md` and `keywords.py`.
3. Find and add Play Store and App Store app IDs.
4. Run `python main.py --mode historical --client {new_client}` for the initial sweep.
5. Add a row to the Admin tab manually if the automation doesn't create it.

---

## Contacts

| Who | What |
|-----|------|
| Valify Engineering | If a client's app ID changes or their Valify integration changes |
| Valify Account Team | If a client's name/branding changes (affects keywords) |
| GitHub repo owner | For cron schedule changes or secrets rotation |
