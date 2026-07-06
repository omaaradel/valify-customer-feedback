#!/usr/bin/env python3
"""
Valify Customer Feedback Monitor

Usage:
  python main.py --client amazon --mode historical
  python main.py --client amazon --mode historical --dry-run
  python main.py --client amazon --mode daily
  python main.py --client amazon --mode daily --source appstore
  python main.py --client all --mode daily --source all --days 30
  python main.py                            (defaults: client=all, mode=daily, source=all)
  python main.py --enrich                   (Gemini/Groq enrichment, full mode)
  python main.py --enrich --enrich-mode scope-only
  python main.py --export-json
  python main.py --digest
  python main.py --digest --dry-run
"""
import argparse
import logging
import sys
import warnings
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv

load_dotenv()

from config import CLIENTS, ClientConfig
from housekeeping import run_housekeeping
from keywords import get_keywords
from scrapers.playstore import fetch as fetch_playstore
from scrapers.appstore import fetch as fetch_appstore
from scrapers.web import fetch as fetch_web
from sheets import SheetsClient
from utils.dates import get_since_date
from utils.dedup import filter_new

_VALID_SOURCES = ("playstore", "appstore", "web", "all")
_VALID_ENRICH_MODES = ("full", "scope-only")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    # ERROR-level messages also go to scrape_errors.log in the project root
    file_handler = logging.FileHandler("scrape_errors.log", encoding="utf-8")
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s")
    )
    logging.getLogger().addHandler(file_handler)

    # Silence noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("gspread").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    # duckduckgo_search 8.x warns it has been renamed to ddgs; suppress it
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="duckduckgo_search")


def scrape_client(
    client: ClientConfig,
    client_key: str,
    source: str,
    since,
    max_per_lang: int,
    appstore_call_n: int = 0,
) -> List[Dict[str, Any]]:
    """Run selected source(s) for one client. Each source is isolated: one failure
    does not abort the others.

    appstore_call_n: number of App Store fetches already completed this run.
    When > 0, the App Store scraper sleeps _SLEEP_BETWEEN_CLIENTS before fetching
    to avoid Apple CDN throttling on multi-client runs.
    """
    log = logging.getLogger("main")
    raw: List[Dict] = []

    if source in ("playstore", "all"):
        try:
            rows = fetch_playstore(
                app_id=client.playstore_id,
                display_name=client.display_name,
                since=since,
                max_per_lang=max_per_lang,
            )
            raw.extend(rows)
        except Exception as exc:
            log.error("[%s] playstore scraper failed: %s", client.display_name, exc)

    if source in ("appstore", "all"):
        if client.appstore_id:
            try:
                rows, suspected_block = fetch_appstore(
                    app_id=client.appstore_id,
                    display_name=client.display_name,
                    since=since,
                    sleep_before=(appstore_call_n > 0),
                )
                if suspected_block:
                    log.error(
                        "[%s] App Store suspected block not resolved -- 0 rows this client",
                        client.display_name,
                    )
                raw.extend(rows)
            except Exception as exc:
                log.error("[%s] appstore scraper failed: %s", client.display_name, exc)
        else:
            log.info("[%s] No App Store ID configured -- skipping appstore", client.display_name)

    if source in ("web", "all"):
        try:
            rows = fetch_web(
                client_key=client_key,
                display_name=client.display_name,
                since=since,
            )
            raw.extend(rows)
        except Exception as exc:
            log.error("[%s] web scraper failed: %s", client.display_name, exc)

    return raw


