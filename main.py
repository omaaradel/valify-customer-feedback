#!/usr/bin/env python3
"""
Valify Customer Feedback Monitor

Usage:
  python main.py --client amazon --mode historical
  python main.py --client amazon --mode historical --dry-run
  python main.py --client amazon --mode daily
  python main.py --client amazon --mode daily --source appstore
  python main.py --client all --mode daily --source all --days 30
"""
import argparse
import logging
import subprocess
import sys
import time
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


def run(
    client_key: str,
    mode: str,
    source: str,
    dry_run: bool,
    backup: bool = False,
    days: int = None,
) -> None:
    log = logging.getLogger("main")

    # Resolve client list
    if client_key.lower() == "all":
        client_keys = list(CLIENTS.keys())
    else:
        key = client_key.lower()
        if key not in CLIENTS:
            log.error("Unknown client '%s'. Available: %s", key, sorted(CLIENTS.keys()))
            sys.exit(1)
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

        # ── Scrape ────────────────────────────────────────────────────────────
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
            if sheet:
                kws = get_keywords(client)
                sheet.upsert_admin(client, "success_empty", kws["en"], kws["ar"])
            continue

        # ── Dedup ─────────────────────────────────────────────────────────────
        new_items = filter_new(raw_items, seen)
        skipped = len(raw_items) - len(new_items)
        log.info(
            "[%s] After dedup: %d new, %d already seen",
            client.display_name, len(new_items), skipped,
        )

        if not new_items:
            log.info("[%s] Nothing new to write.", client.display_name)
            if sheet:
                kws = get_keywords(client)
                sheet.upsert_admin(client, "success_no_new", kws["en"], kws["ar"])
            continue

        # ── Write or preview ──────────────────────────────────────────────────
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
            continue

        new_hashes = [item["_hash"] for item in new_items]
        sheet.append_feedback(new_items)
        sheet.append_hashes(new_hashes)
        # Update local seen set so subsequent clients in this run don't re-process
        seen.update(new_hashes)

        kws = get_keywords(client)
        sheet.upsert_admin(client, "success", kws["en"], kws["ar"])
        log.info("[%s] Wrote %d rows to Feedback Log.", client.display_name, len(new_items))

        # ── Housekeeping ──────────────────────────────────────────────────────
        run_housekeeping(sheet, dry_run=False)

    # ── Optional backup (once, after all clients complete) ────────────────────
    if backup:
        log.info("Running backup_to_git.py ...")
        subprocess.run([sys.executable, "scripts/backup_to_git.py"], check=True)


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
""",
    )
    parser.add_argument(
        "--client",
        required=True,
        metavar="NAME",
        help="Client key (e.g. 'amazon') or 'all' to run every client.",
    )
    parser.add_argument(
        "--mode",
        choices=["historical", "daily"],
        required=True,
        help="'historical' sweeps back to first_tx; 'daily' fetches last 48 h",
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
        help="Scrape and log results without writing to Sheet",
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
    args = parser.parse_args()
    run(args.client, args.mode, args.source, args.dry_run, backup=args.backup, days=args.days)


if __name__ == "__main__":
    main()
