"""
housekeeping.py — Automatic Google Sheet size management.

Called at the end of every main.py run (after scrape + write). Keeps the
Feedback Log under sustainable row counts without any manual cleanup.

Thresholds (data rows, excluding header):
  > 25,000  →  archive off_topic rows older than 30 days → Archive tab
  > 35,000  →  archive ALL rows older than 60 days → Archive tab
  > 45,000  →  create new sibling Google Spreadsheet, move rows older
               than 30 days there (including Archive tab), reset both

Standalone usage:
  python housekeeping.py [--dry-run]
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
SOFT_LIMIT   = 25_000   # prune off_topic + 30d → Archive tab
MEDIUM_LIMIT = 35_000   # prune all + 60d → Archive tab
HARD_LIMIT   = 45_000   # new Archive spreadsheet
ARCHIVE_LIMIT = 50_000  # Archive tab ceiling before new-sheet creation

SOFT_AGE   = 30   # days
MEDIUM_AGE = 60
HARD_AGE   = 30   # cutoff for hard-limit new-sheet move


# ── Main entry point ──────────────────────────────────────────────────────────

def run_housekeeping(sheet, dry_run: bool = False) -> None:
    """
    Run all housekeeping checks. Call with an open SheetsClient instance.
    sheet — SheetsClient from sheets.py
    dry_run — if True, log what would happen but make no changes
    """
    now = datetime.now(timezone.utc)
    row_count = sheet.count_feedback_rows()
    log.info("Housekeeping: Feedback Log has %d data rows", row_count)

    if row_count <= SOFT_LIMIT:
        log.info("Housekeeping: no action needed (%d <= %d)", row_count, SOFT_LIMIT)
        return

    # ── (b) > 25k: archive off_topic older than 30 days ─────────────────────
    log.info(
        "Housekeeping: %d > %d — archiving off_topic rows older than %d days",
        row_count, SOFT_LIMIT, SOFT_AGE,
    )
    _archive_matching(
        sheet, dry_run,
        feedback_type_filter="off_topic",
        before_date=now - timedelta(days=SOFT_AGE),
        label=f"off_topic > {SOFT_AGE}d old",
    )

    row_count = sheet.count_feedback_rows()
    log.info("Housekeeping: row count after step (b): %d", row_count)
    if row_count <= MEDIUM_LIMIT:
        return

    # ── (c) > 35k: archive ALL older than 60 days ───────────────────────────
    log.info(
        "Housekeeping: %d > %d — archiving ALL rows older than %d days",
        row_count, MEDIUM_LIMIT, MEDIUM_AGE,
    )
    _archive_matching(
        sheet, dry_run,
        feedback_type_filter=None,
        before_date=now - timedelta(days=MEDIUM_AGE),
        label=f"all rows > {MEDIUM_AGE}d old",
    )

    row_count = sheet.count_feedback_rows()
    log.info("Housekeeping: row count after step (c): %d", row_count)
    if row_count <= HARD_LIMIT:
        return

    # ── (d) > 45k: create new Archive spreadsheet ───────────────────────────
    log.info(
        "Housekeeping: HARD LIMIT exceeded (%d > %d) — creating archive spreadsheet",
        row_count, HARD_LIMIT,
    )
    _offload_to_new_spreadsheet(sheet, dry_run, now)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _archive_matching(
    sheet,
    dry_run: bool,
    feedback_type_filter: Optional[str],
    before_date: datetime,
    label: str,
) -> None:
    rows = sheet.get_all_feedback_rows()
    to_archive = [
        r for r in rows
        if _is_before(r.get("post_date", ""), before_date)
        and (feedback_type_filter is None or r.get("feedback_type") == feedback_type_filter)
    ]

    if not to_archive:
        log.info("Housekeeping: 0 rows matched — %s", label)
        return

    log.info(
        "Housekeeping: %s%d rows (%s)",
        "[DRY RUN] would archive " if dry_run else "archiving ",
        len(to_archive),
        label,
    )
    if dry_run:
        return

    # Guard: if Archive tab would overflow, offload it first
    archive_count = sheet.count_archive_rows()
    if archive_count + len(to_archive) > ARCHIVE_LIMIT:
        log.warning(
            "Housekeeping: Archive tab would exceed %d rows (%d + %d); "
            "offloading Archive tab to new spreadsheet first",
            ARCHIVE_LIMIT, archive_count, len(to_archive),
        )
        _offload_to_new_spreadsheet(sheet, dry_run=False, now=datetime.now(timezone.utc))

    sheet.append_to_archive(to_archive)
    keep = [r for r in rows if r not in to_archive]
    sheet.replace_feedback_rows(keep)
    log.info(
        "Housekeeping: archived %d rows; %d remain in Feedback Log",
        len(to_archive), len(keep),
    )


def _offload_to_new_spreadsheet(sheet, dry_run: bool, now: datetime) -> None:
    date_str = now.strftime("%Y-%m-%d")
    title = f"Valify Feedback Monitor — Archive {date_str}"
    cutoff = now - timedelta(days=HARD_AGE)

    fb_rows     = sheet.get_all_feedback_rows()
    archive_rows = sheet.get_all_archive_rows()

    to_move_fb  = [r for r in fb_rows if _is_before(r.get("post_date", ""), cutoff)]
    all_to_move = to_move_fb + archive_rows

    log.info(
        "Housekeeping: %s%d rows to '%s'",
        "[DRY RUN] would move " if dry_run else "moving ",
        len(all_to_move),
        title,
    )
    if dry_run:
        return

    new_sheet_id = sheet.create_archive_spreadsheet(title, all_to_move)
    log.info("Housekeeping: archive spreadsheet created (ID: %s)", new_sheet_id)

    keep = [r for r in fb_rows if r not in to_move_fb]
    sheet.replace_feedback_rows(keep)
    sheet.clear_archive_tab()
    log.info(
        "Housekeeping: %d rows moved; %d remain in Feedback Log; Archive tab cleared",
        len(all_to_move), len(keep),
    )

    _record_archive_in_claude_md(date_str, new_sheet_id)


def _is_before(date_str: str, cutoff: datetime) -> bool:
    if not date_str:
        return False
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt < cutoff
    except ValueError:
        return False


def _record_archive_in_claude_md(date_str: str, sheet_id: str) -> None:
    claude_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CLAUDE.md")
    entry = (
        f"| {date_str} | Auto-archive spreadsheet created | "
        f"ID: `{sheet_id}` — rows older than {HARD_AGE}d moved from live sheet |\n"
    )
    try:
        with open(claude_path, "a", encoding="utf-8") as fh:
            fh.write(entry)
        log.info("Housekeeping: recorded archive sheet ID in CLAUDE.md")
    except OSError as exc:
        log.warning("Housekeeping: could not update CLAUDE.md: %s", exc)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    parser = argparse.ArgumentParser(
        description="Valify Sheet housekeeping — safe to run at any time",
        epilog="With --dry-run: reports what would be done without changing anything.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report actions without moving or deleting rows",
    )
    args = parser.parse_args()

    from sheets import SheetsClient
    sheet = SheetsClient()
    run_housekeeping(sheet, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