def run_scrape(
    client_key: str = "all",
    mode: str = "daily",
    source: str = "all",
    dry_run: bool = False,
    backup: bool = False,
    days: int = None,
) -> Dict[str, int]:
    """Scrape, dedup, and write feedback for one or all clients, then run
    housekeeping. Returns a dict mapping client_key to the number of new rows
    written (0 for dry runs, empty items, or clients with nothing new). Errors
    are logged and leave the affected client's count out of the result rather
    than raising; the caller decides what to do with a partial result.
    """
    log = logging.getLogger("main")
    results: Dict[str, int] = {}

    try:
        if client_key.lower() == "all":
            client_keys = list(CLIENTS.keys())
        else:
            key = client_key.lower()
            if key not in CLIENTS:
                log.error("Unknown client '%s'. Available: %s", key, sorted(CLIENTS.keys()))
                return results
            client_keys = [key]

        # Create the Sheets connection and load seen hashes ONCE for the entire run.
        # Sharing one client avoids hitting the 60-reads/minute API quota when running
        # all 8 clients sequentially.
        sheet: Optional[SheetsClient] = None
        seen: Set[str] = set()
        if not dry_run:
            sheet = SheetsClient()
            seen = sheet.get_seen_hashes()
            log.info("Loaded %d existing hashes from Sheet", len(seen))

        # Tracks how many App Store fetches have completed this run.
        # Passed to scrape_client so it can tell fetch_appstore to sleep before
        # non-first clients, preventing Apple CDN throttling.
        appstore_call_n = 0

        for key in client_keys:
            client = CLIENTS[key]
            log.info(
                "=== %s | mode=%s | source=%s | dry_run=%s ===",
                client.display_name, mode, source, dry_run,
            )

            since = get_since_date(mode, client.first_tx, days=days)
            log.info("Fetching feedback since %s", since.date())

            if days and days > 7:
                max_per_lang = 5000
            elif mode == "historical":
                max_per_lang = 2000
            else:
                max_per_lang = 300

            # -- Scrape --------------------------------------------------------
            raw_items = scrape_client(client, key, source, since, max_per_lang,
                                      appstore_call_n=appstore_call_n)
            if source in ("appstore", "all") and client.appstore_id:
                appstore_call_n += 1
            log.info(
                "[%s] Scraped: %d raw items (source: %s)",
                client.display_name, len(raw_items), source,
            )

            if not raw_items:
                log.info("[%s] No items found.", client.display_name)
                results[key] = 0
                if sheet:
                    kws = get_keywords(client)
                    sheet.upsert_admin(client, "success_empty", kws["en"], kws["ar"])
                continue

            # -- Dedup -----------------------------------------------------------
            new_items = filter_new(raw_items, seen)
            skipped = len(raw_items) - len(new_items)
            log.info(
                "[%s] After dedup: %d new, %d already seen",
                client.display_name, len(new_items), skipped,
            )

            if not new_items:
                log.info("[%s] Nothing new to write.", client.display_name)
                results[key] = 0
                if sheet:
                    kws = get_keywords(client)
                    sheet.upsert_admin(client, "success_no_new", kws["en"], kws["ar"])
                continue

            # -- Write or preview --------------------------------------------------
            if dry_run:
                log.info(
                    "[%s] [DRY RUN] Would write %d items. First 5:",
                    client.display_name, len(new_items),
                )
                for item in new_items[:5]:
                    log.info(
                        "  %s  src=%-16s  rating=%-2s  %r",
                        item["post_date"][:10] if item.get("post_date") else "no-date",
                        item["source"],
                        item.get("rating", "?"),
                        item["raw_text"][:80],
                    )
                if len(new_items) > 5:
                    log.info("  ... and %d more", len(new_items) - 5)
                results[key] = len(new_items)
                continue

            new_hashes = [item["_hash"] for item in new_items]
            sheet.append_feedback(new_items)
            sheet.append_hashes(new_hashes)
            # Update local seen set so subsequent clients in this run don't re-process
            seen.update(new_hashes)

            kws = get_keywords(client)
            sheet.upsert_admin(client, "success", kws["en"], kws["ar"])
            log.info("[%s] Wrote %d rows to Feedback Log.", client.display_name, len(new_items))
            results[key] = len(new_items)

            # -- Housekeeping ------------------------------------------------------
            run_housekeeping(sheet, dry_run=False)

        # -- Optional backup (once, after all clients complete) ------------------
        if backup:
            log.info("Running backup...")
            run_backup()

    except Exception as exc:
        log.error("run_scrape failed: %s", exc)

    return results


