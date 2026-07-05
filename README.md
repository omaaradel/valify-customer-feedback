# Valify Customer Feedback Monitor

Scrapes public app-store reviews about Valify Analytics' clients' KYC flows
and writes results to a Google Sheet. Enrichment (classification) is done
manually by pasting `docs/enrich_prompt.md` into a Claude Code session.

**Current phase:** Amazon Play Store sweep only.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your credentials
```

## Run

### Step 1 — Scrape (automated)

```bash
# First run — fetch all Amazon reviews since 2026-03-24
python main.py --client amazon --mode historical

# Preview without writing to Sheet
python main.py --client amazon --mode historical --dry-run

# Subsequent daily runs
python main.py --client amazon --mode daily

# Daily run + dump all tabs to /backups/ as CSV
python main.py --client amazon --mode daily --backup
```

Housekeeping runs automatically at the end of every scrape (no separate
command needed). It checks the Feedback Log row count and archives old
off-topic rows to the Archive tab if thresholds are exceeded. To preview
what housekeeping would do without making changes:

```bash
python housekeeping.py --dry-run
```

### Step 2 — Enrich (manual, human-triggered)

Open a fresh Claude Code session and paste the contents of `docs/enrich_prompt.md`.
Claude will classify all unenriched rows and write the results back to the Sheet.

### Step 3 — Backup (optional, on demand)

```bash
python scripts/backup_to_git.py
```

Writes every Sheet tab as a CSV to `/backups/` (overwrites same-day files).
Use `--backup` on `main.py` to run this automatically after each scrape.
Git commit of `/backups/` is handled in Phase 9.

## Required credentials (in `.env`)

| Variable | How to get it |
|----------|--------------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Create a service account in GCP → Sheets API → download JSON → base64-encode it |
| `GOOGLE_SHEET_ID` | String between `/d/` and `/edit` in your Sheet URL |

Full setup steps: see **Deliverables** section in the conversation that produced this repo.

## Output

Four tabs in the Google Sheet:
- **Feedback Log** — one row per review; sentiment/classification columns filled after Step 2
- **Archive** — rows moved here by housekeeping (same columns as Feedback Log)
- **Admin** — one row per client with status and keyword state
- **seen_hashes** — deduplication registry (do not edit manually)

## Docs

| File | Contents |
|------|---------|
| `docs/scrapers.md` | Platform approach + verified app IDs |
| `docs/keywords.md` | Keyword sets EN + AR per client |
| `docs/enrichment.md` | Classification field definitions and allowed values |
| `docs/enrich_prompt.md` | Paste into Claude Code to run manual enrichment |
| `docs/sheet_schema.md` | Column definitions and allowed values |
| `docs/runbook.md` | What to do when scrapers break |
| `CLAUDE.md` | Full project context, architecture, cost estimates |