def run_enrich(mode: str = "full") -> dict:
    """Run Gemini/Groq enrichment via the provider chain. mode is 'full' (any
    row with no sentiment yet) or 'scope-only' (backfill valify_scope on
    already-enriched on-topic rows). Returns a summary dict: total rows
    processed, valify_scope counts, sentiment counts, and skipped count. On
    failure, returns a zeroed summary with an 'error' key instead of raising.
    """
    log = logging.getLogger("main")
    empty = {"total": 0, "valify_scope": {}, "sentiment": {}, "skipped": 0}
    if mode not in _VALID_ENRICH_MODES:
        log.error("Unknown enrich mode '%s'. Use one of %s", mode, _VALID_ENRICH_MODES)
        return {**empty, "error": f"unknown mode {mode}"}
    try:
        from scripts.enrich_phase8 import run_scope_only, run_full
        if mode == "scope-only":
            return run_scope_only(dry_run=False)
        return run_full(dry_run=False)
    except Exception as exc:
        log.error("run_enrich failed: %s", exc)
        return {**empty, "error": str(exc)}


def run_export_json() -> Optional[str]:
    """Export the Feedback Log to data/feedback.json, structured by client.
    Returns the output path, or None on failure."""
    log = logging.getLogger("main")
    try:
        from scripts.export_json import export_feedback_json
        return export_feedback_json()
    except Exception as exc:
        log.error("run_export_json failed: %s", exc)
        return None


def run_backup() -> Optional[str]:
    """Dump all Sheet tabs to /backups/ as CSV. Returns the backups directory
    path, or None on failure."""
    log = logging.getLogger("main")
    try:
        from scripts.backup_to_git import run_backup as _run_backup_impl
        return _run_backup_impl()
    except Exception as exc:
        log.error("run_backup failed: %s", exc)
        return None


def run_digest(dry_run: bool = False) -> bool:
    """Send the weekly email digest (Mondays only, unless dry_run). Returns
    True if an email was sent, False if skipped (not Monday, dry run, missing
    data/feedback.json, or a send failure)."""
    log = logging.getLogger("main")
    try:
        from scripts.send_digest import send_digest
        return send_digest(dry_run=dry_run)
    except Exception as exc:
        log.error("run_digest failed: %s", exc)
        return False


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Valify Customer Feedback Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --client amazon --mode historical
  python main.py --client amazon --mode historical --dry-run
  python main.py --client amazon --mode daily
  python main.py --client amazon --mode daily --source appstore
  python main.py --client all --mode daily --source all --days 30
  python main.py
  python main.py --enrich
  python main.py --enrich --enrich-mode scope-only
  python main.py --export-json
  python main.py --digest
  python main.py --digest --dry-run
""",
    )
    parser.add_argument(
        "--client",
        default="all",
        metavar="NAME",
        help="Client key (e.g. 'amazon') or 'all' to run every client. Default: all.",
    )
    parser.add_argument(
        "--mode",
        choices=["historical", "daily"],
        default="daily",
        help="'historical' sweeps back to first_tx; 'daily' fetches last 48 h. Default: daily.",
    )
    parser.add_argument(
        "--source",
        choices=list(_VALID_SOURCES),
        default="all",
        help="Data source: playstore, appstore, web, or all (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and log results without writing to Sheet. Also used by --digest to preview without sending.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="After writing, dump all tabs to /backups/ as CSV",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        metavar="N",
        help="Override lookback window to exactly N days. Use --days 30 for the Phase 7 sweep.",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Run Gemini/Groq enrichment instead of scraping. Use --enrich-mode to pick full or scope-only.",
    )
    parser.add_argument(
        "--enrich-mode",
        choices=list(_VALID_ENRICH_MODES),
        default="full",
        help="Enrichment mode when --enrich is set: full or scope-only. Default: full.",
    )
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export the Feedback Log to data/feedback.json, structured by client.",
    )
    parser.add_argument(
        "--digest",
        action="store_true",
        help="Send the weekly email digest. Skips cleanly if today is not Monday.",
    )
    args = parser.parse_args()

    ran_action = False

    if args.enrich:
        result = run_enrich(mode=args.enrich_mode)
        print(result)
        ran_action = True

    if args.export_json:
        path = run_export_json()
        print(path)
        ran_action = True

    if args.digest:
        sent = run_digest(dry_run=args.dry_run)
        print(f"digest sent: {sent}")
        ran_action = True

    if not ran_action:
        run_scrape(args.client, args.mode, args.source, args.dry_run, backup=args.backup, days=args.days)


if __name__ == "__main__":
    main()
